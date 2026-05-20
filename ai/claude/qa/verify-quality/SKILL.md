---
description: Post-handoff independent quality verification. QA verifies the running build against acceptance criteria, runs exploratory testing, unskips and runs E2E Playwright tests (desktop + mobile web), runs the smoke suite, and checks that past incident failure modes cannot be reproduced. Blocks or approves promotion to Ops.
argument-hint: "[feature name or build link]"
disable-model-invocation: true
---

# Verify Quality

Independent verification of the developer's handoff. You are the last gate before Ops — verify thoroughly, block clearly, approve confidently.

**Input:** $ARGUMENTS (feature name or build URL)

**Prerequisite:** The developer has completed the impact brief and test registry is up to date. If no impact brief exists in `.hitl/current-change.yaml`, stop: "Impact brief missing — ask the developer to run `/hitl:dev:impact-brief` before QA handoff."

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Progress Banners

Output the banner for the current step at the start of every step — before any actions or content.

Format: `---` line, `**Verify Quality — Step N / 5: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Read Handoff | `▶ Handoff · ○ Incidents · ○ Verify ACs · ○ Exploratory · ○ E2E + Smoke · ○ Block or Approve` |
| 2 | Check Incidents | `✅ Handoff · ▶ Incidents · ○ Verify ACs · ○ Exploratory · ○ E2E + Smoke · ○ Block or Approve` |
| 3 | Verify ACs | `✅ Handoff · ✅ Incidents · ▶ Verify ACs · ○ Exploratory · ○ E2E + Smoke · ○ Block or Approve` |
| 4 | Exploratory Testing | `✅ Handoff · ✅ Incidents · ✅ Verify ACs · ▶ Exploratory · ○ E2E + Smoke · ○ Block or Approve` |
| 5 | E2E + Smoke Suite | `✅ Handoff · ✅ Incidents · ✅ Verify ACs · ✅ Exploratory · ▶ E2E + Smoke · ○ Block or Approve` |
| 6 | Block or Approve | `✅ Handoff · ✅ Incidents · ✅ Verify ACs · ✅ Exploratory · ✅ E2E + Smoke · ▶ Block or Approve` |

---

## Step 1 — Read the handoff context

1. Read the GitHub issue to get the PRD reference (FR-<ID>), then read `docs/01-product/prd.md` for the acceptance criteria. The PRD is the source of truth — the issue is a pointer.
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

## Step 5 — Run E2E tests and smoke suite

**E2E Playwright tests** — unskip all Playwright tests for this feature by removing or replacing `test.skip('pending environment', ...)` with the actual test body, then run:

```bash
# Desktop Chrome
npx playwright test tests/e2e/features/<feature-name>.spec.ts --project=chromium

# Mobile web — iPhone 15
npx playwright test tests/e2e/features/<feature-name>.spec.ts --project="iPhone 15"

# Mobile web — Pixel 7
npx playwright test tests/e2e/features/<feature-name>.spec.ts --project="Pixel 7"
```

For each test: record Pass / Fail and the visible assertion result. If any test fails, file a defect with `/hitl:qa:report-defect` before proceeding.

**Smoke suite** — run the full smoke suite against the current build:

```bash
npx playwright test tests/e2e/smoke/ --project=chromium
npx playwright test tests/e2e/smoke/ --project="iPhone 15"
npx playwright test tests/e2e/smoke/ --project="Pixel 7"
```

The smoke suite creates a brand-new test customer via `setup.ts`, exercises all registered journeys (including the one added for this feature), then cleans up via `teardown.ts`. If any journey fails, block — the build is not promotable until smoke is green.

Record the E2E and smoke results in `.hitl/current-change.yaml`:
```yaml
required_evidence:
  e2e_tests_pass: true   # or false with defect references
  smoke_suite_pass: true  # or false with defect references
```

---

## Step 6 — Block or approve

**Before approving, verify coverage was recorded:** Check `.hitl/current-change.yaml` under `required_evidence.coverage_pct`. If missing or below 90%, block:
> "QA blocked — line coverage not recorded or below 90%. The developer must run the coverage tool from `/hitl:dev:tdd` Phase 6 and record the result before QA can approve."

Also verify Step 5 evidence before approving:
- `required_evidence.e2e_tests_pass` is `true`
- `required_evidence.smoke_suite_pass` is `true`

If either is missing or `false`, block:
> "QA blocked — E2E tests or smoke suite did not pass. Resolve open defects from Step 5 before approving."

**If all criteria pass, no regressions reproduced, coverage ≥ 90%, E2E pass, and smoke suite pass:**
Update `.hitl/current-change.yaml`:
```yaml
approvals:
  qa: approved
  qa_notes: "All <N> ACs verified. <M> exploratory scenarios passed. E2E: <P> tests pass (desktop + iPhone 15 + Pixel 7). Smoke suite: all journeys pass. No incident regressions reproduced."
```
Post a comment on the GitHub issue, then report to the team:
```bash
gh issue comment <issue-number> \
  --body "## ✅ QA Approved

All <N> acceptance criteria verified. <M> exploratory scenarios passed. E2E tests pass on desktop + iPhone 15 + Pixel 7. Smoke suite green. No incident regressions reproduced.

Build is ready for Ops handoff."
```

**If any criterion fails, regression reproduced, E2E fails, or smoke suite fails:**
Run `/hitl:qa:report-defect` for each blocking issue. Post a comment on the main feature issue linking all defects, then report to the team:
```bash
gh issue comment <issue-number> \
  --body "## 🚫 QA Blocked

<N> blocking defect(s) filed. Promotion is blocked until all are resolved and re-verified.

**Open defects:**
- #<defect-number>: <short description>"
```

Do not approve with open defects. Do not block without filing a defect — informal notes are not actionable.

