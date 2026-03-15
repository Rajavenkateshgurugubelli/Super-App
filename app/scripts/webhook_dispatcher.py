import os
import json
import logging
import requests
from kafka import KafkaConsumer
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - WEBHOOK - %(levelname)s - %(message)s")
logger = logging.getLogger("WebhookDispatcher")

KAFKA_BROKER_URL = os.environ.get('KAFKA_BROKER_URL', 'localhost:29092')
WEBHOOK_TIMEOUT_SECONDS = 5

def start_dispatcher():
    try:
        consumer = KafkaConsumer(
            'transactions',
            bootstrap_servers=[KAFKA_BROKER_URL],
            group_id='webhook_dispatcher_group',
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        logger.info(f"Connected to Kafka at {KAFKA_BROKER_URL}. Listening to 'transactions' topic...")
    except Exception as e:
        logger.error(f"Failed to connect to Kafka at {KAFKA_BROKER_URL}: {e}")
        return

    for message in consumer:
        try:
            event = message.value
            event_type = event.get("event_type")
            payload = event.get("payload", {})

            if event_type == "TransactionCompleted":
                webhook_url = payload.get("webhook_url")
                if webhook_url:
                    dispatch_webhook(webhook_url, payload)

        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")

def dispatch_webhook(url: str, payload: dict):
    # Validate URL
    parsed = urlparse(url)
    if not all([parsed.scheme, parsed.netloc]):
        logger.warning(f"Invalid webhook URL format: {url}")
        return

    logger.info(f"Dispatching webhook for Txn ID {payload.get('transaction_id')} to {url}")
    
    try:
        response = requests.post(url, json=payload, timeout=WEBHOOK_TIMEOUT_SECONDS)
        if 200 <= response.status_code < 300:
            logger.info(f"✅ Webhook delivered successfully: {response.status_code}")
        else:
            logger.warning(f"⚠️ Webhook delivery failed with status {response.status_code}: {response.text}")
    except requests.exceptions.Timeout:
         logger.error(f"❌ Webhook dispatch timed out ({WEBHOOK_TIMEOUT_SECONDS}s) for {url}")
    except requests.exceptions.RequestException as e:
         logger.error(f"❌ Webhook dispatch error for {url}: {e}")

if __name__ == "__main__":
    start_dispatcher()
