---
description: Post-handoff independent quality verification, run at the QA verification step of the workflow after the developer hands off. QA verifies the running build against acceptance criteria, runs exploratory testing, unskips and runs E2E Playwright tests (desktop + mobile web), runs the smoke suite, and checks that past incident failure modes cannot be reproduced. Blocks or approves promotion to Ops.
argument-hint: "[feature name or build link]"
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


# Verify Quality

Independent verification of the developer's handoff. You are the last gate before Ops — verify thoroughly, block clearly, approve confidently.

**Input:** $ARGUMENTS (feature name or build URL)

**Prerequisite:** The developer has completed the impact brief and test registry is up to date. If no impact brief exists in `.hitl/current-change.yaml`, stop: "Impact brief missing — ask the developer to run `/hitl:dev-impact-brief` before QA handoff."

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

1. Read the GitHub issue to get the PRD reference (FR-<ID>), then read `docs/01-product/prd.md` for the acceptance criteria. The PRD is the source of truth — the issue is a pointer. If the PRD has no `FR-` entries, the acceptance criteria on the issue are the source.
2. Read `.hitl/current-change.yaml` — review the impact brief (Section 3: manual verification scenarios) and rollout plan
3. Read the test registry entry for this change — understand what was tested automatically
4. Read the scenarios file at `tests.scenarios_file` in `.hitl/current-change.yaml` (rules: `shared/test-scenarios.md`). The acceptance scenarios are what you verify in Step 3; note who added each and the `Review` line

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

For each AC from the GitHub issue, verify against the running build through the acceptance scenarios that serve it, one row per scenario:

| AC | Scenario | Verification steps | Result |
|----|----------|-------------------|--------|
| `<criterion>` | `SC-<change-id>-<nn> <title>` | `<what you did>` | ✅ Pass / ❌ Fail — `<defect description>` |

An AC with no scenario is a gap: add the scenario (`Added by: qa`) and verify it, so the file matches what was checked.

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

For each test: record Pass / Fail and the visible assertion result. If any test fails, file a defect with `/hitl:qa-report-defect` before proceeding.

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
## Step 5b — Run the scenario check

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/test-scenarios/check_scenarios.py"; [[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/test-scenarios/check_scenarios.py"
python3 "$CHK" --change .hitl/current-change.yaml --stage verify
```

**If the only blocker is `FILE_MISSING` and the change started before 2.17.0** (the record's `hitl_version` is older, or `tests.scenarios_file` is absent while the test plan step is already done): the change is in flight from before scenarios files existed. Write the file now from the change's tests, the way `dev-tdd` does when the test plan step was skipped (`shared/test-scenarios.md`): one scenario per acceptance or integration test, `Added by: dev`, `tests.scenarios_file` set, `tests.scenario_review` recorded `skipped` with `actor` (the person running this step), `pm` from the issue or "PM", reason "change started before 2.17.0", `disposition: defer`, `ts`. Say so in one line, re-run the fence, and continue. Do not block an in-flight change on a file that could not have existed.

**If the only blocker is `REVIEW_PENDING`:** the PM never said the review was done. Ask the person running this step, once, whether to record it as skipped, and who the PM is and why it did not happen. On yes, write `tests.scenario_review` in `.hitl/current-change.yaml` as `status: skipped` with `actor` (the person running this step), `pm`, `reason`, `disposition: defer` and `ts`; rewrite the file's `Review` line to `PM: skipped (<reason>)`; re-run the fence. On no, stop here: the review is due before this step closes. A skipped review is not an FR-29 step skip and goes in no `skips[]` entry.

**Any other `[BLOCK]` finding** is a QA defect: file it with `/hitl:qa-report-defect` as in Step 5 and block in Step 6. Warnings go in the report. Quote the validator's one-line verdict.

---

## Step 6 — Block or approve

**Before approving, verify coverage was recorded:** Check `.hitl/current-change.yaml` under `required_evidence.coverage_pct`. If missing or below 90%, block:
> "QA blocked: line coverage not recorded or below 90%. The developer must run the coverage tool from `/hitl:dev-tdd` Phase 6 and record the result before QA can approve."

Also verify Step 5 evidence before approving:
- `required_evidence.e2e_tests_pass` is `true`
- `required_evidence.smoke_suite_pass` is `true`

If either is missing or `false`, block:
> "QA blocked: E2E tests or smoke suite did not pass. Resolve open defects from Step 5 before approving."

**If all criteria pass, no regressions reproduced, coverage ≥ 90%, E2E pass, smoke suite pass, and the scenario check exited 0 or 1:**
Update `.hitl/current-change.yaml`:
```yaml
approvals:
  qa: approved
  qa_notes: "All <N> ACs verified. <M> exploratory scenarios passed. E2E: <P> tests pass (desktop + iPhone 15 + Pixel 7). Smoke suite: all journeys pass. No incident regressions reproduced."
```
Post a comment on the GitHub issue, then report to the team. After the first line, one line per scenario from the file, failures first, with who added it; then the existing text:
```bash
gh issue comment <issue-number> \
  --body "## ✅ QA Approved

- <scenario title> (added by <who>): pass
- <scenario title> (added by <who>): pass

All <N> acceptance criteria verified. <M> exploratory scenarios passed. E2E tests pass on desktop + iPhone 15 + Pixel 7. Smoke suite green. No incident regressions reproduced.

Build is ready for Ops handoff."
```

**If any criterion fails, regression reproduced, E2E fails, or smoke suite fails:**
Follow `/hitl:qa-report-defect` from its file (`skills/qa-report-defect/SKILL.md` under the plugin root) for each blocking issue. Post a comment on the main feature issue linking all defects, then report to the team:
```bash
gh issue comment <issue-number> \
  --body "## 🚫 QA Blocked

- <scenario title> (added by <who>): fail, #<defect-number>
- <scenario title> (added by <who>): pass

<N> blocking defect(s) filed. Promotion is blocked until all are resolved and re-verified.

**Open defects:**
- #<defect-number>: <short description>"
```

Do not approve with open defects. Do not block without filing a defect — informal notes are not actionable.


## Closing this step

When this step is done, close it the way `ai/shared/next-step.md` describes: what finished, what is
next in words that say what it achieves, and how to start it. Read the next step and its `command`
from `.hitl/current-change.yaml`; `manual` and `guided` are not commands and must not be rendered as
one. Do not list the remaining steps, restate what just happened, or ask permission to continue.
