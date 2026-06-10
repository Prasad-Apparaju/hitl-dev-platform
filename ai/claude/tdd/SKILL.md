---
description: Orchestrate the TDD-as-design Red → Green → Refactor cycle where tests drive the design before implementation code exists. Use after the LLD is approved and before writing any implementation code. Requires an approved LLD — refuses to proceed without one.
argument-hint: "[LLD path or issue number and component name]"
disable-model-invocation: true
---

# TDD as a Design Tool

Orchestrate the Red → Green → Refactor cycle where tests drive the design before code exists.

**Input:** $ARGUMENTS (description of what to implement — should reference an LLD or issue)

If `$ARGUMENTS` is empty, ask: "What are you implementing? Point me to the LLD or issue."

**Refusal rule — design not approved:** Read `.hitl/current-change.yaml`. If the file exists and `status` is not `implementation-approved`, stop:

> Design approval is required before implementation can begin.
>
> Current status: `[status]`
>
> - If the architect is still in the design phase, wait for them to complete `/hitl:architect-design-feature` and reach all gates.
> - If a gate is awaiting review, the TA must run `/hitl:ta-approve` to advance it.
> - If status is `blocked`, the architect must resolve the finding first.
>
> Do not start the TDD cycle until status is `implementation-approved`.

**Refusal rule — no LLD:** If no LLD path is provided or found, stop: "No LLD found. Write the LLD first using `/hitl:dev-generate-docs` — this skill generates tests FROM the spec, not without one."

**Refusal rule — no decision packet:** Before generating any tests, check `.hitl/current-change.yaml` for `source_artifacts.decision_packet`. If the field is missing or the file at that path does not exist on disk, stop:

> No decision packet found for this change.
>
> Decision packets are created at the end of `/hitl:architect-design-feature` (Phase 10 — Step 9). They prove the change has an approved LLD, a test plan, and a scoped domain before code generation begins.
>
> Run `/hitl:architect-design-feature` first. Once the architect approves the packet, resume here.

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Progress Banners

Output the banner for the current phase at the start of every phase — before any questions, analysis, or content.

Format: `---` line, `**TDD — Phase N / 7: [Name]**`, trail, `---`.

| Phase | Name | Banner trail |
|---|---|---|
| 1 | Generate Tests | `▶ RED · ○ Review · ○ Improve Design · ○ Verify RED · ○ GREEN · ○ Verify GREEN · ○ Refactor` |
| 2 | Human Review | `✅ RED · ▶ Review · ○ Improve Design · ○ Verify RED · ○ GREEN · ○ Verify GREEN · ○ Refactor` |
| 3 | Improve Design | `✅ RED · ✅ Review · ▶ Improve Design · ○ Verify RED · ○ GREEN · ○ Verify GREEN · ○ Refactor` |
| 4 | Verify RED | `✅ RED · ✅ Review · ✅ Improve Design · ▶ Verify RED · ○ GREEN · ○ Verify GREEN · ○ Refactor` |
| 5 | Generate Code | `✅ RED · ✅ Review · ✅ Improve Design · ✅ Verify RED · ▶ GREEN · ○ Verify GREEN · ○ Refactor` |
| 6 | Verify GREEN | `✅ RED · ✅ Review · ✅ Improve Design · ✅ Verify RED · ✅ GREEN · ▶ Verify GREEN · ○ Refactor` |
| 7 | Refactor | `✅ RED · ✅ Review · ✅ Improve Design · ✅ Verify RED · ✅ GREEN · ✅ Verify GREEN · ▶ Refactor` |

---

## Phase 1 — Generate Tests (RED)

Update `.hitl/current-change.yaml`: set `current_step: {number: 10, name: "AI generates tests (RED)", phase: "Build"}`.

1. **Read the LLD** for the component being implemented. If no LLD exists, stop (see refusal rule above).

2. **Get manifest data** for the domain. Prefer graph queries if available:
   ```
   /graphify query "domain: <domain-name> facade_apis for contract tests"
   /graphify query "domain: <domain-name> boundary_entities and cross_cutting conventions"
   ```
   Fall back to reading `docs/system-manifest.yaml` directly if the graph is unavailable. Extract:
   - `facade_apis` for this domain → contract tests
   - `cross_cutting` conventions → convention tests
   - `boundary_entities` → entity shape tests

3. **Check existing test coverage** for this domain before generating new tests — avoid duplicating what already exists:
   ```
   /graphify query "existing tests for domain: <domain-name>"
   /graphify query "test coverage gaps in <component-name>"
   ```
   Fall back to reading `docs/03-engineering/testing/test-registry.yaml` directly if the graph is unavailable. Note which behaviors are already tested so you don't regenerate them.

4. **Check the incident registry** for past failures in this domain — these must become regression tests:
   ```
   /graphify query "past incidents affecting domain: <domain-name>"
   /graphify query "incident failure modes in <domain-name>"
   ```
   Fall back to reading `docs/04-operations/incident-registry.yaml` directly. For each relevant incident, add a regression test named `test_<incident_id>_<failure_description>`.

