# Readable Test Scenarios: Low-Level Design

> Status: **draft v1 (2026-10-04)**. The exact shapes for FR-36: the file, the IDs, the change-record
> fields, the validator, the registry field, each skill's edits, the new skill, and the install
> paths. Decisions in [`02-adrs.md`](02-adrs.md). What must fail in [`04-test-plan.md`](04-test-plan.md).

## 1. The file

Path: `docs/03-engineering/testing/scenarios/<change-id>.md`, where `<change-id>` is the change's id
in the repo's own form (`GH-123`, `SVC-3`). One file per change. Template:
`ai/shared/templates/test-scenarios-template.md`.

```markdown
# Test scenarios: GH-123 Discount codes at checkout

| | |
|---|---|
| Change | GH-123 |
| Serves | FR-12 |
| Owner | QA |
| Review | PM: pending |
| Written | by HITL at the test plan step, 2026-10-04 |

## What this change does

Shoppers can enter a discount code at checkout and see the new total before paying. It matters
because support gets a ticket a day about codes that "did nothing". Acceptance criteria: FR-12 in
the PRD.

## Scenarios

### SC-GH-123-01: A blank discount code leaves the total unchanged
- Kind: acceptance
- Priority: strongly-recommended
- Serves: FR-12 AC-2
- Added by: qa
- Given: a cart with two items totalling 40.00
- When: the shopper submits an empty code
- Then: the total still shows 40.00 and the field says a code is needed
- Test: tests/e2e/features/checkout.spec.ts

### SC-GH-123-02: An expired code is refused with the expiry date
- Kind: acceptance
- Priority: regression-required
- Serves: INC-004
- Added by: pm (Dana)
- Given: a code that expired yesterday
- When: the shopper applies it
- Then: the total is unchanged and the message names the expiry date
- Test: deferred (qa, "needs the clock fixture from GH-119")

### SC-GH-123-03: removed
- Removed by: qa, 2026-10-06, duplicate of SC-GH-123-01
```

Rules the validator enforces (codes in section 4):

- The context section `## What this change does` exists and has at most five sentences.
- Every scenario heading is `### <ID>: <title>`; `<ID>` is `SC-<change-id>-<nn>`, `<nn>` two or
  more digits, numbered `01` upward with no gaps and no reuse. A removed scenario keeps its heading
  with the title `removed` and one `- Removed by: <who>, <date>, <why>` line.
- Required fields on a live scenario: `Kind` (`acceptance`, `integration`, `regression`),
  `Priority` (`regression-required`, `strongly-recommended`, `optional`), `Serves` (an acceptance
  criterion or incident reference, free text, non-empty), `Added by` (`qa`, `pm`, `dev`, optionally
  followed by a name in parentheses), `Given`, `When`, `Then`, `Test`.
- `Test` is one of: a path or path-and-name (informational; the citation scan is the proof),
  `none yet`, `deferred (<owner>, "<reason>")`, `declined (<owner>, "<reason>")`.
- Whole file at most 1,000 words (ADR-11), counted outside the header table and headings. Over is a
  warning.
- The `Review` header line is a mirror of the change record (ADR-3).

## 2. Citation

A test cites scenario `SC-GH-123-01` when the token `SC-GH-123-01` or `SC_GH_123_01` appears, case
insensitive, in the text of a test unit: its name, docstring, comment or body. A test unit is:

| Language | Start of a unit |
|---|---|
| Python | `def test_...` or `async def test_...` |
| JavaScript, TypeScript | `test(` or `it(` at line start after whitespace, including `test.skip(` |
| Go | `func Test...` |
| Java, Kotlin | a line with `@Test`, the unit runs to the next `@Test` |

A unit runs from its start line to the next unit's start or end of file. Convention for the name
when the language allows: `test_blank_code_leaves_total_SC_GH_123_01`; otherwise the ID goes in the
docstring or the first comment line. One test may cite several IDs; one ID may be cited by several
tests.

A test is **acceptance or integration** (and so must cite) when its file path contains `/e2e/`,
`/integration/`, `/acceptance/` or `/smoke/`, or its file contains `pytest.mark.integration`,
`describe('integration'` or `describe("integration"`. Unit tests are exempt from the test-to-scenario
direction.

The change's test set, for the test-to-scenario direction, is `tests.files[]` in the change record
(written by `dev-tdd`, section 3). Without it the validator falls back to the files under the test
roots that differ from the merge base with the default branch; if git is unavailable it reports
TESTS_UNSCOPED and checks only the scenario-to-test direction.

