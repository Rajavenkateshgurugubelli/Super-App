import logging
import time
import json
import uuid
from sqlalchemy.orm import Session
from app.models import HealthRecord, Prescription, ConsultationSession, User, Region
from typing import List, Optional

logger = logging.getLogger(__name__)

class HealthService:
    """
    Handles Module 6 (Health & Telemedicine) operations.
    Compliant with RFC-006 PHI isolation and FHIR standards.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_medical_record(
        self, 
        user_id: str, 
        encrypted_data: str, 
        record_type: str, 
        region: Region,
        provider_id: Optional[str] = None
    ):
        """
        Stores an encrypted PHI record. 
        Encryption is performed at the app-level (Zero-Knowledge for DB).
        """
        new_record = HealthRecord(
            id=f"rec-{uuid.uuid4()}",
            user_id=user_id,
            encrypted_data=encrypted_data,
            record_type=record_type,
            provider_id=provider_id,
            region=region
        )
        self.db.add(new_record)
        self.db.commit()
        self.db.refresh(new_record)
        
        logger.info(f"Health record {new_record.id} created for user {user_id} in {region}")
        return new_record

    def issue_prescription(
        self, 
        patient_id: str, 
        doctor_id: str, 
        medication_json: str, 
        region: Region,
        expiry_days: int = 30
    ):
        """
        Issues a FHIR-compliant e-prescription.
        """
        # Verification logic for doctor_id should be in a separate IAM check
        
        expires_at = time.time() + (expiry_days * 86400)
        
        new_prescription = Prescription(
            id=f"rx-{uuid.uuid4()}",
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication_json=medication_json,
            expires_at=expires_at,
            region=region
        )
        self.db.add(new_prescription)
        self.db.commit()
        self.db.refresh(new_prescription)
        
        return new_prescription

    def schedule_consultation(
        self, 
        patient_id: str, 
        doctor_id: str, 
        scheduled_start: float, 
        region: Region
    ):
        """
        Schedules a WebRTC video consultation.
        """
        room_id = f"room-{uuid.uuid4()}"
        
        new_session = ConsultationSession(
            id=f"sess-{uuid.uuid4()}",
            patient_id=patient_id,
            doctor_id=doctor_id,
            room_id=room_id,
            scheduled_start=scheduled_start,
            region=region
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        
        return new_session

    def get_patient_history(self, user_id: str) -> List[HealthRecord]:
        """
        Retrieves all medical records for a user.
        """
        return self.db.query(HealthRecord).filter(
            HealthRecord.user_id == user_id
        ).order_by(HealthRecord.created_at.desc()).all()

    def update_session_status(self, session_id: str, status: str):
        """
        Updates the status of a live consultation (e.g., LIVE, COMPLETED).
        """
        session = self.db.query(ConsultationSession).filter(
            ConsultationSession.id == session_id
        ).first()
        
        if session:
            session.status = status
            if status == "COMPLETED":
                session.actual_end = time.time()
            self.db.commit()
            return session
        return None
