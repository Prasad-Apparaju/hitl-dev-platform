# GH-143 release 2.16.0, correctness lens, round 2

Reviewer: clean-context validation reviewer (Fable 5.1), 2026-10-01.
Source: hitl-dev-platform main at b3bf007e34ad872b5056e56537bba6798e1af1a9 ("fix(release 2.16.0): round 1 findings"). Round 1 reviewed 36f85f1. Repo not modified.

## Verdict

**Pass with one fix.** The round-1 finding is fixed, the three gates are green at b3bf007, and the diff since 36f85f1 touches only the six files expected. One new finding of the same class as round 1's upgrade F2: start-change Step 6c sets LINKED inline but borrows `$ROOT` from a fence 27 lines earlier, and in a fresh shell the fallback is the bare `/shared/ci/linked/linked.py`. One-line fix; does not need another round.

## Round-1 claim

F1: "\"40 tests against a fake host plus 7 gate tests\" does not reproduce: ci/linked collects 34; 40 is only reached by adding the 5 ci/wiring linked tests and 1 Team Pulse pfx2 test, which do not use a fake host." **Fixed.** CHANGELOG.md 2.16.0 now reads "34 checker tests against a fake host, 7 gate tests and 6 wiring tests". Counts reproduce (check 1).

## Checks

1. F1 counts. `python3 -m pytest ci/linked -q` collects 34 (28 `def test_` plus parametrisation; 2 of the 34, chk8 and pfx1, read config and do not touch the fake host, so "34 against a fake host" is loose by two but not wrong in the sense that matters). `python3 -m pytest ci/preflight -k linked -q` collects 10, not 7: the 7 are `ci/preflight/test_check_change_linked.py::test_gate1..test_gate6` (gate2 has an a/b pair); the other 3 are the pre-existing `TestLinkedIssue` tests that merely match the keyword. `python3 -m pytest ci/wiring -k linked -q` is 5, plus `tools/team-pulse/test_pulse.py::test_pfx2_change_id_prefix_falls_back_to_the_repository_setting` is 6. Pass. Nit: the Team Pulse test is a config-fallback unit test, labelled "wiring" by grouping only.
2. Gates. `python3 -m pytest ci/ tools/ -q`: 1314 passed in 81.58s. `python3 ci/skill-lint/check_skills.py`: exit 0 (63 directory-name fallbacks, valid). `(cd tools/workflow-catalog && python3 derive.py verify)`: VERIFY OK for all eight workflows. Pass.
3. Skill meaning after the round-1 fixes. `git diff 36f85f1 b3bf007 -- ai/claude ai/shared` read in full. tdd (lines 44-46), ops/deploy (82-84) and apply-change (54-57) each now carry ROOT resolution, the LINKED assignment and the checker call in one fence; the prose around them is unchanged in meaning (refuse on exit 2 quoting the verdict line, stop on exit 3 naming the failed read; fetch by pinned reference, cite the reference not the cached path). start-change Step 6c (line 474) inlines LINKED but has no ROOT resolution of its own; its only ROOT lines are 341 and 447, inside earlier fences. Live run of the tdd fence's two lines in an empty scratch dir with CLAUDE_PLUGIN_ROOT unset: ROOT resolves to `/Users/Prasad_1/.claude/plugins/cache/hitl/hitl/2.12.1`, LINKED to `<that>/shared/ci/linked/linked.py`, and `python3 "$LINKED" --help` reports the file missing (exit 2) because the installed cache is 2.12.1, which predates the checker. Path is under the plugin root, never a bare `/shared` path. Pass for the three skills, fail for Step 6c (finding 1). Note: the brief said the installed cache is 2.15.0; on this machine installed_plugins.json lists only 2.12.1.
4. Diff scope. `git diff --stat 36f85f1 b3bf007`: CHANGELOG.md, ai/claude/apply-change/SKILL.md, ai/claude/ops/deploy/SKILL.md, ai/claude/start-change/SKILL.md, ai/claude/tdd/SKILL.md, ai/shared/linked-changes.md; 6 files, +16/-7. Pass.

## New findings

1. **start-change Step 6c falls back to a bare `/shared` path in a fresh shell** (ai/claude/start-change/SKILL.md:474). The line `LINKED="ci/linked/linked.py"; [[ -f "$LINKED" ]] || LINKED="$ROOT/shared/ci/linked/linked.py"; python3 "$LINKED" link-sub ...` is inline prose, not in the fence that sets ROOT (line 447, Step 6b). Bash tool calls do not share environment between invocations, so when the model runs 6c on its own in a product repo without `ci/linked/`, ROOT is empty. Reproduced: `env -u ROOT -u CLAUDE_PLUGIN_ROOT bash -c '<the 6c line>'` in an empty dir prints `LINKED=/shared/ci/linked/linked.py` and `python3: can't open file '/shared/ci/linked/linked.py'`. This is the defect round 1's upgrade F2 fixed in the other four skills; the upgrade round-2 report lists it as advisory note 1. Fix: prepend the same ROOT line to the 6c command, or move the three statements into a fence. Scope-limited: the platform repo has `ci/linked/` locally, so only onboarded product repos hit it.

No other findings. Not re-checked here (upgrade lens): the plugin-side `scripts/build.sh` ci/linked block that ships `shared/ci/linked/linked.py` was reported uncommitted by the upgrade round-2 reviewer; the fallback path in all five skills depends on it landing in the 2.16.0 build.
