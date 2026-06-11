---
description: Manage an active production incident from declaration through resolution and registry logging. Declares severity, guides response, tracks timeline, and logs a structured entry to the incident registry when resolved. Use when a production system is degraded or down — not as part of the normal delivery workflow.
argument-hint: "[brief description of what is failing]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---


# Incident Response

Manage a production incident from declaration to registry entry. This skill is triggered reactively — not as part of the delivery workflow.

**Input:** $ARGUMENTS (brief description of the failure)

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Progress Banners

Format: `---` line, `**Incident Response — Step N / 5: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Declare | `▶ Declare · ○ Investigate · ○ Mitigate · ○ Resolve · ○ Log` |
| 2 | Investigate | `✅ Declare · ▶ Investigate · ○ Mitigate · ○ Resolve · ○ Log` |
| 3 | Mitigate | `✅ Declare · ✅ Investigate · ▶ Mitigate · ○ Resolve · ○ Log` |
| 4 | Resolve | `✅ Declare · ✅ Investigate · ✅ Mitigate · ▶ Resolve · ○ Log` |
| 5 | Log to Registry | `✅ Declare · ✅ Investigate · ✅ Mitigate · ✅ Resolve · ▶ Log` |

---

## Step 1 — Declare the incident

Determine severity based on user impact:

| Severity | Criteria |
|---|---|
| SEV-1 | Complete outage or data loss affecting all users; payment or auth system down |
| SEV-2 | Major feature unavailable or degraded for >10% of users; significant error rate spike |
| SEV-3 | Minor feature degraded; workaround available; <10% of users affected |
| SEV-4 | Cosmetic issue or performance degradation with no user-visible functional impact |

Create a GitHub issue for incident tracking:
```bash
gh issue create \
  --title "INC: <brief description> [SEV-<N>]" \
  --label "incident,sev-<N>" \
  --body "**Declared at:** <ISO timestamp>
**Severity:** SEV-<N>
**Affected:** <what is failing>
**User impact:** <who is affected and how>
**On-call:** <person or rotation handling>"
```

Record the incident issue number — all updates go there.

Alert the team: post in the incident channel with the GitHub issue link and severity.

---

## Step 2 — Investigate

Check the observability stack for signals:

1. **Error rate** — is it elevated? Since when? Does it correlate with a recent deployment?
2. **Latency** — is a specific endpoint or service slow?
3. **Recent deployments** — check deployment history for the last 2 hours:
   ```bash
   # Kubernetes
   kubectl rollout history deployment/<name>
   # Check .hitl/ for recent changes
   find .hitl/ -name "*.yaml" -newer $(date -d '2 hours ago' +%Y-%m-%d) 2>/dev/null
   ```
4. **Recent IaC or config changes** — check git log for infrastructure commits
5. **Downstream dependencies** — is the issue in this service or in a dependency?
   ```
   /graphify query "services this domain depends on: <domain-name>"
   ```

Check the incident registry for similar past incidents:
```
/graphify query "past incidents in domain: <domain-name> with similar failure mode"
```

State the working hypothesis: "Most likely cause: `<hypothesis>`. Evidence: `<signals>`."

---

## Step 3 — Mitigate

Mitigation means stopping user impact as fast as possible — it is not the same as root cause fix.

Common mitigations to consider (assess applicability, do not apply blindly):

| Mitigation | When to use |
|---|---|
| Roll back to previous artifact (`/hitl:ops-rollback`) | Deployment caused the incident |
| Toggle feature flag off | Change is behind a flag |
| Redirect traffic to healthy region/AZ | Regional failure |
| Scale up replicas | Capacity-related degradation |
| Kill a runaway process or job | Resource exhaustion |
| Revert a config change | Misconfiguration |
| Enable maintenance mode | Full outage requiring coordinated fix |

Execute the chosen mitigation. Verify user impact has stopped or reduced. Post an update on the incident issue:
```bash
gh issue comment <incident-issue-number> \
  --body "**Update <timestamp>:** Mitigation applied — <what was done>. Impact status: <still degraded / mitigated / resolved>."
```

---

## Step 4 — Resolve

Once user impact is stopped:

1. Confirm the system is operating within normal parameters — check all go/no-go criteria for the affected domain
2. Run the smoke suite to confirm no cascading failures:
   ```bash
   npx playwright test tests/e2e/smoke/ --project=chromium
   ```
3. Declare the incident resolved. Post on the issue:
   ```bash
   gh issue comment <incident-issue-number> \
     --body "**Resolved at:** <ISO timestamp>
   **Duration:** <start to resolution>
   **Root cause (working hypothesis):** <description>
   **Fix applied:** <what was done to resolve>
   **Follow-up required:** <yes — link to fix issue | no>"
   ```

Close the incident issue (leave it labeled `incident` for registry reference):
```bash
gh issue close <incident-issue-number> --comment "Incident resolved."
```

---

## Step 5 — Log to incident registry

Add an entry to `docs/04-operations/incident-registry.yaml` using this schema:

```yaml
- id: INC-<next-sequential-number>
  title: "<brief description>"
  severity: <SEV-1 | SEV-2 | SEV-3 | SEV-4>
  domain: <affected manifest domain>
  declared_at: <ISO timestamp>
  resolved_at: <ISO timestamp>
  duration_minutes: <N>
  trigger: <deployment | config-change | external-dependency | traffic-spike | unknown>
  failure_mode: "<one sentence: what broke and how">
  user_impact: "<one sentence: who was affected and what they experienced">
  mitigation: "<one sentence: what stopped the impact">
  root_cause: "<one sentence: why it happened">
  preventable_by_test: <true | false>
  test_that_would_have_caught_it: "<describe the test, or null if not preventable by a test">
  github_issue: <incident issue number>
  follow_up_issue: <fix issue number or null>
```

If `preventable_by_test: true`, create a follow-up issue to add the regression test:
```bash
gh issue create \
  --title "Regression test: <failure mode from INC-<N>>" \
  --label "regression,test" \
  --body "Add a test that would have caught INC-<N>.
  
Test scenario: <describe the test>
  
See: #<incident-issue-number>"
```

This follow-up test must be included in the test plan of the next change that touches this domain — the incident registry ensures it is not forgotten.

---

## Important Rules

- Mitigation (stop the bleeding) always takes priority over root cause investigation
- Do not close the incident issue without a registry entry — informal Slack threads are not actionable for future changes
- If the incident was caused by a deployment, always check whether a regression test would have caught it — the `preventable_by_test` field drives the regression coverage loop
- A SEV-1 or SEV-2 incident always requires a post-mortem — schedule it within 48 hours of resolution