5. **Check the test strategy** for domain-specific constraints:
   ```
   /graphify query "test strategy constraints for <domain-name>"
   ```
   Fall back to reading `docs/03-engineering/testing/strategy.md` if the graph is unavailable or returns nothing specific.

Generate three categories of tests. All are written now (RED phase), but they run at different points:

**A. Unit tests** — written and run in this TDD cycle. Target ≥90% line coverage (hard gate at Phase 6).
   - Happy path for every method in the LLD
   - Error path for every `error_modes` entry in the facade
   - Precondition violation for every `preconditions` entry
   - Every `if`/`else` branch and early-return path in the LLD's described logic
   - Boundary entity shape tests (verify entity matches the manifest shape)
   - Convention tests (e.g., if `idempotency-keys` applies, test key rejection)
   - Regression tests for every incident found in step 4
   - Before presenting: count methods × (happy path + each error mode + each precondition violation). Fewer than 3 tests per public method on average means branch gaps — add more.

**B. Integration tests** — written now, run at Phase 6 GREEN (real service calls, no mocks for the domain under test).
   - One integration test per `facade_api` entry in the manifest for this domain
   - Tests make real calls to the service (use a test database/sandbox, not mocks)
   - Verify the contract each facade API promises to other domains
   - Verify cross-domain boundary entities have the correct shape at the wire level
   - Mark with `@pytest.mark.integration` / `describe('integration', ...)` so they can be run separately

**C. Playwright E2E tests** — written now as stubs (`test.skip`), unskipped by QA at Step 22.
   Write one Playwright test file per PRD acceptance criterion for this feature. Each test:
   - Simulates a real user in a browser — no direct API calls, no mocks
   - Runs against both desktop Chrome and a mobile device (`devices['iPhone 15']` and `devices['Pixel 7']`)
   - Follows the user journey end-to-end: navigate → interact → assert visible outcome
   - Is marked `test.skip('pending environment', ...)` so it does not break RED phase
   - Lives in `tests/e2e/features/<feature-name>.spec.ts`

   File structure:
   ```typescript
   import { test, devices } from '@playwright/test';
   const iphone = devices['iPhone 15'];
   const android = devices['Pixel 7'];

   test.skip('pending environment');

   test.describe('<feature-name>', () => {
     test.use({ ...iphone }); // repeat block with android
     test('<AC description — desktop>', async ({ page }) => { /* ... */ });
   });
   ```

   > **Note on native mobile apps:** Playwright covers web browsers and mobile web (responsive/PWA). If the feature includes a native iOS or Android app, those require Appium or Detox — flag that in the test plan.

**D. Smoke suite contribution** — add this feature's happy-path user journey to `tests/e2e/smoke/journeys/<feature-name>.spec.ts`. The smoke suite runs a fresh new-customer flow on every build.

   Structure:
   ```
   tests/e2e/smoke/
     setup.ts          ← creates a brand-new test customer (signup → onboard)
     teardown.ts       ← deletes test customer and all associated data
     journeys/
       <existing>.spec.ts
       <feature-name>.spec.ts   ← ADD THIS for the current feature
   ```

   The journey file must:
   - Assume a fresh customer created in `setup.ts` — no pre-existing data
   - Exercise the feature's primary user action end-to-end via browser
   - Assert the visible outcome the PM would verify
   - Run on desktop Chrome + `devices['iPhone 15']` + `devices['Pixel 7']`
   - NOT be skipped — smoke suite always runs

   If `tests/e2e/smoke/setup.ts` does not exist yet, create it now. It must:
   - Hit the app's signup flow via Playwright (real browser, not API)
   - Complete onboarding
   - Store the created customer's credentials in a fixture file for the journey tests to consume
   - Be idempotent (safe to run repeatedly; tears down previous test customer first)

7. **Register each new test** in `docs/03-engineering/testing/test-registry.yaml`. Required fields: `id`, `name`, `domain`, `risk`, `type` (`unit` / `integration` / `e2e` / `smoke`), `origin` (`tdd`), `file`. For incident regression tests, also set `incident_ref`.

8. **Present all generated tests** to the user. Do NOT proceed to Phase 2 until the user reviews.

9. **STOP and present a specific review checklist:**

   > **Tests need your review before I write any code. Work through this list:**
   >
   > 1. **Unit coverage gaps** — I generated unit tests from the LLD. What domain knowledge or business rules aren't in the LLD? Add tests for those now.
   > 2. **Integration contracts** — Does each facade API have an integration test that makes a real call? Are the contract assertions specific (exact field names, error codes)?
   > 3. **E2E journeys** — Does each Playwright test follow what a real user would do? Are the assertions on visible UI outcomes, not internal state?
   > 4. **Smoke suite** — Does the new journey in the smoke suite represent what the PM would demo? Does it start from a brand-new customer with no prior data?
   > 5. **Incident registry** — Are past failure modes in this domain covered by a regression test?
   > 6. **Security edge cases** — Unauthenticated access rejected? User A cannot access User B's data? Input at max/empty/null?
   > 7. **Mobile coverage** — Are the Playwright tests running against both `iPhone 15` and `Pixel 7` device profiles?
   >
   > Remove tests that only verify implementation details (mock called once, internal method invoked).
   >
   > When you're satisfied, say **"tests approved"** to proceed.

