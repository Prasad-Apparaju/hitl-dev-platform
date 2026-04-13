# [Project Name] — Security Audit Report

**Date:** YYYY-MM
**Scope:** [What was audited — design docs, source code, infrastructure config, deployed system]
**Findings:** N CRITICAL | N HIGH | N MEDIUM | N LOW

---

## Finding Summary

| ID | Severity | Finding | Component |
|----|:--------:|---------|-----------|
| C-1 | CRITICAL | [One-line description] | [Component/domain] |
| H-1 | HIGH | [One-line description] | [Component/domain] |
| M-1 | MEDIUM | [One-line description] | [Component/domain] |
| L-1 | LOW | [One-line description] | [Component/domain] |

---

## Severity Definitions

| Severity | Definition | Expected Response |
|----------|-----------|-------------------|
| CRITICAL | Exploitable in production, data loss or unauthorized access likely | Fix before launch or next release |
| HIGH | Exploitable with effort, significant impact if exploited | Fix within current sprint |
| MEDIUM | Limited exploitability or impact, defense-in-depth concern | Fix within next 2 sprints |
| LOW | Best practice gap, minimal direct risk | Track, fix when convenient |

---

## CRITICAL Findings — Detail

### C-1: [Finding Title]

[Detailed description of the vulnerability — what it is, how it can be exploited, what data/systems are at risk.]

**Affected files/components:**
- `path/to/file.py`
- `path/to/config.yaml`

**Remediation:**
1. [Specific fix step]
2. [Specific fix step]

**Verification:** [How to confirm the fix works — test to add, check to run]

**Status:** Open | In Progress | Fixed (PR #N)

---

## HIGH Findings — Detail

### H-1: [Finding Title]

[Same structure as CRITICAL]

---

## MEDIUM Findings — Detail

### M-1: [Finding Title]

[Same structure as CRITICAL]

---

## LOW Findings — Detail

### L-1: [Finding Title]

[Same structure as CRITICAL]

---

## Remediation Tracking

| ID | Severity | Status | Fix PR | Regression Test | Verified |
|----|:--------:|:------:|:------:|:---------------:|:--------:|
| C-1 | CRITICAL | Open | — | — | — |
| H-1 | HIGH | Open | — | — | — |

---

## Common Vulnerability Categories to Check

Use this as an audit checklist. Not all categories apply to every project.

| Category | What to look for |
|----------|-----------------|
| **Injection** | SQL injection, NoSQL injection, command injection, prompt injection (LLM systems) |
| **Authentication** | Weak password policy, missing MFA, insecure token storage, key rotation |
| **Authorization** | Missing RBAC, privilege escalation, IDOR |
| **Data exposure** | PII in logs/traces, unencrypted storage, overly broad API responses |
| **External APIs** | Missing rate limiting, no idempotency on mutating calls, unvalidated webhooks |
| **File handling** | No content validation (magic bytes), path traversal, missing size limits |
| **Infrastructure** | Unauthenticated internal services, missing network policies, `:latest` tags |
| **Secrets** | Hardcoded credentials, unrotated keys, secrets in environment variables vs. vault |
| **Dependencies** | Unpinned versions, known CVEs, unused dependencies |
| **Observability** | PII leaking into traces/metrics, debug endpoints exposed in production |

---

## Next Audit

**Scheduled:** [date]
**Trigger:** Any CRITICAL finding should trigger a focused re-audit of that area within 2 weeks of the fix.
