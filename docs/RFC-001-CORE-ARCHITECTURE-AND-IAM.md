# RFC-001: Global Identity, Access Management (IAM), and Base Architecture

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Last Modified:** 2026-03-27  
> **Target Audience:** Engineering Teams, Security, Compliance, Infrastructure  
> **Supersedes:** N/A

---

## 1. Abstract

This RFC defines the foundational architecture for the Global Genesis Super App — a multi-region, multi-tenant platform serving the **United States**, **European Union**, and **India**. It specifies the global system topology, unified Identity and Access Management (IAM) system, authentication flows, and the data architecture required to operate under three distinct regulatory regimes (CCPA, GDPR, DPDP/RBI) simultaneously.

---

## 2. Motivation

The Super App must function as a single user experience while respecting the sovereignty boundaries of each market. A user in Munich, a user in Mumbai, and a user in Manhattan must all see the same "app," but their data, KYC verification, payment rails, and privacy rights are governed by entirely different legal frameworks. The architecture must be regulation-native from day zero — not bolted on as an afterthought.

### 2.1. Existing System Baseline

The current Global Genesis codebase already implements:

| Component | Current State | RFC Target |
|---|---|---|
| Backend | Python gRPC servers per region (US `:50051`, EU `:50052`, IN `:50053`) | Formalize as independent deployments on EKS per-region |
| Gateway | Single FastAPI BFF translating REST → gRPC | Multi-region gateway fleet behind global LB |
| IAM | JWT-based auth, WebAuthn/Passkey support, basic KYC enum | Full federated IAM with region-specific KYC orchestration |
| Database | SQLite (dev) / CockroachDB (prod target) | Geo-sharded CockroachDB with data residency fencing |
| Service Mesh | Istio with mTLS, SPIFFE IDs, AuthorizationPolicies | Extend to cross-cluster mesh for multi-region |
| IaC | Terraform AWS EKS + VPC modules | Multi-cloud (AWS us-east-1, AWS eu-west-1, AWS ap-south-1) |

---

## 3. System Topology

### 3.1. Global Region Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GLOBAL CONTROL PLANE                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ DNS (Route53 │  │ Global CDN   │  │ Config Store (Consul)    │  │
│  │ / CloudFlare)│  │ (CloudFront) │  │ Feature Flags (LaunchD.) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
└─────────┼────────────────┼───────────────────────┼──────────────────┘
          │                │                       │
    ┌─────▼─────┐    ┌─────▼─────┐          ┌─────▼─────┐
    │  US-EAST-1│    │EU-WEST-1  │          │AP-SOUTH-1 │
    │  (Virginia)│   │(Ireland)  │          │(Mumbai)   │
    ├───────────┤    ├───────────┤          ├───────────┤
    │ EKS       │    │ EKS       │          │ EKS       │
    │ ┌───────┐ │    │ ┌───────┐ │          │ ┌───────┐ │
    │ │Gateway│ │    │ │Gateway│ │          │ │Gateway│ │
    │ │Fleet  │ │    │ │Fleet  │ │          │ │Fleet  │ │
    │ └───┬───┘ │    │ └───┬───┘ │          │ └───┬───┘ │
    │ ┌───▼───┐ │    │ ┌───▼───┐ │          │ ┌───▼───┐ │
    │ │UserSvc│ │    │ │UserSvc│ │          │ │UserSvc│ │
    │ │WltSvc │ │    │ │WltSvc │ │          │ │WltSvc │ │
    │ │PmtSvc │ │    │ │PmtSvc │ │          │ │PmtSvc │ │
    │ └───┬───┘ │    │ └───┬───┘ │          │ └───┬───┘ │
    │ ┌───▼───┐ │    │ ┌───▼───┐ │          │ ┌───▼───┐ │
    │ │CRDB   │ │    │ │CRDB   │ │          │ │CRDB   │ │
    │ │Node   │ │    │ │Node   │ │          │ │Node   │ │
    │ └───────┘ │    │ └───────┘ │          │ └───────┘ │
    └───────────┘    └───────────┘          └───────────┘
