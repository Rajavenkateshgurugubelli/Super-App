# 📦 Module 3: Real-Time Delivery & Geospatial Engine

> **Execution Level:** HIGH-DEPTH (Buildable)  
> **Target Regions:** US (ACH), EU (SEPA), IN (UPI)

---

## 🏗️ 1. Geospatial Strategy: H3 Hexagonal Indexing
Standard Radial searching (Lat/Long +/- 0.05) is O(N) and inefficient for 10M+ drivers. 
**Strategy**: Use **Uber H3** to index all coordinates into 64-bit integer cells.

### 1.1. Spatial Resolution
- **Resolution 7**: (~5 km² cells) for Regional Demand heatmaps.
- **Resolution 9**: (~0.1 km² cells) for Last-Mile Driver Matching.

---

## 🧭 2. Real-Time Driver Tracking (Redis GEO)
Drivers send a heartbeat every 5 seconds via **WebSocket**.

### 2.1. WebSocket Ping Contract
**Endpoint**: `ws://api.genesis.app/ws/logistics/telemetry`
**Payload (JSON)**:
```json
{
  "event": "DRIVER_HEARTBEAT",
  "driver_id": "drv_889",
  "lat": 19.0760,
  "lng": 72.8777,
  "h3_index": "8928308280fffff", # Resolution 9
  "status": "AVAILABLE",
  "region": "IN"
}
```

### 2.2. Tracking Loop (Go/Redis)
```go
func UpdateDriverLocation(driverID string, h3Index uint64, lat, lng float64) {
    // 1. Log to Redis GEO (for distanceCalcs)
    redis.GeoAdd("drivers_geo:in", lng, lat, driverID)
    
    // 2. Set H3 Index Hash (for O(1) cellular matching)
    redis.HSet("drivers_h3:in", driverID, h3Index)
    
    // 3. Mark Availability
    redis.SAdd("online_drivers:" + h3Index, driverID)
}
```

---

## 🏁 3. Delivery Order State Machine
Standardizes the lifecycle of every physical delivery or ride.

### 3.1. Discrete Lifecycle Model
| State | Event | Trigger |
|---|---|---|
| `ORDER_PLACED` | `payment.success` | Wallet confirms funds escrowed |
| `COURIER_SEARCHING` | `dispatch.search` | System pings top 5 nearby H3 cells |
| `COURIER_MATCHED` | `driver.accept` | Driver claims the order |
| `GEOFENCE_ENTERED` | `telemetry.entry` | Driver within 100m of Merchant H3 cell |
| `IN_TRANSIT` | `merchant.handover` | Merchant scans QR on Driver App |
| `COMPLETED` | `telemetry.exit` | Driver within 50m of Customer H3 cell |

---

## 🛰️ 4. Geofencing API Contract
The **Dispatch Service** uses Geofences to trigger events without manual button presses.

### 4.1. Geofence Definition
- **Geofence Center**: `(MerchantLat, MerchantLng)`
- **Radius**: `100m`
- **Action**: `POST /api/logistics/orders/{id}/status/arrived`

---

## 🏗️ 5. Next Level: Build Call
**Instruction to LLM:** "Write the Go microservice for the 'Logistics Dispatcher' using the `h3-go` library. Implement the 'Cellular Search' function that finds available drivers within the user's current H3 cell and adjacent neighbor cells (O(1) complexity)."
