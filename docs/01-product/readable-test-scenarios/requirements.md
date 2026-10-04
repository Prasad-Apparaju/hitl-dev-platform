# Readable Test Scenarios: Requirements

> **What this is.** Every change gets a file of test scenarios written the way a manual tester
> writes them: Given, When, Then, one behaviour each. QA owns the file. The PM reviews the
> acceptance scenarios there and can add to them before any code exists. Every scenario has an ID
> that its test cites, and a check proves the link both ways. This is **FR-36** in the
> [PRD](../prd.md) backlog table (§5.7), ticket
> [#148](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/148), status Backlog. The
> design (how it is built) goes in `docs/design/readable-test-scenarios/`, not started.
> Status: **draft v1.4 (2026-10-04)**, one validation review (section 11). Related: `qa-plan-tests`, `qa-review-tests`,
> `dev-tdd`, the test registry, FR-29 skip-with-record.

## 1. The problem

HITL already writes test scenarios in a human format. The QA plan-tests skill reads the acceptance
criteria and the design, queries the incident registry, and writes each scenario as Given, When,
Then with a name and a priority. Then it reports them in chat and saves a name and a one-line
description per scenario in the change file. The full scenario is gone when the session ends.

What a PM or developer can open afterwards is test code: pytest files, Playwright stubs named after
an acceptance criterion, and a registry that indexes tests by name and domain. None of that is a
document a PM reads, reviews or adds a row to. And the PM is not in the test path. The catalog puts
the PM at requirements and at the impact brief. The person who reviews tests in the TDD cycle is
whoever is running the session, in practice the developer.

| What exists | What it does | What it misses |
|---|---|---|
| `qa-plan-tests`, step 4 | Writes Given/When/Then scenarios, grouped by priority, one E2E scenario per acceptance criterion, one smoke journey | Reports them in chat; persists only a name and one line each |
| Test strategy template | A manual test case table: objective, preconditions, steps, expected, priority, linked requirements and incidents | System-level; no skill fills it per change |
| `dev-tdd`, Phase 2 | Stops after generating tests, before RED is verified, and waits for a human to review and add tests against a checklist | The human is the developer; the review leaves no readable artifact |
| `qa-review-tests` | Checks every acceptance criterion has a test, every error mode is exercised, regressions present | Checks tests against criteria, not against the scenarios QA wrote |
| Test registry | Name, domain, risk, type, origin, incident link per test | An index of code, not steps a person can follow |

**What we deliver.** One markdown file per change, in a QA-owned place, that holds the full
scenarios. A stable ID per scenario that the test cites. A PM review of the acceptance scenarios
that runs alongside the build, recorded, and never holds up coding. A fail-closed check that every scenario has a test or a recorded reason, and
every acceptance test has a scenario. No new tooling and no new grammar.

## 2. Who needs it

| Who | What they need |
|---|---|
| PM | Open one file, read the acceptance scenarios in plain words, add the case the team missed, and see later which passed |
| Developer | Write tests from scenarios instead of from a chat transcript; know which scenario each test serves |
| QA | Own the scenarios, review the developer's tests against them, record what was deferred and why |
| Architect | See integration scenarios at the boundaries the design declares |
| HITL maintainer | One file format, one ID scheme, one checker, wired into the steps that already exist |

## 3. Scope

**In.** The scenarios file and its format. The ID scheme. The write path in `qa-plan-tests`. The
PM review of acceptance scenarios and its record. The citation rule in `dev-tdd`. The two-way check
in `qa-review-tests` and its validator. The per-scenario result in `qa-verify-quality`. The scenario
ID in the test registry. The Fast Track path where the test plan step was skipped. A shared page per
change, published from the file on request, where people review, comment, add and edit without a
Claude Code session, pulled back into the file by HITL.

**Out.** Gherkin or any BDD runner. Generating test code by parsing the scenarios. A test
management tool or a manual test execution tracker. Replacing the acceptance criteria in the PRD;
they stay the source and the scenarios elaborate them. Native mobile test frameworks.

**Slices.**

| Slice | What it delivers | Requirements |
|---|---|---|
| 1 The file and the IDs | `qa-plan-tests` writes the file; IDs; `dev-tdd` cites them; the registry carries them | TS-1, TS-2, TS-7, TS-8 |
| 2 People in the loop | The PM review, asynchronous by default, recorded; adding a scenario by chat or on the shared page; one invitation per role; the review by chat or page | TS-3, TS-10, TS-11, TS-12 |
| 3 The check and the report | Two-way validator at test review and at QA verify; a PM-added scenario is a tracked gap; per-scenario results at verify | TS-4, TS-5, TS-6, TS-9 |

## 4. Goals

1. A PM can review and add to the tests for a change without reading code.
2. No scenario is lost. What QA wrote at design time is what the developer tests against and what
   verify reports on.
3. Every acceptance or integration test traces to a scenario, and every scenario to a test or a
   recorded reason it has none.
4. Nothing new on the Fast Track path except one file that was going to exist anyway.
5. Reviewing takes minutes and adding takes a sentence. A PM, developer or QE reads the file
   without opening anything else, and adds a scenario by saying it to HITL in their own words.

## 5. Requirements

Requirement IDs are `TS-<n>`.

| ID | Requirement | Priority | Slice |
|---|---|---|---|
| **TS-1** | **One scenarios file per change, written at the test plan step.** `qa-plan-tests` writes the full scenarios to `docs/03-engineering/testing/scenarios/<change-id>.md`, never only to chat. The file header names the change, the requirement it serves, the owner (QA) and, for the reader, the review state; the change record is the authoritative place for that state (TS-3). Each scenario carries: ID, title, kind (acceptance, integration, regression), priority (regression-required, strongly recommended, optional), the acceptance criterion or incident it comes from, Given, When, Then, who added it (qa, pm, dev), and the test that cites it or the reason none does. The exact layout is the design's call; these fields are not. | Must | 1 |
| **TS-2** | **A stable ID per scenario, cited by its test.** IDs are `SC-<change-id>-<nn>` (SC for scenario; `TS-` is this document's requirement prefix and `TC-` is the strategy template's test-case prefix), assigned in order and never reused, including after a scenario is removed. A test that serves a scenario carries the ID in its name or its docstring. One test may cite several scenarios; one scenario may be cited by several tests. | Must | 1 |
| **TS-3** | **The PM reviews the acceptance scenarios; the review does not hold up coding.** When QA writes the file, the PM is told where it is (the issue comment today; the per-change block when #112 ships). The PM reads the acceptance scenarios in their own time and may edit or add any. RED starts when the developer is ready; nothing waits for the PM. The review is recorded in the change file with who and when. It is due before QA verify closes; if it is still missing then, the person running verify records it as skipped in the change record, with the PM named and a reason, using the skip-record field dialect (`actor`, `reason`, `ts`, `disposition`) but not as an FR-29 step skip, because the review is not a catalog step. Never dropped quietly. A scenario the PM adds or changes after RED has started is a gap under TS-5: the check surfaces it, the developer covers it or QA defers it with a reason. Teams that would rather wait can set a preference that makes the review a gate before RED; the default is not to wait. | Must | 2 |
| **TS-4** | **A two-way check at QA review, fail-closed.** `qa-review-tests` runs a validator: every scenario in the file is cited by at least one test, or carries a recorded deferral with an owner and a reason; every acceptance and integration test in the change cites at least one scenario. Either failure blocks QA approval. The validator runs at test review and again at QA verify, because test review is a ceremony step Fast Track may skip and QA verify is a hard gate; a missing file is a blocker at both. The validator lives under `ci/` beside the other fail-closed checkers and can run in the product repo's CI. | Must | 3 |
| **TS-5** | **A scenario the PM adds is a gap until a test cites it.** A scenario added after the PM review, by anyone, is a TS-4 failure until it is cited or deferred with a reason. This is the behaviour Gherkin gives for free, delivered by the check instead of by a runner. | Must | 3 |
| **TS-6** | **Verify reports per scenario, in the scenario's words.** `qa-verify-quality` maps test results back to scenario IDs and posts pass or fail per scenario title to the issue, with who added the scenario, so the PM reads "a blank discount code leaves the total unchanged (added by pm): pass", not a pytest node id. A failure on a scenario a person added is listed first in the comment; it is the clearest evidence the review was worth their time. | Should | 3 |
| **TS-7** | **The registry carries the scenario ID.** Each test registry entry gains a `scenarios` list. Impact analysis can then answer "which scenarios cover this domain" the way it answers for tests today. | Should | 1 |
| **TS-8** | **The file is readable on its own, and short.** Three parts. *Context once, at the top:* what the change does for whom, in at most five sentences, and a link to the acceptance criteria. A reader needs nothing else open to review the scenarios. *Each scenario stands alone:* Given, When, Then in plain English under `ai/shared/plain-english.md`, one behaviour per scenario, one line each where the behaviour allows, no code identifiers, no file paths, the user's words for the thing. The acceptance criterion it serves is named, so a reader can judge whether the scenario actually tests it. *Concise:* a change with five acceptance criteria fits on two pages, which the lint counts as 1,000 words; the file gets a row in the plain-English ceilings table and the lint flags longer files, which is a prompt to split or trim, not a block. The E2E scenario per acceptance criterion and the smoke journey already required by `qa-plan-tests` follow the same rules. | Must | 1 |
| **TS-9** | **Fast Track still gets the file.** When the test plan step is skipped, `dev-tdd` writes the scenarios file from the tests it generates, marked `added-by: dev`, so every change that reaches GREEN has a file the PM can read later. The review is then recorded as skipped in the change record with the developer as `actor` and the reason "test plan step skipped", the same dialect as TS-3. | Should | 3 |
| **TS-10** | **Anyone adds or changes a scenario by talking to HITL.** From any role's session, or on the shared page (TS-12), a person describes the behaviour in their own words ("what if the discount code has expired"). HITL writes it as Given, When, Then, assigns the next ID, names the acceptance criterion it serves (asks which when unclear; none is a question for the PM, not a new requirement), marks who added it, writes it to the file and confirms in one line. Editing the file by hand is also allowed; the check treats both the same. The review itself works the same way: HITL reads the acceptance scenarios back grouped by criterion and asks what else could go wrong; the person answers; HITL writes. Nobody has to learn the format to contribute. | Must | 2 |
| **TS-11** | **One invitation per role, where they already are, never a block.** The PM is invited when the file is written: one line in the issue comment (or the per-change block once #112 ships) with the path, the page link when one exists (TS-12), and "add any you can think of". The developer is invited when RED starts: the TDD skill shows the acceptance scenarios and asks in one line. QE is invited at test review. One invitation per role per change, brief under FR-29 comms, never a prompt that waits for an answer. Adding is optional for the developer and QE and declining leaves no record; the PM review record is TS-3. HITL does not nag: a second reminder for the same role on the same change is a defect. | Must | 2 |
| **TS-12** | **A shared page per change for people who are not in a Claude Code session.** On request from the person running the step, or when the team's preference says so, HITL publishes the scenarios file as a private page and gives the link to share with the team. On the page a reviewer reads the context and the scenarios, comments on one, adds a scenario in their own words, or edits one, with their name on it. HITL pulls what people did on the page back into the file: new scenarios get the next ID, edits are applied, comments that ask a question become a question for the PM, everything is marked with who did it, and the page is regenerated from the file so both say the same thing. Until pulled, a page change is pending and the page shows it as pending; the file is the only record the check reads. One page per change; the page says which change and which version of the file it shows. Publishing is the act of the person running the step, never HITL's on its own, and the same consent rule as the per-change block applies: nothing is published on anyone's behalf. The page runtime is the host's (the claude.ai page capabilities available to the session), not something HITL ships, and there is no such route on the Codex side. When that runtime cannot collect edits or comments, the page is read-only and says so, and the chat route (TS-10) and the file remain. | Should | 2 |

## 6. Rules the design must keep

- Nothing in this feature makes a developer wait to start coding. Teams that want to get to RED
  resent a review queue in front of it, and a review people resent gets rubber-stamped. The PM
  review runs alongside the build; the two-way check, not a gate, is what keeps a late PM addition
  from being lost. Waiting is an opt-in preference, never the default.
- The acceptance criteria in the PRD stay the source of truth. Scenarios elaborate them and link to
  them; they never replace or contradict them. A scenario with no criterion behind it is a question
  for the PM, not a new requirement.
- The file is QA-owned. The PM edits it during review; the developer adds `added-by: dev` scenarios;
  QA decides what is deferred and why.
- No parsing of the scenarios to produce code. The link is the ID, read by a checker, not a grammar
  read by a runner.
- A missing or orphaned scenario is a recorded gap, never a silent one. A deferral and a skipped
  review use the skip-record field dialect (who, why, when, deferred or declined) in the change
  record. They are not FR-29 step skips: the review is not a catalog step and the First Pass
  checker would reject the key.
- Everything HITL writes into the file follows `ai/shared/plain-english.md`.
- A page is a view of the file, regenerated from it. A change made on the page is in the record
  only once HITL has pulled it into the file with an ID and a name. There is one page per change
  and no page across changes; that would be a dashboard, which HITL does not ship.
- Chat is the input, the file is the record. A scenario someone says to HITL exists only once it is in
  the file with an ID. Nothing lives in chat alone, which is the defect this feature fixes.
- The way to get people to review is a short file and a one-sentence way to add to it, not a
  reminder. If people are not adding scenarios, shorten the file before adding a prompt.

## 7. Not doing

- Gherkin, Cucumber, pytest-bdd, playwright-bdd or any step-definition layer. If a team later wants
  executable E2E scenarios, playwright-bdd can be added to the E2E layer alone without touching this.
- A test management product, a manual test execution log, or a dashboard. The TS-12 page is one
  change's file rendered for review, not a place to browse tests across changes, and it is not
  where results live.
- Back-filling scenarios for changes that shipped before this feature.
- Scenarios for native mobile frameworks; the existing note in `qa-plan-tests` stands.

## 8. How we know it worked

| Measure | Target |
|---|---|
| Changes approved at QA verify with no scenarios file | Zero. The TS-4 validator fails on a missing file at test review and again at QA verify, which Fast Track cannot skip. |
| Acceptance or integration tests citing no scenario | Zero at QA approval. |
| Scenarios with neither a test nor a recorded reason | Zero at QA approval. |
| PM-added scenarios | At least one in the first three changes a PM reviews during user testing. Evidence, not proof. |
| Readability | A reader with no access to the code can say what each scenario checks and which criterion it serves, with nothing else open. Checked by the plain-English lint on the file plus one reviewer's read. |
| Length | A change with five acceptance criteria fits on two pages. The lint flags longer files. |
| Developer- or QE-added scenarios | At least one in the first five changes during user testing. Evidence, not proof. |
| Scenarios added by chat or on the page rather than by editing the file | Most of them. If people edit the file by hand instead, the chat and page routes are too clumsy. |
| Page and file disagree after a pull | Never. The page shows the file version it was built from; a reviewer comparing the two finds no difference. |

## 9. Version

| Version | Date | Change |
|---|---|---|
| draft v1.4 | 2026-10-04 | After the validation review (section 11): scenario IDs are `SC-`, not `TS-`; a skipped PM review uses the skip-record dialect in the change record and is not an FR-29 step skip; the validator runs at test review and at QA verify; TS-5 moved to slice 3 beside TS-4; the change record is authoritative for review state; the per-change block is "when #112 ships"; TS-6 and TS-8 made checkable; TS-12 names the host runtime. |
| draft v1.3 | 2026-10-04 | Owner: also offer a shared page to review, add and update scenarios together. New TS-12 (a private page per change published from the file on request, people comment, add and edit with their name on it, HITL pulls changes back into the file, the file stays the record, read-only fallback when the runtime cannot collect). TS-10 and TS-11 reference it. Scope, section 6, section 7 and section 8 updated. |
| draft v1.2 | 2026-10-04 | Owner: the file must be readable with enough context, concise, and PM, developers and QE should be drawn to review and add by chatting with HITL. TS-8 rewritten (context once at the top, each scenario stands alone, two-page ceiling with a lint row). New TS-10 (add or change a scenario by chat, from any role) and TS-11 (one invitation per role, never a block, never a nag). TS-6 names who added a scenario. Goal 5, two section 6 rules, three section 8 measures. |
| draft v1.1 | 2026-10-04 | TS-3 reworked after the owner noted that some teams hate being blocked on reviewing test cases before they can code: the PM review is asynchronous by default with a deadline (before QA verify closes) instead of a gate before RED; waiting is an opt-in preference. New rule in section 6. |
| draft v1 | 2026-10-04 | First draft from the discussion on 2026-10-03 and 2026-10-04. Two choices settled by the owner: the file is QA-owned under the engineering testing directory and the PM reviews from there; plain markdown with IDs, not Gherkin. Not reviewed. |

## 10. Where to look

- `ai/claude/qa/plan-tests/SKILL.md`, steps 4 and 5: writes Given/When/Then today, persists only names
- `ai/claude/qa/review-tests/SKILL.md`: the gate this feature's validator joins
- `ai/claude/tdd/SKILL.md`, Phase 2: the human review that gains a cited-ID rule
- `ai/claude/qa/verify-quality/SKILL.md`: per-test pass/fail today, per-scenario under TS-6
- `ai/shared/templates/test-strategy-template.md`: the manual test case table whose fields TS-1 reuses
- `ai/shared/templates/test-registry-template.yaml`: the index that gains a `scenarios` list
- `ai/shared/skip-record.md` and `docs/01-product/first-pass/requirements.md`: the deferral record TS-3 and TS-4 reuse
- `ci/first-pass/check_skips.py`: the fail-closed validator pattern TS-4 follows

## 11. Review history

| Date | Reviewer | Verdict | What changed |
|---|---|---|---|
| 2026-10-04 | One clean-context validation agent, nine-point checklist, 13 tool calls | Proceed with changes, nothing blocking | Five should-fix and six notes, all applied in v1.4. Verified correct: the section 1 claims about the four skills and two templates, the catalog keys, the FR-29 comms fit, every path in section 10, the PRD row, slice coverage, no remaining gate before RED. |
