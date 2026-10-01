# 2.16.0 correctness review, round 1

Reviewer: clean-context validation agent (lens: correctness). Repo at 36f85f11d2c2a53cc60dc50b93e852fa60f10d07 ("chore(release): 2.16.0"). Claim list: the `## [2.16.0]` section of CHANGELOG.md. Nothing in the repo was modified; temp records and the `gh` stub lived in the session scratchpad.

**Verdict: verified** (one minor finding, no stops, nothing to decide).

| # | Check | Command | Result | Observed |
|---|-------|---------|--------|----------|
| 1 | Gates | `python3 -m pytest ci/ tools/ -q`; `python3 ci/skill-lint/check_skills.py`; `(cd tools/workflow-catalog && python3 derive.py verify)` | pass | `1314 passed in 80.42s`; `Skill lint: 65/65 files pass all hard gates; 0 failures, 0 warnings`; `VERIFY OK: numberless catalog reproduces runtime for spine->development, ...` |
| 2a | No `linked_changes`, `gh` stubbed (PATH stub exits 99) | `PATH=<stub>:$PATH python3 ci/linked/linked.py need docs-approved --change <tmp>` | pass | `no linked changes`, exit 0, stub never invoked |
| 2b | Docs partner GH-131 / GH-60 | `need docs-approved --change <tmp GH-131>`; `state --change <tmp GH-60>` | pass | GH-131: `waiting on: Prasad-Apparaju/hitl-dev-platform GH-131 is not approved (no record: no issue/131- branch, no approval comment, no merged PR)`, exit 2. GH-60: `docs GH-60 Prasad-Apparaju/hitl-dev-platform issue=closed record=none (no issue/60- branch) approved=yes merged=yes deployed=[]`, exit 0 |
| 2c | Provider GH-36 in pappar/hitl-claude-plugin | `need provider-deployed --env prod --change <tmp>` | pass | `not found: pappar/hitl-claude-plugin has no issue 36 (the link names a wrong change id or issue)`, exit 2 |
| 2d | Pinned fetch; branch refused | `fetch Prasad-Apparaju/hitl-dev-platform@de692d0:docs/design/data-layer/03-lld.md --out-dir <tmp>` then `git show de692d0:... \| cmp`; `fetch ...@main:...` with `gh` stubbed | pass | exit 0, `cmp` silent (byte-identical, file lands at `<tmp>/Prasad-Apparaju/hitl-dev-platform/de692d0/docs/design/data-layer/03-lld.md`); `@main`: `refused: a pinned reference is owner/repo@<commit sha>:<path>; a branch name is not a pin`, exit 2, stub never invoked |
| 2e | Prefix | `python3 ci/first-pass/gen_change.py --stub SCM-12 issue/12-x 2.16.0`; `pytest tools/team-pulse/test_pulse.py -q -k pfx2`; read ai/claude/start-change/SKILL.md | pass | line 4 `change_id: "SCM-12"`; `1 passed, 13 deselected`; SKILL.md:91 reads `change_id_prefix` from `.hitl/config.yaml` (default `GH`), :92 `CHANGE_ID="${PREFIX}-${N}"`, :382 same |
| 2+ | Exit 3 path (extra) | `PATH=<stub>:$PATH ... need docs-approved --change <tmp GH-131>` | pass | `host unreadable: gh api repos/Prasad-Apparaju/hitl-dev-platform/issues/131 failed (exit 99)`, exit 3 |
| 3 | Carriers for the changelog claims | grep + read | pass, one count off (F1) | see carrier table below |
| 4 | Skill wiring | `python3 -m pytest ci/wiring -q -k linked`; read three SKILL.md | pass | `5 passed, 427 deselected`; tdd/SKILL.md:45 `need docs-approved ... 3 the host could not be read: stop, say which read failed`; ops/deploy/SKILL.md:83 `need provider-deployed --env <environment> # 2: quote the waiting line and stop; 3: the host could not be read, stop`; apply-change/SKILL.md:51 `stop on exit 2 (quote its verdict line) or exit 3 (the host could not be read; say which read failed)` |
| 5 | Gate fail-closed | `python3 -m pytest ci/preflight -q`; read check_change.py:81-131 (`_partner_pr_files`), :454-471 (`_check_packet_in_partner`), :487-492 (`check_lld_adr_for_api`) | pass | `20 passed`. No host failure path returns a passing check: every non-zero `gh` exit, JSON decode error, or missing head sha in `_partner_pr_files` returns `(files=[], err)`; both callers turn `err` into `CheckResult(..., False, ...)`; `_partner_file` returns None on `gh` failure or missing yaml and the caller fails the check (:467). An empty PR list (host OK) falls through to `No decision packet in this changeset or in the linked docs partner(s)`, False. `_docs_partners` (:60-76) drops a `docs` entry with no trailing issue digits, which removes the partner rather than passing it; linked.py is the strict reader and reports `MALFORMED` exit 2 for a bad record. `gh api --paginate --slurp` is supported by the installed gh 2.83.1 |
| 6 | PRD | grep docs/01-product/PRD.md | pass | §5.7 Backlog at :128; :137 FR-30 row links `multi-repo-workspace/requirements.md` (exists, header `draft, v1.1 (2026-09-30)`); :138 FR-31 and :141 FR-35 present; `grep -o '\| FR-[0-9]*' \| sort \| uniq -d` empty |
| 7 | Plain English | `python3 -m pytest ci/wiring/test_plain_english.py -q`; `grep -c '—'` | pass | `16 passed`; em dashes: `ai/shared/linked-changes.md:0`, `docs/linked-changes.md:0` |
| 8 | Getting-started counts | `ls ../hitl-claude-plugin/skills \| wc -l`; `find ai/claude -name SKILL.md \| wc -l`; grep docs/getting-started.md | pass | built 60, source 60, getting-started.md:63 `There are 60 HITL commands`, :74 `The other 54`. Note: ../hitl-claude-plugin is still at `chore(release): build v2.15.0` (plugin.json 2.15.0), so the comparison against the built tree is against the 2.15.0 build; source and build agree at 60, and no skill directory is added or removed in this release |

