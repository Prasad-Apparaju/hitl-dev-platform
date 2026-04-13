# [Project Name] — Infrastructure Cost Analysis

**Date:** YYYY-MM
**Last verified:** [date — cloud pricing changes frequently]

> Cloud pricing is dynamic. Spot/preemptible prices fluctuate. All prices are USD/month unless noted. Verify against provider pricing pages before committing.

---

## Environment Summary

| Environment | Purpose | Always-on? | Estimated monthly cost |
|-------------|---------|:----------:|----------------------:|
| Local dev | Developer machines | N/A | $0–30 (API calls only) |
| Dev/staging | Shared test environment | Partial | $XX |
| Production | Live traffic | Yes | $XXX |

---

## Compute Comparison

### GPU Instances (if applicable)

| Provider | Instance | GPU | vCPU | RAM | On-Demand/hr | Spot/hr | Monthly On-Demand |
|----------|----------|-----|------|-----|:------------:|:-------:|------------------:|
| AWS | g6.xlarge | 1x L4 | 4 | 16 GB | $X.XX | $X.XX | $XXX |
| GCP | g2-standard-4 | 1x L4 | 4 | 16 GB | $X.XX | $X.XX | $XXX |
| Azure | NC4as_T4_v3 | 1x T4 | 4 | 28 GB | $X.XX | $X.XX | $XXX |

### App Instances (no GPU)

| Provider | Instance | vCPU | RAM | On-Demand/hr | Monthly |
|----------|----------|------|-----|:------------:|--------:|
| AWS | t3.medium | 2 | 4 GB | $X.XX | $XX |
| GCP | e2-medium | 2 | 4 GB | $X.XX | $XX |
| Azure | B2s | 2 | 4 GB | $X.XX | $XX |

---

## Storage Comparison

| Provider | Service | Storage/GB/mo | Egress/GB | Notes |
|----------|---------|:-------------:|:---------:|-------|
| AWS | S3 Standard | $0.023 | $0.09 | |
| GCP | GCS Standard | $0.020 | $0.12 | |
| Azure | Blob Hot | $0.018 | $0.087 | |

---

## Managed Services Comparison

| Service | AWS | GCP | Azure | Notes |
|---------|-----|-----|-------|-------|
| Kubernetes | EKS ($73/mo) | GKE (free zonal) | AKS (free) | GKE Autopilot charges per pod |
| Database | RDS PostgreSQL | Cloud SQL | Azure DB | Compare vCPU + storage pricing |
| Vector DB | Self-hosted | Self-hosted | Self-hosted | Managed options: Pinecone, Weaviate Cloud |

---

## Cost Optimization Strategies

| Strategy | Savings | Trade-off |
|----------|:-------:|-----------|
| Spot/preemptible instances | 60–70% | Can be preempted; need graceful shutdown |
| Reserved/committed use (1yr) | 30–40% | Locked in for 1 year |
| Scale-to-zero (dev/staging) | 80–90% | Cold start latency on resume |
| Auto-shutdown timer | 50–70% | Must handle state persistence |
| Right-sizing | 10–30% | Requires monitoring actual usage first |

---

## Per-Environment Cost Breakdown

### Local Development

| Component | Monthly cost | Notes |
|-----------|------------:|-------|
| API calls (LLM providers) | $5–20 | Depends on usage |
| Cloud storage (dev prefix) | $1–5 | Small datasets |
| **Total** | **$5–30** | |

### Dev/Staging (cloud)

| Component | Monthly cost | Notes |
|-----------|------------:|-------|
| Compute | $XX | [instance types, hours/day] |
| Database | $XX | [instance type] |
| Storage | $XX | [estimated GB] |
| Networking | $XX | |
| **Total** | **$XX** | |

### Production

| Component | Monthly cost | Notes |
|-----------|------------:|-------|
| Compute | $XXX | [instance types, scaling config] |
| Database | $XXX | [instance type, HA config] |
| GPU (if applicable) | $XXX | [instance type, hours/day] |
| Storage | $XX | [estimated GB, lifecycle rules] |
| Monitoring | $XX | [self-hosted vs managed] |
| Networking / CDN | $XX | |
| **Total** | **$XXX** | |

---

## Recommendation

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary cloud | [provider] | [why — pricing, GPU availability, team expertise] |
| GPU strategy | [on-demand / spot / reserved] | [cost vs reliability tradeoff] |
| Dev environment | [ephemeral / always-on] | [cost vs convenience] |
| Commitment | [none / 1yr CUD / 3yr CUD] | [only after 3+ months of stable usage data] |

---

## Review Schedule

Re-evaluate costs quarterly or when:
- Monthly spend exceeds budget by >20%
- New GPU/instance types become available
- Workload profile changes significantly (e.g., scaling to more users)
