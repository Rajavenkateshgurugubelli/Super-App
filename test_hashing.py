import sys
import os
sys.path.append(os.getcwd())
from app.security import get_password_hash, verify_password

try:
    print("Hashing 'test'...")
    h = get_password_hash("test")
    print(f"Success: {h}")
    
    print("Hashing 'mypassword'...")
    h = get_password_hash("mypassword")
    print(f"Success: {h}")

except Exception as e:
    print(f"Error: {e}")
