---
name: qa-verify-quality
description: Post-handoff independent quality verification. QA verifies the running build against acceptance criteria, runs exploratory testing beyond the happy path, and checks that past incident failure modes cannot be reproduced. Blocks or approves promotion to Ops.
argument-hint: "[feature name or build link]"
disable-model-invocation: true
---

# Verify Quality

Independent verification of the developer's handoff. You are the last gate before Ops — verify thoroughly, block clearly, approve confidently.

**Input:** $ARGUMENTS (feature name or build URL)

**Prerequisite:** The developer has completed the impact brief and test registry is up to date. If no impact brief exists in `.hitl/current-change.yaml`, stop: "Impact brief missing — ask the developer to run `/impact-brief` before QA handoff."

---

## Step 1 — Read the handoff context

1. Read the GitHub issue — extract all acceptance criteria
2. Read `.hitl/current-change.yaml` — review the impact brief (Section 3: manual verification scenarios) and rollout plan
3. Read the test registry entry for this change — understand what was tested automatically

---

## Step 2 — Check incident regressions

Query the incident registry for the affected domain — prefer a graph query:
```
/graphify query "past incidents affecting domain: <domain-name>"
/graphify query "incident failure modes in <domain-name>"
```
Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. Build a list of failure modes to probe during exploratory testing. If no incidents exist for this domain, say so — do not skip.

---

## Step 3 — Verify acceptance criteria

For each AC from the GitHub issue, verify against the running build:

| AC | Verification steps | Result |
|----|-------------------|--------|
| `<criterion>` | `<what you did>` | ✅ Pass / ❌ Fail — `<defect description>` |

Go beyond the happy path — test boundary values, empty states, concurrent use, and failure injection where relevant.

---

## Step 4 — Exploratory testing

Run the manual verification scenarios from the impact brief (Section 3). Then probe:
- Edge cases the developer may not have anticipated from the domain knowledge
- Interactions with adjacent features the impact brief flagged as at-risk
- Past incident failure modes identified in Step 2

Document each finding: what you did, what you expected, what happened.

---

## Step 5 — Block or approve

**If all criteria pass and no regressions reproduced:**
Update `.hitl/current-change.yaml`:
```yaml
approvals:
  qa: approved
  qa_notes: "All <N> ACs verified. <M> exploratory scenarios passed. No incident regressions reproduced."
```
Report: "QA approved. Build is ready for Ops handoff."

**If any criterion fails or regression reproduced:**
Run `/qa:report-defect` for each blocking issue. Then report: "QA blocked. `<N>` defect(s) filed — see issue(s) `<list>`. Promotion is blocked until all are resolved and re-verified."

Do not approve with open defects. Do not block without filing a defect — informal notes are not actionable.

---

## Important Rules

- Verify against the running build, not the code — tests passing in CI does not replace this step
- Every block must have a filed defect (`/qa:report-defect`) — "it didn't work" is not sufficient
- If a past incident failure mode CAN be reproduced: it is a regression — block regardless of ACs passing
- Re-verification after a fix requires a new verify-quality run — do not lift a block without re-running
