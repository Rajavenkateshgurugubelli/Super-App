# Super App Global Genesis Roadmap

This document outlines the phased expansion of the Super App into a global, event-driven, secure, and decentralized financial operating system.

## Milestone 1: Event-Driven & Edge Foundation (Phases 7–10)
To scale globally, microservices must stop waiting on each other. We are moving from synchronous gRPC calls to asynchronous event streaming.

### Phase 7: Event-Driven Architecture (Planned)
**7.1 Message Broker Setup**
- [ ] Install and configure Apache Kafka or Redpanda (for lower latency).
- [ ] Create `docker-compose-kafka.yml` for local development.
**7.2 Event Producers & Consumers**
- [ ] Refactor WalletService to emit `TransactionInitiated` events instead of direct DB writes.
- [ ] Create a dedicated NotificationService that consumes events and sends alerts.
- [ ] Implement Dead Letter Queues (DLQ) for failed transaction events.

### Phase 8: Edge Caching & High-Speed State (Planned)
**8.1 Redis Integration**
- [ ] Deploy a Redis cluster for edge caching.
- [ ] Implement a Write-Through cache in FastAPI for user profiles.
- [ ] Cache frequently accessed Policy/Compliance rules to reduce CockroachDB load.
**8.2 Distributed Locking**
- [ ] Implement Redis Redlock to prevent double-spending in the WalletService during concurrent requests.

### Phase 9: Observability & Distributed Tracing (Planned)
**9.1 OpenTelemetry Setup**
- [ ] Install OpenTelemetry SDKs in the Python backend.
- [ ] Instrument all gRPC and FastAPI endpoints to generate trace IDs.
**9.2 Monitoring Stack**
- [ ] Deploy Prometheus (metrics) and Jaeger (tracing) via Docker Compose.
- [ ] Create a Grafana dashboard visualizing gRPC latency and transaction throughput.

### Phase 10: Infrastructure as Code (IaC) (Planned)
**10.1 Cloud Provisioning**
- [ ] Initialize Terraform (`main.tf`, `variables.tf`).
- [ ] Write Terraform modules to provision AWS ECS/EKS or GCP Cloud Run.
- [ ] Automate CockroachDB managed cluster provisioning.

---

## Milestone 2: The Micro-Frontend (MFE) Shell (Phases 11–14)
A Super App cannot be a monolith on the frontend. It must be a "Shell" that loads independent Mini-Apps dynamically.

### Phase 11: Micro-Frontend Architecture (Planned)
**11.1 Webpack Module Federation**
- [ ] Reconfigure the React/Vite app to use Webpack Module Federation (or Vite equivalent).
- [ ] Create the Host/Shell application (handles routing and JWT state).
- [ ] Extract the `WalletDashboard` into a standalone Remote/Mini-App.

### Phase 12: Shared Ecosystem Resources (Planned)
**12.1 Universal Component Library**
- [ ] Create a standalone React component library (buttons, modals, forms) using Tailwind.
- [ ] Set up Storybook to document the UI kit.
- [ ] Publish the library locally so all future Mini-Apps use the same design system.

### Phase 13: The Mobile Super App Container (Planned)
**13.1 React Native / Expo Initialization**
- [ ] Initialize `super-app-mobile` using Expo.
- [ ] Implement the Mobile Shell native navigation.
- [ ] Create WebViews or native bridging to load the web-based Mini-Apps dynamically inside the mobile shell.

### Phase 14: Mobile API Bridging (Planned)
**14.1 Connect-Web/gRPC-Web**
- [ ] Implement Envoy Proxy to translate gRPC calls for the mobile frontend.
- [ ] Update the API Gateway to handle mobile-specific bandwidth constraints (payload compression).

---

## Milestone 3: Advanced Security & Sovereignty (Phases 15–18)
Protecting the system against nation-state-level threats and complying with global data laws.

### Phase 15: Zero-Trust Service Mesh (Planned)
**15.1 Istio / Linkerd**
- [ ] Inject a Service Mesh sidecar into the backend Docker containers.
- [ ] Enforce strict mTLS (Mutual TLS) between the UserService and WalletService.
- [ ] Implement network policies denying all traffic except explicitly allowed routes.

