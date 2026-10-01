# GH-143 upgrade review, round 1 (2.16.0)

**Verdict: proceed with changes.** The package builds, validates, syncs and onboards cleanly; the 2.15.0 upgrade path keeps and updates the right files. Two skills wire the new checker through shell variables they never set, so the plugin-side fallback cannot run, and one CHANGELOG claim describes a gate that only the platform repo has.

Source `36f85f1` ("chore(release): 2.16.0"); plugin `release/2.x` at `057b25a` plus the uncommitted `scripts/build.sh`, copied to a scratch directory and built there (`bash scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform`, exit 0).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Build clean, guard, reachability, version | PASS | build.log: no `SOURCE PATH` or `MISSING` lines, `all shared/ references resolve`, `Build complete.`; plugin.json `"version": "2.16.0"` |
| 2 | Linked changes ship where skills look | PARTIAL | `shared/ci/linked/linked.py` (only file, no test), `shared/linked-changes.md` present; `--help` exit 0; literal `linked.py` references: dev-tdd 1, ops-deploy 1, dev-retro 2, **dev-apply-change 0, dev-start-change 0** (both use `$LINKED`, see F2); dev-start-change fences: no bare `${CLAUDE_PLUGIN_ROOT}`; one fence comment (line 94) mentions `"$CLAUDE_PLUGIN_ROOT/..."` as a warning, not a path |
| 3 | Every shared/ reference resolves | PASS | 72 unique refs, 0 missing |
| 4 | Shipped-validators manifest | PASS | built sha256 `f21651d6…17d414` = line 77 `ci/linked/linked.py  # 2.16.0`; `--check`: `manifest current`, exit 0 |
| 5 | 2.15.0 upgrade path | PASS | 27 files seeded from `hitl--v2.15.0`; run 1: `+ installed ci/linked/linked.py`, `^ updated ci/first-pass/migrate_project.py (an older shipped version, unmodified)`, `24 identical, 3 installed, 1 updated, 0 kept`; all 28 files then byte-identical to the build; run 2 after appending a line to linked.py: `~ ci/linked/linked.py differs from the shipped version — KEPT yours` with a diff, edit present on disk |
| 6 | Stale-test cleanup | PASS | hash `d7e6a9ed…ee180a` of `36f85f1:ci/linked/test_linked.py` is line 37 of retired-tests.sha256 as `test_linked.py`; dev-update line 278 lists `ci/linked/test_linked.py`, line 288 loop includes `ci/linked` |
| 7 | `claude plugin validate` | PASS | `✔ Validation passed`, exit 0 |
| 8 | CHANGELOG 2.16.0 claims | PARTIAL | carriers: linked.py, linked-changes.md, dev-tdd/dev-apply-change/ops-deploy refusals, dev-conclude fold (`fold_before_partners` in workflow-steps.md, schema, linked.py), pinned LLD (dev-review-lld-adherence line 35), `change_id_prefix` (dev-start-change, pulse.py, team-pulse.md), `issues:` + `issue-repo` (pm-add-feature, pm-report-bug, qa-report-defect, dev-conclude), `link-sub` (dev-start-change). **Source-only:** the traceability gate (`ci/preflight/check_change.py`, see F3), `docs/linked-changes.md`, the design package, "40 tests … plus 7 gate tests" |
| 9 | `git status --short` after build | PASS | 24 modified + 2 untracked; every path maps to a file in `git diff --stat v2.15.0..36f85f1` (usage-guide.md = docs/usage-guide.md one-line add) or is the known `scripts/build.sh` edit; nothing stale |
| 10 | Fresh onboarding | PASS | init exit 0; `ci/linked/linked.py` installed (17769 bytes); `.gitignore` line 7 `.hitl/linked/`; `.claude/commands` = 19 entries, identical list to a v2.15.0 init |

## Findings

**F1. dev-tdd and ops-deploy never set `ROOT`, so their plugin fallback is dead.** Both fences read, verbatim:
`LINKED="ci/linked/linked.py"; [[ -f "$LINKED" ]] || LINKED="$ROOT/shared/ci/linked/linked.py"`
Neither skill contains `ROOT=` (grep count 0; dev-start-change and dev-retro do define it). In a plugin-onboarded repo that has not yet run `/hitl:dev-update` (no `ci/linked/`), the line resolves to `/shared/ci/linked/linked.py`; observed: `python3: can't open file '/shared/ci/linked/linked.py': [Errno 2]`, exit 2. Exit 2 is the "waiting on a partner" code, so dev-tdd's rule "stop on a non-zero exit, quoting its verdict line" stops the step quoting a Python error as the verdict. Mitigation: the sync in dev-update installs `ci/linked/linked.py` (check 5), after which the first branch is taken. Fix: add the same `ROOT=` line the other skills use, or drop the fallback and say "run /hitl:dev-update".

**F2. dev-start-change Step 6c and dev-apply-change call `python3 "$LINKED"` with `LINKED` set nowhere.** dev-apply-change line 51: "run `python3 "$LINKED" fetch <ref>` (`LINKED` resolves as in `${CLAUDE_PLUGIN_ROOT}/shared/linked-changes.md`)"; dev-start-change line 474: "`python3 "$LINKED" link-sub owner/docs#<epic> <this repo>#<N>`". `shared/linked-changes.md` has no assignment, only the prose "The script is `ci/linked/linked.py` in the repository, or `$ROOT/shared/ci/linked/linked.py` in the plugin." Observed with the variable unset: `python3: can't find '__main__' module in '<cwd>'`, exit 1. This is the only path that writes `linked_changes` and links a slice under its epic, so a fresh 2.16.0 user hits it on the first linked change. Fix: put the two-line resolver in linked-changes.md as a fence and have both skills quote it, or inline it.

**F3. The traceability-gate claim is source-only but the shipped doc presents it as a product-repo gate.** CHANGELOG: "the traceability gate finds the decision packet and the LLD in the docs partner's pull request". `check_change.py` lives at `ci/preflight/` in the platform repo, runs from `ci/workflows/traceability-check.yml` there, is not in the package (`shared/ci/` has no `preflight`), and `init-project.sh` does not copy it (fresh target has only first-pass and data-layer workflows). Yet the shipped `shared/linked-changes.md` row 26 reads "| the CI traceability gate | `check_change.py` | the decision packet and the LLD or ADR found in the `docs` partner's PR when none is local |". Either mark the row and the CHANGELOG line as platform-repo CI, or ship the gate.

No other findings. Checks 1, 3, 4, 5, 6, 7, 9 and 10 hold as run.
