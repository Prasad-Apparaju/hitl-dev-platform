# GH-105 slice 0 (linked changes), round 1, correctness

Reviewer: clean-context validation agent (Fable 5.1). Commit 8be4d97, branch issue/105-multi-repo-design, 2026-10-01.
Checklist: the eight items from the issue's 2026-10-01 comment. Nothing in the repo was modified; scratch files under the session scratchpad.

**Verdict: not verified.** One fail-open in the central check (an unrelated merged PR approves a docs partner) and one red test in the suite. Everything else on the list holds.

## Findings

### Stops

**S1. The PR search approves partners it should not.** Check: item 2 on the real host. Claim (LLD §3.1): approved = record status, else a marker comment, else "a merged PR". Evidence: `linked.py` and `check_change.py` both find a partner's PRs with `search/issues?q=repo:R+is:pr+<change_id>`, and GitHub matches that loosely. For a docs partner `GH-14` on this repo (issue 14 closed, zero marker comments, no `issue/14-` branch) the checker printed `approved=yes merged=yes` and `satisfied: docs-approved`, exit 0. The matched PR is #57, head `issue/56-first-pass-wiring`, whose title and body contain no `GH-` id at all. The same search feeds the gate's partner file list, so a decision packet in an unrelated PR would satisfy `decision-packet` and `lld-adr-update`. Smallest fix: after the search, keep only items whose head branch starts with `issue/<n>-` or whose title or body contains the change id as a whole word (`\bGH-14\b`); apply the same filter in `_partner_pr_files`. Add a NEG case: a merged PR for another issue in the same repo must not approve or merge the partner.

**S2. Suite is red.** Check: item 1, `python3 -m pytest ci/ tools/ -q`: 1306 passed, 1 failed. `test_no_shipped_bash_block_depends_on_an_unset_plugin_root` flags the built `dev-start-change` Step 3 fence: the trailing comment `# shared/linked-changes.md` on the `CHANGE_ID` line (`ai/claude/start-change/SKILL.md:91`) is rewritten by the plugin build to `${CLAUDE_PLUGIN_ROOT}/shared/...`, and the guard only skips comment-only lines. Harmless at runtime (it is a comment) but the release gate will not pass. Smallest fix: drop the trailing comment or put it on its own line.

### Decide

**D1. A partner issue that does not exist reads as "host unreadable".** Item 3: plugin `GH-36` is a 404 on `pappar/hitl-claude-plugin`; the checker printed `host unreadable: gh api repos/pappar/hitl-claude-plugin/issues/36 failed (exit 1)`, exit 3. It blocks, which is right, but the cause named is wrong: nothing is unreadable, the partner is mistyped. Decide whether a 404 on the issue itself should be exit 2 with "issue 36 not found".

**D2. The gate reads a partner packet at the default branch when the PR read fails.** Item 6: in `_partner_pr_files`, a failed `repos/R/pulls/<n>` read sets `head=""` and continues, so `_partner_file` then fetches `docs/decisions/issue-<n>.yaml` at `HEAD`. A pass is still backed by a real, complete packet, so a host failure alone never passes, but it is not "fetched by ref" as LLD §5 says and can validate a different revision than the PR carries. Smallest fix: return an error when the pull read fails, as the files read already does.

**D3. A closed partner with no approval shows as "record status unreadable".** Item 2: `GH-142` (closed, released, branch deleted, one comment, no marker) and `GH-131` (open epic, two comments, no marker) both print `approved=no`, exit 2, which follows LLD §3.1: closure is not approval. But the verdict line says `record status unreadable` when there is simply no `issue/142-` branch, and the text line never shows the issue is closed (only `--json` does). Decide: say `no record (no issue/142- branch)` and add `issue=closed` to the line so the person knows the partner is finished, not pending.

### Minor

**M1. PFX-1 and PFX-2 carry no test ID.** Item 8: PFX-2 is covered by content in `tools/team-pulse/test_pulse.py::test_change_id_prefix_falls_back_to_the_repository_setting`; PFX-1's wiring half is in WIRE-2's assertions, but `gen_change.py --stub SCM-12` and `hitl_branch_reconcile` against `SCM-12` have no test (both pass by hand). Add the two assertions and tag the pulse test.

**M2. `REF_RE` accepts uppercase hex and lowercases it; LLD §4 says `[0-9a-f]`.** Harmless; align the LLD or the regex.

## Checklist

1. **fail (suite red, rest holds):** `python3 -m pytest ci/ tools/ -q` 1306 passed, 1 failed (S2); skill lint 65/65 pass; `grep -i linked ai/shared/workflows.yaml` empty and the file is untouched by 8be4d97; `need docs-approved` and `state` on a file with no `linked_changes` print `no linked changes`, exit 0, with a stub `gh` on PATH that was never called (also for a missing change file); `test_chk3_...` asserts `h.calls == []`.
2. **fail (S1):** `GH-142` and `GH-131` as docs partners: `state` exit 0, `need docs-approved` exit 2, verdict names the partner, per LLD §3.1; `GH-14` passes with no approval anywhere. tdd: the linked rule at `ai/claude/tdd/SKILL.md:41` runs before the no-LLD rule at line 50 and the fence comment says exit 3 is "the host could not be read: stop, say which read failed".
3. **pass (D1 noted):** `GH-36` 404 exit 3; real issues `GH-40` (open) and `GH-37` (closed) give `has no merged PR`, exit 2. `ops/deploy` Step 1 item 4 runs `need provider-deployed --env <environment>` and says stop on 2 or 3. Provider deployment is better protected than approval because `deployed` only comes from the exact `## 🚀 Deployed to` marker.
4. **pass:** `fetch Prasad-Apparaju/hitl-dev-platform@de692d0:docs/design/data-layer/03-lld.md --out-dir <tmp>` lands at `<tmp>/Prasad-Apparaju/hitl-dev-platform/de692d0/docs/design/data-layer/03-lld.md`, byte-identical to `git show de692d0:...` (cmp); `@main` and `@release/2.x` refused, exit 2, stub `gh` never called; tdd line 48, apply-change line 51, review-lld-adherence line 35 all name `owner/repo@<commit>:<path>` and say cite the reference, not the path.
5. **pass:** start-change line 91 forms `CHANGE_ID="${PREFIX}-${N}"` from `change_id_prefix` with default GH; `hitl_branch_reconcile` on `change_id: "SCM-12"` with a `workflow.steps` block and `issue/12-x` prints `match` (and `mismatch` for `issue/13-x`); `gen_change.py --stub SCM-12 issue/12-x 2.15.0` writes `change_id: "SCM-12"`; `pytest tools/team-pulse -q -k prefix` 1 passed; retro Step 3b appends `## Linked changes` from `linked.py state`.
6. **pass (D2 noted):** `pytest ci/preflight -q` 19 passed; every `GH_RUN` non-zero exit, missing `gh` (127), unparseable body or missing file returns a failed CheckResult; no partner declared returns None and the local checks run unchanged.
7. **pass (wording in D1, D3):** an em-dash grep on `docs/linked-changes.md` and `ai/shared/linked-changes.md` finds none; `waiting on: ... is not approved (record status ..., no approval comment, no merged PR)` and `refused: a pinned reference is owner/repo@<commit sha>:<path>; a branch name is not a pin` read as a colleague would say them.
8. **pass (M1):** NEG-1..9, CHK-1..10 in `ci/linked/test_linked.py`; GATE-1..5 in `ci/preflight/test_check_change_linked.py`; FIL-1, WIRE-1..5 in `ci/wiring/test_wiring.py`; PFX-1 and PFX-2 uncovered by ID (see M1).