```

### 3.2. Global Load Balancing Strategy

**DNS-Level Routing (Layer 0):**

| Provider | Role | Policy |
|---|---|---|
| AWS Route 53 | Primary DNS | Geolocation routing policy: US IPs → `us-east-1`, EU IPs → `eu-west-1`, India IPs → `ap-south-1` |
| CloudFlare | DDoS + WAF | Proxy mode, rate limiting at edge (OWASP CRS), bot detection |
| Failover | Active-Active | Health checks every 10s. If `ap-south-1` fails, India traffic routes to `eu-west-1` (lowest latency fallback per undersea cable topology) |

**Application-Level Routing (Layer 7):**

```yaml
# Istio VirtualService — region-aware traffic split
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: gateway-vs
  namespace: superapp-prod
spec:
  hosts:
    - "api.superapp.global"
  http:
    - match:
        - headers:
            x-user-region:
              exact: "INDIA"
      route:
        - destination:
            host: gateway.superapp-in.svc.cluster.local
            port:
              number: 8000
    - match:
        - headers:
            x-user-region:
              exact: "EU"
      route:
        - destination:
            host: gateway.superapp-eu.svc.cluster.local
            port:
              number: 8000
    - route:
        - destination:
            host: gateway.superapp-us.svc.cluster.local
            port:
              number: 8000
```

### 3.3. API Gateway Architecture

Each region runs an independent FastAPI gateway fleet (extending the existing `gateway/main.py`). The gateway is the sole ingress point for all client traffic.

**Gateway Responsibilities:**

1. **Protocol Translation:** REST/JSON → gRPC Protobuf (existing)
2. **Authentication:** JWT validation, token refresh, WebAuthn challenge proxying
3. **Region Resolution:** Extracts `x-user-region` from JWT claims or GeoIP lookup, attaches as gRPC metadata
4. **Rate Limiting:** Redis sliding-window (existing: 120 req/min/IP)
5. **Request Enrichment:** Attaches OpenTelemetry trace context, correlation IDs
6. **Schema Validation:** Pydantic request models with per-region field requirements
7. **Circuit Breaking:** Hystrix-pattern circuit breakers per downstream service

**Gateway Fleet Sizing (per region):**

| Metric | Value |
|---|---|
| Pods | 3 (min) — 20 (max) via HPA |
| HPA Target | CPU 60%, Request latency P95 < 200ms |
| Pod Resources | 500m CPU / 512Mi RAM request, 2 CPU / 2Gi RAM limit |
| Health Check | `/health/ready` (liveness), `/health/live` (readiness) |

### 3.4. CDN Strategy

```
Client Request
     │
     ▼
CloudFront Edge (PoP: 400+ locations)
     │
     ├── Static Assets (JS bundles, CSS, images)
     │   └── Cache-Control: public, max-age=31536000, immutable
     │   └── Content-Hash based invalidation via CI/CD
     │
     ├── API Responses (selective caching)
     │   └── GET /api/fx/rates → Cache 60s (Vary: Accept-Language)
     │   └── GET /api/policies → Cache 600s
     │   └── All POST/PUT/DELETE → No cache, pass-through
     │
     └── Mini-App Bundles
         └── Per-version cache: /mini-apps/wallet/v2.3.1/bundle.js
         └── Cache-Control: public, max-age=86400
