# RFC-002: Universal Payment and Wallet Engine

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Last Modified:** 2026-03-27  
> **Target Audience:** Engineering Teams, FinTech Compliance, Payment Operations  
> **Depends On:** RFC-001 (IAM & Base Architecture)

---

## 1. Abstract

This RFC defines the architecture for the Universal Payment and Wallet Engine — the financial backbone of the Global Genesis Super App. It specifies how a single payment orchestrator dynamically routes transactions across UPI (India), SEPA/Open Banking (EU), and ACH/Stripe (US), backed by an immutable double-entry ledger, PCI-DSS compliant tokenization, and a fraud detection streaming pipeline.

---

## 2. Existing System Baseline

The current Super App already implements:

| Component | Current State | RFC Target |
|---|---|---|
| Wallet | `app/services/wallet_service.py` — gRPC service with multi-currency (USD, INR, EUR) | Full ledger-backed wallet with settlement accounts |
| Transactions | `Transaction` model with status tracking | Immutable double-entry ledger with audit trail |
| FX | Static rate matrix, `ConversionRate` model | Real-time FX feed with spread management |
| Fraud | None | Real-time Kafka streaming fraud detection |
| Payment Rails | Internal transfers only | UPI, SEPA, ACH/Stripe integration |
| DLQ | Kafka DLQ with 3x retry, JSONL store | Extended with reconciliation automation |
| Redis | Write-through cache, Redlock for double-spend | Settlement batching, rate limiting per user |

---

## 3. Payment Orchestrator

### 3.1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                      PAYMENT ORCHESTRATOR                            │
│                                                                      │
│  ┌───────────────────┐                                               │
│  │ Transaction       │    ┌──────────────────────────────────┐       │
│  │ Ingress           │───►│ Region Resolver                  │       │
│  │ (Gateway REST)    │    │ • JWT region claim               │       │
│  └───────────────────┘    │ • Sender/Receiver region lookup  │       │
│                           │ • Currency + corridor detection  │       │
│                           └──────────────┬───────────────────┘       │
│                                          │                           │
│                  ┌───────────────────────┼───────────────────────┐   │
│                  │                       │                       │   │
│          ┌───────▼───────┐       ┌───────▼───────┐       ┌──────▼──┐│
│          │ INDIA         │       │ EUROPE        │       │ US      ││
│          │ Payment Rail  │       │ Payment Rail  │       │ Payment ││
│          │               │       │               │       │ Rail    ││
│          │ ┌───────────┐ │       │ ┌───────────┐ │       │┌───────┐││
│          │ │ UPI (NPCI) │ │       │ │SEPA Credit│ │       ││Stripe │││
│          │ │ Collect/Pay│ │       │ │Transfer   │ │       ││ACH    │││
│          │ └───────────┘ │       │ └───────────┘ │       ││Cards  │││
│          │ ┌───────────┐ │       │ ┌───────────┐ │       │└───────┘││
│          │ │ IMPS       │ │       │ │Open Banking│ │       │┌───────┐││
│          │ │ NEFT/RTGS  │ │       │ │(PSD2 APIs)│ │       ││Plaid  │││
│          │ └───────────┘ │       │ └───────────┘ │       ││(ACH)  │││
│          │ ┌───────────┐ │       │ ┌───────────┐ │       │└───────┘││
│          │ │ RuPay Cards│ │       │ │SWIFT (int.)│ │       │┌───────┐││
│          │ └───────────┘ │       │ └───────────┘ │       ││Wire   │││
│          └───────────────┘       └───────────────┘       │└───────┘││
│                                                          └─────────┘│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                  SAGA COORDINATOR                            │    │
│  │  Orchestrates multi-step payment flow with compensations     │    │
│  │  Existing: app/services/saga_coordinator.py                  │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2. Payment Rail Router

