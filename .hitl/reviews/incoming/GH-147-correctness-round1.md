# GH-147 correctness review, round 1 (2.16.1)

Reviewer: clean-context validation agent, correctness lens. Commit 40a6b56921e3834c206252d6b0890c0db733dd81. Repo not modified apart from this file; temp files under the session scratchpad.

**Verdict: verified with changes.** Every acceptance item in #144, #145 item "refuse a bare number" (at the entry skill) and the #146 items named in the changelog is carried by code or skill text and passes by command. One changelog sentence claims more skills than carry the rule, and one pre-fill sentence contradicts the floor rule two paragraphs below it on who acknowledges.

## Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Gates | pass | `python3 -m pytest ci/ tools/ -q`: 1319 passed in 80s. `check_skills.py`: 65/65 files pass, 0 failures, 0 warnings. `derive.py verify`: VERIFY OK for all eight workflows. |
| 2a | #144 fake host | pass | `test_chk11` asserts qa passes, staging exits 2, and a `deploy` step `done` with no environment prints "deploy step done but no environment recorded" and exits 2. `test_chk12` deletes the branch, routes the merged PR to `merge_commit_sha: feedface0000`, reads the record at that ref and asserts `record=merged@feedfac`. `python3 -m pytest ci/linked -q`: 38 passed. |
| 2b | #144 real host | pass | Temp change file with provider `Prasad-Apparaju/hitl-dev-platform` `GH-60`, `need provider-deployed --env prod` printed `provider GH-60 ... issue=closed record=implementation-approved@8d45f0f approved=yes merged=yes deployed=[]` then `waiting on: ... GH-60 is not deployed to prod (no deployment recorded)`, exit 2. No `issue/60-` branch exists on the host (0 matches). `git log -1 8d45f0f` is "Merge pull request #64 from Prasad-Apparaju/issue/60-wrapper-drift" with two parents, so the record was read at the merge commit. The GH-60 record has no `deploy` step, so "no deployment recorded" is the right branch of the wording (linked.py:344). |
| 2c | ops-deploy writes `deployments:` | pass | `ai/claude/ops/deploy/SKILL.md:131` adds `deployments:` as an appended list under Step 4; line 135 says a CI deploy that never runs the skill "must append the same line to the record, or post the comment below, or the consumer waits". |
| 2d | schema lists `deployments` | pass | `ai/shared/templates/change-context.schema.yaml:448`, `type: list[object]`, item fields follow, description names #144 and the consumer read. |
| 3 | #146 item 2 approver | pass | `test_neg12` passes (stranger ignored, permission read failure ignored, maintainer approves). `linked.py:192-201`: `_approver` returns False on no login, on `HostError` from the permission read, and when `permission` is not in `APPROVER_PERMISSIONS = ("admin", "maintain", "write")` (line 39), so `read` is ignored. Ignored markers are counted at line 212 and shown by `fmt` at lines 299-300 as `ignored-markers=N(not from a writer)`. |
| 4 | #146 item 4, #145 | pass | `grep -rn '#GH-}' ai/claude`: none. `ta-approve/SKILL.md:164,213,235` and `hooks/sync-step-to-issue.sh:52` use `sed -n 's/.*[^0-9]\([0-9][0-9]*\)$/\1/p'`; run on SVC-3, GH-12, EMAIL-14, nodigits gives 3, 12, 14, empty. No `GH-` guard remains in either file. `resolve DOCS-7` prints `-R org/docs 7` (exit 0), `resolve SVC-3` prints `3`, `resolve 7` prints "ambiguous: a bare number; use <PREFIX>-7" (exit 2). `start-change/SKILL.md:47` refuses a bare number with a prefix configured and names the form ("Use SVC-3, or DOCS-3 for the docs repository"). All four argument hints mention a change id (start-change, apply-change, tdd, switch-context line 3). |
| 5 | #146 items 1 and 6 | pass | `tdd/SKILL.md:53`: passes without a local file when `skips:` has `step: packet` or `workflow.steps[]` shows `packet` as `skipped`/`not_applicable`, or when the value is a pinned `owner/repo@<commit>:<path>` fetched with `linked.py fetch`. `apply-change/SKILL.md:49` says the same for both cases. |
| 6 | #146 item 11 | pass with a note | `start-change/SKILL.md:284`: with `reaches_production: false`, deploy and promote are offered under Leave out as `decline`, reason "does not reach production (impact record)", `ack_by` the person confirming the plan. `test_check_skips.py:65-66` asserts `resolve_crit(CATALOG["deploy"])` is `floor` at tiers 0 and 3; the catalog entry (`catalog.yaml:74`) carries `crit: floor` and no `cond`. The changelog says "a floor step is still never dropped by a rule alone"; `check_skips.py:578-587` still refuses a floor skip with no `ack_by`. See finding 2. |
| 7 | Bold claims carried | pass with a note | The one bold claim is the heading "Linked changes, from the first two-repo run"; its sentences map to linked.py:192-212 and 248-283 and 344, ops/deploy/SKILL.md:131-135, ta-approve:164, sync-step-to-issue.sh:52, start-change:47 and :284, tdd:53, apply-change:49, linked.py `resolve`. See finding 1 for the one sentence that outruns its carriers. |
| 8 | Plain English | pass | `pytest ci/wiring/test_plain_english.py -q`: 16 passed. Em dash count: `docs/linked-changes.md` 0, `ai/shared/linked-changes.md` 0. |

## Findings

**Stops:** none.

**Decide**

1. The changelog sentence "Skills take `<PREFIX>-<n>`, refuse a bare number when a prefix is configured" is carried only by `ai/claude/start-change/SKILL.md:47` and, for acceptance without a refusal, `ai/claude/switch-context/SKILL.md:49`. `ai/claude/apply-change/SKILL.md` got the argument hint but its body still says "issue number" at lines 25 and 45 and never mentions the prefix, the refusal, or `linked.py resolve`; `ai/claude/tdd/SKILL.md` likewise has only the hint (lines 25-27 say "LLD or issue"). #145 asks for "skills that take an issue or change". Either narrow the sentence to start-change and switch-context, or add the one-line rule from start-change:47 to apply-change Step 2 and tdd's input paragraph. Not a stop: start-change is the entry point where the number is first bound.

**Minor**

2. `ai/claude/start-change/SKILL.md:284` pre-fills `ack_by` as "the person confirming the plan", while rule 1 at line 330 in the same skill says a floor skip "requires the accountable role's risk-accepted `ack_by`". Deploy and promote are Ops-role floor steps, so the two sentences disagree on who may acknowledge. The validator only requires a named person (`check_skips.py:537-538`, 587), so the changelog claim holds mechanically, but the skill text should say which rule wins (for example, "the confirming person, who accepts the risk on Ops's behalf for a change that does not reach production").

3. `ai/claude/ops/deploy/SKILL.md:140` posts the Deployed comment to `<issue-number>` with no derivation line, unlike ta-approve and the hook. Harmless now that the record is the primary signal, but a one-line pointer to "the digits at the end of the change id" would make the changelog's "every place" literally true.
