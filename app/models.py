from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SAEnum
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
    name = Column(String)
    region = Column(SAEnum(Region), default=Region.UNSPECIFIED)
    kyc_status = Column(SAEnum(KycStatus), default=KycStatus.PENDING)
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