```python
# app/services/payment/rail_router.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class PaymentCorridor(Enum):
    """Defines the payment corridor based on sender/receiver regions."""
    DOMESTIC_US = "US→US"
    DOMESTIC_EU = "EU→EU"
    DOMESTIC_IN = "IN→IN"
    CROSS_BORDER_US_EU = "US↔EU"
    CROSS_BORDER_US_IN = "US↔IN"
    CROSS_BORDER_EU_IN = "EU↔IN"

class PaymentMethod(Enum):
    UPI_COLLECT = "upi_collect"         # India: Pull payment (payee requests)
    UPI_PAY = "upi_pay"                 # India: Push payment (payer initiates)
    IMPS = "imps"                       # India: Immediate real-time (< ₹5L)
    NEFT = "neft"                       # India: Batch settlement (hourly)
    RTGS = "rtgs"                       # India: High-value real-time (> ₹2L)
    SEPA_CREDIT = "sepa_credit"         # EU: Credit transfer (1 business day)
    SEPA_INSTANT = "sepa_instant"       # EU: Instant credit (< 10 seconds)
    OPEN_BANKING_PIS = "ob_pis"         # EU: PSD2 Payment Initiation Service
    ACH_DEBIT = "ach_debit"             # US: ACH pull (2-3 business days)
    ACH_CREDIT = "ach_credit"           # US: ACH push (1-2 business days)
    STRIPE_CARD = "stripe_card"         # US/Global: Card payment (instant)
    WIRE_TRANSFER = "wire"              # Cross-border: SWIFT/Wire
    WALLET_INTERNAL = "wallet_internal" # Internal: In-app wallet transfer

@dataclass
class RoutingDecision:
    primary_rail: PaymentMethod
    fallback_rail: Optional[PaymentMethod]
    estimated_settlement_time: str
    fee_basis_points: int  # Fee in basis points (100 = 1%)
    requires_additional_kyc: bool
    compliance_checks: list[str]

class PaymentRailRouter:
    """
    Determines the optimal payment rail based on:
    1. Sender region
    2. Receiver region
    3. Amount (some rails have min/max)
    4. Currency
    5. Speed requirement (instant vs. batch)
    6. Cost optimization
    """

    # Rail selection matrix
    ROUTING_TABLE = {
        # Domestic India
        (Region.INDIA, Region.INDIA, "instant"): RoutingDecision(
            primary_rail=PaymentMethod.UPI_PAY,
            fallback_rail=PaymentMethod.IMPS,
            estimated_settlement_time="< 30 seconds",
            fee_basis_points=0,  # UPI is zero-cost
            requires_additional_kyc=False,
            compliance_checks=["rbi_transaction_limit"]
        ),
        (Region.INDIA, Region.INDIA, "batch"): RoutingDecision(
            primary_rail=PaymentMethod.NEFT,
            fallback_rail=PaymentMethod.IMPS,
            estimated_settlement_time="< 2 hours",
            fee_basis_points=0,
            requires_additional_kyc=False,
            compliance_checks=["rbi_transaction_limit"]
        ),
        # Domestic EU
        (Region.EU, Region.EU, "instant"): RoutingDecision(
            primary_rail=PaymentMethod.SEPA_INSTANT,
            fallback_rail=PaymentMethod.SEPA_CREDIT,
            estimated_settlement_time="< 10 seconds",
            fee_basis_points=20,  # ~0.2%
            requires_additional_kyc=False,
            compliance_checks=["psd2_sca", "eu_sanctions_screening"]
        ),
        (Region.EU, Region.EU, "batch"): RoutingDecision(
            primary_rail=PaymentMethod.SEPA_CREDIT,
            fallback_rail=None,
            estimated_settlement_time="1 business day",
            fee_basis_points=10,
            requires_additional_kyc=False,
            compliance_checks=["psd2_sca", "eu_sanctions_screening"]
        ),
        # Domestic US
        (Region.US, Region.US, "instant"): RoutingDecision(
            primary_rail=PaymentMethod.STRIPE_CARD,
            fallback_rail=PaymentMethod.ACH_CREDIT,
            estimated_settlement_time="< 5 seconds (card)",
            fee_basis_points=290,  # Stripe 2.9% + $0.30
            requires_additional_kyc=False,
            compliance_checks=["ofac_screening", "state_money_transmitter"]
        ),
        (Region.US, Region.US, "batch"): RoutingDecision(
            primary_rail=PaymentMethod.ACH_CREDIT,
            fallback_rail=None,
            estimated_settlement_time="1-2 business days",
            fee_basis_points=25,
            requires_additional_kyc=False,
            compliance_checks=["ofac_screening"]
        ),
        # Cross-border: US ↔ EU
        (Region.US, Region.EU, "instant"): RoutingDecision(
            primary_rail=PaymentMethod.STRIPE_CARD,
            fallback_rail=PaymentMethod.WIRE_TRANSFER,
            estimated_settlement_time="< 5 seconds (card), 1-2 days (wire)",
            fee_basis_points=350,
            requires_additional_kyc=True,
            compliance_checks=["ofac_screening", "eu_sanctions_screening", "fx_markup_disclosure"]
        ),
        # Cross-border: US ↔ India
        (Region.US, Region.INDIA, "instant"): RoutingDecision(
            primary_rail=PaymentMethod.WIRE_TRANSFER,
            fallback_rail=None,
            estimated_settlement_time="1-3 business days",
            fee_basis_points=400,
            requires_additional_kyc=True,
            compliance_checks=["ofac_screening", "rbi_lrs_limit", "fema_compliance", "purpose_code"]
        ),
        # Cross-border: EU ↔ India
        (Region.EU, Region.INDIA, "instant"): RoutingDecision(
            primary_rail=PaymentMethod.WIRE_TRANSFER,
            fallback_rail=None,
            estimated_settlement_time="1-3 business days",
            fee_basis_points=380,
            requires_additional_kyc=True,
            compliance_checks=["eu_sanctions_screening", "rbi_lrs_limit", "fema_compliance", "purpose_code"]
        ),
    }

    async def route(
        self,
        sender_region: Region,
        receiver_region: Region,
        amount: Decimal,
        currency: str,
        speed: str = "instant"
    ) -> RoutingDecision:
        key = (sender_region, receiver_region, speed)
        decision = self.ROUTING_TABLE.get(key)

        if decision is None:
            # Reverse corridor lookup
            key_reverse = (receiver_region, sender_region, speed)
            decision = self.ROUTING_TABLE.get(key_reverse)

        if decision is None:
            raise UnsupportedCorridorError(
                f"No payment rail for {sender_region.name} → {receiver_region.name}"
            )

        # Amount-based overrides
        if sender_region == Region.INDIA and amount > Decimal("200000"):
            decision = RoutingDecision(
                primary_rail=PaymentMethod.RTGS,
                fallback_rail=PaymentMethod.NEFT,
                estimated_settlement_time="< 30 minutes",
                fee_basis_points=0,
                requires_additional_kyc=False,
                compliance_checks=["rbi_transaction_limit", "rbi_high_value_reporting"]
            )

        return decision
```