Test roots: `--tests` (repeatable) or the defaults `tests/`, `test/`, `spec/`, `__tests__/`.

## 3. Change-record fields

In `.hitl/current-change.yaml` (schema: `ai/shared/templates/change-context.schema.yaml`):

```yaml
tests:
  scenarios_file: docs/03-engineering/testing/scenarios/GH-123.md
  scenario_review:
    status: pending            # pending | done | skipped
    # done:
    by: "Dana (PM)"
    ts: 2026-10-05T14:02:00Z
    # skipped (skip-record dialect, not an FR-29 step skip):
    actor: "Sam (QA)"          # who recorded the skip
    pm: "Dana"                 # who was named
    reason: "PM on leave; acceptance criteria were reviewed at intake"
    disposition: defer         # defer | decline
    ts: 2026-10-07T09:10:00Z
  files:                       # the change's own tests, written by dev-tdd at RED
    - tests/e2e/features/checkout.spec.ts
    - tests/test_cart.py
  scenarios_page:              # optional, TS-12
    url: https://claude.ai/artifact/...
    published_at: 2026-10-05T10:00:00Z
    last_pull: 2026-10-06T16:30:00Z
```

`.hitl/config.yaml`: `scenario_review_gate: true` (ADR-5). Absent means false.

## 4. The validator

`ci/test-scenarios/check_scenarios.py`. Shape and contract as `ci/first-pass/check_skips.py`: a
finding is `{code, message, waivable, locus}`; exit 2 when any non-waivable finding exists, 1 with
`--strict` when any waivable one does, else 0; anything it cannot parse is MALFORMED, never a
traceback. Python 3.10, PyYAML only.

```
python3 ci/test-scenarios/check_scenarios.py [--change .hitl/current-change.yaml]
        [--file <scenarios.md>] [--stage draft|review|verify] [--tests <dir>]... [--strict] [--json]
```

| Code | Blocker | When |
|---|---|---|
| FILE_MISSING | yes | No scenarios file: the record names a path that does not exist, or names none and the stage is `review` or `verify`. |
| MALFORMED | yes | Heading, field list or record cannot be parsed; a required field is missing; a value is outside its enum. Message carries the line. |
| ID_PREFIX | yes | An ID's change part is not this change's id. |
| ID_DUPLICATE | yes | The same ID twice. |
| ID_SEQUENCE | yes | Numbers are not `01..N` contiguous, counting removed ones. |
| CONTEXT_MISSING | yes | No `## What this change does` section, or it is empty. |
| CONTEXT_LONG | no | The context has more than five sentences. |
| SCENARIO_UNCITED | yes (warning at `draft`) | A live scenario with no citing test and a `Test` field that is not `deferred (...)` or `declined (...)`. |
| DEFERRAL_INCOMPLETE | yes | `deferred` or `declined` without both an owner and a quoted reason. |
| TEST_UNCITED | yes (warning at `draft`) | An acceptance or integration test unit in the change's test set cites no ID. Locus is `file:line`. |
| TESTS_UNSCOPED | no | The change's test set could not be determined; the test-to-scenario direction was not run. |
| REVIEW_PENDING | at `verify` only | `scenario_review.status` is `pending` (warning at `review`). |
| REVIEW_RECORD_INCOMPLETE | yes | `done` without `by` and `ts`; `skipped` without `actor`, `pm`, `reason`, `disposition`, `ts`. |
| REVIEW_HEADER_STALE | no | The file's `Review` line disagrees with the record. |
| LENGTH | no | More than 1,000 words. |
| PLAIN | no | An em dash, or a word from the plain-English table, in the file. The table is read from `plain-english.md` next to the validator's shipped copy or under `ai/shared/`; without it only the em dash check runs. |

Stages. `draft` is what `qa-scenarios` runs right after a person adds a scenario, before any test
exists: the structural codes block, the three coverage codes warn. `review` is test review; `verify`
is QA verify, where a pending review also blocks.

Output, human: one line per finding, `[BLOCK]` or `[warn]`, then a one-line verdict:
`Scenarios: N scenarios, M cited, K deferred, review <status>.` With `--json`: the finding list.

## 5. Registry

`ai/shared/templates/test-registry-template.yaml`: each entry gains