---

## Phase 2 — Human Reviews + Adds Tests

Wait for the user to work through the checklist above. Do not prompt them to hurry or summarize what you're waiting for — they need to think through each item.

If the user says "tests approved" without engaging with the checklist, ask: "Did you check the incident registry for this domain? And are there security edge cases covered?" Only proceed when both are confirmed.

When the user says "tests approved" and has addressed the checklist, proceed to Phase 3.

---

## Phase 3 — Tests Improve the Design

1. **Analyze the approved test suite against the LLD.** For each test that covers behavior the LLD does not describe:
   - Flag it: "This test expects [behavior], but the LLD doesn't specify it."
   - Propose an LLD update: "Add to the LLD: [specific text]"

2. **If gaps are found**, update the LLD before proceeding. Ask the user to confirm each LLD change.

3. **If no gaps found**, say "LLD is consistent with the test suite" and proceed.

---

## Phase 4 — Verify RED

1. **Run the full test suite.** All NEW tests must FAIL (no implementation exists).

2. **If any new test passes**, flag it:
   - "This test passed before implementation. Either the test is wrong (testing existing behavior) or the LLD describes something that already exists."
   - Ask the user to investigate before proceeding.

3. **If all new tests fail**, say "RED confirmed — all tests fail as expected" and proceed.

---

## Phase 5 — Generate Code (GREEN)

Update `.hitl/current-change.yaml`: set `current_step: {number: 14, name: "Generate code (GREEN)", phase: "Build"}`.

1. **Generate the simplest implementation** that makes all failing tests pass.
   - Read the LLD for the implementation spec
   - Follow the conventions from the manifest's `cross_cutting` section
   - Follow the coding standards from `CLAUDE.md`
   - Add inline comments for non-obvious logic

2. **Do not over-engineer.** The goal is passing tests, not anticipating future requirements.

3. **Present the generated code** to the user for review.

---

## Phase 6 — Verify GREEN

1. **Run the full test suite** (new + existing).

2. **If new tests pass but existing tests fail**, flag: "Regression detected in [test]. The new code broke existing behavior." Fix before proceeding.

3. **If new tests still fail**, continue generating code to make them pass. Return to Phase 5.

4. **Run coverage and enforce the 90% gate.** Once all tests pass, measure line coverage for the component under test:

   | Language | Command |
   |---|---|
   | Python | `pytest --cov=<module> --cov-report=term-missing --cov-fail-under=90` |
   | TypeScript/JS | `jest --coverage --coverageThreshold='{"global":{"lines":90}}'` |
   | Go | `go test ./... -coverprofile=coverage.out && go tool cover -func=coverage.out` |
   | Other | Run your test runner's coverage tool; check line coverage ≥ 90% |

   **If coverage < 90%:**
   - Read the coverage report. Identify every uncovered line or branch.
   - For each uncovered path, **generate a test** that exercises it — this is AI-generated, same as Phase 1. Present the new tests to the user and go through Phase 2 (human review) for them before proceeding. Do not skip the review gate for coverage-gap tests.
   - After Phase 2 approval: re-run Phase 4 (Verify RED for new tests), Phase 5 (generate code to make them pass if needed), then re-run this coverage check.
   - Repeat until coverage ≥ 90%. Do not proceed to Phase 7 until the gate passes.

   **If coverage ≥ 90%:**
   - Record the coverage percentage in `.hitl/current-change.yaml` under `required_evidence.coverage_pct`.

5. **Run integration tests** (now that the implementation exists):
   ```bash
   pytest -m integration   # Python
   jest --testPathPattern=integration   # JS/TS
   ```
   All integration tests must pass. If any fail:
   - Diagnose: is it a contract mismatch (implementation disagrees with the facade spec) or a test environment issue?
   - Fix the implementation or the test environment. Do not remove or skip failing integration tests.
   - Re-run until all pass, then proceed to Phase 7.

   Record result in `.hitl/current-change.yaml` under `required_evidence.integration_tests_pass: true`.

   E2E Playwright tests remain `test.skip` — they run at QA verify (Step 22), not here. Do not unskip them now.

---

## Phase 7 — Refactor

Update `.hitl/current-change.yaml`: set `current_step: {number: 16, name: "Refactor", phase: "Build"}`.

1. **Review the passing code** for simplification opportunities:
   - Remove duplication
   - Improve naming
   - Extract helpers if warranted (not prematurely)

2. **After each refactor change**, rerun the test suite. If any test breaks, revert the refactor — it changed behavior, not just style.

3. **Present the final refactored code** to the user.

4. **Update `.hitl/current-change.yaml`** — mark `tests_red: done` and `tests_green: done` in `required_evidence`.

5. **Say:** "TDD cycle complete. Tests: [count passing]. Code ready for code review (steps 18-19 of the workflow)."

---

## Important Rules

- Never skip the human review step (Phase 2) — this is where domain expertise enters
