# RFC-006: Health, Telemedicine, and Strict Compliance

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Target Audience:** Engineering, Health Compliance, Legal, Security Teams  
> **Depends On:** RFC-001 (IAM), RFC-003 (Frontend SDK)

---

## 1. Abstract

This RFC defines the architecture for the **Health & Wellness** module of the Super App. It specifies the physical and logical isolation of Protected Health Information (PHI), the telemedicine video infrastructure (WebRTC), high-assurance identity verification for medical providers, and interoperable health data exchange using the **HL7 FHIR** standard.

---

## 2. PHI Data Isolation Strategy

Health data carries the highest legal risk (HIPAA, GDPR, DPDP). The Super App uses an **Air-Gapped Data Model** for PHI.

### 2.1. Physical vs Logical Isolation
1. **Physical**: The Health database (PostgreSQL + EDB Transparent Data Encryption) runs in a separate VPC/Project with restricted IAM access. Communication is strictly via a **Health Gateway Proxy**.
2. **Logical**: No PHI is ever stored in the general User, Payment, or Social databases. Only the `user_id` (UUID) is used as a foreign key for cross-referencing.

### 2.2. Encryption-at-Rest (EAR)
PHI is encrypted at the application level using a **Patient-Specific Key** (PSK) derived from the user's biometric entropy or master passphrase. This ensures the platform itself cannot decrypt the data without user interaction (Zero-Knowledge).

---

## 3. Telehealth Infrastructure (WebRTC)

### 3.1. Consultation Architecture
- **Protocol**: Peer-to-Peer (P2P) **WebRTC** with DTLS-SRTP encryption.
- **Signaling**: WebSocket-based signaling server (AWS AppSync / custom Go server) to negotiate the connection.
- **STUN/TURN**: Globally distributed TURN servers (Twilio / CoTURN) to handle NAT traversal, especially for mobile users on carrier-grade NAT.

### 3.2. Low-Bandwidth Optimizations (India Market)
To ensure reliable consultations in 2G/3G environments:
- **Simulcast**: Doctors receive 720p; Patients receive 240p/360p based on adaptive bitrate (ABR).
- **VP9/AV1 Codecs**: Superior compression for low-bitrate video.
- **Audio-Only Fallback**: Automatic transition to OPUS-compressed audio if packet loss exceeds 15%.

---

## 4. High-Assurance Identity (The Handoff)

Access to medical records requires more than a simple JWT.

### 4.1. Step-Up Authentication
When a user accesses Health records, the Shell triggers a **Step-Up Challenge**:
1. **FIDO2/WebAuthn**: Re-verification via biometric (FaceID / Fingerprint).
2. **Identity Linkage**: For medical providers (Doctors/Nurses), we verify their National Provider Identifier (NPI) or State Medical Council (India) credentials through a dedicated high-assurance provider.

### 4.2. Short-Lived "Medical Access Tokens"
The IAM service issues a scoped, 5-minute `HEALTH_ACCESS` token only after successful step-up. This token is restricted to the `/api/health/*` namespace.

---

## 5. EHR Interoperability (HL7 FHIR)

To connect with external hospitals (Cerner, Epic) and pharmacies, the Super App implements the **FHIR R4/R5** API standard.

### 5.1. Resource Mapping
- **Patient**: Maps Super App `UserPII` to FHIR Patient resource.
- **Observation**: For syncing wearable data (Apple HealthKit / Google Fit).
- **Encounter**: For telemedicine history.
- **MedicationRequest**: For e-prescriptions.

**FHIR API Example (JSON):**
```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [{ "system": "http://www.nlm.nih.gov/research/pim/rxnorm", "code": "58242", "display": "Aspirin 81 mg" }]
  },
  "subject": { "reference": "Patient/usr_123" },
  "authoredOn": "2026-03-27T12:00:00Z"
}
```

---

## 6. Execution Tasks (Epic 6 Extension)

| Task ID | Component | Description |
|---|---|---|
| H-101 | **Health Vault** | Deploy air-gapped RDS/PostgreSQL cluster with TDE enabled. |
| H-102 | **WebRTC Signal** | Implement consultation room signaling and TURN relay integration. |
| H-103 | **FHIR Gateway** | Build the FHIR-to-Internal mapping layer for external healthcare partners. |
| H-104 | **Identity Step-up** | Implement biometric re-verification flow in the Shell for PHI access. |

*End of RFC-006*
