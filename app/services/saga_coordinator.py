import os
import json
import logging
import requests
from kafka import KafkaConsumer, KafkaProducer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - SAGA-COORDINATOR - %(levelname)s - %(message)s")
logger = logging.getLogger("SagaCoordinator")

KAFKA_BROKER_URL = os.environ.get('KAFKA_BROKER_URL', 'localhost:29092')

class SagaCoordinator:
    """
    Implements a Choreography Saga architecture guaranteeing eventual consistency.
    Listens to a stream of domain events. If a downstream service emits a failure
    event (e.g., KYCRejectionEvent), the Saga catches it and issues compensating 
    transactions upstream (e.g., RefundWallet) to ensure the system returns to a valid state.
    """
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER_URL],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def start(self):
        try:
            consumer = KafkaConsumer(
                'transactions',
                'kyc-events',
                bootstrap_servers=[KAFKA_BROKER_URL],
                group_id='saga_coordinator_group',
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info("Saga Orchestrator online. Monitoring distributed transactions for failures...")
        except Exception as e:
            logger.error(f"Saga Orchestrator failed to initialize Kafka: {e}")
            return

        for message in consumer:
            self.process_domain_event(message.topic, message.value)

    def process_domain_event(self, topic: str, event: dict):
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        
        # Scenario: A transaction cleared the Wallet, but failed compliance checks on the Notification/Webhook side
        if event_type == "WebhookDeliveryFailed" or event_type == "ComplianceCheckFailed":
            txn_id = payload.get("transaction_id")
            from_wallet = payload.get("from_wallet")
            amount = payload.get("amount")
            
            logger.warning(f"SAGA: Detected failure '{event_type}' for txn {txn_id}. Initiating Compensating Refund...")
            
            # Emit the compensating transaction back to the Wallet Service
            compensating_event = {
                "event_type": "CompensatingRefundRequested",
                "payload": {
                    "original_transaction_id": txn_id,
                    "target_wallet": from_wallet,
                    "refund_amount": amount,
                    "reason": f"Saga Rollback due to {event_type}"
                }
            }
            
            self.producer.send('transactions', value=compensating_event)
            self.producer.flush()
            logger.info(f"SAGA: CompensatingRefundRequested successfully queued onto the message bus.")

if __name__ == "__main__":
    saga = SagaCoordinator()
    saga.start()
