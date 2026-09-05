# Verification review — lens: upgrade — round 1

Source: hitl-dev-platform @ 0dd84c9a807d4eb0798e2c64b597c8594b830db0 (HEAD)
Plugin: hitl-claude-plugin release/2.x (serving 2.10.1), built into a scratch clone, nothing released.
Scratch: /private/tmp/claude-501/-Users-Prasad-1-Projects-hitl-dev-platform/d2e697f0-dbaf-467f-b425-b4fac95245c1/scratchpad/vr-upgrade

## Checks

| # | Check | Result | Deciding output |
|---|-------|--------|-----------------|
| 1 | Build from source into scratch clone | pass | `bash scripts/build.sh <src> \| tail -5` → `all shared/ references resolve` / `Build complete.` |
| 2 | New skill exists, old skill is a redirect | pass | `ls` → both `skills/dev-verification-review/SKILL.md` and `skills/dev-adversarial-review/SKILL.md`; `grep -c dev-verification-review skills/dev-adversarial-review/SKILL.md` → `3` |
| 3 | New shared files exist; old ones absent | pass with finding | new: all three present. old: `shared/adversarial-review.md` and `shared/templates/adversarial-review-record.yaml` are STILL PRESENT in the build (source has neither: `ls ai/shared/adversarial-review.md` → No such file). See point 1. |
| 4 | Shipped gate identical to source | pass | `diff -q shared/ci/adversarial/check_review.py <src>/ci/adversarial/check_review.py` → no output (IDENTICAL) |
| 5 | No bare `shared/` paths in new SKILL.md | pass | `grep -nE '(^\|[^}/A-Za-z0-9_])shared/[a-z]' skills/dev-verification-review/SKILL.md` → no output |
| 6 | Version and changelog | pass | plugin.json version → `2.11.0`; `grep -n '^## \[2.11.0\]' CHANGELOG.md` → `7:## [2.11.0] — 2026-09-04` |
| 7 | Old 1.0-shape records still parse under the new gate | pass | run against `.hitl/reviews/GH-92-release-2.8.0-round5-{consequence,correctness}.yaml` with `--sha 699b87a3…` → codes emitted: `[warn] TARGET_NOT_HEAD`, `[warn] ROUND_DEPTH`, `[BLOCK] VERDICT_NOT_SHIP` (round5-consequence verdict is `do-not-ship`), exit 2. NO `REVIEW_MALFORMED`, NO `WRONG_STANCE`. The block is that record's own content. |
| 8 | Validator sync keeps a locally-differing gate (co-owned) | pass | flag shape: `migrate_project.py [--root ROOT] [--apply] [--sync-validators PLUGIN_ROOT] [--overwrite PATH]`. Dry run from `<scratch>/proj` with the published 2.10.1 `ci/adversarial/check_review.py` in place → `~ ci/adversarial/check_review.py differs from the shipped version — KEPT yours.` … `= 0 identical, 14 to install, 1 modified here and kept, 0 overwritten by name` … `(dry run — re-run with --apply to install)`. `diff -q` against release/2.x copy afterwards → NOT OVERWRITTEN. |
| 9 | Fresh install today is 2.10.1 without the new skill | pass | `claude plugin install hitl@hitl` → `Successfully installed plugin: hitl@hitl`; `ls cfg/plugins/cache/hitl/hitl/` → `2.10.1`; its `skills/` lists `dev-adversarial-review`, no `dev-verification-review`; its `shared/` has `adversarial-review.md` only. |
| 10 | No live references to the old filenames in source | pass | one hit: `ci/wiring/test_shipped_tools_are_self_contained.py:243: assert (cmds / "adversarial-review.md").exists()` — that is the `.claude/commands/adversarial-review.md` redirect command the test deliberately keeps for one release (#101), not the removed shared prose or template. |

## Points

1. **worth deciding** — The build ships two stale files alongside the new ones: `shared/adversarial-review.md` and `shared/templates/adversarial-review-record.yaml`. Neither exists in source any more. `scripts/build.sh` copies shared prose and templates forward (lines 250-265, 414-420) and has stale-dir removal only for `skills/` (line 52) and `commands/` (line 94), nothing for `shared/`. The build also rewrites the stale template: because `adversarial-review.md` left `SHARED_PROSE`, pass 2 strips its prefix and nothing re-adds it, so `git diff` shows `${CLAUDE_PLUGIN_ROOT}/shared/adversarial-review.md` → bare `shared/adversarial-review.md` (line 13). Nothing shipped references either stale file (grep over skills/, agents/, shared/ finds only the stale template's own self-reference), so an upgrader is not broken; they do get two templates and two prose files describing two contradictory review models, one carrying exactly the bare-path shape the build's own comment says it exists to prevent. The `git diff --stat` review step the build prints is the only thing standing between these and release/2.x. Decide whether the release commit removes them by hand or the build learns to sweep `shared/`.

2. **minor** — Check 7 reproduces the 1.0-shape records parsing cleanly, but the only 1.0 records available carry a `do-not-ship` verdict, so the run ends BLOCKED on content and never reaches the "old record passes the gate" outcome the redirect skill promises ("your existing review records still pass the gate"). The shape claim is verified; the pass-through claim for a 1.0 record with verdict `ship` was not exercised here.

Everything else on the list did what it says. Fresh install baseline is 2.10.1 as expected, the co-owned validator protocol held on a dry run, the gate copy is byte-identical, and the redirect command resolves to the new name.

## Verdict

VERIFIED. The one open item (point 1) is a packaging leftover the release commit can drop; it does not break an upgrading or freshly-installing user.
