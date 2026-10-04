# Readable Test Scenarios: Implementation Plan

> Status: **draft v1 (2026-10-04)**. Build order for FR-36 from [`03-lld.md`](03-lld.md). All three
> requirement slices are built in one release because the validator (slice 3) is what makes the
> file (slice 1) and the people-in-the-loop promises (slice 2) true; shipping the file without the
> check would re-create the defect this fixes in a new place.

## Phases

| Phase | What | Files | Proven by |
|---|---|---|---|
| A. Shapes | Shared rules prose, file template, schema fields, registry field, plain-English ceiling row | `ai/shared/test-scenarios.md`, `ai/shared/templates/test-scenarios-template.md`, `ai/shared/templates/change-context.schema.yaml`, `ai/shared/templates/test-registry-template.yaml`, `ai/shared/plain-english.md` | W-7 to W-10 |
| B. Validator | `check_scenarios.py` and its tests | `ci/test-scenarios/` | Section 1 of the test plan, all 35 cases |
| C. Skills | Edits to plan-tests, tdd, review-tests, verify-quality; the new `qa/scenarios` skill | `ai/claude/qa/*/SKILL.md`, `ai/claude/tdd/SKILL.md` | W-1, W-11 to W-13, skill-lint, plain-English lint |
| D. Install and sync | The seven places in LLD section 9, CI template, plugin.json | `tools/scripts/init-project.sh`, two start-* skills, `migrate_project.py`, `shipped-validators-hashes.py`, `ci/workflows/test-scenarios-check.yml`, `plugin.json`, plugin repo `build.sh` | W-2 to W-6 |
| E. Documents | Role guides, README, PRD FR-5, CHANGELOG | `docs/roles/*.md`, `README.md`, `docs/01-product/prd.md`, `CHANGELOG.md` | Doc checks: paths exist, no double-brace placeholders, no line-break tags |
| F. Gates | The full gate set | `docs/releasing.md` step 4 commands plus `scripts/build.sh` in the plugin repo | All green |
| G. Validation review | One clean-context agent, checklist from the test plan section 3, runs the validator on fixtures and reads every edited skill | One page, verdict |
| H. Sandbox run | Test plan section 3 by hand, in a `CLAUDE_CONFIG_DIR` sandbox | Owner's call; needed before release, not before commit |

Phases A, B and C run in parallel once A's shapes are fixed (they are, in the LLD). D and E after C.
F after D and E. G after F. Release is a separate decision: this plan ends at a committed, built,
gate-green tree on `main`; `docs/releasing.md` takes it from there as 2.17.0 (behaviour changes:
a new skill, a new validator, new record fields).

## Not in this build

- The per-change block (#112) as an invitation surface; the issue comment is used until it ships.
- Reading `scenarios` from the registry in impact analysis.
- Any Codex-side change (not maintained).
- Back-filling scenarios for shipped changes.
