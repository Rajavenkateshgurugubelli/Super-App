# 🛸 Super App Master Orchestrator: System Context for AI Coding Agents

> **Objective:** Build the Orchestration Layer for the Global Genesis Super App (12 Modules).
> **Target Environment:** Multi-Region Kubernetes (EKS/GKE).
> **Target Markets:** US (HIPAA), EU (GDPR), India (RBI/DPDP).

---

## 🤖 AI Coding Directive (Prompt Header)

"Act as a Senior Infrastructure Engineer specializing in Global Scale Distributed Systems. Your task is to implement the **Master Orchestration Layer** for a 12-module Super App ecosystem. You must ensure that each module is physically isolated according to regional data laws while remaining seamlessly integrated via a Shared Event Mesh and a Host-Shell API Gateway."

---

## 🏗️ 1. Infrastructure Parameters (The "Connective Tissue")

### 1.1. Kubernetes Architecture (K8s)
- **Namespaces**: `core`, `social`, `health`, `logistics`, `fintech`, `research`, `iam`.
- **Node Pools**: Separate 'PHI-Compliant' pools for `health` using `Nitro Enclaves` or `TDE`.
- **Global Ingress**: Use **Envoy Gateway** with a custom LUA filter for `x-genesis-region` traffic steering.

### 1.2. Service Mesh (Istio)
- **mTLS**: Enforce `STRICT` mutual TLS between all modules.
- **Sidecar Egress**: Prohibit all egress from the `health` namespace to the public internet except through a verified **Compliance-Audit-Proxy**.

### 1.3. Polyglot persistence Connectivity
Confirm the following service connections in the `ConfigMap`:
- **Social (M5)**: Connects to `neo4j-cluster.global.svc`.
- **Health (M6)**: Connects to `mongodb-atlas-phi-us.private.svc`.
- **Logistics (M7)**: Connects to `postgis-primary.regional.svc`.
- **Wallet (M2)**: Connects to `cockroachdb-ledger.global.svc`.

---

## 🚦 2. The Global API Gateway (The "Guardian")

Implement the **Envoy L7 Rewrite Rules** for regional routing:
1. **Header Based**: `If Header 'x-genesis-region' == 'IN' -> Route: 'internal-lb-mumbai'`.
2. **Path Based**: `If Path matches '/api/phi/*' -> Redirect: 'secure-phi-gateway.health'`.
3. **IAM Based**: `If Scope 'genesis:health:full_phi' matches -> Inject: 'vault-pii-decrypt-token'`.

---

## 🕸️ 3. The Shared Event Mesh (Kafka Orchestration)

Define the **Topic Architecture** for cross-app coordination:
| Topic | Producer | Consumers |
|---|---|---|
| `health.prescription.issued` | Health Service | Logistics (Delivery), Social (Nudge) |
| `logistics.order.complete` | Logistics Service | Wallet (Release Escrow), Social (Achievement) |
| `social.post.sentiment` | Social Service | Wealth/Tax (Nudge), Health (Nudge) |

---

## 🔐 4. Data Residency Enforcement (The "Wall")

**CRITICAL**: You must write a `MutatingAdmissionWebhook` that prevents any pod in the `india` cluster from mounting a persistent volume that is not tagged with `region=ap-south-1` to comply with RBI data localization mandates.

---

## 🏗️ 5. Build Instruction
"Based on this context, generate the **Istio VirtualService** and **Gateway** manifests to handle cross-domain regional routing. Also, implement the **Go Fiber** skeleton for the `Master-Gateway-Orchestrator` that verifies **Scoped JWTs** before proxying requests to the specific domain-authorized microservices."
