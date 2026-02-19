import logging
from app import policy_pb2
from app import policy_pb2_grpc

class PolicyService(policy_pb2_grpc.PolicyServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def CheckCompliance(self, request, context):
        self._logger.info(f"Checking compliance: User={request.user_id}, Action={request.action}, TargetRegion={request.target_region}")
        
        # Policy 1: Blocked Regions (e.g. India sending to restricted zones, mock logic)
        # Using string mapping for demo: 
        # Source Region comes from User (need to lookup user? Or pass in request? 
        # Request only has user_id. PolicyService ideally shouldn't depend on UserService DB directly for decoupling.
        # But for this monolithic-style repo, we can direct query or assume source region is passed.
        # Let's assume for now checks are simple rules based on inputs.
        
        if request.target_region == "Restricted":
            return policy_pb2.CheckComplianceResponse(allowed=False, reason="Region Restricted")
            
        # Policy 2: High Value Cross-Border Transfers
        # We need amount for this. The current proto CheckComplianceRequest lacks amount.
        # For now, let's just implement a mocked region check.
        # "If user is from Region A and target is Region B, check rules"
        
        # Extended Logic Attempt (simulation):
        # We'll just define a rule: "No transfers to region ID '99'"
        if request.target_region == "99":
             return policy_pb2.CheckComplianceResponse(allowed=False, reason="Region 99 is sanctioned")

        return policy_pb2.CheckComplianceResponse(allowed=True, reason="Compliant")

    def GetRegionPolicy(self, request, context):
        return policy_pb2.GetRegionPolicyResponse(
            policy=policy_pb2.Policy(
                policy_id="pol_1",
                region=request.region,
                rules={"data_residency": "strict", "gdpr": "enabled"}
            )
        )
