# Upgrade review, round 3: HITL 2.14.0 (source 2de5aee, plugin release/2.x + uncommitted build.sh edit)

## Verdict

**Verified.** A fresh copy of the plugin repo builds against source 2de5aee with exit 0 and "Build complete", the reachability check is clean, the built generator is byte-identical to the source file at that commit, the built skill differs from source only by the build's standard plugin-root path rewrite on one line, plugin validate passes, and the changed-file list is the same 21 entries as round 2 with no new file.

Scratch: `/private/tmp/claude-501/-Users-Prasad-1-Projects-hitl-dev-platform/e2e18ebd-e633-40b2-8e01-d93500ee8242/scratchpad/ru3/plugin` (`<P>` below). Plugin copy diff before build: `scripts/build.sh` only (11 changed lines: team-pulse tools block + allowlist entry), branch `release/2.x`. Source HEAD `2de5aee fix(team-pulse): every number on the page links to its GitHub query (2.14.0 correctness review F1)`; source working tree clean for tools/team-pulse, ai/claude/skills/team-pulse, ai/shared/team-pulse.md and CHANGELOG.md.

## Checks

| # | Check | Command | Result | Output |
|---|-------|---------|--------|--------|
| 1 | Build | `cp -R hitl-claude-plugin <P>`; `bash scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform` | pass | `EXIT=0`; log line 216 `all shared/ references resolve`; line 217 `Build complete.`; no `MISSING`, no `Refusing`. plugin.json version `2.14.0`. |
| 2a | Built pulse.py identical to source at 2de5aee | `git show 2de5aee:tools/team-pulse/pulse.py \| cmp - shared/tools/team-pulse/pulse.py`; `shasum -a 256` both | pass | `pulse.py IDENTICAL to 2de5aee`; both hash `8e0af6832a10c14d…`. Directory holds `pulse.py` only. `python3 pulse.py --help` exit 0. |
| 2b | Built SKILL.md identical to source at 2de5aee | `git show 2de5aee:ai/claude/skills/team-pulse/SKILL.md \| cmp - skills/team-pulse/SKILL.md`; `diff` | pass, with one expected rewrite | Differs at line 30 only: source `` `shared/team-pulse.md` `` becomes `` `${CLAUDE_PLUGIN_ROOT}/shared/team-pulse.md` ``. That is the "Normalizing path references" sed at scripts/build.sh:499, applied to every skill (37 built skills carry the same `${CLAUDE_PLUGIN_ROOT}/shared/` rewrite); the round-2 build showed the identical one-line diff. With line 30 removed from both, `rest IDENTICAL`. The new `ROOT=` line (40) carries the 2de5aee fix (the `os.path.isfile(... plugin.json)` filter) verbatim. |
| 2c | Built shared/team-pulse.md identical to source | `git show 2de5aee:ai/shared/team-pulse.md \| cmp - shared/team-pulse.md` | pass | `team-pulse.md IDENTICAL`. |
| 3 | Plugin validate | `claude plugin validate <P>` | pass | `✔ Validation passed`. |
| 4 | Changed-file list equals round 2 | `git status --short \| wc -l` and list | pass | 21 entries, the same set as round 2: 17 modified (plugin.json, CHANGELOG.md, scripts/build.sh, check_skips.py, gen_change.py, retired-tests.sha256, shipped-validators.sha256, getting-started.md, skip-record.md, change-context.schema.yaml, usage-guide.md, dev-impact-brief, dev-start-change, dev-switch-context, dev-update, dev-verification-review, help) + 4 untracked (skipped_line.py, shared/team-pulse.md, shared/tools/team-pulse/, skills/team-pulse/). No new file. |

## Round-1 findings, standing disposition

1. **stops → fixed (round 2)** — Claim: `build.sh refuses to build 2.14.0 because shared/team-pulse.md is named by the team-pulse skill but is not in the SHARED_PROSE allowlist.` Still fixed at 2de5aee: build exits 0, file present and identical to source.

2. **minor → accepted** — Claim: `shipped-validators.sha256 carries a second 2.14.0 hash for skipped_line.py (0025330c…) that matches pre-release commit bff41fd, not any shipped build.` Unchanged.

3. **decide → accepted** — Claim: `The build only reaches the reachability check with the uncommitted build.sh team-pulse block; release/2.x as committed does not ship pulse.py.` Unchanged; `scripts/build.sh` still shows ` M` in the plugin working copy. Per the lead, release.sh commits the plugin working tree as the build commit.

4. **minor → accepted** — Claim: `retired-tests.sha256 lists two hashes for test_skipped_line.py, one of which (d54444cf…) is not the 66304b1 file.` Unchanged.

## New findings

None. The only byte difference between source and package in the team-pulse files is the build's standard path normalization on SKILL.md line 30, which is how the reference resolves inside an installed plugin. Nothing failed.
