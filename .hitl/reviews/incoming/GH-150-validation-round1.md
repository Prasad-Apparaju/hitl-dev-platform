# GH-150 validation review, round 1

Reviewer: clean-context validation agent (Claude Fable 5.1). Commit: c7ed5b9d9e4cbd078d67e7a9dabd02b96300cd8c on issue/150-breadcrumb-mod. Date: 2026-10-05.

**Verdict: PASS with two decisions. No stops. The footprint, the renderer cache, the default path and the build all check out; the bold-current-step claim has no carrier against real renderer output.**

## Checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Gates | pass | `python3 -m pytest ci/ tools/ -q` → `1384 passed in 90.89s`; `check_skills.py` → `66/66 files pass all hard gates; 0 failures`; `derive.py verify` → `VERIFY OK`; `run_matrix.sh` → `RESULT: 283 passed, 0 failed (of 283 assertions)` with the `band/...` case lines |
| 2 | Footprint | pass | `claude plugin validate <tmp>` → `./breadcrumb-band.js hooks: ui.render{component=AbovePrompt}, turn.complete` and `calls: $.fs.exists (via readCache, readMode), $.fs.read (via readCache, readMode), $.ui.invalidate, $.ui.resolve`; `claude plugin test <tmp>` → `10 pass / 0 fail` |
| 3 | Mutation | pass | Copy with `on('tool.call', ...)` validates as `hooks: ui.render{component=AbovePrompt}, tool.call, turn.complete`; `pytest ci/breadcrumb-mod -q` on the real tree → `4 passed`; test_breadcrumb_mod.py:96 asserts `hooks == ALLOWED_HOOKS` (set equality), so the mutant fails |
| 4 | Renderer by hand | pass | No config: ribbon printed, cache 3 lines, `EQUAL: line1 == printed HITL line`; `band`: stdout empty, rc=0, file 119 bytes; `both`: ribbon printed; statusline with the matrix JSON wrote the cache; _steps.sh:399-400 `tmp="$dir/.breadcrumb.txt.tmp.$$"` then `mv -f` |
| 5 | Default unchanged | pass | run_matrix.sh diff adds one case of 12 assertions (283 - 12 = 271 pre-existing, all pass); welcome.sh diff is one inserted block at lines 54-63, the printed path at 64-87 untouched |
| 6 | Live mod | pass | `claude -p "say ok" --plugin-dir <asm> --max-turns 1` in a band-mode project → rc=0, stdout `ok`, stderr empty (0 bytes). No debug log file was present under ~/.claude/debug to grep |
| 7 | Plugin build | pass | `build.sh` → `Validation passed`; `ls hooks/` has `breadcrumb-band.js` and `hooks.json`, `hooks/tests: No such file or directory`; `claude plugin validate .` prints the same two hooks and four calls |
| 8 | Wiring | pass, one carrier gap | `.hitl/breadcrumb.txt` at .gitignore:17, init-project.sh:173, start-from-prd/SKILL.md:118, update/SKILL.md:444; tests.yml:44-51 installs the CLI before the suite; getting-started.md:148-152 documents the setting. CHANGELOG claim "with the current step in bold" has no carrier (Decide 1) |
| 9 | Coverage | see table | BM-1 partial, the rest implemented |

## Findings

### Stops

None.

### Decide

1. **The bold current step never fires on what the renderer writes.** `hitl_render_ribbon` (ai/claude/hooks/_steps.sh:355-378) marks the current phase `◐` and joins phases with two spaces; it never emits `▶` or ` › `. By-hand line 1 is `HITL development ▸ GH-000 ▸ Requirements ✓  Design ✓  Build ◐  Verify ·  Assess ·  Ship ·  Post-Ship ·`. The mod's `ribbonPieces` (breadcrumb-band.js:35-49) bolds from `▶`, and the mod test fixture (hooks/tests/breadcrumb-band.test.ts:5) is `Requirements ✓ › Design ▶ Tests · Train · Packet › Build ·`, a shape the renderer does not produce; the LLD §2 example repeats it. In use the band draws line 1 plain, and the step name (banner line `▸ Build: Generate Code (GREEN) · tier 2`) and the trail are not in the cache at all. CHANGELOG.md:11-12 "with the current step in bold" has no carrier. Decide: accept a phase-only band and fix the CHANGELOG, LLD example and test fixture, or add the step line to the cache (renderer change plus a matrix assertion).
2. **Band mode drops the plain-English directive from each prompt.** welcome.sh:62 `[[ "$mode" == "band" ]] && exit 0` runs before welcome.sh:86 `Plain English, short: shared/plain-english.md applies to every reply and document.` That line is a model directive (2.12.0), not breadcrumb content. BM-2 says the transcript prints nothing for an active change, so this is per spec, and hitl-gate.sh:49 still sends it at SessionStart. Decide: keep as is, or print that one line in band mode.

### Minor

3. **Two warning forms in line 3.** welcome.sh:61 writes `⚠ branch=main ≠ GH-000. Context may be stale; run /hitl:dev-switch-context`; statusline-hitl.sh:91 writes `⚠ branch≠GH-000`. The last writer wins, so the band's warning text flips between the two. LLD §2 accepts this; one form would be steadier.
4. **Skip reason misses the CI guard string.** LLD §5 says the mod test skips with a reason containing "not installed"; test_breadcrumb_mod.py:31-32 says `the \`claude\` CLI is not on PATH; ... (install it in CI before this job)`. tests.yml:71 greps `"not installed"`, so a skip would pass that guard. The `claude --version` at tests.yml:51 fails the job first, so this is a second line only.

## Requirements coverage

| ID | Status | Where |
|---|---|---|
| BM-1 | partial | breadcrumb-band.js:52-71 draws workflow, change id, phase ribbon (current phase `◐`) and hint; step name and bold marker absent against real output (Decide 1) |
| BM-2 | implemented | _steps.sh:383-387 `hitl_breadcrumb_mode`; welcome.sh:57-63; matrix `band/band`, `band/both`, `band/nochange` lines |
| BM-3 | implemented | _steps.sh:395-402 writer; callers welcome.sh:61 and statusline-hitl.sh:91; .gitignore:17; mod reads only the cache (breadcrumb-band.js:21-27) |
| BM-4 | implemented | test_breadcrumb_mod.py:23-24, 90-97; mutation check above |
| BM-5 | implemented | `claude -p` run rc=0, no ribbon printed in band mode; getting-started.md:148-152 recommends `both` for mixed teams |
| BM-6 | implemented | breadcrumb-band.js:74-77 invalidates on turn.complete; welcome.sh rewrites the cache on every prompt |
| BM-7 | implemented | tests/breadcrumb-band.test.ts, 10 cases incl. setting absent, band, cache missing, desktop; matrix case with 12 assertions (fixture shape caveat in Decide 1) |
| BM-8 | implemented | plugin build ships hooks/breadcrumb-band.js and hooks/hooks.json, no hooks/tests; update/SKILL.md:443-446 adds the ignore line |
