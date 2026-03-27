from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
import time

from app.database import Base

# Enums matching Protobufs
class Region(enum.Enum):
    UNSPECIFIED = 0
    INDIA = 1
    EU = 2
    US = 3
    
    # Add a fallback or handling? 
    # SQLAlchemy Enum stores names by default unless values_callable is specified, 
    # but the error "'1' is not among the defined enum values" suggests it's trying to convert 
    # the integer 1 to an Enum member by name, which fails if the Enum is treating 1 as value?
    
    # Actually, the error `(builtins.LookupError) '1' is not among the defined enum values`
    # normally comes from SQLAlchemy trying to map a value back to the python Enum.
    # But here we are INSERTING. 
    # The users service is passing `region=request.region` (which is int 1 from proto).
    # Then `User(..., region=request.region, ...)`
    # The model defines `region = Column(SAEnum(Region), ...)`
    # If using SAEnum(Region), it expects a Region enum member, not an integer.
    # So `request.region` (int 1) is passed, SA tries to validate it against Region enum.
    # 1 is not a member object. Region(1) would be the member.
    
    # So the fix is in user_service.py to cast int to Enum.

class KycStatus(enum.Enum):
    UNSPECIFIED = 0
    PENDING = 1
    VERIFIED = 2
    FAILED = 3

class Currency(enum.Enum):
    UNSPECIFIED = 0
    USD = 1
    INR = 2
    EUR = 3

class AccountStatus(enum.Enum):
    ACTIVE = 0
    SUSPENDED = 1
    DELETED = 2
    PENDING_VERIFICATION = 3

class EntryType(enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class AccountType(enum.Enum):
    USER_WALLET = "USER_WALLET"
    OMNIBUS = "OMNIBUS"      # Holds funds in flight
    REVENUE = "REVENUE"      # Platform fees
    FX_POOL = "FX_POOL"      # Liquidity for conversion
    COLLECTION = "COLLECTION" # Regional rail endpoints
    SUSPENSE = "SUSPENSE"    # Error investigation

class User(Base):
    """
    Central user identity. Stores ONLY non-PII global metadata.
    PII is stored in region-local tables (UserPII).
    """
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    # SHA-256 hash of email for global lookups without storing PII
    email_hash = Column(String, unique=True, index=True, nullable=True) 
    created_at = Column(Float, default=lambda: time.time())
    primary_region = Column(SAEnum(Region), default=Region.UNSPECIFIED)
    account_status = Column(SAEnum(AccountStatus), default=AccountStatus.ACTIVE)
    is_admin = Column(Boolean, default=False, nullable=True)
    
    # Decentralized Identity (W3C DID)
    did = Column(String, unique=True, index=True, nullable=True)
    did_document = Column(String, nullable=True) 

    wallets = relationship("Wallet", back_populates="owner")
    pii = relationship("UserPII", back_populates="user", uselist=False)

class UserPII(Base):
    """
    Region-LOCAL PII storage. This table is geo-fenced.
    """
    __tablename__ = "user_pii"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    region = Column(SAEnum(Region), nullable=False)

    # These fields are considered PII and stay in region-local storage
    email = Column(String, index=True) # Encrypted
    name = Column(String) # Encrypted
    phone_number = Column(String, index=True) # Encrypted
    passport_number = Column(String) # Encrypted
    encrypted_dek = Column(String) # For envelope encryption
    password_hash = Column(String, nullable=True)
    
    # Encrypted PII field (e.g. government ID)
    encrypted_pii = Column(String, nullable=True)
    kyc_status = Column(SAEnum(KycStatus), default=KycStatus.PENDING)
    
    last_modified_at = Column(Float, default=lambda: time.time())

    user = relationship("User", back_populates="pii")

class Wallet(Base):
    __tablename__ = "wallets"

    wallet_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"))
    currency = Column(SAEnum(Currency), default=Currency.UNSPECIFIED)
    balance = Column(Float, default=0.0)

    owner = relationship("User", back_populates="wallets")
    outgoing_transactions = relationship("Transaction", foreign_keys="[Transaction.from_wallet_id]", back_populates="source_wallet")
    incoming_transactions = relationship("Transaction", foreign_keys="[Transaction.to_wallet_id]", back_populates="destination_wallet")

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    from_wallet_id = Column(String, ForeignKey("wallets.wallet_id"))
    to_wallet_id = Column(String, ForeignKey("wallets.wallet_id"))
    amount = Column(Float)
    status = Column(String, default="PENDING")
    timestamp = Column(Float) # Unix timestamp

    source_wallet = relationship("Wallet", foreign_keys=[from_wallet_id], back_populates="outgoing_transactions")
    destination_wallet = relationship("Wallet", foreign_keys=[to_wallet_id], back_populates="incoming_transactions")
    conversion = relationship("ConversionRate", uselist=False, back_populates="transaction")
    ledger_entries = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"))
    wallet_id = Column(String, nullable=True) # Backwards compatibility/specific mapping
    account_id = Column(String, nullable=False, index=True) # wallet_id or system_account_id
    account_type = Column(SAEnum(AccountType), default=AccountType.USER_WALLET)
    amount = Column(Float)
    entry_type = Column(SAEnum(EntryType))
    currency = Column(SAEnum(Currency))
    description = Column(String)
    timestamp = Column(Float, default=lambda: time.time())

    transaction = relationship("Transaction", back_populates="ledger_entries")
    wallet = relationship("Wallet", backref="ledger_entries")

class ConversionRate(Base):
    __tablename__ = "conversion_rates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"))
    from_currency = Column(String)
    to_currency = Column(String)
    rate = Column(Float)
    timestamp = Column(Float)
    
    transaction = relationship("Transaction", back_populates="conversion")

