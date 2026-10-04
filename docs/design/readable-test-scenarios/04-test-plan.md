# Readable Test Scenarios: Test Plan

> Status: **draft v1 (2026-10-04)**. What must fail for FR-36. Validator cases are proven by
> mutation: each NEG case has a fixture that differs from a passing one by the one defect it names,
> and the test asserts the code and the exit. Wiring cases assert the seams, in the style of
> `ci/wiring/test_wiring.py`.

## 1. Validator: `ci/test-scenarios/test_check_scenarios.py`

Fixtures are built in a temp dir by a helper that writes a change record, a scenarios file and a
tests tree from short strings.

| Case | Fixture | Expect |
|---|---|---|
| POS-1 | Two scenarios, both cited by an e2e test, review `done` | exit 0, no findings |
| POS-2 | One deferred with owner and reason, one cited | exit 0 |
| POS-3 | Removed scenario `02` between live `01` and `03` | exit 0 |
| POS-4 | Citation by underscore form `SC_GH_123_01` in a Python test name | cited |
| POS-5 | Unit test under `tests/unit/` with no ID | no TEST_UNCITED |
| POS-6 | Stage `review`, review `pending` | exit 0, REVIEW_PENDING as warning |
| POS-7 | Record `skipped` with actor, pm, reason, disposition, ts, stage `verify` | exit 0 |
| NEG-1 | Record names a file that does not exist | FILE_MISSING, exit 2 |
| NEG-2 | No `scenarios_file` field, stage `verify` | FILE_MISSING, exit 2 |
| NEG-3 | Heading `### SC-GH-123-1 title` (no colon) | MALFORMED with line, exit 2 |
| NEG-4 | Scenario missing `Then` | MALFORMED, exit 2 |
| NEG-5 | `Kind: manual` | MALFORMED, exit 2 |
| NEG-6 | ID `SC-GH-999-01` in change GH-123 | ID_PREFIX, exit 2 |
| NEG-7 | Two `SC-GH-123-01` | ID_DUPLICATE, exit 2 |
| NEG-8 | `01`, `03` with no `02` | ID_SEQUENCE, exit 2 |
| NEG-9 | No context section | CONTEXT_MISSING, exit 2 |
| NEG-10 | Live scenario, `Test: none yet`, no test cites it | SCENARIO_UNCITED, exit 2 |
| NEG-11 | `Test: deferred (qa)` without a reason | DEFERRAL_INCOMPLETE, exit 2 |
| NEG-12 | e2e test unit with no ID, file in `tests.files` | TEST_UNCITED with `file:line`, exit 2 |
| NEG-13 | Same as NEG-12 but the file is not in `tests.files` | no TEST_UNCITED (out of scope) |
| NEG-14 | Stage `verify`, review `pending` | REVIEW_PENDING blocker, exit 2 |
| NEG-15 | Review `done` without `ts` | REVIEW_RECORD_INCOMPLETE, exit 2 |
| NEG-16 | Review `skipped` without `pm` | REVIEW_RECORD_INCOMPLETE, exit 2 |
| NEG-17 | File `Review` line says `done`, record says `pending` | REVIEW_HEADER_STALE warning |
| NEG-18 | 1,100 words | LENGTH warning; with `--strict` exit 1 |
| NEG-19 | An em dash in a Then | PLAIN warning |
| NEG-20 | Change record with a duplicate YAML key | MALFORMED, exit 2, no traceback |
| NEG-21 | Scenarios file is a symlink out of the repo or over 50 MB | MALFORMED, exit 2 |
| NEG-22 | No `tests.files`, not a git repo | TESTS_UNSCOPED warning, scenario-to-test direction still runs |
| NEG-23 | Six-sentence context | CONTEXT_LONG warning |
| NEG-24 | `--json` | output parses as a list of findings with the four keys |
| NEG-25 | Comment line inside a test unit cites the ID, name does not | cited (the whole unit counts) |
| POS-8 | Stage `draft`, live scenario `none yet`, no tests | exit 0, SCENARIO_UNCITED as warning |
| NEG-27 | Stage `draft`, duplicate ID | ID_DUPLICATE, exit 2 |
| NEG-26 | Playwright `test.skip('pending environment', ...)` unit with no ID in `tests/e2e/` | TEST_UNCITED |

