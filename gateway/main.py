from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import grpc
import os
import sys
import jwt
import time
import json
import asyncio
import redis as redis_lib
import redis.asyncio as aioredis

# ── Path setup ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
APP_DIR = os.path.join(BASE_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

from app import user_pb2, user_pb2_grpc
from app import wallet_pb2, wallet_pb2_grpc
from app.security import SECRET_KEY, ALGORITHM

# ── OpenTelemetry ──────────────────────────────────────────────────────────────
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

try:
    resource = Resource.create(attributes={"service.name": os.environ.get("OTEL_SERVICE_NAME", "superapp-gateway")})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    otlp_exporter = OTLPSpanExporter(endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"), insecure=True)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
    GrpcInstrumentorClient().instrument()
    app = FastAPI(title="Super App Gateway", version="3.0.0")
    FastAPIInstrumentor.instrument_app(app)
except Exception as e:
    print(f"OpenTelemetry init failed: {e}")
    app = FastAPI(title="Super App Gateway", version="3.0.0")

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Redis (sync for rate limiting; async for pub/sub WebSocket) ────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_redis_sync = None
try:
    _redis_sync = redis_lib.from_url(REDIS_URL, decode_responses=True)
    _redis_sync.ping()
    print("Gateway: Redis (sync) connected")
except Exception as e:
    print(f"Gateway: Redis (sync) unavailable ({e})")

# ── Rate Limiting ──────────────────────────────────────────────────────────────
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_RPM", "120"))
RATE_WINDOW = 60

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if _redis_sync and not request.url.path.startswith("/ws"):
        try:
            client_ip = request.client.host
            key = f"rate:{client_ip}"
            now = time.time()
            pipe = _redis_sync.pipeline()
            pipe.zremrangebyscore(key, 0, now - RATE_WINDOW)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, RATE_WINDOW)
            results = pipe.execute()
            if results[2] > RATE_LIMIT:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=429, content={"detail": f"Rate limit: {RATE_LIMIT} req/min"}, headers={"Retry-After": str(RATE_WINDOW)})
        except Exception:
            pass
    return await call_next(request)

# ── gRPC Channel ───────────────────────────────────────────────────────────────
GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
GRPC_SECURE = os.environ.get("GRPC_SECURE", "false").lower() == "true"
print(f"gRPC → {GRPC_HOST} (secure={GRPC_SECURE})")

if GRPC_SECURE:
    if GRPC_HOST.startswith("https://"):
        GRPC_HOST = GRPC_HOST.replace("https://", "")
        if ":" not in GRPC_HOST:
            GRPC_HOST = f"{GRPC_HOST}:443"
    channel = grpc.secure_channel(GRPC_HOST, grpc.ssl_channel_credentials())
else:
    channel = grpc.insecure_channel(GRPC_HOST)

user_stub = user_pb2_grpc.UserServiceStub(channel)
wallet_stub = wallet_pb2_grpc.WalletServiceStub(channel)

# ── Auth helpers ───────────────────────────────────────────────────────────────
security = HTTPBearer()

def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("user_id"):
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return _decode_token(credentials.credentials)["user_id"]