class PaymentTokenStore(Base):
    """
    PCI-DSS scope minimization: stores tokenized references to external payment methods.
    Does NOT store raw PAN, CVV, or sensitive track data.
    """
    __tablename__ = "payment_tokens"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    provider = Column(String) # "stripe", "razorpay", "plaid"
    provider_token = Column(String) # Vault ID
    last4 = Column(String(4))
    brand = Column(String)
    method_type = Column(String) # "CARD", "BANK"
    is_default = Column(Boolean, default=False)
    region = Column(SAEnum(Region))
    timestamp = Column(Float, default=lambda: time.time())

class SystemAccount(Base):
    """Tracking node for platform-level funds."""
    __tablename__ = "system_accounts"
    id = Column(String, primary_key=True) # e.g. "OMNIBUS_USD", "REVENUE_IN"
    account_type = Column(SAEnum(AccountType))
    currency = Column(SAEnum(Currency))
    balance = Column(Float, default=0.0)
    region = Column(SAEnum(Region))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String) # "SAR", "USER_DELETION", "CRYPTO_SHA_ROTATION"
    entity_id = Column(String)
    payload = Column(Text) # JSON blob
    severity = Column(String) # "INFO", "WARN", "CRITICAL"
    region = Column(SAEnum(Region))
    timestamp = Column(Float, default=lambda: time.time())

class SuspiciousTransaction(Base):
    """
    AML (Anti-Money Laundering) flagging for high-risk transactions.
    """
    __tablename__ = "suspicious_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), index=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    reason = Column(String)
    severity = Column(String) # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, default="PENDING_REVIEW") # PENDING_REVIEW, CLEARED, BLOCKED
    created_at = Column(Float, default=lambda: time.time())

    transaction = relationship("Transaction")
    user = relationship("User")

class WebAuthnCredential(Base):
    """Stores WebAuthn public-key credentials (passkeys) per user."""
    __tablename__ = "webauthn_credentials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    # Base64url-encoded credential ID assigned by the authenticator
    credential_id = Column(String, unique=True, nullable=False, index=True)
    # CBOR-encoded public key (stored as hex string for SQLite compat)
    public_key = Column(String, nullable=False)
    # Signature counter for replay-attack detection
    sign_count = Column(Integer, default=0, nullable=False)
    # Human-readable label (e.g. "Touch ID on MacBook")
    label = Column(String, nullable=True)
    created_at = Column(Float, default=lambda: time.time(), nullable=False)
    last_used_at = Column(Float, nullable=True)

    owner = relationship("User", backref="passkeys")

