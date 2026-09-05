# Validation review: correctness, round 2, HITL 2.12.0

Commit: 3b35cdc40d19f9efb3e33c07ccd01fa4285dc10b (HEAD). Plugin: hitl-claude-plugin release/2.x, built into a scratch clone. Read-only run; no tracked file modified.

## Checks

| # | Check | Result | Deciding output |
|---|-------|--------|-----------------|
| 1 | `bash scripts/build.sh <dev-platform>` in scratch clone of release/2.x | pass | `all shared/ references resolve` / `Build complete.` |
| 2 | Built `skills/dev-preferences/SKILL.md`, default tone string | pass | line 301: `"plain English, short: no filler, no em dashes, numbers in a table (HITL's plain-english rule)"`; grep for `CLAUDE_PLUGIN_ROOT` or `shared/` on that line: 0 |
| 3 | Extracted `prefs.py` (261 lines, parses), `write short "only when you ask" decision straight ""` in empty git repo | pass | `10:- **Tone:** plain English, short: no filler, no em dashes, numbers in a table (HITL's plain-english rule)`; Tone line with `$` or `shared/`: 0; `grep -c '—' CLAUDE.md` = 0 |
| 4 | `show` with the block doubled | pass | `CLAUDE.md has 2 begin / 2 end markers, so more than one preferences block. Showing the first; fix the file by hand, the other modes refuse to touch it.` exit 0; em dashes in output: 0 |
| 5 | `pytest ci/wiring/test_plain_english.py -q`; `grep -c '^def test_'` | pass | `16 passed in 0.21s`; def test_ count: 6 |
| 6 | probe.py: `_marks('Done — nothing to do')` / `_marks('Done. Nothing to do')`; echo-with-em-dash grep over SKILL.md | pass | `marks(em dash) = ['em dash']`, `marks(plain) = []`, `probe OK`; echo grep count: 0 |
| 7 | `plain-english` in hitl-gate.sh / _steps.sh / welcome.sh; non-comment em dash lines in write-session-summary.sh | pass (see point 1) | counts 1 / 1 / 1; the literal `grep -v '^[0-9]*:\s*#'` returned lines 5 and 16, both trailing `# ...` shell comments on code lines, never printed; `grep -n 'printf.*—'` on the built hook: empty |
| 8 | `pytest ci/wiring -q`; skill lint; breadcrumb matrix | pass | `250 passed in 24.14s`; `Skill lint: 63/63 files pass all hard gates; 0 failures, 0 warnings.`; `RESULT: 271 passed, 0 failed (of 271 assertions)` |
| 9 | `pytest ci/ tools/ -q` | pass | `898 passed in 59.62s` |
| 10 | Changed files under ai/ outside the expected classes | reported | `ai/claude/update/change-file-migration.md` (skill sub-document with an embedded Python script; three print() messages reworded, em dash to colon). Also outside ai/: `ci/wiring/test_shipped_tools_are_self_contained.py` rebumps the floor-region hash for `personas.md / where they live` to match the reworded echo lines |

Extra checks the changes could have disturbed, also run:

- Built `hooks/hitl-gate.sh` line 49 reads `Plain English, short: shared/plain-english.md applies to every reply and document.`; the build does not rewrite `shared/` inside hooks (`CLAUDE_PLUGIN_ROOT` count in the three hooks: 0 / 0 / 0), and rendering the line through an unquoted heredoc with `CLAUDE_PLUGIN_ROOT=/x/plug` set prints it verbatim. The round-1 defect class (unexpanded variable reaching a person) does not recur here.
- `_skill_files()` in the lint walks every `.md` under `ai/claude` and `ai/shared`, so the new surface 2b covers `change-file-migration.md` and `personas.md` too, not only SKILL.md. Grep for print/echo/SystemExit lines carrying an em dash in non-SKILL `.md` files under ai/: empty.
- `personas.md` diff is three `echo` messages (em dash to colon); 16 em dashes remain in its prose, none in a printed string.

## Points

1. **minor**: check 7's literal command is not empty. Lines 5 and 16 of `ai/claude/hooks/write-session-summary.sh` carry an em dash in a trailing shell comment (`exit 0  # not a HITL project — skip silently`). They are never written or printed; the `printf` that writes into a user's `.gitignore` is clean. The check's intent holds; the check text should say "no em dash in a printed or written string" rather than "non-comment lines".
2. **minor**: the floor-region hash in `ci/wiring/test_shipped_tools_are_self_contained.py` was rebumped for `personas.md / where they live`. That is the correct consequence of rewording a protected region and the diff of the region is three echo lines, but a rebumped floor hash is the kind of edit a release reviewer should see named; it is not in the commit message list the round-2 brief carried.
3. **minor**: the new lint surface matches `\b(print|SystemExit|echo)\b` and then extracts double-quoted literals only. A single-quoted `echo '...—...'` or an f-string with the mark inside a `{}` expression would pass. No such line exists today (grep over ai/ for echo/print with em dash: empty), so this is a coverage note, not a defect.

Everything else is right.

## Verdict

VERIFIED.
