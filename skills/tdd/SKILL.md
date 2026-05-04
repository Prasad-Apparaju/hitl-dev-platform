---
name: tdd
description: Orchestrate the TDD-as-design Red → Green → Refactor cycle where tests drive the design before implementation code exists. Use after the LLD is approved and before writing any implementation code. Requires an approved LLD — refuses to proceed without one.
argument-hint: "[LLD path or issue number and component name]"
disable-model-invocation: true
---

# TDD as a Design Tool

Orchestrate the Red → Green → Refactor cycle where tests drive the design before code exists.

**Input:** $ARGUMENTS (description of what to implement — should reference an LLD or issue)

If `$ARGUMENTS` is empty, ask: "What are you implementing? Point me to the LLD or issue."

**Refusal rule:** If no LLD path is provided or found, stop: "No LLD found. Write the LLD first using `/generate-docs` — this skill generates tests FROM the spec, not without one."

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

6. **Generate maximum test coverage** from the LLD + manifest, filling gaps not already covered:
   - Happy path tests for every method in the LLD
   - Error path tests for every `error_modes` entry in the facade
   - Precondition tests for every `preconditions` entry
   - Boundary entity shape tests (verify the entity matches the manifest shape)
   - Contract tests from facade APIs (verify the domain's promises to other domains)
   - Convention tests (e.g., if `idempotency-keys` convention applies, test that the tool rejects missing keys)
   - Regression tests for every incident found in step 4

7. **Register each new test** in the test registry (`docs/03-engineering/testing/test-registry.yaml`) with:
   - domain, risk level, type (unit/integration/contract), origin: `tdd`
   - For incident regression tests: include `incident_ref`

5. **Present all generated tests** to the user. Do NOT proceed to Phase 2 until the user reviews.

6. **STOP and present a specific review checklist:**

   > **Tests need your review before I write any code. Work through this list:**
   >
   > 1. **Coverage gaps** — I generated tests from the LLD. What domain knowledge or business rules do you know that aren't in the LLD? Add tests for those now.
   > 2. **Incident registry** — Check for past failures in this domain (graph query preferred: `/graphify query "past incidents affecting domain: <domain-name>"`, or read `docs/04-operations/incident-registry.yaml` directly). Are any of those failure modes missing from the tests above?
   > 3. **Security edge cases** — Is there a test for: unauthenticated access rejected? User A cannot access User B's data? Input at max length / empty / null?
   > 4. **Realistic failure modes** — What's the most likely way this breaks in production that I haven't tested? (network timeout? partial write? concurrent requests?)
   > 5. **Test quality** — Read 3 random tests from the list. Does the assertion actually verify the behavior described in the test name? If not, those tests need to be rewritten.
   >
   > Remove any tests that only verify implementation details (mock called once, internal method invoked). Those tests will break on every refactor without catching real bugs.
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

2. **If all pass**, proceed to Phase 7.

3. **If new tests pass but existing tests fail**, flag: "Regression detected in [test]. The new code broke existing behavior." Fix before proceeding.

4. **If new tests still fail**, continue generating code to make them pass. Return to Phase 5.

---

## Phase 7 — Refactor

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
