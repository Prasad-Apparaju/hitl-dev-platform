# TDD as a Design Tool

Orchestrate the Red → Green → Refactor cycle where tests drive the design before code exists.

**Input:** $ARGUMENTS (description of what to implement — should reference an LLD or issue)

If `$ARGUMENTS` is empty, ask: "What are you implementing? Point me to the LLD or issue."

---

## Phase 1 — Generate Tests (RED)

1. **Read the LLD** for the component being implemented. If no LLD exists, stop and say: "No LLD found. Write the LLD first — this skill generates tests FROM the spec, not without one."

2. **Read the system manifest** (`docs/system-manifest.yaml`) for:
   - The domain this component belongs to
   - The `facade_apis` for this domain (contract tests)
   - The `cross_cutting` conventions that apply (convention tests)
   - The `boundary_entities` that cross this domain (entity shape tests)

3. **Generate maximum test coverage** from the LLD + manifest:
   - Happy path tests for every method in the LLD
   - Error path tests for every `error_modes` entry in the facade
   - Precondition tests for every `preconditions` entry
   - Boundary entity shape tests (verify the entity matches the manifest shape)
   - Contract tests from facade APIs (verify the domain's promises to other domains)
   - Convention tests (e.g., if `idempotency-keys` convention applies, test that the tool rejects missing keys)

4. **Register each test** in the test registry (`docs/test-registry.yaml`) with:
   - domain, risk level, type (unit/integration/contract), origin: `tdd`

5. **Present all generated tests** to the user. Do NOT proceed to Phase 2 until the user reviews.

6. **STOP and ask:**
   - "Review the tests above. Add edge cases, domain-specific scenarios, or integration tests I missed."
   - "When you're satisfied, say 'tests approved' to proceed."

---

## Phase 2 — Human Reviews + Adds Tests

Wait for the user to:
- Add edge cases AI missed
- Add scenarios from the incident registry
- Remove tests that are trivial or wrong
- Challenge assumptions

When the user says "tests approved" or equivalent, proceed to Phase 3.

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

4. **Say:** "TDD cycle complete. Tests: [count passing]. Code ready for code review (steps 13-14 of the workflow)."

---

## Important Rules

- Never generate implementation code before tests exist and are reviewed
- Never skip the human review step (Phase 2) — this is where domain expertise enters
- If the LLD is too vague to generate tests from, say so and stop — do not guess
- Register every test in the test registry with metadata
- The test suite IS the refined specification — treat it as such
