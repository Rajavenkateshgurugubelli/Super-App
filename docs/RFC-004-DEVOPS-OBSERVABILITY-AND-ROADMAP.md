# RFC-004: DevOps, Observability, and Execution Roadmap

> **Status:** PROPOSED | **Created:** 2026-03-27 | **Depends On:** RFC-001, RFC-002, RFC-003

---

## 1. Infrastructure as Code (Terraform)

### 1.1. Multi-Region Strategy

Extending existing `terraform/main.tf` (AWS EKS + VPC) to three regions:

```
terraform/
├── modules/
│   ├── vpc/              # Reusable VPC module
│   ├── eks/              # Reusable EKS module
│   ├── cockroachdb/      # CRDB StatefulSet on EKS
│   ├── redis/            # ElastiCache Redis cluster
│   ├── kafka/            # MSK (Managed Streaming for Kafka)
│   └── observability/    # Prometheus + Grafana + Jaeger
├── environments/
│   ├── dev/              # Single-region (us-east-1)
│   ├── staging/          # Dual-region (us-east-1 + eu-west-1)
│   └── prod/
│       ├── us-east-1/    # US production
│       ├── eu-west-1/    # EU production
│       └── ap-south-1/   # India production
├── main.tf               # Existing (extended)
├── variables.tf          # Existing (extended)
├── backend.tf            # S3 remote state + DynamoDB locking
└── versions.tf
```

### 1.2. Region Module (Reusable per-region deployment)

```hcl
# terraform/modules/region/main.tf
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name    = "${var.environment}-superapp-${var.region_short}"
  cidr    = var.vpc_cidr
  azs     = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets
  enable_nat_gateway = true
  single_nat_gateway = var.environment != "prod"
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.0"
  cluster_name    = "${var.environment}-superapp-${var.region_short}"
  cluster_version = "1.30"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    core = {
      min_size = var.environment == "prod" ? 3 : 1
      max_size = var.environment == "prod" ? 15 : 3
      desired_size = var.environment == "prod" ? 3 : 1
      instance_types = var.environment == "prod" ? ["m6i.xlarge"] : ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      labels = { role = "core-services" }
    }
    spot = {
      min_size = 0
      max_size = var.environment == "prod" ? 10 : 2
      desired_size = 0
      instance_types = ["m6i.xlarge", "m5.xlarge", "m5a.xlarge"]
      capacity_type  = "SPOT"
      labels = { role = "mini-app-workloads" }
    }
  }
}

module "msk" {
  source             = "terraform-aws-modules/msk-kafka-cluster/aws"
  name               = "${var.environment}-superapp-kafka-${var.region_short}"
  kafka_version      = "3.5.1"
  number_of_nodes    = var.environment == "prod" ? 3 : 1
  instance_type      = var.environment == "prod" ? "kafka.m5.large" : "kafka.t3.small"
  ebs_volume_size    = var.environment == "prod" ? 500 : 50
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  encryption_in_transit = { client_broker = "TLS" }
}
```

### 1.3. Remote State Configuration

```hcl
# terraform/backend.tf
terraform {
  backend "s3" {
    bucket         = "superapp-terraform-state"
    key            = "global/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "superapp-terraform-locks"
    kms_key_id     = "alias/terraform-state-key"
  }
}
```

---

## 2. CI/CD Pipeline

### 2.1. Pipeline Architecture

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Git Push │───►│ Build &  │───►│ Security │───►│ Deploy   │───►│ Promote  │
│          │    │ Test     │    │ Scan     │    │ Canary   │    │ or       │
│          │    │          │    │          │    │ (10%)    │    │ Rollback │
└─────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 2.2. Core Backend Pipeline

```yaml
# .github/workflows/backend-deploy.yml
name: Backend CI/CD
on:
  push:
    branches: [main]
    paths: ['app/**', 'gateway/**', 'protos/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=app --cov-report=xml
      - run: flake8 app/ gateway/ --max-line-length=120

  security:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: pip audit
      - run: trivy image superapp-backend:${{ github.sha }}
      - run: semgrep --config=auto app/ gateway/

  build:
    needs: security
    runs-on: ubuntu-latest
    steps:
      - run: docker build -t $ECR_REPO:${{ github.sha }} .
      - run: docker push $ECR_REPO:${{ github.sha }}

  deploy-canary:
    needs: build
    strategy:
      matrix:
        region: [us-east-1, eu-west-1, ap-south-1]
    steps:
      - name: Deploy Canary (10% traffic)
        run: |
          kubectl set image deployment/superapp-backend \
            backend=$ECR_REPO:${{ github.sha }} \
            --namespace=superapp-${{ matrix.region }}
          kubectl annotate deployment/superapp-backend \
            "flagger.app/canary-weight=10"

      - name: Monitor (10 min)
        run: |
          sleep 600
          ERROR_RATE=$(curl -s "$PROMETHEUS/api/v1/query?query=rate(http_requests_total{status=~'5..'}[5m])" | jq '.data.result[0].value[1]')
          P95=$(curl -s "$PROMETHEUS/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))" | jq '.data.result[0].value[1]')
          if (( $(echo "$ERROR_RATE > 0.01 || $P95 > 0.5" | bc -l) )); then
            echo "Canary failed. Rolling back."
            kubectl rollout undo deployment/superapp-backend
            exit 1
          fi

      - name: Promote to 100%
        if: success()
        run: kubectl annotate deployment/superapp-backend "flagger.app/canary-weight=100"
```

