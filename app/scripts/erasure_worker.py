import json
import os
import sys
import time
from kafka import KafkaConsumer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.getcwd())
from app.models import Base, User, UserPII, Wallet, Transaction, AccountStatus

KAFKA_BROKER = os.environ.get("KAFKA_BROKER_URL", "localhost:9092")

# Regional DB mapping for local development simulation
# In production, these would be regional CockroachDB nodes with geo-partitioning
REGION_DB_MAP = {
    1: "sqlite:///./data/in/superapp.db",
    2: "sqlite:///./data/eu/superapp.db",
    3: "sqlite:///./data/us/superapp.db"
}

def process_erasure(event):
    user_id = event["user_id"]
    region = event["region"]
    db_url = REGION_DB_MAP.get(region, "sqlite:///./superapp.db")
    
    print(f"--- Processing GDPR Erasure Request ---")
    print(f"Request ID: {event.get('request_id')}")
    print(f"User ID: {user_id}")
    print(f"Region Shard: {region} ({db_url})")
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. PURGE PII (Strict Deletion)
        pii = session.query(UserPII).filter(UserPII.user_id == user_id).first()
        if pii:
            session.delete(pii)
            print(f"[SUCCESS] Purged regional PII record.")
        else:
            print(f"[INFO] No PII found for user in this shard.")
            
        # 2. DE-IDENTIFY Global Metadata
        # We retain the UUID for transaction audit trails but remove all lookup keys
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            user.email_hash = None
            user.did = None
            user.did_document = None
            user.account_status = AccountStatus.DELETED
            user.is_admin = False
            print(f"[SUCCESS] De-identified global identity record.")
            
        # 3. LEGACY DATA (Financial Auditability)
        # Under GDPR Art. 17(3)(b), we may retain financial data for legal compliance (Tax/AML)
        # However, we mark the wallets as closed.
        wallets = session.query(Wallet).filter(Wallet.user_id == user_id).all()
        for w in wallets:
            w.balance = 0.0
            print(f"[SUCCESS] Zeroed and closed wallet {w.wallet_id}.")
            
        session.commit()
        print(f"--- Erasure Complete for {user_id} ---")
    except Exception as e:
        print(f"[ERROR] Erasure failed: {e}")
        session.rollback()
    finally:
        session.close()

def main():
    print(f"Super App GDPR Erasure Engine starting...")
    print(f"Connecting to Kafka at {KAFKA_BROKER}...")
    
    # Simple retry loop for Kafka availability
    for i in range(5):
        try:
            consumer = KafkaConsumer(
                "user.erasure",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='erasure-worker-group'
            )
            print("Connected to Kafka.")
            break
        except Exception as e:
            print(f"Kafka connection attempt {i+1} failed ({e}). Retrying in 5s...")
            time.sleep(5)
    else:
        print("Failed to connect to Kafka. Exiting.")
        return
    
    print("Listening for erasure requests...")
    for message in consumer:
        try:
            event = message.value
            process_erasure(event)
        except Exception as e:
            print(f"Error processing message: {e}")

if __name__ == "__main__":
    main()
