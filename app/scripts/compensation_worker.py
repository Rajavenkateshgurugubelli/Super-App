import json
import os
import sys
import time
import logging
import grpc
from kafka import KafkaConsumer

# Add app to path
sys.path.append(os.getcwd())
from app import wallet_pb2, wallet_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s - COMPENSATION - %(levelname)s - %(message)s")
logger = logging.getLogger("CompWorker")

KAFKA_BROKER = os.environ.get("KAFKA_BROKER_URL", "localhost:29092")
# In production, this would route to the specific regional gRPC endpoint
WALLET_SERVICE_URL = os.environ.get("WALLET_SERVICE_URL", "localhost:50051")

def handle_compensation(event):
    payload = event.get("payload", {})
    txn_id = payload.get("original_transaction_id")
    wallet_id = payload.get("target_wallet")
    amount = payload.get("refund_amount")
    reason = payload.get("reason")
    
    logger.warning(f"Starting Compensation for {txn_id} | Target: {wallet_id} | Amount: {amount}")
    
    try:
        channel = grpc.insecure_channel(WALLET_SERVICE_URL)
        stub = wallet_pb2_grpc.WalletServiceStub(channel)
        
        req = wallet_pb2.RefundFundsRequest(
            original_transaction_id=txn_id,
            wallet_id=wallet_id,
            amount=amount,
            reason=reason
        )
        
        resp = stub.RefundFunds(req)
        if resp.success:
            logger.info(f"COMPENSATION SUCCESS: {txn_id} | Refunded via {resp.compensation_id}")
        else:
            logger.error(f"COMPENSATION FAILED: {txn_id} | {resp.message}")
            
    except Exception as e:
        logger.error(f"Critical error during compensation of {txn_id}: {e}")

def main():
    logger.info(f"Financial Compensation Worker starting...")
    
    consumer = None
    for i in range(10):
        try:
            consumer = KafkaConsumer(
                "transactions",
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='compensation-worker-group'
            )
            break
        except Exception:
            time.sleep(5)
            
    if not consumer: return

    for message in consumer:
        event = message.value
        if event.get("event_type") == "CompensatingRefundRequested":
            handle_compensation(event)

if __name__ == "__main__":
    main()
