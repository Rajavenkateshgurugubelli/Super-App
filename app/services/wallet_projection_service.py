import os
import json
import logging
import redis
from kafka import KafkaConsumer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - CQRS-PROJECTION - %(levelname)s - %(message)s")
logger = logging.getLogger("WalletProjectionService")

KAFKA_BROKER_URL = os.environ.get('KAFKA_BROKER_URL', 'localhost:29092')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

class WalletProjectionService:
    """
    Implements the Query side of the CQRS pattern.
    Listens to Kafka Transaction Events (the Command side) and materializes 
    an ultra-fast read-optimized viewing layer in Redis. Real users querying their 
    balance hit this Redis view, entirely avoiding the CockroachDB master nodes.
    """
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL)

    def start(self):
        try:
            consumer = KafkaConsumer(
                'transactions',
                bootstrap_servers=[KAFKA_BROKER_URL],
                group_id='cqrs_projection_group',
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info(f"CQRS Projection Engine connected to Kafka. Materializing views to Redis...")
        except Exception as e:
            logger.error(f"CQRS failed to connect to Kafka: {e}")
            return

        for message in consumer:
            self.process_event(message.value)

    def process_event(self, event: dict):
        event_type = event.get("event_type")
        payload = event.get("payload", {})

        if event_type == "TransactionCompleted":
            from_wallet = payload.get("from_wallet")
            to_wallet = payload.get("to_wallet")
            amount = payload.get("amount", 0.0)

            # Materialize the Read Model:
            # We decrement the sender's balance and increment the receiver's balance in Redis.
            # In a true Event Sourcing architecture, balance is just a fold (reduce) over all events.
            if from_wallet:
                # Atomically apply the debit to the materialized view
                new_bal = self.redis_client.hincrbyfloat(f"wallet_view:{from_wallet}", "balance", -amount)
                logger.info(f"CQRS: Updated Read View for {from_wallet}: {new_bal}")
            
            if to_wallet:
                # Atomically apply the credit
                new_bal = self.redis_client.hincrbyfloat(f"wallet_view:{to_wallet}", "balance", amount)
                logger.info(f"CQRS: Updated Read View for {to_wallet}: {new_bal}")

if __name__ == "__main__":
    service = WalletProjectionService()
    service.start()
