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
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
import hmac
import hashlib

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

# ── WAF Middleware ─────────────────────────────────────────────────────────────
SQLI_PATTERN = re.compile(r"(?i)(UNION.*SELECT|SELECT.*FROM|INSERT.*INTO|UPDATE.*SET|DELETE.*FROM|DROP.*TABLE|EXEC.*xp_cmdshell|--|\bOR\b.*=)")
XSS_PATTERN = re.compile(r"(?i)(<script>|javascript:|onerror=|onload=|eval\()")

class WafMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        req = Request(scope, receive)

        # 1. Check Query Params
        query_string = req.url.query
        if SQLI_PATTERN.search(query_string) or XSS_PATTERN.search(query_string):
            from fastapi.responses import JSONResponse
            res = JSONResponse(status_code=403, content={"detail": "WAF Blocked: Malicious query parameters detected."})
            return await res(scope, receive, send)

        # 2. Check Body Payload Data (Interceptor trick for ASGI)
        body_bytes = b""
        more_body = True
        
        async def receive_wrapper() -> Message:
            nonlocal body_bytes, more_body
            if more_body:
                message = await receive()
                body_bytes += message.get("body", b"")
                more_body = message.get("more_body", False)
                return message
            return {"type": "http.request", "body": b"", "more_body": False}
        
        # Read the entire body up front
        while more_body:
            message = await receive()
            body_bytes += message.get("body", b"")
            more_body = message.get("more_body", False)

        decoded_body = body_bytes.decode('utf-8', errors='ignore')
        
        if SQLI_PATTERN.search(decoded_body) or XSS_PATTERN.search(decoded_body):
            from fastapi.responses import JSONResponse
            res = JSONResponse(status_code=403, content={"detail": "WAF Blocked: Malicious payload detected."})
            return await res(scope, receive, send)
            
        # 3. HMAC Signature Verification (if it's a mutating request)
        if req.method in ["POST", "PUT", "PATCH"] and body_bytes:
            client_sig = req.headers.get("X-Signature")
            if not client_sig:
                from fastapi.responses import JSONResponse
                return await JSONResponse(status_code=403, content={"detail": "Missing X-Signature header for payload integrity."})(scope, receive, send)
            
            # Recompute signature
            expected_sig = hmac.new(
                SECRET_KEY.encode('utf-8'), 
                body_bytes, 
                hashlib.sha256
            ).hexdigest()

            # Time-constant compare
            if not hmac.compare_digest(client_sig, expected_sig):
                from fastapi.responses import JSONResponse
                return await JSONResponse(status_code=403, content={"detail": "Payload signature mismatch. Tampering detected."})(scope, receive, send)

        # Re-emit the read body for the actual handler
        async def receive_re_emit() -> Message:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        await self.app(scope, receive_re_emit, send)

app.add_middleware(WafMiddleware)

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
    # Try mTLS with client cert first, then fall back to plain TLS
    try:
        from app.security.tls import get_channel_credentials
        channel = grpc.secure_channel(GRPC_HOST, get_channel_credentials())
        print("Gateway: mTLS channel established (client cert + CA)")
    except Exception as e:
        print(f"Gateway: mTLS cert load failed ({e}), using plain TLS")
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

FX_CACHE_TTL = 300  # 5 minutes
POLICY_CACHE_TTL = 600  # 10 minutes

# Default compliance policy rules (cached in Redis on first request)
_DEFAULT_POLICIES = {
    "version": "1.0",
    "transfer_limits_usd": {
        "per_transaction": 10000.0,
        "daily": 50000.0,
        "monthly": 200000.0,
    },
    "geo_fencing": {
        "blocked_regions": [],
        "high_risk_regions": ["UNSPECIFIED"],
        "require_kyc_above_usd": 1000.0,
    },
    "rate_limiting": {
        "requests_per_minute": int(os.environ.get("RATE_LIMIT_RPM", "120")),
    },
    "kyc": {
        "auto_approve_below_usd": 500.0,
        "manual_review_above_usd": 5000.0,
    },
}

