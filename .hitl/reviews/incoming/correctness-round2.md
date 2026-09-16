# Correctness review, round 2: HITL release 2.13.0 at `9998611`

Scope: round 1 verified `b5b1bed`. One fix landed since (`9998611`, "the shipped-validators manifest lists the built workflows.yaml hash"). This round checks that the fix does what it claims and nothing else moved. Commands ran from the worktree checkout of `9998611` (`git rev-parse HEAD` = `99986110a39804bc393f2ef54097a73393df1a19`); the main checkout is at the same commit and the two files under review hash identically in both.

## Checks

| # | Check | Command | Result | Deciding output |
|---|-------|---------|--------|-----------------|
| 1 | Only the fix changed | `git diff b5b1bed..9998611 --stat` | pass | `ci/shipped-validators.sha256 \| 1 +`, `tools/scripts/shipped-validators-hashes.py \| 19 ++++++++++++++++++-`; 2 files changed. Nothing under `.hitl/` in the range either. |
| 2a | `built_form()` does one replacement, nothing else | `git show 9998611 -- tools/scripts/shipped-validators-hashes.py` | pass | Body is `text.replace("ai/claude/dev-practices/", "${CLAUDE_PLUGIN_ROOT}/skills/dev-practices/")` on the utf-8 decode, re-encoded. No other transform. |
| 2b | `current()` adds the built hash for the non-Python file only | same diff; `sed -n '12,26p'` of the script | pass | Guard is `if not path.endswith(".py")`; `SOURCES` has exactly one non-`.py` entry, `ai/shared/workflows.yaml -> ci/first-pass/workflows.yaml`. Dedupes with `if (built, rel) not in res`. |
| 2c | Built-form hash is in the manifest on a `# 2.13.0` line | `python3 -c "...built_form(open('ai/shared/workflows.yaml','rb').read())..."`; `grep -n workflows.yaml ci/shipped-validators.sha256` | pass | Printed `191d6d02a42b80e7a80d1a3c87c2334c8c64d4739b6a6ba17c5ef4e1eaeb79af`; manifest line 60: `191d6d02...  ci/first-pass/workflows.yaml  # 2.13.0`. |
| 3a | Build's rewrite composes to the script's replacement | `sed -n '470,560p' hitl-claude-plugin/scripts/build.sh` | pass | Pass 1: `s\|ai/claude/dev-practices/\|skills/dev-practices/\|g`; pass 2: `s\|skills/dev-practices/\|${CLAUDE_PLUGIN_ROOT}/skills/dev-practices/\|g`. No other pass-1/2/3 pattern (`ai/shared/`, `shared/templates`, `skills/dev-`, `$VAR/shared/`, `CLAUDE_PLUGIN_ROOT`) occurs in `workflows.yaml` (grep exit 1). |
| 3b | `ai/claude/dev-practices/` is the only source path the build rewrites in the file | `grep -n "ai/claude/" ai/shared/workflows.yaml` | pass, with a note | 7 hits. Line 30 is the rewritten one. Lines 78, 97, 114, 127, 141, 154 are `# Canonical source: ai/claude/start-brownfield/…`, `start-migration`, `migrate/review-external-docs`, `start-change`, `start-from-prd`, `ops/plan-platform` comment lines. None match any build pattern, and the plugin's shipped copy shows them verbatim, so `built_form()` leaving them alone is correct. See point 2. |
| 3c | Byte-for-byte against a real build (beyond the checklist) | `shasum -a 256 hitl-claude-plugin/shared/workflows.yaml` (release/2.x, committed `efdad0c chore(release): build v2.12.1`, working tree clean for that file) | pass | `191d6d02a42b…79af`, identical to the manifest's 2.13.0 line. Source `ai/shared/workflows.yaml` hashes `2632228667…89cfda` (the 2.12.1 line) and last changed at `d59550e`, so 2.12.1 and 2.13.0 ship the same bytes. The plugin's uncommitted `build.sh` edit is one line in a skip-list `case` (drops an `ai/claude/ai/claude/` entry), not the rewrite block. |
| 4a | Manifest check | `python3 tools/scripts/shipped-validators-hashes.py --check` | pass | `manifest current: every synced validator in the tree is listed`, exit 0. |
| 4b | Full suites | `python3 -m pytest ci tools -q` | pass | `1119 passed, 6 skipped in 66.07s`. |
| 4c | Skill lint | `python3 ci/skill-lint/check_skills.py` | pass | `63/63 files pass all hard gates; 0 failures, 0 warnings`, exit 0. |
| 5 | Manifest matches dev-update install paths | `python3 -m pytest ci/wiring/test_shipped_validators_manifest.py -q -rs` | pass | In the worktree: `2 passed, 1 skipped` (skip: `plugin repo not checked out beside this one`, the build.sh-copies-manifest test). Re-run read-only against the main checkout's identical copy (`-p no:cacheprovider`, sibling plugin present): `3 passed`. |
| 5b | Version label is not load-bearing (beyond the checklist) | `grep -n … ci/first-pass/migrate_project.py` | pass | `_shipped_hashes` parses `line.split("#", 1)[0].split()`; match is `_sha256(dst) in shipped.get(rel, ())` (line 289). Hash-set membership per path; the `# version` comment is discarded. |

## Points

1. **minor**: the manifest's `# 2.13.0` line for `workflows.yaml` is also the built form every 2.12.1 install holds (same source bytes). The consumer ignores the label, so behaviour is right; the label just under-describes which releases the line covers. No change needed.
2. **minor**: six `# Canonical source: ai/claude/…` comment lines in `workflows.yaml` ship unrewritten and point at source-repo locations that do not exist in the installed plugin. Pre-existing, comments only, and correct for `built_form()` to leave alone since the build leaves them alone. Not part of this fix.
3. **minor**: `built_form()` mirrors `build.sh` by hand, and the automated test with the sibling plugin present only checks that `build.sh` copies the manifest, not that the mirrored rewrite still matches. Today the release runbook's build step compares them, and 3c confirms they match now. A cheap hardening would be for that test, when the sibling is present, to assert the manifest contains the sha256 of the plugin's `shared/workflows.yaml`. Optional.

The fix does what its commit message says, the manifest line matches a real build byte for byte, and nothing else in the range moved.

## Verdict

VERIFIED
