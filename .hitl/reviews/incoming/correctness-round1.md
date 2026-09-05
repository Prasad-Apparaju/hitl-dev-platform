# Verification review — correctness — round 1

State under review: `1d20e4b3585683b96179add79b0b5c29ab43f3f0` (HEAD, confirmed with `git rev-parse HEAD`).
Scratch: `/private/tmp/claude-501/.../scratchpad/vr-correctness`. No tracked files modified.

## Checks

| # | Check | Command | Result | Deciding output |
|---|---|---|---|---|
| 1 | Gate suite passes | `python3 -m pytest ci/adversarial -q` | pass | `58 passed, 1 skipped in 3.63s` |
| 2 | A clean 2.0 record passes | `python3 ci/adversarial/check_review.py --root . --change <scratch>/change.yaml --reviews <scratch>/reviews` | pass | `Release gate: verification review present, fresh, and cleared.` exit=0 |
| 3a | `verdict: not-verified` blocks | same, `--reviews <scratch>/reviews_ns` | pass | `[BLOCK] VERDICT_NOT_SHIP: ... verdict is 'not-verified'` exit=2 |
| 3b | `result: fail` + `verdict: verified` blocks | same, `--reviews <scratch>/reviews_fc` | pass | `[BLOCK] VERDICT_CONTRADICTED: the round says 'verified' but 1 check(s) failed (GH-101-round1.yaml: a)` exit=2 |
| 4 | 1.0 record parses under its own rules | `check_review.py --root . --change <scratch>/change92.yaml --reviews .hitl/reviews --sha 699b87a34b5e9e7624484c44a37f4b7df037f518` (record: `schema_version: '1.0'`, `stance: refute`, `verdict: do-not-ship`) | pass | No `REVIEW_MALFORMED`, no `WRONG_STANCE`. Printed: `[warn] TARGET_NOT_HEAD`, `[warn] ROUND_DEPTH` (round 5), `[BLOCK] VERDICT_NOT_SHIP: ...round5-consequence.yaml: verdict is 'do-not-ship'` exit=2. All expected for that record set; not this check's concern. |
| 5 | Step keys unchanged; skip ledger clean | `grep -c 'key: adv_design\|key: adv_code\|key: adversarial_review' ai/shared/workflows.yaml`; `python3 ci/first-pass/check_skips.py ai/shared/templates/GH-000-example.yaml` | pass | `3`; `First Pass skip ledger: clean.` exit=0 |
| 6 | No agent carries the refute line | `grep -il refute ai/claude/agents/*.md` | pass | empty (grep exit=1) |
| 7 | Skill lint | `python3 ci/skill-lint/check_skills.py` | pass | `Skill lint: 63/63 files pass all hard gates; 0 failures, 0 warnings.` (the `tail -2` form only shows the trailing note line and a blank; `tail -5` shows the summary) |
| 8 | Docs and runtime agree | `python3 -m pytest ci/wiring -q -k "workflow_steps_doc or follow_the_runtime or reviewer_agent"` | pass | `3 passed, 231 deselected in 0.27s` |
| 9 | Command map names the new command only | `grep -c 'dev-verification-review' docs/command-map.generated.md`; `grep -c 'dev-adversarial-review' ...` | pass | `2`; `0` |
| 10 | Skill consistent with itself and the template | read: `ai/claude/verification-review/SKILL.md`, `ai/shared/templates/verification-review-record.yaml`, `ci/adversarial/check_review.py` lines 447-544 | pass, with one point below | Compared: Step 5 disposition table (fix/accept/defer -> fixed/accepted+accepted_by) vs template `status: open|fixed|accepted`, `accepted_by` — agree. Step 3 report classes (stops it working / worth deciding / minor) vs template `class: stops|decide|minor` — agree, prose-to-enum mapping unstated but unambiguous. Step 6 `checks` fields (check, command, result pass/fail/unknown, output) vs template `checks[]` — identical. Step 3 `.hitl/reviews/incoming/<lens>-round<N>.md` and Step 6 `.hitl/reviews/<change-id>-round<N>.yaml` vs template "each reviewer gets its own record and its own lens" — see point 2. No sentence in the skill contradicts another sentence in the skill on record fields or report shape. |

## Points

1. **worth deciding** — The skill's "accept" disposition cannot reach a passing gate when the accepted finding sits on a `fail` check. Step 5 and Step 7 say every stops/decide point ends as `fixed` **or** `accepted` with a name, and the gate's own message says the same ("A failed check is resolved as a finding — fixed, or accepted with a name — not by the verdict"). But `failed_checks` (check_review.py:450-472) counts every `result: fail` with no look at findings. Reproduced: a record with `checks[0].result: fail`, `findings[0].status: accepted, accepted_by: prasad`, `verdict: verified` -> `[BLOCK] VERDICT_CONTRADICTED ... 1 check(s) failed` exit=2. Since accepting changes no code, a re-run round against the same sha fails the same check again, so the only way through is `verdict: not-verified` (blocks) or rewriting the reviewer's checks table (which Step 6 says is "the table from the report"). Either the accept path is meant not to apply to failed checks, in which case Step 5/7 and the gate message overstate it, or the gate should exclude fails covered by an accepted-with-name finding. Someone has to choose which.
2. **minor** — Step 6 (and the shared contract, `ai/shared/verification-review.md:238`) names the record `.hitl/reviews/<change-id>-round<N>.yaml`, one file per round, while Step 3 spawns one reviewer per lens and the template says each reviewer writes its own record. Two lenses in one round collide on that filename. The gate discovers by `listdir` and reads `round`/`lens` from the fields, so the lens-suffixed names already in `.hitl/reviews/` (`GH-92-release-2.8.0-round5-correctness.yaml`) work fine; the skill just does not say to add the suffix, and the Step 6 bash echo hardcodes `round1`.
3. **minor** — Step 2 says "a round takes roughly ten minutes" and then the example offer says "Three lenses, about half an hour". If lenses run in parallel in the background the round is still ten minutes; if serial the first sentence is the per-lens cost. The two sentences quote different things as "a round".

Everything on the checklist passed with the expected output. Points 2 and 3 are wording; point 1 is a real, reproduced gap in a path the skill promises but the gate does not allow, and it is not one of the ten checks.

## Verdict

**VERIFIED** — all ten checks pass as specified. Point 1 is worth deciding before the next release but does not fail a check in this brief.
