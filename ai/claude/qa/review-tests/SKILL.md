---
description: Formal QA review of test coverage after the TDD RED phase. Verifies every acceptance criterion has a test, every LLD error mode is exercised, incident regressions are present, E2E stubs exist for all ACs, and smoke suite contribution is included. Gates implementation start.
argument-hint: "[feature name, PR link, or LLD path]"
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


# Review Test Coverage

Verify that the test suite produced by the TDD cycle is complete before implementation begins. This is a blocking gate — do not approve if coverage gaps exist.

**Input:** $ARGUMENTS (feature name, PR link, or LLD path)

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Step 1 — Read the spec

1. Read the GitHub issue to get the PRD reference (FR-<ID>), then read `docs/01-product/prd.md` at that requirement for the acceptance criteria. The PRD is the source of truth — the issue is a pointer. If the PRD has no `FR-` entries, the acceptance criteria on the issue are the source.
2. Read the LLD at the path in `.hitl/current-change.yaml` (`source_artifacts.lld`) — note every method signature, error mode, precondition, and boundary entity
3. Read the test plan from `.hitl/current-change.yaml` under `tests.plan` — this is what the developer committed to covering
4. Read the scenarios file at `tests.scenarios_file` (rules: `shared/test-scenarios.md`). Every acceptance and integration test should cite one of its IDs
5. List the test files in `tests/` — read them

---

## Step 2 — Check incident regressions

Query the incident registry for the affected domain — prefer a graph query:
```
/graphify query "past incidents affecting domain: <domain-name>"
/graphify query "incident failure modes in <domain-name> that need regression coverage"
```
Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. For each incident relevant to this domain: verify a regression test exists that would have caught it. If no incidents exist for this domain, say so explicitly — do not skip the check.

---

## Step 3 — Coverage matrix

For each item in the spec, confirm test coverage:

| Spec item | Source | Scenario | Test(s) | Status |
|-----------|--------|----------|---------|--------|
| `<AC from PRD>` | PRD (FR-<ID>) | `SC-<change-id>-<nn>` | `<test name>` | ✅ / ❌ |
| `<method + error mode from LLD>` | LLD | `<ID or none>` | `<test name>` | ✅ / ❌ |
| `<incident regression>` | Incident registry | `SC-<change-id>-<nn>` | `<test name>` | ✅ / ❌ |

The `Scenario` column is the ID the test cites. An acceptance or integration test with none is a gap; a unit test may have none.

Flag every ❌ as a gap that must be resolved before implementation starts.

---

## Step 4 — Review E2E and smoke suite contributions

**E2E Playwright stubs** — verify that for every PRD acceptance criterion there is a Playwright test file in `tests/e2e/features/` marked `test.skip('pending environment', ...)`. Confirm each stub targets:
- Desktop Chrome
- `devices['iPhone 15']`
- `devices['Pixel 7']`

Flag any AC that has no stub. Flag any stub that runs without `test.skip` (E2E tests must not run during RED).

**Smoke suite contribution** — verify that a journey file exists at `tests/e2e/smoke/journeys/<feature-name>.spec.ts`. Confirm it:
- Is NOT skipped (smoke suite always runs)
- Assumes a fresh customer created by `tests/e2e/smoke/setup.ts`
- Asserts a visible outcome the PM could verify
- Runs on desktop Chrome + `devices['iPhone 15']` + `devices['Pixel 7']`

If the smoke setup file (`tests/e2e/smoke/setup.ts`) does not exist yet, flag it as a gap — the developer must create it as part of this change.

---

## Step 5 — Verify measured coverage

Check `.hitl/current-change.yaml` under `required_evidence.coverage_pct`.

**If `coverage_pct` is missing or below 90%:** Block immediately.
> "Coverage gate not met. The TDD cycle must produce ≥90% line coverage before QA review proceeds. Ask the developer to run the coverage check from Phase 6 of `/hitl:dev-tdd` and record the result in `.hitl/current-change.yaml` under `required_evidence.coverage_pct`."

**If `coverage_pct` ≥ 90%:** note it in the approval report and proceed to Step 5b.

---

## Step 5b — Run the scenario check

Prove the link between scenarios and tests in both directions (FR-36):

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/test-scenarios/check_scenarios.py"; [[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/test-scenarios/check_scenarios.py"
python3 "$CHK" --change .hitl/current-change.yaml --stage review
```

Exit 2 blocks: quote every `[BLOCK]` finding in the report and treat each as a gap for Step 6. Warnings (`[warn]`) are listed in the report and do not block; `REVIEW_PENDING` is a warning here, since the PM review is due by QA verify, not by now. Quote the validator's one-line verdict.

Then say QE's one invitation, one line: "Add a scenario you can think of with `/hitl:qa-scenarios`." Say it once; do not repeat it; do not wait for an answer.

---

## Step 6 — Approve or block

**If no gaps, E2E stubs present for all ACs, smoke journey file exists, coverage ≥ 90%, and the scenario check exited 0 or 1:** Update the test registry at `docs/03-engineering/testing/test-registry.yaml` to record the reviewed tests. Report: "Test coverage approved. `<N>` tests cover `<M>` acceptance criteria, `<K>` LLD error modes, and `<J>` incident regressions. E2E stubs: `<P>` ACs covered. Smoke suite: journey file present. Line coverage: `<coverage_pct>`%. Scenarios: `<S>`, all cited or deferred. Implementation may proceed."

**If any gap exists (unit coverage, E2E stubs missing, smoke journey missing, coverage < 90%, scenario check exit 2):** List every gap with the specific spec item it fails to cover. Do not approve. Report: "Test coverage blocked. `<N>` gap(s) found — implementation must not start until these are resolved."


## Closing this step

When this step is done, close it the way `ai/shared/next-step.md` describes: what finished, what is
next in words that say what it achieves, and how to start it. Read the next step and its `command`
from `.hitl/current-change.yaml`; `manual` and `guided` are not commands and must not be rendered as
one. Do not list the remaining steps, restate what just happened, or ask permission to continue.