Carriers for the 2.16.0 claims (verbatim claim fragment, then file:line):

- "each record names its partners in an optional `linked_changes` list (`repo`, `change_id`, `role` of `docs`, `provider`, `consumer` or `code`)": ci/linked/linked.py (strict reader, `--help` text), ai/claude/start-change/SKILL.md:474, ai/shared/linked-changes.md.
- "`ci/linked/linked.py` reads a partner's state from the host through `gh`, never from its code": `--help` text and checks 2a-2d above.
- "`dev-tdd` and `dev-apply-change` refuse while a `docs` partner is unapproved": ai/claude/tdd/SKILL.md:45, ai/claude/apply-change/SKILL.md:51.
- "`ops-deploy` refuses while a `provider` is not merged and deployed to the target environment": ai/claude/ops/deploy/SKILL.md:83.
- "the traceability gate finds the decision packet and the LLD in the docs partner's pull request": ci/preflight/check_change.py:454 (`_check_packet_in_partner`), :487 (`check_lld_adr_for_api` partner branch).
- "a docs change folds its PRD delta when its `code` partners have merged": ai/claude/dev-practices/workflow-steps.md:191 (`need code-merged`, `fold_before_partners`), ai/shared/linked-changes.md:28, pinned by ci/wiring/test_wiring.py:973.
- "An LLD approved in another repository is accepted by pinned reference `owner/repo@<commit>:<path>`": ai/claude/apply-change/SKILL.md:51, check 2d.
- "The change-id prefix is a repository setting (`change_id_prefix` in `.hitl/config.yaml`, default `GH`) and shows in the breadcrumb, Team Pulse and the retro": ai/claude/start-change/SKILL.md:91-92; tools/team-pulse/pulse.py (grep `change_id_prefix`), test_pulse.py pfx2; ai/shared/linked-changes.md:52-53. Breadcrumb and retro show it by construction: both print `change_id` from the record (ai/claude/retro/SKILL.md:42; docs/getting-started.md:129 shows a `BUG-412` breadcrumb).
- "`issues:` names where epics and slices are filed and intake links a slice under its epic as a sub-issue": `issue-repo` calls in ai/claude/pm/add-feature/SKILL.md:103 (epic), ai/claude/conclude/SKILL.md:148 (slice), ai/claude/pm/report-bug/SKILL.md:45 and ai/claude/qa/report-defect/SKILL.md:73 (bug); `link-sub` in ai/claude/start-change/SKILL.md:474.
- "Single-repository projects are unchanged": check 2a (no host call, exit 0); 1314 tests green.
- "Conventions in `shared/linked-changes.md`, user doc `docs/linked-changes.md`, design package `docs/design/multi-repo-workspace/`": all exist (01-design, 02-adrs, 03-lld, 04-test-plan, 05-implementation-plan).
- "40 tests against a fake host plus 7 gate tests": ci/preflight/test_check_change_linked.py collects 7 (holds). ci/linked collects 34, not 40; see F1.

## Findings

**Stops**: none.

**Decide**: none.

**Minor**

- F1. The claim "40 tests against a fake host plus 7 gate tests" does not reproduce as written. `pytest ci/linked --collect-only` reports `34 tests collected`. The number 40 is reached only by adding the 5 `ci/wiring -k linked` tests and the 1 Team Pulse `pfx2` test, which read skill prose and the pulse renderer, not a fake host. Either say "34 tests against a fake host, 6 wiring and Team Pulse tests, plus 7 gate tests" or "40 tests plus 7 gate tests" without the fake-host qualifier. No behaviour is affected.
