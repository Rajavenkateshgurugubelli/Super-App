# 🕸️ Module 4: Cross-App Event Mesh (The "Glue")

> **Execution Level:** HIGH-DEPTH (Buildable)  
> **Target Regions:** US (HIPAA), EU (GDPR), IN (RBI)

---

## 🏗️ 1. Unified Kafka Mesh Architecture
Super App services communicate via **Kafka (Avro)** to maintain data isolation while enabling high-depth integration.

### 1.1. Core Logic: "Contextual Cross-Selling"
- **Trigger**: User posts `I have a headache` (Social).
- **Service**: `Intelligence-Gateway` (Python NLP) scans the stream.
- **Event**: `social.post.sentiment_flagged`.
- **Reaction**: `Health-Recommender` suggests a doctor; `Logistics-Recommender` suggests pharmacy delivery.

---

## 🔐 2. Distributed Saga Pattern (Transactional Glue)
A **Saga** coordinates a sequence of local transactions across multiple microservices.

### 2.2. Use Case: "The Telehealth-to-Delivery Pipeline"
A single user gesture (Booking a Consult) involves three domains:

| Step | Service | Local Action | Compensating Action (Rollback) |
|---|---|---|---|
| 1 | `HEALTH` | Post-Consult `Session_Created` | `cancel_consult` |
| 2 | `WALLET` | `hold_funds` (Escrow) | `release_funds` |
| 3 | `LOGISTICS` | `create_pharmacy_nudge` | `delete_nudge` |

---

## 📦 3. Precise Avro Schema Definition
Avro ensures data contracts between Producers (Social) and Consumers (Health/Wallet) are NEVER broken.

### 3.1. `CrossAppNudge` Event Schema
**Namespace**: `app.genesis.events.core`
```json
{
  "type": "record",
  "name": "CrossAppNudge",
  "fields": [
    { "name": "user_id", "type": "string" },
    { "name": "source_action_id", "type": "string" }, # Trace the Social Post ID
    { "name": "nudge_intent", "type": "string" },    # "MEDICAL_CONSULT_NEEDED"
    { "name": "confidence_score", "type": "float" }, # 0.95
    { "name": "suggested_merchant_ids", "type": { "type": "array", "items": "string" } }
  ]
}
```

---

## 🚦 4. The "Intelligent Push" Aggregator
Instead of 100 notifications, Module 8 (Integration) batches events based on user state to prevent fatigue.

### 4.1. Prioritization Logic
```python
def route_notification(event):
    # 1. Inspect Event Metadata
    priority = event.get("priority", "P3") # P0-P3
    
    # 2. State Check: User is Driving?
    if user_in_state(event.user_id) == "DRIVING":
        if priority != "P0": # Only critical delivery alerts
            return queue_for_later(event)
            
    # 3. Publish to WebSocket (gateway/main.py)
    publish_to_user_channel(event.user_id, event.payload)
```

---

## 🏗️ 5. Next Level: Build Call
**Instruction to LLM:** "Write the Python Kafka Consumer for the 'Intelligence Orchestrator' using the `confluent-kafka` library. Implement the 'Saga Coordinator' that handles the `Step 1 (Health) -> Step 2 (Wallet)` flow, and registers the 'Compensating Transaction' if the `WALLET_INSUFFICIENT_FUNDS` event is received."
