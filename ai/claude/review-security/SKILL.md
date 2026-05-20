---
name: review-security
description: Security review at three points in the workflow — threat model the design before implementation, SAST scan the generated code before architect code review, and run a periodic system-wide security baseline. Each phase is independent; run only the phase that matches your workflow position. Required for Tier 3+ auth/payments/data changes; recommended for Tier 2+.
argument-hint: "[--phase design|code|system] [change ID or issue number]"
disable-model-invocation: true
---

# Security Review

Security is reviewed at three distinct points in the workflow — threat modeling the design before code is written, SAST analysis of the generated code before architect code review, and a periodic system-wide baseline scan. Each phase is independent.

**Input:** $ARGUMENTS
- `--phase design <issue-or-change-ID>` — Step 5 (post-HLD, before LLD): threat model the feature design
- `--phase code <change-ID>` — Step 17 (post-refactor, before architect code review): SAST + code-level security checklist
- `--phase system` — scheduled: system-wide SAST baseline (no change ID required)

**Tier gate:**
- Tier 3+ (auth, payments, data model, cross-domain): both `--phase design` and `--phase code` are **required**
- Tier 2 (normal feature): both phases are **recommended**; skip only with explicit lead sign-off recorded in `.hitl/current-change.yaml`
- Tier 0–1: skip unless the change touches auth or secrets handling

---

## Phase: Design (`--phase design`)

Run after HLD is approved, before LLD is written. Threat modeling at this point is cheap — changes are still in documents. After the LLD, changes cost implementation time.

---

### Progress Banners (design phase)

Format: `---` line, `**Security Review (Design) — Step N / 3: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Data Flow + Trust Boundaries | `▶ Data Flow · ○ STRIDE Threats · ○ Report` |
| 2 | STRIDE Threat Enumeration | `✅ Data Flow · ▶ STRIDE Threats · ○ Report` |
| 3 | Report + Design Actions | `✅ Data Flow · ✅ STRIDE Threats · ▶ Report` |

---

### Design Step 1 — Data flow and trust boundaries

Read the approved HLD and Phase 1 of the LLD in progress. Map:

**Data flows:** For each data input the feature accepts, trace the path from entry point to storage and to any output:
```
Data flow map — <feature>
──────────────────────────
  [User browser] → POST /api/payment → [PaymentService] → [Stripe API]
                                      → [PaymentsDB — stores card_last4, amount]
                                      → [AuditLog — stores user_id, timestamp, result]
```

**Trust boundaries:** Mark where data crosses a trust boundary (unauthenticated → authenticated, external → internal, user-controlled → system):
```
Trust boundaries:
  [Internet / unauthenticated] ──── TLS ────> [API Gateway] (boundary: auth check here)
  [API Gateway / authenticated] ─────────────> [PaymentService]
  [PaymentService] ──────────────── mTLS ────> [Stripe] (boundary: external service)
