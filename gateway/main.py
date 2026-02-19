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
GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
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

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateWalletRequest(BaseModel):
    currency: int # 1=USD, 2=INR, 3=EUR

class TransferRequest(BaseModel):
    from_wallet_id: str
    to_wallet_id: str
    amount: float

@app.post("/api/users")
def create_user(req: CreateUserRequest):
    try:
        grpc_req = user_pb2.CreateUserRequest(
            email=req.email,
            name=req.name,
            region=req.region,
            password=req.password
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
        if not resp.token:
             raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"token": resp.token, "user": {"user_id": resp.user.user_id, "name": resp.user.name, "email": resp.user.email}}
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
             raise HTTPException(status_code=401, detail="Invalid credentials")
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/wallets")
def create_wallet(req: CreateWalletRequest, user_id: str = Depends(get_current_user)):
    try:
        grpc_req = wallet_pb2.CreateWalletRequest(
            user_id=user_id,
            currency=req.currency
        )
        resp = wallet_stub.CreateWallet(grpc_req)
        return {"wallet_id": resp.wallet.wallet_id, "currency": resp.wallet.currency, "balance": resp.wallet.balance}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}")
def get_balance(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        # Ideally verify wallet belongs to user_id here or in backend
        grpc_req = wallet_pb2.GetBalanceRequest(wallet_id=wallet_id)
        resp = wallet_stub.GetBalance(grpc_req)
        return {"wallet_id": resp.wallet.wallet_id, "balance": resp.wallet.balance, "currency": resp.wallet.currency}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/transfer")
def transfer_funds(req: TransferRequest, user_id: str = Depends(get_current_user)):
    try:
        grpc_req = wallet_pb2.TransferFundsRequest(
            from_wallet_id=req.from_wallet_id,
            to_wallet_id=req.to_wallet_id,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
