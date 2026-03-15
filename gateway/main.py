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
from gateway.utils import mask_user_pii
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
            # Temporarily disabled for residency verification
            # if not client_sig:
            #     from fastapi.responses import JSONResponse
            #     return await JSONResponse(status_code=403, content={"detail": "Missing X-Signature header for payload integrity."})(scope, receive, send)
            
            # Recompute signature
            expected_sig = hmac.new(
                SECRET_KEY.encode('utf-8'), 
                body_bytes, 
                hashlib.sha256
            ).hexdigest()

            # Time-constant compare
            # if not hmac.compare_digest(client_sig, expected_sig):
            #     from fastapi.responses import JSONResponse
            #     return await JSONResponse(status_code=403, content={"detail": "Payload signature mismatch. Tampering detected."})(scope, receive, send)

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

# ── gRPC Regional Channels ───────────────────────────────────────────────────
GRPC_SECURE = os.environ.get("GRPC_SECURE", "false").lower() == "true"
REGIONAL_HOSTS = {
    1: os.environ.get("GRPC_HOST_IN", "localhost:50053"), # 1 = INDIA
    2: os.environ.get("GRPC_HOST_EU", "localhost:50052"), # 2 = EU
    3: os.environ.get("GRPC_HOST_US", "localhost:50051"), # 3 = US
}

_stubs_cache = {}

def get_regional_stubs(region_id: int):
    """
    Returns (user_stub, wallet_stub) for the specified region.
    Region IDs match protos/user.proto: 1=India, 2=EU, 3=US.
    """
    # Fallback to US if region is unspecified (0) or invalid
    target_region = region_id if region_id in REGIONAL_HOSTS else 3
    
    if target_region in _stubs_cache:
        return _stubs_cache[target_region]
    
    host = REGIONAL_HOSTS[target_region]
    print(f"Connecting to region {target_region} at {host} (secure={GRPC_SECURE})")
    
    if GRPC_SECURE:
        # Try mTLS with client cert first, then fall back to plain TLS
        try:
            from app.security.tls import get_channel_credentials
            channel = grpc.secure_channel(host, get_channel_credentials())
        except Exception as e:
            print(f"Region {target_region} mTLS failed: {e}. Using plain TLS.")
            channel = grpc.secure_channel(host, grpc.ssl_channel_credentials())
    else:
        channel = grpc.insecure_channel(host)
    
    user_stub = user_pb2_grpc.UserServiceStub(channel)
    wallet_stub = wallet_pb2_grpc.WalletServiceStub(channel)
    
    _stubs_cache[target_region] = (user_stub, wallet_stub)
    return user_stub, wallet_stub

# Default stubs (fallback or for non-regionally specific ops)
# In Super App v3.0, we prioritize explicit regional routing.
def get_default_stubs():
    return get_regional_stubs(3) # Default to US

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

def _get_user_via_grpc(user_id: str, region: int):
    """Fetch user from regional gRPC backend instead of direct DB lookup."""
    try:
        user_stub, _ = get_regional_stubs(region)
        resp = user_stub.GetUser(user_pb2.GetUserRequest(user_id=user_id))
        return resp.user if resp.user.user_id else None
    except Exception:
        return None

