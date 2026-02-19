import logging
import uuid
import grpc
from app import user_pb2, user_pb2_grpc
from app.database import SessionLocal
from app.models import User
from app import models
from app.security import get_password_hash, verify_password, create_access_token

class UserService(user_pb2_grpc.UserServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def CreateUser(self, request, context):
        self._logger.info(f"Creating user for email: {request.email}")
        session = SessionLocal()
        try:
            # Check if user exists
            existing_user = session.query(User).filter(User.email == request.email).first()
            if existing_user:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details('User with this email already exists')
                return user_pb2.CreateUserResponse()

            hashed_password = get_password_hash(request.password) if request.password else None

            # Create User model
            new_user = User(
                user_id=str(uuid.uuid4()), 
                email=request.email,
                name=request.name,
                region=models.Region(request.region), # Cast int to Enum
                password_hash=hashed_password,
                kyc_status=models.KycStatus.PENDING 
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            return user_pb2.CreateUserResponse(
                user=self._map_user_to_proto(new_user)
            )
        except Exception as e:
            self._logger.error(f"Error creating user: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def Login(self, request, context):
        self._logger.info(f"Login attempt for: {request.email}")
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.email == request.email).first()
            if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
                # Return empty token/user on failure (gRPC doesn't have 401, typically use context.abort)
                # For simplicity in this demo, return success=False logic or catch in gateway
                 context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                 context.set_details('Invalid credentials')
                 return user_pb2.LoginResponse()

            token = create_access_token({"sub": user.email, "user_id": user.user_id})
            
            return user_pb2.LoginResponse(
                token=token,
                user=self._map_user_to_proto(user)
            )
        finally:
            session.close()

    def GetUser(self, request, context):
        self._logger.info(f"Getting user: {request.user_id}")
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.user_id == request.user_id).first()
            if not user:
                 # return empty or raise error (for now empty default)
                 return user_pb2.GetUserResponse()
            
            return user_pb2.GetUserResponse(
                user=self._map_user_to_proto(user)
            )
        finally:
            session.close()

    def UpdateProfile(self, request, context):
        self._logger.info(f"Updating profile for: {request.user_id}")
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.user_id == request.user_id).first()
            if user:
                user.name = request.name
                session.commit()
                session.refresh(user)
                return user_pb2.UpdateProfileResponse(user=self._map_user_to_proto(user))
            return user_pb2.UpdateProfileResponse()
        finally:
            session.close()

    def _map_user_to_proto(self, user_model):
        return user_pb2.User(
            user_id=user_model.user_id,
            email=user_model.email,
            name=user_model.name,
            region=user_model.region.value,
            kyc_status=user_model.kyc_status.value
        )