### Phase 16: Biometric & Passwordless Auth (Planned)
**16.1 WebAuthn / Passkeys**
- [ ] Update users table to store public key credentials.
- [ ] Implement the WebAuthn API on the React frontend (FaceID/TouchID).
- [ ] Modify the FastAPI gateway to issue JWTs based on cryptographic signatures rather than passwords.

### Phase 17: Cross-Border Data Residency (Planned)
**17.1 Geo-Routing Engine**
- [ ] Enhance the Phase 1 Geo-Fencing Middleware to physically route EU requests to an EU database node and US/India requests to their respective nodes.
- [ ] Implement data masking for cross-border admin queries (e.g., hiding PII if an Indian admin views a US user).

### Phase 18: Advanced API Security (Planned)
**18.1 Rate Limiting & WAF**
- [ ] Implement sliding-window rate limiting in Redis to prevent DDoS attacks on the Gateway.
- [ ] Set up a Web Application Firewall (WAF) rule set to block SQL injection and cross-site scripting (XSS).

---

## Milestone 4: Decentralized Ledger & Programmable Finance (Phases 19–22)
Moving from a simple relational database to a system capable of handling complex, immutable, cross-border financial consensus.

### Phase 19: Immutable Transaction Ledger (Planned)
**19.1 Permissioned Blockchain Integration**
- [ ] Deploy a lightweight private blockchain node (e.g., Hyperledger Fabric) alongside CockroachDB to act as an append-only, immutable audit trail.
- [ ] Write "Chaincode" (smart contracts) to handle the absolute source of truth for wallet balances.
- [ ] Sync state between the SQL database (for fast reads) and the ledger (for cryptographic proof).

### Phase 20: Decentralized Identity (DID) (Planned)
**20.1 Self-Sovereign Identity**
- [ ] Implement W3C standard Decentralized Identifiers (DIDs) for user accounts.
- [ ] Create a Verifiable Credentials (VC) issuance flow (e.g., verifying KYC status without storing the raw passport data).

### Phase 21: Financial Routing Arbitrage (Planned)
**21.1 Smart-Routing Engine**
- [ ] Build an algorithm in the WalletService that calculates the cheapest path for cross-border transfers (e.g., routing through a liquidity pool vs. standard ACH/SEPA).
- [ ] Implement Webhooks to listen for asynchronous payment confirmations from third-party APIs.

### Phase 22: Automated Reconciliation (Planned)
**22.1 Cron Jobs & Auditing**
- [ ] Write a Python daemon that runs nightly to reconcile the CockroachDB state against the Immutable Ledger state.
- [ ] Generate automated compliance reports for financial regulators.

---

## Milestone 5: AI Orchestration & High Availability (Phases 23–26)
Making the app autonomous and virtually unkillable.

### Phase 23: On-Device AI Orchestrator (Planned)
**23.1 Local LLM Integration**
- [ ] Integrate a lightweight, open-source model (like Llama 3 Nano) into the mobile app shell for on-device natural language parsing.
- [ ] Allow users to type "Send $50 to John" and have the AI map this to the exact gRPC endpoint without the user clicking through the UI.

### Phase 24: Real-Time Analytics Pipeline (Planned)
**24.1 ClickHouse Deployment**
- [ ] Deploy ClickHouse as an OLAP (Online Analytical Processing) database.
- [ ] Stream logs and events from Kafka into ClickHouse.
- [ ] Build an internal admin dashboard for real-time user behavior analytics.

### Phase 25: Chaos Engineering (Planned)
**25.1 Fault Tolerance Testing**
- [ ] Implement scripts to randomly kill Docker containers (UserService, Redis) while load testing to ensure the system recovers automatically.
- [ ] Verify that the frontend gracefully degrades (e.g., caching the user's last balance if the wallet service is down).

### Phase 26: Multi-Region Active-Active Failover (Planned)
**26.1 Global Disaster Recovery**
- [ ] Simulate a full region outage (e.g., US-East goes offline).
- [ ] Automate the DNS failover to route all traffic to the EU or India clusters with zero data loss.
