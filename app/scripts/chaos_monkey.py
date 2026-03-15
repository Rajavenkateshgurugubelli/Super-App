import docker
import random
import time
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - CHAOS MONKEY - %(levelname)s - %(message)s")
logger = logging.getLogger("ChaosMonkey")

# Candidate services to unleash chaos upon. Avoid DBs or Kafka for base testing to ensure app-tier resilience.
TARGET_SERVICES = [
    "gateway",
    "wallet-service",
    "user-service",
    "policy-service"
]

def run_chaos(interval_seconds=30):
    try:
        client = docker.from_env()
        logger.info(f"Connected to Docker daemon. Commencing Chaos Engineering on services: {TARGET_SERVICES}")
    except Exception as e:
        logger.error(f"Failed to connect to Docker daemon: {e}")
        sys.exit(1)

    while True:
        try:
            # Sleep for the interval before striking
            time.sleep(interval_seconds)

            # Pick a target
            target = random.choice(TARGET_SERVICES)
            
            # Find the container
            containers = client.containers.list(filters={"name": target})
            if not containers:
                logger.warning(f"Could not find running container for {target}. Skipper this cycle.")
                continue

            container = containers[0]
            action = random.choice(["restart", "stop_start"])

            if action == "restart":
                logger.warning(f"💥 ACTION: Restarting container '{target}' (ID: {container.short_id})...")
                container.restart()
                logger.info(f"✅ Recovered container '{target}'.")
            
            elif action == "stop_start":
                pause_duration = random.randint(3, 10)
                logger.warning(f"💥 ACTION: Stopping container '{target}' for {pause_duration} seconds...")
                container.stop()
                time.sleep(pause_duration)
                logger.warning(f"♻️ ACTION: Starting container '{target}'...")
                container.start()
                logger.info(f"✅ Recovered container '{target}'.")

        except KeyboardInterrupt:
            logger.info("Chaos Monkey scaling down. Exiting...")
            break
        except Exception as e:
            logger.error(f"Chaos Monkey encountered an error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # In a real environment, this interval is longer (e.g., minutes/hours).
    # Setting to 15 seconds for aggressive local load testing proof.
    run_chaos(interval_seconds=15)