class SocialRelationship(Base):
    """
    Relational social graph for following and blocking users.
    Maps to RFC-005 Social Graph requirements.
    """
    __tablename__ = "social_relationships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = Column(String, ForeignKey("users.user_id"), index=True)
    followed_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # RELATIONSHIP_TYPE: FOLLOW, BLOCK, MUTE
    type = Column(String, default="FOLLOW") 
    created_at = Column(Float, default=lambda: __import__("time").time())
    
    # Data Residency for the relationship record
    region = Column(SAEnum(Region)) 

    follower = relationship("User", foreign_keys=[follower_id], backref="following")
    followed = relationship("User", foreign_keys=[followed_id], backref="followers")

class FeedActivity(Base):
    """
    Stores user-generated posts and activities.
    Maps to RFC-005 Activity Store.
    """
    __tablename__ = "feed_activities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # Content type: POST, REACTION, COMMENT, MILESTONE
    activity_type = Column(String, default="POST") 
    content = Column(Text) # JSON blob for flexible content (text, media refs)
    
    # Media handles (referenced in Section 4 of RFC-005)
    media_url = Column(String, nullable=True) 
    
    created_at = Column(Float, default=lambda: __import__("time").time())
    region = Column(SAEnum(Region))

    owner = relationship("User", backref="activities")

class ChatRoom(Base):
    """
    Messaging groups or 1:1 sessions.
    """
    __tablename__ = "chat_rooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True) # For group chats
    is_group = Column(Boolean, default=False)
    created_at = Column(Float, default=lambda: __import__("time").time())
    region = Column(SAEnum(Region))

class ChatMessage(Base):
    """
    Stores encrypted message blobs per RFC-005 Section 3.
    Uses Signal-protocol compatible E2EE envelopes.
    """
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, ForeignKey("chat_rooms.id"), index=True)
    sender_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # Encrypted blob (SignalProtocol Envelope)
    encrypted_payload = Column(Text) 
    
    # Ephemeral message metadata
    is_read = Column(Boolean, default=False)
    delivered_at = Column(Float, nullable=True)
    created_at = Column(Float, default=lambda: __import__("time").time())
    
    # Message integrity/hash
    signature = Column(String, nullable=True)

    room = relationship("ChatRoom", backref="messages")
    sender = relationship("User")

class HealthRecord(Base):
    """
    Stores Protected Health Information (PHI) per RFC-006.
    Logical isolation from general app data.
    """
    __tablename__ = "health_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # Encrypted PHI blob (Patient-Specific Key used for decryption)
    encrypted_data = Column(Text, nullable=False) 
    
    # Metadata for filtering (non-PHI)
    record_type = Column(String) # "LAB_RESULT", "VACCINATION", "CONSULTATION_NOTE"
    provider_id = Column(String, nullable=True) # Reference to a Doctor User ID
    
    created_at = Column(Float, default=lambda: time.time())
    region = Column(SAEnum(Region)) # Strict data residency (HIPAA/GDPR/DPDP)

    owner = relationship("User", backref="medical_history")

class Prescription(Base):
    """
    e-Prescription management per FHIR R4 standard.
    """
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("users.user_id"), index=True)
    doctor_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # FHIR-standardized content (Encrypted)
    medication_json = Column(Text, nullable=False) 
    status = Column(String, default="ACTIVE") # ACTIVE, COMPLETED, CANCELLED
    
    issued_at = Column(Float, default=lambda: time.time())
    expires_at = Column(Float, nullable=True)
    region = Column(SAEnum(Region))

class ConsultationSession(Base):
    """
    Tracks WebRTC consultations between doctors and patients.
    """
    __tablename__ = "consultation_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("users.user_id"), index=True)
    doctor_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # WebRTC Room ID / Signaling Channel
    room_id = Column(String, unique=True, index=True)
    status = Column(String, default="SCHEDULED") # SCHEDULED, LIVE, COMPLETED, CANCELLED
    
    scheduled_start = Column(Float)
    actual_end = Column(Float, nullable=True)
    created_at = Column(Float, default=lambda: time.time())
    region = Column(SAEnum(Region))

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
