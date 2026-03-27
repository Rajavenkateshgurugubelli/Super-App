# RFC-008: Super App Integration & Global Event Mesh

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Target Audience:** All Engineering Teams, Platform, SRE  
> **Depends On:** All (RFC-001 through RFC-007)

---

## 1. Abstract

This RFC defines the **Integration Layer** that transforms 8 disparate modules into a single, cohesive **Super App**. It specifies the Global Event Mesh (Kafka), the Unified Search Engine (Elasticsearch), and the Intelligent Push Notification Aggregator. This is the "Software Glue" of the Genesis platform.

---

## 2. Cross-Domain Events (Kafka Mesh)

Each module acts as an independent sovereign domain. Communication is **Event-Driven, Not Request-Response**, to prevent cascading failures.

### 2.1. The Event Mesh Architecture
1. **Producer**: The `DeliveryService` emits `delivery.order.completed`.
2. **Consumer Cluster (Payment)**: Listens for the event → calculates final fare (with surcharges) → triggers `wallet_service.captureFund`.
3. **Consumer Cluster (Social)**: Listens for the event → posts automatic "Nishant just ordered from Pizza Hut" update (if user consented).

**Example Sequence (Universal Checkout Bridge):**
- **Trigger**: User hits "Buy" in `Mini-App: Food`.
- **Event**: `mini_app.payment_request` (Topic: `superapp.payments.requests`).
- **Orchestration**: `SagaCoordinator` intercepts → checks Wallet Balance → triggers `PaymentConsentModal` in the Shell.
- **Completion**: `payment.executed` (Topic: `superapp.payments.completed`).

---

## 3. Global Search (Unified Intelligence)

A single search bar at the top of the app must navigate the entire ecosystem.

### 3.1. The Search Engine (Elasticsearch / OpenSearch)
- **Data Ingestion**: Change Data Capture (CDC) from all databases (CRDB, Neo4j, RDS) pushes updates to the **Search Index**.
- **Indiced Search (Intelligent Weighting)**:
  - **Social**: Friends/Followers (Weight: 1.0)
  - **Services**: Nearby Restaurants/Doctors (Weight: 0.8)
  - **Orders**: Past Receipts (Weight: 0.5)

**Search Query Example:**
```json
{
  "query": {
    "multi_match": {
      "query": "Raj",
      "fields": ["friend_name^3", "doctor_name^2", "restaurant_name"]
    }
  }
}
```

---

## 4. Intelligent Push Notifications

To avoid notification fatigue, we use a **Prioritized Delivery Queue**.

### 4.1. Prioritization Matrix
| Priority | Category | Examples | Delivery Channel | TTL |
|---|---|---|---|---|
| **P0** | **Critical/Safety** | "Doctor calling", "Fraud alert", "OTP" | Aggressive (Sound + High Priority) | 1 min |
| **P1** | **Transactional** | "Driver arrived", "Food delivered" | Normal (Silent/Vibration) | 15 min |
| **P2** | **Social** | "Someone liked your post" | Batch (Digests) | 24 hours |
| **P3** | **Marketing** | "50% off pizza" | Low (Background fetching) | 7 days |

---

## 5. Security & Isolation within the Mesh

Even in the Event Mesh, data boundaries must be respected.
- **PII Filtering**: A **Compliance Proxy** strips PII from all Kafka messages before they cross region-boundaries. Only `user_id` and non-PII metadata are shared.
- **Schema Registry**: Enforces strict Protobuf schemas (e.g., `payment_v2.proto`) to prevent integration breaks.

---

## 6. Execution Tasks (Epic 8 Extension)

| Task ID | Component | Description |
|---|---|---|
| I-101 | **Event Mesh** | Setup Kafka cross-region MirrorMaker and Schema Registry. |
| I-102 | **Unified Search** | Deploy Elasticsearch cluster and implement CDC connectors. |
| I-103 | **Push Aggregator** | Build the notification prioritization and batching service. |
| I-104 | **Integration Sagas** | Implement cross-domain Saga workflows (e.g., Ride -> Wallet -> Receipt). |

*End of RFC-008*