```

---

## 4. Unified IAM Architecture

### 4.1. Design Principles

1. **Single Identity, Multiple Profiles:** A user has ONE global `user_id` (UUID v4) but may have region-specific KYC profiles, compliance statuses, and data residency constraints.
2. **Credential Agnostic:** The identity layer supports password, WebAuthn/Passkey (existing), OAuth2 social login, and region-specific login methods (OTP-only for India UPI linking).
3. **Zero-Trust by Default:** Every inter-service call is authenticated via mTLS (existing Istio SPIFFE) and authorized via RBAC/ABAC policies.

### 4.2. KYC Orchestration by Region

The existing `KycStatus` enum (`UNSPECIFIED`, `PENDING`, `VERIFIED`, `FAILED`) is extended to a full KYC orchestration system:

```
┌──────────────────────────────────────────────────────────────┐
│                    KYC ORCHESTRATOR SERVICE                   │
│                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────────────┐     │
│  │ US KYC   │     │ EU KYC   │     │ India KYC        │     │
│  │ Provider │     │ Provider │     │ Provider         │     │
│  ├──────────┤     ├──────────┤     ├──────────────────┤     │
│  │ SSN      │     │ eIDAS    │     │ Aadhaar          │     │
│  │ verify   │     │ cert     │     │ e-KYC (UIDAI)    │     │
│  │ OFAC     │     │ validate │     │ Video KYC        │     │
│  │ screening│     │ PEP/sanc.|     │ PAN verify       │     │
│  │ Driver's │     │ National │     │ Bank stmt verify │     │
│  │ License  │     │ ID card  │     │                  │     │
│  └──────────┘     └──────────┘     └──────────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            INTERNAL RISK SCORING ENGINE               │   │
│  │  Input: KYC result + transaction pattern + region     │   │
│  │  Output: risk_score (0.0 – 1.0)                       │   │
│  │  Threshold: >= 0.7 → manual review queue              │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Region-Specific KYC Requirements:**

| Field | US | EU | India |
|---|---|---|---|
| **Primary ID** | SSN (last 4 for basic, full for banking) | National ID / Passport (eIDAS Level of Assurance: Substantial) | Aadhaar number (12-digit, UIDAI verified) |
| **Secondary ID** | Driver's License / State ID | Utility bill (proof of address, < 3 months old) | PAN card (10-char alphanumeric) |
| **Liveness Check** | Selfie + document match (Jumio) | Video identification (eIDAS LoA High) | Video KYC per RBI Master Direction 2020 |
| **Sanctions Screening** | OFAC SDN List + FinCEN | EU consolidated sanctions list | RBI debarment list + FATF |
| **Re-verification** | Annual for full banking | GDPR: upon data retention review | As per RBI norms (transaction-triggered) |
| **Data Storage** | `us-east-1` encrypted at rest | `eu-west-1` ONLY. GDPR Art. 5(1)(e) | `ap-south-1` ONLY. RBI data localization circular 2018 |

### 4.3. User Identity Schema

Extending the existing `User` model in `app/models.py`:

```python
class User(Base):
    """
    Central user identity. Stores ONLY non-PII global metadata.
    PII is stored in region-local tables (see UserPII).
    """
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email_hash = Column(String, unique=True, index=True)  # SHA-256 hash for lookup
    created_at = Column(Float, default=lambda: time.time())
    primary_region = Column(SAEnum(Region), nullable=False)
    account_status = Column(SAEnum(AccountStatus), default=AccountStatus.ACTIVE)
    did = Column(String, unique=True, index=True, nullable=True)  # W3C DID

    # Global replicated — non-PII
    wallets = relationship("Wallet", back_populates="owner")
    passkeys = relationship("WebAuthnCredential", back_populates="owner")


class UserPII(Base):
    """
    Region-LOCAL PII storage. This table is NEVER replicated across regions.
    Each region's CockroachDB node stores only its own users' PII.
    Geo-fenced via CockroachDB zone configs.
    """
    __tablename__ = "user_pii"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    region = Column(SAEnum(Region), nullable=False)

    # Encrypted at rest (AES-256-GCM via app-level envelope encryption)
    encrypted_email = Column(LargeBinary, nullable=False)
    encrypted_name = Column(LargeBinary, nullable=False)
    encrypted_phone = Column(LargeBinary, nullable=False)
    encrypted_government_id = Column(LargeBinary, nullable=True)  # SSN/Aadhaar/NationalID

    # KYC
    kyc_status = Column(SAEnum(KycStatus), default=KycStatus.PENDING)
    kyc_provider_ref = Column(String, nullable=True)  # External KYC provider reference
    kyc_verified_at = Column(Float, nullable=True)
    kyc_expiry_at = Column(Float, nullable=True)
    risk_score = Column(Float, default=0.0)

    # GDPR-specific
    consent_marketing = Column(Boolean, default=False)
    consent_analytics = Column(Boolean, default=False)
    data_retention_expiry = Column(Float, nullable=True)  # GDPR Art. 17 automation
    erasure_requested_at = Column(Float, nullable=True)

    # Audit
    last_modified_at = Column(Float)
    last_modified_by = Column(String)  # admin user_id or "SYSTEM"
```

