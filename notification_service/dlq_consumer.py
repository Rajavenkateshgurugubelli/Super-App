import json
import logging
import os
import time
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DLQ-Consumer")

# Config
MAX_RETRIES = 3
RETRY_DELAY_SEC = 5
DLQ_LOG_PATH = os.environ.get("DLQ_LOG_PATH", "compliance_reports/dlq_events.jsonl")

# In-memory counters (exposed via file or metrics endpoint)
stats = {"total_received": 0, "total_retried": 0, "total_dead": 0}


def _append_dead_letter(event: dict):
    """Persist permanently dead event to JSONL file for admin inspection."""
    os.makedirs(os.path.dirname(DLQ_LOG_PATH), exist_ok=True)
    record = {
        **event,
        "permanently_failed_at": datetime.utcnow().isoformat() + "Z",
        "stats_snapshot": dict(stats),
    }
    try:
        with open(DLQ_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.error(f"💀 Permanently dead event written to {DLQ_LOG_PATH}")
    except Exception as e:
        logger.critical(f"Could not write dead letter to file: {e}")


def _retry_event(producer: KafkaProducer, event: dict, retry_count: int) -> bool:
    """Re-publish original_message back to 'transactions' topic. Returns True if successful."""
    original = event.get("original_message")
    if not original:
        logger.error("DLQ event has no original_message — cannot retry.")
        return False

    for attempt in range(1, retry_count + 1):
        try:
            producer.send("transactions", value=original)
            producer.flush()
            logger.info(f"✅ Retry attempt {attempt}/{retry_count} succeeded — re-queued to 'transactions'.")
            stats["total_retried"] += 1
            return True
        except Exception as e:
            logger.warning(f"Retry attempt {attempt}/{retry_count} failed: {e}")
            if attempt < retry_count:
                time.sleep(RETRY_DELAY_SEC)
    return False


def main():
    kafka_url = os.environ.get("KAFKA_BROKER_URL", "localhost:29092")
    topic = "transactions-dlq"

    logger.info(f"Starting DLQ Consumer. Connecting to Kafka at {kafka_url}...")

    consumer = None
    retries = 5
    while retries > 0:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[kafka_url],
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                auto_offset_reset="earliest",
                group_id="dlq-group",
                api_version=(0, 10, 1),
                enable_auto_commit=True,
            )
            logger.info("Connected to Kafka DLQ consumer successfully.")
            break
        except Exception as e:
            logger.warning(f"Connection failed: {e}. Retrying in 5s...")
            time.sleep(5)
            retries -= 1

    if not consumer:
        logger.error("Could not connect to Kafka DLQ consumer. Exiting.")
        return

    # Producer for retrying events back to main topic
    retry_producer = None
    try:
        retry_producer = KafkaProducer(
            bootstrap_servers=[kafka_url],
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            api_version=(0, 10, 1),
        )
        logger.info("Connected to retry producer.")
    except Exception as e:
        logger.warning(f"Could not initialise retry producer: {e}. Retry disabled.")

    logger.info(f"Listening for dead-letter events on topic: {topic}")

    for message in consumer:
        try:
            dlq_event = message.value
            stats["total_received"] += 1

            error_reason = dlq_event.get("error_reason", "unknown")
            failed_at = dlq_event.get("failed_at", 0)

            logger.error(
                f"🚨 DLQ event #{stats['total_received']} received. "
                f"Reason: '{error_reason}'. "
                f"Originally failed at: {datetime.utcfromtimestamp(float(failed_at)).isoformat()}"
            )

            # Attempt retry
            retry_count = dlq_event.get("retry_count", 0) + 1
            if retry_producer and retry_count <= MAX_RETRIES:
                logger.info(f"Attempting retry {retry_count}/{MAX_RETRIES}...")
                dlq_event["retry_count"] = retry_count
                success = _retry_event(retry_producer, dlq_event, retry_count=1)
                if not success:
                    # Exhausted this retry — re-enqueue with incremented count (next consumer pick-up)
                    retry_producer.send(topic, value=dlq_event)
                    retry_producer.flush()
                    logger.warning(f"Re-enqueued with retry_count={retry_count} for next attempt.")
            else:
                # Permanently dead
                logger.error(
                    f"💀 Event exceeded max retries ({MAX_RETRIES}). Moving to dead letter store."
                )
                stats["total_dead"] += 1
                _append_dead_letter(dlq_event)

        except Exception as e:
            logger.critical(f"Critical error processing DLQ message: {e}")

    logger.info(f"DLQ Consumer shutting down. Stats: {stats}")


if __name__ == "__main__":
    main()
