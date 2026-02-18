import grpc
import sys
import os
import time

# Add root and app directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'app'))

from app import user_pb2
from app import user_pb2_grpc

def run():
    print("Attempting to connect to server...")
    # Retry logic
    for i in range(5):
        try:
            with grpc.insecure_channel('localhost:50051') as channel:
                stub = user_pb2_grpc.UserServiceStub(channel)
                response = stub.CreateUser(user_pb2.CreateUserRequest(
                    email="test@example.com", 
                    name="Test User", 
                    region=user_pb2.REGION_US
                ))
                print(f"Success! User created with ID: {response.user.user_id}")
                return
        except Exception as e:
            print(f"Connection attempt {i+1} failed: {e}")
            time.sleep(1)
    print("Failed to connect after retries.")

if __name__ == '__main__':
    run()
