# Verification review: release 2.11.0, lens correctness, round 1

Reviewed: 0dd84c9a807d4eb0798e2c64b597c8594b830db0 (HEAD). Clean context, checklist run. No tracked files modified. Scratch records under `scratchpad/vr-rel-correctness/`.

## Checks

| # | Check | Command | Result | Deciding output |
|---|-------|---------|--------|-----------------|
| 1 | Test suite | `python3 -m pytest ci/ tools/ -q \| tail -1` | pass | `881 passed, 1 skipped in 57.23s` |
| 2 | Skill lint | `python3 ci/skill-lint/check_skills.py \| grep 'Skill lint'` | pass | `Skill lint: 63/63 files pass all hard gates; 0 failures, 0 warnings.` |
| 3 | Breadcrumb matrix | `bash ci/breadcrumb/run_matrix.sh \| grep RESULT` | pass | `RESULT: 271 passed, 0 failed (of 271 assertions)` |
| 4 | Catalog reproduces runtime | `(cd tools/workflow-catalog && python3 derive.py verify \| tail -1)` | pass | `VERIFY OK: numberless catalog reproduces runtime for spine->development, ... release->release` |
| 5 | Old command remains one release | `ls` both SKILL.md; `grep -c ... plugin.json` | pass | both files exist; count `2` (plugin.json lines 6 and 60). Old skill is a 24-line redirect: "This command moved ... /hitl:dev-verification-review $ARGUMENTS ... removed in the release after 2.11.0" |
| 6 | Step keys unchanged | `grep -c 'key: adv_design\|key: adv_code\|key: adversarial_review' ai/shared/workflows.yaml`; `grep -c adversarial_review ci/first-pass/check_skips.py` | pass | `3`; `1` (`HARD_GATE_STEPS` at line 60). Diff of workflows.yaml changes only `label:` and `command:` on the three lines |
| 7 | Gate reads both shapes | `check_review.py --root . --change change.yaml --reviews reviews_a` (1.0, stance refute, ship) and `reviews_b` (2.0, checks pass, verified) | pass | A: `[warn] SHALLOW_REVIEW ... Release gate: verification review present, fresh, and cleared.` exit=0. B: `Release gate: verification review present, fresh, and cleared.` exit=0 |
| 8 | VERDICT_CONTRADICTED and a finding naming its check | `reviews_c` (check a fail, findings []) then `reviews_d` (+ finding F1 check: a, accepted, accepted_by) | pass | C: `[BLOCK] VERDICT_CONTRADICTED: the round says 'verified' but 1 check(s) failed with no finding answering for them (GH-1-round1.yaml: a)` exit=2. D: `Release gate: verification review present, fresh, and cleared.` exit=0 |
| 9 | Five reviewer agents open with Verify, refute gone | `grep -L 'Verify, do not confirm' ai/claude/agents/*-reviewer.md`; `grep -il refute ai/claude/agents/*.md` | pass | both empty; five `*-reviewer.md` files present. `ci/wiring/test_wiring.py:234-240` asserts both conditions |
| 10 | Docs agree with runtime, portal with version | `pytest ci/wiring -q -k "workflow_steps_doc or follow_the_runtime or portal_agrees"`; `grep -c v2.11.0 site/index.html` | pass | `3 passed, 231 deselected in 0.27s`; `1`. `plugin.json` line 3 `"version": "2.11.0"` |
| 11 | Example change file and live release change | `check_skips.py ai/shared/templates/GH-000-example.yaml`; `check_skips.py .hitl/current-change.yaml` | pass | `First Pass skip ledger: clean.` exit=0, both |
| 12 | Changelog vs `git diff --stat 143c864..HEAD` (39 files) | read-only | pass, two minor notes below | Every changelog claim maps to a changed file (skills, plugin.json, workflows.yaml, check_review.py + tests, five agents, test_wiring.py, renamed contract + template, .hitl/reviews GH-101 records). See points 1 and 2 for what the changelog does not name |

## Points

1. **minor** — Changelog says "This is also the first release whose review step passed on a review rather than a waiver." At HEAD, `.hitl/current-change.yaml` line 41 has step 5 `adversarial_review` at `status: open`. The sentence is true of GH-101's step (records `GH-101-round1/2-correctness.yaml` exist) but is written in the release note as if already true of the release itself, which at commit time it is not; it becomes true only if this round clears. Wording, not behaviour.

2. **minor** — Four shipped files changed under `ai/` are not named in the changelog: `ai/claude/dev-practices/SKILL.md`, `ai/claude/dev-practices/workflow-steps.md`, `ai/claude/start-change/SKILL.md`, `ai/claude/validate/SKILL.md`. All four diffs are rename follow-through only (command name, step label, "adversarial" to "verification" in prose), which the line "Their names and labels do [change]" covers in substance. Likewise `ci/wiring/test_shipped_tools_are_self_contained.py` (4 lines) now asserts the redirect alias is exposed; the changelog mentions the refute wiring test but not this one.

3. **minor** — A 1.0 record with zero findings and no checks (check 7, record A) clears the gate with only a `SHALLOW_REVIEW` warning. That is exactly what the changelog promises ("1.0 records keep passing on their own rules"), so it is not a defect of this release; noting it because the 2.0 rules are stricter and the two shapes coexist for at least one release.

It is right. The changelog's testable claims hold at the commit named.

## Verdict

VERIFIED.
