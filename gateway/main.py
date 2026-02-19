from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import grpc
import os
import sys

# Add root to sys.path to find protos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey patch sys.path so that 'import user_pb2' works from inside app/
# The generated code expects 'import user_pb2', not 'from app import# Add root to sys.path to find protos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey patch sys.path so that 'import user_pb2' works from inside app/
# The generated code expects 'import user_pb2', not 'from app import user_pb2'
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from app import user_pb2, user_pb2_grpc
from app import wallet_pb2, wallet_pb2_grpc

app = FastAPI(title="Super App Gateway")

# gRPC Channel
GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
channel = grpc.insecure_channel(GRPC_HOST)
user_stub = user_pb2_grpc.UserServiceStub(channel)
wallet_stub = wallet_pb2_grpc.WalletServiceStub(channel)

# Pydantic Models for Request Body
class CreateUserRequest(BaseModel):
    email: str
    name: str
    region: int # 1=India, 2=EU, 3=US

class CreateWalletRequest(BaseModel):
    user_id: str
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
            region=req.region
        )
        resp = user_stub.CreateUser(grpc_req)
        return {"user_id": resp.user.user_id, "name": resp.user.name, "email": resp.user.email}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/wallets")
def create_wallet(req: CreateWalletRequest):
    try:
        grpc_req = wallet_pb2.CreateWalletRequest(
            user_id=req.user_id,
            currency=req.currency
        )
        resp = wallet_stub.CreateWallet(grpc_req)
        return {"wallet_id": resp.wallet.wallet_id, "currency": resp.wallet.currency, "balance": resp.wallet.balance}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}")
def get_balance(wallet_id: str):
    try:
        grpc_req = wallet_pb2.GetBalanceRequest(wallet_id=wallet_id)
        resp = wallet_stub.GetBalance(grpc_req)
        return {"wallet_id": resp.wallet.wallet_id, "balance": resp.wallet.balance, "currency": resp.wallet.currency}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/transfer")
def transfer_funds(req: TransferRequest):
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
def get_transactions(wallet_id: str):
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
