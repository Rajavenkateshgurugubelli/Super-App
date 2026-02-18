import logging
from app import policy_pb2
from app import policy_pb2_grpc

class PolicyService(policy_pb2_grpc.PolicyServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def CheckCompliance(self, request, context):
        self._logger.info(f"Checking compliance for user {request.user_id} performing {request.action} in {request.target_region}")
        # Mock logic: Block if target region is 'Restricted'
        allowed = True
        reason = "Compliant"
        if request.target_region == "Restricted":
            allowed = False
            reason = "Region Restricted"
            
        return policy_pb2.CheckComplianceResponse(
            allowed=allowed,
            reason=reason
        )

    def GetRegionPolicy(self, request, context):
        return policy_pb2.GetRegionPolicyResponse(
            policy=policy_pb2.Policy(
                policy_id="pol_1",
                region=request.region,
                rules={"data_residency": "strict", "gdpr": "enabled"}
            )
        )
