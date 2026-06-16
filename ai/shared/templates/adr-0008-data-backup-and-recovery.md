# ADR-0008: Data Backup and Recovery

| | |
|---|---|
| **Status** | Draft — complete before the first production data write |
| **Date** | [fill in] |
| **Deciders** | [fill in: architect, ops/platform lead] |
| **Supersedes** | — |
| **Related** | ADR-0004 (change tier policy), ADR-0005 (observability), ADR-0007 (security baseline) |

---

## 1. Context

The HITL workflow includes `/hitl:ops-backup-database` (run before any Tier 3+ database migration) and expects a tested restore procedure before any production deploy that modifies persistent data. Without a defined backup and recovery policy, these skills cannot enforce meaningful pre-flight checks and the team has no agreed RTO/RPO targets to verify against.

## 2. Decision

### Recovery objectives

| Objective | Target | Rationale |
|---|---|---|
| **RPO** (Recovery Point Objective — maximum acceptable data loss) | [fill in — e.g., 1 hour / 15 minutes / near-zero] | |
| **RTO** (Recovery Time Objective — maximum time to restore service) | [fill in — e.g., 4 hours / 30 minutes] | |

### Databases and stores

For each data store, record the backup approach:

| Store | Type | Backup tool | Frequency | Retention | Location |
|---|---|---|---|---|---|
| [fill in — e.g., PostgreSQL main DB] | [relational] | [fill in — e.g., pg_dump / AWS RDS automated backup] | [fill in — e.g., daily full + hourly WAL] | [fill in — e.g., 30 days] | [fill in — e.g., S3 `prod-backups/`] |
| [fill in — e.g., Redis cache] | [cache] | [fill in — e.g., RDB snapshots] | [fill in] | [fill in] | [fill in] |
| [fill in — e.g., Uploaded files] | [object storage] | [fill in — e.g., S3 versioning + cross-region replication] | [continuous] | [fill in] | [fill in] |

### Restore procedure

[fill in — step-by-step restore procedure, or link to runbook at `docs/04-operations/runbooks/restore.md`]

The restore procedure must be documented well enough that an on-call engineer who was not part of the original setup can execute it at 2am.

**Who can authorise a restore:**
[fill in — e.g., "Any Ops lead or on-call engineer. Notify the engineering manager within 30 minutes of initiating a restore."]

### Backup verification

| Check | Frequency | Owner |
|---|---|---|
| Automated restore test (non-production) | [fill in — e.g., weekly] | [fill in] |
| Manual restore drill (full production restore to staging) | [fill in — e.g., quarterly] | [fill in] |
| Backup integrity check (hash verification) | [fill in — e.g., daily, automated] | [fill in] |

A backup that has never been tested is not a backup.

### Pre-deploy backup gate

For any HITL change that modifies persistent data (Tier 2+), `/hitl:ops-backup-database` runs before the migration and records:
```yaml
backup:
  taken_at: <ISO timestamp>
  location: <path or S3 URI>
  verified: true|false
```
Deploy is blocked if `verified: false`.

### Encryption and access

| Aspect | Approach |
|---|---|
| Backup encryption at rest | [fill in — e.g., AES-256 via S3 SSE-KMS] |
| Backup encryption in transit | [fill in — e.g., TLS 1.2+] |
| Access control | [fill in — e.g., IAM role `backup-restore-role` — restricted to Ops leads] |
| Cross-region replication | [fill in — yes for production / no] |

## 3. Alternatives Considered

[fill in — e.g., "Evaluated point-in-time recovery via AWS RDS vs daily pg_dump. Chose RDS PITR because it achieves our 15-minute RPO without custom scripting."]

## 4. Consequences

### Positive
- RTO/RPO targets are defined before an incident — not negotiated under pressure
- `/hitl:ops-backup-database` has a verified procedure to enforce
- Audit evidence of backup testing is available for compliance reviews

### Negative
- [fill in — e.g., "Cross-region replication adds ~$X/month in S3 transfer costs. Accepted given the RPO requirement."]

## 5. Open Questions

1. [ ] What are the RTO/RPO requirements? Are they defined by a business SLA or a best-effort target?
2. [ ] Has a restore drill been performed recently? When was the last successful restore from backup?
3. [ ] Are there any data stores currently without a backup? (e.g., queues, ephemeral caches — are they in scope?)
4. [ ] Who is the on-call owner for data recovery incidents?

## ROI Estimate

**Value dimension:** Risk / Operability
**Expected outcome:** Restore achievable within RTO in a verified drill; every production data migration has a verified pre-deploy backup
**Baseline metric:** [fill in: last known backup test date, current estimated RTO if untested]
**Expected cost:** [fill in: storage cost + restore drill time]
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
