# HITL 2.0 — Validation Guide (for an independent reviewer / Codex)

**Purpose:** give an independent agent (Codex) everything needed to verify and validate the HITL 2.0 release without prior context. It maps each capability to its **requirement**, its **design**, and the **test or check** that proves it, then lists the exact commands to run and what a pass looks like.

**Scope of 2.0:** the workflow-model redesign (numberless catalog, profiles/tags, phase-ribbon breadcrumb, generated command-map, name citations) plus three enhancement fixes: manifest drift checker (#16 gap 1), brownfield PRD initialization (#18), and the docs-only workflow + stale-change-file gate (#19).

**Validation splits into two parts, validated independently:**
- **Part 1 (§1–5): the main HITL source** (`hitl-dev-platform`) — proves the requirements, design, and tests are correct. Run from the repo root `/Users/Prasad_1/Projects/hitl-dev-platform`.
- **Part 2 (§6): the built plugin** (`hitl-claude-plugin`) — proves `build.sh` faithfully carries the validated source into the shipped artifact. Run from the plugin repo root `/Users/Prasad_1/Projects/hitl-claude-plugin`.

Part 1 answers "is the source correct?"; Part 2 answers "does the build match the source?". The plugin does not carry the dev-platform test suite (deriver, matrix, pytest all live in `hitl-dev-platform`), so Part 2 checks **build fidelity and structural validity**, not unit tests.

---

## 0. Prerequisites (read before running Part 1)

The Python checks in §1 need a `python3` that has **PyYAML** and **pytest** installed — the same dependencies the CI workflows install (`ci/workflows/*.yml` all run `pip install pyyaml [pytest]`). Use a virtualenv or conda Python that has them, or run `pip install pyyaml pytest` first.

The bare macOS system Python (`/Library/Developer/CommandLineTools/usr/bin/python3`) ships **neither** and will fail with `ModuleNotFoundError: No module named 'yaml'` / `No module named pytest`. That is an environment gap, **not** a release defect — verify the interpreter before concluding a check failed. `python3 -c "import yaml, pytest"` should exit cleanly before you start.

---

## 1. Run these checks first (machine-verifiable, must all pass) — Part 1, source

| # | Command | Pass criterion |
|---|---------|----------------|
| 1 | `python3 tools/workflow-catalog/derive.py verify` | Prints `VERIFY OK: ... spine->development, brownfield->brownfield, docs->docs, greenfield->prd, migration->migration, migration_review->migration_review, platform->platform`. Proves the numberless catalog reproduces the runtime `ai/shared/workflows.yaml` losslessly. |
| 2 | `python3 -m pytest tools/workflow-catalog/test_derive.py ci/skill-lint/test_check_skills.py ci/manifest-drift/test_check_manifest_drift.py ci/hooks -q` | `99 passed`. Deriver (12), skill-lint (8), drift-checker (4), enforcement hooks (75: intake gate #20 = 14, platform gate + chip #21 = 57, breadcrumb renderers = 4). |
| 3 | `python3 ci/skill-lint/check_skills.py --root ai/claude` | Exit 0; `52/52 files pass all hard gates` (8 advisory warnings are acceptable). |
| 4 | `bash ci/breadcrumb/run_matrix.sh` | `RESULT: 270 passed, 0 failed (of 270 assertions)`. |
| 5 | `python3 tools/workflow-catalog/derive.py command-map \| diff - docs/command-map.generated.md` | No output (the checked-in command-map is not stale). |

If any of 1–5 fails, that is a real regression — report it. All five pass on the current `main`.

---

## 2. Requirements → Design → Test traceability

Verify the chain is intact: each capability has a requirement, a design, and something that proves it.

| Capability | Requirement | Design | Test / check |
|---|---|---|---|
| **Numberless identity** (steps keyed by stable `key`+name+phase, not global position) | `docs/design/workflow-model/00-requirements.md` (G1), `docs/01-product/prd.md` FR-1 | `docs/design/workflow-model/01-design.md` §4; `tools/workflow-catalog/catalog.yaml` | Check 1 (derive verify) + `tools/workflow-catalog/test_derive.py` |
| **Structure separated from execution** (generated command-map) | 00-requirements G2; PRD FR-3 | `docs/command-map.generated.md` (generated) | Check 5 (no drift) |
| **Phase-ribbon breadcrumb** (numberless, phase ✓/◐/·) | 00-requirements; PRD FR-4 | `docs/design/workflow-model/02-rollout.md`; `ai/claude/hooks/_steps.sh` | Check 4 (`ci/breadcrumb/run_matrix.sh`, 270 assertions; see `ci/breadcrumb/README.md`) |
| **Three-tier taxonomy** (7 workflows / 6 profiles / 5 tags) | PRD §4 | `docs/design/workflow-model/01-design.md` §4 | Profiles/tags resolve in `test_derive.py`; workflows in Check 1 |
| **Platform-bootstrap workflow (#21)** (onboarded → delivery-ready: readiness register, generated roadmap, hard production-deploy gate) | Plugin issue #21; PRD FR-25 | `docs/design/platform-bootstrap/` (D1-D6 locked); catalog `platform:` block; `ai/shared/templates/platform-readiness-template.yaml`; `ai/claude/hooks/check-platform-ready.sh` | Check 1 (`platform->platform` lossless) + Check 2 (`ci/hooks/test_check_platform_ready.py`, 17 cases) + Check 4 (platform position cases) |
| **Skill quality gates** | `docs/design/workflow-model/04-harness-acceptance-criteria.md` Part A | Part A rules | Check 3 (`ci/skill-lint/check_skills.py`) + `test_check_skills.py` |
| **Manifest drift checker (#16)** | Plugin issue #16 (gap 1) | `ci/manifest-drift/check_manifest_drift.py` (self-derives scan roots from the manifest) | Check 2 (`test_check_manifest_drift.py`); CI template `ci/workflows/convention-check.yml` |
| **Docs-only workflow (#19)** | Plugin issue #19; PRD §4 | `docs/design/workflow-model/01-design.md` §4 (Docs bullet); catalog `docs:` block; `ai/claude/start-change/SKILL.md` classifier | Check 1 (`docs->docs` lossless) + Check 4 (docs position cases) |
| **Stale-change-file gate (#19)** | Plugin issue #19 | `ai/claude/hooks/_steps.sh` (`hitl_change_active` treats `status: merged` as inactive) | Check 4 (the `merged/inactive` case in `run_matrix.sh`) |
| **Brownfield PRD init (#18)** | Plugin issue #18; PRD FR-18 | `ai/claude/start-brownfield/SKILL.md` Step 8; `ai/claude/pm/add-feature`, `pm/design-feature`; 10 read-only PM/QA skills | **Review-only** (prose skills, no automated test) — see §3 |
| **Traceability chain at merge** | PRD FR-13 | `ai/claude/commands/architect/verify-traceability.md` | CI template `ci/workflows/traceability-check.yml` (runs `ci/preflight/check_change.py`) |

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

---

## 6. Part 2 — Validating the built plugin (`hitl-claude-plugin`)

The plugin is **generated** from `hitl-dev-platform` by `scripts/build.sh` (skill-dir remapping, `${CLAUDE_PLUGIN_ROOT}` path rewrites, `hooks.json` rewrites, asset copying). Part 1 proved the source; Part 2 proves the build carries it faithfully and is structurally valid. **Run these from the plugin repo root** (`/Users/Prasad_1/Projects/hitl-claude-plugin`), which sits beside `hitl-dev-platform`.

### 6.1 Build fidelity and structural validity (must pass)

| # | Command | Pass criterion |
|---|---------|----------------|
| 1 | `./scripts/build.sh` | Ends with `plugin validation passed` and `Build complete`. This regenerates from source and runs `claude plugin validate`. |
| 2 | `git status --porcelain \| sort > /tmp/a; ./scripts/build.sh >/dev/null; git status --porcelain \| sort > /tmp/b; diff /tmp/a /tmp/b && echo idempotent` | Prints `idempotent` — a second consecutive build changes the same file set, none new. The build is a stable, faithful transform of source. |
| 3 | `grep -rl 'ai/claude/hooks/' hooks/ \| wc -l` | `0` — no built hook script leaks a source-tree path (the plugin has no `hooks.json`; hooks are wired per-project at install time). |
| 4 | `python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])"` | `2.0.0`. |

### 6.2 2.0 assets present in the built artifact (must all exist)

Confirm each capability's shipped surface actually made it into the plugin:

| Capability | Check (from plugin root) | Expect |
|---|---|---|
| #19 docs workflow | `grep '^  docs:' shared/workflows.yaml` | present |
| #19 stale-file gate | `grep 'A merged change is done' hooks/_steps.sh` | present (the `status: merged` guard) |
| #16 drift checker shipped | `test -f shared/ci/manifest-drift/check_manifest_drift.py` | exists |
| #18 PRD template shipped | `test -f shared/templates/prd-template.md` | exists |
| #18 first-run establishment | `grep -l 'First-run establishment' skills/pm-add-feature/SKILL.md skills/pm-design-feature/SKILL.md` | both |
| #18 read-only guards | `grep -rl 'No product requirements exist yet' skills/ \| wc -l` | `10` |
| numberless catalog | `grep -c 'phase:' shared/workflows.yaml` | non-zero (per-step phases shipped) |

### 6.3 Source ↔ build parity spot-check

Confirm shipped files are faithful transforms of source. **`build.sh` deliberately rewrites source-tree paths in comments** (`ai/claude/...` → `${CLAUDE_PLUGIN_ROOT}/skills/...`), so a raw `diff` on a file that contains such a comment is *expected* to differ on those lines only — that is not corruption. Two checks:

```bash
# a) A file with no path references must match source exactly:
diff hooks/_steps.sh ../hitl-dev-platform/ai/claude/hooks/_steps.sh && echo "hooks/_steps.sh matches source"

# b) For a file that carries path comments, the ONLY differences must be those rewrites.
#    Strip the rewritten comment lines, then the remainder must match:
diff <(grep -v 'Canonical source:' shared/workflows.yaml) \
     <(grep -v 'Canonical source:' ../hitl-dev-platform/ai/shared/workflows.yaml) \
  && echo "workflows.yaml matches source (apart from expected path rewrites)"
```
Both should print their "matches source" line. If (b) shows any diff *other* than a `Canonical source:` comment, that is a real build defect.

### 6.4 What Part 2 does *not* need

The dev-platform test suite (derive verify, `run_matrix.sh`, pytest) validates the **source** and is not shipped in the plugin — do not look for it there. Part 2 is satisfied when 6.1–6.3 pass. Check the marketplace pin (`.claude-plugin/marketplace.json` `source.commit` on the plugin repo's `main`) to know which build customers actually receive — validating an unpinned build has zero effect on installed customers.