### 3.3. UPI Integration Specifics (India)

```
┌────────────┐     ┌───────────────┐     ┌─────────────┐     ┌──────────┐
│ Super App  │     │ PSP (Payment  │     │ NPCI UPI    │     │ Receiver │
│ (Payer)    │     │ Service       │     │ Switch      │     │ Bank     │
│            │     │ Provider)     │     │             │     │          │
└─────┬──────┘     └──────┬────────┘     └──────┬──────┘     └────┬─────┘
      │                   │                     │                  │
      │ Initiate UPI Pay  │                     │                  │
      │ (VPA: user@super) │                     │                  │
      │──────────────────►│                     │                  │
      │                   │                     │                  │
      │                   │ Collect Request      │                  │
      │                   │────────────────────►│                  │
      │                   │                     │                  │
      │                   │                     │ Debit Request    │
      │                   │                     │─────────────────►│
      │                   │                     │                  │
      │                   │                     │ Debit Response   │
      │                   │                     │◄─────────────────│
      │                   │                     │                  │
      │                   │ Collect Response     │                  │
      │                   │◄────────────────────│                  │
      │                   │                     │                  │
      │ UPI Callback      │                     │                  │
      │ (status: SUCCESS) │                     │                  │
      │◄──────────────────│                     │                  │
      │                   │                     │                  │
      │ Kafka Event:      │                     │                  │
      │ payment.upi.completed                   │                  │
```

**UPI Configuration:**

```python
UPI_CONFIG = {
    "psp_partner": "razorpay",  # or "paytm", "phonepe"
    "vpa_handle": "@superapp",
    "transaction_limits": {
        "per_transaction": Decimal("100000"),   # ₹1 Lakh per txn
        "daily_limit": Decimal("500000"),       # ₹5 Lakh per day
    },
    "callback_url": "https://api.superapp.global/webhooks/upi",
    "mandate_support": True,  # UPI AutoPay for recurring
    "settlement_cycle": "T+0",  # Same-day settlement
}
```

### 3.4. SEPA / Open Banking Integration (EU)

```python
SEPA_CONFIG = {
    "psd2_provider": "plaid_eu",  # or "truelayer", "tink"
    "sepa_instant_enabled": True,
    "sepa_scheme": "SCT Inst",  # SEPA Credit Transfer Instant
    "bic": "SUPRGB2L",
    "iban_prefix": "GB",
    "transaction_limits": {
        "sepa_instant_max": Decimal("100000"),  # €100K per SCT Inst
        "sepa_credit_max": Decimal("999999999"),  # Effectively unlimited
    },
    "sca_requirements": {
        "threshold": Decimal("30"),  # SCA required above €30
        "exemptions": ["trusted_beneficiary", "recurring", "low_value"],
    },
    "callback_url": "https://api.superapp.global/webhooks/sepa",
}
```

---

## 4. Immutable Double-Entry Ledger

### 4.1. Design Philosophy

Every financial operation in the Super App is recorded as a **double-entry** in an **append-only** ledger. No row is ever updated or deleted. Corrections are made by posting compensating entries. This provides:

1. **Auditability:** Complete transaction history for any account at any point in time.
2. **Reconcilability:** Sum of all debits must equal sum of all credits (invariant).
3. **Regulatory Compliance:** Immutable audit trail for PCI-DSS, RBI, and EU payment directives.

### 4.2. Ledger Schema