### 4.4. CockroachDB Geo-Fencing Configuration

```sql
-- Create database with locality-aware zone configs
ALTER DATABASE superapp_global CONFIGURE ZONE USING
    constraints = '{"+region=us-east-1": 1, "+region=eu-west-1": 1, "+region=ap-south-1": 1}',
    num_replicas = 5,
    lease_preferences = '[[+region=us-east-1]]';

-- Global table: replicated everywhere (non-PII only)
ALTER TABLE users CONFIGURE ZONE USING
    constraints = '{"+region=us-east-1": 1, "+region=eu-west-1": 1, "+region=ap-south-1": 1}',
    num_replicas = 5;

-- PII tables: geo-fenced to specific regions
-- EU PII NEVER leaves eu-west-1
ALTER PARTITION eu OF TABLE user_pii CONFIGURE ZONE USING
    constraints = '[+region=eu-west-1]',
    num_replicas = 3,
    lease_preferences = '[[+region=eu-west-1]]';

-- India PII NEVER leaves ap-south-1 (RBI mandate)
ALTER PARTITION india OF TABLE user_pii CONFIGURE ZONE USING
    constraints = '[+region=ap-south-1]',
    num_replicas = 3,
    lease_preferences = '[[+region=ap-south-1]]';

-- US PII stays in us-east-1
ALTER PARTITION us OF TABLE user_pii CONFIGURE ZONE USING
    constraints = '[+region=us-east-1]',
    num_replicas = 3,
    lease_preferences = '[[+region=us-east-1]]';

-- Partition by region column
ALTER TABLE user_pii PARTITION BY LIST (region) (
    PARTITION us VALUES IN ('US'),
    PARTITION eu VALUES IN ('EU'),
    PARTITION india VALUES IN ('INDIA')
);
```

---

## 5. Authentication Flows

### 5.1. OAuth2.0/OIDC Token Architecture

**Token Types and Lifetimes:**

| Token | Type | Lifetime | Storage | Scope |
|---|---|---|---|---|
| Access Token | JWT (RS256) | 15 minutes | Client memory ONLY | API access |
| Refresh Token | Opaque (UUID) | 30 days | HttpOnly Cookie + server-side in Redis | Token renewal |
| ID Token | JWT (RS256) | 15 minutes | Client memory | User profile claims |
| Session Token | Opaque (UUID) | 24 hours | Redis cluster | Session state |

