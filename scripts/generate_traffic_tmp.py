import requests
import time
import hmac
import hashlib
import json

BASE_URL = "http://localhost:8000"
SECRET_KEY = "supersecretkey" # Matches default in app/security.py

def get_signature(body_bytes):
    return hmac.new(SECRET_KEY.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()

def generate_traffic():
    print("Generating traffic...")
    
    # 1. Hit public endpoints
    for _ in range(20):
        requests.get(f"{BASE_URL}/health")
        requests.get(f"{BASE_URL}/api/fx/rates")
        requests.get(f"{BASE_URL}/api/policies")
        time.sleep(0.1)

    # 2. Login
    login_data = {"email": "admin@abc.com", "password": "admin1", "region": 3}
    body_bytes = json.dumps(login_data).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "X-Signature": get_signature(body_bytes)
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/login", data=body_bytes, headers=headers)
        if resp.status_code == 200:
            token = resp.json().get("token")
            auth_headers = {"Authorization": f"Bearer {token}"}
            print("Login successful. Generating authenticated traffic...")
            
            # 3. Hit authenticated endpoints
            for _ in range(50):
                requests.get(f"{BASE_URL}/api/me", headers=auth_headers)
                requests.get(f"{BASE_URL}/api/wallets", headers=auth_headers)
                time.sleep(0.05)
        else:
            print(f"Login failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Error during traffic generation: {e}")

if __name__ == "__main__":
    generate_traffic()