```yaml
    scenarios: [SC-GH-123-01]   # the scenario IDs this test cites; [] when a unit test cites none
```

Written by `dev-tdd` step 7. Read by nothing new in this slice; impact analysis may read it later.

## 6. Edits to existing skills

**`ai/claude/qa/plan-tests/SKILL.md`**

- Step 4: keep the scenario format; add `Kind` and `Serves` to it. Plain-English rule: one
  behaviour, one line per Given, When and Then where the behaviour allows, the user's words, no
  identifiers.
- Step 5 becomes "Write the file and hand off": write
  `docs/03-engineering/testing/scenarios/<change-id>.md` from the template with every scenario,
  IDs `SC-<change-id>-01` upward, `Added by: qa`, `Test: none yet`; keep `tests.qa_scenarios` in the
  record for the breadcrumb but set `tests.scenarios_file` and `tests.scenario_review.status:
  pending`; post one line on the issue: the path and "add any you can think of: `/hitl:qa-scenarios`
  or edit the file". That line is the PM's one invitation (TS-11). Then the existing close.
- Reference `shared/test-scenarios.md` for the rules.

**`ai/claude/tdd/SKILL.md`**

- Refusal rule (new, after the packet rule): if `.hitl/config.yaml` has `scenario_review_gate: true`
  and `tests.scenario_review.status` is `pending`, stop with a one-line message naming the PM review
  and `/hitl:qa-scenarios`.
- Phase 1, new step 6: read the scenarios file. If it exists: cite the ID of the scenario each test
  serves in its name or docstring (section 2); every acceptance and integration test cites one. Show
  the acceptance scenarios by title in one short list and say one line: "These are the acceptance
  scenarios the tests cover. Add one with `/hitl:qa-scenarios` if you can think of a behaviour that
  is missing." That is the developer's one invitation; do not repeat it. If the file does not exist
  (the test plan step was skipped): write it from the generated tests, one scenario per acceptance
  or integration test, titles in plain words, `Added by: dev`, and set `tests.scenario_review` to
  `skipped` with the developer as `actor`, `pm` from the issue or "PM", reason "test plan step
  skipped", `disposition: defer`.
- Step 7 (registry): add `scenarios: [...]` per entry.
- After generating tests, write `tests.files[]` to the change record.
- Phase 2 checklist gains item 8: "Scenarios: does every acceptance and integration test cite the
  scenario it serves? Is any scenario in the file still `none yet` without a test?"
- The review before Phase 2 is the developer's own review of their tests and stays as it is.

**`ai/claude/qa/review-tests/SKILL.md`**

- Step 3 matrix gains a `Scenario` column (the ID the test cites).
- New Step 5b "Run the scenario check": the fence below, stage `review`. Exit 2 blocks with the
  findings quoted; warnings are listed in the report. QE's one invitation: one line, "Add a
  scenario you can think of with `/hitl:qa-scenarios`."
