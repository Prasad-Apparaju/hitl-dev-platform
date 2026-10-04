# GH-149 release 2.17.0, round 2 (correctness + upgrade, one pass)

Verdict: verified. All four round-1 claims are fixed at 5e298a6; the CI template behaves as the changelog now says on four fixture records; gates green; no new blocking findings.

Reviewed: /Users/Prasad_1/Projects/hitl-dev-platform at 5e298a68d4d9102b1f4d3d645d1fdd545de9aefb (`git rev-parse HEAD`). Plugin repo /Users/Prasad_1/Projects/hitl-claude-plugin on release/2.x at ae25853, read only. Neither repo modified apart from this file; fixtures under the session scratchpad (`r2-ci/`).

## Round-1 claims (verbatim) and status

- U1: "The update skill syncs the two new files but never stages them.", **fixed**. ai/claude/update/SKILL.md:288 loop now reads `... ci/linked ci/test-scenarios .github/workflows/first-pass-check.yml .github/workflows/data-layer-check.yml .github/workflows/test-scenarios-check.yml; do`. Both paths present.
- U2: "The Upgrading paragraph is true for the skills and not for CI.", **fixed**. CHANGELOG `### Upgrading` now says: "The new CI check runs in report-only mode on a change record from before 2.17.0 that names no scenarios file, so an open pull request does not go red; run test review once and the normal check applies." and "`/hitl:dev-update` installs and stages the validator and the CI template." The template carries it: ci/workflows/test-scenarios-check.yml picks `draft` when `tests.scenarios_file` is absent and `hitl_version` is below 2.17, else `review`, and prints a one-line notice on the draft path. Verified by running the extracted block (check 2).
- C1: "The changelog says the check \"is installed and kept current the same way as the First Pass checker\" and every skill resolves it at `$ROOT/shared/ci/test-scenarios/check_scenarios.py` and reads `shared/test-scenarios.md`.", **fixed**. Plugin repo: `git log --oneline -1 -- scripts/build.sh` = `ae25853 build: ship ci/test-scenarios, test-scenarios.md and test-scenarios-check.yml (FR-36, source #148)`; `git diff --quiet HEAD -- scripts/build.sh` exit 0. build.sh:438-441 copies the workflow to shared/ci-workflows, 445-450 copies the validator (excluding tests and conftest) to shared/ci/test-scenarios, 493 lists test-scenarios.md in SHARED_PROSE.
- C2: "`ci/test-scenarios/check_scenarios.py:491` calls `re.split(r\"[\s,(]\", hdr_status, 1)`.", **fixed**. Line 491 now `re.split(r"[\s,(]", hdr_status, maxsplit=1)`; the only `re.split` in the file. `python3 -m pytest ci/test-scenarios -q`: 54 passed in 0.68s, no warnings summary. `python3 -W error::DeprecationWarning ci/test-scenarios/check_scenarios.py --help` exit 0.
- U3 (Minor, pre-existing): "`init-project.sh` has no `--help`.", not addressed, by design; round 1 marked it pre-existing and not a 2.17.0 change. Not counted.

## Checks

1. U1: `grep -n "ci/test-scenarios" ai/claude/update/SKILL.md` gives lines 278 (retired-test list) and 288 (git add loop with both new paths). PASS.
2. U2: run block extracted from the template between `run: |` and the end of the step, relative validator path replaced with the absolute source path, executed in four scratch repos:
   - (a) `hitl_version: "2.16.1"`, no `scenarios_file`: prints "Change record predates 2.17.0 and names no scenarios file: reporting only (draft stage) until test review writes it.", `[warn] REVIEW_PENDING`, exit 0. PASS.
   - (b) `hitl_version: "2.17.0"`, no `scenarios_file`: `[BLOCK] FILE_MISSING: the change record names no tests.scenarios_file`, exit 2. PASS.
   - (c) `hitl_version: "2.16.1"`, `scenarios_file: .../x.md` absent: no draft notice, `[BLOCK] FILE_MISSING: scenarios file does not exist`, exit 2. PASS.
   - (d) `hitl_version: "2.17.0"`, file written from ai/shared/templates/test-scenarios-template.md with one scenario `SC-GH-123-01`, `Test: tests/cart.spec.ts`, review `PM: done`; record `scenario_review: {status: done, by: Dana, ts: ...}`, `files: [tests/cart.spec.ts]`; spec names `SC_GH_123_01` and cites `// SC-GH-123-01`: `Scenarios: 1 scenarios, 1 cited, 0 deferred, review done.`, exit 0. Same file with `hitl_version: "2.16.1"`: identical review-stage result, exit 0. PASS.
   Fixture note: `tests.files` is a list of path strings; a first attempt with mapping entries was dropped by the validator and produced SCENARIO_UNCITED. That is the fixture, not the fix.
3. C1: see claim text. `grep -n "test-scenarios" scripts/build.sh` gives 438, 440, 441, 444-450, 493. PASS.
4. C2: `grep -n "maxsplit=1"` hits line 491 only; pytest and `-W error` as above. PASS.
5. Scope: `git diff --stat df217b2 5e298a6` lists CHANGELOG.md, ai/claude/update/SKILL.md, ci/shipped-validators.sha256, ci/test-scenarios/check_scenarios.py, ci/workflows/test-scenarios-check.yml; 5 files, +12/-5. `shasum -a 256 ci/test-scenarios/check_scenarios.py` = ce2a5c6e...e4e, equal to ci/shipped-validators.sha256:80 `# 2.17.0`; commit 5e298a6 replaced the earlier d9d4a0ce line for the same unreleased version rather than adding one, which is right for a version not yet published. `python3 -m pytest ci/wiring -q`: 435 passed. `python3 ci/skill-lint/check_skills.py`: 66/66 pass, 0 failures, 0 warnings. PASS.

## New findings

None blocking. Two observations:

- The built tree in the plugin working directory predates these fixes: `shared/ci/test-scenarios/check_scenarios.py` hashes d9d4a0ce (the pre-C2 validator), `shared/ci/shipped-validators.sha256:80` lists that hash, the built CI template has no report-only block, and the built dev-update loop lacks the new paths. Expected, since nothing has been rebuilt since round 1; the release must run build.sh from 5e298a6 before committing the 2.17.0 build, or the shipped plugin carries none of the round-1 fixes.
- The template's version test treats a record with no `hitl_version` as pre-2.17.0 (defaults to `0`). With no `scenarios_file` such a record gets the report-only path. Reasonable for old records; a 2.17.0 record always carries the field per the schema, so no gap in practice. Low.
