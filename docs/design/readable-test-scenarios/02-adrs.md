# Readable Test Scenarios: Decisions (ADRs)

> Status: **draft v1 (2026-10-04)**. Decisions for FR-36. Each is one paragraph: the choice, the
> alternative we did not take, and why. Context in [`01-design.md`](01-design.md), mechanics in
> [`03-lld.md`](03-lld.md).

## ADR-1. Markdown with a fixed field list, parsed by headings

One `### SC-<change>-<nn>: <title>` heading per scenario, followed by a short `- Field: value` list.
Not Gherkin (settled in the requirements), and not YAML front matter per scenario either: a PM edits
a bulleted list without breaking it, and a validator parses headings and `- Key: value` lines with
one regex each. The cost is that a free-form edit can break parsing; the validator reports that as
MALFORMED with the line number, which is the same contract the First Pass checker has.

## ADR-2. IDs are `SC-<change-id>-<nn>`, cited as a token in test text

`SC` for scenario. `TS-` is the requirements document's own prefix and `TC-` is the strategy
template's test-case prefix, so either would collide. The change id is the repo's own form (`GH-123`,
`SVC-3`). A test cites a scenario when the ID appears, with hyphens or underscores and in any case,
in the test's name, docstring or body. No AST, no per-language plugin: a regex over test text works
for Python, TypeScript, Go and Java today and for the next language tomorrow. The alternative, a
registry row per test with a `scenarios` list as the only link, was rejected as the sole mechanism
because registries drift; it is kept as a second index (TS-7), not the proof.

## ADR-3. The change record is authoritative for review state; the file shows it for the reader

`tests.scenario_review` in `.hitl/current-change.yaml` holds `pending`, `done` or `skipped` with the
fields in the LLD. The file header carries a `Review` line that HITL rewrites from the record so the
PM sees the state where they read. The validator reads the record and, when the header disagrees,
reports REVIEW_HEADER_STALE as a warning and fixes nothing. One source, one mirror, no merge logic.

## ADR-4. No new catalog step; the review is a window, not a step

Adding a step to the development workflow renumbers every open change, changes the breadcrumb
matrix and the command map, and would make the review a thing to skip. The review lives between
`test_plan` and `qa_verify`. A skipped review therefore uses the skip-record field dialect (`actor`,
`reason`, `ts`, `disposition`) inside `tests.scenario_review`, not an entry in `skips[]`, which the
First Pass checker keys on catalog steps and would reject. `check_skips.py` is untouched.

## ADR-5. The opt-in gate is one key in `.hitl/config.yaml`

`scenario_review_gate: true` makes `dev-tdd` refuse to start RED while the review is `pending`.
Default absent, meaning false. Not a `dev-preferences` setting, because that block is about how HITL
talks and is per person in `CLAUDE.md`; this is a team rule about the process and belongs with
`change_id_prefix` and the other team settings.

## ADR-6. One skill, `qa-scenarios`, for add, review, publish and pull

Four verbs in one skill so there is one thing to learn and one place the file is edited by
conversation. It lives under `ai/claude/qa/` because QA owns the file and the plugin build maps that
directory to `/hitl:qa-scenarios` without a build-script change; any role runs it, as any role runs
`ta-approve`. Spreading the behaviour across `pm-*`, `dev-tdd` and `qa-*` would have put the same
editing logic in four files.

## ADR-7. The validator runs twice: at test review and at QA verify

`test_review` is a ceremony step Fast Track may skip; `qa_verify` is a hard gate. Running at both
makes TS-4 hold on every path. At `review` a pending PM review is a warning, at `verify` it is a
blocker unless recorded skipped. Same script, one `--stage` flag.

## ADR-8. Fast Track: the TDD skill writes the file from the tests

When there is no file at RED, `dev-tdd` derives one scenario per acceptance or integration test it
generated, `Added by: dev`, and records the review as skipped with the developer as actor and the
reason "test plan step skipped". The alternative, exempting Fast Track changes from the file, would
leave the PM nothing to read for exactly the changes that got the least review.

## ADR-9. The page is a rendering of the file, pulled, never merged

`qa-scenarios publish` builds a page from the file; `qa-scenarios pull` turns page comments and
submitted rows into file edits and republishes. The file never reads from the page without a person
running pull, and a page row is nothing to the validator until pulled. Two-way live sync was
rejected: it needs a service HITL does not ship and would make the page a second record. The page
runtime is the host's (the Artifact tool and its capabilities in the session); when absent or unable
to collect, the skill says so and publishes read-only or not at all.

## ADR-10. Ship and sync the validator exactly like First Pass

`ci/test-scenarios/check_scenarios.py` goes to product repos through the same five places as
`ci/first-pass/`: `init-project.sh`, the two start-* copy blocks, `migrate_project.py` `SYNC_SETS`,
`shipped-validators-hashes.py`, and the plugin repo's `build.sh`. Its dev-repo tests stay out of
product repos through the existing `hitl_copy_tools` filter. A sixth install path would be a new
class of drift.

## ADR-11. Word count is the length unit

The ceilings table speaks in pages; the validator needs a number. One page is 500 words, so the
scenarios file ceiling is 1,000 words of markdown, counted after stripping the table and the
headings. Over the ceiling is a warning (LENGTH), never a blocker, matching "a prompt to trim".
