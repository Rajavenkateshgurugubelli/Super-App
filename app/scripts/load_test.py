import requests
import time
import random
import logging
import uuid
import sys
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - LOAD TEST - %(levelname)s - %(message)s")
logger = logging.getLogger("LoadTest")

API_URL = "http://localhost:8000/api/transfer"
MOCK_TOKEN = "your_dummy_jwt_token_here"  # In a real environment, generate a valid JWT or bypass auth for testing.

def simulate_transaction(worker_id):
    try:
        # We simulate a generic transfer payload
        payload = {
            "from_wallet_id": "c1356be4-3c66-4191-bcb7-22a4c8402b85",
            "to_wallet_id": str(uuid.uuid4()),
            "amount": round(random.uniform(5.0, 50.0), 2),
            "currency": 1
        }
        
        headers = {
            "Authorization": f"Bearer {MOCK_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Note: In our current setup, the WAF enforces X-Signature. We bypass it here or assume WAF is temporarily disabled for pure throughput tests if signatures aren't dynamically generated.
        # For full testing, we would generate the HMAC signature here.
        
        response = requests.post(API_URL, json=payload, headers=headers, timeout=5.0)
        
        if response.status_code == 200 or response.status_code == 202:
            logger.info(f"Worker {worker_id} - Success ({response.status_code})")
        else:
            logger.warning(f"Worker {worker_id} - Failed ({response.status_code}): {response.text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Worker {worker_id} - Connection error: {e}")

def run_load_test(rpm=60, duration_seconds=60):
    logger.info(f"Starting Load Test targeting {API_URL} at {rpm} requests/min for {duration_seconds}s.")
    sleep_interval = 60.0 / rpm
    
    end_time = time.time() + duration_seconds
    worker_counter = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        while time.time() < end_time:
            executor.submit(simulate_transaction, worker_counter)
            worker_counter += 1
            time.sleep(sleep_interval)

    logger.info("Load test completed.")

if __name__ == "__main__":
    # Fire 120 requests per minute for 2 minutes
    run_load_test(rpm=120, duration_seconds=120)