def get_token_data(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return _decode_token(credentials.credentials)

def _db_get_user(user_id: str):
    """Direct DB lookup — used for is_admin and extra fields not in proto."""
    from app.database import SessionLocal
    from app.models import User as UserModel
    session = SessionLocal()
    try:
        return session.query(UserModel).filter(UserModel.user_id == user_id).first()
    finally:
        session.close()

def require_admin(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    db_user = _db_get_user(user_id)
    if not db_user or not db_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id

# ── FX Helpers ─────────────────────────────────────────────────────────────────
FX_RATES_USD_BASE = {1: 1.0, 2: 83.12, 3: 0.918}
CURRENCY_NAMES = {1: "USD", 2: "INR", 3: "EUR"}

def _convert_amount(amount: float, from_c: int, to_c: int):
    rate = FX_RATES_USD_BASE.get(to_c, 1.0) / FX_RATES_USD_BASE.get(from_c, 1.0)
    return round(amount * rate, 4), round(rate, 6)

# ── Pydantic Models ─────────────────────────────────────────────────────────────
class CreateUserRequest(BaseModel):
    email: str
    name: str
    region: int = 1
    password: str
    phone_number: str = None

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateWalletRequest(BaseModel):
    currency: int = 1

class TransferRequest(BaseModel):
    from_wallet_id: str
    to_wallet_id: str = None
    to_phone_number: str = None
    amount: float

class ConvertRequest(BaseModel):
    wallet_id: str
    to_currency: int
    amount: float

class UpdateProfileRequest(BaseModel):
    name: str

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0", "rate_limit_rpm": RATE_LIMIT}

# ── Auth endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/users", status_code=201)
def create_user(req: CreateUserRequest):
    try:
        resp = user_stub.CreateUser(user_pb2.CreateUserRequest(
            email=req.email, name=req.name, region=req.region,
            password=req.password, phone_number=req.phone_number or ""
        ))
        if not resp.user.user_id:
            raise HTTPException(status_code=400, detail="Failed to create user")
        # Auto-create USD wallet
        wallet_id = None
        try:
            w = wallet_stub.CreateWallet(wallet_pb2.CreateWalletRequest(user_id=resp.user.user_id, currency=1))
            wallet_id = w.wallet.wallet_id
        except Exception:
            pass
        return {"user_id": resp.user.user_id, "name": resp.user.name, "email": resp.user.email, "wallet_id": wallet_id, "message": "Account created! Please sign in."}
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/login")
def login(req: LoginRequest):
    try:
        resp = user_stub.Login(user_pb2.LoginRequest(email=req.email, password=req.password))
        if not resp.token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Fetch is_admin from DB
        from app.database import SessionLocal
        from app.models import User as UserModel
        session = SessionLocal()
        try:
            db_user = session.query(UserModel).filter(UserModel.user_id == resp.user.user_id).first()
            is_admin = bool(db_user.is_admin) if db_user else False
        finally:
            session.close()
        return {
            "token": resp.token,
            "user": {
                "user_id": resp.user.user_id, "name": resp.user.name,
                "email": resp.user.email, "region": resp.user.region,
                "kyc_status": resp.user.kyc_status,
                "phone_number": resp.user.phone_number,
                "is_admin": is_admin,
            }
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=401, detail=e.details())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/me")
def get_me(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    try:
        resp = user_stub.GetUser(user_pb2.GetUserRequest(user_id=user_id))
        if not resp.user.user_id:
            raise HTTPException(status_code=404, detail="User not found")
        db_user = _db_get_user(user_id)
        is_admin = bool(db_user.is_admin) if db_user else False
        return {
            "user_id": resp.user.user_id, "name": resp.user.name,
            "email": resp.user.email, "region": resp.user.region,
            "kyc_status": resp.user.kyc_status,
            "phone_number": resp.user.phone_number,
            "is_admin": is_admin,
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.patch("/api/me")
def update_profile(req: UpdateProfileRequest, token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    try:
        resp = user_stub.UpdateProfile(user_pb2.UpdateProfileRequest(user_id=user_id, name=req.name))
        return {"user_id": resp.user.user_id, "name": resp.user.name, "email": resp.user.email}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

# ── Wallet endpoints ───────────────────────────────────────────────────────────
@app.post("/api/wallets")
def create_wallet(req: CreateWalletRequest, user_id: str = Depends(get_current_user)):
    try:
        resp = wallet_stub.CreateWallet(wallet_pb2.CreateWalletRequest(user_id=user_id, currency=req.currency))
        w = resp.wallet
        return {"wallet_id": w.wallet_id, "currency": w.currency, "balance": w.balance}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets")
def list_wallets(user_id: str = Depends(get_current_user)):
    try:
        from app.database import SessionLocal
        from app.models import Wallet
        session = SessionLocal()
        try:
            wallets = session.query(Wallet).filter(Wallet.user_id == user_id).all()
            return {"wallets": [{"wallet_id": w.wallet_id, "currency": w.currency.value if hasattr(w.currency, "value") else int(w.currency), "balance": float(w.balance), "user_id": w.user_id} for w in wallets]}
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallets/{wallet_id}/balance")
def get_balance(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        resp = wallet_stub.GetBalance(wallet_pb2.GetBalanceRequest(wallet_id=wallet_id))
        return {"wallet_id": resp.wallet.wallet_id, "balance": resp.wallet.balance, "currency": resp.wallet.currency}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/transactions")
def get_transactions(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        resp = wallet_stub.GetTransactionHistory(wallet_pb2.GetTransactionHistoryRequest(wallet_id=wallet_id))
        return {"transactions": [{"transaction_id": t.transaction_id, "from_wallet_id": t.from_wallet_id, "to_wallet_id": t.to_wallet_id, "amount": t.amount, "status": t.status, "timestamp": t.timestamp} for t in resp.transactions]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/conversions")
def get_conversion_history(wallet_id: str, user_id: str = Depends(get_current_user)):
    try:
        resp = wallet_stub.GetConversionHistory(wallet_pb2.GetConversionHistoryRequest(wallet_id=wallet_id))
        return {"records": [{"transaction_id": r.transaction_id, "from_currency": r.from_currency, "to_currency": r.to_currency, "rate": r.rate, "amount_original": r.amount_original, "amount_converted": r.amount_converted, "timestamp": r.timestamp} for r in resp.records]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/transfer")
def transfer_funds(req: TransferRequest, user_id: str = Depends(get_current_user)):
    if not req.to_wallet_id and not req.to_phone_number:
        raise HTTPException(status_code=400, detail="Recipient wallet ID or phone number required")
    try:
        resp = wallet_stub.TransferFunds(wallet_pb2.TransferFundsRequest(
            from_wallet_id=req.from_wallet_id,
            to_wallet_id=req.to_wallet_id or "",
            to_phone_number=req.to_phone_number or "",
            amount=req.amount
        ))
        if not resp.success:
            raise HTTPException(status_code=400, detail=resp.message)
        return {"success": True, "transaction_id": resp.transaction_id, "message": resp.message}
    except HTTPException:
        raise
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

# ── FX / Convert ───────────────────────────────────────────────────────────────
@app.get("/api/fx/rates")
def get_fx_rates():
    rates = {}
    for fc, fn in CURRENCY_NAMES.items():
        rates[fn] = {CURRENCY_NAMES[tc]: round(FX_RATES_USD_BASE[tc] / FX_RATES_USD_BASE[fc], 6) for tc in CURRENCY_NAMES}
    return {"rates": rates, "base": "USD", "updated_at": int(time.time())}

@app.post("/api/convert")
def convert_currency(req: ConvertRequest, user_id: str = Depends(get_current_user)):
    try:
        bal_resp = wallet_stub.GetBalance(wallet_pb2.GetBalanceRequest(wallet_id=req.wallet_id))
        from_currency = bal_resp.wallet.currency
        if from_currency == req.to_currency:
            raise HTTPException(status_code=400, detail="Source and target currency are the same")
        converted, rate = _convert_amount(req.amount, from_currency, req.to_currency)
        return {"from_currency": CURRENCY_NAMES.get(from_currency), "to_currency": CURRENCY_NAMES.get(req.to_currency), "amount_original": req.amount, "amount_converted": converted, "rate": rate, "wallet_id": req.wallet_id}
    except HTTPException:
        raise
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

# ── P-D: Admin endpoints ───────────────────────────────────────────────────────
@app.get("/api/admin/stats")
def admin_stats(admin_id: str = Depends(require_admin)):
    from app.database import SessionLocal
    from app.models import User as UserModel, Wallet, Transaction
    session = SessionLocal()
    try:
        total_users = session.query(UserModel).count()
        total_wallets = session.query(Wallet).count()
        total_transactions = session.query(Transaction).count()
        total_volume = session.query(Transaction).with_entities(
            __import__('sqlalchemy').func.sum(Transaction.amount)
        ).scalar() or 0.0
        completed = session.query(Transaction).filter(Transaction.status == "SUCCESS").count()
        pending = session.query(Transaction).filter(Transaction.status == "PENDING").count()
        return {
            "total_users": total_users,
            "total_wallets": total_wallets,
            "total_transactions": total_transactions,
            "total_volume_usd": round(float(total_volume), 2),
            "completed_transactions": completed,
            "pending_transactions": pending,
        }
    finally:
        session.close()

@app.get("/api/admin/users")
def admin_list_users(admin_id: str = Depends(require_admin), limit: int = 50, offset: int = 0):
    from app.database import SessionLocal
    from app.models import User as UserModel, Wallet
    session = SessionLocal()
    try:
        users = session.query(UserModel).offset(offset).limit(limit).all()
        result = []
        for u in users:
            wallets = session.query(Wallet).filter(Wallet.user_id == u.user_id).all()
            total_balance = sum(float(w.balance) for w in wallets)
            result.append({
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "phone_number": u.phone_number,
                "region": u.region.name if u.region else "UNSPECIFIED",
                "kyc_status": u.kyc_status.name if u.kyc_status else "UNSPECIFIED",
                "is_admin": bool(u.is_admin),
                "wallet_count": len(wallets),
                "total_balance_usd": total_balance,
            })
        total = session.query(UserModel).count()
        return {"users": result, "total": total, "limit": limit, "offset": offset}
    finally:
        session.close()

@app.get("/api/admin/transactions")
def admin_list_transactions(admin_id: str = Depends(require_admin), limit: int = 50, offset: int = 0):
    from app.database import SessionLocal
    from app.models import Transaction
    session = SessionLocal()
    try:
        txns = session.query(Transaction).order_by(Transaction.timestamp.desc()).offset(offset).limit(limit).all()
        return {"transactions": [{"transaction_id": t.transaction_id, "from_wallet_id": t.from_wallet_id, "to_wallet_id": t.to_wallet_id, "amount": t.amount, "status": t.status, "timestamp": t.timestamp} for t in txns], "total": session.query(Transaction).count()}
    finally:
        session.close()

# ── P-E: WebSocket — Real-time Notifications ───────────────────────────────────
# Active WebSocket connections keyed by user_id
_ws_connections: dict[str, WebSocket] = {}

@app.websocket("/ws/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str, token: str = None):
    """
    Real-time notification socket.
    Client connects with: ws://host/ws/{user_id}?token=<jwt>
    Backend publishes to Redis channel `notifications:{user_id}` on transfer complete.
    """
    # Validate token from query param
    token = websocket.query_params.get("token", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("user_id") != user_id:
            await websocket.close(code=1008)
            return
    except jwt.PyJWTError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _ws_connections[user_id] = websocket

    # Subscribe to Redis pub/sub channel for this user
    redis_async = None
    pubsub = None
    try:
        redis_async = aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = redis_async.pubsub()
        await pubsub.subscribe(f"notifications:{user_id}")

        # Send welcome ping
        await websocket.send_json({"event": "connected", "user_id": user_id})

        # Polling loop: listen for Redis messages + keep-alive
        while True:
            try:
                message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0)
                if message and message.get("type") == "message":
                    await websocket.send_text(message["data"])
            except asyncio.TimeoutError:
                # Keep-alive ping every second timeout
                try:
                    await websocket.send_json({"event": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break
            except Exception:
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error for {user_id}: {e}")
    finally:
        _ws_connections.pop(user_id, None)
        if pubsub:
            try:
                await pubsub.unsubscribe(f"notifications:{user_id}")
                await pubsub.close()
            except Exception:
                pass
        if redis_async:
            try:
                await redis_async.aclose()
            except Exception:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
