# Correctness review, release 2.12.0, round 1

Repo `/Users/Prasad_1/Projects/hitl-dev-platform` at `3aa5ca2a8bc46049e43576f72674692c8dec99da`. Validation checklist run, lens: correctness. No tracked file modified by this review. Scratch: `scratchpad/vr212-correctness` (probe.py, welcome.out, proj/.hitl/).

Working-tree note: while this ran, `ai/claude/preferences/SKILL.md` acquired a 4-line uncommitted edit from another agent (lines 194 and 301). Checks 7 and 8 were re-verified against `HEAD` with `git show`; check 1 ran on the working tree, and the edit is string-only, so the outcome is not in doubt but the run was not on a pristine HEAD.

## Verdict: VERIFIED

All twelve checks pass. The changelog's claims map to changed files. Nothing found that stops it working.

## Checks

| # | Check | Result | Deciding output |
|---|-------|--------|-----------------|
| 1 | `python3 -m pytest ci/ tools/ -q \| tail -1` | pass | `897 passed in 56.39s` |
| 2 | `python3 ci/skill-lint/check_skills.py \| grep 'Skill lint'` | pass | `Skill lint: 63/63 files pass all hard gates; 0 failures, 0 warnings.` |
| 3 | `bash ci/breadcrumb/run_matrix.sh \| grep RESULT` | pass | `RESULT: 271 passed, 0 failed (of 271 assertions)` |
| 4 | lint covers the four surfaces | pass | `grep -c '^def test_'` = 5; names: `test_hook_messages_are_plain_english`, `test_the_lines_skills_tell_the_model_to_say_are_plain_english`, `test_document_templates_are_plain_english`, `test_the_preferences_block_is_plain_english`, `test_the_rule_ships_and_the_banner_points_at_it` |
| 5 | lint not vacuous (`probe.py` on `_marks`) | pass | `a: ['em dash', "'robust'"]`, `b: []`, `c: ["'Note that'"]`, `PROBE OK`. The tell caught in (a) is `robust`, not `it's worth noting`: `_marks` reports the first regex hit only, one tell per line |
| 6 | no em dash in text that reaches people | pass | `grep -c '—' ai/shared/plain-english.md` = 1 (the example row, expected). `welcome.sh` in a scratch project with empty `.hitl/`: exit 0, em dash count in output 0, last content lines `Write for people: plain English, no filler, one page where one page will do.` / `The rule is shared/plain-english.md; it applies to every reply and every document.` then the rule bar |
| 7 | preferences default tone | pass | HEAD `SKILL.md:300 ANS["tone"] = ...` / `:301 else "plain English, short: no filler, no em dashes, numbers in a table (shared/plain-english.md)"` |
| 8 | older blocks still parse | pass | HEAD `SKILL.md:188 ... set by (.*?)(?: —\|,) /hitl:dev-preferences`. Functional probe of that regex against an em-dash header and a comma header: `old: alice \| new: alice` |
| 9 | generator + HLD/LLD/ADR templates carry ceilings | pass | `grep -c 'plain-english\|ceiling'`: SKILL.md 2, hld 1, lld 1, adr 1 |
| 10 | getting-started says 58, plugin ships 58 | pass | `docs/getting-started.md:61: **There are 58 HITL commands...**`; `ls -d .../hitl-claude-plugin/skills/*/ \| wc -l` = 58. Plugin repo is on `release/2.x` at `988371d build: ship plain-english.md as shared prose`, so already past 2.11.0, not at it as the checklist stated; the count is unaffected |
| 11 | floor sentences survived | pass | `19 passed, 145 deselected in 0.05s`; `grep -c 'A preference shapes form, never substance' CLAUDE.md.template` = 1 |
| 12 | changelog vs `git diff --stat bd5eba8..HEAD` | pass, with notes | 74 files. Every changelog claim maps to a changed file (map below). Changed ai/ci files the changelog does not name: `ai/claude/plugin/plugin.json` (version bump), `ci/wiring/test_shipped_tools_are_self_contained.py` (floor sentence text + 7 SHA pins re-pinned to the reworded templates), `ai/claude/generate-docs/templates/CLAUDE.md.template` (30 lines reworded, floor sentence intact) |

Claim to file map for check 12: rule → `ai/shared/plain-english.md` (new, 72 lines). Banners → `hooks/_steps.sh:292`, `hooks/welcome.sh:76`. Preferences default and comma delimiter → `preferences/SKILL.md` (lines 188, 268, 300-301). Generator and templates → `generate-docs/SKILL.md`, `hld-template.md`, `lld-component-template.md`, `adr-template.md`; impact brief, retro, review ceilings → `impact-brief/SKILL.md`, `retro/SKILL.md`, `conclude/SKILL.md` (+2 each). Lint → `ci/wiring/test_plain_english.py` (161 lines; template surface covers both `ai/shared/templates` and `generate-docs/templates`). "Around sixty shipped lines reworded" → the remaining ~45 skill, hook and template files.

## Points, ranked

1. **worth deciding.** One em dash still reaches people at HEAD and the lint cannot see it: `git grep -n 'print(.*—' HEAD -- 'ai/claude/**/SKILL.md'` → `ai/claude/preferences/SKILL.md:194: print("CLAUDE.md has %d begin / %d end markers — more than one preferences block. ...")`. That is an error message the skill prints to the user in `show` mode. The lint's four surfaces (hook messages, quoted say-lines, templates, the BLOCK literal) do not include `print()` strings in skill scripts. The headline claim "no em dashes in text that reaches people" is therefore true for the four surfaces the changelog names and false for this one path. (The uncommitted working-tree edit removes it, which suggests someone already found it; it is not in 3aa5ca2.) A second, lesser case: `hooks/write-session-summary.sh:46` writes `# HITL session logs — operational artifacts, not product code` into the project's `.gitignore`.
2. **worth deciding.** The changelog says "Every prompt banner points at the rule". Two hook files carry the pointer (`_steps.sh`, `welcome.sh`). `hooks/hitl-gate.sh` prints a `━━━` banner and does not. It is a PreToolUse block notice, not a session-entry prompt, so the claim holds if "prompt banner" means SessionStart and the no-active-change directive; `test_the_rule_ships_and_the_banner_points_at_it` asserts only on those two files, which matches that reading.
3. **minor.** `docs/getting-started.md` changed to "There are 58 HITL commands" but the 2.12.0 changelog section does not mention it. The checklist treated it as a changelog claim; it is not one.
4. **minor.** `ci/wiring/test_shipped_tools_are_self_contained.py` re-pinned seven SHA constants and `EMITTED_BLOCK_SHA` to the reworded template bytes. Expected cost of the rewording; the floor-sentence assertions still pass; the changelog does not say the pins moved.
5. **minor.** `_marks` reports at most one tell per line (first regex hit). The lint is still fail-closed, so this only affects the failure message, not the outcome.

Nothing classed **stops it working**.
