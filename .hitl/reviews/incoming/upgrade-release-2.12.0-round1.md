# Validation review, lens: upgrade, HITL 2.12.0, round 1

Source: /Users/Prasad_1/Projects/hitl-dev-platform @ 3aa5ca2a8bc46049e43576f72674692c8dec99da
Plugin: /Users/Prasad_1/Projects/hitl-claude-plugin, release/2.x (serving 2.11.0), built into a scratch clone
Scratch: /private/tmp/claude-501/-Users-Prasad-1-Projects-hitl-dev-platform/d2e697f0-dbaf-467f-b425-b4fac95245c1/scratchpad/vr212-upgrade
No tracked file in either repo was modified.

## Verdict: VERIFIED

All ten checks pass. Nothing found that stops the upgrade working.

## Checks

| # | Check | Result | Deciding output |
|---|-------|--------|-----------------|
| 1 | Build into scratch clone | pass | `bash scripts/build.sh <src>` exit 0; tail: `all shared/ references resolve` / `Build complete.`; `grep -i stale build.log` -> no lines. `git diff --stat`: 60 files, +392/-346; only untracked file `?? shared/plain-english.md` |
| 2 | plain-english.md shipped and identical | pass | `ls shared/plain-english.md` -> present; `diff -q` vs `<src>/ai/shared/plain-english.md` -> IDENTICAL |
| 3 | Pointer in both banner hooks | pass | `grep -c plain-english`: `hooks/welcome.sh:1`, `hooks/_steps.sh:1` |
| 4 | Banners rendered from built hooks | pass | Intake (tail -4): `Write for people: plain English, no filler, one page where one page will do.` / `The rule is shared/plain-english.md; it applies to every reply and every document.`; `grep -c '—'` -> 0. Active (issue/000-x + GH-000 example): `… ✓Recncl ✓QAVfy ✓ImpBrf ▶ Risk-Rated Rollout Plan ·VfyPR ·IntVfy ·Figma2 …` / `Plain English, short: shared/plain-english.md applies to every reply and document.`; `grep -c '—'` -> 0. Both exit 0, empty stderr |
| 5 | Old em-dash block still parses (show/off/on) | pass | Script extracted from built SKILL.md lines 73-333 (261 lines, `py_compile` OK). `show` printed the block incl. `set by Ada Lovelace`. `off` -> `Preferences are now PAUSED.` / `These are Ada Lovelace's settings, and CLAUDE.md is committed - ...`; diff vs original = only line 3 `ACTIVE` -> `PAUSED`, em-dash marker retained. `on` -> `Preferences are now ACTIVE.`; file byte-identical to original |
| 6 | Fresh block uses comma marker and default tone | pass | `write short "only when you ask" decision straight ""` -> `Saved to CLAUDE.md in this project.`; `grep -c 'status: ACTIVE, set by Bob,'` -> 1; line 10: `- **Tone:** plain English, short: no filler, no em dashes, numbers in a table (${CLAUDE_PLUGIN_ROOT}/shared/plain-english.md)`; `grep -c '—'` -> 0; `show` prints the block back |
| 7 | Fresh install today is 2.11.0 baseline | pass | `claude plugin install hitl@hitl` -> `Successfully installed plugin: hitl@hitl (scope: user)`; `ls cfg/plugins/cache/hitl/hitl/` -> `2.11.0`; plugin.json version 2.11.0; `ls .../2.11.0/shared/plain-english.md` -> No such file or directory |
| 8 | Version and changelog | pass | plugin.json version -> `2.12.0`; `grep -n '^## \[2.12.0\]' CHANGELOG.md` -> `7:## [2.12.0] — 2026-09-05` |
| 9 | Shipped skills/agents resolve every shared/ file named | pass | 21 unique `${CLAUDE_PLUGIN_ROOT}/shared/...` refs checked; no `MISSING` lines |
| 10 | Redirect skill still ships | pass | `ls skills \| grep -c ...` -> 2 (`dev-adversarial-review`, `dev-verification-review`) |

## Points, ranked

1. **worth deciding**: the default Tone line that `write` puts into the project's committed CLAUDE.md carries the literal string `${CLAUDE_PLUGIN_ROOT}/shared/plain-english.md` (SKILL.md line 301, observed in the C6 output). CLAUDE.md is not a plugin file, so nothing expands that variable there; a teammate reading the file sees an unresolved shell variable, and one without HITL installed has no file to open. The parser round-trips it fine (C6 show), so it is not a defect in the upgrade path, but it is a shipped line that the plain-English standard's own "write for people" test would not pass.
2. **minor**: the 2.12.0 changelog heading (`## [2.12.0] — 2026-09-05`) and the multi-block warning inside the prefs script (line 122, `... markers — more than one preferences block`) both use an em dash, in the release that ships a rule against em dashes (plain-english.md line 17). The heading matches every prior heading, so this is a convention question, not a regression.
3. **minor**: em dashes remain in shipped prose after the rewording pass: 69 files under skills/, 59 under shared/, 6 under agents/, 11 under hooks/ (the hooks hits sampled are shell comments, not output). The two banners and the fresh prefs block are clean, which is what this lens tested; the rest is residue the standard now points at.

Nothing else. The em-dash-to-comma marker migration is transparent: old blocks read, toggle, and restore byte-for-byte; new blocks write and read back with the comma form.