**JWT Claims Structure:**

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-2026-q1-us-east-1"
  },
  "payload": {
    "iss": "https://auth.superapp.global",
    "sub": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "aud": ["https://api.superapp.global"],
    "exp": 1711540200,
    "iat": 1711539300,
    "nbf": 1711539300,
    "jti": "tok_unique-nonce-value",
    "region": "INDIA",
    "kyc_level": "VERIFIED",
    "scopes": ["wallet:read", "wallet:transfer", "profile:read"],
    "mfa_verified": true,
    "device_fingerprint_hash": "sha256:abcdef..."
  }
}
```

### 5.2. Authentication Sequence (Standard Login)

```
┌────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐
│ Client │    │  CDN/LB │    │ Gateway  │    │ AuthSvc  │    │ UserStore │
│ (App)  │    │  Edge   │    │ (FastAPI)│    │ (gRPC)   │    │ (CRDB)    │
└───┬────┘    └────┬────┘    └────┬─────┘    └────┬─────┘    └─────┬─────┘
    │              │              │               │                │
    │ POST /auth/login            │               │                │
    │ {email, password}           │               │                │
    │─────────────►│              │               │                │
    │              │──────────────►│               │                │
    │              │              │               │                │
    │              │              │  GeoIP lookup  │                │
    │              │              │  → region=IN   │                │
    │              │              │               │                │
    │              │              │ AuthenticateUser(email,pass,region)
    │              │              │──────────────►│                │
    │              │              │               │                │
    │              │              │               │ SELECT user_id │
    │              │              │               │ FROM users     │
    │              │              │               │ WHERE email_hash=│
    │              │              │               │ SHA256(email)  │
    │              │              │               │───────────────►│
    │              │              │               │◄───────────────│
    │              │              │               │                │
    │              │              │               │ SELECT * FROM  │
    │              │              │               │ user_pii WHERE │
    │              │              │               │ user_id=? AND  │
    │              │              │               │ region='INDIA' │
    │              │              │               │───────────────►│
    │              │              │               │◄───────────────│
    │              │              │               │                │
    │              │              │               │ bcrypt.verify  │
    │              │              │               │ (password,hash)│
    │              │              │               │                │
    │              │              │               │ Generate tokens│
    │              │              │               │ (access+refresh│
    │              │              │               │  +id_token)    │
    │              │              │◄──────────────│                │
    │              │              │               │                │
    │              │              │ Store refresh  │               │
    │              │              │ token in Redis │               │
    │              │              │ (region-local) │               │
    │              │              │               │                │
    │              │◄─────────────│               │                │
    │◄─────────────│              │               │                │
    │              │              │               │                │
    │ 200 OK       │              │               │                │
    │ {access_token, id_token}    │               │                │
    │ Set-Cookie: refresh_token   │               │                │
    │ (HttpOnly, Secure, SameSite=Strict)         │                │
```

### 5.3. Cross-Region Session Replication

Sessions are **NOT** replicated globally by default. Each region maintains its own Redis cluster for session state. This is a deliberate design decision:

**Rationale:**
- GDPR Article 44+: Session data containing behavioral signals cannot be transferred outside the EU without Standard Contractual Clauses.
- RBI data localization: Session tokens referencing Indian financial data must stay in India.
- Latency: Cross-ocean Redis replication adds 120-200ms (unacceptable for auth).

**Cross-Region Access Pattern:**

When a user physically moves from one region to another (e.g., traveling from India to the US), the following occurs:

```
1. Client connects from US IP → DNS routes to us-east-1 gateway
2. Gateway receives JWT → validates signature (RSA public key is globally replicated)
3. JWT contains claim: region=INDIA
4. Gateway issues cross-region gRPC call to ap-south-1 AuthService:
   → ValidateSession(session_id, user_id)
5. If valid: Gateway creates LOCAL session in us-east-1 Redis
   → Scoped: read-only access to non-financial features
   → Full financial ops still route to ap-south-1
6. JWT refreshed with additional claim: roaming_region=US
```

### 5.4. Key Rotation Strategy

```yaml
# Key rotation managed via HashiCorp Vault
# Path: secret/superapp/jwt-keys/

rotation_policy:
  algorithm: RS256
  key_size: 4096
  rotation_interval: 90d
  overlap_period: 7d  # Old key valid for 7 days after rotation
  
  regional_keys:
    us-east-1:
      current_kid: "key-2026-q1-us-east-1"
      vault_path: "transit/keys/jwt-us-east-1"
    eu-west-1:
      current_kid: "key-2026-q1-eu-west-1"
      vault_path: "transit/keys/jwt-eu-west-1"
    ap-south-1:
      current_kid: "key-2026-q1-ap-south-1"
      vault_path: "transit/keys/jwt-ap-south-1"

  jwks_endpoint: "https://auth.superapp.global/.well-known/jwks.json"
  # JWKS contains ALL active keys from ALL regions
  # Cached by gateways for 300s with background refresh
