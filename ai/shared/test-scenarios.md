# Test scenarios: the shared rules (FR-36)

One file of test scenarios per change, written the way a manual tester writes them, that a PM, a
developer and QE can read in minutes and add to in a sentence. QA owns the file. Every scenario has
an ID its test cites. `ci/test-scenarios/check_scenarios.py` proves the link both ways at test
review and at QA verify. Used by `qa-plan-tests`, `dev-tdd`, `qa-review-tests`, `qa-verify-quality`
and `qa-scenarios`. Do not fork these rules into a skill; point at this file.

## The file

Path: `docs/03-engineering/testing/scenarios/<change-id>.md`. Template:
`shared/templates/test-scenarios-template.md`. Header table (Change, Serves, Owner, Review,
Written), then `## What this change does` in at most five sentences with a pointer to the
acceptance criteria, then `## Scenarios`.

One scenario is one heading and eight fields:

```markdown
### SC-<change-id>-<nn>: <title in the user's words>
- Kind: acceptance | integration | regression
- Priority: regression-required | strongly-recommended | optional
- Serves: <acceptance criterion or incident, for example FR-12 AC-2 or INC-004>
- Added by: qa | pm | dev   (a name in parentheses is welcome: pm (Dana))
- Given: <one precondition>
- When: <one action>
- Then: <one visible outcome>
- Test: none yet | <path> | deferred (<owner>, "<reason>") | declined (<owner>, "<reason>")
```

IDs run `01` upward, never reused. A removed scenario keeps its heading with the title `removed`
and one line: `- Removed by: <who>, <date>, <why>`.

## How to write one

- One behaviour per scenario. If a Then needs "and", it is two scenarios.
- The user's words for the thing: "the total", not `cart.total_cents`. No code identifiers, no
  file paths, no HTTP codes unless the user sees them.
- One line each for Given, When and Then where the behaviour allows.
- The title says what is true when the test passes: "A blank code leaves the total unchanged".
- Everything follows `shared/plain-english.md`. The whole file fits in 1,000 words for a change
  with five acceptance criteria; over that, split the change or trim, do not pad.

## How a test cites a scenario

Put the ID in the test's name where the language allows (`test_blank_code_SC_GH_123_01`) or in its
docstring or first comment. Hyphens or underscores, any case. Every acceptance and integration test
cites at least one scenario; a unit test may. One test may cite several scenarios.

## The record

`.hitl/current-change.yaml` under `tests:`: `scenarios_file` (the path), `scenario_review`
(`status: pending | done | skipped`, with `by` and `ts` for done; `actor`, `pm`, `reason`,
`disposition`, `ts` for skipped), `files` (the change's own test files, written at RED),
`scenarios_page` (optional: `url`, `published_at`, `last_pull`). The record is authoritative for the
review state; the file's `Review` line mirrors it. A skipped review is not an FR-29 step skip and
goes in no `skips[]` entry.

## Who adds, and how they are asked

Anyone adds by saying the behaviour to HITL (`/hitl:qa-scenarios`) or by editing the file; the
check treats both the same. Each role is invited once per change, where they already are:

| Who | When | The one line |
|---|---|---|
| PM | the file is written | on the issue: the path, and "add any you can think of" |
| Developer | RED starts | the acceptance scenario titles, and "add one if a behaviour is missing" |
| QE | test review | "add a scenario you can think of" |

Never a prompt that waits for an answer. Never a second reminder on the same change. If nobody adds
scenarios, shorten the file before adding a prompt.

## The PM review

The PM reads the acceptance scenarios in their own time, edits or adds, and says they are done; HITL
records `done`. RED does not wait unless `.hitl/config.yaml` has `scenario_review_gate: true`. The
review is due before QA verify closes; at verify, `pending` is recorded `skipped` with the PM named
and a reason, by the person running the step, once asked. Never dropped quietly.

## The page

`qa-scenarios publish` renders the file as a private page with the host's Artifact tool when the
session has it; `pull` brings comments and additions back into the file with the person's name and
republishes. The file is the record; a page row does not exist to the check until pulled. One page
per change, never one across changes. Without the tool: say so, give the path.
