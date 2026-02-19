import requests
import json

url = "http://localhost:8000/api/users"
payload = {
    "email": "test_user_v5@example.com",
    "name": "Test User",
    "password": "securepassword123",
    "region": 1
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