```

---

## 6. Data Architecture: CAP Theorem Trade-Offs

### 6.1. Data Classification Matrix

| Data Category | Consistency | Availability | Partition Tolerance | Database | Replication |
|---|---|---|---|---|---|
| **User Identity (non-PII)** | Eventual (5s) | High | Yes | CockroachDB | Global 5-replica |
| **User PII** | Strong | Medium | Yes | CockroachDB | Region-locked 3-replica |
| **Wallet Balances** | Strong | Medium | Yes | CockroachDB | Region-local with cross-region reads |
| **Transactions** | Strong | Medium | Yes | CockroachDB | Region-local, async replicated for analytics |
| **Session State** | Eventual (1s) | High | Yes | Redis Cluster | Region-local only |
| **FX Rates** | Eventual (60s) | High | Yes | Redis | Global broadcast |
| **Analytics Events** | Eventual (minutes) | High | Yes | Kafka → ClickHouse | Kafka MirrorMaker cross-region |
| **Audit Logs** | Strong | Medium | Yes | CockroachDB + S3 | Append-only, region-local, archived to S3 |

### 6.2. CockroachDB Cluster Topology

```
Region: us-east-1 (3 nodes)          Region: eu-west-1 (3 nodes)
┌─────────┐ ┌─────────┐ ┌─────────┐  ┌─────────┐ ┌─────────┐ ┌─────────┐
│ CRDB-US │ │ CRDB-US │ │ CRDB-US │  │ CRDB-EU │ │ CRDB-EU │ │ CRDB-EU │
│ Node 1  │ │ Node 2  │ │ Node 3  │  │ Node 1  │ │ Node 2  │ │ Node 3  │
│ AZ: 1a  │ │ AZ: 1b  │ │ AZ: 1c  │  │ AZ: 1a  │ │ AZ: 1b  │ │ AZ: 1c  │
└────┬────┘ └────┬────┘ └────┬────┘  └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │            │           │           │
     └───────────┼───────────┘            └───────────┼───────────┘
                 │                                    │
                 │        Raft consensus              │
                 │◄──────────────────────────────────►│
                 │                                    │
                                  │
                     Region: ap-south-1 (3 nodes)
                     ┌─────────┐ ┌─────────┐ ┌─────────┐
                     │ CRDB-IN │ │ CRDB-IN │ │ CRDB-IN │
                     │ Node 1  │ │ Node 2  │ │ Node 3  │
                     │ AZ: 1a  │ │ AZ: 1b  │ │ AZ: 1c  │
                     └─────────┘ └─────────┘ └─────────┘
```

**CockroachDB Configuration:**

```sql
-- Cluster settings for global deployment
SET CLUSTER SETTING kv.range_merge.queue_enabled = true;
SET CLUSTER SETTING server.time_until_store_dead = '5m0s';
SET CLUSTER SETTING kv.rangefeed.enabled = true;  -- Required for changefeeds

-- Topology: each node tagged with locality
-- cockroach start --locality=region=us-east-1,zone=us-east-1a
-- cockroach start --locality=region=eu-west-1,zone=eu-west-1a
-- cockroach start --locality=region=ap-south-1,zone=ap-south-1a
```

---

## 7. Compliance Enforcement Architecture

### 7.1. Per-Region Compliance Matrix

| Requirement | GDPR (EU) | CCPA (US) | DPDP/RBI (India) |
|---|---|---|---|
| **Right to Erasure** | MANDATORY. Art. 17. 30-day response. | Optional. "Right to Delete" on request. | DPDP Sec. 12. "Right to Erasure" | 
| **Data Portability** | MANDATORY. Art. 20. JSON/CSV export. | Not required. | DPDP Sec. 13. Machine-readable format. |
| **Consent Granularity** | Per-purpose consent required. | Opt-out model. | Opt-in model per DPDP. |
| **Data Localization** | Data may leave EU with SCCs/BCRs. | No federal requirement. | **ABSOLUTE.** RBI mandates ALL payment data stored in India. |
| **Breach Notification** | 72 hours to DPA. | "Without unreasonable delay." | 72 hours to CERT-In. |
| **DPO Requirement** | Mandatory for large-scale processing. | Not required. | Data Fiduciary must appoint. |

### 7.2. Automated Compliance Enforcement

```python
# compliance/enforcement_engine.py

