# 💊 Prescription-to-Delivery Handover API Specification

> **Version:** 1.0.0  
> **Type:** Cross-Domain Integration (Health -> Logistics)  
> **Draft:** ARCH-2026-MODULAR

---

## 🏗️ 1. Integration Logic
1. **Health Service**: User finishes consultation; Doctor issues `Prescription`.
2. **Handover Trigger**: `Health Service` emits `PRESCRIPTION_ISSUED` Kafka event.
3. **Logistics Service**: Fetches available Pharmacies via `H3 Hexagonal Indexing`.
4. **Gateway**: Serves the `Unified Checkout` page for the user to confirm "Deliver Now."

---

## 📝 2. OpenAPI Specification (YAML)

```yaml
openapi: 3.0.0
info:
  title: Genesis Prescription Handover API
  version: 1.0.0
  description: Connects clinical health events to physical delivery orders.

paths:
  /api/health/prescriptions/{id}/handover:
    post:
      summary: Initiate delivery for an issued prescription.
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      security:
        - BearerAuth: [ "genesis:health:read", "genesis:logistics:write" ]
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/HandoverRequest'
      responses:
        '201':
          description: Delivery order initiated from prescription.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DeliveryDraft'
        '403':
          description: Token lacks necessary scopes.

components:
  schemas:
    HandoverRequest:
      type: object
      properties:
        delivery_address_id:
          type: string
        recipient_name:
          type: string
        is_urgent:
          type: boolean
          default: false
        h3_cell_recipient:
          type: string
          description: H3 Index (Res 9) for high-precision matching.

    DeliveryDraft:
      type: object
      properties:
        order_id:
          type: string
          format: uuid
        pharmacy_id:
          type: string
        medication_items:
          type: array
          items:
            $ref: '#/components/schemas/MedItem'
        estimated_eta:
          type: integer
          description: Minutes until delivery.
        base_cost:
          type: number
        currency:
          type: string

    MedItem:
      type: object
      properties:
        med_name:
          type: string
        dosage:
          type: string
        quantity:
          type: integer

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

## 🕸️ 3. Event-Driven Schema (Kafka)
**Topic**: `health.prescription.issued`

### 3.1. Message Payload
```json
{
  "event_id": "uuid-123",
  "user_id": "uuid-abc",
  "prescription_id": "uuid-xyz",
  "clinician_id": "uuid-doc",
  "region": "IN",
  "pharmacy_nudge": {
    "recommended_pharmacies": ["store_v1", "store_v2"],
    "h3_cell_origin": "8928308280fffff"
  },
  "timestamp": 1711561353
}
```

---

## 🏗️ 4. Build Call
**Instruction to LLM:** "Based on this specification, implement the 'Handover Controller' in the `Logistics Service`. It must subscribe to the `health.prescription.issued` Kafka topic and use the `H3-Indexer` to find the 3 nearest pharmacies to the user's current city center (H3 Resolution 7)."
