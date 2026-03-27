# 💰 Wealth & Tax Optimizer (Module 9) API Specification

> **Version:** 1.0.0  
> **Type:** Cross-Border Financial Intelligence (FinTech)  
> **Target:** US/India Dual-Filers (NRIs/Expats)

---

## 🏗️ 1. Integration Logic
1. **Wallet Service**: Provides real-time balances for app-internal wallets.
2. **Wealth Service (M9)**: Connects to external US Banks (Plaid) and Indian Banks (Account Aggregator).
3. **Tax Engine**: Calculates 1040 [US] and IT-Return [India] estimated liabilities.
4. **Action**: Optimizes which currency to liquidiate for high-value Super App purchases.

---

## 📝 2. OpenAPI Specification (YAML)

```yaml
openapi: 3.0.0
info:
  title: Genesis Wealth & Tax Optimizer API
  version: 1.0.0
  description: Handles global balance sheet aggregation and multi-jurisdictional tax optimization.

paths:
  /api/wealth/accounts/india:
    get:
      summary: Get NRO/NRE account status and repatriation readiness.
      security:
        - BearerAuth: [ "genesis:wealth:read" ]
      responses:
        '200':
          description: List of Indian bank accounts with tax residency status.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IndiaAccountList'

  /api/wealth/tax/harvest:
    post:
      summary: Calculate tax harvesting strategy across 1040 and IT-Return.
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/HarvestRequest'
      responses:
        '200':
          description: Optimized liquidation strategy.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OptimizationResult'

components:
  schemas:
    IndiaAccountList:
      type: object
      properties:
        accounts:
          type: array
          items:
            $ref: '#/components/schemas/IndiaAccount'

    IndiaAccount:
      type: object
      properties:
        account_id:
          type: string
        bank_name:
          type: string
        account_type:
          type: string
          enum: [ "NRE", "NRO", "FCNR", "SAVINGS" ]
        currency:
          type: string
          default: "INR"
        balance:
          type: number
        tds_status:
          type: string
          description: Tax Deducted at Source status for the current FY.
        repatriable:
          type: boolean
          description: True for NRE/FCNR, limited for NRO.

    HarvestRequest:
      type: object
      properties:
        target_amount_usd:
          type: number
        user_tax_residency:
          type: string
          enum: [ "US_RESIDENT", "NRI_INDIA", "EU_RESIDENT" ]
        include_unrealized_gains:
          type: boolean
          default: true

    OptimizationResult:
      type: object
      properties:
        suggested_source:
          type: string
          enum: [ "USD_WALLET", "NRE_CONVERSION", "STOCK_LIQUIDATION" ]
        estimated_tax_impact_usd:
          type: number
        dtaa_benefit_applied:
          type: boolean
          description: Benefit under Double Tax Avoidance Agreement.
        lrs_remaining_limit_usd:
          type: number
          description: India Liberalized Remittance Scheme ($250k cap).

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
```

---

## ⚖️ 3. Compliance Logic: DTAA & LRS
- **DTAA (Double Tax Avoidance Agreement)**: The engine detects if income earned in India (e.g., FD interest in NRO) is already taxed and provides a "Foreign Tax Credit (FTC)" estimate for the US 1040.
- **LRS (Liberalized Remittance Scheme)**: Tracks the $250,000 yearly cap for Resident Indians (transfers out of India) and the 1-Million limit for NRIs (NRO to NRE).

---

## 🏗️ 4. Build Call
**Instruction to LLM:** "Write the Python service for the 'Wealth Tax Engine'. It must implement the `calculate_it_return_deductions` function that applies the Section 80C [India] limits and the `calculate_1040_foreign_tax_credit` flow based on the provided NRO interest income."
