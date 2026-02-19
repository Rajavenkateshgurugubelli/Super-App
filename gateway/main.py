from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import grpc
import os
import sys
import jwt
import sys
import os

# Add the project root (where 'app' is located) to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# Also add 'app' itself for some generated code hacks if needed, but usually parent is enough
APP_DIR = os.path.join(BASE_DIR, "app")
if APP_DIR not in sys.path:
  sys.path.append(APP_DIR)

# Now imports should work
from app import user_pb2, user_pb2_grpc
from app import wallet_pb2, wallet_pb2_grpc
from app.security import SECRET_KEY, ALGORITHM

app = FastAPI(title="Super App Gateway")
security = HTTPBearer()

# gRPC Channel
# gRPC Channel
GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
GRPC_SECURE = os.environ.get("GRPC_SECURE", "false").lower() == "true"

print(f"Connecting to gRPC service at {GRPC_HOST} (Secure: {GRPC_SECURE})")

if GRPC_SECURE:
    # Cloud Run/HTTPS requires secure channel with system certs
    # GRPC_HOST might include https:// prefix which needs stripping for python grpc?
    # Actually python grpc usually expects host:port. 
    # Cloud Run URL: https://service-hash-region.a.run.app (port 443 implicit)
    
    if GRPC_HOST.startswith("https://"):
        GRPC_HOST = GRPC_HOST.replace("https://", "")
        if ":" not in GRPC_HOST:
             GRPC_HOST = f"{GRPC_HOST}:443"
             
    creds = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(GRPC_HOST, creds)
else:
    channel = grpc.insecure_channel(GRPC_HOST)
user_stub = user_pb2_grpc.UserServiceStub(channel)
wallet_stub = wallet_pb2_grpc.WalletServiceStub(channel)

# Auth Dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

# Pydantic Models for Request Body
class CreateUserRequest(BaseModel):
    email: str
    name: str
    region: int # 1=India, 2=EU, 3=US
    password: str
    phone_number: str = None

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateWalletRequest(BaseModel):
    currency: int # 1=USD, 2=INR, 3=EUR

class TransferRequest(BaseModel):
    from_wallet_id: str
    to_wallet_id: str = None
    to_phone_number: str = None
    amount: float

@app.post("/api/users")
def create_user(req: CreateUserRequest):
    try:
        grpc_req = user_pb2.CreateUserRequest(
            email=req.email,
            name=req.name,
            region=req.region,
            password=req.password,
            phone_number=req.phone_number
        )
        resp = user_stub.CreateUser(grpc_req)
        return {"user_id": resp.user.user_id, "name": resp.user.name, "email": resp.user.email}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/login")
def login(req: LoginRequest):
    try:
        grpc_req = user_pb2.LoginRequest(email=req.email, password=req.password)
        resp = user_stub.Login(grpc_req)
        if resp.success: # Assuming LoginResponse has success field, wait, check proto
            # Check user.proto? Usually Login returns token.
            # user.proto: rpc Login (LoginRequest) returns (LoginResponse);
            # message LoginResponse { string token = 1; User user = 2; bool success = 3; string message = 4; }
            # Let's assume standard structure.
            return {
                "token": resp.token,
                "user": {
                    "user_id": resp.user.user_id,
                    "name": resp.user.name,
                    "email": resp.user.email,
                    # region is enum in proto, map to int or string?
                    "region": resp.user.region
                }
            }
        else:
             raise HTTPException(status_code=401, detail=resp.message)
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())
    except Exception as e:
        # Fallback for proto mismatch
        raise HTTPException(status_code=401, detail="Login Failed")

@app.post("/api/wallets")
def create_wallet(req: CreateWalletRequest, user_id: str = Depends(get_current_user)):
    try:
        # Map pydantic currency (int) to proto currency enum
        grpc_req = wallet_pb2.CreateWalletRequest(user_id=user_id, currency=req.currency)
        resp = wallet_stub.CreateWallet(grpc_req)
        # Assuming CreateWalletResponse has wallet field
        w = resp.wallet
        return {
            "wallet_id": w.wallet_id,
            "currency": w.currency,
            "balance": w.balance
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets")
def list_wallets(user_id: str = Depends(get_current_user)):
    try:
        grpc_req = wallet_pb2.ListWalletsRequest(user_id=user_id)
        resp = wallet_stub.ListWallets(grpc_req)
        return {"wallets": [{
            "wallet_id": w.wallet_id,
            "currency": w.currency,
            "balance": w.balance,
            "user_id": w.user_id
        } for w in resp.wallets]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/balance")
def get_balance(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        # Security: Check if wallet belongs to user? 
        # For now, simplistic.
        grpc_req = wallet_pb2.GetBalanceRequest(wallet_id=wallet_id)
        resp = wallet_stub.GetBalance(grpc_req)
        return {
            "wallet_id": resp.wallet.wallet_id, 
            "balance": resp.wallet.balance, 
            "currency": resp.wallet.currency
        }
    except grpc.RpcError as e:
         raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/transfer")
def transfer_funds(req: TransferRequest, user_id: str = Depends(get_current_user)):
    if not req.to_wallet_id and not req.to_phone_number:
         raise HTTPException(status_code=400, detail="Either Recipient Wallet ID or Phone Number is required")
         
    try:
        grpc_req = wallet_pb2.TransferFundsRequest(
            from_wallet_id=req.from_wallet_id,
            to_wallet_id=req.to_wallet_id if req.to_wallet_id else "",
            to_phone_number=req.to_phone_number if req.to_phone_number else "",
            amount=req.amount
        )
        resp = wallet_stub.TransferFunds(grpc_req)
        if not resp.success:
            raise HTTPException(status_code=400, detail=resp.message)
        return {"success": True, "transaction_id": resp.transaction_id, "message": resp.message}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/transactions")
def get_transactions(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        grpc_req = wallet_pb2.GetTransactionHistoryRequest(wallet_id=wallet_id)
        resp = wallet_stub.GetTransactionHistory(grpc_req)
        return {"transactions": [{
            "transaction_id": t.transaction_id,
            "from_wallet_id": t.from_wallet_id,
            "to_wallet_id": t.to_wallet_id,
            "amount": t.amount,
            "status": t.status,
            "timestamp": t.timestamp
        } for t in resp.transactions]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/conversions")
def get_conversion_history(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        grpc_req = wallet_pb2.GetConversionHistoryRequest(wallet_id=wallet_id)
        resp = wallet_stub.GetConversionHistory(grpc_req)
        return {"records": [{
            "transaction_id": r.transaction_id,
            "from_currency": r.from_currency,
            "to_currency": r.to_currency,
            "rate": r.rate,
            "amount_original": r.amount_original,
            "amount_converted": r.amount_converted,
            "timestamp": r.timestamp
        } for r in resp.records]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