### 2.3. Mini-App Independent Pipeline

Mini-apps deploy independently (see RFC-003 Section 6.4). They bypass the core backend pipeline entirely — deployed as static bundles to S3/CloudFront, versioned via the Mini-App Registry manifest.

---

## 3. Observability

### 3.1. Distributed Tracing — Cross-Region Request Flow

The existing OpenTelemetry + Jaeger setup is extended for cross-region correlation:

```
User in India opens wallet → CDN → ap-south-1 Gateway → UserService (ap-south-1)
                                                       → WalletService (ap-south-1)
                                                       → PaymentOrchestrator (ap-south-1)
                                                         → Stripe API (US external)
                                                         → Fraud Detection (Kafka → ML model)
                                                       → LedgerWrite (CockroachDB ap-south-1)
                                                       → Kafka: payment.completed
                                                         → NotificationService (ap-south-1)
                                                         → AnalyticsConsumer → ClickHouse

Full trace spans ~8 services across 2 regions and 1 external API.
All correlated via W3C Trace Context (traceparent header).
```

**OTel Collector Configuration (per region):**

```yaml
# kubernetes/observability/otel-collector.yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: "0.0.0.0:4317" }
      http: { endpoint: "0.0.0.0:4318" }

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024
  attributes:
    actions:
      - key: deployment.region
        value: "${REGION}"
        action: upsert
  tail_sampling:
    policies:
      - name: error-traces
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: high-latency
        type: latency
        latency: { threshold_ms: 1000 }
      - name: sample-rest
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }

exporters:
  otlp/jaeger:
    endpoint: "jaeger-collector.observability:4317"
    tls: { insecure: true }
  prometheus:
    endpoint: "0.0.0.0:8889"
  otlp/central:  # Cross-region trace aggregation
    endpoint: "otel-central.superapp.global:4317"
    tls: { cert_file: /certs/client.crt, key_file: /certs/client.key }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, attributes, tail_sampling]
      exporters: [otlp/jaeger, otlp/central]
    metrics:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [prometheus]
```

### 3.2. Key Dashboards (Extending Existing Grafana)

| Dashboard | Key Panels | Alert Threshold |
|---|---|---|
| **API Gateway** | Request rate, P95 latency, 5xx rate, auth failures | 5xx > 1%, P95 > 500ms |
| **Payment Engine** | TPS, success rate, avg settlement time, DLQ depth | Success < 99%, DLQ > 100 |
| **Cross-Region** | Inter-region latency heatmap, CRDB replication lag | Replication lag > 5s |
| **Mini-App Health** | Load time per app, crash rate, bridge call errors | Crash rate > 2% |
| **Compliance** | Erasure request queue depth, KYC pending count | Erasure > 30 days old |

---

## 4. Execution Epics

Ordered by critical path dependencies. Each epic includes acceptance criteria suitable for direct import into Jira.

### Epic 1: Global IAM Foundation (Weeks 1-4)
**Depends on:** Nothing (critical path start)

| Story | Acceptance Criteria |
|---|---|
| Split User model → User + UserPII | Alembic migration passes. Existing tests green. PII table has region column. |
| Implement KYC Orchestrator service | `/api/kyc/initiate` accepts region-specific documents. Mock providers return KYC status. |
| Deploy CockroachDB 3-region cluster | `cockroach node status` shows 9 nodes across 3 regions. Geo-fencing smoke test passes. |
| JWT key rotation via Vault | JWKS endpoint returns current + previous key. Token signed with old key validates for 7 days. |
| GDPR erasure pipeline | `POST /api/user/erasure-request` queues erasure. Kafka consumers delete data. Reconciliation confirms. |

### Epic 2: Double-Entry Ledger & Wallet Engine (Weeks 3-6)
**Depends on:** Epic 1 (User model)

| Story | Acceptance Criteria |
|---|---|
| Implement LedgerEntry + AccountBalance models | Alembic migration. Sum of debits equals credits invariant enforced in DB constraint. |
| Wallet transfer via ledger (replace current) | Existing transfer tests pass using new ledger. Balance consistency test with 1000 concurrent transfers. |
| Settlement accounts per region | System accounts created on startup. Daily balance report generated. |
| FX conversion through ledger | Cross-currency transfer creates proper debit/credit pairs with FX spread entries. |

### Epic 3: Payment Rail Integration (Weeks 5-8)
**Depends on:** Epic 2 (Ledger)