def _get_cached_fx_rates():
    """Return FX rate matrix from Redis cache (5 min TTL) or compute live."""
    CACHE_KEY = "fx:rates"
    if _redis_sync:
        try:
            cached = _redis_sync.get(CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
    # Compute fresh rates
    rates = {}
    for fc, fn in CURRENCY_NAMES.items():
        rates[fn] = {
            CURRENCY_NAMES[tc]: round(FX_RATES_USD_BASE[tc] / FX_RATES_USD_BASE[fc], 6)
            for tc in CURRENCY_NAMES
        }
    payload = {"rates": rates, "base": "USD", "updated_at": int(time.time()), "cached": False}
    if _redis_sync:
        try:
            _redis_sync.setex(CACHE_KEY, FX_CACHE_TTL, json.dumps(payload))
            payload["cached"] = False  # first write — actually fresh
        except Exception:
            pass
    return payload

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

class ExecuteNLRequest(BaseModel):
    command: str

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

@app.get("/api/users/{user_id}/kyc-credential")
def get_kyc_credential(user_id: str, token_data: dict = Depends(get_token_data)):
    import datetime
    import uuid
    # Verify authorization
    if token_data["user_id"] != user_id:
        db_user = _db_get_user(token_data["user_id"])
        if not db_user or not db_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this credential")
            
    target_user = _db_get_user(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not target_user.did:
        raise HTTPException(status_code=400, detail="User does not have a registered DID")
        
    issuer_did = "did:superapp:admin"
    
    vc_payload = {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1"
        ],
        "id": f"http://superapp.internal/credentials/{uuid.uuid4()}",
        "type": ["VerifiableCredential", "KycCredential"],
        "issuer": issuer_did,
        "issuanceDate": datetime.datetime.utcnow().isoformat() + "Z",
        "credentialSubject": {
            "id": target_user.did,
            "kycStatus": target_user.kyc_status.name,
            "region": target_user.region.name
        }
    }
    
    # Generate JWT proof
    token = jwt.encode({"vc": vc_payload, "iss": issuer_did, "sub": target_user.did}, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "verifiableCredential": vc_payload,
        "jwt": token,
        "status": "ISSUED"
    }

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
    """Returns FX rate matrix, served from Redis cache (5 min TTL)."""
    return _get_cached_fx_rates()

@app.get("/api/policies")
def get_policies():
    """Returns active compliance and policy rules (Redis-cached, 10 min TTL)."""
    CACHE_KEY = "policies:active"
    if _redis_sync:
        try:
            cached = _redis_sync.get(CACHE_KEY)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                return data
        except Exception:
            pass
    payload = {**_DEFAULT_POLICIES, "cached": False, "retrieved_at": int(time.time())}
    if _redis_sync:
        try:
            _redis_sync.setex(CACHE_KEY, POLICY_CACHE_TTL, json.dumps(payload))
        except Exception:
            pass
    return payload

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
@app.post("/api/ai/execute")
def execute_ai_command(req: ExecuteNLRequest, user_id: str = Depends(get_current_user)):
    from app.services.ai_orchestrator import execute_nl_command
    from app.database import SessionLocal
    from app.models import Wallet
    
    intent = execute_nl_command(req.command)
    action = intent.get("action")
    payload = intent.get("payload", {})
    
    if action == "unknown":
        raise HTTPException(status_code=400, detail="Command not understood.")
        
    session = SessionLocal()
    try:
        # Resolve user's primary wallet USD
        user_wallet = session.query(Wallet).filter(Wallet.user_id == user_id, Wallet.currency == 1).first()
        if not user_wallet:
             # Just fallback to any first wallet
             user_wallet = session.query(Wallet).filter(Wallet.user_id == user_id).first()
             
        if not user_wallet:
            raise HTTPException(status_code=400, detail="You do not have a registered wallet.")

        if action == "transfer":
            amount = payload.get("amount")
            target = payload.get("to_target")
            
            # Map to TransferFunds Request
            transfer_req = TransferRequest(
                from_wallet_id=user_wallet.wallet_id,
                to_phone_number=target if target.startswith('+') else None,
                to_wallet_id=target if not target.startswith('+') else None,
                amount=amount
            )
            
            # Re-use existing transfer function locally
            try:
                res = transfer_funds(transfer_req, user_id)
                return {"success": True, "message": f"Successfully executed intent: Transferred {amount} to {target}", "transaction": res}
            except HTTPException as e:
                return {"success": False, "message": f"Failed to execute intent: {str(e.detail)}"}
                
        elif action == "check_balance":
            res = get_balance(user_wallet.wallet_id, user_id)
            return {"success": True, "message": f"Successfully executed intent: Balance is {res['balance']} {res['currency']}"}
            
    finally:
         session.close()
         
    return {"success": False, "message": "Intent action not fully implemented by gateway mapping"}

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

# ── Phase 16: WebAuthn / Passkeys ─────────────────────────────────────────────
class WebAuthnRegisterBeginRequest(BaseModel):
    label: str = "My Passkey"

class WebAuthnLoginBeginRequest(BaseModel):
    email: str

class WebAuthnLoginCompleteRequest(BaseModel):
    assertion: dict
    challenge_email: str  # email used to look up the user for sign_count update

@app.post("/api/auth/webauthn/register/begin")
def webauthn_register_begin(
    req: WebAuthnRegisterBeginRequest,
    token_data: dict = Depends(get_token_data),
):
    """Generate a WebAuthn credential creation challenge (auth required)."""
    from app.services.webauthn_service import begin_registration
    from app.database import SessionLocal
    from app.models import User as UserModel
    user_id = token_data["user_id"]
    session = SessionLocal()
    try:
        user = session.query(UserModel).filter(UserModel.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        options = begin_registration(
            user_id=user_id,
            user_name=user.email,
            user_display_name=user.name or user.email,
        )
        return options
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/auth/webauthn/register/complete", status_code=201)
def webauthn_register_complete(
    credential: dict,
    label: str = "My Passkey",
    token_data: dict = Depends(get_token_data),
):
    """Verify attestation and store the new passkey credential."""
    from app.services.webauthn_service import complete_registration
    user_id = token_data["user_id"]
    try:
        cred = complete_registration(user_id=user_id, credential_json=credential, label=label)
        return {
            "success": True,
            "credential_id": cred.credential_id,
            "label": cred.label,
            "created_at": cred.created_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/webauthn/login/begin")
def webauthn_login_begin(req: WebAuthnLoginBeginRequest):
    """Generate an assertion challenge for a passkey login (public endpoint)."""
    from app.services.webauthn_service import begin_authentication
    from app.database import SessionLocal
    from app.models import User as UserModel
    session = SessionLocal()
    try:
        user = session.query(UserModel).filter(UserModel.email == req.email).first()
        user_id = user.user_id if user else None
        options = begin_authentication(user_id=user_id)
        return options
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/auth/webauthn/login/complete")
def webauthn_login_complete(req: WebAuthnLoginCompleteRequest):
    """Verify the passkey assertion and issue a JWT token."""
    from app.services.webauthn_service import complete_authentication
    from app.database import SessionLocal
    from app.models import User as UserModel
    try:
        user_id = complete_authentication(assertion_json=req.assertion)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Issue JWT using the same logic as /api/login
    session = SessionLocal()
    try:
        user = session.query(UserModel).filter(UserModel.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        token = jwt.encode(
            {"user_id": user_id, "email": user.email},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        return {
            "token": token,
            "user": {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
                "is_admin": bool(user.is_admin),
                "auth_method": "passkey",
            },
        }
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
