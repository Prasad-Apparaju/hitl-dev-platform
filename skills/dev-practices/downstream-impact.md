# Downstream Impact Assessment + Rollout Plan — Reference

> Use the `/impact-brief` skill to produce these artifacts. This file is the reference.

## When it fires (Steps 14–15)

After all code + tests + docs are ready and before creating the PR.

## Downstream Impact Brief (Step 14)

Five sections, each aimed at a different stakeholder:

| Section | Question | Who reads it |
|---------|----------|-------------|
| 1. Flows + components | What user-visible behaviors changed? | PM, QA |
| 2. Risk assessment | What can break? Severity × likelihood | Lead, Ops |
| 3. Manual verification | What to test beyond the automated suite? | QA, Ops |
| 4. Mental model update | What assumptions does the PM hold that are no longer true? | PM |
| 5. Rollout strategy | How do we derisk deployment? | Ops, Lead |

**Section 4 is the one teams most often skip and most often regret.** "Approve now queues for scheduled delivery instead of publishing immediately" takes 30 seconds and prevents weeks of downstream confusion.

## Risk-Rated Rollout Plan (Step 15)

| Risk level | Example | Rollout |
|-----------|---------|---------|
| Low | Config fix, doc update | Direct deploy |
| Medium | New feature behind flag, additive endpoint | Flag off → staging → 24h soak → production |
| High | Changed existing behavior, new external integration | Canary 5-10% → 4h monitor → 25% → 4h → 100% |
| Critical | Irreversible side effects, billing, migration | Canary 1% → manual gate each step → 24h soak per tier |

Each promotion step checks explicit go/no-go criteria:
- Error rate delta < [threshold specific to this change]
- Latency delta < [threshold]
- Business metric within tolerance of baseline
- No increase in failure-mode scores

The developer proposes the criteria; the lead reviews them at integration verification (step 16).

## Inputs Required

- `git diff main...HEAD` — the actual diff
- **Affected domains** — prefer graph queries:
  ```
  /graphify query "domain: <domain-name> components and facade APIs"
  ```
  Fall back to reading `docs/system-manifest.yaml` directly if the graph is unavailable.
- **Past failures in the affected domains** — prefer graph queries:
  ```
  /graphify query "past incidents affecting domain: <domain-name>"
  ```
  Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable.
- **Coverage for affected areas** — prefer graph queries:
  ```
  /graphify query "test coverage for domain: <domain-name>"
  ```
  Fall back to reading `docs/03-engineering/testing/test-registry.yaml` directly if the graph is unavailable.
- `.hitl/current-change.yaml` — change tier and approved domain