| Story | Acceptance Criteria |
|---|---|
| PaymentRailRouter implementation | Router returns correct rail for all 9 corridor combinations. Unit tests with 100% coverage. |
| Stripe integration (US) | Card payment E2E: tokenize → charge → webhook → ledger entry. Sandbox tests pass. |
| UPI integration via Razorpay (India) | UPI collect request → callback → ledger entry. VPA validation. Sandbox tests pass. |
| SEPA integration via Plaid EU | SEPA instant transfer E2E in sandbox. PSD2 SCA flow tested. |
| Fraud detection pipeline | Kafka stream processor scores transactions. Blocked transactions routed to review queue. |

### Epic 4: Multi-Region Infrastructure (Weeks 4-7)
**Depends on:** Epic 1 (IAM for region-aware routing)

| Story | Acceptance Criteria |
|---|---|
| Terraform modules for 3-region EKS | `terraform plan` clean for all 3 regions. `terraform apply` creates clusters in staging. |
| Istio multi-cluster mesh | mTLS between all services. Cross-cluster service discovery works. |
| Kafka MirrorMaker 2 cross-region | Events produced in ap-south-1 visible in us-east-1 analytics topic within 30s. |
| Route53 geo-routing | DNS resolution from India returns ap-south-1 endpoint. Failover tested. |
| CockroachDB geo-fencing validation | PII write for EU user from US node → CockroachDB routes to eu-west-1 range. Verified via `SHOW RANGES`. |

### Epic 5: Mini-App Platform (Weeks 6-10)
**Depends on:** Epic 1 (Auth), Epic 2 (Wallet for checkout bridge)

| Story | Acceptance Criteria |
|---|---|
| Bridge SDK v1.0 | Published to npm. All 10 capabilities tested: location, camera, pay, storage, auth, analytics, haptics, share, navigation, clipboard. |
| OTA manifest system | Manifest served from CDN. Shell loads correct mini-app version. Canary rollout at 10% works. |
| Mobile shell (React Native) | App boots on iOS + Android. WebView loads wallet mini-app. Bridge calls work. |
| Developer CLI scaffold | `npx @superapp/create-mini-app test-app` generates working project. `npm run dev` starts with mocked bridge. |
| Security sandbox enforcement | Mini-app cannot access localStorage of another mini-app. CSP blocks unauthorized network calls. |

### Epic 6: Observability & Monitoring (Weeks 7-9)
**Depends on:** Epic 4 (Infrastructure deployed)

| Story | Acceptance Criteria |
|---|---|
| OTel Collector per-region | Traces from all services appear in Jaeger. Cross-region trace stitching works. |
| Grafana dashboards (5 dashboards) | All panels from Section 3.2 rendering. PagerDuty alerts configured. |
| Tail sampling | Only error traces + high-latency traces + 10% sample stored. Storage reduction > 80%. |
| SLO monitoring | 99.99% availability SLO tracked. Error budget burn rate alerts at 50% and 80%. |

### Epic 7: Compliance Automation (Weeks 8-11)
**Depends on:** Epic 1 (IAM), Epic 2 (Ledger), Epic 4 (Multi-region)

| Story | Acceptance Criteria |
|---|---|
| Automated reconciliation (daily) | T+1 reconciliation runs. Report generated in `compliance_reports/`. Discrepancy alerts fire. |
| Data residency enforcement middleware | PII write to wrong region raises `DataResidencyViolationError`. 100% of write paths covered. |
| Consent management (GDPR) | User can grant/revoke per-purpose consent. Consent state stored in UserPII. Marketing emails respect consent. |
| RBI data localization audit | Automated script verifies no Indian PII exists in us-east-1 or eu-west-1 CRDB nodes. |

### Epic 8: Load Testing & Chaos Engineering (Weeks 10-12)
**Depends on:** All previous epics

| Story | Acceptance Criteria |
|---|---|
| Load test suite (extending `app/scripts/load_test.py`) | 10,000 TPS sustained for 30 min per region. P95 < 500ms. Zero data loss. |
| Chaos: kill a CRDB node | Raft leader election completes in < 10s. No failed transactions during failover. |
| Chaos: region outage simulation | DNS failover redirects traffic within 30s. Financial data integrity preserved. |
| Chaos: Kafka broker failure | DLQ captures in-flight messages. Retry succeeds after broker recovery. |
| Production readiness review | All SLOs met. Security scan clean. Compliance audit passed. Go/no-go decision. |

---

## 5. Timeline Visualization

```
Week:  1    2    3    4    5    6    7    8    9    10   11   12
       ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
Epic1: ████████████████
Epic2:           ████████████████
Epic3:                     ████████████████
Epic4:                ████████████████
Epic5:                          ████████████████████
Epic6:                                    ██████████
Epic7:                                         ████████████
Epic8:                                                   ████████
```

**Critical Path:** Epic 1 → Epic 2 → Epic 3 → Epic 8 (Production Readiness)

---

*End of RFC-004*
