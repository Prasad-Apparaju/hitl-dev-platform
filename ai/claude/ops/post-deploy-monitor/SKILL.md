---
description: Required post-deployment monitoring after every Tier 2+ deployment reaches full traffic. Reads go/no-go criteria from the rollout plan, samples metrics at risk-scaled intervals over the full soak period, and produces a STABLE/WATCH/ROLLBACK verdict. Run after the final canary promotion — /hitl:ops-deploy records the required soak duration by risk level.
argument-hint: "[change ID, e.g. 'GH-42']"
disable-model-invocation: true
---

# Post-Deploy Extended Monitoring

Required monitoring after every Tier 2+ deployment reaches full traffic. Produces a STABLE / WATCH / ROLLBACK verdict before the change is considered complete.

**Input:** $ARGUMENTS (change ID)

This skill is separate from `/hitl:ops-monitor-canary` (which runs at each promotion step). This runs after the **final promotion** and covers the full soak window — the change is not done until this skill produces a STABLE verdict.

**Soak duration and check interval by risk level:**

| Risk level | Soak duration | Check interval | Min checks |
|---|---|---|---|
| Low | 1 hour | every 30 min | 2 |
| Medium | 4 hours | every 1 hour | 4 |
| High | 12 hours | every 2 hours | 6 |
| Critical | 24 hours | every 4 hours | 6 |

Read `rollout_plan.risk` from `.hitl/current-change.yaml` to determine which row applies. If the soak duration was shortened in the rollout plan (operator discretion), use the approved value — not the default above.

---

## Step 1 — Set up the monitoring session

Read `.hitl/current-change.yaml`:
- `rollout_plan.risk` — determines soak duration and check interval (see table above)
- `rollout_plan.go_no_go` — the criteria and their thresholds
- `observability.dashboard` — the dashboard URL set up by `/hitl:ops-setup-observability`
- `observability.alerts` — the alert names to watch
- `deployment.deployed_at` — reference timestamp for baseline comparison

Compute the session schedule from the risk-level table. State the soak end time explicitly.

Record the session start time and expected end time. Post an update on the GitHub issue:
```bash
gh issue comment <issue-number> \
  --body "## 🔍 Post-Deploy Monitoring Started

**Soak period:** <duration>
**Dashboard:** <URL>
**Checking every:** <interval>
**Session ends:** <ISO timestamp>"
```

---

## Step 2 — Sample metrics at each interval

At each check interval, read the observability stack and evaluate every go/no-go criterion:

```
Metric check — <ISO timestamp> (<elapsed> into soak)
──────────────────────────────────────────────────
  <metric>:        <current value>  vs  baseline <baseline>  [threshold: <threshold>]  ✅ / ⚠️ / ❌
  <metric>:        <current value>  vs  baseline <baseline>  [threshold: <threshold>]  ✅ / ⚠️ / ❌
```

Symbols:
- ✅ — within threshold, no action needed
- ⚠️ — within threshold but trending toward it (>80% of threshold) — flag for attention
- ❌ — threshold exceeded — recommend pause and escalate to lead

For any ⚠️ reading: record it in the log and increase check frequency for the next period.

For any ❌ reading: immediately notify the lead and post on the issue:
```bash
gh issue comment <issue-number> \
  --body "## ⚠️ Metric Threshold Exceeded

**Metric:** <name>
**Current value:** <value>
**Threshold:** <threshold>
**Time:** <ISO timestamp>

Recommend: investigate before continuing soak. If the trend continues, consider rollback with /hitl:ops-rollback."
```

---

## Step 3 — Produce the final stability report

At the end of the soak period, produce a summary:

```
Post-Deploy Stability Report — <ChangeID>
─────────────────────────────────────────
Soak period:   <start> → <end>  (<duration>)
Checks run:    <N>
Alerts fired:  <N> (list if any)

Criteria results:
  <metric>   MIN: <min>  MAX: <max>  AVG: <avg>  THRESHOLD: <threshold>  ✅ / ❌
  <metric>   MIN: <min>  MAX: <max>  AVG: <avg>  THRESHOLD: <threshold>  ✅ / ❌

Incidents during soak: <N> (link to issue if any)

Recommendation: STABLE / WATCH / ROLLBACK

Rationale: <one sentence>
```

**STABLE** — all criteria within threshold for the full soak period. No further monitoring required.

**WATCH** — all criteria within threshold but one or more showed ⚠️ trend. Recommend a follow-up check in 24h.

**ROLLBACK** — one or more criteria exceeded threshold. Run `/hitl:ops-rollback`.

---

## Step 4 — Record and close

Update `.hitl/current-change.yaml`:

```yaml
post_deploy_monitor:
  status: complete
  soak_duration: <duration>
  checks_run: <N>
  alerts_fired: <N>
  result: stable | watch | rollback
  report_at: <ISO timestamp>
```

Post the final report on the GitHub issue:
```bash
gh issue comment <issue-number> \
  --body "## ✅ Post-Deploy Monitoring Complete

**Soak:** <duration>
**Result:** STABLE / WATCH / ROLLBACK
**Checks:** <N> over <duration>

<paste stability report>"
```

If result is STABLE, the change is fully shipped — the issue can be closed if not already done.

---

## Important Rules

- Do not skip checks during the soak period — gaps in the log reduce confidence in the stability verdict
- A single ❌ reading does not automatically mean rollback — assess whether it is a transient spike or a sustained trend
- If alerts fired during the soak period, reference them in the report — silence is not evidence of stability
- The soak period clock starts from the final promotion (100% traffic), not from the initial canary step
