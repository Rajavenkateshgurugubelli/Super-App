# RFC-007: On-Demand Delivery and Logistics Engine

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Target Audience:** Engineering, Logistics Ops, Fleet Management  
> **Depends On:** RFC-001 (IAM), RFC-002 (Wallet)

---

## 1. Abstract

This RFC defines the technology stack for **Delivery, Ride-Hailing, and Logistics** in the Super App. It specifies the geospatial indexing strategy for real-time location tracking, a robust Finite State Machine (FSM) for orders, the dispatch/matching algorithm for fleet efficiency, and the decoupled portal architecture for Merchants and Drivers.

---

## 2. Geospatial Architecture

The system must process **1,000,000+ pings/second** from drivers to provide accurate ETAs and matching.

### 2.1. Layered Strategy
1. **The Ingest Layer (Redis GEO)**: All driver location pings (`lat`, `lng`, `driver_id`, `status`) are pushed to Redis every 5 seconds. Redis' `GEOADD` and `GEORADIUS` provide ultra-low latency searches (sub-1ms) for "drivers within 5km".
2. **The Audit Layer (PostGIS)**: Completed trips and historical paths are persisted in **PostgreSQL with PostGIS** for accurate distance calculations, fraud analysis, and multi-polygon geofencing.

**Redis CLI Example (Ingest):**
```bash
# Add driver location (lat, lng, member)
GEOADD drivers:india:mumbai 72.8777 19.0760 "drv_999"

# Find within 5km of user
GEORADIUS drivers:india:mumbai 72.8700 19.0700 5 km WITHDIST WITHCOORD
```

---

## 3. Order & Trip State Machine

Deliveries and rides have complex, inter-dependent lifecycles.

### 3.1. The FSM Design (XState Pattern)
- **States**: `SEARCHING` -> `ACCEPTED` -> `ARRIVING` -> `IN_TRANSIT` -> `COMPLETED`.
- **Transitions**: Triggered by user/driver actions (e.g., `START_TRIP`) or external events (e.g., `PAYMENT_SUCCESS`).

**Edge Case Handling:**
- **Driver Cancellation**: Transition back to `SEARCHING` with a higher retry priority. Triggers a Kafka event `delivery.driver.unassigned`.
- **Network Drops**: Mobile apps cache the current state. Upon reconnect, the app polls the `SyncOrder` API to reconcile the local state with the backend's source-of-truth.

---

## 2. Routing & Driver Matching Algorithm

The dispatch algorithm (Matching Service) operates on a "Greedy but Fair" model.

### 4.1. The Dispatch Loop
1. **Search Cluster**: Identify `drivers` within a 5-10km radius of the `pickup`.
2. **Filter**: Apply constraints (Driver rating > 4.0, Vehicle type, Active order count < 1).
3. **Score**: `Score = (Distance Weight * d) + (Traffic Weight * t) + (Idle Time Bonus * i)`.
4. **Offer**: Send Push / WebSocket notification to the top 3 drivers in priority sequence (15s response window).

---

## 5. Portal Architecture (Merchant & Driver)

These are standalone mini-apps or independent web views within the Super App ecosystem.

### 5.1. Merchant Portal
- **Services**: `MenuManagement`, `OrderManagement`, `RevenueDashboard`.
- **Tech**: React + Vite, real-time "Order Ding" via WebSockets.

### 5.2. Driver Portal
- **Services**: `LocationBroadcast`, `EarningSettlement`, `Navigator`.
- **Integrations**: Google Maps SDK / Mapbox for turn-by-turn. Biometric auth for daily login (KYC requirement).

---

## 6. Execution Tasks (Epic 7 Extension)

| Task ID | Component | Description |
|---|---|---|
| L-101 | **Geo Ingest** | Deploy Redis cluster with GEO data-type support. |
| L-102 | **Order FSM** | Implement the core Delivery/Ride FSM and transaction logic. |
| L-103 | **Dispatch Svc** | Build the matching engine with weight-based scoring logic. |
| L-104 | **Partner SDK** | Develop the Merchant and Driver web-view frameworks for mini-apps. |

*End of RFC-007*
