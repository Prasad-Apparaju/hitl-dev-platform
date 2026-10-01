# GH-142 release 2.15.0, upgrade lens, round 2

**Verdict: PASS.** All three round-1 findings are fixed or accepted-unchanged, and the build from de692d0 is whole. No new findings.

Reviewed: source /Users/Prasad_1/Projects/hitl-dev-platform at de692d023ec23d580fe54a9b34988bbc9dbfa26b. Plugin repo copied to a scratch directory with the uncommitted scripts/build.sh edit kept, built with `bash scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform` (stdout and stderr to a log file, exit 0).

## Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Build completes; guard clean; reachability passes; plugin.json 2.15.0; the two files changed in de692d0 hash to 2.15.0 lines; hashes --check passes; built schema identical to template | PASS | Build log: `plugin validation passed`, `Packaging check: no test/conftest/bytecode under shared/`, `all shared/ references resolve`, `Build complete.`; no `SOURCE PATH`, `MISSING`, `Refusing` or `FAILED` lines. `.claude-plugin/plugin.json` line 9 `"version": "2.15.0"`. `shasum -a 256` of built `shared/ci/data-layer/check_data_layer.py` = `4919905c...e08434`, listed at shipped-validators.sha256 line 74 `# 2.15.0`; `data-layer.schema.yaml` = `e32e8b50...591bd`, line 75 `# 2.15.0`. `python3 tools/scripts/shipped-validators-hashes.py --check` prints `manifest current: every synced validator in the tree is listed`, exit 0. `cmp shared/ci/data-layer/data-layer.schema.yaml shared/templates/data-layer/data-layer.schema.yaml` identical. Remaining `ai/` references in built skills are exactly the allowlisted set (start-change/SKILL.md, plugin/plugin.json, workflows.yaml, check-platform-ready.sh, agents/, plus the bare directory names `ai/claude/` and `ai/shared/` in prose). 40 skill files carry `${CLAUDE_PLUGIN_ROOT}` (HEAD had 39; the new dev-map-data-layer is the +1). |
| 2 | F1: CHANGELOG count equals pytest | PASS | CHANGELOG 2.15.0 section: `104 tests by mutation`. `python3 -m pytest ci/data-layer tools/data-layer -q` in the source repo: `104 passed in 12.84s`. |
| 3 | F2/F3: fresh init installs map-data-layer symlink, prints the data-layer line, installed validator says absent | PASS | `bash tools/scripts/init-project.sh <tmp> --tool claude --name fresh` exit 0. Output line 21: `✓ ci/data-layer/ + tools/data-layer/ (data-layer validator, scorecard, adapters) + .github/workflows/data-layer-check.yml`. `<tmp>/.claude/commands/map-data-layer.md` is a symlink to `ai/claude/map-data-layer/SKILL.md`. In `<tmp>`: `python3 ci/data-layer/check_data_layer.py` prints `data layer: absent (docs/02-design/data)`, exit 0. |
| 4 | de692d0 hash of ci/data-layer/test_check_data_layer.py is in the built retired-tests.sha256 by basename | PASS | `git diff --stat d6a37fe de692d0 -- ci/data-layer/test_check_data_layer.py` = 2 insertions. Hash `d6d75703...eefb0f` found at built `shared/ci/retired-tests.sha256` line 36 as `test_check_data_layer.py`. |
| 5 | `claude plugin validate <scratch>` passes; post-build git status lists only the release's files | PASS | `✔ Validation passed`. `git status --short`: M plugin.json, CHANGELOG.md, scripts/build.sh, shared/ci/first-pass/migrate_project.py, shared/ci/retired-tests.sha256, shared/ci/shipped-validators.sha256, shared/getting-started.md, shared/usage-guide.md, skills/dev-check-conventions, dev-start-brownfield, dev-update, help SKILL.md; ?? shared/ci-workflows/data-layer-check.yml, shared/ci/data-layer/, shared/data-layer.md, shared/templates/data-layer/, shared/tools/data-layer/, skills/dev-map-data-layer/. Same set as the plugin working tree before the build plus plugin.json. |

## Round-1 findings

**F1** — "CHANGELOG 2.15.0 says \"101 tests by mutation\"; pytest over ci/data-layer and tools/data-layer at d6a37fe prints \"102 passed\". Source-only claim, off by one."
Status: **fixed**. CHANGELOG now reads 104; pytest prints 104 passed (check 2).

**F2** — "init-project.sh's hard-coded .claude/commands symlink list (lines 348-350) omits map-data-layer: 47 symlinks against 60 shipped skills."
Status: **fixed**. `tools/scripts/init-project.sh` line 350 now ends `adversarial-review verification-review map-data-layer; do`; a fresh init creates 48 command symlinks including `map-data-layer.md` (check 3). `git diff v2.14.0..de692d0 -- tools/scripts/init-project.sh` shows this one-word addition as the only change to the list. The other 12 skills without a symlink (help, update, validate, preferences, retro, review-security, start-change, switch-context, ta-approve, draft-for, skills/agentic-intake, skills/team-pulse) were already absent in 2.14.0 and are not part of the claim.

**F3** — "init-project.sh \"Next steps\" prints items 1 and 3 with no 2."
Status: **accepted-unchanged**. Output lines 32-34 still print `1. Edit CLAUDE.md` then `3. Edit docs/system-manifest.yaml`. The diff since v2.14.0 does not touch this block.

## New findings

None.

Note for the release owner, not a finding: build.sh dies silently if its stdout is piped into a truncating reader (for example `| head`). SIGPIPE stops it after the skill sync and before path normalization, leaving raw `ai/shared/...` paths in the working tree while the pipeline exits 0. I hit this during the review and rebuilt to a log file; the evidence above is from the clean run. Worth remembering when wrapping the build in a one-liner.
