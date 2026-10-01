# GH-143 release 2.16.0: round 3 validation review (correctness + upgrade)

**Verdict: PASS. No new findings. Ready to release.**

Reviewed: hitl-dev-platform at 39c3e2871b272505e9e71498c8844fe4496629ca. Plugin built in a scratch copy of hitl-claude-plugin (release/2.x with the uncommitted scripts/build.sh edit). Neither repo was modified.

## Carried claim

N1: "ai/claude/start-change/SKILL.md:474 Step 6c sets LINKED inline but never resolves ROOT in that command; ROOT only exists in the Step 6b fence at line 447."

**Status: fixed.** Commit 39c3e28 prepends the same `ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c ...)}"` resolver used by the Step 6b fence to the Step 6c inline command. Source line 474 and built `skills/dev-start-change/SKILL.md` line 474 carry the identical command (byte-equal on the extracted segment).

Run in an empty temp directory, fresh shell (`env -i HOME PATH CLAUDE_PLUGIN_ROOT=<scratch> bash --noprofile --norc`), command text taken verbatim from the built skill up to `python3 "$LINKED"`:

```
LINKED=<scratch>/shared/ci/linked/linked.py
python3 "$LINKED" --help   -> usage printed, exit 0
```

## Checks

1. N1 (above). Fence scan of the built `skills/` and `shared/` trees: zero bash fences and zero inline shell commands carry a bare `$CLAUDE_PLUGIN_ROOT` or `${CLAUDE_PLUGIN_ROOT}` outside a `${CLAUDE_PLUGIN_ROOT:-` fallback (comment lines that explain the fallback excluded). The only bare occurrences are prose file references such as `${CLAUDE_PLUGIN_ROOT}/shared/next-step.md`, which the build's path normalization emits by design and which nothing executes.
2. `python3 -m pytest ci/ tools/ -q` -> 1314 passed in 82s, exit 0.
   `python3 ci/skill-lint/check_skills.py` -> 65/65 files pass, 0 failures, 0 warnings, exit 0.
   `(cd tools/workflow-catalog && python3 derive.py verify)` -> VERIFY OK for all eight workflows, exit 0.
3. `cp -R hitl-claude-plugin <scratch>/plugin && bash scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform > build.log 2>&1` -> exit 0, "Build complete.", no error/warn/fail/traceback lines in build.log, `.claude-plugin/plugin.json` version 2.16.0.
   `python3 tools/scripts/shipped-validators-hashes.py --check` -> "manifest current", exit 0; the built `shared/ci/shipped-validators.sha256` is byte-equal to source `ci/shipped-validators.sha256` and lists `ci/linked/linked.py` under 2.16.0 with a hash matching the shipped file.
   `claude plugin validate <scratch>/plugin` -> Validation passed, exit 0.
   `git -C <scratch>/plugin status --short` -> the release's files only: plugin.json (version bump), CHANGELOG.md, scripts/build.sh (the pre-existing uncommitted edit), the shared/ and skills/ files the 2.16.0 changes touch, plus new `shared/ci/linked/` and `shared/linked-changes.md`. No stray files.
   Scratch vs the real plugin working tree differs only where the real tree has not yet been rebuilt from 39c3e28: version 2.15.0 -> 2.16.0, CHANGELOG, the hash manifest, linked-changes.md's gate-scope wording (round 1), and the Step 6c resolver in dev-start-change plus the round-1 fallback lines in dev-apply-change, dev-tdd, ops-deploy. Rebuilding the real tree before release will close that gap.
4. `git diff --stat b3bf007 39c3e28` -> exactly `ai/claude/start-change/SKILL.md | 2 +-`, one line changed.

## New findings

None.
