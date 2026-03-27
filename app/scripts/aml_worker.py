import json
import os
import sys
import time
from kafka import KafkaConsumer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.getcwd())
from app.models import Base, Transaction, SuspiciousTransaction, User, Wallet, AuditLog
import uuid

# Configuration — In production, these would be regional and fetched from Vault
KAFKA_BROKER = os.environ.get("KAFKA_BROKER_URL", "localhost:9092")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./superapp.db")

# Thresholds (Demo specific)
THRESHOLD_USD = 10000.0
# Velocity check: more than 5 transactions in 1 minute
VELOCITY_WINDOW_SEC = 60
VELOCITY_THRESHOLD = 5

# Local state for velocity tracking (In production, use Redis sliding window)
USER_TRANSACTION_COUNT = {} # {user_id: [timestamp1, timestamp2, ...]}

def generate_automated_sar(session, user_id, txn_id, flags):
    """
    Generates a FinCEN/RBI compatible SAR JSON (Draft).
    In a real system, this is a legal requirement for compliance.
    """
    user = session.query(User).filter(User.user_id == user_id).first()
    
    sar_report = {
        "report_id": f"SAR-{uuid.uuid4()}",
        "filing_date": time.strftime("%Y-%m-%d"),
        "subject": {
            "user_id": user_id,
            "did": user.did if user else None,
            "hash": user.email_hash if user else None
        },
        "transaction": {
            "txn_id": txn_id,
        },
        "suspicion_indicators": [f["reason"] for f in flags],
        "jurisdiction": user.primary_region.name if user else "GLOBAL"
    }
    
    audit_log = AuditLog(
        entity_type="SAR",
        entity_id=sar_report["report_id"],
        payload=json.dumps(sar_report),
        severity="CRITICAL",
        region=user.primary_region if user else None
    )
    session.add(audit_log)
    print(f"[RECOMP] Automated SAR Generated: {sar_report['report_id']}")

def analyze_transaction(event):
    txn_id = event["transaction_id"]
    from_wallet = event["from_wallet"]
    amount = event["amount"]
    currency = event["currency"]
    
    print(f"--- AML Analysis: Transaction {txn_id} ---")
    print(f"Amount: {amount} {currency}")
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get User ID from Wallet
        wallet = session.query(Wallet).filter(Wallet.wallet_id == from_wallet).first()
        if not wallet:
            print(f"[WARN] Source wallet {from_wallet} not found in DB.")
            return
        user_id = wallet.user_id
        
        flags = []
        
        # 1. Volume Check (Hard Threshold)
        # In a real system, we'd use a real-time FX price to normalize to USD
        if amount >= THRESHOLD_USD:
            flags.append({
                "reason": f"High value transaction: {amount} {currency} exceeds threshold ${THRESHOLD_USD}",
                "severity": "HIGH"
            })
            
        # 2. Velocity Check (Rapid-fire transactions)
        now = time.time()
        if user_id not in USER_TRANSACTION_COUNT:
            USER_TRANSACTION_COUNT[user_id] = []
        
        # Clean up old timestamps (sliding window)
        USER_TRANSACTION_COUNT[user_id] = [t for t in USER_TRANSACTION_COUNT[user_id] if now - t < VELOCITY_WINDOW_SEC]
        USER_TRANSACTION_COUNT[user_id].append(now)
        
        if len(USER_TRANSACTION_COUNT[user_id]) >= VELOCITY_THRESHOLD:
            flags.append({
                "reason": f"High velocity detected: {len(USER_TRANSACTION_COUNT[user_id])} transactions in {VELOCITY_WINDOW_SEC}s window.",
                "severity": "MEDIUM"
            })
            
        # 3. Destination Risk (Internal lookup vs External)
        # Future: Check if recipient is on a sanctions list (OFAC, etc.)
        
        # Commit Flags to DB
        if flags:
            severity_set = [f["severity"] for f in flags]
            for flag in flags:
                print(f"[FLAGGED] {flag['severity']}: {flag['reason']}")
                suspicious = SuspiciousTransaction(
                    transaction_id=txn_id,
                    user_id=user_id,
                    reason=flag["reason"],
                    severity=flag["severity"],
                    status="PENDING_REVIEW"
                )
                session.add(suspicious)
            
            # If any flag is HIGH, generate an automated SAR for audit
            if "HIGH" in severity_set:
                generate_automated_sar(session, user_id, txn_id, flags)

            session.commit()
            print(f"Recorded {len(flags)} AML flags for investigation.")
        else:
            print("[INFO] No suspicious patterns detected.")
            
    except Exception as e:
        print(f"[ERROR] AML analysis failed: {e}")
        session.rollback()
    finally:
        session.close()

def main():
    print(f"Super App Anti-Money Laundering (AML) Worker starting...")
    print(f"Connecting to Kafka at {KAFKA_BROKER}...")
    
    # Connection logic with retries
    consumer = None
    for i in range(10):
        try:
            consumer = KafkaConsumer(
                "transactions",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='aml-processing-group'
            )
            print("Successfully connected to Kafka.")
            break
        except Exception as e:
            print(f"Kafka connection attempt {i+1} failed. Retrying in 5s...")
            time.sleep(5)
            
    if not consumer:
        print("Could not connect to Kafka. Exiting Worker.")
        return
    
    print("Listening for financial events...")
    for message in consumer:
        try:
            event = message.value
            # We process only TransactionCompleted events emitted by WalletService
            if event.get("event_type") == "TransactionCompleted":
                payload = event.get("payload")
                if payload:
                    analyze_transaction(payload)
        except Exception as e:
            print(f"Error processing Kafka message: {e}")

if __name__ == "__main__":
    main()
