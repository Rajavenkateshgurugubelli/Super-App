from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

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

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True) # Nullable for existing users migration
    is_admin = Column(Boolean, default=False, nullable=True)  # Phase 3: Admin role
    name = Column(String)
    region = Column(SAEnum(Region), default=Region.UNSPECIFIED)
    kyc_status = Column(SAEnum(KycStatus), default=KycStatus.PENDING)
    phone_number = Column(String, unique=True, index=True)
    # Encrypted PII field (e.g. government ID)
    encrypted_pii = Column(String, nullable=True)

    wallets = relationship("Wallet", back_populates="owner")

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

class ConversionRate(Base):
    __tablename__ = "conversion_rates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"))
    from_currency = Column(String)
    to_currency = Column(String)
    rate = Column(Float)
    timestamp = Column(Float)
    
    transaction = relationship("Transaction", back_populates="conversion")