```python
class LedgerEntry(Base):
    """
    Append-only double-entry ledger. NEVER UPDATE. NEVER DELETE.
    Each financial operation creates exactly 2 entries (debit + credit).
    """
    __tablename__ = "ledger_entries"
    __table_args__ = {"info": {"immutable": True}}

    entry_id = Column(String, primary_key=True, default=lambda: f"le_{uuid.uuid4().hex}")
    
    # Transaction grouping
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), 
                          nullable=False, index=True)
    sequence_num = Column(Integer, nullable=False)  # Order within transaction
    
    # Account identification
    account_id = Column(String, nullable=False, index=True)  # wallet_id or system account
    account_type = Column(SAEnum(AccountType), nullable=False)
    # AccountType: USER_WALLET, SETTLEMENT_US, SETTLEMENT_EU, SETTLEMENT_IN,
    #              FX_SPREAD_REVENUE, PLATFORM_FEE, SUSPENSE, RESERVE
    
    # Entry details
    entry_type = Column(SAEnum(EntryType), nullable=False)  # DEBIT or CREDIT
    amount = Column(Numeric(precision=18, scale=8), nullable=False)  # 8 decimal precision
    currency = Column(String(3), nullable=False)  # ISO 4217
    
    # Running balance (denormalized for performance)
    balance_after = Column(Numeric(precision=18, scale=8), nullable=False)
    
    # Metadata
    description = Column(String, nullable=False)
    created_at = Column(Float, nullable=False, default=lambda: time.time())
    created_by = Column(String, nullable=False)  # service name or user_id
    idempotency_key = Column(String, unique=True, nullable=False, index=True)
    
    # Compliance
    region = Column(SAEnum(Region), nullable=False)
    regulatory_reference = Column(String, nullable=True)  # UPI RRN, SEPA EndToEndId, etc.


class AccountBalance(Base):
    """
    Materialized view of current balance per account.
    Updated atomically with LedgerEntry via CockroachDB transaction.
    Serves as a cache — can always be recomputed from ledger_entries.
    """
    __tablename__ = "account_balances"

    account_id = Column(String, primary_key=True)
    currency = Column(String(3), primary_key=True)
    balance = Column(Numeric(precision=18, scale=8), nullable=False, default=0)
    last_entry_id = Column(String, nullable=False)
    last_updated_at = Column(Float, nullable=False)
    version = Column(Integer, nullable=False, default=0)  # Optimistic locking
```

### 4.3. Double-Entry Transaction Example

When User A (US, USD wallet) sends $100 to User B (India, INR wallet):

```
Transaction ID: txn_abc123
FX Rate: 1 USD = 83.50 INR
Platform Fee: 1.5% ($1.50)
FX Spread: 0.5% ($0.50)

Ledger Entries:
┌────────┬──────────────────────┬──────┬────────────┬──────────┬────────────┐
│ Seq    │ Account              │ Type │ Amount     │ Currency │ Description│
├────────┼──────────────────────┼──────┼────────────┼──────────┼────────────┤
│ 1      │ wallet_userA_usd     │ DR   │ 100.00     │ USD      │ Transfer out│
│ 2      │ settlement_us        │ CR   │ 100.00     │ USD      │ US settlement│
│ 3      │ settlement_us        │ DR   │ 98.00      │ USD      │ Net to convert│
│ 4      │ platform_fee_revenue │ CR   │ 1.50       │ USD      │ Platform fee│
│ 5      │ fx_spread_revenue    │ CR   │ 0.50       │ USD      │ FX spread  │
│ 6      │ settlement_in        │ DR   │ 8,183.00   │ INR      │ IN settlement│
│ 7      │ wallet_userB_inr     │ CR   │ 8,183.00   │ INR      │ Transfer in│
└────────┴──────────────────────┴──────┴────────────┴──────────┴────────────┘

Invariant check:
  USD Debits: 100.00 + 98.00 = 198.00
  USD Credits: 100.00 + 1.50 + 0.50 = 102.00 ... wait.

Actually, proper double-entry:
  Sum of ALL DEBITS = Sum of ALL CREDITS (per currency)
  
  USD: DR 100.00 (wallet_A) = CR 100.00 (settlement_us)  ✓
  USD: DR 98.00 (settlement) = CR 1.50 (fee) + CR 0.50 (spread) + CR 96.00 (fx_pool) ... 

Let me correct with the proper full flow:

Corrected Ledger Entries:
┌────┬─────────────────────────┬──────┬──────────┬──────┬─────────────────────────────┐
│ #  │ Account                 │ Type │ Amount   │ CCY  │ Description                  │
├────┼─────────────────────────┼──────┼──────────┼──────┼─────────────────────────────┤
│ 1  │ user_A_wallet_USD       │ DR   │ 100.00   │ USD  │ Debit sender wallet          │
│ 2  │ superapp_omnibus_USD    │ CR   │ 100.00   │ USD  │ Credit omnibus (holds funds) │
│ 3  │ superapp_omnibus_USD    │ DR   │ 1.50     │ USD  │ Extract platform fee         │
│ 4  │ superapp_fee_revenue    │ CR   │ 1.50     │ USD  │ Fee revenue recognized       │
│ 5  │ superapp_omnibus_USD    │ DR   │ 0.50     │ USD  │ Extract FX spread            │
│ 6  │ superapp_fx_revenue     │ CR   │ 0.50     │ USD  │ FX spread revenue            │
│ 7  │ superapp_omnibus_USD    │ DR   │ 98.00    │ USD  │ Send net to FX conversion    │
│ 8  │ superapp_fx_pool_USD    │ CR   │ 98.00    │ USD  │ FX pool receives USD         │
│ 9  │ superapp_fx_pool_INR    │ DR   │ 8,183.00 │ INR  │ FX pool releases INR         │
│ 10 │ superapp_omnibus_INR    │ CR   │ 8,183.00 │ INR  │ Omnibus receives INR         │
│ 11 │ superapp_omnibus_INR    │ DR   │ 8,183.00 │ INR  │ Release to receiver          │
│ 12 │ user_B_wallet_INR       │ CR   │ 8,183.00 │ INR  │ Credit receiver wallet       │
└────┴─────────────────────────┴──────┴──────────┴──────┴─────────────────────────────┘

Invariant: USD Debits = USD Credits = 200.00 ✓
Invariant: INR Debits = INR Credits = 16,366.00 ✓
```

