# HITL 2.0 — Validation Guide (for an independent reviewer / Codex)

**Purpose:** give an independent agent (Codex) everything needed to verify and validate the HITL 2.0 release without prior context. It maps each capability to its **requirement**, its **design**, and the **test or check** that proves it, then lists the exact commands to run and what a pass looks like.

**Scope of 2.0:** the workflow-model redesign (numberless catalog, profiles/tags, phase-ribbon breadcrumb, generated command-map, name citations) plus three enhancement fixes: manifest drift checker (#16 gap 1), brownfield PRD initialization (#18), and the docs-only workflow + stale-change-file gate (#19).

**Run everything from the repo root:** `/Users/Prasad_1/Projects/hitl-dev-platform` (paths below are repo-relative).

---

## 1. Run these checks first (machine-verifiable, must all pass)

| # | Command | Pass criterion |
|---|---------|----------------|
| 1 | `python3 tools/workflow-catalog/derive.py verify` | Prints `VERIFY OK: ... spine->development, brownfield->brownfield, docs->docs, greenfield->prd, migration->migration, migration_review->migration_review`. Proves the numberless catalog reproduces the runtime `ai/shared/workflows.yaml` losslessly. |
| 2 | `python3 -m pytest tools/workflow-catalog/test_derive.py ci/skill-lint/test_check_skills.py ci/manifest-drift/test_check_manifest_drift.py -q` | `24 passed`. Deriver (12), skill-lint (8), drift-checker (4). |
| 3 | `python3 ci/skill-lint/check_skills.py --root ai/claude` | Exit 0; `51/51 files pass all hard gates` (8 advisory warnings are acceptable). |
| 4 | `bash ci/breadcrumb/run_matrix.sh` | `RESULT: 238 passed, 0 failed (of 238 assertions)`. |
| 5 | `python3 tools/workflow-catalog/derive.py command-map \| diff - docs/command-map.generated.md` | No output (the checked-in command-map is not stale). |

If any of 1–5 fails, that is a real regression — report it. All five pass on the current `main`.

---

## 2. Requirements → Design → Test traceability

Verify the chain is intact: each capability has a requirement, a design, and something that proves it.

| Capability | Requirement | Design | Test / check |
|---|---|---|---|
| **Numberless identity** (steps keyed by stable `key`+name+phase, not global position) | `docs/design/workflow-model/00-requirements.md` (G1), `docs/01-product/prd.md` FR-1 | `docs/design/workflow-model/01-design.md` §4; `tools/workflow-catalog/catalog.yaml` | Check 1 (derive verify) + `tools/workflow-catalog/test_derive.py` |
| **Structure separated from execution** (generated command-map) | 00-requirements G2; PRD FR-3 | `docs/command-map.generated.md` (generated) | Check 5 (no drift) |
| **Phase-ribbon breadcrumb** (numberless, phase ✓/◐/·) | 00-requirements; PRD FR-4 | `docs/design/workflow-model/02-rollout.md`; `ai/claude/hooks/_steps.sh` | Check 4 (`ci/breadcrumb/run_matrix.sh`, 238 assertions; see `ci/breadcrumb/README.md`) |
| **Three-tier taxonomy** (6 workflows / 6 profiles / 5 tags) | PRD §4 | `docs/design/workflow-model/01-design.md` §4 | Profiles/tags resolve in `test_derive.py`; workflows in Check 1 |
| **Skill quality gates** | `docs/design/workflow-model/04-harness-acceptance-criteria.md` Part A | Part A rules | Check 3 (`ci/skill-lint/check_skills.py`) + `test_check_skills.py` |
| **Manifest drift checker (#16)** | Plugin issue #16 (gap 1); `docs/business/...` n/a | `ci/manifest-drift/check_manifest_drift.py` (self-derives scan roots from the manifest) | Check 2 (`test_check_manifest_drift.py`); CI template `ci/workflows/convention-check.yml` |
| **Docs-only workflow (#19)** | Plugin issue #19; PRD §4 | `docs/design/workflow-model/01-design.md` §4 (Docs bullet); catalog `docs:` block; `ai/claude/start-change/SKILL.md` classifier | Check 1 (`docs->docs` lossless) + Check 4 (docs position cases) |
| **Stale-change-file gate (#19)** | Plugin issue #19 | `ai/claude/hooks/_steps.sh` (`hitl_change_active` treats `status: merged` as inactive) | Check 4 (the `merged/inactive` case in `run_matrix.sh`) |
| **Brownfield PRD init (#18)** | Plugin issue #18; PRD FR-18 | `ai/claude/start-brownfield/SKILL.md` Step 8; `ai/claude/pm/add-feature`, `pm/design-feature`; 10 read-only PM/QA skills | **Review-only** (prose skills, no automated test) — see §3 |
| **Traceability chain at merge** | PRD FR-13 | `ai/claude/architect/verify-traceability` | CI template `ci/workflows/traceability-check.yml` |

---

## 3. Review-only validation (no automated test; read and reason)

These changes are skill prose (instructions the AI follows), so they cannot be unit-tested. Validate by reading the files and confirming the logic is sound and internally consistent.

**#18 — brownfield PRD initialization.** Confirm:
- `ai/claude/start-brownfield/SKILL.md` Step 8 initializes `docs/01-product/prd.md` from the template (personas + format, explicitly **not** back-filled features).
- `ai/claude/pm/add-feature/SKILL.md` and `ai/claude/pm/design-feature/SKILL.md` each have a "First-run establishment" block that creates the PRD if absent before writing the first requirement.
- The 10 read-only skills (`pm/prioritize`, `pm/review-progress`, `pm/enhance-feature`, `pm/prep-demo`, `pm/review-scope-change`, `pm/answer-questions`, `pm/update-requirement`, `qa/plan-tests`, `qa/review-tests`, `qa/verify-quality`) each contain the guard `No product requirements exist yet` and stop rather than proceeding on an empty PRD.
- `docs/01-product/prd.md` FR-18 describes this behavior.

**#19 classifier routing.** In `ai/claude/start-change/SKILL.md` Step 3, confirm the `docs` workflow is chosen only when a change touches **nothing but docs**, and a mixed docs+code change stays on the `development` spine.

**#16 graceful degradation.** In `ai/claude/check-conventions/SKILL.md`, confirm the drift check reports `SKIPPED` (not passed) when the checker is absent.

---

## 4. Optional: exercise the fixed behaviors directly

**Drift checker self-derivation (#16)** — prove it adapts to a non-`app/` layout:
```bash
tmp=$(mktemp -d); mkdir -p "$tmp/backend/services" "$tmp/docs"
printf 'def a(): pass\n' > "$tmp/backend/services/auth.py"
printf 'def b(): pass\n' > "$tmp/backend/services/orphan.py"
printf 'domains:\n  services:\n    files:\n      - backend/services/auth.py\n' > "$tmp/docs/system-manifest.yaml"
( cd "$tmp" && python3 /Users/Prasad_1/Projects/hitl-dev-platform/ci/manifest-drift/check_manifest_drift.py )
# Expect: WARNING listing backend/services/orphan.py (an app/-only default would have missed it)
```

**Merged change is inactive (#19)** — the gate must force fresh intake:
```bash
grep -A6 'hitl_change_active()' ai/claude/hooks/_steps.sh
# Confirm: returns non-active when top-level `status: merged`.
```

---

## 5. What "validated" means

- **Sections 1 (all five checks green)** = the machine-verifiable core of 2.0 is intact.
- **Section 3 (review-only checks confirmed)** = the prose-level fixes are logically sound.
- Report any check that fails, any traceability row where the design or test is missing, and any skill guard that is absent or contradicts its design.

**Known non-blocking items** (do not report as failures): 8 advisory skill-lint warnings; skipped steps render with the same `·` glyph as open steps (matrix-locked, deliberate); MCP write-tool gating is a documented gap. The `.github/workflows/` gates are shipped as templates in `ci/workflows/`, not yet installed on GitHub — the checks in §1 are the source of truth.
