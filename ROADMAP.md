# Super App Global Genesis — Roadmap

> **Current Version:** 2.0.0 | **Last Updated:** 2026-02-20

---

## ✅ Phase 2 Complete — Production Hardening & Full Feature Completeness

### P-A: Core Fixes ✅
- [x] **Session Persistence** — `/api/me` endpoint restores session on page refresh (no more logout)
- [x] **Signup Auto-Wallet** — New users automatically get a USD wallet created on registration
- [x] **Proper Error Codes** — 409 Conflict for duplicate email, 401 for bad credentials, 404 for missing resources
- [x] **Password Confirmation** — Signup form validates `confirm_password` client-side

### P-B: Currency Conversion UI ✅
- [x] **FX Rates Endpoint** — `GET /api/fx/rates` returns live rate matrix (USD base)
- [x] **Conversion Quote Endpoint** — `POST /api/convert` for wallet-specific conversion previews
- [x] **Convert Tab** — Fifth tab in WalletDashboard with from/to picker, amount input, animated quote result
- [x] **FX Widget on Overview** — Live USD→INR and USD→EUR rates shown on overview page
- [x] **Full Rate Table** — Tabular matrix of all 9 cross-currency pairs in the Convert tab

### P-C: Rate Limiting ✅
- [x] **Redis Sliding-Window** — 120 req/min per IP using sorted sets (ZRANGEBYSCORE)
- [x] **Fail-Open Design** — Redis errors never block requests; graceful degradation
- [x] **Configurable via Env** — `RATE_LIMIT_RPM` env variable
- [x] **429 with Retry-After** — Standard HTTP response with `Retry-After: 60` header

### UI/UX Overhaul ✅
- [x] **Premium Dark Theme** — Glassmorphism, Inter font, indigo/violet/cyan gradient system
- [x] **5-Tab Dashboard** — Overview / Send / Convert / History / Analytics
- [x] **Session Bootstrap Spinner** — "Restoring session..." screen on reload
- [x] **Toast Notifications** — Replaces browser `alert()` — animated overlay messages
- [x] **Sticky Glass Nav** — User avatar chip + email + sign-out button

---

## Milestone 1: Event-Driven & Edge Foundation (Phases 7–10)

### Phase 7: Event-Driven Architecture ✅ (Partially complete)
**7.1 Message Broker Setup**
- [x] Apache Kafka + Zookeeper deployed in docker-compose
- [x] `docker-compose-kafka.yml` created
**7.2 Event Producers & Consumers**
- [x] WalletService emits `TransactionInitiated` / `TransactionCompleted` events
- [x] NotificationService consumes Kafka events
- [ ] Dead Letter Queues (DLQ) for failed transaction events

### Phase 8: Edge Caching & High-Speed State ✅ (Partially complete)
**8.1 Redis Integration**
- [x] Redis deployed and connected in WalletService
- [x] Write-through cache for wallet balances (60s TTL)
- [ ] Cache for Policy/Compliance rules
**8.2 Distributed Locking**
- [x] Redis Redlock for double-spend prevention on TransferFunds

### Phase 9: Observability & Distributed Tracing ✅
**9.1 OpenTelemetry**
- [x] OpenTelemetry SDK installed in backend and gateway
- [x] All gRPC and FastAPI endpoints instrumented
**9.2 Monitoring Stack**
- [x] Jaeger deployed (traces at :16686)
- [x] Prometheus deployed (metrics at :9090)
- [ ] Grafana dashboard

### Phase 10: Infrastructure as Code (IaC) ✅ (Partially complete)
**10.1 Cloud Provisioning**
- [x] Terraform configs initialized (`main.tf`, `variables.tf`)
- [x] GCP Cloud Build YAML (`cloudbuild.yaml`)
- [ ] Full ECS/EKS modules

---

## Milestone 2: Micro-Frontend Shell (Phases 11–14)

### Phase 11: Micro-Frontend Architecture ✅
**11.1 Vite Module Federation**
- [x] Shell host application with JWT state management
- [x] WalletDashboard extracted as Remote/Mini-App
- [x] Shared React/ReactDOM via federation

### Phase 12: Shared Ecosystem Resources ⚙️ (In Progress)
**12.1 Universal Component Library**
- [x] `shared-ui` package with Button component (vendored for Docker)
- [ ] Storybook documentation
- [ ] Full design system (Input, Modal, Card, Badge)

### Phase 13: Mobile Super App Container (Planned)
- [ ] React Native / Expo initialization
- [ ] Mobile Shell native navigation
- [ ] WebViews for web-based Mini-Apps

### Phase 14: Mobile API Bridging (Planned)
- [ ] Envoy Proxy for gRPC-Web
- [ ] Payload compression for mobile bandwidth

---

## Milestone 3: Advanced Security & Sovereignty (Phases 15–18)

### Phase 15: Zero-Trust Service Mesh (Planned)
- [ ] Istio / Linkerd sidecar injection
- [ ] mTLS between UserService and WalletService
- [ ] Network policies (deny-by-default)

### Phase 16: Biometric & Passwordless Auth (Planned)
- [ ] WebAuthn / Passkeys
- [ ] Public key credential storage
- [ ] JWT issuance via cryptographic signatures

### Phase 17: Cross-Border Data Residency (Planned)
- [ ] Geo-Routing Engine (EU → EU node, IN → IN node)
- [ ] PII masking for cross-border admin queries

### Phase 18: Advanced API Security ✅ (Partially complete)
**18.1 Rate Limiting**
- [x] Redis sliding-window rate limiting (120 req/min per IP, configurable)
- [x] 429 responses with `Retry-After` header
- [ ] WAF (SQL injection / XSS blocking)

---

## Milestone 4: Decentralized Ledger (Phases 19–22) — Planned

### Phase 19: Immutable Transaction Ledger
- [ ] Hyperledger Fabric private blockchain node
- [ ] Chaincode for wallet balances
- [ ] SQL ↔ Ledger state sync

### Phase 20: Decentralized Identity (Planned)
- [ ] W3C DID implementation
- [ ] Verifiable Credentials for KYC

### Phase 21: Financial Routing Arbitrage (Planned)
- [ ] Smart-routing algorithm (cheapest cross-border path)
- [ ] Webhook listeners for payment confirmations

### Phase 22: Automated Reconciliation (Planned)
- [ ] Nightly Python reconciliation daemon
- [ ] Compliance reports for regulators

---

## Milestone 5: AI Orchestration & HA (Phases 23–26) — Planned

### Phase 23: On-Device AI Orchestrator
- [ ] LLM integration (Llama 3 Nano) for NL payment intent parsing
- [ ] "Send $50 to John" → auto-maps to gRPC endpoint

### Phase 24: Real-Time Analytics Pipeline
- [ ] ClickHouse OLAP deployment
- [ ] Kafka → ClickHouse event streaming
- [ ] Internal admin analytics dashboard

### Phase 25: Chaos Engineering
- [ ] Scripts to randomly kill containers under load
- [ ] Frontend graceful degradation (last-known balance cache)

### Phase 26: Multi-Region Active-Active Failover
- [ ] Region outage simulation
- [ ] Automated DNS failover (zero data loss)
