import requests
import time
import random
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - LOAD TEST - %(levelname)s - %(message)s")
logger = logging.getLogger("LoadHarness")

GATEWAY_URL = "http://localhost:8000"
LOGIN_URL = f"{GATEWAY_URL}/api/login"
TRANSFER_URL = f"{GATEWAY_URL}/api/transfer"

# Region Mapping: 1=India, 2=Europe, 3=USA
REGIONS = [1, 2, 3]

def run_worker(worker_id):
    """Simulates a user lifecycle: Login -> Check Wallets -> Transfer."""
    try:
        region = random.choice(REGIONS)
        # 1. Login (Mocked email/pass)
        # In a real test, we would have a pool of real test accounts
        user_email = f"loadtest_{random.randint(1, 1000)}@example.com"
        
        # 2. Simulate Transfer
        # For pure load testing, we use a pre-authorized token or bypass auth
        payload = {
            "from_wallet_id": str(uuid.uuid4()),
            "to_wallet_id": str(uuid.uuid4()),
            "amount": round(random.uniform(1.0, 100.0), 2)
        }
        
        headers = {
            "Authorization": "Bearer MOCKED_TOKEN", # Gateway must be in test mode to accept this
            "Content-Type": "application/json"
        }
        
        start = time.time()
        resp = requests.post(TRANSFER_URL, json=payload, headers=headers, timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            logger.info(f"Worker {worker_id} | SUCCESS | Region {region} | Latency {latency:.2f}ms")
        elif resp.status_code == 429:
            logger.warning(f"Worker {worker_id} | RATE_LIMITED | Latency {latency:.2f}ms")
        else:
            logger.error(f"Worker {worker_id} | FAILED {resp.status_code} | {resp.text[:50]}")

    except Exception as e:
        logger.error(f"Worker {worker_id} | ERROR: {e}")

def main(qps=10, duration=30):
    logger.info(f"### Super App Shard Stress Test ###")
    logger.info(f"Targeting: {GATEWAY_URL} | Goal: {qps} QPS | Duration: {duration}s")
    
    total_requests = qps * duration
    delay = 1.0 / qps
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        for i in range(total_requests):
            executor.submit(run_worker, i)
            time.sleep(delay)

if __name__ == "__main__":
    main(qps=25, duration=60) # 1500 Requests