### 4.4. Consistency Model

**Strong Consistency** is required for all financial writes:

```python
async def execute_transfer(self, transfer: TransferRequest) -> TransferResult:
    """
    Executes a financial transfer as an atomic database transaction.
    Uses CockroachDB SERIALIZABLE isolation (default).
    """
    async with self.db.begin() as txn:
        # 1. Acquire pessimistic lock on sender account balance
        sender_balance = await txn.execute(
            select(AccountBalance)
            .where(AccountBalance.account_id == transfer.sender_wallet_id)
            .where(AccountBalance.currency == transfer.currency)
            .with_for_update()  # SELECT ... FOR UPDATE (row-level lock)
        )

        if sender_balance.balance < transfer.amount:
            raise InsufficientFundsError()

        # 2. Create all ledger entries atomically
        entries = self._build_ledger_entries(transfer)
        for entry in entries:
            txn.add(entry)

        # 3. Update materialized balances with optimistic lock
        sender_balance.balance -= transfer.amount
        sender_balance.version += 1
        receiver_balance.balance += transfer.converted_amount
        receiver_balance.version += 1

        # 4. Emit domain event (within same transaction for outbox pattern)
        outbox_event = OutboxEvent(
            event_type="payment.transfer.completed",
            aggregate_id=transfer.transaction_id,
            payload=transfer.to_event_payload(),
        )
        txn.add(outbox_event)

        await txn.commit()
        # Outbox poller publishes to Kafka asynchronously
```

**Eventual Consistency** is acceptable for:
- Balance display on the dashboard (Redis cache, 60s TTL — existing)
- Analytics events (Kafka → ClickHouse pipeline — existing)
- FX rate updates (5-minute cache — existing)

---

## 5. PCI-DSS Compliance & Tokenization

### 5.1. Compliance Scope Definition

```
┌────────────────────────────────────────────────────────────────┐
│                    PCI-DSS SCOPE BOUNDARY                      │
│                                                                │
│  IN SCOPE (requiring PCI-DSS SAQ-D certification):             │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ • Card tokenization service (Stripe.js + server-side)│      │
│  │ • Payment gateway integration endpoints              │      │
│  │ • Webhook callback handlers for card events          │      │
│  │ • HSM-backed encryption key management               │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                │
│  OUT OF SCOPE (via tokenization — PAN never touches our infra):│
│  ┌──────────────────────────────────────────────────────┐      │
│  │ • Frontend clients (Stripe.js handles PAN capture)   │      │
│  │ • API Gateway (only sees tokens, never raw PAN)      │      │
│  │ • Core backend services                              │      │
│  │ • Database (stores Stripe tokens, not PAN)           │      │
│  │ • Kafka event streams                                │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 5.2. Tokenization Architecture

```python
class PaymentTokenStore(Base):
    """
    Stores tokenized payment method references.
    NO PAN, CVV, or sensitive card data is ever stored.
    """
    __tablename__ = "payment_tokens"

    token_id = Column(String, primary_key=True, default=lambda: f"ptk_{uuid.uuid4().hex}")
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    # Token reference (provider-specific)
    provider = Column(String, nullable=False)  # "stripe", "razorpay", "adyen"
    provider_token = Column(String, nullable=False)  # Stripe Payment Method ID
    provider_customer_id = Column(String, nullable=False)  # Stripe Customer ID
    
    # Non-sensitive card metadata (safe to store)
    card_last4 = Column(String(4), nullable=True)
    card_brand = Column(String, nullable=True)  # "visa", "mastercard", "rupay"
    card_expiry_month = Column(Integer, nullable=True)
    card_expiry_year = Column(Integer, nullable=True)
    card_country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    
    # Method type
    method_type = Column(String, nullable=False)  # "card", "bank_account", "upi_vpa"
    
    # Status
    is_default = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    status = Column(String, default="active")  # active, expired, revoked
    
    # Compliance
    region = Column(SAEnum(Region), nullable=False)
    created_at = Column(Float, default=lambda: time.time())
