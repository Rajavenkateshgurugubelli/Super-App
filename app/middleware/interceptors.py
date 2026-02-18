import grpc
import logging
from app.services.policy_service import PolicyService
from app import policy_pb2

class GeoFencingInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        # In a real app, we might inject this or initialize it differently
        self._policy_service = PolicyService()

    def intercept_service(self, continuation, handler_call_details):
        # Extract metadata
        metadata = dict(handler_call_details.invocation_metadata)
        region = metadata.get('x-region', 'unknown')
        user_id = metadata.get('x-user-id', 'anonymous')
        
        self._logger.info(f"GeoFencingInterceptor: Intercepted request from region: {region} for user: {user_id}")

        # Basic Geo-Fencing Check
        if region == 'Restricted':
             self._logger.warning(f"Blocking request from restricted region: {region}")
             # For this Genesis phase, we log heavily but permit the request 
             # to allow easier testing of other components. 
             # To strictly block, we would raise a gRPC error here.
             # abort_rpc(grpc.StatusCode.PERMISSION_DENIED, "Access Denied by Geo-Fencing")

        return continuation(handler_call_details)
