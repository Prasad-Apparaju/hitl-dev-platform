# GH-151 validation review, round 1

Reviewer: clean-context validation agent (Claude Fable 5.1). Commit: 92bccd06313c548ae777c282f72bbd73e8904985 on issue/151-skills-guide, confirmed with `git rev-parse HEAD`. Working tree untouched except this file. The plugin repo build was run as instructed; its working tree was already modified before the build.

**Verdict: PASS. No stops. One decide item, four minor. Behaviour of the six split skills is preserved.**

## Checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Gates | pass | `python3 -m pytest ci/ tools/ -q`: `1515 passed, 53 skipped`. `check_skills.py`: `66/66 files pass all hard gates`. `derive.py verify`: `VERIFY OK`. `run_matrix.sh`: `287 passed, 0 failed`. |
| 2 | Fences, blockquotes, commands | pass | Script over main vs new SKILL.md plus siblings, trailing whitespace normalised: fences 49 of 50 verbatim, blockquotes 38 of 41, `/hitl:` names 45 of 45. The two gaps are Minor 2 and 3 below; both keep the behaviour. start-change: old fences 3, 4 and 8 are embedded verbatim after the added `ROOT=` and `PY=` lines; `bash -n` passes on all 11 new start-change fences with placeholders replaced. |
| 3 | Reference files | pass | All 10 new files are named in their SKILL.md (intake-detail 4 mentions, setup-detail 4, phase-detail 3, others 1 or 2). No new file links onward to a further reference; the only `.md` mentions are return pointers to `SKILL.md`, output paths under `docs/`, and one description of a file in resync-validators.md:25. The three over 100 lines (intake-detail 226, setup-detail 142) start with `## Contents`; phase-detail is 85 lines. `bash scripts/build.sh` exits 0; the six plugin skill directories list exactly the source files, no stale file. |
| 4 | History trim | pass | 35 removed lines matched the pattern. Ten sampled; every rule survives: `apply-change/SKILL.md:51` "refuse a bare number and name the form"; `:93` "penetration test whatever else was found; they are conditional steps"; `pm/design-feature/SKILL.md:93` "Compound-surface probe"; `agentic-intake/SKILL.md:18` "run no compound-agentic validator, and produce no design artifact"; `start-change/SKILL.md:32` "No tier question at intake; the tier is proposed at Step 4" (story of the three-and-a-half-hour path dropped); `intake-detail.md:82` "a different spelling each time is how a name stops being findable"; `intake-detail.md:162` "the confirming person, never `not_applicable`"; `start-from-prd/SKILL.md:82` "(Windows Python defaults to cp1252)"; `setup-detail.md:71` "Install the semgrep convention rules"; `resync-validators.md:11` "a blind copy would revert that fix on every run" and `:17` "an older version is not an edit". No removal dropped a rule. |
| 5 | Rules before steps | pass with one gap | start-change `## Rules that hold throughout` at line 25, Step 1 at 55, old three bullets present plus seven. start-brownfield 13 before Step 0 at 22. update 11 before Step 1 at 19. tdd 73 before Phase 1 at 97, the one old bullet verbatim. design-system 76 before Phase 1 at 82, the one old bullet verbatim. start-migration has no rules section (Decide 1). |
| 6 | Guard test | pass | `ci/wiring/test_skill_guide.py`: TOKEN_CEILING 5500 on eight long skills, HISTORY_CEILING 3 on prose outside fences, contents list over 100 lines, third-person description under 1,024 chars. Mutation: a copy of tdd/SKILL.md plus 3,000 chars in a scratch checkout fails with `tdd/SKILL.md body is about 5654 tokens; only the first 5,000 come back after compaction`. |
| 7 | Evals | pass | Five cases read. `ops-incident` in help/SKILL.md:110 and :192. `SVC-42`: fixture writes `change_id_prefix: SVC`, start-change/SKILL.md:66 names the `<PREFIX>-<n>` form. `hasn't been set up for HITL` in qa/plan-tests/SKILL.md:10. `Design approval is required before implementation can begin` in tdd/SKILL.md:31. `Added by:` and `### SC-<change-id>-<nn>:` in qa/scenarios/SKILL.md:64 to 66 and ai/shared/test-scenarios.md:19. docs/releasing.md lines 67 to 69 carry the same two commands as evals/README.md. Not run. |
| 8 | Contents lists | pass | verification-review (263 lines, 12 entries), personas (178, 5), challenge-stance (127, 7), graphify-setup (136, 7): entries equal the `## ` headings in order. |
| 9 | Plain English | pass | `test_plain_english.py`: `16 passed`. Em dashes: 0 in evals/README.md; 55 across the ten reference files (Minor 4). |

## Findings

### Stops
None.

### Decide
1. **start-migration has no rules section.** `ai/claude/start-migration/SKILL.md` goes from the intro (lines 10 and 12 hold two bold rules, "Migration is not brownfield" and "pause after each") straight to `## Step 0` at line 17. The old file had no Important Rules section either, so nothing was lost, but the commit message says all six got "the rules that hold throughout placed before the steps". Either add the section or amend the claim.

### Minor
2. **One blockquote became a rule bullet.** main `start-brownfield/SKILL.md:147-149` "> **Breadcrumb advancement:** at the start of each step below, edit `.hitl/current-change.yaml` ..." is now `start-brownfield/SKILL.md:15` "**Breadcrumb.** Step 1 writes `.hitl/current-change.yaml`. At the start of every later step, set the previous step's `status: done`, the new step's `status: current`, and `current_step` ...". Same rule, stronger placement; the "every blockquote preserved" claim is 38 of 41.
3. **One duplicate fence was folded.** main `update/SKILL.md` Step 3 repeated the Step 1 version-read fence without its comments. New `update/SKILL.md:66` says "Run the Step 1 block again." Same behaviour; the "every bash fence preserved" claim is 49 of 50.
4. **Em dashes rose in three skills.** Old SKILL.md vs new SKILL.md plus siblings: start-migration 70 to 88, design-system 59 to 71, tdd 38 to 40; setup-detail.md alone has 25. Model-facing prose is not linted by decision, so no gate; noted against the no-em-dash preference.
5. **Headroom on the ceiling is thin.** Body tokens by the test's measure: start-change 5487, start-brownfield 5198, update 5193 against 5500. The next sentence added to start-change SKILL.md fails the guard, which is the intent, but the owner should expect it on the first follow-up.