```

### 5.3. Fraud Detection Event Stream

```
┌──────────────────────────────────────────────────────────────────────┐
│                   FRAUD DETECTION PIPELINE                           │
│                                                                      │
│  Payment Event                                                       │
│  (Kafka: payment.initiated)                                          │
│       │                                                              │
│       ▼                                                              │
│  ┌────────────────────┐                                              │
│  │ STREAM PROCESSOR   │                                              │
│  │ (Kafka Streams /   │                                              │
│  │  Flink)            │                                              │
│  │                    │                                              │
│  │ Enrichment:        │                                              │
│  │ • User profile     │                                              │
│  │ • Device fingerprint│                                             │
│  │ • GeoIP            │                                              │
│  │ • Historical txns  │                                              │
│  └────────┬───────────┘                                              │
│           │                                                          │
│           ▼                                                          │
│  ┌────────────────────┐    ┌─────────────────────────────┐           │
│  │ RULE ENGINE        │    │ ML MODEL SERVICE            │           │
│  │                    │    │                             │           │
│  │ Static Rules:      │    │ • XGBoost anomaly detection │           │
│  │ • Velocity checks  │    │ • Features: amount, time,  │           │
│  │   (>5 txns/hour)  │    │   device, geo, network     │           │
│  │ • Amount thresholds│    │ • Inference latency: <50ms │           │
│  │   (>$10K single)  │    │ • Retrained weekly on       │           │
│  │ • Geo-impossible   │    │   labeled fraud data       │           │
│  │   (US→IN in 1 min)│    │                             │           │
│  │ • Blacklist check  │    │ Output: fraud_score (0-1)  │           │
│  └────────┬───────────┘    └──────────────┬──────────────┘           │
│           │                               │                          │
│           └───────────┬───────────────────┘                          │
│                       │                                              │
│                       ▼                                              │
│              ┌────────────────┐                                      │
│              │ DECISION ENGINE│                                      │
│              │                │                                      │
│              │ score < 0.3:   │──► APPROVE (auto)                    │
│              │ 0.3 ≤ s < 0.7:│──► REVIEW (manual queue)             │
│              │ score ≥ 0.7:   │──► BLOCK (auto) + alert              │
│              └────────────────┘                                      │
│                                                                      │
│  Blocked Event → Kafka: payment.fraud.blocked                        │
│  Approved Event → Kafka: payment.fraud.cleared                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. API Contracts

### 6.1. Payment Initiation — Request

```json
// POST /api/v2/payments/initiate
// Authorization: Bearer <access_token>
// Idempotency-Key: <client-generated-uuid>
// X-Device-Fingerprint: <encrypted-device-id>

{
  "from_wallet_id": "wlt_a1b2c3d4e5f6",
  "to": {
    "type": "wallet",               // "wallet" | "bank_account" | "upi_vpa"
    "wallet_id": "wlt_f6e5d4c3b2a1", // Required if type=wallet
    "upi_vpa": null,                 // Required if type=upi_vpa (e.g. "user@superapp")
    "bank_account": null             // Required if type=bank_account
  },
  "amount": "100.00",               // String to avoid floating point
  "currency": "USD",                // ISO 4217
  "speed": "instant",               // "instant" | "standard" | "economy"
  "purpose": "personal_transfer",   // Required for cross-border (RBI purpose code)
  "note": "Dinner last night",      // Optional, max 140 chars
  "metadata": {                     // Optional, client-defined
    "invoice_id": "INV-2026-001"
  }
}
```

**Response — 202 Accepted:**

```json
{
  "transaction_id": "txn_7890abcdef123456",
  "status": "PROCESSING",
  "payment_rail": "upi_pay",
  "estimated_completion": "2026-03-27T16:35:00Z",
  "fee": {
    "amount": "0.00",
    "currency": "INR",
    "breakdown": {
      "platform_fee": "0.00",
      "fx_spread": "0.00",
      "rail_fee": "0.00"
    }
  },
  "fx_rate": {
    "from": "USD",
    "to": "INR",
    "rate": "83.5000",
    "locked_until": "2026-03-27T16:40:00Z"
  },
  "recipient_receives": {
    "amount": "8350.00",
    "currency": "INR"
  },
  "links": {
    "self": "/api/v2/payments/txn_7890abcdef123456",
    "cancel": "/api/v2/payments/txn_7890abcdef123456/cancel"
  },
  "_idempotency": {
    "key": "client-uuid-here",
    "expires_at": "2026-03-28T16:34:00Z"
  }
}
```

### 6.2. Payment Webhook Callback

