import logging
from app import policy_pb2
from app import policy_pb2_grpc
import redis
import os
import json

class PolicyService(policy_pb2_grpc.PolicyServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.redis_client = None
        
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self._logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            self._logger.warning(f"Failed to connect to Redis: {e}. Policy caching disabled.")

    def CheckCompliance(self, request, context):
        self._logger.info(f"Checking compliance: User={request.user_id}, Action={request.action}, TargetRegion={request.target_region}")
        
        cache_key = f"policy:{request.user_id}:{request.action}:{request.target_region}"
        
        # 1. Check Cache
        if self.redis_client:
            try:
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    self._logger.debug("Policy Cache Hit")
                    data = json.loads(cached_result)
                    return policy_pb2.CheckComplianceResponse(
                        allowed=data["allowed"], 
                        reason=data["reason"]
                    )
            except Exception as e:
                self._logger.warning(f"Redis Cache Error: {e}")

        # 2. Evaluate Policy
        allowed = True
        reason = "Compliant"

        if request.target_region == "Restricted":
            allowed = False
            reason = "Region Restricted"
        elif request.target_region == "99":
            allowed = False
            reason = "Region 99 is sanctioned"

        # 3. Cache Result
        if self.redis_client:
            try:
                cache_data = json.dumps({"allowed": allowed, "reason": reason})
                self.redis_client.set(cache_key, cache_data, ex=300) # TTL 5 minutes
            except Exception as e:
                self._logger.warning(f"Redis Set Error: {e}")

        return policy_pb2.CheckComplianceResponse(allowed=allowed, reason=reason)

    def GetRegionPolicy(self, request, context):
        return policy_pb2.GetRegionPolicyResponse(
            policy=policy_pb2.Policy(
                policy_id="pol_1",
                region=request.region,
                rules={"data_residency": "strict", "gdpr": "enabled"}
            )
        )
