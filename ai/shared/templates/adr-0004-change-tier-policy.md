# ADR-0004: Change Tier Classification

| | |
|---|---|
| **Status** | Draft — complete at project kickoff |
| **Date** | [fill in] |
| **Deciders** | [fill in: tech lead, architect] |
| **Supersedes** | — |
| **Related** | ADR-0001 (HITL adoption) |

---

## 1. Context

The HITL workflow scales by tier — Tier 3+ changes require HLD review gates, security reviews, and architect sign-off that Tier 1–2 changes skip. Without project-specific tier definitions, developers make inconsistent classification calls, and high-risk changes may be under-processed.

The generic HITL tier definitions (in `/hitl:dev-practices`) are a starting point. This ADR customizes them for this project's specific risk profile.

## 2. Decision

Apply the following tier definitions for this project:

### Tier 0 — Trivial (standard PR only, no HITL workflow)

[fill in — examples of what qualifies as trivial for this project:]
- Typo or comment fix
- Config value change with no behavioral impact
- Log message or error string wording

### Tier 1 — Bug fix (abbreviated workflow: issue + code/test steps; skip training plan)

[fill in — examples:]
- Regression fix for a specific reported and reproducible bug
- Minor behavioral correction within a single function
- Dependency patch with no public API changes

### Tier 2 — Normal feature (full workflow)

[fill in — examples:]
- New API endpoint or UI screen within a single domain
- Change touching 1–2 files within a bounded scope
- Performance optimization with a clear, measurable target

### Tier 3 — Non-trivial / high-risk (full workflow + HLD review gate + security review)

**Always Tier 3 for this project — fill in the list that applies:**
- [ ] Any change to authentication or authorization logic
- [ ] Any change to payment or billing processing
- [ ] Any change to data models requiring a migration
- [ ] Any AI model selection, prompt engineering, or inference pipeline change
- [ ] Any cross-domain change touching more than 2 domains
- [ ] Any change to [fill in: project-specific high-risk area]

### Tier 4 — Incident / P0 (fix first, full docs within 48 hours)

[fill in: define what constitutes a P0 for this project — e.g., "any outage affecting >X% of users or any data loss event"]

### Tie-breaking rule

When in doubt, default up. If a change could plausibly be Tier 2 or Tier 3, treat it as Tier 3. The cost of the extra process is lower than the cost of an under-reviewed high-risk change.

## 3. Alternatives Considered

### Alt 1: Always use the full Tier 2 workflow for everything
Simpler to communicate. Rejected because: Tier 0/1 changes don't need HLD/LLD; over-processing trivial changes creates friction and incentivizes bypassing the process entirely.

### Alt 2: Developer discretion on tier (no predefined rules)
Maximum flexibility. Rejected because: under deadline pressure, developers consistently under-tier changes; explicit rules reduce cognitive load and create a clear basis for disagreements in review.

## 4. Consequences

### Positive
- High-risk changes reliably get the full process
- Low-risk changes are not over-processed
- Clear criteria reduce debate in code review about "did this need an LLD?"

### Negative
- Edge cases still require judgment — the tie-breaking rule handles them
- The Tier 3 list must be kept current as the system evolves (add domains here when they become high-risk)

## 5. Implementation Notes

The tier is recorded in `.hitl/current-change.yaml` at step 3 (`/hitl:dev-apply-change`). The 31-step workflow branches on this value — skipping or adding gates accordingly.

Review this ADR whenever a new high-risk domain is added to `docs/system-manifest.yaml`.

## 6. Open Questions

1. [fill in: any ambiguous cases for this project's Tier 2/3 boundary]
2. [fill in: does the team want a lightweight "Tier 1.5" for small features that don't warrant a full LLD?]

## 7. Status

**Draft.** Complete and accept at project kickoff before the first Tier 2 change. Assign to: [fill in: tech lead].

## ROI Estimate

**Value dimension:** Risk / Quality
**Expected outcome:** No Tier 3 change is accidentally processed as Tier 2
**Baseline metric:** [fill in: if available — past incidents from under-processed high-risk changes]
**Expected cost:** One-time: ~1 hour team discussion | Ongoing: ~5 minutes per change to classify
**Verification:** 30-day check [fill in date] | 90-day check [fill in date] — were there Tier 3 changes processed as Tier 2?

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
