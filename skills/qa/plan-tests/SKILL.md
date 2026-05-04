---
name: qa-plan-tests
description: Design-time QA contribution. QA reviews the LLD and queries the incident registry to identify test scenarios the developer may miss — edge cases from past failures, domain-specific failure modes, and integration gaps. Non-blocking input to the test plan before the TDD cycle starts.
argument-hint: "[LLD path or GitHub issue number]"
disable-model-invocation: true
---

# Contribute Test Scenarios at Design Time

Review the LLD and acceptance criteria before the TDD cycle starts. Contribute test scenarios from domain knowledge and the incident registry. This is non-blocking — your output is input to the developer's test plan, not a gate.

**Input:** $ARGUMENTS (LLD path or GitHub issue number)

---

## Step 1 — Read the design

1. Read the GitHub issue to get the PRD reference (FR-<ID>), then read `docs/01-product/prd.md` at that requirement for the acceptance criteria and scope. The PRD is the source of truth — the issue is a pointer.
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
Scenario: <name>
  Given: <precondition>
  When:  <action>
  Then:  <expected outcome>
  Why:   <incident reference or domain rationale>
```

Group scenarios by:
- **Regression required** — from past incidents, must be covered
- **Strongly recommended** — high-risk gaps from the LLD review
- **Optional** — lower-risk scenarios worth including if time allows

---

## Step 5 — Record and hand off

Update `.hitl/current-change.yaml` under `tests.qa_scenarios`:

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
```

Report the scenario list to the developer. Confirm: "Review these scenarios — regression-required ones must be in the test plan before the TDD cycle starts."

---

## Important Rules

- If the LLD is too vague to generate concrete scenarios, flag it as a design gap before TDD starts
