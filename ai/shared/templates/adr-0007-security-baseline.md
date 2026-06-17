# ADR-0007: Security Baseline

| | |
|---|---|
| **Status** | Draft — complete before the first Tier 3 change or before any change touching auth, payments, or PII |
| **Date** | [fill in] |
| **Deciders** | [fill in: architect, security lead or dev lead] |
| **Supersedes** | — |
| **Related** | ADR-0001 (HITL adoption), ADR-0004 (change tier policy), ADR-0005 (observability) |

---

## 1. Context

The HITL workflow runs `/hitl:review-security` at Step 20 of every Tier 2+ change and `/hitl:ops-pentest` before production deploys of Tier 3+ changes. Both skills need to know the project's defined security baseline — what standards apply, what tools are in use, and what is explicitly out of scope — to give meaningful output rather than generic checklists.

## 2. Decision

### Secret management

| Secret type | Storage approach | Notes |
|---|---|---|
| App secrets (DB passwords, API keys) | [fill in — e.g., AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager / env vars in CI] | |
| CI/CD secrets | [fill in — e.g., GitHub Actions secrets] | |
| Local development | [fill in — e.g., `.env` file gitignored, template in `.env.example`] | |

**Hard rules:**
- Secrets must never be committed to git — enforced by [fill in: pre-commit hook / secret scanning / gitleaks]
- Secrets must never be set as plain environment variables in production containers — must use a vault reference

### Dependency vulnerability scanning

| Tool | Scope | Action on HIGH/CRITICAL finding |
|---|---|---|
| [fill in — e.g., Dependabot / Snyk / OWASP Dependency Check] | [e.g., all production dependencies] | [e.g., block PR / notify / auto-PR fix] |

Update cadence: [fill in — e.g., weekly automated PRs for patch updates; manual review for minor/major]

### Static analysis (SAST)

| Tool | Runs when | Blocks PR on finding? |
|---|---|---|
| [fill in — e.g., CodeQL / Semgrep / SonarQube / none] | [e.g., every PR] | [fill in — yes for HIGH+] |

### Security review gates

| Trigger | Required action |
|---|---|
| Any Tier 2+ change | `/hitl:review-security` at Step 20 of the 31-step workflow — mandatory, not advisory |
| Any change touching auth, payments, or PII | Additional architect security sign-off before PR merge |
| Tier 3+ production deploy | `/hitl:ops-pentest` before deploy — targeted scan of changed surface |
| Annual or post-incident | Full penetration test by [fill in: internal team / external vendor] |

### Authentication and authorisation (platform level)

[fill in — This covers platform/infrastructure auth, not application-level auth (which is in a domain ADR). Examples: "All cloud resources accessed via IAM roles — no long-lived access keys. Developers use SSO via [provider]. Production access requires MFA."]

### Compliance scope

[fill in — e.g., SOC 2 Type II, ISO 27001, GDPR, HIPAA, PCI DSS, or "none currently required". Record what is in scope and what is explicitly out of scope.]

| Standard | In scope | Notes |
|---|---|---|
| [fill in] | [yes / no / partial] | |

## 3. Alternatives Considered

[fill in — e.g., "Evaluated Snyk vs Dependabot for dependency scanning. Chose Dependabot because it is native to GitHub and covers both security and version updates without an additional subscription."]

## 4. Consequences

### Positive
- `/hitl:review-security` can enforce project-specific standards rather than generic OWASP defaults
- Secret leaks are caught before they reach git history
- Compliance scope is explicit — auditors have a starting point

### Negative
- [fill in — e.g., "SAST introduces ~3 minute CI overhead per PR. Accepted."]

## 5. Implementation Notes

- The pre-commit hook for secret scanning must be configured in the repo root — do not rely on developers installing it manually
- `/hitl:ops-pentest` reads this ADR to scope its scan — keep the compliance scope section current
- Any exception to the hard rules (e.g., a secret in an env var for a legacy component) must be documented here with a remediation date

## 6. Open Questions

1. [ ] Which compliance standards apply now and which are anticipated within 12 months?
2. [ ] Is there an existing security escalation path for critical vulnerabilities found in production?
3. [ ] What is the agreed SLA for patching CRITICAL dependency vulnerabilities? (HITL recommendation: ≤48h)

## ROI Estimate

**Value dimension:** Risk / Compliance
**Expected outcome:** No HIGH+ vulnerabilities go undetected for more than [fill in] days; secret leaks blocked at pre-commit
**Baseline metric:** [fill in: current CVSS score distribution in dependencies, any known outstanding vulnerabilities]
**Expected cost:** [fill in: tooling cost + setup time]
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
