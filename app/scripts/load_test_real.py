import requests
import hmac
import hashlib
import json
import time
import random
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import jwt

# Configuration (Mirrors app/security.py)
SECRET_KEY = "supersecretkey" # This would be an env var in prod
ALGORITHM = "HS256"

# Load Test Config
GATEWAY_URL = "http://localhost:8000"
TRANSFER_ENDPOINT = f"{GATEWAY_URL}/api/transfer"
CONCURRENCY = 20
TEST_DURATION = 30 # Seconds

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [STRESS TEST] - %(levelname)s - %(message)s")
logger = logging.getLogger("RegionalStress")

def generate_signed_jwt(user_id, region):
    """Generates a real JWT with the region claim required for Gateway sharding."""
    payload = {
        "user_id": user_id,
        "region": region,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def compute_hmac_signature(body_dict):
    """Computes the SHA256 HMAC for WAF verification."""
    body_bytes = json.dumps(body_dict, separators=(',', ':')).encode('utf-8')
    return hmac.new(SECRET_KEY.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()

def execute_strike(strike_id):
    """Simulates a single authenticated, signed cross-shard transfer request."""
    # Randomly target one of the three shards: India (1), EU (2), USA (3)
    region = random.choice([1, 2, 3])
    user_id = f"load_user_{strike_id}_{region}"
    
    token = generate_signed_jwt(user_id, region)
    
    # Payload for the transfer
    payload = {
        "from_wallet_id": f"wallet_{strike_id}",
        "to_wallet_id": "global_omnibus",
        "amount": round(random.uniform(0.1, 500.0), 2)
    }
    
    # Sign the payload for the WAF
    signature = compute_hmac_signature(payload)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Signature": signature,
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    try:
        resp = requests.post(TRANSFER_ENDPOINT, json=payload, headers=headers, timeout=5)
        latency = (time.time() - start_time) * 1000
        
        if resp.status_code == 200:
            logger.info(f"Strike {strike_id} | SUCCESS | Region {region} | Latency {latency:.2f}ms")
        elif resp.status_code == 403:
            logger.error(f"Strike {strike_id} | WAF BLOCK | Latency {latency:.2f}ms | {resp.json().get('detail')}")
        elif resp.status_code == 429:
            logger.warning(f"Strike {strike_id} | RATE LIMITED | Latency {latency:.2f}ms")
        else:
            logger.error(f"Strike {strike_id} | ERR {resp.status_code} | {resp.text[:60]}")
            
    except Exception as e:
        logger.error(f"Strike {strike_id} | NETWORK ERR | {str(e)}")

def run_stress_test():
    logger.info("Starting High-Capacity Regional Shard Stress Test...")
    logger.info(f"Targeting: {GATEWAY_URL} | Concurrency: {CONCURRENCY} | Duration: {TEST_DURATION}s")

    delay = 1.0 / 20 # 20 Requests Per Second strike rate
    total_strikes = 20 * TEST_DURATION

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        for i in range(total_strikes):
            executor.submit(execute_strike, i)
            time.sleep(delay)

if __name__ == "__main__":
    run_stress_test()
