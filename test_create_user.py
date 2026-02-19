import urllib.request
import json
import logging

logging.basicConfig(level=logging.INFO)

url = "http://localhost:8000/api/users"
payload = {
    "email": "test_script_user@example.com",
    "name": "Script User",
    "password": "mypassword",
    "region": 1
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        print(f"Response: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
