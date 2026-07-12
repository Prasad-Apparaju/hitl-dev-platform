# Changelog

All notable changes to the HITL plugin are documented here.

---

## [2.0.1] — 2026-07-11

### Fixed

**Intake gate: absolute paths never matched the bootstrap exemption, and out-of-project files
were wrongly blocked (issue #20).** `check-hitl-context.sh` classified paths after only stripping
a leading `./`, but Claude Code sends `tool_input.file_path` as an absolute path. Consequences:
the `.hitl/`/`.claude/` bootstrap exemption never fired (so intake itself could be blocked, the
exact chicken-and-egg it exists to prevent), and files outside the project (scratchpads under
`/tmp`, user-level config) were gated as if they were project source. Affected paths are now
normalized against the project root (`$CLAUDE_PROJECT_DIR`, falling back to the hook's working
directory): absolute paths inside the project are rewritten relative, symlinks are resolved on
both sides before the containment check, and paths outside the project are ignored — HITL
governs this project's files only. Regression suite: `ci/hooks/test_check_hitl_context.py`.
Also shipped on `release/1.x` as 1.0.31.

## [2.0.0] — 2026-07-10

Major version: the workflow model is a different mental model. Existing 1.x projects keep working (the change-file schema change is additive), but the identity, breadcrumb, and taxonomy are new, so it ships as a major. 1.x continues on `release/1.x` for critical fixes.

### Changed

**Numberless workflow model.** Steps are identified by a stable `key` + name + phase, never by global position. The runtime `workflows.yaml` is derived from a single numberless catalog (`tools/workflow-catalog/`), and the breadcrumb is a phase ribbon with no global `Step N / total` counter. Taxonomy is three tiers: 6 workflows, 6 profiles, 5 tags.

### Added

**Docs-only workflow (#19).** A documentation-only change gets its own 6-step spine (issue → scope → draft → domain-routed review → reconcile → merge) instead of owing the full delivery trail or bypassing HITL. Mixed docs+code changes stay on the delivery spine.

**Stale-change-file gate (#19).** A change marked `status: merged` is treated as inactive, so a concluded change file no longer satisfies the session gate for the next change.

**Manifest drift checker shipped (#16).** `ci/manifest-drift/check_manifest_drift.py` is now shipped under `shared/ci/`, copied into product repos at onboarding, and derives its scan roots from the manifest (no hardcoded `app/ src/`).

**Brownfield PRD initialization (#18).** Brownfield onboarding initializes the PRD shell (personas + format), the entry PM skills establish it on first run, and read-only PM/QA skills report "no requirements yet" instead of failing when the PRD is empty.

---

## [1.0.30] — 2026-06-21

### Fixed

**Breadcrumb now renders block-style YAML steps (issue #15).** `hooks/_steps.sh` only parsed
single-line flow maps (`- { n: 1, … }`); a change file written with block-style `workflow.steps`
(equally valid YAML, and easily produced by anything that edits the file) parsed to zero steps,
so the breadcrumb showed `Step ? / N` with no trail. The parser now handles **both** styles.
Also: the renderers tolerate **unquoted** `name:`/`phase:`; a workflow block that yields no steps
now shows the "run `/hitl:dev-update`" hint instead of a silent `?`; and the `unverifiable` branch
marker is no longer shown (it was permanent noise on long-lived non-`issue/*` branches).

**Hooks no longer silently no-op on Windows (issue #14).** The hook wrappers and several hooks
hard-coded `python3`, which on Windows is the Microsoft Store stub (on PATH but runs nothing) —
so plugin discovery returned empty and **every gate silently did nothing**. All Python callers
(wrapper template, the hooks, and the `dev-start-change` / `dev-update` generators) now probe
`python3 → python → py` with an `import sys` smoke test that rejects the stub, and force UTF-8
stdout (`PYTHONUTF8=1`) so breadcrumb glyphs don't crash on Windows' cp1252 default.

---

## [1.0.29] — 2026-06-17

### Fixed

**`/hitl:dev-update` change-file migration no longer mangles `current-change.yaml`.** The 1.0.28
migration (Step 4.5) round-tripped the whole file through `yaml.safe_dump`, which (1) **stripped
every inline comment** — destroying hand-written annotations like `# CORRECTED` / `# MISSED in
first draft` on the impact analysis — and (2) wrote the steps as multi-line **block** maps, which
the breadcrumb parser (`hooks/_steps.sh`) can't read, producing a "step trail unavailable" error.

The migration is now **surgical**: it replaces only the `workflow:` block (as single-line flow
maps) and upserts the version stamps, leaving every other line — and all comments — byte-for-byte
intact. The file is never round-tripped through a YAML dumper. Reported by a user upgrading the
Cerrtus consolidation to 1.0.28.

---

## [1.0.28] — 2026-06-16

### Added

**`/hitl:dev-start-change` — the enforced front door for starting a change.** Pick a GitHub
issue, have HITL classify the right workflow (development / brownfield / migration / prd) from
the issue, see the full step plan, and get a seeded-and-pushed `.hitl/current-change.yaml` — then
it routes into the matching workflow. A new `SessionStart` gate (`hitl-gate.sh`) plus a per-prompt
directive insist on this before any work happens, and `check-hitl-context.sh` now hard-blocks all
edits (not just source) until a change is active for the branch — so you can't drift into a
session without choosing a workflow. (`.hitl/` and `.claude/` paths stay writable so intake and
onboarding can bootstrap.)

**Self-describing, workflow-aware `current-change.yaml` (schema v2).** The change file now carries
its own workflow definition — an embedded `workflow` block with each step's stable `key`, label,
and status. The breadcrumb renderers read this block via a single shared parser
(`hooks/_steps.sh`), so the welcome banner and the status line can never again disagree on step
count or labels.

**Branch ↔ change mismatch warnings (issue #12).** A new `expected_branch` field plus a soft
"unverifiable"/hard "mismatch" marker in the breadcrumb and a hard edit-block when a committed
`current-change.yaml` has been inherited onto the wrong branch.

### Fixed

**Empty / drifting step trail (issue #10).** The status line previously matched the workflow phase
with a hardcoded `case` that real changes (`phase: "Design"`/`"Build"`) never hit, leaving an empty
trail; the banner used a separate hardcoded 32-step list. Both hardcoded models are gone — there is
now one canonical catalog (`ai/shared/workflows.yaml`: development 31 steps + 19a, brownfield 11,
migration 9, prd 4) that drives everything.

### Changed

**`/hitl:dev-update` migrates the change file.** On upgrade it remaps the embedded workflow by
stable `key` (preserving done/current across renumbering — e.g. the brownfield 8→11 growth),
shows a diff, and requires confirmation. The start-skills and `dev-apply-change` now seed the v2
block; `dev-apply-change`'s phase inconsistency was corrected.

---

## [1.0.27] — 2026-06-16

### Changed

**`/hitl:architect-review-existing` Phase 4a: architect now chooses which baseline ADRs to fill in.**

Previously Phase 4a decided for the architect which stubs to complete and blocked progression until specific ones were accepted. The new approach presents all 8 baseline ADRs in a single table with their gating requirements, then asks the architect which to complete now. For each selected ADR, Claude pre-fills every field derivable from the Phase 1 and Phase 2 findings and asks only for the fields that cannot be inferred from code (RTO/RPO targets, compliance scope, reviewer names, PR size policy, etc.). Deferred stubs are listed at the end with their gates so the team knows what to follow up on.

ADR numbering for new project-specific decisions (Phase 4b) corrected to start from ADR-0009.

### Upgrade guide — 1.0.26 → 1.0.27

```bash
/hitl:dev-update
```

---

## [1.0.26] — 2026-06-16

### Added

**Baseline ADR set completed: ADR-0006, 0007, and 0008.**

All three are picked up automatically by the `adr-000*.md` glob in Step 0 of every setup flow — no manual copy needed.

- **ADR-0006 (Branching and PR strategy)**: branching model, branch naming convention, PR size expectations, required reviewers by change tier, merge strategy, and branch protection rules. Gates: first PR merged via the HITL workflow.

- **ADR-0007 (Security baseline)**: secret management approach, dependency vulnerability scanning tool, SAST configuration, security review gates (when `/hitl:review-security` and `/hitl:ops-pentest` are mandatory), and compliance scope. Gates: first Tier 2 production deploy.

- **ADR-0008 (Data backup and recovery)**: RTO/RPO targets, backup approach per data store, tested restore procedure, verification cadence, and the pre-deploy backup gate used by `/hitl:ops-backup-database`. Gates: first production data write.

`/hitl:architect-review-existing` Phase 4a now lists all 8 baseline stubs with their gates, and groups the "ask architect" prompt by priority: stubs that block the first Tier 2 change vs stubs that block the first Tier 2 production deploy.

**Complete baseline ADR set:**

| ADR | Topic | Type | Gates |
|---|---|---|---|
| 0001 | HITL adoption | Pre-filled | — |
| 0002 | Documentation-first | Pre-filled | — |
| 0003 | Test strategy | Stub | First Tier 2 change |
| 0004 | Change tier policy | Stub | First Tier 2 change |
| 0005 | Observability strategy | Stub | First Tier 2 prod deploy |
| 0006 | Branching and PR strategy | Stub | First PR |
| 0007 | Security baseline | Stub | First Tier 2 prod deploy |
| 0008 | Data backup and recovery | Stub | First prod data write |

### Upgrade guide — 1.0.25 → 1.0.26

```bash
/hitl:dev-update
```

Existing projects: re-run `/hitl:architect-review-existing` — Phase 4a will copy ADR-0006, 0007, and 0008 stubs and prompt the architect to fill them in.

---

## [1.0.25] — 2026-06-16

### Added

**Observability setup added to all three onboarding flows. New ADR-0005 baseline stub.**

- **New `adr-0005-observability-strategy.md` stub**: covers application observability (logging, metrics, tracing, error tracking, dashboards, alerting, on-call routing) and agentic observability (session logs, token cost registry). Automatically copied to every project during Step 0 setup via the existing `adr-000*.md` glob.

- **Brownfield** (`/hitl:dev-start-brownfield`) — new Step 6 surveys existing observability infrastructure, seeds the token cost registry from the plugin template, fills in ADR-0005 with the architect, and flags gaps by severity (no logging = 🔴, no alerting = 🟡). Old Steps 6–10 shift to Steps 7–11.

- **PRD** (`/hitl:dev-start-from-prd`) — Step 4 handoff now includes observability provisioning as item 3: set up app observability stack and token cost registry before first deploy.

- **Migration** (`/hitl:dev-start-migration`) — Step 9 handoff now gates first production slice on observability infrastructure being in place for the target system.

- **`/hitl:architect-review-existing`** — Phase 2 adds Decision 9 (Observability as-built): extracts logging format, metrics tooling, tracing, error tracking, and on-call routing. Phase 4a adds ADR-0005 to the baseline stubs table; all three stubs (ADR-0003, 0004, 0005) must be accepted before the first Tier 2 production deploy.

### Upgrade guide — 1.0.24 → 1.0.25

```bash
/hitl:dev-update
```

Existing brownfield projects: re-run `/hitl:architect-review-existing` — Phase 4a will copy the missing ADR-0005 stub and ask the architect to fill it in. Then run Step 6 of `/hitl:dev-start-brownfield` as a standalone observability check.

---

## [1.0.24] — 2026-06-16

### Added

**Build and deployment pipeline verification added to all three setup flows.**

- **Brownfield** (`/hitl:dev-start-brownfield`) — new Step 5 verifies the existing pipeline: identifies the CI system (GitHub Actions, Jenkins, GitLab CI, CircleCI, Buildkite), runs a build check, confirms a staging deploy job exists. Offers to scaffold a starter pipeline if missing or broken. Old Steps 5–9 shift to Steps 6–10.

- **PRD** (`/hitl:dev-start-from-prd`) — Step 4 handoff now includes a pipeline setup item: after architect design is approved, provision CI/CD from the deployment view HLD and verify a commit reaches staging before any code is written.

- **Migration** (`/hitl:dev-start-migration`) — Step 9 handoff now includes an explicit pipeline gate between architect design approval and the first development slice: provision CI/CD for the target repo with build, test, and deploy-to-staging jobs; no production cutover step without a manual approval gate.

### Upgrade guide — 1.0.23 → 1.0.24

```bash
/hitl:dev-update
```

Existing brownfield projects: Step 5 is now the pipeline verification step. If you have already completed brownfield setup, run the Step 5 pipeline check as a standalone verification before your next change.

---

## [1.0.23] — 2026-06-16

### Added

**Deployment view staleness detection.**
Two automatic detection points prevent the deployment view HLD from drifting out of sync with infrastructure:

1. **Edit-time hook** (`check-domain-boundary.sh`): fires automatically whenever an IaC file is edited (Dockerfile, docker-compose, k8s/, helm/, terraform/, serverless.yml, .github/workflows/, infra/). If `docs/02-design/technical/hld/deployment-view.md` exists, a warning is emitted noting the view may be stale and pointing to the file or `/hitl:architect-review-existing` Phase 4c to regenerate.

2. **Post-apply step** (`/hitl:ops-apply-iac` Step 6): after every successful IaC apply, compares what changed against the deployment view and updates affected sections in place — services table, external dependencies, environments, CI/CD pipeline diagram. Skips silently if only config tuning or version bumps occurred with no topology change.

### Upgrade guide — 1.0.22 → 1.0.23

```bash
/hitl:dev-update
```

---

## [1.0.22] — 2026-06-16

### Added

**Deployment view HLD generated during brownfield architect review.**
`/hitl:architect-review-existing` Phase 4c now reads the infrastructure files already surveyed in Phase 1b (Dockerfile, docker-compose.yml, k8s/, terraform/, serverless.yml, CI/CD configs) and generates `docs/02-design/technical/hld/deployment-view.md`. The document covers environments, a Mermaid infrastructure diagram, services/containers table, external dependencies, and CI/CD pipeline. If no IaC files are found, the step is skipped and flagged as a Phase 5 concern. Phase 6 handoff now reports whether the deployment view was generated.

### Upgrade guide — 1.0.21 → 1.0.22

```bash
/hitl:dev-update
```

For existing brownfield projects: re-run `/hitl:architect-review-existing`. Phase 4c will generate the deployment view from your existing IaC files.

---

## [1.0.21] — 2026-06-16

### Fixed

**Baseline ADR stubs not delivered in brownfield onboarding (`/hitl:dev-start-brownfield`).**
Two bugs allowed the architect to reach `/hitl:architect-review-existing` without the 4 baseline ADR stubs:

1. **Step 0 all-or-nothing skip.** When `.hitl/hooks/` already existed (interrupted setup, re-run, manual wiring), the entire Step 0 was skipped including the ADR stub copy. Restructured: hook wiring (sub-steps 1–3) is still skipped when hooks exist, but gitignore and ADR stub sub-steps (4–5) always run.

2. **`architect-review-existing` never mentioned the stubs.** Added Phase 4a before any new ADRs are created: lists the 4 expected baseline stubs, copies any that are missing, and explicitly asks the architect to fill in ADR-0003 (test strategy) and ADR-0004 (change tier policy) before proceeding to ADR-0005+. These two stubs are pre-created but need architect input — they gate the first Tier 2 change.

### Upgrade guide — 1.0.20 → 1.0.21

```bash
/hitl:dev-update
```

For existing brownfield projects missing the stubs: re-run `/hitl:architect-review-existing`. Phase 4a will detect and copy the missing files.

---

## [1.0.20] — 2026-06-16

### Added

**Comprehensive usage guide (`shared/usage-guide.md`).**
Distributed with the plugin. Covers all six team scenarios with start commands, step-by-step flows, human gates, and what each path produces:

1. New project from a PRD
2. Existing codebase (brownfield onboarding)
3. Migration (source → target system replacement)
4. Enhancement (day-to-day 32-step workflow)
5. Bug fix (Tier 1 abbreviated path)
6. Incident response (P0 fix-first, P1 abbreviated)

Includes role-specific command tables for PM, Architect, QA, and Ops, plus context-switching guidance and a full quick-reference table.

### Upgrade guide — 1.0.19 → 1.0.20

```bash
/hitl:dev-update
```

No project changes needed. The usage guide is available at `${CLAUDE_PLUGIN_ROOT}/shared/usage-guide.md` after updating.

---

## [1.0.19] — 2026-06-16

### Fixed

**Plugin update cache-bust (`/hitl:dev-update`).**
`claude plugin marketplace update` can silently skip an update when `plugin-catalog-cache.json` holds a stale `marketplace_sha`. The update skill now detects a no-op (version unchanged after update) and automatically deletes the catalog cache file, then retries. If the version still doesn't change after the cache bust, the user is genuinely on the latest.

**`reinstall.sh` busts catalog cache and removes stale local marketplace entries.**
Added two pre-install steps: delete `plugin-catalog-cache.json` (forces fresh fetch) and remove any `known_marketplaces.json` entries for hitl marketplaces pointing at local/tmp paths (left over from dev installs). These stale entries prevented the GitHub-based marketplace from being the authoritative source.

### Upgrade guide — 1.0.18 → 1.0.19

```bash
/hitl:dev-update
```

If the update appears to be a no-op, the skill now handles it automatically. No manual steps needed.

---

## [1.0.18] — 2026-06-16

### Added

**Per-issue feature branches with context isolation.**
`/hitl:dev-apply-change` now creates an `issue/{N}-{slug}` branch before writing `.hitl/current-change.yaml` and commits the file immediately to anchor it to the branch. Each issue gets its own isolated YAML state automatically through git.

**Three-layer context conflict detection.**
Switching between issues in the same Claude Code session previously risked carrying stale context from the prior issue. Three defences now prevent this:

1. `check-hitl-context.sh` (PreToolUse hook) — blocks source code edits if the current branch's issue number doesn't match the YAML's `change_id`. Exit code 2 stops the tool call.
2. `welcome.sh` (UserPromptSubmit hook) — injects a visible `⚠️ HITL CONTEXT MISMATCH` warning into the model context on every prompt when branch and YAML diverge, even before any edit is attempted.
3. `/hitl:dev-switch-context` (new skill) — explicit context reload: stashes uncommitted work, checks out the target branch, reads `current-change.yaml`, reloads the GitHub issue + HLD + LLD from disk, and outputs a context-reset block instructing the model to discard all prior conversation context.

**Statusline breadcrumbs for all setup paths.**
Previously only `Migration Setup` and `Development` phases showed breadcrumbs. Three new phases added:

| Phase | Steps | Breadcrumb labels |
|---|---|---|
| `PRD Setup` | 4 | CLAUDE.md · Manifest · Issue · Handoff |
| `Brownfield Setup` | 9 | MapCode · CLAUDE.md · Manifest · ArchRvw · Docs · Registries · Graphify · Issue · Handoff |
| `Migration Review` | 5 | Context · Evaluate · MigReview · Brief · Handoff |

All three start skills (`dev-start-from-prd`, `dev-start-brownfield`, `dev-start-migration`) now write `.hitl/current-change.yaml` at Step 1 and update `current_step` at each subsequent step.

**Migration: source code is read-only.**
The migration skill now explicitly states that the source codebase is being *replaced*, not extended. A mandatory block is appended to the project's `CLAUDE.md` during setup: source code is reference only; all target behaviors must be implemented from scratch using the behavioral inventory as the only bridge.

**Workflow docs distributed with plugin.**
`shared/workflow-prd.md`, `shared/workflow-brownfield.md`, and `shared/workflow-migration.md` are now bundled with the plugin. `build.sh` auto-syncs these on every build.

### Fixed

**Graphify install gate removed from setup skills.**
`/hitl:dev-start-from-prd` and `/hitl:dev-start-brownfield` previously blocked setup with a machine-level install step (`uv tool install graphifyy`). The gate is removed; per-project commands (`graphify .`, `graphify hook install`) are retained as conditional steps that run only if Graphify is already installed.

**Stale command names swept.**
`/hitl:start-brownfield`, `/hitl:start-migration`, `/hitl:start-prd`, and `/hitl:ops-log-incident` replaced with current names across all skills and templates.

**Release logic corrected.**
`build.sh` previously set `marketplace.json source.commit` to the HEAD *before* the build commit, meaning installations always resolved to the prior version. A new `release.sh` script fixes the ordering: build → commit → pin SHA → create `hitl--vX.Y.Z` tag → commit marketplace update.

**Adoption guide updated.**
`docs/playbook/adoption-guide.md` referenced the deprecated `generate-docs reverse-engineer` sprint. Updated to reflect the current `/hitl:dev-start-brownfield` flow with `architect-review-existing` producing real ADRs.

### Upgrade guide — 1.0.17 → 1.0.18

```bash
/hitl:dev-update
```

No migration needed for existing projects. New behaviour is additive — branches are created on next `/hitl:dev-apply-change` run. If you have an existing `.hitl/current-change.yaml` on `main`, it will continue to work; breadcrumbs and context checks activate on the next change.

---

## [1.0.17] — 2026-06-15

### Added

**Migration flow: source codebase analysis (`/hitl:dev-start-migration` Step 5).**

The migration flow previously had no step that read the existing source code. The behavioral inventory produced by vendor runbooks or verbal description alone missed behaviors that are only visible in the actual code. This fills that gap.

**New Step 5 — Analyze source codebase:**

| Source location | What happens |
|---|---|
| Local path (same or sibling repo) | Reads top-level structure and key files; extracts APIs, domain behaviors, data contracts, integration points, auth rules, background jobs |
| Remote-only or inaccessible | User describes behavior verbally; entries marked `confidence: low` |

Output: `docs/00-migration/source-behavioral-inventory.md` — a table-structured inventory of every BI-NNN item that the target system must implement. This file is the objective definition of "migration complete."

**`/hitl:dev-review-external-docs` updated (Phase 1b + migration brief):**

- New Phase 1b reads `source-behavioral-inventory.md` before evaluating external docs. If absent, the skill warns and asks whether to proceed without it.
- Migration brief template now includes a **behavior coverage matrix** — one row per BI ID, with fields for target slice and status (`Not started / In progress / Complete / Descoped`). Each migration slice must declare which BI IDs it covers in its GitHub issue.

**Migration is complete when** every BI entry in the inventory has status `Complete` or `Descoped` in the coverage matrix. `Descoped` requires an explicit architect decision.

**Migration flow step renumbering:** old Steps 5–8 became Steps 6–9. Statusline updated to 9 steps, with new `SrcAnal` label at position 5.

### Upgrade guide — 1.0.16 → 1.0.17

```bash
/hitl:dev-update
```

Existing migration projects: run `/hitl:dev-start-migration` Step 5 manually to generate the behavioral inventory from your source codebase, then rerun `/hitl:dev-review-external-docs` to add the coverage matrix to your migration brief.

---

## [1.0.16] — 2026-06-15

### Added

**New skill: `/hitl:architect-review-existing` — reconstruct and document architecture decisions in an existing codebase.**

Fills the gap in the brownfield onboarding flow: the system manifest captures domain boundaries, but nothing captured *why* the existing technology choices were made or what constraints they impose. This skill reads the codebase and interviews the architect to produce real ADRs (not generic stubs) before incremental work begins.

**Six-phase flow:**

| Phase | What happens |
|---|---|
| 1 — Landscape | Reads system manifest + key technology indicator files; produces a Tech Stack Summary |
| 2 — Extract decisions | Identifies concrete decisions across 8 categories: service architecture, data, auth, API style, cross-domain communication, deployment, test strategy as-built, non-obvious patterns |
| 3 — Interview | Asks architect which decisions were deliberate vs inherited, confirms rationale, surfaces constraints and regrets |
| 4 — Document ADRs | Creates real ADRs (ADR-0005+) for significant decisions — status Accepted or Under review; never fabricates rationale |
| 5 — Surface concerns | Categorizes concerns as blocking HITL compliance (🔴), address in first changes (🟡), or worth noting (🟢) |
| 6 — Handoff | Produces summary of ADRs created, key constraints, and pre-conditions for first Tier 2 change |

**Brownfield flow updated:** New Step 4 added between system manifest generation (Step 3) and priority component documentation (now Step 5). Steps 4–8 renumbered to 5–9. Architect must confirm ADRs before proceeding to Step 5.

### Upgrade guide — 1.0.15 → 1.0.16

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

---

## [1.0.15] — 2026-06-14

### Fixed

**Persistent HITL breadcrumb via `statusLine` (fixes #7, #8).**

The `UserPromptSubmit` `welcome.sh` banner was routed into Claude's model context as `<system-reminder>` — not visible to the user. The fix adds a `statusLine` command to `.claude/settings.json` that Claude Code renders persistently in the UI status bar, showing the active change, phase, step number, and a windowed step trail:

```
HITL: Development · Step 14/31: GREEN [FR-42 · T2]
     ✓11.RED ✓12.TstRvw ✓13.VfyRED ▶14.GREEN ·15.VfyGRN ·16.Refact ·17.Conv …
```

Changes:
- `ai/claude/hooks/statusline-hitl.sh` — moved from `ai/claude/` (was never distributed by build.sh) into `hooks/` so it is now synced to the plugin; YAML path fixed from relative `$(dirname $0)/../` to `$CLAUDE_PROJECT_DIR` anchor
- `init-project.sh` and Step 0 of all three start skills — `statusLine` key added to `.claude/settings.json` template; `statusline-hitl` added to the hook wrapper generation loop
- `/hitl:dev-update` Step 4 — now checks for `statusLine` in `.claude/settings.json` and regenerates if absent

**Mermaid diagram constraints (fixes #9).**

Generated HLD/LLD diagrams broke GitHub rendering in two ways: nested generics in `classDiagram` (`~~` double-close from Java types like `ResponseEntity<Page<Order>>`) and literal `\n` in flowchart node labels. Both patterns now have:

1. **Template guardrails** — `hld-template.md` and `lld-component-template.md` have inline `<!-- Mermaid rules -->` comments that the architect skills read during generation
2. **`/hitl:dev-validate` checks** — two new checks added alongside the existing `<br/>` check:
   - `grep -n '~~' <file>` — catches nested generics before they reach GitHub
   - `grep -n '\\n' <file>` — catches literal `\n` in node labels

### Upgrade guide — 1.0.14 → 1.0.15

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Then run `/hitl:dev-update` in each project to add the `statusLine` to `.claude/settings.json` and regenerate hook wrappers. Restart Claude Code after.

---

## [1.0.14] — 2026-06-14

### Added

**New skill: `/hitl:help` — command discovery.**

Describe what you're trying to do and get a recommendation, or run it with no argument for the full command directory grouped by role.

```
/hitl:help                          # full directory — all commands by role
/hitl:help I want to enhance a feature that already exists
/hitl:help how do I start a TDD cycle
/hitl:help the code doesn't match the design doc
```

Covers all 40+ commands across dev, architect, QA, PM, and ops. Always gives a best guess — never says "I'm not sure" without recommending something.

### Upgrade guide — 1.0.13 → 1.0.14

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

---

## [1.0.13] — 2026-06-14

### Added

**New skill: `/hitl:pm-enhance-feature` — structured enhancement workflow for any existing feature.**

Works for product capabilities, PRD requirements, skills, agents, services, or any named component. Fills the gap between `/hitl:pm-update-requirement` (assumes you already know what to change) and `/hitl:pm-add-feature` (for new features from scratch).

**Five-phase flow:**

| Phase | What happens |
|---|---|
| 1 — Discover | Finds all artifacts related to the feature: PRD requirement, HLD/LLD, SKILL.md/AGENT.md, source paths from the system manifest, open GitHub issues |
| 2 — Explain | Summarizes current behavior in plain business language (no code, no YAML) — confirms the PM is looking at the right thing |
| 3 — Interview | Asks about the gap, affected users, impact, desired outcome, what must stay unchanged, constraints |
| 4 — Draft | Produces a structured enhancement request with problem statement, proposed changes, acceptance criteria, and explicit out-of-scope list |
| 5 — Record | Updates the PRD, creates a GitHub issue, and tells the PM what happens next (tier assessment → design → dev) |

Supports rigorous / moderate / light challenge modes. Never drafts the requirement until Phase 3 is complete. Never accepts unmeasurable acceptance criteria ("make it better", "improve it") without pushing for specifics.

### Upgrade guide — 1.0.12 → 1.0.13

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

---

## [1.0.12] — 2026-06-14

### Added

**Default ADR stubs written to `docs/02-design/technical/adrs/` during project setup.**

Every new HITL project now gets four starter ADRs that document the foundational decisions teams always need to make. They are created by both `init-project.sh` and Step 0 of all three start skills (`/hitl:dev-start-from-prd`, `/hitl:dev-start-brownfield`, `/hitl:dev-start-migration`). Existing files are never overwritten — safe to run on projects that already have ADRs.

| File | Status at creation | Purpose |
|---|---|---|
| `adr-0001-hitl-adoption.md` | Accepted (pre-filled) | Why the team adopted HITL; rationale, alternatives, ROI tracking |
| `adr-0002-documentation-first.md` | Accepted (pre-filled) | Decision to write HLD/LLD before code; consequences, exceptions |
| `adr-0003-test-strategy.md` | Draft (fill before first Tier 2 change) | Test framework, coverage gate, mocking policy, CI gates |
| `adr-0004-change-tier-policy.md` | Draft (fill at project kickoff) | Project-specific Tier 0–4 definitions; Tier 3 high-risk list |

ADR-0001 and ADR-0002 include pre-filled rationale that applies to any HITL project. ADR-0003 and ADR-0004 are stubs with prompts — the team fills them in at kickoff.

### Upgrade guide — 1.0.11 → 1.0.12

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

For existing projects, copy the ADR stubs manually:

```bash
mkdir -p docs/02-design/technical/adrs
PLUGIN_ROOT=$(python3 -c "
import json,os,sys
try:
  d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
  for inst in d.get('plugins',{}).get('hitl@hitl',[]):
    p=inst.get('installPath','')
    if os.path.isfile(os.path.join(p,'.claude-plugin/plugin.json')):
      print(p);sys.exit(0)
except:pass
" 2>/dev/null)
for f in "$PLUGIN_ROOT/shared/templates"/adr-000*.md; do
  dest="docs/02-design/technical/adrs/$(basename "$f")"
  [[ -f "$dest" ]] || cp "$f" "$dest"
done
```

---

## [1.0.11] — 2026-06-13

### Fixed

**Session logs no longer end up in the product repo's git history.**

`write-session-summary.sh` writes to `docs/session-logs/` inside the project directory. Nothing previously added that path to `.gitignore`, so session logs were silently committed on the next `git add`.

**Three-layer fix:**

1. **Step 0 of all start skills** now adds `docs/session-logs/` to `.gitignore` as part of initial project setup — same step that wires hooks and creates `.claude/settings.json`.

2. **`init-project.sh`** adds the `.gitignore` entry when creating the docs directory structure.

3. **`write-session-summary.sh` hook** adds the entry as a safety net on every session end — idempotent, only adds if missing. Covers existing projects that were set up before this fix without requiring a manual step.

**For existing projects with session logs already committed:**

```bash
# Remove from tracking (keeps the files on disk)
git rm -r --cached docs/session-logs/

# Commit the removal
git commit -m "chore: untrack HITL session logs"
```

The `.gitignore` entry will be added automatically on the next session end by the updated hook.

### Upgrade guide — 1.0.10 → 1.0.11

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. The safety-net fix in `write-session-summary.sh` activates on the next session end — no other action needed for existing projects.

---

## [1.0.10] — 2026-06-13

### Added

**New skill: `/hitl:dev-validate` — iterative validation loop.**

Runs a check → fix → re-check loop until every artifact from the session passes. Never exits until all checks pass (or explicitly marks items as unresolvable with a reason).

**What it validates by artifact type:**

| Type | Checks |
|---|---|
| Source code | Test suite (no regressions), coverage gate, linter, happy-path run |
| Tests | Execute without error, behavior-named, no unexplained skips |
| Docs (`.md`) | File paths exist, commands execute, no `{{placeholder}}`, no `<br/>` in Mermaid, index updated, cross-refs live |
| YAML / JSON | Parses, no placeholders, required fields present |
| Scripts / hooks | Executes, execute bit set, shebang present, `.hitl/` guard in hooks |
| Skill / agent files | Frontmatter valid, command names exist in `plugin.json`, paths exist, no placeholders |

**The loop:**
1. Inventory all files produced/modified
2. Run all applicable checks — log each PASS / FAIL
3. Fix every FAIL
4. Re-check — repeat from step 3 until zero failures
5. Report: what was checked, what was fixed, what (if anything) is genuinely unresolvable

**`CLAUDE.md.template` updated.** The Testing section is now a Validation Gate that directs Claude to run `/hitl:dev-validate` before reporting done on any task. Applies to all 40 skills universally.

### Upgrade guide — 1.0.9 → 1.0.10

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. No project-level changes needed — the new skill and updated CLAUDE.md template are available immediately after restart.

**Existing projects:** The CLAUDE.md template update only applies to new projects initialized after this release. To apply it to an existing project, add this section to your `CLAUDE.md`:

```markdown
## Validation (Mandatory — no exceptions)

After completing any task, run `/hitl:dev-validate` before reporting done.
```

---

## [1.0.9] — 2026-06-13

### Fixed

**Hooks no longer fail with "No such file or directory" on current Claude Code.**

Two bugs caused all six hooks to fail immediately after `plugin install` on any machine where Claude Code's working directory was not the project root:

**Bug 1 — Wrong plugin discovery schema (issue #6).**
All plugin path discovery code read `~/.claude/settings.json["plugins"]`, but current Claude Code stores installed plugin records in `~/.claude/plugins/installed_plugins.json` with a different schema. The hook wrappers generated by Step 0 could not find the plugin and silently exited — hooks never ran.

Fixed everywhere discovery runs:
- Detection snippet in Step 0 of all three start skills (`dev-start-from-prd`, `dev-start-brownfield`, `dev-start-migration`)
- Wrapper template written by Step 0
- Wrapper generation in `tools/scripts/init-project.sh`

New discovery order: `installed_plugins.json` first (current Claude Code v2 schema), fallback to `settings.json["plugins"]` (legacy).

**Bug 2 — Relative hook paths in `.claude/settings.json` (issue #7).**
Hook commands were written as `bash .hitl/hooks/welcome.sh` — a path relative to whatever Claude Code's working directory happened to be. Claude Code does not guarantee the cwd is the project root when invoking hooks. All six hooks failed with "No such file or directory" when Claude Code launched from a subdirectory or from a path other than the project root.

Fixed by using `$CLAUDE_PROJECT_DIR` (the env var Claude Code provides to hook commands) as an anchor:
```json
{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/welcome.sh\"" }
```

Fixed in `.claude/settings.json` templates in all three start skills and `init-project.sh`.

**`/hitl:dev-update` Step 4 detection updated.**
The stale-wrapper check was `grep "claude/settings.json"` — this now incorrectly marks the new wrappers as stale. Updated to `grep "installed_plugins.json"`: absence means the wrapper predates the v2 discovery fix and should be recreated. Step 4 also now checks and recreates `.claude/settings.json` if `CLAUDE_PROJECT_DIR` is absent.

### Upgrade guide — 1.0.8 → 1.0.9

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code.

**Existing projects — update hook wiring:** Run `/hitl:dev-update` from inside the project. Step 4 detects stale wrappers and settings.json and recreates them automatically.

Or do it manually:
```bash
rm -rf .hitl/hooks/ .claude/settings.json
```
Then re-run `/hitl:dev-start-from-prd` (or brownfield/migration) — Step 0 recreates both.

---

## [1.0.8] — 2026-06-11

### Added

**All skills now exit immediately in projects that haven't adopted HITL.**

Every skill except the three start skills and `/hitl:dev-update` now checks for `.hitl/` at the start. If the directory is absent, the skill outputs a setup prompt and stops — nothing else happens:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

This covers all 37 non-setup skills: `dev-practices`, `dev-tdd`, `dev-apply-change`, `dev-check-conventions`, `dev-generate-docs`, `dev-conclude`, `dev-impact-brief`, `dev-review-lld-adherence`, `dev-review-security`, `ta-approve`, all `architect-*`, `pm-*`, `qa-*`, `ops-*`, and `migrate-review-external-docs`.

**Known limitation (tracked):** `/hitl:*` commands appear in Claude Code's command palette in every project because Claude Code does not yet support per-project plugin skill visibility. The guard above is the mitigation — commands are visible but safe to invoke anywhere. A feature request has been filed with Anthropic to add project-scoped skill loading.

**README: opt-in model, opt-out instructions, and clean removal guide added to both repos.**

- "What happens when you install" — explains what is global (commands in palette) vs per-project (hooks, banner)
- "Opting a project out" — delete `.hitl/hooks/` and `.claude/settings.json`
- "Removing the plugin entirely" — `claude plugin uninstall hitl@hitl` + project cleanup

### Upgrade guide — 1.0.7 → 1.0.8

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. No project-level changes needed.

---

## [1.0.7] — 2026-06-11

### Fixed

**Plugin hooks no longer activate in projects that never opted into HITL.**

`hooks/hooks.json` was shipped in the plugin and auto-loaded by Claude Code, registering all hooks at user/global scope. This meant every project on the machine — including those with no `.hitl/` directory — had the HITL hooks firing. The immediate impact: `check-hitl-context.sh` exits 2 (blocking all `Edit`/`Write` tool calls) in any repo where `.hitl/current-change.yaml` is absent, even if that repo has nothing to do with HITL.

**Two changes:**

1. **`hooks/hooks.json` deleted.** The project-level hook wiring (`.hitl/hooks/` + `.claude/settings.json`, created by Step 0 of any start skill) is the correct mechanism and is unaffected. The global registration file is gone.

2. **All 6 hook scripts now guard on `.hitl/` presence.** As a safety net for any user who has plugin-level hooks wired in their user settings from an older install, every script now exits 0 immediately if `.hitl/` does not exist in the current working directory:
   ```bash
   [[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently
   ```
   This covers: `welcome.sh`, `check-hitl-context.sh`, `check-domain-boundary.sh`, `rebuild-graph.sh`, `sync-step-to-issue.sh`, `write-session-summary.sh`.

### Upgrade guide — 1.0.6 → 1.0.7

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. No project-level changes needed — the fix is entirely in the plugin.

---

## [1.0.6] — 2026-06-10

### Fixed

**`/hitl:dev-update` now correctly detects the installed version and upgrades the plugin.**

Three bugs prevented the update skill from working on current Claude Code:

1. **Version always showed `NOT_FOUND`.** The detection script read from `~/.claude/settings.json`, but Claude Code stores installed plugin records in `~/.claude/plugins/installed_plugins.json`. Fixed: reads `installed_plugins.json` first, falls back to scanning `settings.json` for the plugin path.

2. **`claude plugin install` is a no-op when already installed.** Step 2 was using the install command, which prints "already installed" and does nothing. Fixed: now uses `claude plugin marketplace update hitl` (refreshes the cached manifest) followed by `claude plugin update hitl@hitl` (installs the new version).

3. **`CHANGELOG.md` was not present in the installed plugin.** Step 3 tries to show the changelog from the plugin directory, but the file was never copied there. Fixed: `build.sh` now copies `CHANGELOG.md` from the source repo on every build. Step 3 falls back to the source repo URL if the file is missing.

### Upgrade guide — 1.0.5 → 1.0.6

Since `/hitl:dev-update` was broken in 1.0.5, upgrade manually this once:

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. After this, `/hitl:dev-update` will work correctly for all future upgrades.

---

## [1.0.5] — 2026-06-10

### Fixed

**Hook wrappers now survive plugin updates — "HITL_PLATFORM_ROOT is not set" error eliminated.**

The wrappers written by Step 0 used `${HITL_PLUGIN_ROOT:-<path>}` to locate the plugin. That env var was never set by Claude Code, and the fallback path was hardcoded to whatever version was current at setup time. After a `plugin install` bump (e.g. `1.0.4` → `1.0.5`), the versioned path changed and every hook silently failed or printed "is not set".

Wrappers are now fully dynamic: each one runs a short Python snippet at call time to read `~/.claude/settings.json` and discover the current plugin path. No env var, no hardcoded path — survives version bumps and reinstalls on any platform (macOS, Linux, WSL).

Old pattern (broken after update):
```bash
exec bash "${HITL_PLUGIN_ROOT:-/path/to/hitl/1.0.4}/hooks/welcome.sh" "$@"
```

New pattern (dynamic, version-agnostic):
```bash
PLUGIN_ROOT=$(python3 -c "
import json,os,sys
cfg=os.path.expanduser('~/.claude/settings.json')
try:
  data=json.load(open(cfg))
  for p in data.get('plugins',[]):
    path=p if isinstance(p,str) else p.get('path','')
    if os.path.isfile(os.path.join(path,'.claude-plugin/plugin.json')):
      print(path);sys.exit(0)
except:pass
" 2>/dev/null)
[[ -z "$PLUGIN_ROOT" ]] && exit 0
exec bash "$PLUGIN_ROOT/hooks/welcome.sh" "$@"
```

**Step 0 plugin detection now checks the installed plugin path, not the source repo path.**

The check that detects whether the HITL plugin is installed was looking for `ai/claude/plugin/plugin.json` — a path that only exists in the source repo. The installed plugin has `.claude-plugin/plugin.json`. Fixed in all three start skills and the update skill.

**Step 0 hook delegate path corrected.**

The wrappers generated by Step 0 were calling `ai/claude/hooks/<name>.sh` (source repo layout). The installed plugin has hooks at `hooks/<name>.sh`. Fixed.

**`/hitl:dev-start-from-prd` — command renamed from `start-prd`.**

`start-prd` could be misread as "start production". The command is renamed to `/hitl:dev-start-from-prd` — "start a project from a PRD document". No functional change.

**`/hitl:dev-update` Step 4 now detects and recreates stale wrappers.**

If `.hitl/hooks/` exists but the wrappers use an old path pattern (env var or hardcoded path), Step 4 now deletes the stale wrappers and recreates them with the dynamic discovery template. Detection check: `grep "claude/settings.json" .hitl/hooks/welcome.sh`.

### Added

**README: prerequisites table, Graphify billing note, troubleshooting section (both repos).**

- Prerequisites table: lists `bash`, `python3`, `PyYAML`, `git`, `gh`, and `graphify` with what fails silently if each is absent.
- Graphify billing note: subscription users must pass `--backend claude-cli` for the initial build. The background rebuild hook (`rebuild-graph.sh`) never calls an LLM and is always free.
- Troubleshooting section: SSH host-key fix for machines where `claude plugin install` fails with "No ED25519 host key is known for github.com".

**Documentation screenshots corrected — SVG diagrams now show correct `dev-` prefixed command names.**

| File | What changed |
|---|---|
| `docs/images/developer-commands.svg` | 6 commands updated: `generate-docs`, `tdd`, `apply-change`, `check-conventions`, `impact-brief`, `conclude` → all now show `dev-` prefix |
| `docs/images/tdd-flow.svg` | `/hitl:tdd` → `/hitl:dev-tdd` in two places |
| `docs/images/welcome-banner.svg` | `dev-start-prd` → `dev-start-from-prd` |

### Upgrade guide — 1.0.4 → 1.0.5

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code.

**Existing projects — update hook wrappers:** After restarting, run `/hitl:dev-update` from inside your project. Step 4 will detect the stale wrappers and recreate them automatically.

Or do it manually: delete `.hitl/hooks/` and re-run `/hitl:dev-start-from-prd` (or brownfield/migration). Step 0 will recreate the wrappers with the new dynamic pattern and skip all other setup steps.

---

## [1.0.4] — 2026-06-09

### Fixed

**`/hitl:ta-approve` — Technical Advisor role now published correctly.**

- `ta-approve` was missing from `plugin.json`, so it was not included in the plugin.
- When it was accidentally added by a prior build, it had the wrong name (`dev-ta-approve`) because the build script was applying the `dev-` prefix intended for developer skills.
- Fixed: `ta-approve` is now a special case in the build script and maps to `/hitl:ta-approve` — its own role prefix, distinct from `dev-`, `architect-`, `pm-`, `qa-`, and `ops-`.

**Stale `dev-ta-approve` removed.** The wrongly-named duplicate is deleted from the plugin.

**All internal command cross-references corrected.** Skill files (dev-practices, architect skills, qa skills, ops skills, ta-approve itself) referenced developer commands without the `dev-` prefix. All corrected:

| Was | Now |
|---|---|
| `/hitl:tdd` (in cross-references) | `/hitl:dev-tdd` |
| `/hitl:apply-change` (in cross-references) | `/hitl:dev-apply-change` |
| `/hitl:generate-docs` (in cross-references) | `/hitl:dev-generate-docs` |
| `/hitl:check-conventions` (in cross-references) | `/hitl:dev-check-conventions` |
| `/hitl:impact-brief` (in cross-references) | `/hitl:dev-impact-brief` |
| `/hitl:review-lld-adherence` (in cross-references) | `/hitl:dev-review-lld-adherence` |

**README By Role table updated:** Added Technical Advisor row. Added missing developer skills (`dev-review-lld-adherence`, `dev-review-security`) to Developer row.

### Upgrade guide — 1.0.3 → 1.0.4

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code.

---

## [1.0.3] — 2026-06-09

### Fixed

**Command names now match the actual plugin commands.**

The published plugin prefixes all flat developer skills with `dev-` (e.g. `/hitl:dev-start-from-prd`, `/hitl:dev-update`). All documentation and scripts now use the correct names. Previously the README, CHANGELOG, and reinstall script showed names without the prefix, which caused "command not found" confusion.

Corrected names:

| Was (wrong) | Now (correct) |
|---|---|
| `/hitl:dev-start-from-prd` | `/hitl:dev-start-from-prd` |
| `/hitl:start-brownfield` | `/hitl:dev-start-brownfield` |
| `/hitl:start-migration` | `/hitl:dev-start-migration` |
| `/hitl:update` | `/hitl:dev-update` |
| `/hitl:apply-change` | `/hitl:dev-apply-change` |
| `/hitl:check-conventions` | `/hitl:dev-check-conventions` |
| `/hitl:impact-brief` | `/hitl:dev-impact-brief` |
| `/hitl:tdd` | `/hitl:dev-tdd` |
| `/hitl:generate-docs` | `/hitl:dev-generate-docs` |
| `/hitl:conclude` | `/hitl:dev-conclude` |

### Upgrade guide — 1.0.2 → 1.0.3

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code. No other action needed — this is a documentation-only fix.

---

## [1.0.2] — 2026-06-09

### Added

**`/hitl:dev-update` skill** — update the plugin from inside Claude Code without touching a terminal.

Running `/hitl:dev-update` will:
1. Locate the plugin installation from `~/.claude/settings.json`
2. Re-run the plugin install command to fetch the latest release
3. Show the version change and a summary of what was updated
4. Re-wire `.hitl/hooks/` if they are missing or point to the wrong path
5. Prompt you to restart Claude Code

### Fixed

**README corrections:**

- Install and update instructions now clearly separated — install once with the marketplace commands, update thereafter with `/hitl:update`. Explicit note added not to re-run install commands to update.
- Install table corrected to list all available commands (phantom `architect-review-design`, `architect-verify-traceability`, `ops-review-release`, `ops-monitor-canary` removed)
- Removed two phantom Architect commands that were listed but never existed: `/hitl:architect-review-design`, `/hitl:architect-verify-traceability`
- Removed two phantom Ops commands: `/hitl:ops-review-release`, `/hitl:ops-monitor-canary`. Replaced with actual ops commands.

### Upgrade guide — 1.0.1 → 1.0.2

Run the plugin install command to update:

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code. From now on, just run `/hitl:dev-update` whenever you want to upgrade.

---

## [1.0.1] — 2026-06-09

### Fixed

**Hook wiring now works for plugin users without cloning the repo.**

Previously, hooks were defined in `plugin.json` and ran from the plugin directory. This caused two failures:
- Scripts could not find `.hitl/current-change.yaml` (which lives in the user's project, not the plugin)
- On machines where the plugin path differed from the path baked into `.claude/settings.json`, every hook fired a "No such file or directory" error

**Windows / WSL compatibility fixes** — hook scripts now work correctly when Claude Code runs inside WSL on Windows.

- `welcome.sh`, `sync-step-to-issue.sh`: replaced hardcoded `/tmp/` paths with `${TMPDIR:-${TMP:-/tmp}}`, which resolves correctly on macOS, Linux, WSL, and Git Bash
- `write-session-summary.sh`: replaced `echo -e` with `printf` — portable across all shells including those on Windows

### What changed

| File | Change |
|---|---|
| `ai/claude/plugin/plugin.json` | Removed `"hooks"` entry — plugin-level hooks are the wrong mechanism |
| `ai/claude/start-from-prd/SKILL.md` | Added Step 0: auto-wires `.hitl/hooks/` and `.claude/settings.json` |
| `ai/claude/start-brownfield/SKILL.md` | Added Step 0: same hook wiring |
| `ai/claude/start-migration/SKILL.md` | Added Step 0: same hook wiring |
| `.claude/settings.json` | Removed hardcoded `/Users/Prasad_1/…` path prefix from all hook commands |
| `ai/claude/hooks/welcome.sh` | Replaced `/tmp` hardcode with `${TMPDIR:-${TMP:-/tmp}}` |
| `ai/claude/hooks/sync-step-to-issue.sh` | Same `/tmp` fix |
| `ai/claude/hooks/write-session-summary.sh` | Replaced `echo -e` with portable `printf` |

### How hooks now work

Each start skill (`/hitl:dev-start-from-prd`, `/hitl:dev-start-brownfield`, `/hitl:dev-start-migration`) includes a **Step 0** that runs once per project:

1. Discovers the plugin installation path from `~/.claude/settings.json`
2. Creates `.hitl/hooks/*.sh` wrapper scripts in the user's project — each wrapper delegates to the real script in the plugin via `${HITL_PLATFORM_ROOT:-<discovered-path>}`
3. Creates `.claude/settings.json` in the user's project pointing to those wrappers

This is the same pattern `init-project.sh` used, now delivered automatically through the plugin.

---

## Upgrade guide — 1.0.0 → 1.0.1

### Everyone

Run the plugin install command to update:

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code so the updated `plugin.json` is reloaded.

### New projects (not yet initialized)

No further action needed. Run your start skill as normal — Step 0 will wire the hooks automatically.

### Existing projects (already running the HITL workflow)

Your project does not have `.hitl/hooks/` wrappers yet. Create them now by running the appropriate start skill — it is **idempotent** and will skip any setup that is already in place:

```
/hitl:dev-start-from-prd
```
or
```
/hitl:dev-start-brownfield
```
or
```
/hitl:dev-start-migration
```

Step 0 will detect that `.hitl/hooks/` is missing, wire everything up, and prompt you to restart Claude Code. After the restart, hooks will fire correctly on every edit.

### Windows / WSL users

No special steps required beyond the above. The `/tmp` path fix and `printf` fix are included in this release and work automatically.

---

## [1.0.0] — initial release