```json
// POST <merchant_webhook_url>
// X-Superapp-Signature: sha256=<HMAC-SHA256(payload, webhook_secret)>
// X-Superapp-Event-Type: payment.completed
// X-Superapp-Delivery-Id: <unique-delivery-uuid>
// X-Superapp-Timestamp: 1711541700

{
  "event_id": "evt_abc123def456",
  "event_type": "payment.completed",
  "created_at": "2026-03-27T16:35:00Z",
  "data": {
    "transaction_id": "txn_7890abcdef123456",
    "status": "COMPLETED",
    "payment_rail": "upi_pay",
    "amount": {
      "sent": {
        "amount": "100.00",
        "currency": "USD"
      },
      "received": {
        "amount": "8350.00",
        "currency": "INR"
      }
    },
    "fee_charged": {
      "amount": "0.00",
      "currency": "USD"
    },
    "fx_rate_applied": "83.5000",
    "sender": {
      "user_id": "usr_sender_id",
      "wallet_id": "wlt_a1b2c3d4e5f6",
      "region": "US"
    },
    "receiver": {
      "user_id": "usr_receiver_id",
      "wallet_id": "wlt_f6e5d4c3b2a1",
      "region": "INDIA"
    },
    "regulatory": {
      "purpose_code": "P0801",
      "rbi_reference": "RRN2026032700001",
      "sanctions_cleared": true,
      "aml_score": 0.12
    },
    "completed_at": "2026-03-27T16:35:00Z"
  },
  "metadata": {
    "invoice_id": "INV-2026-001"
  }
}
```

### 6.3. Transaction Status Query

```json
// GET /api/v2/payments/txn_7890abcdef123456
// Authorization: Bearer <access_token>

// Response — 200 OK:
{
  "transaction_id": "txn_7890abcdef123456",
  "status": "COMPLETED",
  "status_history": [
    {"status": "INITIATED", "at": "2026-03-27T16:34:00Z", "detail": "Payment initiated"},
    {"status": "FRAUD_CHECK_PASSED", "at": "2026-03-27T16:34:01Z", "detail": "Fraud score: 0.08"},
    {"status": "COMPLIANCE_CLEARED", "at": "2026-03-27T16:34:02Z", "detail": "OFAC + RBI cleared"},
    {"status": "RAIL_SUBMITTED", "at": "2026-03-27T16:34:03Z", "detail": "Submitted to UPI NPCI"},
    {"status": "COMPLETED", "at": "2026-03-27T16:35:00Z", "detail": "UPI RRN: 2026032700001"}
  ],
  "can_cancel": false,
  "can_refund": true,
  "refund_deadline": "2026-04-27T16:35:00Z",
  "ledger_entries": [
    {"entry_id": "le_001", "account": "user_wallet", "type": "DEBIT", "amount": "100.00", "currency": "USD"},
    {"entry_id": "le_012", "account": "user_wallet", "type": "CREDIT", "amount": "8350.00", "currency": "INR"}
  ]
}
```

---

## 7. Failure States and Recovery

### 7.1. Transaction State Machine

```
                    ┌──────────┐
                    │INITIATED │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌──────────┐
        │FRAUD     │ │EXPIRED │ │COMPLIANCE│
        │BLOCKED   │ │(timeout│ │REJECTED  │
        │          │ │ 5 min) │ │          │
        └──────────┘ └────────┘ └──────────┘
              │
              │ (if cleared)
              ▼
        ┌──────────────┐
        │COMPLIANCE    │
        │CHECK         │
        └──────┬───────┘
               │
        ┌──────┼──────────┐
        ▼      ▼          ▼
  ┌──────────┐ │   ┌──────────┐
  │COMPLIANCE│ │   │MANUAL    │
  │REJECTED  │ │   │REVIEW    │
  └──────────┘ │   └──────────┘
               ▼
        ┌──────────────┐
        │RAIL_SUBMITTED│
        └──────┬───────┘
               │
        ┌──────┼──────────────┐
        ▼      ▼              ▼
  ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │COMPLETED │ │RAIL      │ │RAIL_TIMEOUT  │
  │          │ │REJECTED  │ │(DLQ + retry) │
  └──────────┘ └──────────┘ └──────────────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │RECONCILIATION│
                             │_PENDING      │
                             └──────────────┘
```

### 7.2. Dead Letter Queue (DLQ) Architecture

Extending the existing DLQ system (`notification_service/dlq_consumer.py`):

