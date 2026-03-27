# 🏗️ 2026 Modular Architecture Specification: The "Host Shell"

> **Status:** ADOPTED (RC-4)  
> **Concept:** Dynamic Micro-Apps powered by Polyglot Persistence and Event Mesh.

---

## 📱 I. Frontend: The "Host Shell"
The frontend is a **React Native with Re.Pack (Module Federation)** container. It acts as the Host for independent Mini-App bundles.

### 1.1. Visual Design: "Genesis Glass"
- **Navigation**: Persistent bottom bar with 4 nodes (**Home**, **Social**, **Health**, **Logistics**).
- **Styling**: Shared Atoms (Atomic Design) with Glassmorphism blur effects.
- **Micro-App Themes**:
    - **Social**: Story-centric, high motion.
    - **Health**: Clinical-warm, high-contrast status.
    - **Logistics**: Map-centric, utility-heavy tracking.

---

## ⚙️ II. Backend: Polyglot Distributed Engine
Instead of a monolithic DB, Genesis 2026 uses optimized stores for each domain.

### 2.1. Persistence Strategy
| Pillar | Database | Primary Use Case |
|---|---|---|
| **Social** | **Neo4j** | Graph-traversal (follows, mutuals, interests). |
| **Health** | **MongoDB** | FHIR-compliant record blobs, telemetry logs. |
| **Logistics** | **PostGIS** | Geospatial tracking and ACID delivery transactions. |
| **Identity** | **CockroachDB** | Global user registry and regional PII shards. |

### 2.2. Scoped IAM & Tokens
Permissions are granularly scoped. A token for "Social" cannot access "Health" PHI.
- **Identity Provider**: Genesis-Auth (OIDC).
- **Scopes**: `genesis:social:read`, `genesis:health:full_phi`, `genesis:wallet:pay`.

---

## 🕸️ III. The Event Mesh (The "Glue")
**Kafka** is the backbone for cross-module orchestration.

### 3.1. Scenario: Prescription-to-Delivery
1. **Trigger**: `HealthService` emits `PRESCRIPTION_ISSUED`.
2. **Action 1**: `LogisticsService` pre-calculates pharmacy ETA.
3. **Action 2**: `IntegrationService` sends high-priority Story-style notification.
4. **Action 3**: `SocialService` offers a "Nudge" in the user's health-interest-graph feed.

---

## 🌍 IV. Regional Compliance
- **US**: AWS-East (HIPAA Silos).
- **EU**: Frankfurt (GDPR Right-to-Forgotten Workers).
- **India**: Mumbai (UPI Rails + RBI Data Localization).

---

## 🚀 Execution Summary
- **Frontend**: Transition to Re.Pack Module Federation.
- **Backend**: Move Social to Neo4j, Health to MongoDB.
- **Integration**: Deploy the Prescription-to-Delivery handover API.
