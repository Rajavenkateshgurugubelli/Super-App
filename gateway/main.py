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

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

# Setup Tracing
try:
    resource = Resource.create(attributes={"service.name": os.environ.get("OTEL_SERVICE_NAME", "superapp-gateway")})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    otlp_exporter = OTLPSpanExporter(endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"), insecure=True)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Instrument gRPC Client
    GrpcInstrumentorClient().instrument()
    
    app = FastAPI(title="Super App Gateway")
    FastAPIInstrumentor.instrument_app(app) # Instruments requests
except Exception as e:
    print(f"Failed to initialize OpenTelemetry: {e}")
    app = FastAPI(title="Super App Gateway") # Fallback creation

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
        # LoginResponse proto only has: token (str) and user (User)
        # No success field — check token is non-empty
        if resp.token:
            return {
                "token": resp.token,
                "user": {
                    "user_id": resp.user.user_id,
                    "name": resp.user.name,
                    "email": resp.user.email,
                    "region": resp.user.region
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except grpc.RpcError as e:
        raise HTTPException(status_code=401, detail=e.details())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

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
        # wallet_pb2 has no ListWallets RPC — query the shared DB directly
        from app.database import SessionLocal
        from app.models import Wallet
        session = SessionLocal()
        try:
            wallets = session.query(Wallet).filter(Wallet.user_id == user_id).all()
            return {"wallets": [{
                "wallet_id": w.wallet_id,
                "currency": w.currency.value if hasattr(w.currency, 'value') else str(w.currency),
                "balance": float(w.balance),
                "user_id": w.user_id
            } for w in wallets]}
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