```

**Data classification:** What data does this feature handle?
- PII: names, emails, addresses, phone numbers
- Financial: card numbers, account numbers, transaction amounts
- Health: medical data, prescriptions
- Credentials: passwords, tokens, API keys
- Internal: user IDs, business data

State the classification. Higher-classified data requires more scrutiny in the next step.

---

### Design Step 2 — STRIDE threat enumeration

For each component in the data flow, enumerate threats using STRIDE:

| Threat type | Question |
|---|---|
| **Spoofing** | Can an attacker impersonate a user, service, or component? Is identity verified at every trust boundary? |
| **Tampering** | Can an attacker modify data in transit or at rest? Are integrity checks in place? |
| **Repudiation** | Can an attacker deny performing an action? Is there an audit trail for sensitive operations? |
| **Information Disclosure** | Can an attacker access data they should not? What does an error response reveal? |
| **Denial of Service** | Can an attacker exhaust resources? Are rate limits and timeouts designed in? |
| **Elevation of Privilege** | Can an attacker gain permissions above their level? Are authorization checks on every action? |

For each threat found, record:
```
STRIDE finding — <threat-type>
───────────────────────────────
Component:   PaymentService.processPayment()
Threat:      Tampering — amount parameter not re-validated server-side; client could submit modified amount
Severity:    Critical
Mitigation:  Validate amount against server-side price catalog before charging; never trust client-submitted price
Design fix:  Add `price_catalog.lookup(product_id)` before Stripe charge call; log discrepancy if submitted ≠ catalog
```

**Severity classification:**

| Severity | Criteria |
|---|---|
| **Critical** | Threat could lead to auth bypass, data breach, or financial loss without mitigating control |
| **High** | Threat could lead to privilege escalation, data exposure, or significant data integrity failure |
| **Medium** | Threat is partially mitigated or requires unusual attacker conditions |
| **Low** | Defense-in-depth gap; would not succeed without other Critical/High also failing |

---

### Design Step 3 — Report and design actions

```
Security review — Design phase — <feature> (issue #<N>)
─────────────────────────────────────────────────────────
Data classification: <PII | Financial | Credentials | Internal>
Trust boundaries:    <N identified>

STRIDE findings:
  ❌ CRITICAL (N): <short description>
  ⚠️  HIGH (N):    <short description>
  ℹ️  MEDIUM (N):  <short description>
  ✅  LOW (N):

Required design changes before LLD:
  1. <specific change — what to add/modify in the design>
```

Save the threat model to `docs/02-design/technical/threat-model-<feature-slug>.md`.

Update `.hitl/current-change.yaml`:
```yaml
security_review:
  design:
    reviewed_at: <ISO timestamp>
    threat_model: docs/02-design/technical/threat-model-<feature-slug>.md
    findings_critical: <N>
    findings_high: <N>
    result: blocked | findings | clean
```

**If any Critical or High finding exists:** the LLD must address each one before Phase 5 of design-feature can be approved. The `architect-reviewer` must confirm mitigations are in the LLD before approval.

---

## Phase: Code (`--phase code`)

Run after Step 16 (Refactor complete), before Step 17 (Convention Checks). Reviews the generated implementation for security vulnerabilities — white-box, source-level, independent of runtime behavior.

---

### Progress Banners (code phase)

Format: `---` line, `**Security Review (Code) — Step N / 3: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | SAST Scan | `▶ SAST · ○ Code Checklist · ○ Report` |
| 2 | Code Security Checklist | `✅ SAST · ▶ Code Checklist · ○ Report` |
| 3 | Report + Issues | `✅ SAST · ✅ Code Checklist · ▶ Report` |

---

### Code Step 1 — SAST scan

Run the tools appropriate for the project's language stack. Report which were run and which were skipped (and why).

**Semgrep — security rulesets (language-agnostic baseline):**
```bash
# OWASP Top 10 rules
semgrep scan --config "p/owasp-top-ten" --error src/ app/

# General security audit
semgrep scan --config "p/security-audit" --error src/ app/

# Secrets (belt-and-suspenders after check-conventions)
semgrep scan --config "p/secrets" --error src/ app/
```

**Language-specific tools:**

| Language | Tool | Command |
|---|---|---|
| Python | Bandit | `bandit -r src/ app/ -ll -f text` (`-ll` = medium severity and above) |
| JavaScript / TypeScript | ESLint security plugin | `npx eslint --plugin security --rule 'security/detect-*: error' src/` |
| Go | Gosec | `gosec ./...` |
| Ruby | Brakeman | `brakeman --no-pager -w 2` |
| Java | SpotBugs (FindSecBugs) | `spotbugs -textui -effort:max -bug-categories SECURITY` |
| .NET | Security Code Scan | `dotnet build /p:RunSecurityCodeScan=true` |

**Dependency vulnerabilities (belt-and-suspenders after check-conventions):**
```bash
npm audit --audit-level=high   # Node
pip-audit -r requirements.txt  # Python
govulncheck ./...              # Go
```

SAST findings report:
```
SAST results — <change-ID>
───────────────────────────
  ❌ CRITICAL (N):  bandit B105 — hardcoded password in tests/fixtures/user.py:23
  ⚠️  HIGH (N):     semgrep — SQL query built with string concat in app/db.py:87
  ℹ️  MEDIUM (N):   gosec G304 — file path from user input in handlers/upload.go:44
  ✅  LOW (0):
```

Critical and High SAST findings block the PR — do not proceed to Step 18 (Code Review Round 1) with open Critical or High findings.

---

### Code Step 2 — Code-level security checklist

Walk through these checks for the in-scope implementation files — the files changed by this feature, not the entire codebase:

**Input validation**
- [ ] All external inputs (request body, query params, headers, file uploads, env vars at startup) are validated before use
- [ ] Validation happens server-side — never trust client-side validation alone
- [ ] File upload size and type are constrained

**Injection prevention**
- [ ] SQL queries use parameterized queries or an ORM — no string concatenation with user data
- [ ] Shell commands use parameterized execution — no `os.system(user_input)` or equivalent
- [ ] Template rendering uses auto-escaped templates — no raw HTML injection

**Authentication and authorization**
- [ ] Every protected route checks authentication before executing business logic
- [ ] Every protected resource checks authorization — not just "is user logged in?" but "does this user own this resource?"
- [ ] Privilege check happens server-side, not derived from a client-supplied role claim
- [ ] Tokens are validated (signature, expiry, audience) on every request — not cached from a previous valid check

**Data handling**
- [ ] Sensitive data (passwords, tokens, PII) is not logged
- [ ] Sensitive data is not returned in API responses beyond what the caller needs (no over-fetching)
- [ ] Passwords are hashed with a modern algorithm (bcrypt, argon2, scrypt) — never stored or compared in plaintext

**Error handling**
- [ ] Error responses do not include stack traces, internal paths, or database error details
- [ ] Error messages to clients are generic — specific details go to server-side logs only

**Cryptography**
- [ ] No custom cryptography — only approved library implementations
- [ ] No weak algorithms: MD5 or SHA1 for security purposes, DES, RC4, ECB mode

**Session and token management**
- [ ] Session tokens have appropriate expiry
- [ ] Tokens are invalidated on logout — not just dropped client-side
- [ ] Session fixation is not possible (new session ID on login)

For each check: ✅ Pass / ❌ Fail (with file and line) / N/A (with reason).

---

### Code Step 3 — Report and issues

Combine SAST findings and checklist results:

```
Security review — Code phase — <change-ID>
────────────────────────────────────────────
SAST:       Critical N · High N · Medium N · Low N
Checklist:  N/N items passing (N failing)

Blocking (must fix before merge):
  ❌ [file:line] <description>

Non-blocking (document and schedule):
  ℹ️  [file:line] <description>

Result: BLOCKED / FINDINGS / CLEAN
```

Create a GitHub issue for each Critical or High finding (same format as `/ops:pentest`).

Update `.hitl/current-change.yaml`:
```yaml
security_review:
  code:
    reviewed_at: <ISO timestamp>
    sast_tools_run: [semgrep-owasp, bandit, eslint-security]
    findings_critical: <N>
    findings_high: <N>
    checklist_items_failing: <N>
    result: blocked | findings | clean
```

A `blocked` result prevents advancing to Step 18 (Code Review Round 1).

---

## Phase: System (`--phase system`)

Run on a schedule (monthly or after a significant release) across the entire codebase — not scoped to a single change.

Run the same SAST tools as `--phase code` but against all source directories. In addition:

**Access control audit:**
- List all routes/endpoints in the application and their auth requirements
- Flag any endpoint that is accessible without authentication and should not be
- Flag any admin or internal endpoint that lacks explicit role checks

**Dependency baseline:**
```bash
npm audit --audit-level=moderate
pip-audit
govulncheck ./...
```

Report all Critical and High findings as GitHub issues labeled `security,system-scan`. Track in the incident registry if severity warrants it.

Update a standing `docs/04-operations/security-baseline.yaml` with the scan date and finding counts so the next scan can compare.

---

## When to Run

| Phase | When | Gate |
|---|---|---|
| `--phase design` | After HLD approved, before LLD (Step 5) | Required Tier 3+; recommended Tier 2+. LLD cannot be approved until Critical/High findings have mitigations in the design |
| `--phase code` | After Step 16 (Refactor), before Step 17 (Check Conventions) | Required Tier 3+; recommended Tier 2+. Critical/High block PR |
| `--phase system` | Monthly schedule or post-major-release | Not a change gate — raises issues |

---

## Important Rules

- SAST findings are white-box — a finding means the code has the shape of a vulnerability, not necessarily that it is exploitable. Investigate before dismissing as a false positive.
- A SAST finding dismissed as a false positive must be documented with the specific reason — do not suppress rules silently
- Threat modeling is only useful before the LLD — after implementation it produces a list of things to fix, not a list of things to design correctly
- `--phase code` and `/ops:pentest` are complementary, not redundant: this skill finds source-level vulnerabilities; pentest finds runtime vulnerabilities. Both are needed
