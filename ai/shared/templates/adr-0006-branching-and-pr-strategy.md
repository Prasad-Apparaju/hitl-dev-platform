# ADR-0006: Branching and PR Strategy

| | |
|---|---|
| **Status** | Draft — complete before the first PR is merged via the HITL workflow |
| **Date** | [fill in] |
| **Deciders** | [fill in: dev lead, architect] |
| **Supersedes** | — |
| **Related** | ADR-0001 (HITL adoption), ADR-0004 (change tier policy) |

---

## 1. Context

The HITL 31-step workflow creates a GitHub issue per change, works in a named branch, and opens a PR that passes through defined review gates before merge. Without a documented branching and PR strategy, developers make inconsistent decisions about branch naming, PR size, required reviewers, and merge approach — which undermines HITL's traceability and review gates.

## 2. Decision

### Branching model

[fill in — HITL works best with trunk-based development: short-lived feature branches (1–3 days), merged to `main` frequently. Record any deviation and the reason.]

| Aspect | Decision | Notes |
|---|---|---|
| Main branch | [fill in — e.g., `main`] | Protected — no direct pushes |
| Feature branches | [fill in — e.g., `feat/<issue-number>-<slug>`] | One branch per HITL change |
| Release branches | [fill in — e.g., none / `release/vX.Y`] | |
| Hotfix branches | [fill in — e.g., `fix/<issue-number>-<slug>`] | |

### Branch naming convention

[fill in — Example: `feat/123-add-payment-webhook`, `fix/456-null-pointer-on-checkout`]

The HITL `sync-step-to-issue.sh` hook uses the branch name to associate session activity with a GitHub issue — follow the `<type>/<issue-number>-<slug>` pattern for full traceability.

### PR expectations

| Aspect | Decision |
|---|---|
| Maximum PR size | [fill in — HITL recommendation: ≤400 lines changed per PR; larger changes must be decomposed into slices] |
| Draft PRs allowed | [fill in — yes / no] |
| PR template | `docs/templates/pull-request-template.md` (from HITL plugin) |
| Linked issue required | Yes — every PR must reference the HITL change issue |

### Required reviewers by change tier

| Tier | Required reviewers | Auto-merge allowed |
|---|---|---|
| Tier 1 (trivial) | [fill in — e.g., 1 peer] | [fill in — yes / no] |
| Tier 2 (standard) | [fill in — e.g., 1 peer + TA approval via `/hitl:ta-approve`] | No |
| Tier 3 (significant) | [fill in — e.g., 1 peer + architect + TA approval] | No |
| Tier 4 (critical) | [fill in — e.g., 2 peers + architect + TA approval] | No |

### Merge strategy

[fill in — e.g., squash merge to keep `main` history linear, or merge commit to preserve branch history. Record the choice and enforce it in GitHub branch protection.]

| Branch | Merge strategy | Reason |
|---|---|---|
| Feature → main | [fill in — squash / merge commit / rebase] | |
| Release → main | [fill in] | |

### Branch protection rules

[fill in — what GitHub branch protection rules are applied to `main`]

- [ ] Require PR before merging
- [ ] Require status checks to pass (CI build, tests)
- [ ] Require conversation resolution
- [ ] Restrict who can push directly

## 3. Alternatives Considered

[fill in — e.g., "Evaluated Gitflow but chose trunk-based because our release cadence is continuous and Gitflow's long-lived branches create merge conflicts that slow HITL's slice-based delivery."]

## 4. Consequences

### Positive
- HITL traceability is preserved — every commit links to an issue and a PR
- Review gates are predictable — developers know exactly what is required by tier

### Negative
- [fill in — e.g., "Squash merging loses individual commit history inside a PR. Mitigated by requiring descriptive PR titles and bodies."]

## 5. Open Questions

1. [ ] What is the agreed maximum PR size in lines? (HITL recommendation: 400)
2. [ ] Who can approve Tier 3 and Tier 4 PRs if the architect is unavailable?
3. [ ] Are there any exceptions to the branch naming convention (e.g., dependabot branches)?

## ROI Estimate

**Value dimension:** Delivery velocity / Risk
**Expected outcome:** Consistent PR review cycle time; no blocked merges due to ambiguous review requirements
**Baseline metric:** [fill in: current average PR review time, current merge conflict frequency]
**Expected cost:** One-time setup of branch protection rules — ~1 hour
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
