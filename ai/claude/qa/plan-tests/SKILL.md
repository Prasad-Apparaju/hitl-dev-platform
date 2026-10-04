---
description: Design-time QA contribution. QA reviews the LLD and queries the incident registry to identify test scenarios the developer may miss — edge cases from past failures, domain-specific failure modes, and integration gaps. Non-blocking input to the test plan before the TDD cycle starts.
argument-hint: "[LLD path or GitHub issue number]"
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

**If there are no product requirements yet:** if `docs/01-product/prd.md` is absent, stop and output this, do not proceed:

```
No product requirements exist yet, so there is nothing here to work from.
Create the first requirement, then re-run this command:

  /hitl:pm-add-feature      capture a new requirement
  /hitl:pm-design-feature   design a user-facing feature
```

**If the PRD exists but has no `FR-` entries** (written before HITL, or in another form), do not stop. Say so in one line and continue, using the acceptance criteria on the GitHub issue, which the packet gate approved against:

```
The PRD has no FR- entries, so the acceptance criteria on the issue are used instead.
```

---


# Contribute Test Scenarios at Design Time

Review the LLD and acceptance criteria before the TDD cycle starts. Contribute test scenarios from domain knowledge and the incident registry. This is non-blocking — your output is input to the developer's test plan, not a gate.

**Input:** $ARGUMENTS (LLD path or GitHub issue number)

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Step 1 — Read the design

1. Read the GitHub issue to get the PRD reference (FR-<ID>), then read `docs/01-product/prd.md` at that requirement for the acceptance criteria and scope. The PRD is the source of truth — the issue is a pointer. If the PRD has no `FR-` entries, the acceptance criteria on the issue are the source.
2. Read the LLD at `$ARGUMENTS` (or at the path in `.hitl/current-change.yaml` under `source_artifacts.lld`)
3. Note: method signatures, error modes, preconditions, boundary entities, and any interactions with other domains

---

## Step 2 — Query incident history

This is the core value QA brings at design time — knowledge of what has broken before.

Query the incident registry for the affected domain — prefer a graph query:
```
/graphify query "past incidents affecting domain: <domain-name>"
/graphify query "incident failure modes in <domain-name>"
/graphify query "edge cases that caused incidents in <domain-name>"
```
Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable.

For each relevant incident, identify: what triggered it, what the failure mode was, and what test would have caught it. These become mandatory regression scenarios.

---

## Step 3 — Identify coverage gaps in the draft test plan

Read the test plan in `.hitl/current-change.yaml` under `tests.plan` if it exists. For each of the following, check whether it is represented:

- **Concurrent/race conditions** — if the LLD touches shared state, is there a concurrency scenario?
- **Boundary values** — are min/max/empty/nil inputs tested for every input parameter?
- **Cascading failures** — if this component calls downstream services, are downstream failure modes tested?
- **Partial success** — if the operation can partially succeed, is rollback or idempotency tested?
- **Permission boundaries** — if the LLD describes authorization, are unauthorized access attempts tested?
- **Volume/load edges** — if the LLD has rate limits or pagination, are boundary sizes tested?

---

## Step 4 — Produce test scenarios

Write concrete test scenarios for each gap found. Format each scenario clearly enough that the developer can write a test directly from it:

```
Scenario: <name, in the user's words: what is true when this passes>
  Kind:   acceptance | integration | regression
  Layer:  unit | integration | e2e | smoke
  Serves: <acceptance criterion or incident, for example FR-12 AC-2 or INC-004>
  Given: <one precondition>
  When:  <one action>
  Then:  <one visible outcome>
  Why:   <incident reference or domain rationale>
```

Write every scenario the way a manual tester would, so a PM can read it in a minute (FR-36): one
behaviour per scenario; one line each for Given, When and Then where the behaviour allows; the user's
words for the thing ("the total", not `cart.total_cents`); no code identifiers, file paths or HTTP
codes unless the user sees them. The rules are in `shared/test-scenarios.md`; do not restate them.

Group scenarios by:
- **Regression required** — from past incidents, must be covered
- **Strongly recommended** — high-risk gaps from the LLD review
- **Optional** — lower-risk scenarios worth including if time allows

For each acceptance criterion in the PRD, produce at least one **E2E Playwright scenario** that exercises the criterion as a real user would — browser-driven, desktop + mobile (iPhone 15, Pixel 7). Flag any criterion that cannot be exercised via browser (native mobile app only) — those require Appium or Detox and must be noted in the test plan.

Produce one **smoke suite scenario** for the feature's primary happy-path user journey. The scenario must assume a brand-new customer (created by the smoke suite setup step) and assert the visible outcome a PM would verify.

---

## Step 5 — Write the file and hand off

1. **Write the scenarios file** at `docs/03-engineering/testing/scenarios/<change-id>.md` from the
   plugin's `shared/templates/test-scenarios-template.md`, with every scenario from Step 4. IDs run
   `SC-<change-id>-01` upward in the order listed, regression-required first; each scenario carries
   its `Kind`, `Priority` (the Step 4 group), `Serves`, `Added by: qa` and `Test: none yet`. The
   `## What this change does` section is at most five sentences and ends with where the acceptance
   criteria are. If a file already exists, append new scenarios with the next IDs; never renumber.

2. **Update `.hitl/current-change.yaml`.** Keep `tests.qa_scenarios` for the breadcrumb, and add
   the file and the review state:

```yaml
tests:
  qa_scenarios:
    contributed_by: qa
    regression_required:
      - <scenario name>: <brief description>
    strongly_recommended:
      - <scenario name>: <brief description>
    optional:
      - <scenario name>: <brief description>
  scenarios_file: docs/03-engineering/testing/scenarios/<change-id>.md
  scenario_review:
    status: pending
```

3. **Invite the PM, once.** Post one line on the issue: the path, and that they can add any they
   can think of. This is the PM's one invitation for this change (`shared/test-scenarios.md`): post
   it once, never post a reminder, and do not wait for an answer. It is non-blocking.

```bash
CHANGE_ID=$(python3 -c "import yaml;print(yaml.safe_load(open('.hitl/current-change.yaml'))['change_id'])")
ISSUE_NUM=$(printf '%s' "$CHANGE_ID" | sed -n 's/^\(.*[^0-9]\)\{0,1\}\([0-9][0-9]*\)$/\2/p')   # the digits at the end: GH-12, SVC-3
gh issue comment "$ISSUE_NUM" --body "Test scenarios for this change are in \`docs/03-engineering/testing/scenarios/${CHANGE_ID}.md\`. Read the acceptance scenarios when you have a minute and add any you can think of: \`/hitl:qa-scenarios\`, or edit the file."
```

4. **Report the scenario list to the developer.** Confirm: "Review these scenarios. The
   regression-required ones must be in the test plan before the TDD cycle starts. Every acceptance
   and integration test will cite the ID of the scenario it serves."

---

## Important Rules

- If the LLD is too vague to generate concrete scenarios, flag it as a design gap before TDD starts
- The scenarios file is the record QA owns; the rules for its shape, IDs, citations and the one
  invitation per role are in `shared/test-scenarios.md`

## Closing this step

When this step is done, close it the way `ai/shared/next-step.md` describes: what finished, what is
next in words that say what it achieves, and how to start it. Read the next step and its `command`
from `.hitl/current-change.yaml`; `manual` and `guided` are not commands and must not be rendered as
one. Do not list the remaining steps, restate what just happened, or ask permission to continue.
