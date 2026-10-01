# GH-105 slice 0 (linked changes), round 2, correctness

Reviewer: clean-context validation agent (Fable 5.1). Commit 6bb5e6e, branch issue/105-multi-repo-design, 2026-10-01.
Scope: re-verify the seven round-1 findings (report `.hitl/reviews/incoming/GH-105-slice0-round1-correctness.md`, reviewed 8be4d97) on the real host and in the suite, then the full suite, the skill lint and the diff between the two commits. Nothing in the repo was modified; temp change files and fetch output under the session scratchpad.

**Verdict: verified.** Both stops and all three decide items are fixed and demonstrated on the real host; the suite is green (1313 passed) and the skill lint passes. One half of M1 (the PFX-2 tag on the Team Pulse test) was not applied. Two new items, both decide/minor: a merged partner PR is invisible to the "merged PR" criterion once its branch is deleted and its title names the issue as `#60` rather than `GH-60` (fail-closed, but it is this repository's own PR convention), and a dead line in GATE-6.

## Round-1 findings

**S1. "The PR search approves partners it should not."** Fixed. Real host, docs partner `GH-14` on `Prasad-Apparaju/hitl-dev-platform`: `state` prints `issue=closed record=none (no issue/14- branch) approved=no merged=no`, exit 0; `need docs-approved` adds `waiting on: ... GH-14 is not approved (no record: no issue/14- branch, no approval comment, no merged PR)`, exit 2. `ci/linked/linked.py:50` `mentions` is a whole-word match with alphanumeric guards (GH-14 does not match GH-142 or GH-14a, test `test_mentions_is_a_whole_word_match`); the search loop at line 198 keeps a hit only when the id is a whole word in its title or body, and issue-branch PRs come from the `pulls?head=` read at line 191. `ci/preflight/check_change.py:111` `_partner_pr_files` keeps a hit only when the pull's head ref starts with `issue/<n>-` or the id is a whole word in the search item's or pull's title or body. NEG-10 (`test_neg10_...`) and GATE-6 cover the unrelated merged PR. `python3 -m pytest ci/linked ci/preflight -q`: 53 passed.

**S2. "Suite is red."** Fixed. `python3 -m pytest ci/wiring -q -k plugin_root`: 3 passed. `ai/claude/start-change/SKILL.md:91-92` now carry `PREFIX=...` and `CHANGE_ID="${PREFIX}-${N}"` on their own lines with no trailing comment. In the rebuilt plugin (`../hitl-claude-plugin`, working tree rebuilt on top of 057b25a, uncommitted) `skills/dev-start-change/SKILL.md` lines 91-92 match the source; the only `${CLAUDE_PLUGIN_ROOT}/shared` occurrences outside a `${CLAUDE_PLUGIN_ROOT:-` fallback are lines 422 and 475, both prose outside any fence (fence parity checked), so no shipped bash block depends on an unset plugin root.

**D1. "A partner issue that does not exist reads as 'host unreadable'."** Fixed. `gh api repos/pappar/hitl-claude-plugin/issues/36` is a 404 (gh exit 1). `need provider-deployed --env prod` on that partner prints `not found: pappar/hitl-claude-plugin has no issue 36 (the link names a wrong change id or issue)`, exit 2. `linked.py:173` probes `repos/<R>` after a failed issue read: repo readable means `NotFound` (exit 2), otherwise `HostError` (exit 3); `test_d1_...` covers both branches.

**D2. "The gate reads a partner packet at the default branch when the PR read fails."** Fixed. `check_change.py:100` returns `([], "could not read R#n (gh exit k)")` on a failed pull read and `:104` on an unparseable one; nothing is fetched afterwards, so `_partner_file` is never reached with `HEAD`. A missing head sha is also an error (`:114`). `test_gate6_...` asserts the failed pull read yields a failed check whose message names `could not read org/docs#7`.

**D3. "A closed partner with no approval shows as 'record status unreadable'."** Fixed. Real host, docs partners `GH-142` and `GH-131`: the state lines read `issue=closed record=none (no issue/142- branch) approved=no merged=no` and `issue=open record=none (no issue/131- branch) ...`; the waiting line says `no record: no issue/142- branch, no approval comment, no merged PR`. Exit 2 from `need`, 0 from `state`.

**M1. "PFX-1 and PFX-2 carry no test ID."** Half fixed. `ci/linked/test_linked.py:318` `test_pfx1_a_prefixed_change_id_still_yields_its_issue_number` runs `gen_change.py --stub SCM-12` and `hitl_branch_reconcile` (asserts `match`, `mismatch`); 1 passed. `tools/team-pulse/test_pulse.py` is untouched by 6bb5e6e (last change 8be4d97): `test_change_id_prefix_falls_back_to_the_repository_setting` at line 270 still carries no `PFX-2` tag in its name or docstring. Still open (minor).

**M2. "`REF_RE` accepts uppercase hex and lowercases it; LLD §4 says `[0-9a-f]`."** Fixed. `linked.py:36` is `[0-9a-f]{7,40}`, identical to `docs/design/multi-repo-workspace/03-lld.md:76`. Real host: `fetch Prasad-Apparaju/hitl-dev-platform@ABCDEF1:docs/linked-changes.md --out-dir <tmp>` prints `refused: a pinned reference is owner/repo@<commit sha>:<path>; a branch name is not a pin`, exit 2, nothing written. `test_m2_...` covers it.

## Checks

- pass: `python3 -m pytest ci/ tools/ -q` at 6bb5e6e, 1313 passed in 81s.
- pass: `python3 ci/skill-lint/check_skills.py`, 65/65 files pass, 0 failures, 0 warnings.
- pass: `python3 -m pytest ci/linked ci/preflight -q`, 53 passed; `python3 -m pytest ci/wiring -q -k plugin_root`, 3 passed.
- pass: `git diff --stat 8be4d97 6bb5e6e`, 8 files: the two readers and their tests (S1, D1, D2, D3, M2, PFX-1), `start-change` (S2), the two hash manifests (new `linked.py` and `test_linked.py` digests), and the implementation plan (phases A to E marked done). Nothing outside the round-1 scope. The working tree also carries an uncommitted edit to `05-implementation-plan.md` adding the round-1 row to the review table, plus the unrelated `.claude/settings.json` and `HITL Step Picker.pdf` entries.
- pass: real-host runs for S1, D1, D3, M2 as recorded above; all `gh` calls were reads.

## New findings

**N1 (decide). A merged partner PR is invisible once its branch is deleted unless its title or body says `GH-<n>`.** Real host, docs partner `GH-60`: PR #64 merged from `issue/60-wrapper-drift` on 2026-08, branch since deleted, title `fix(onboarding): init-project.sh emitted pre-#14 wrappers ...`. `state` prints `issue=closed record=none (no issue/60- branch) approved=no merged=no`; `search/issues?q=repo:R+is:pr+GH-60` returns zero items, so neither reader can see it (the gate's head-ref check never gets a hit to inspect). Of this repository's merged PRs on `issue/<n>-` branches (5 in the last 80 merged), none names the issue as `GH-<n>` and all use `#<n>`; three of the five branches are deleted. `ai/shared/team-pulse.md:76` states the prefix convention as `GH-12`, `issue/12-`, `#12`, so `#60` is a form HITL itself documents. Fail-closed (a false "not approved", never a false pass), so not a stop. Smallest fix: also search `is:pr+%23<n>` (or `#<n>` in the whole-word match, guarded so `#60` does not match `#601`), or query the host for closed pulls by `head:issue/<n>-`; add a NEG case with a merged PR whose branch is gone and whose title says `#60`. Alternatively state in `docs/linked-changes.md` that a partner's PR must name the change id or keep its branch.

**N2 (minor). GATE-6 has a dead line.** `ci/preflight/test_check_change_linked.py:118` sets a `Host(fail=("repos/org/docs/pulls/7\n",))` that line 126 immediately replaces with `failing_pull`; the trailing newline in the `fail` key would not have matched anyway. Harmless; delete the line.

No third finding.
