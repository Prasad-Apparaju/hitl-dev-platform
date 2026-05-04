# ROI Estimation Reference

## When it fires (Step 4 — conditional)

ROI estimation is required for any change costing more than ~1 day of effort. For smaller changes, state "ROI estimate not required — change is <1 day" explicitly so the skip is auditable.

## Issue Template Section

Add this to the GitHub issue during the design phase:

```markdown
## ROI Estimate

**Value dimension:** [Quality / Reliability / Velocity / Cost / Risk / UX]
**Expected outcome:** [specific, falsifiable prediction with timeframe]
  e.g., "self_eval/overall improves by 15-25% within 30 days"
**Baseline metric (before):** [current measured value, not estimated]
  e.g., "Current self_eval/overall mean = 0.72 (last 30 days from Langfuse)"
**Expected cost:**
  - Build: [engineering days]
  - AI dev tokens: [estimated_cost_usd from token_tracking.estimated in .hitl/current-change.yaml]
  - Ongoing: [per-call or per-month cost delta]
  - Maintenance: [new operational burden]
**Measurement plan:** [which metric, which dashboard, when to check]
**Verification checkpoints:**
  - [ ] 30-day check: [date]
  - [ ] 90-day check: [date]
**Decision if ROI not realized:** [revert / rearchitect / accept partial return]
```

## Value Dimension Reference

| Dimension | Example changes | How to measure |
|-----------|----------------|----------------|
| Quality | Best-of-N sampling, context compression | Eval score lift, HITL rejection rate |
| Reliability | Retry policy, idempotency, DLQ | Error rate, incident count, MTTR |
| Velocity | System manifest, training plans | Time-to-first-PR, rework rate |
| Cost | Model routing, prompt caching | Cost per generation, tokens per output |
| Risk | Brand isolation, canary deployment | Blast radius, rollback frequency |
| UX | Latency improvements, streaming | p95 latency, time-to-first-token |

## Verification Cadence

| Checkpoint | Who | What they check | Outcomes |
|-----------|-----|----------------|----------|
| **30-day** | Developer + Lead | Metric direction, cost within estimate, unexpected side effects | On track / Inconclusive (extend to 60d) / Off track (investigate) |
| **90-day** | Lead + PM | Actual vs estimated ROI, business impact | ROI realized / Partial / Not realized → execute decision plan |

After the 90-day checkpoint, update the ADR:

```markdown
## Actual Outcome (90-day verification, YYYY-MM-DD)

**Expected:** [original prediction]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — and what was done about it]
```

The 90-day reviews create a calibration loop: over 5-10 verified changes, the team learns whether it systematically overestimates value, underestimates cost, or misses timelines.

## AI Token Cost Tracking

Token cost for the development process itself (Claude Code sessions running `/tdd`, `/generate-docs`, `/apply-change`, etc.) is tracked separately from production AI costs.

### Where costs come from

Token cost is not visible in Langfuse. Langfuse traces production LLM calls — not the Claude Code sessions that run the HITL process. The source of actual dev token costs is the **Claude Code session summary** shown at the end of each session, or the **Anthropic API usage dashboard**.

### Per-change tracking

`.hitl/current-change.yaml` carries a `token_tracking` block:

```yaml
token_tracking:
  estimated:                      # Populated by /apply-change at step 3
    total_cost_usd: 0.85
    by_phase: {design: 0.15, build: 0.45, verify: 0.20, assess: 0.05}
  actual:                         # Filled in as sessions complete
    total_cost_usd: 0.97
    sessions:
      - date: "2026-05-01"
        steps_covered: [10, 11, 12, 13, 14, 15, 16, 17]
        cost_usd: 0.52
```

After each Claude Code session, record the session cost and which steps were covered. The session cost appears in the Claude Code session summary.

### Cross-change registry

At step 24 (PR creation), copy the completed `token_tracking.actual` into `docs/03-engineering/costs/token-cost-registry.yaml` (template at `ai/templates/token-cost-registry-template.yaml`). After 5+ entries, the registry surfaces optimization signals — see the template for what patterns to look for.

### Estimation method (step 3)

`/apply-change` estimates cost from artifact file sizes:

| Input | Token estimate |
|-------|---------------|
| File content | chars ÷ 4 |
| Claude Sonnet 4.6 input rate | $3 / M tokens |
| Claude Sonnet 4.6 output rate | $15 / M tokens |
| Typical output/input ratio | 0.3× for review steps; 0.5× for generation steps |

Estimates are intentionally rough. The registry calibrates them over time — if actual consistently exceeds estimated by >50%, adjust the ratio for that phase.

## Training Plan (Step 8 — conditional)

Training plan required when the change introduces:
- A new architectural pattern
- A new external system integration
- A new framework or primitive
- A new ML/AI technique
- A significant refactor that changes how engineers reason about a subsystem

**Not required for:** new endpoints on existing controllers, bug fixes, mental-model-preserving refactors, test/doc-only changes.

When it doesn't fire, state explicitly: "no new capability — training plan not required."

**Location:** `docs/03-engineering/training/<capability-name>.md`

**Issue link format:**
```markdown
## Training Plan
[training: <capability-name>](../blob/main/docs/03-engineering/training/<capability-name>.md)
```
