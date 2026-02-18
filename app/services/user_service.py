import logging
import uuid
from app import user_pb2
from app import user_pb2_grpc

class UserService(user_pb2_grpc.UserServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def CreateUser(self, request, context):
        self._logger.info(f"Creating user for email: {request.email}")
        user_id = str(uuid.uuid4())
        return user_pb2.CreateUserResponse(
            user=user_pb2.User(
                user_id=user_id,
                email=request.email,
                name=request.name,
                region=request.region,
                kyc_status=user_pb2.KYC_STATUS_PENDING
            )
        )

    def GetUser(self, request, context):
        self._logger.info(f"Getting user: {request.user_id}")
        return user_pb2.GetUserResponse(
            user=user_pb2.User(
                user_id=request.user_id,
                email="mock@example.com",
                name="Mock User",
                region=user_pb2.REGION_US,
                kyc_status=user_pb2.KYC_STATUS_VERIFIED
            )
        )

    def UpdateProfile(self, request, context):
        self._logger.info(f"Updating profile for: {request.user_id}")
        return user_pb2.UpdateProfileResponse(
            user=user_pb2.User(
                user_id=request.user_id,
                name=request.name
            )
        )