class ComplianceEnforcementEngine:
    """
    Middleware injected into every data-write path.
    Ensures no PII crosses region boundaries.
    """

    REGION_ALLOWED_ZONES = {
        Region.EU: {"eu-west-1"},
        Region.INDIA: {"ap-south-1"},
        Region.US: {"us-east-1", "us-west-2"},  # US allows multi-region within country
    }

    async def validate_write(self, table: str, region: Region, target_zone: str):
        if table in PII_TABLES and target_zone not in self.REGION_ALLOWED_ZONES[region]:
            await self.emit_compliance_violation_event(
                violation_type="DATA_RESIDENCY_BREACH",
                table=table,
                region=region,
                target_zone=target_zone,
            )
            raise DataResidencyViolationError(
                f"Cannot write PII for region {region.name} to zone {target_zone}"
            )

    async def handle_erasure_request(self, user_id: str, region: Region):
        """GDPR Art. 17 / DPDP Sec. 12 erasure pipeline."""
        # 1. Mark user for erasure
        # 2. Kafka event: user.erasure.requested
        # 3. Each service consumer deletes its local data
        # 4. Verify via reconciliation within 30 days
        # 5. Issue compliance certificate
        pass
```

---

## 8. Security Hardening

### 8.1. Encryption Hierarchy

```
┌──────────────────────────────────────────────┐
│              ENVELOPE ENCRYPTION              │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │ Master Key (HSM-backed via AWS KMS) │     │
│  │ One per region, never leaves HSM    │     │
│  └─────────────┬───────────────────────┘     │
│                │ encrypts                    │
│  ┌─────────────▼───────────────────────┐     │
│  │ Data Encryption Key (DEK)           │     │
│  │ Rotated every 24 hours              │     │
│  │ Cached in-memory (max 1 hour)       │     │
│  └─────────────┬───────────────────────┘     │
│                │ encrypts                    │
│  ┌─────────────▼───────────────────────┐     │
│  │ PII Field Values                    │     │
│  │ AES-256-GCM with per-field IV       │     │
│  │ email, name, phone, government_id   │     │
│  └─────────────────────────────────────┘     │
│                                              │
└──────────────────────────────────────────────┘
```

### 8.2. mTLS and Service Identity (Existing + Extension)

The existing Istio mTLS configuration (`kubernetes/istio/peer-authentication.yaml`) is extended:

```yaml
# Strict mTLS for ALL traffic in all Super App namespaces
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: global-strict-mtls
  namespace: istio-system  # Mesh-wide
spec:
  mtls:
    mode: STRICT

# SPIFFE ID format: spiffe://superapp.global/ns/{namespace}/sa/{service-account}
# Cross-cluster: Istio multi-cluster mesh with shared root CA
```

---

## 9. Open Questions

| # | Question | Owner | Deadline |
|---|---|---|---|
| 1 | Should we use CockroachDB Serverless or Dedicated for India (cost vs. control)? | Infra Lead | 2026-04-15 |
| 2 | eIDAS Level of Assurance: Substantial vs. High for financial mini-apps? | Compliance | 2026-04-10 |
| 3 | India Video KYC: Build vs. Buy (DigiLocker API vs. custom)? | Product | 2026-04-20 |
| 4 | Cross-region Kafka: MirrorMaker 2 vs. Confluent Cluster Linking? | Platform | 2026-04-15 |

---

## 10. Appendix: Migration Path from Current State

The existing codebase uses SQLite for local development and has the schema in `app/models.py`. The migration path:

1. **Phase A (Week 1-2):** Split `User` model → `User` (global) + `UserPII` (regional). Alembic migration.
2. **Phase B (Week 3-4):** Deploy CockroachDB 3-node cluster in each region. Run dual-write (SQLite + CRDB) with shadow reads.
3. **Phase C (Week 5-6):** Implement geo-fencing zone configs. Validate PII isolation with integration tests.
4. **Phase D (Week 7-8):** Cut over. Remove SQLite dependency. CockroachDB becomes sole persistence.

---

*End of RFC-001*
