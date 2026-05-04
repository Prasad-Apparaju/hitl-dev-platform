---
name: qa-report-defect
description: Create a structured defect report when verify-quality finds issues. Files a GitHub issue with AC reference, reproduction steps, severity, environment, and incident registry link. Updates the HITL context to reflect the promotion block.
argument-hint: "[defect description]"
disable-model-invocation: true
---

# Report a Defect

File a structured defect report when QA verification finds an issue that blocks promotion. Every block must have a filed defect — informal notes are not actionable.

**Input:** $ARGUMENTS (description of what failed)

---

## Step 1 — Gather defect details

Collect before filing:
1. Which acceptance criterion is violated (or which incident regression reproduced)
2. Exact reproduction steps — specific enough that the developer can reproduce independently
3. Expected behavior vs actual behavior
4. Environment: build version, deployment URL, test data used
5. Severity:
   - **Critical** — data loss, security issue, or complete feature failure
   - **High** — primary user journey blocked or incident regression reproduced
   - **Medium** — secondary flow broken, workaround exists
   - **Low** — cosmetic or edge-case degradation

---

## Step 2 — Check for prior incidents

Query the incident registry to determine if this defect matches a known past failure — prefer a graph query:
```
/graphify query "incidents matching failure mode: <defect description>"
/graphify query "past defects in domain: <domain-name> related to <component>"
```
Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. If this is a regression of a known incident, note the incident ID — it raises severity.

---

## Step 3 — Check for duplicates

```bash
gh issue list --search "<keywords>" --state open --label "defect"
```
If a duplicate exists, add a comment to the existing issue with your specific reproduction steps rather than creating a new one. Return the issue URL and stop.

---

## Step 4 — File the defect

```bash
gh issue create \
  --title "defect(<severity>): <short description>" \
  --label "defect,qa-block" \
  --body "<structured body>"
```

Issue body format:

```
## Defect Report

**Severity:** <Critical / High / Medium / Low>
**Feature:** <GitHub issue or PR being tested>
**AC violated:** <exact text of the acceptance criterion, or "incident regression: #<id>">

### Steps to Reproduce
1. <step>
2. <step>
3. <step>

**Expected:** <what should happen>
**Actual:** <what happened instead>

### Environment
- Build: <artifact tag or commit SHA>
- URL: <deployment URL>
- Test data: <any relevant inputs or account state>

### Prior incident reference
<incident ID and link if this is a regression, or "none">

### Notes
<any additional context — logs, screenshots, timing observations>
```

---

## Step 5 — Update HITL context

Record the defect in `.hitl/current-change.yaml`:

```yaml
qa_defects:
  - issue: <GitHub issue URL>
    severity: <severity>
    ac_violated: <AC text>
    status: open
```

Set `approvals.qa: blocked` in `.hitl/current-change.yaml`.

Report: "Defect filed: `<issue URL>`. Promotion is blocked until this is resolved and `/qa:verify-quality` is re-run."

---

## Important Rules

- Severity drives urgency — Critical and High defects must be fixed before any promotion step; Medium and Low may be deferred with explicit PM and architect sign-off
- Every block must have a corresponding GitHub issue — verbal blocks are not tracked
- If this is a regression of a past incident, it is always at least High severity
- After the developer fixes a defect, a full re-run of `/qa:verify-quality` is required — spot-checking the fix is not sufficient
