import requests
import uuid

BASE_URL = "http://localhost:8000"

def run_tests():
    print("Testing API Gateway...")
    
    # 1. Create User
    email = f"gateway{uuid.uuid4()}@example.com"
    print(f"Creating user: {email}")
    resp = requests.post(f"{BASE_URL}/api/users", json={
        "email": email,
        "name": "Gateway User",
        "region": 3
    })
    print(f"User Response: {resp.status_code} - {resp.json()}")
    if resp.status_code != 200:
        print("FAILED: Create User")
        return
    user_id = resp.json()["user_id"]

    # 2. Create Wallet
    print(f"Creating wallet for user: {user_id}")
    resp = requests.post(f"{BASE_URL}/api/wallets", json={
        "user_id": user_id,
        "currency": 1
    })
    print(f"Wallet Response: {resp.status_code} - {resp.json()}")
    if resp.status_code != 200:
        print("FAILED: Create Wallet")
        return
    wallet_id = resp.json()["wallet_id"]

    # 3. Get Balance
    print(f"Getting balance for wallet: {wallet_id}")
    resp = requests.get(f"{BASE_URL}/api/wallets/{wallet_id}")
    print(f"Balance Response: {resp.status_code} - {resp.json()}")
    if resp.status_code != 200:
        print("FAILED: Get Balance")
        return

    print("SUCCESS: usage flow verified via REST Gateway!")

if __name__ == "__main__":
    run_tests()