```python
class PaymentDLQHandler:
    """
    Handles failed payment events that exhausted retry attempts.
    Existing DLQ: 3x retry → JSONL store.
    Extended: + automated reconciliation + alerting.
    """

    RETRY_POLICY = {
        "max_attempts": 5,
        "backoff_base_ms": 1000,
        "backoff_multiplier": 2,
        "backoff_max_ms": 60000,
        "retry_topic": "payments.retry",
        "dlq_topic": "payments.dlq",
    }

    async def handle_dlq_event(self, event: PaymentEvent):
        """Process events that have failed all retry attempts."""
        
        # 1. Persist to durable store
        await self.dlq_store.persist(event)
        
        # 2. Create reconciliation ticket
        recon_ticket = ReconciliationTicket(
            transaction_id=event.transaction_id,
            failure_reason=event.last_error,
            original_amount=event.amount,
            currency=event.currency,
            sender_region=event.sender_region,
            receiver_region=event.receiver_region,
            requires_manual_review=event.amount > Decimal("1000"),
            created_at=time.time(),
        )
        await self.recon_store.create(recon_ticket)
        
        # 3. If funds were debited but not credited → COMPENSATE
        if event.status == "RAIL_SUBMITTED" and event.debit_confirmed:
            await self.saga_coordinator.compensate(
                transaction_id=event.transaction_id,
                compensation_type="FULL_REVERSAL",
                reason="Rail timeout after DLQ exhaustion",
            )
        
        # 4. Alert on-call
        await self.alert_service.page(
            severity="P2" if event.amount > Decimal("10000") else "P3",
            title=f"Payment DLQ: {event.transaction_id}",
            detail=f"Failed after {self.RETRY_POLICY['max_attempts']} attempts: {event.last_error}",
        )
```

### 7.3. Automated Reconciliation

```python
class ReconciliationEngine:
    """
    Runs on a schedule (extending existing reconciliation_worker.py).
    Compares internal ledger state with external payment rail confirmations.
    """

    async def daily_reconciliation(self):
        """T+1 reconciliation for all payment rails."""
        
        yesterday = date.today() - timedelta(days=1)
        
        for region in [Region.US, Region.EU, Region.INDIA]:
            # 1. Fetch internal ledger entries for the date
            internal_entries = await self.ledger.get_entries_by_date(
                date=yesterday, region=region
            )
            
            # 2. Fetch external confirmations from payment rails
            external_confirmations = await self._fetch_external_confirmations(
                region=region, date=yesterday
            )
            
            # 3. Match and identify discrepancies
            matched, unmatched_internal, unmatched_external = self._reconcile(
                internal_entries, external_confirmations
            )
            
            # 4. Generate reconciliation report
            report = ReconciliationReport(
                date=yesterday,
                region=region,
                total_transactions=len(internal_entries),
                matched=len(matched),
                unmatched_internal=len(unmatched_internal),
                unmatched_external=len(unmatched_external),
                discrepancy_amount=sum(e.amount for e in unmatched_internal),
            )
            
            # 5. Store report (existing: compliance_reports/)
            await self.report_store.save(report, path=f"compliance_reports/{region.name}/")
            
            # 6. Alert if discrepancies exceed threshold
            if report.discrepancy_amount > Decimal("100"):
                await self.alert_service.page(
                    severity="P1",
                    title=f"Reconciliation Discrepancy: {region.name}",
                    detail=f"${report.discrepancy_amount} unmatched",
                )
```

---

## 8. Settlement Architecture

### 8.1. Settlement Accounts per Region

| Account | Currency | Purpose | Settlement Cycle |
|---|---|---|---|
| `settlement_us_usd` | USD | Holds US funds pending ACH/Stripe settlement | T+1 (ACH), T+0 (Stripe Instant Payouts) |
| `settlement_eu_eur` | EUR | Holds EU funds pending SEPA settlement | T+0 (SEPA Instant), T+1 (SEPA Credit) |
| `settlement_in_inr` | INR | Holds India funds pending UPI/NEFT settlement | T+0 (UPI), T+0 (IMPS), T+2h (NEFT) |
| `fx_pool_usd` | USD | FX conversion pool | Rebalanced daily |
| `fx_pool_eur` | EUR | FX conversion pool | Rebalanced daily |
| `fx_pool_inr` | INR | FX conversion pool | Rebalanced daily |
| `reserve_us` | USD | Regulatory reserve (state money transmitter) | Quarterly audit |
| `reserve_eu` | EUR | PSD2 safeguarding account | Monthly audit |
| `reserve_in` | INR | RBI escrow account | Monthly audit |

---

## 9. Non-Functional Requirements

| Metric | Target | Measurement |
|---|---|---|
| Payment Initiation Latency (P95) | < 500ms | OpenTelemetry (existing Jaeger) |
| Transaction Throughput | 10,000 TPS per region | Load test (`app/scripts/load_test.py`) |
| Ledger Write Latency (P99) | < 100ms | CockroachDB query metrics |
| Fraud Detection Latency (P95) | < 200ms | Kafka Streams lag monitoring |
| Availability | 99.99% (4 nines) | Uptime monitoring |
| Data Durability | 100% (zero loss) | Raft consensus + WAL |
| Reconciliation Accuracy | 99.999% | Daily reconciliation reports |

---

*End of RFC-002*