A mutation check in the test file: for each blocker code, assert that removing the defect from the
fixture makes the code disappear, so no case passes for an unrelated reason.

## 2. Wiring: additions to `ci/wiring/`

| Case | Asserts |
|---|---|
| W-1 | Every skill that runs `check_scenarios.py` resolves it with `ROOT=` set in the same fence and a `$ROOT/shared/ci/test-scenarios/` fallback (the 2.16.0 lesson). |
| W-2 | `shipped-validators-hashes.py` lists `ci/test-scenarios`; `ci/shipped-validators.sha256` contains the current hash of `check_scenarios.py` (existing manifest test extended by adding the directory; the test should fail before the hash is regenerated). |
| W-3 | `migrate_project.py` `SYNC_SETS` has the `ci/test-scenarios` entry; `init-project.sh` run against a temp target lands `check_scenarios.py` and not `test_check_scenarios.py` (extends `test_shipped_tools_are_self_contained.py`). |
| W-4 | The start-brownfield and start-from-prd copy fences name `ci/test-scenarios`. |
| W-5 | `plugin.json` lists `ai/claude/qa/scenarios`. |
| W-6 | `ai/shared/test-scenarios.md` exists and is referenced by the four skills; the plugin build's `SHARED_PROSE` contains it (checked in the plugin repo's own test if one exists, else by building). |
| W-7 | `test-scenarios-template.md` has no double-brace placeholders and passes the template plain-English lint. |
| W-8 | `plain-english.md` ceilings table has the scenarios row. |
| W-9 | `change-context.schema.yaml` has `tests.scenarios_file`, `tests.scenario_review`, `tests.files`, `tests.scenarios_page`. |
| W-10 | `test-registry-template.yaml` has `scenarios`. |
| W-11 | `qa-plan-tests` no longer tells the model to report scenarios only in chat: its Step 5 names the file path. |
| W-12 | `dev-tdd` names `scenario_review_gate` and the Fast Track file write. |
| W-13 | The new skill passes `ci/skill-lint/check_skills.py` and `test_skill_calls_are_achievable.py` (it tells people what to run, never the model). |

## 3. Behaviour, by hand in a sandbox product repo

Run in a `CLAUDE_CONFIG_DIR` sandbox against a built plugin, with a tiny product repo that has a
PRD with one FR and two acceptance criteria.

1. `/hitl:qa-plan-tests` writes the file with at least two scenarios, IDs `01` and `02`, the
   context in five sentences or fewer, one invitation line on the issue. The change record has
   `scenarios_file` and `scenario_review.status: pending`.
2. `/hitl:qa-scenarios add` with "what if the code has expired" appends `03` with `Added by`, asks
   which criterion when unclear, confirms in one line, runs the validator and shows its verdict.
3. `/hitl:dev-tdd` with the gate off starts RED without waiting; the generated e2e test cites IDs;
   `tests.files` is written; the checklist item 8 is present; the invitation is one line and appears
   once.
4. `/hitl:dev-tdd` with `scenario_review_gate: true` and review `pending` refuses with one line.
5. `/hitl:qa-review-tests` runs the validator; a scenario with `none yet` and no test blocks.
6. `/hitl:qa-verify-quality` with review `pending` asks once, records `skipped` with the PM named,
   re-runs, and the approval comment lists scenarios with who added them, failures first.
7. Fast Track: skip `test_plan` at intake; `/hitl:dev-tdd` writes the file from the tests with
   `Added by: dev` and the review `skipped`.
8. `/hitl:qa-scenarios publish` in a session with the Artifact tool gives a private link; in one
   without, says so and gives the path. `pull` after a comment adds the scenario with the
   commenter's name.
9. `python3 ci/wiring/test_plain_english.py` and the full gate set in `docs/releasing.md` step 4
   pass; `bash ci/breadcrumb/run_matrix.sh` is unchanged (no catalog edit).