- Step 6 approval text adds "Scenarios: N, all cited or deferred."

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/test-scenarios/check_scenarios.py"; [[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/test-scenarios/check_scenarios.py"
python3 "$CHK" --change .hitl/current-change.yaml --stage review
```

**`ai/claude/qa/verify-quality/SKILL.md`**

- Step 1 reads the scenarios file alongside the registry.
- Step 3 verifies acceptance criteria through the scenarios: the table gains a `Scenario` column.
- New Step 5b: run the validator at stage `verify` (same fence, `--stage verify`). If
  REVIEW_PENDING: ask the person running the step, once, whether to record the PM review as skipped
  (who is the PM, why); write `tests.scenario_review` as `skipped`, update the file's `Review` line,
  re-run. Any other blocker blocks as a QA defect.
- Step 6 approval comment: after the first line, one line per scenario, failures first:
  `- <title> (added by <who>): pass|fail`. Then the existing text.

## 7. The new skill: `ai/claude/qa/scenarios/SKILL.md` (`/hitl:qa-scenarios`)

Frontmatter: `description` (any role: add, change or review the test scenarios for a change by
talking; publish them as a shared page; pull what people did on the page back into the file),
`argument-hint: "[change id] [add | review | publish | pull]"`, `disable-model-invocation: true`.
Preamble: the standard `.hitl/` check. Locate the file from `tests.scenarios_file` in the change
record, or from the change id in `$ARGUMENTS`; if none, say so and name `/hitl:qa-plan-tests`.

Modes, chosen from `$ARGUMENTS` or from what the person says:

- **add** (default when the person describes a behaviour): write it as Given, When, Then in their
  words; assign the next ID; ask which acceptance criterion or incident it serves when not clear
  (no answer: `Serves: question for PM` and one line on the issue); `Added by: <role> (<name>)` from
  `$ARGUMENTS` or what the person said, else asked once at the first write (nothing in `.hitl/`
  records a session role); `Test: none yet`; `Kind` and `Priority`
  proposed in the same line and changeable; append to the file; confirm in one line with the ID.
  Several in one conversation are fine; one confirmation each.
- **review**: read the acceptance scenarios back grouped by `Serves`, one line each; ask once "what
  else could go wrong?"; add what they say (as **add**). When the person is the PM and says they are
  done, write `tests.scenario_review` `done` with `by` and `ts`, rewrite the file's `Review` line,
  one line on the issue. When they are not the PM, record nothing about the review.
- **publish**: if the Artifact tool is available in this session, build a page from the file (the
  context, the scenarios grouped by `Serves`, the review state, a comment affordance per scenario
  and an add-a-scenario form when the runtime can collect) and publish it private; write
  `tests.scenarios_page`; give the link and say it is private until shared. If the tool is not
  available, say so in one line and give the file path. Never publish unless asked in this run.
- **pull**: read the page's comments and submitted rows since `last_pull`; for each: a new scenario
  becomes **add** with `Added by: <name>`; an edit to an existing scenario is applied and the
  scenario gets `- Edited by: <name>, <date>`; a comment that asks a question is appended under the
  scenario as `- Question (<name>): ...` and one line goes on the issue for the PM; a comment from
  the PM saying the review is done records it as in **review**. Rewrite the file, update
  `last_pull`, republish so the page shows the pulled state, report one line per pulled item.

Rules: everything written follows `shared/plain-english.md`; the file is the record and the page a
view (ADR-9); after any write, run the validator at stage `draft` and show its one-line verdict.
Close the way `shared/next-step.md` describes.

## 8. Shared prose and templates

- `ai/shared/test-scenarios.md`: the rules in sections 1, 2 and the invitation rule, written for
  the model, referenced by the four skills. Added to `SHARED_PROSE` in the plugin repo's `build.sh`.
- `ai/shared/templates/test-scenarios-template.md`: section 1's skeleton with placeholders in angle
  brackets (no double-brace placeholders; the template lint checks).
- `ai/shared/plain-english.md` ceilings table: `| Test scenarios file | two pages (1,000 words) for
  a change with five acceptance criteria |`.
- `ai/shared/templates/change-context.schema.yaml`: the fields in section 3.
- `ai/shared/templates/test-registry-template.yaml`: the `scenarios` field.

## 9. Install and sync (ADR-10)

| Place | Edit |
|---|---|
| `tools/scripts/init-project.sh` | A block after `ci/linked`: `hitl_copy_tools ci/test-scenarios`. |
| `ai/claude/start-brownfield/SKILL.md`, `ai/claude/start-from-prd/SKILL.md` | The copy fence gains `ci/test-scenarios`. |
| `ci/first-pass/migrate_project.py` `SYNC_SETS` | `{"src": "shared/ci/test-scenarios", "dst": "ci/test-scenarios", "mode": "co-owned", "glob": "*.py"}`. |
| `tools/scripts/shipped-validators-hashes.py` | `("ci/test-scenarios", "ci/test-scenarios", True)`; then run it. |
| `ci/workflows/test-scenarios-check.yml` | A CI template like `first-pass-check.yml`, running the validator at stage `review` on pull requests; installed by `init-project.sh` the same way. |
| Plugin repo `scripts/build.sh` | Copy `ci/test-scenarios/*.py` (not `test_*`) to `shared/ci/test-scenarios/`; add `test-scenarios.md` to `SHARED_PROSE`. |
| `ai/claude/plugin/plugin.json` | `"ai/claude/qa/scenarios"` in `skills`. |

## 10. Documents

`docs/roles/qa.md` and `docs/roles/pm.md` (one entry each; the developer's invitation lives in the TDD skill, so `docs/roles/developer.md` is unchanged), `README.md` role
table (QA gains `qa-scenarios`; counts), `docs/01-product/prd.md` FR-5 (QA: plan, scenarios, review,
verify) and FR-36 moves out of Backlog when released, `CHANGELOG.md` under Unreleased.
