---
description: Create or update dashboards and alerts for a change before it is deployed. Reads the rollout plan go/no-go criteria and wires them to named observability instruments. Blocks deployment until a named dashboard and alert exist for every criterion. Run after IaC is applied and before /hitl:ops:deploy.
argument-hint: "[change ID or domain name]"
disable-model-invocation: true
---

# Set Up Observability

Instrument the change so that failures are visible and pages fire before the canary window closes. This is a mandatory gate before `/hitl:ops:deploy` for Tier 2+ changes.

**Input:** $ARGUMENTS (change ID or domain name)

**Refusal rule:** If `.hitl/current-change.yaml` is missing a `rollout_plan` section, stop: "No rollout plan found. Run `/hitl:ops:review-release` to produce go/no-go criteria before setting up observability."

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Progress Banners

Format: `---` line, `**Observability Setup — Step N / 4: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Identify Signals | `▶ Signals · ○ Check Existing · ○ Create/Update · ○ Verify + Record` |
| 2 | Check Existing | `✅ Signals · ▶ Check Existing · ○ Create/Update · ○ Verify + Record` |
| 3 | Create / Update | `✅ Signals · ✅ Check Existing · ▶ Create/Update · ○ Verify + Record` |
| 4 | Verify + Record | `✅ Signals · ✅ Check Existing · ✅ Create/Update · ▶ Verify + Record` |

---

## Step 1 — Identify the signals that matter

1. Read `.hitl/current-change.yaml` — extract:
   - `rollout_plan.go_no_go` criteria (these are the required metrics)
   - `manifest.domain` — the affected domain(s)
   - `rollout_plan.risk` — determines the required alert severity and page routing

2. Prefer a graph query to identify which metrics are already tracked for this domain:
   ```
   /graphify query "observability signals for domain: <domain-name>"
   /graphify query "dashboards and alerts for domain: <domain-name>"
   ```
   Fall back to reading `docs/system-manifest.yaml` under the domain's `observability` section if available.

3. For each go/no-go criterion in the rollout plan, identify:
   - The **metric name** it corresponds to (e.g., `http_request_error_rate_5xx`, `p99_latency_ms`)
   - The **baseline** (7-day rolling average or known stable value)
   - The **threshold** (from the rollout plan — must be a specific number, not "low" or "normal")
   - Whether this metric is currently collected and visible

If any criterion has a vague threshold ("low", "good", "normal"), stop: "Go/no-go criterion `<criterion>` has a non-measurable threshold. Update the rollout plan with a specific number before setting up observability."

---

## Step 2 — Check what already exists

Check the project's observability stack. Identify the tool in use from the project config (Datadog, Grafana, CloudWatch, Prometheus + Alertmanager, Honeycomb, etc.):

```
/graphify query "observability stack and dashboard URLs for this project"
```
Fall back to checking `docs/system-manifest.yaml` under `cross_cutting.observability` and scanning for dashboard config files (`grafana/`, `datadog/monitors/`, `.cloudwatch/`, etc.).

For each required metric, verify whether:
- **A panel exists** on a named dashboard that shows this metric in real time
- **An alert exists** with the rollout-plan threshold and a defined routing path (who gets paged)

List what is missing:

```
Observability gap report
────────────────────────
Required for rollout plan: 3 criteria

  ✅ http_request_error_rate_5xx — panel on "API Overview" dashboard, alert INC-ALERT-42
  ❌ p99_latency_ms — panel exists but no alert configured
  ❌ order_completion_rate — no panel, no alert
```

---

## Step 3 — Create or update instruments

For each gap identified in Step 2:

**Dashboard panels** — add a panel to an existing relevant dashboard (or create a feature-specific dashboard if none applies):
- Panel title: `[FeatureName] — <metric description>`
- Time range: last 24h by default, with 1h zoom available
- Show the go/no-go threshold as an annotation or reference line on the panel
- Include a baseline comparison (7-day rolling average if available)

**Alerts** — create an alert for each go/no-go criterion:

| Alert field | Required value |
|---|---|
| Name | `[ChangeID] — <criterion description>` |
| Condition | Threshold from rollout plan (exact number) |
| Evaluation window | ≥5 minutes (no single-datapoint pages) |
| Severity | Medium (Tier 2) / High (Tier 3) / Critical (Tier 4) |
| Routing | On-call rotation for the affected domain |
| Message | Include change ID, rollout plan context, rollback procedure link |

If the on-call routing for this domain does not exist, stop: "No on-call route configured for domain `<domain>`. Configure routing before deploying."

Present the created/updated instruments with their URLs or config paths before proceeding.

---

## Step 4 — Verify and record

1. **Verify each instrument is live** — confirm the dashboard panel renders data (not "no data") and the alert is in an active/evaluating state (not "paused" or "error").

2. **Simulate a threshold breach** if the observability stack supports test alerts:
   ```bash
   # Datadog example
   curl -X POST "https://api.datadoghq.com/api/v1/monitor/<monitor-id>/test" ...
   ```
   Skip if the stack does not support test alerts — note it explicitly.

3. **Update `.hitl/current-change.yaml`**:

```yaml
observability:
  status: configured
  dashboard: "<URL or path to dashboard>"
  alerts:
    - name: "<alert name>"
      metric: "<metric>"
      threshold: "<value>"
      routing: "<on-call rotation name>"
```

4. Report to the team:

```bash
gh issue comment <issue-number> \
  --body "## 📊 Observability Configured

Dashboard: <URL>
Alerts active: <N> — routing to <on-call rotation>

Canary criteria are now instrumented. Ready to deploy."
```

Report: "Observability configured. `<N>` alerts active. Deployment may proceed with `/hitl:ops:deploy`."

---

## Important Rules

- Never mark observability as configured without verifying the dashboard renders data and the alert is active
- Every go/no-go criterion in the rollout plan must have a corresponding alert — partial coverage is a blocker
- The on-call routing must exist before deployment — do not deploy without a defined escalation path
- Alert thresholds must match the rollout plan exactly — do not set tighter or looser thresholds without updating the plan
