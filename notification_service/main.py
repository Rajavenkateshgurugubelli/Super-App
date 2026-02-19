import json
import logging
import os
from kafka import KafkaConsumer
import time
import sys

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NotificationService")

def main():
    kafka_url = os.environ.get('KAFKA_BROKER_URL', 'localhost:29092')
    topic = "transactions"
    
    logger.info(f"Starting Notification Service. Connecting to {kafka_url}...")
    
    # Retry connection logic
    consumer = None
    retries = 5
    while retries > 0:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[kafka_url],
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='notification-group',
                api_version=(0, 10, 1)
            )
            logger.info("Connected to Kafka successfully.")
            break
        except Exception as e:
            logger.warning(f"Connection failed: {e}. Retrying in 5s...")
            time.sleep(5)
            retries -= 1

    if not consumer:
        logger.error("Could not connect to Kafka. Exiting.")
        return

    logger.info(f"Listening for events on topic: {topic}")

    for message in consumer:
        try:
            event = message.value
            event_type = event.get("event_type")
            payload = event.get("payload")
            
            if event_type == "TransactionInitiated":
                handle_transaction_event(payload)
            else:
                logger.debug(f"Ignored event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")

def handle_transaction_event(payload):
    txn_id = payload.get("transaction_id")
    amount = payload.get("amount")
    currency = payload.get("currency")
    to_wallet = payload.get("to_wallet")
    
    # Mock sending Notification
    logger.info(f"🔔 NOTIFICATION: Transaction {txn_id} initiated.")
    logger.info(f"   Message: 'You have sent {amount} {currency} to {to_wallet}.'")
    
    # Here we would integrate with Twilio (SMS) or SendGrid (Email)

if __name__ == "__main__":
    main()
