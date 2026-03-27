# 🆔 Module 1: The Core Infrastructure & Identity (IAM)

> **Execution Level:** HIGH-DEPTH (Buildable)  
> **Target Regions:** US (HIPAA/CCPA), EU (GDPR), IN (RBI/DPDP)

---

## 🏗️ 1. The "Host Shell" Architecture
The Host Shell is a **Micro-Frontend (MFE)** container built with **React Native (Expo)**. It uses **Module Federation** to dynamically load "Mini-Apps" (Social, Wallet, etc.) from regional buckets.

### 1.1. AuthN/AuthZ Flow (OIDC)
1. **Frontend**: Client starts a `WebAuthn` or `OAuth2` flow.
2. **Discovery**: Client hits `https://api.genesis.app/.well-known/openid-configuration`.
3. **Regional Steering**: The API Gateway (Envoy) uses the `x-genesis-region` header or the client's IP to route to the correct regional **IAM Provider**.

---

## 🌍 2. Global User Registry (DB Schema)
The Registry is a **CockroachDB Global Table** replicated across all three regions for low-latency lookups. It contains NO PII.

### 2.1. Registry Schema (`global_users`)
```sql
CREATE TABLE global_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_hash STRING UNIQUE, -- sha256(email) for lookups
    account_status ENUM('active', 'suspended', 'pending_erasure'),
    home_region ENUM('US', 'EU', 'IN'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE ON UPDATE now(),
    -- No PII (Name, Phone, etc.) stored here.
) REPLICATED;
```

---

## 🔐 3. Regional PII Vaults (Sharding)
The actual PII is stored in **Regional Tables** that are physically restricted to their geographic regions using CockroachDB **Multi-Regional Data placement**.

### 3.1. India Shard (Mumbai): `user_pii_in`
**Compliance: RBI Data Localization & DPDP.**
- **Legal Entity**: Genesis India Pvt Ltd.
- **Verification**: Aadhaar (OIDC via DigiLocker).
- **Schema**:
```sql
CREATE TABLE user_pii_in (
    user_id UUID PRIMARY KEY REFERENCES global_users(user_id),
    full_name STRING,
    phone_number STRING UNIQUE,
    aadhaar_masked STRING, -- Last 4 digits + Vault Ref
    aadhaar_vault_ref STRING, -- Pointer to secure vault for full ID
    kyc_level INT, -- 1=Basic, 2=Full
) REGIONAL BY ROW AS "india-mumbai";
```

### 3.2. EU Shard (Frankfurt): `user_pii_eu`
**Compliance: GDPR Article 44 (Transfers).**
- **Verification**: eID (Standardized EU Identity Wallet).
- **Schema**:
```sql
CREATE TABLE user_pii_eu (
    user_id UUID PRIMARY KEY REFERENCES global_users(user_id),
    full_name STRING,
    consent_flags JSONB, -- Explicit granular GDPR consents
    legal_age BOOLEAN,
    eid_provider_id STRING,
) REGIONAL BY ROW AS "europe-west3";
```

### 3.3. US Shard (N. Virginia): `user_pii_us`
**Compliance: HIPAA/CCPA.**
- **Verification**: SSN (via Plaid/Identifi).
```sql
CREATE TABLE user_pii_us (
    user_id UUID PRIMARY KEY REFERENCES global_users(user_id),
    full_name STRING,
    ssn_last4 STRING,
    phi_opt_in BOOLEAN DEFAULT FALSE, -- Essential for Health data linkage
) REGIONAL BY ROW AS "us-east-1";
```

---

## 🚦 4. API Gateway (Envoy) Routing Logic
The Gateway is the **Enforcer**. It rejects any request attempting to access `user_pii_in` from an `EU` IP unless proxying through a verified regional tunnel.

### 4.1. Traffic Steering Logic
```python
def route_genesis_request(request):
    # 1. Inspect JWT
    token = request.headers.get("Authorization")
    payload = decode_jwt(token)
    region_claim = payload.get("region")
    
    # 2. Check GeoIP as Fallback
    client_region = geo_ip_lookup(request.remote_addr)
    
    # 3. Security Check: Region Mismatch
    if region_claim and region_claim != client_region:
        log_anomaly("Region Mismatch", f"User {payload['user_id']} claiming {region_claim} from {client_region}")
        # Allow if User is traveling, but enforce cross-region latency policies.

    # 4. Route to Regional Upstream
    upstream = f"iam_service_{client_region.lower()}"
    return forward(request, upstream)
```

---

## 🏗️ 5. Next Level: Build Call
**Instruction to LLM:** "Write the Terraform module for the US-East CockroachDB cluster using the `REGIONAL BY ROW` strategy and the Python FastAPI middleware for the Envoy Gateway to validate region-sharding headers."
