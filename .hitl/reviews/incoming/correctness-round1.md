# Correctness review, round 1: HITL 2.13.0 (b5b1bed)

Reviewed in a scratch clone (`git clone --local`, checkout b5b1bed, `git status` empty). Nothing in the tracked tree was modified; the mutation ran in a second scratch clone.

| # | Check | Command | Result | Deciding output |
|---|---|---|---|---|
| 1a | #129 sizer, API change, tier 1, fast | `python3 ci/first-pass/size_plan.py rec.yaml 1 fast` (rec: change_id GH-1, workflow development, surfaces [api], security_sensitive false) | pass | `proposed: [{'step': 'baseline', 'disposition': 'defer', 'reason': 'not required before this ships'}]`; `excluded baseline: []`; outcome `applies: True, needed_now: False` |
| 1b | #129 e2e | `python3 -m pytest ci/first-pass/test_129_api_fast_track_e2e.py -q` | pass | `3 passed`. Read: sizer -> writes outcomes back -> `gen_change.py` -> `check_skips.check()` (library call, not the CLI; equivalent, the CLI exits 2 iff a non-waivable finding exists); asserts no non-waivable findings, baseline `defer`, actor `dev@team`, reason `not required before this ships`. Test 2 is the mutation (old sizer output blocks with `COND_UNCONFIRMED`). |
| 2 | #129 security unchanged | same record, `security_sensitive: true`, tier 1 fast | pass | sec_design / cve_audit / pentest: `in plan: True`, outcome `(applies True, needed_now True)`, `in proposed: False`, `in excluded: False` |
| 3a | #124 unidentified record | change file from `gen_change.py` (tier 2, `first_pass: True`, pentest skip `{not_applicable, actor: x, reason: y}`), record = issue 124's record with no id; `python3 ci/first-pass/check_skips.py .hitl/current-change.yaml` | pass | `[BLOCK] RECORD_UNIDENTIFIED: ... it has no change_id or workflow` exit=2 |
| 3b | #124 contradicted | + `change_id: GH-1`, `workflow: development`, `security_sensitive: true`, `pentest applies: false` | pass | `[BLOCK] RECORD_CONTRADICTED: impact record says step 'pentest' applies: False, but the sizing rules say true` exit=2 |
| 3c | #124 agreeing | `security_sensitive: false`, issue's four-step `rule_outcomes` | pass | exit=0, only `[warn] DEFER_NO_FOLLOWUP` (waivable; from my repro's baseline defer, not the #124 path). `NON_WAIVABLE` set at check_skips.py:70-99 contains both codes. |
| 4a | #130 Step 3c prose | read `ai/claude/start-change/SKILL.md:136-148` | pass | names `skills/dev-apply-change/SKILL.md`, "Steps 2 and 3", "Do not invoke the command"; no call/invoke instruction |
| 4b | #130 wiring test | `python3 -m pytest ci/wiring/test_skill_calls_are_achievable.py -q` | pass | `60 passed` |
| 4c | #130 mutation (scratch clone) | insert "Call `/hitl:dev-apply-change`." under Step 3c, rerun | pass | `AssertionError: ai/claude/start-change/SKILL.md tells the model to call a command it cannot invoke ... line 138: /hitl:dev-apply-change` (two tests fail, both on start-change) |
| 5 | start-change against itself | read 6b:443-475, Step 8:488-499, apply-change Step 3:85-107 | pass | 6b prose "Certify without `--rollup`... appended after the check" matches block (`check_skips.py .hitl/current-change.yaml` then `resurface.py ... --append`). Step 8 "Steps 4 to 8 ... impact analysis already ran at Step 3c" agrees with 3c "Steps 2 and 3". apply-change Step 3 "Do not fold this change's skips into the roll-up here ... decided at intake's Step 4b" agrees with 6b "impact step reads them and does not append". |
| 6 | #114 | read lines 18-34 of the three QA skills; `pytest ci/wiring/test_qa_prd_precondition.py -q` | pass | all three: absent PRD stops (stop clause has no `FR-`); "If the PRD exists but has no `FR-` entries ... do not stop. Say so in one line and continue". `12 passed` |
| 7 | #121 | `grep -rn "ai/claude/ai/claude" ai docs --include=*.md \| grep -v session-logs` | pass | no output (grep exit 1). generate-docs SKILL.md:244-246: "copy skills to `.claude/`", `cp -r ai/claude/ <your-repo>/.claude/` |
| 8 | #116 | `HITL_HOME=$(mktemp -d)`; `release_notice.py state` / `post --version 2.13.0` / `body --version 2.13.0`; `grep -rn "plugin marketplace add" ai/claude/hooks/`; `pytest tools/hitl-onboarding ci/wiring/test_release_notice_wiring.py -q` | pass | state: `ask`, Question 1 and 2 both "(yes / no, default no)". post: `Refusing to post: no recorded yes ... Nothing was sent.` exit=2, home dir empty (`total 0`). body: `H I T L   2 . 1 3 . 0 \n` exactly. hooks grep: no output. `76 passed` |
| 9 | checkbox menu, names | `pytest ci/wiring/test_step4_checkboxes.py ci/wiring/test_product_names.py -q`; read Step 4:149-274 | pass | `48 passed`. Step 4 lists left-out steps "every time", `AskUserQuestion` single-select with `Fast Track (Recommended)`, `Full Scale`, `Pick steps myself` and `preview`; `multiSelect` over every left-out step; "Steps that always stay are never checkboxes." |
| 10 | claim carriers | grep / read | pass with one gap | see below |
| 11 | gates | `pytest ci tools -q`; `ci/skill-lint/check_skills.py`; `derive.py verify` | pass | `1119 passed, 6 skipped`; `63/63 files pass ... 0 failures, 0 warnings`; `VERIFY OK` |

