# Upgrade review, round 2: HITL 2.14.0 (source 66304b1, plugin release/2.x + uncommitted build.sh edit)

## Verdict

**Verified.** With `team-pulse.md` on the SHARED_PROSE allowlist, `bash scripts/build.sh` exits 0 with "Build complete", every shared/ and skills/ reference in the package resolves, the stale sweep removed nothing, plugin validate passes, and the changed-file list is round 1's twenty entries plus `shared/team-pulse.md`.

Scratch: `/private/tmp/claude-501/-Users-Prasad-1-Projects-hitl-dev-platform/e2e18ebd-e633-40b2-8e01-d93500ee8242/scratchpad/ru2/plugin` (`<P>` below), a fresh copy. Build log at `../build.log`. Only diff in the copy before building: `scripts/build.sh` (team-pulse tools block + `SHARED_PROSE=(... next-step.md team-pulse.md)`). Source HEAD `66304b1`, unchanged.

## Checks

| # | Check | Command | Result | Output |
|---|-------|---------|--------|--------|
| 1 | Build | `cp -R hitl-claude-plugin <P>`; `git status --short` = ` M scripts/build.sh`; `bash scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform` | pass | `EXIT=0`; log line 217 `Build complete.`; reachability check prints `all shared/ references resolve`; no `MISSING`, no `Refusing`. plugin.json version `2.14.0`. `grep -rc "SOURCE PATH"` non-zero only in `scripts/build.sh:1` (script text, not shipped). |
| 2 | team-pulse.md ships | `test -f shared/team-pulse.md`; `cmp` against `ai/shared/team-pulse.md` | pass | `OK shared/team-pulse.md`; "Syncing shared prose" lists it eighth; `team-pulse.md identical to source`. |
| 3 | Team Pulse skill and generator | `test -f skills/team-pulse/SKILL.md`; `test -f shared/tools/team-pulse/pulse.py`; `ls shared/tools/team-pulse/`; `python3 "$ROOT/shared/tools/team-pulse/pulse.py" --help` | pass | Both `OK`; directory holds `pulse.py` only (no tests); `--help` exit 0. |
| 4 | Every shared/ and skills/ reference resolves | `grep -rhoE 'shared/[A-Za-z0-9_./-]+' skills agents commands \| sed ... \| sort -u` then `test -e` each; same for `skills/<name>/SKILL.md` | pass | 59 unique shared/ refs, 0 missing (round 1: 1 missing). 7 unique skills/ refs, 0 missing. |
| 5 | Stale sweep deleted nothing else | `ls shared/*.md`; `git status --short \| grep '^ D'` | pass | 14 top-level shared/*.md present = 8 SHARED_PROSE (challenge-stance, verification-review, skip-record, personas, plain-english, issue-hygiene, next-step, team-pulse) + 6 SHARED_DOCS (getting-started, command-map, usage-guide, workflow-prd, workflow-brownfield, workflow-migration). `none deleted`; no tracked file shows as `D`. |
| 6 | Plugin validate | `claude plugin validate <P>` | pass | `✔ Validation passed` (also inside build.sh). |
| 7 | Changed-file list vs round 1 | `git status --short \| wc -l` and list | pass | 21 entries: the same 17 modified and 3 untracked as round 1 (plugin.json, CHANGELOG.md, scripts/build.sh, check_skips.py, gen_change.py, retired-tests.sha256, shipped-validators.sha256, getting-started.md, skip-record.md, change-context.schema.yaml, usage-guide.md, dev-impact-brief, dev-start-change, dev-switch-context, dev-update, dev-verification-review, help; skipped_line.py, shared/tools/team-pulse/, skills/team-pulse/) plus one new untracked `?? shared/team-pulse.md`. Nothing outside the release. |

Not rerun this round (source unchanged, checks read files the allowlist fix does not touch): Step 6b apply call, manifest hashes, the 2.13.0 migrate_project path, retired-tests entry. Round-1 results stand.

## Round-1 findings, disposition

1. **stops → fixed** — Claim: `build.sh refuses to build 2.14.0 because shared/team-pulse.md is named by the team-pulse skill but is not in the SHARED_PROSE allowlist.` Evidence now: `SHARED_PROSE` at scripts/build.sh:440 ends with `team-pulse.md`; build exits 0; file present and byte-identical to source; `shared/usage-guide.md` link `[team-pulse.md](team-pulse.md)` resolves.

2. **minor → accepted** — Claim: `shipped-validators.sha256 carries a second 2.14.0 hash for skipped_line.py (0025330c…) that matches pre-release commit bff41fd, not any shipped build.` Unchanged; accepted by the lead as minor.

3. **decide → accepted** — Claim: `The build only reaches the reachability check with the uncommitted build.sh team-pulse block; release/2.x as committed does not ship pulse.py.` Lead's disposition: release.sh commits the plugin working tree as the build commit, as 2.13.0's allowlist edit did. Still uncommitted in the working copy at review time (`M scripts/build.sh`); the release commit must include it.

4. **minor → accepted** — Claim: `retired-tests.sha256 lists two hashes for test_skipped_line.py, one of which (d54444cf…) is not the 66304b1 file.` Unchanged; accepted by the lead as minor.

No new findings. Nothing failed.