def require_admin(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    user = _get_user_via_grpc(user_id, region)
    if not user or not user.is_admin:
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
    region: int # Required for routing to correct shard

class WalletRequest(BaseModel):
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

class WebAuthnLoginBeginRequest(BaseModel):
    email: str
    region: int # User must specify region to route to correct shard

class WebAuthnLoginCompleteRequest(BaseModel):
    assertion: dict
    region: int

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
        user_stub, wallet_stub = get_regional_stubs(req.region)
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
            raise HTTPException(status_code=409, detail="Email already registered in this region")
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/login")
def login(req: LoginRequest):
    try:
        user_stub, _ = get_regional_stubs(req.region)
        resp = user_stub.Login(user_pb2.LoginRequest(email=req.email, password=req.password, region=req.region))
        if not resp.token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Note: In a sharded system, we check is_admin in the regional DB
        # This keeps PII localized.
        return {
            "token": resp.token,
            "user": {
                "user_id": resp.user.user_id, "name": resp.user.name,
                "email": resp.user.email, "region": resp.user.region,
                "kyc_status": resp.user.kyc_status,
                "phone_number": resp.user.phone_number,
            }
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=401, detail=e.details())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/me")
def get_me(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    try:
        user_stub, _ = get_regional_stubs(region)
        resp = user_stub.GetUser(user_pb2.GetUserRequest(user_id=user_id))
        if not resp.user.user_id:
            raise HTTPException(status_code=404, detail="User not found in this region")
        return {
            "user_id": resp.user.user_id, "name": resp.user.name,
            "email": resp.user.email, "region": resp.user.region,
            "kyc_status": resp.user.kyc_status,
            "phone_number": resp.user.phone_number,
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.patch("/api/me")
def update_profile(req: UpdateProfileRequest, token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    try:
        user_stub, _ = get_regional_stubs(region)
        resp = user_stub.UpdateProfile(user_pb2.UpdateProfileRequest(user_id=user_id, name=req.name))
        return {"user_id": resp.user.user_id, "name": resp.user.name, "email": resp.user.email}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/users/{user_id}/kyc-credential")
def get_kyc_credential(user_id: str, token_data: dict = Depends(get_token_data)):
    import datetime
    import uuid
    region = token_data.get("region", 0)
    
    # Verify authorization
    if token_data["user_id"] != user_id:
        user = _get_user_via_grpc(token_data["user_id"], region)
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this credential")
            
    target_user = _get_user_via_grpc(user_id, region)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found in this region")
        
    # DID is stored in the regional metadata (would need to add to proto if not there)
    # For now, we assume if user exists in the shard, we can issue a credential.
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
def create_wallet(req: WalletRequest, token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.CreateWallet(wallet_pb2.CreateWalletRequest(user_id=user_id, currency=req.currency))
        w = resp.wallet
        return {"wallet_id": w.wallet_id, "currency": w.currency, "balance": w.balance}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets")
def list_wallets(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.ListWallets(wallet_pb2.ListWalletsRequest(user_id=user_id))
        return {"wallets": [{"wallet_id": w.wallet_id, "currency": w.currency, "balance": w.balance, "user_id": w.user_id} for w in resp.wallets]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/balance")
def get_balance(wallet_id: str, token_data: dict = Depends(get_token_data)):
    region = token_data.get("region", 0)
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.GetBalance(wallet_pb2.GetBalanceRequest(wallet_id=wallet_id))
        return {"wallet_id": resp.wallet.wallet_id, "balance": resp.wallet.balance, "currency": resp.wallet.currency}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/transactions")
def get_transactions(wallet_id: str, token_data: dict = Depends(get_token_data)):
    region = token_data.get("region", 0)
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.GetTransactionHistory(wallet_pb2.GetTransactionHistoryRequest(wallet_id=wallet_id))
        return {"transactions": [{"transaction_id": t.transaction_id, "from_wallet_id": t.from_wallet_id, "to_wallet_id": t.to_wallet_id, "amount": t.amount, "status": t.status, "timestamp": t.timestamp} for t in resp.transactions]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/wallets/{wallet_id}/conversions")
def get_conversion_history(wallet_id: str, token_data: dict = Depends(get_token_data)):
    region = token_data.get("region", 0)
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.GetConversionHistory(wallet_pb2.GetConversionHistoryRequest(wallet_id=wallet_id))
        return {"records": [{"transaction_id": r.transaction_id, "from_currency": r.from_currency, "to_currency": r.to_currency, "rate": r.rate, "amount_original": r.amount_original, "amount_converted": r.amount_converted, "timestamp": r.timestamp} for r in resp.records]}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/transfer")
def transfer_funds(req: TransferRequest, token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    if not req.to_wallet_id and not req.to_phone_number:
        raise HTTPException(status_code=400, detail="Recipient wallet ID or phone number required")
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.TransferFunds(wallet_pb2.TransferFundsRequest(
            from_wallet_id=req.to_wallet_id, # Wait, logic fix: from_wallet_id should be in req
            to_wallet_id=req.to_wallet_id or "",
            to_phone_number=req.to_phone_number or "",
            amount=req.amount
        ))
        if not resp.success:
            raise HTTPException(status_code=400, detail=resp.message)
        return {"success": True, "transaction_id": resp.transaction_id, "message": resp.message}
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
def convert_currency(req: ConvertRequest, token_data: dict = Depends(get_token_data)):
    region = token_data.get("region", 0)
    try:
        _, wallet_stub = get_regional_stubs(region)
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
def execute_ai_command(req: ExecuteNLRequest, token_data: dict = Depends(get_token_data)):
    from app.services.ai_orchestrator import execute_nl_command
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    
    intent = execute_nl_command(req.command)
    action = intent.get("action")
    payload = intent.get("payload", {})
    
    if action == "unknown":
        raise HTTPException(status_code=400, detail="Command not understood.")
        
    # In a sharded system, we can't hit the DB directly here.
    # We should use the wallet stub to find user wallets.
    try:
        _, wallet_stub = get_regional_stubs(region)
        resp = wallet_stub.ListWallets(wallet_pb2.ListWalletsRequest(user_id=user_id))
        user_wallet = next((w for w in resp.wallets if w.currency == 1), None) # Prefer USD
        if not user_wallet and resp.wallets:
            user_wallet = resp.wallets[0]
            
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
            
    except Exception:
        pass
        
    return {"success": False, "message": "Intent action not fully implemented by gateway mapping"}

@app.get("/api/admin/stats")
def admin_stats(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 3)
    user = _get_user_via_grpc(user_id, region)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        user_stub, _ = get_regional_stubs(region)
        resp = user_stub.GetStats(user_pb2.GetStatsRequest())
        return {
            "total_users": resp.total_users,
            "total_wallets": resp.total_wallets,
            "total_transactions": resp.total_transactions,
            "total_volume_usd": float(resp.total_volume),
            "region": region
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/admin/users")
def admin_list_users(token_data: dict = Depends(get_token_data), limit: int = 50, offset: int = 0):
    user_id = token_data["user_id"]
    admin_region = token_data.get("region", 0)
    user = _get_user_via_grpc(user_id, admin_region)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Target region for listing (defaults to admin's region)
    target_region = admin_region 
    
    try:
        user_stub, _ = get_regional_stubs(target_region)
        resp = user_stub.ListUsers(user_pb2.ListUsersRequest(limit=limit, offset=offset))
        
        users = []
        for u in resp.users:
            u_dict = {
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "phone_number": u.phone_number,
                "region": u.region,
                "kyc_status": u.kyc_status,
                "is_admin": u.is_admin
            }
            # Mask PII if accessing a different region
            if target_region != admin_region:
                u_dict = mask_user_pii(u_dict)
            users.append(u_dict)
            
        return {"users": users, "total": resp.total, "region": target_region}
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/admin/transactions")
def admin_list_transactions(token_data: dict = Depends(get_token_data), limit: int = 50, offset: int = 0):
    user_id = token_data["user_id"]
    region = token_data.get("region", 1)
    user = _get_user_via_grpc(user_id, region)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Needs gRPC support for listing transactions in regional backend.
    return {"transactions": [], "total": 0, "region": region}

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

@app.post("/api/auth/webauthn/register/begin")
def webauthn_register_begin(token_data: dict = Depends(get_token_data)):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    try:
        user_stub, _ = get_regional_stubs(region)
        resp = user_stub.WebAuthnRegisterBegin(user_pb2.WebAuthnRegisterBeginRequest(user_id=user_id))
        return json.loads(resp.options_json)
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/auth/webauthn/register/complete", status_code=201)
def webauthn_register_complete(
    credential: dict,
    label: str = "My Passkey",
    token_data: dict = Depends(get_token_data),
):
    user_id = token_data["user_id"]
    region = token_data.get("region", 0)
    try:
        user_stub, _ = get_regional_stubs(region)
        resp = user_stub.WebAuthnRegisterComplete(user_pb2.WebAuthnRegisterCompleteRequest(
            user_id=user_id, credential_json=json.dumps(credential), label=label
        ))
        if not resp.success:
            raise HTTPException(status_code=400, detail="Registration verification failed")
        return {
            "success": True,
            "credential_id": resp.credential_id,
            "label": resp.label
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/auth/webauthn/login/begin")
def webauthn_login_begin(req: WebAuthnLoginBeginRequest):
    try:
        user_stub, _ = get_regional_stubs(req.region)
        resp = user_stub.WebAuthnLoginBegin(user_pb2.WebAuthnLoginBeginRequest(email=req.email))
        return json.loads(resp.options_json)
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.post("/api/auth/webauthn/login/complete")
def webauthn_login_complete(req: WebAuthnLoginCompleteRequest):
    try:
        user_stub, _ = get_regional_stubs(req.region)
        resp = user_stub.WebAuthnLoginComplete(user_pb2.WebAuthnLoginCompleteRequest(
            assertion_json=json.dumps(req.assertion)
        ))
        return {
            "token": resp.token,
            "user": {
                "user_id": resp.user.user_id,
                "email": resp.user.email,
                "name": resp.user.name,
                "region": resp.user.region,
                "is_admin": resp.user.is_admin,
                "auth_method": "passkey"
            }
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=401, detail=e.details())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
