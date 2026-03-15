import json
import logging
import os
import time
from kafka import KafkaConsumer
from clickhouse_driver import Client

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AnalyticsConsumer")

def setup_clickhouse(client):
    try:
        # Create DB
        client.execute('CREATE DATABASE IF NOT EXISTS superapp')
        
        # Create Table optimized for analytics (MergeTree)
        client.execute('''
            CREATE TABLE IF NOT EXISTS superapp.transactions_analytics (
                transaction_id UUID,
                event_type String,
                amount Float64,
                currency Int32,
                from_wallet_id String,
                to_wallet_id String,
                timestamp DateTime
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, currency)
        ''')
        logger.info("ClickHouse schema verified/created.")
    except Exception as e:
        logger.error(f"ClickHouse setup failed: {e}")

def main():
    kafka_url = os.environ.get('KAFKA_BROKER_URL', 'localhost:29092')
    ch_host = os.environ.get('CLICKHOUSE_HOST', 'localhost')
    topic = "transactions"
    
    logger.info(f"Starting Analytics Consumer. Kafka: {kafka_url}, ClickHouse: {ch_host}")
    
    # Initialize ClickHouse Client
    ch_client = Client(host=ch_host)
    
    # Retry connection logic for Kafka
    consumer = None
    retries = 5
    while retries > 0:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[kafka_url],
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='analytics-group',
                api_version=(0, 10, 1)
            )
            logger.info("Connected to Kafka successfully.")
            break
        except Exception as e:
            logger.warning(f"Kafka connection failed: {e}. Retrying in 5s...")
            time.sleep(5)
            retries -= 1

    if not consumer:
        logger.error("Could not connect to Kafka. Exiting.")
        return

    # Ensure ClickHouse tables exist
    # Retry loop since CH might be starting up
    ch_retries = 5
    while ch_retries > 0:
        try:
            ch_client.execute('SELECT 1')
            setup_clickhouse(ch_client)
            break
        except Exception as e:
            logger.warning(f"ClickHouse connection failed: {e}. Retrying...")
            time.sleep(5)
            ch_retries -= 1

    logger.info(f"Listening for events on topic: {topic} to sink into ClickHouse.")

    # Batching config
    batch_size = 100
    batch_timeout = 5.0 # seconds
    batch = []
    last_flush = time.time()

    for message in consumer:
        try:
            event = message.value
            event_type = event.get("event_type")
            
            # We are interested in TransactionInitiated or TransactionCompleted type events
            if event_type in ["TransactionInitiated", "TransactionCompleted"]:
                payload = event.get("payload", {})
                
                # Normalize data for ClickHouse
                row = {
                    'transaction_id': payload.get("transaction_id", "00000000-0000-0000-0000-000000000000"),
                    'event_type': event_type,
                    'amount': float(payload.get("amount", 0.0)),
                    'currency': int(payload.get("currency", 1)),
                    'from_wallet_id': payload.get("from_wallet", ""),
                    'to_wallet_id': payload.get("to_wallet", ""),
                    'timestamp': int(time.time())
                }
                batch.append(row)
                
            # Flush batch if it's full or timeout reached
            now = time.time()
            if len(batch) >= batch_size or (now - last_flush) >= batch_timeout:
                if batch:
                    try:
                        ch_client.execute(
                            'INSERT INTO superapp.transactions_analytics (transaction_id, event_type, amount, currency, from_wallet_id, to_wallet_id, timestamp) VALUES',
                            batch
                        )
                        logger.info(f"Flushed {len(batch)} records to ClickHouse.")
                    except Exception as ch_err:
                        logger.error(f"Failed to insert batch to ClickHouse: {ch_err}")
                    batch.clear()
                last_flush = now
                
        except Exception as e:
            logger.error(f"Error processing message for analytics: {e}")

if __name__ == "__main__":
    main()
