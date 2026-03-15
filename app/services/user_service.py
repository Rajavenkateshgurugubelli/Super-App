import logging
import uuid
import json
import grpc
from sqlalchemy import func
from app import user_pb2, user_pb2_grpc
from app.database import SessionLocal
from app.models import User, Wallet, Transaction
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

            # Generate W3C DID
            user_uuid = str(uuid.uuid4())
            did_string = f"did:superapp:{user_uuid}"
            did_doc = {
                "@context": ["https://www.w3.org/ns/did/v1"],
                "id": did_string,
                "verificationMethod": [{
                    "id": f"{did_string}#keys-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": did_string,
                    # We would typically store the public key derived from user credentials here
                    "publicKeyMultibase": "placeholder"
                }],
                "authentication": [f"{did_string}#keys-1"]
            }

            # Create User model
            new_user = User(
                user_id=user_uuid, 
                email=request.email,
                name=request.name,
                region=models.Region(request.region), # Cast int to Enum
                password_hash=hashed_password,
                kyc_status=models.KycStatus.PENDING, 
                phone_number=request.phone_number,
                did=did_string,
                did_document=json.dumps(did_doc)
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

            token = create_access_token({"sub": user.email, "user_id": user.user_id, "region": user.region.value})
            
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

    def GetStats(self, request, context):
        self._logger.info("Retrieving regional statistics")
        session = SessionLocal()
        try:
            total_users = session.query(User).count()
            total_wallets = session.query(Wallet).count()
            total_transactions = session.query(Transaction).count()
            total_volume = session.query(func.sum(Transaction.amount)).scalar() or 0.0
            
            return user_pb2.GetStatsResponse(
                total_users=total_users,
                total_wallets=total_wallets,
                total_transactions=total_transactions,
                total_volume=total_volume
            )
        finally:
            session.close()

    # WebAuthn gRPC Handlers
    def WebAuthnRegisterBegin(self, request, context):
        from app.services.webauthn_service import begin_registration
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.user_id == request.user_id).first()
            if not user:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return user_pb2.WebAuthnOptionsResponse()
            options = begin_registration(user_id=user.user_id, user_name=user.email, user_display_name=user.name)
            return user_pb2.WebAuthnOptionsResponse(options_json=json.dumps(options))
        finally:
            session.close()

    def WebAuthnRegisterComplete(self, request, context):
        from app.services.webauthn_service import complete_registration
        try:
            cred = complete_registration(
                user_id=request.user_id,
                credential_json=json.loads(request.credential_json),
                label=request.label
            )
            return user_pb2.WebAuthnRegisterCompleteResponse(
                success=True,
                credential_id=cred.credential_id,
                label=cred.label
            )
        except Exception as e:
            return user_pb2.WebAuthnRegisterCompleteResponse(success=False)

    def WebAuthnLoginBegin(self, request, context):
        from app.services.webauthn_service import begin_authentication
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.email == request.email).first()
            user_id = user.user_id if user else None
            options = begin_authentication(user_id=user_id)
            return user_pb2.WebAuthnOptionsResponse(options_json=json.dumps(options))
        finally:
            session.close()

    def WebAuthnLoginComplete(self, request, context):
        from app.services.webauthn_service import complete_authentication
        session = SessionLocal()
        try:
            user_id = complete_authentication(assertion_json=json.loads(request.assertion_json))
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                 context.set_code(grpc.StatusCode.NOT_FOUND)
                 return user_pb2.WebAuthnLoginCompleteResponse()
                 
            token = create_access_token({"sub": user.email, "user_id": user.user_id, "region": user.region.value})
            return user_pb2.WebAuthnLoginCompleteResponse(
                token=token,
                user=self._map_user_to_proto(user)
            )
        except Exception:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return user_pb2.WebAuthnLoginCompleteResponse()
        finally:
            session.close()

    def ListUsers(self, request, context):
        self._logger.info(f"Listing users with limit={request.limit}, offset={request.offset}")
        session = SessionLocal()
        try:
            users = session.query(User).offset(request.offset).limit(request.limit).all()
            total = session.query(User).count()
            return user_pb2.ListUsersResponse(
                users=[self._map_user_to_proto(u) for u in users],
                total=total
            )
        finally:
            session.close()

    def _map_user_to_proto(self, user_model):
        return user_pb2.User(
            user_id=user_model.user_id,
            email=user_model.email,
            name=user_model.name,
            region=user_model.region.value,
            kyc_status=user_model.kyc_status.value,
            phone_number=user_model.phone_number or "",
            is_admin=bool(user_model.is_admin)
        )
