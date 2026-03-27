import logging
import uuid
import grpc
from app import kyc_pb2, kyc_pb2_grpc
from app.database import SessionLocal
from app.models import UserPII, KycStatus, Region
from app import models

class KycService(kyc_pb2_grpc.KycServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def InitiateKyc(self, request, context):
        self._logger.info(f"Initiating KYC for user: {request.user_id} in region: {request.region}")
        session = SessionLocal()
        try:
            # Look up PII in the local shard (UserPII is geo-fenced)
            pii = session.query(UserPII).filter(UserPII.user_id == request.user_id).first()
            if not pii:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("User PII not found in this region")
                return kyc_pb2.InitiateKycResponse()

            # Logic for regional verification simulation
            # US: SSN verification simulation
            # EU: eIDAS simulation
            # IN: Aadhaar simulation (offline)
            
            status = KycStatus.PENDING
            message = "KYC initiated. Documents submitted for processing."

            # Demo-grade auto-approval logic for valid-looking IDs
            if len(request.document_id) >= 8:
                if request.document_type in ["Passport", "SSN", "Aadhaar", "National ID"]:
                    status = KycStatus.VERIFIED
                    message = "Automated verification successful based on document pattern."
                else:
                    status = KycStatus.PENDING
                    message = "Unsupported document type for auto-approval. Manual review required."
            else:
                status = KycStatus.FAILED
                message = "Invalid document ID length."

            pii.kyc_status = status
            session.commit()

            return kyc_pb2.InitiateKycResponse(
                kyc_id=str(uuid.uuid4()),
                status=status.value,
                message=message
            )
        except Exception as e:
            self._logger.error(f"Error initiating KYC: {e}")
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return kyc_pb2.InitiateKycResponse()
        finally:
            session.close()

    def GetKycStatus(self, request, context):
        session = SessionLocal()
        try:
            pii = session.query(UserPII).filter(UserPII.user_id == request.user_id).first()
            if not pii:
                return kyc_pb2.GetKycStatusResponse(
                    status=KycStatus.KYC_STATUS_UNSPECIFIED.value,
                    message="User PII not found"
                )
            
            return kyc_pb2.GetKycStatusResponse(
                status=pii.kyc_status.value,
                message=f"Current status: {pii.kyc_status.name}"
            )
        finally:
            session.close()

    def UpdateKycStatus(self, request, context):
        # Admin action to update status manually
        session = SessionLocal()
        try:
            pii = session.query(UserPII).filter(UserPII.user_id == request.user_id).first()
            if not pii:
                return kyc_pb2.UpdateKycStatusResponse(success=False)
            
            pii.kyc_status = KycStatus(request.status)
            session.commit()
            return kyc_pb2.UpdateKycStatusResponse(success=True)
        finally:
            session.close()