Check 10, one line per bold claim:
- Fast Track / goal-first (#125): `ai/shared/templates/claude-md-hitl-block.md:8`, `ai/claude/hooks/statusline-hitl.sh:99`, `ai/claude/help/SKILL.md:32,198-205`, `docs/getting-started.md:106` (34 steps + 4). Sub-claim "asks for the goal first" (Step 2 vs Step 3 order) not read: unknown.
- Checkboxes: `ai/claude/start-change/SKILL.md` Step 4, `docs/fast-track.md`, `site/fast-track.html`, `ci/wiring/test_step4_checkboxes.py`.
- Release notice (#116): `tools/hitl-onboarding/release_notice.py`, `start-from-prd/SKILL.md:271`, `start-brownfield/SKILL.md:451`, `update/SKILL.md:471`, retro share line `retro/SKILL.md:98`, `ci/wiring/test_release_notice_wiring.py`.
- #129: `ci/first-pass/size_plan.py`, `test_129_api_fast_track_e2e.py`. #124: `ci/first-pass/check_skips.py:70-99, 230-258, 468-492`. #130: start-change Step 3c, `ci/wiring/test_skill_calls_are_achievable.py`. #114: three `ai/claude/qa/*/SKILL.md`, `test_qa_prd_precondition.py`. #121: `generate-docs/SKILL.md:244-246`, `docs/playbook/migration-guide.md:123`, `docs/examples/greenfield/README.md:11`.

## Points

1. **minor**: the #129 e2e test drives `check_skips.check()` as a library, not the `check_skips.py` CLI. The CLI's exit code is derived from the same non-waivable set (`sys.exit(2 if blockers else 0)`), so the assertion is equivalent, but the checklist's "exit 0" is inferred, not observed by the test.
2. **minor**: with a record carrying only a `pentest` outcome, a tier-2 Fast Track change file blocks on `COND_UNCONFIRMED` for `sec_design` and `cve_audit` before reaching "clean". That is the gate working as designed; the checklist's "three-line record" needs the issue's full four-step `rule_outcomes` to reach exit 0.
3. **minor**: changelog sub-claim "`dev-start-change` asks for the goal first" (#125) was not verified; Step 2 is titled "Choose the issue (insist)" and I did not read its body.

Everything on the checklist that was run passed. No finding stops it working.

VERIFIED
