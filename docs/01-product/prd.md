# HITL AI-Driven Development - Product Requirements Document

**Product:** HITL (Human-In-The-Loop) AI-Driven Development Platform
**Version:** 2026-07-09
**Status:** Draft
**Author:** Prasad (PM)
**Last Updated:** 2026-07-09

> **Provenance note:** this PRD was reverse-engineered from the shipped product (plugin v1.0.30 surface plus the locked workflow-model design on branch `design/workflow-model`). It baselines what HITL *is* so that future requirements have something to diff against. New requirements append here via `/hitl:pm-add-feature`; this document does not retroactively justify past decisions (the design docs and ADRs do that).

---

## 1. Executive Summary

HITL is a document-driven delivery model for teams that use AI heavily in non-trivial software work, packaged as a Claude Code plugin. AI produces code faster than teams can review it, and does so confidently even when wrong. HITL makes that speed safe by organizing the team around documentation as the shared source of truth: AI generates; humans shape, review, and decide.

The product gives each role (PM, Architect, Technical Advisor, Developer, QA, Ops) AI-powered skills that do the legwork of their step in the delivery process, enforcement hooks and CI gates that keep the process honest without relying on memory or discipline, and a traceability chain from requirement to production (issue → PRD → HLD/LLD → code → tests → deployment) that can be audited after the fact.

Success looks like: teams adopt HITL and ship AI-assisted changes where every change is traceable to an approved design, review gates are demonstrably enforced rather than aspirational, and the process survives team growth and personnel change because it lives in the harness, not in people's heads.

---

## 2. Problem Statement

Four related pains, felt by teams using AI coding tools at scale:

1. **Review cannot keep up with generation.** AI writes code faster than humans review it, and presents wrong code as confidently as right code. Unreviewed AI code reaches production, or review becomes a rubber stamp.
2. **Siloed AI sessions drift.** Each AI session invents its own patterns. Without a shared source of truth, a codebase accumulates inconsistent conventions until a rewrite is cheaper than a fix.
3. **Process exists but is not enforced.** Teams write down their process, then bypass it under deadline pressure. Nobody can tell, from the outside, whether the process was actually followed for any given change.
4. **Leadership cannot prove control.** When an auditor, regulator, or customer security review asks "prove your AI-assisted changes were reviewed and traceable," most teams have nothing to show but git blame and good intentions.

Who feels it: engineering teams in regulated or high-audit environments, platform teams setting org standards, and any team doing migrations or cross-domain work with AI. If unsolved: drift compounds, audit exposure grows with AI code volume, and the trust gap between leadership and AI-assisted teams widens.

---

## 3. Target Users and Personas

| Persona | Role | Key need | Success metric |
|---------|------|----------|---------------|
| Product Manager | Owns requirements and priorities | Turn ideas into precise, testable requirements without writing specs by hand | Features ship matching acceptance criteria; scope changes are visible |
| Architect | Owns system design and design gates | Analyze impact, produce HLD/LLD, keep manifest and code in sync | No unreviewed design drift; decision packets complete |
| Technical Advisor | Approves scope, HLD, LLD, decision packets | Fast, informed approve/reject at each gate | Gates cleared without becoming bottlenecks |
| Developer | Implements from approved LLDs | Generate tests and code from design with conventions carried automatically | Code passes LLD-adherence and convention review first time |
| QA Engineer | Owns test evidence | Verify coverage against acceptance criteria and incident history | No regression escapes; test registry current |
| Ops Engineer | Owns build, deploy, rollout | Risk-rated rollouts with canary criteria and rollback plans | Deploys traceable; incidents fed back into the registry |
| Engineering leadership (VP Eng / Platform lead / CISO) | Buys and sponsors adoption | Prove AI-assisted development is controlled and auditable | Can answer an audit or security questionnaire from the trail |

---

## 4. Solution Overview

HITL encodes one contract: a **workflow** is a repeatable abstraction for one whole change, decomposed into phases → steps → substeps, where each step is owned by a role and backed by a skill or command that does the heavy lifting with AI. The chain is seeded by the problem statement (a GitHub issue); each step consumes the previous step's outputs; handoffs are issues backed by updated documentation; everything happens on one branch, spanning requirement → post-deployment.

Identity has three tiers, so granularity is earned rather than assumed (locked 2026-06-23, see `docs/design/workflow-model/01-design.md` §4):

- **8 workflows** own their step sequence (`ai/shared/workflows.yaml` is the source): Development (the delivery spine every change runs on), Brownfield, Migration (establishment), Migration Review (evaluate external migration docs), PRD (stand up a greenfield project), Docs (documentation-only, its own short spine), Platform Bootstrap (onboarded → delivery-ready, long-lived, register-driven; FR-25), Release (publish a version). An incident is Tier 4 of the Development workflow (fix first, docs within 48 hours), not a workflow of its own.
- **6 profiles** are named presets over the shared delivery spine: Feature, Enhancement, Fix, Tech Change, Upgrade, Security.
- **5 tags** tune required evidence within a profile: `refactor`, `perf`, `chore`, `tooling`, `infra`.

The human's profile/tag choice only proposes; impact analysis decides the actual steps and required evidence, and a floor of never-skippable steps is enforced regardless. The harness is a force-multiplier, not a rulebook: the owner supplies judgment, the harness supplies legwork, context, and rigor.

The product surface delivering this: 60 role skills, 5 lightweight commands, 6 subagent role definitions, 11 hook scripts (9 wired into each opted-in project), CI workflow templates, 38 document templates, and a numberless workflow catalog from which the runtime process, the command map, and the breadcrumb are all derived. Counts as of 2.16.1; the skill directories under `ai/claude/` are the source.

---

## 5. Functional Requirements

### 5.1 Workflow Engine and Catalog

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-1 | The process is defined once in a numberless catalog (steps identified by stable key + name + phase, never by global position) | Must Have | Inserting or reordering a catalog step requires zero edits to other docs; `tools/workflow-catalog/` derivation reproduces the runtime `workflows.yaml` losslessly, verified in CI |
| FR-2 | Profiles and tags resolve to a concrete step plan via impact analysis, with the floor enforced regardless of what the human selected | Must Have | Resolution engine tests pass; a change tagged `chore` still hits impact-analysis and docs-reconciled floors |
| FR-3 | Each catalog step declares its executing command and accountable role; the human-readable command map is generated, not hand-maintained | Must Have | `docs/command-map.generated.md` regenerates without drift in CI |
| FR-4 | Every session shows a phase-ribbon breadcrumb of where the change stands (phases + named steps, no global numbering) | Must Have | Breadcrumb matrix (`ci/breadcrumb/run_matrix.sh`) passes, including the no-phase fallback; its RESULT line is the assertion count |

### 5.2 Role Skills and Commands

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-5 | Each role has skills covering its full journey (PM: 10 skills; Architect: design-system, design-feature, review-code, review-existing, review-design, verify-traceability; Dev: practices, TDD, generate-docs, apply-change, reviews; QA: plan, scenarios, review, verify; Ops: build, deploy, IaC, rollback, monitor) | Must Have | Every step in the command map with a non-manual executor resolves to an existing skill, command, or agent; skill-lint CI gate passes |
| FR-6 | Skills consume the previous step's outputs (issue, PRD entry, HLD, LLD) so no step starts from a blank page | Must Have | Architect design-feature reads the issue; dev-tdd reads the approved LLD; qa-plan-tests reads acceptance criteria from the PRD |
| FR-7 | Independent review runs in a separate context from generation (reviewer subagents: architect, PM, QA, ops-release, spec-conformance) | Must Have | Spec-conformance review runs in a different context window from the implementer |
| FR-8 | A Codex CLI surface mirrors the Claude Code skill surface for OpenAI Codex users. **Not maintained since 2.10.0 (2026-09-04)**: `ai/codex/` stays in the repo for reference, no release validates it, and new capabilities are not mirrored | Deferred | `ai/codex/` install script wires AGENTS.md and hooks in a product repo (last verified on 2.9.x) |

### 5.3 Enforcement and Gates

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-9 | Hooks enforce process at tool-use time: no implementation without a valid `.hitl/current-change.yaml` and approved design; domain boundaries checked on write | Must Have | Editing `src/` without an approved LLD is blocked by the PreToolUse hook; cross-domain writes outside the approved manifest domain are flagged |
| FR-10 | Design gates require explicit human approval (scope, HLD, LLD, decision packet) recorded in the change file | Must Have | `approvals.architecture: approved` must be present before implementation skills proceed; `/hitl:ta-approve` records the decision |
| FR-11 | Hooks degrade gracefully: optional dependencies missing means silent no-op, never a broken session | Must Have | With PyYAML absent, `check-domain-boundary.sh` no-ops; with `gh` absent, issue sync is skipped silently |
| FR-12 | CI gates catch drift the hooks cannot: catalog drift, skill-lint, breadcrumb matrix, manifest drift | Must Have | `ci/workflows/` templates run green on this repo; a manifest/code mismatch fails the drift check |
| FR-36 | **Readable test scenarios**: one Given/When/Then file per change under the engineering testing directory, QA-owned, written at the test plan step; every scenario has an `SC-` ID its test cites; a fail-closed two-way check at test review and QA verify; the PM reviews alongside the build (never a gate before RED unless `scenario_review_gate` is set); anyone adds by chat (`/hitl:qa-scenarios`) or on a shared page; plain markdown, not Gherkin. Shipped 2.17.0 ([#148](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/148), [requirements](readable-test-scenarios/requirements.md), [design](../design/readable-test-scenarios/01-design.md)) | Should Have | `ci/test-scenarios/check_scenarios.py` exits 2 on a scenario with no test and no recorded reason, or an acceptance or integration test citing no scenario, and never prints a traceback (54 tests); `qa-plan-tests` writes the file; the check runs in `qa-review-tests` and `qa-verify-quality` |
| FR-37 | **Breadcrumb as a band**: the breadcrumb drawn as a persistent band above the prompt by a draw-only Claude Code mod inside the HITL plugin, switched by a team setting in `.hitl/config.yaml` (`breadcrumb: text`, the default, `band`, or `both`); one renderer (the shell `_steps.sh` writes a four-line cache the mod draws), the text breadcrumb stays the floor everywhere a mod cannot draw. Shipped 2.18.0 ([#150](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/150), [requirements](breadcrumb-mod/requirements.md), [design](../design/breadcrumb-mod/01-design.md)) | Should Have | `claude plugin validate` lists exactly `ui.render{component=AbovePrompt}` and `turn.complete` and the four calls `fs.exists`, `fs.read`, `ui.resolve`, `ui.invalidate`; `ci/breadcrumb-mod` fails on anything else; the breadcrumb matrix passes with the band case; default output byte-identical to 2.17.0 |

### 5.4 Traceability and Audit

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-13 | Every change carries an unbroken chain: issue → PRD requirement → HLD/LLD → code → tests → deployment record | Must Have | `/hitl:architect-verify-traceability` confirms the chain intact before merge |
| FR-14 | Step completion is synced to the GitHub issue as comments, making progress visible without asking anyone | Should Have | `sync-step-to-issue.sh` posts step transitions when `gh` is available |
| FR-15 | Session activity is summarized to session logs automatically | Should Have | `write-session-summary.sh` writes to `docs/session-logs/` on session end |
| FR-16 | Downstream impact of a change is captured as an impact brief the PM can read (what changed, in their mental model) | Must Have | `/hitl:dev-impact-brief` produces the brief; PM review is a step in the delivery spine |
| FR-32 | A **Team Pulse** page shows, per person and per epic, what is moving, what is waiting on someone else, and who can unblock it, generated from GitHub by `/hitl:team-pulse` with no manual edits. Epic checkbox lists are read as slice trees with a state per slice; a self-reported `Hours:` line renders milestone progress; hook and gate comments never count as human activity. Wording is mutual help, never appraisal. `audience: team` (default) gives every contributor the same page; `audience: leads` adds a leads-only planning section and still offers the team page. Refresh is schedulable | Should Have | On a repo with one or more epics and two or more contributors the page is produced in one run with no manual edits; every event and number links to its GitHub source; the attention strip lists exactly the epics with a flag and the PRs past the configured thresholds; hook and gate comments never appear as human activity; a valid `Hours:` line renders a milestone bar and an invalid one is ignored; with `audience: leads` the leads-only section never appears on the team page and the team page contains nothing the leads page lacks; with `publish: file` the skill works without an Artifact tool |

### 5.5 Onboarding Paths

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-17 | A greenfield project can start from a PRD (`/hitl:dev-start-from-prd`): hooks wired, manifest initialized, first issue created, system design produced before any per-change work | Must Have | Path completes on a fresh repo; design gate blocks the delivery loop until approved |
| FR-18 | A brownfield project can onboard without a retroactive PRD (`/hitl:dev-start-brownfield`): codebase mapped, manifest generated from source, existing architecture reverse-engineered into docs, registries seeded | Must Have | Path completes on an existing codebase; onboarding initializes the PRD *shell* (`docs/01-product/prd.md` with personas and format, no back-filled features) so the PM/QA skills activate; the entry skills (`pm-add-feature`, `pm-design-feature`) also establish it on first run if onboarding was skipped, and read-only PM/QA skills report "no requirements yet" rather than failing when §5 is empty |
| FR-19 | A migration can onboard with a migration brief replacing the PRD (`/hitl:dev-start-migration`), sliced BI-driven | Must Have | Migration Slice workflow available; brief gates design work |
| FR-20 | Adoption is graduated: a team can take only the conventions layer (Level 1) and add gates later | Should Have | Adoption Ladder documented in README; Level 1 requires only CLAUDE.md + shared rules |

### 5.6 Distribution and Updates

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-21 | Installable as a Claude Code plugin from a public marketplace in two commands, no SSH key or GitHub account required | Must Have | `claude plugin marketplace add pappar/hitl-claude-plugin && claude plugin install hitl@hitl` succeeds on a clean machine |
| FR-22 | In-place update via `/hitl:dev-update` | Should Have | Update completes without re-wiring hooks manually |
| FR-23 | The plugin repo (`hitl-claude-plugin`) is generated from this source-of-truth repo by the plugin repo's `scripts/build.sh`; fixes land in `ai/claude/` here and are rebuilt, never patched downstream | Must Have | Build reproduces the published surface; release flow (version bump, changelog, tag, marketplace pin) documented |
| FR-24 | A white-label offline distribution (HumAIn-branded zip, no external dependencies) can be generated for companies that cannot install from a public marketplace | Should Have | `tools/scripts/make-release.sh <version>` produces `humain-<version>.zip` from this repo |
| FR-25 | The onboarding → customer-delivery bridge is codified: a `platform` workflow (Survey → Verify → Deliver → Operate → Ready, plus migration-only Parity and Cutover) driven by a machine-readable readiness register at `docs/04-operations/platform-readiness.yaml`; onboarding persists pipeline/observability verdicts to it; the roadmap is generated from it (`/hitl:ops-plan-platform`); Tier 2+ production deploys are hard-blocked until `delivery_ready` or waived (plugin issue #21; design: `docs/design/platform-bootstrap/`) | Must Have | Gate: `ci/hooks/test_check_platform_ready.py`; catalog verify covers `platform`; brownfield/greenfield/migration all hand off to the roadmap |
| FR-26 | A **compound agentic system** delivery surface governs products that are a graph of deterministic services, simple agents, and deep agents with sync and asynchronous A2A edges: the design classifies each component and names the orchestration pattern, marks the determinism boundary, models A2A/inter-component contracts as manifest `facade_apis`, bounds each agent to necessary-and-sufficient privilege and an approved-tool set (declared, validated, and surfaced as generated posture matrices), and makes each **agent** independently evaluable plus one end-to-end flow, with a gated observability + PM eval-console declaration. HITL governs the design; it ships no runtime, messaging backbone, live dashboard, or eval engine (EPIC #10; requirements: `docs/01-product/compound-agentic-surface/requirements.md`; design: `docs/design/compound-agentic-surface/`). **2.2.0 ships the core** (per-agent + e2e eval, declared saga + compensation-gap advisory, observability floor gate); **universal per-component/edge coverage, required-when compensation, and delegated per-interaction authority are re-scoped to 2.3.0** (#42, requirements §4.1) | Should Have | Compound surface selectable in `pm-design-feature`; privilege validator flags over/under-privilege; approved-tool gate blocks unapproved tools; PM can run an independent eval on one **agent**; observability floor gate blocks a missing declaration; two-stage Codex validation (source → built plugin) passes before 2.2.0 ships |
| FR-28 | An **Agentic Design Advisor** encodes agentic-systems expertise as **one runnable intake command** (`hitl:agentic-intake`) that **asks the questions an expert asks**: a thorough intake understands the whole scenario, then **composes a right-sized recommendation report** for the change (a lens with no data contributes no section — the lenses are report **sections**, not separate commands). The report gives per-lens recommendations, a recommended floor, and chosen/rejected. It **recommends** the simplest option that fits (never silently decides), **records** every decision (a skipped recommended control is recorded, never silent), and **hands off** a neutral **`agentic-design-handoff.yaml`** (components + connections + `proposed_kind`s + recommendation IDs + target-path hints) — **not** a manifest. A **human authors** the real manifest in the design phase, and the compound-agentic surface (#10) **validates** it — the Advisor stays in the PM/elicitation lane and authors no design artifact (not even a `kind:` field). A **deploy report section** surfaces the **build-vs-buy** decision (managed-by-default), **records** it for a human to carry to the platform/ops track, and provisions nothing. It is the right-sizing **front door** to FR-26 and the agentic instance of the best-practice-advisory (#8). HITL governs the design; the Advisor ships no runtime (requirements: `docs/01-product/agentic-design-advisor/requirements.md`; design: `docs/design/agentic-design-advisor/`). **Shipped as 2.3.0 (EPIC #35).** | Should Have | Intake composes a proportionate recommendation report; the recommended floor is recorded and a skip is never silent (owner/reason recorded); every menu decision is recommended + recorded + overridable; the output is a decision record + a **neutral handoff** (no authored manifest field, not even `kind`), and a human authors the manifest that #10 then validates — the Advisor authors no design artifact |
| FR-29 | **First Pass** — a right-sized, **thin-whole-first, skip-with-record** way to run any workflow, for teams (PMs especially) who want to ship a basic version fast and iterate. It is a *first pass* at v1 fidelity you then deepen — not a "faster" method that implies the full method is slow; it leverages HITL's think-holistically-implement-incrementally philosophy (a thin pass through the whole, then deepen). After HITL determines the tiered step plan, the team may **skip individual steps** it chooses and proceed to build; every skip is **recorded, never silent** (`step, criticality, actor, reason, timestamp, deferred-or-declined-or-starter`) in neutral language. First Pass **extends tiers** (skip within/below what the tier prescribes, on recorded authority) and **protects a floor**: a small tier-scoped set of load-bearing steps (irreversible-ops, security/compliance at higher tiers, the fail-closed validators) is skippable only via an **authorized risk-accepted** record by the accountable role — never silently (a skip ≠ a waiver; a floor skip linked to a hard gate still needs the human-authored waiver). Skipped choices **resurface proactively and politely** — escalating by criticality — at the top of the change's own issue, the next change touching the same area, and incident/postmortem, with the intent to convince (never to block or shame). A skipped step's disposition is **defer** (listed in **one line at the top of the change's issue** so v1 ships and the deferred rigor is tracked; a ticket only when asked for), **decline** (a deliberate choice), or **starter** — where HITL can, it gives the team *something* honest and minimal (marked *needs-enhancement*) to iterate on rather than a gap; e.g. the starter acceptance criterion is simply *"a working version of the system"*, with specific criteria deferred to the enhancement pass. First Pass also keeps interaction **brief** and friction **low**: routine, reversible, in-scope reads/edits proceed without permission prompts; only critical/irreversible/outward actions still prompt (never "bypass all safety"). The skip ledger is durable and referable, so at any later point HITL can point to exactly what was skipped, by whom, and why. Generalizes the FR-28 skip pattern to the whole workflow; reuses tiers, waivers, and the issue model (requirements: `docs/01-product/first-pass/requirements.md`; design: `docs/design/first-pass/`). | Should Have | After the plan is determined, a team can skip a step and proceed; each skip is recorded with actor + reason + disposition and is never silent; a floor step cannot be skipped without the accountable role's authorized risk-accepted record; deferred steps are listed in one line at the top of the change's issue, with a ticket only when asked for; recorded skips resurface politely at the next overlapping change and at incidents; the skip ledger is queryable and lets HITL cite exactly what was skipped and why |


### 5.7 Backlog

Numbers are assigned here when a requirement is proposed, in order, and never reused. A row stays
at **Backlog** until it is scheduled; when it ships, the row moves to its section above with
acceptance criteria. Detail lives in each feature's requirements doc.

| ID | Requirement | Status | Ticket | Requirements |
|----|------------|:------:|:------:|--------------|
| FR-27 | **Metrics generation**: framework-effectiveness metrics derived from HITL's durable artifacts into a local register and report, evidence-class labeled, no phone-home | Backlog | [#22](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/22) | in the epic |
| FR-30 | **Multi-repo workspace**: two access tiers, code repo-scoped, documentation one shared tree readable by all, HITL fully usable by both tiers | Backlog | [#105](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/105) | [multi-repo-workspace/requirements.md](multi-repo-workspace/requirements.md) (slice 0, linked changes, first) |
| FR-31 | **Data layer**: an evidence-based business ontology, source mappings and lineage next to the manifest, derived on brownfield, authored forward on greenfield, kept current per change | Backlog | [#131](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/131) | [data-layer/requirements.md](data-layer/requirements.md) |
| FR-33 | **Single developer mode**: team shape as a plan input, no handoffs to oneself, clean-context substitution recorded where a second reader is lost, questions for the architect and PM batched with assumption-and-proceed, floor unchanged | Backlog | [#135](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/135) | [single-developer-mode/requirements.md](single-developer-mode/requirements.md) |
| FR-34 | **Branch context**: writes that belong to no active change (a new issue's PRD entry, backlog, design docs) go to main, never to another change's branch; one check at the writing command, park or sibling worktree, one way back, issue creation alone never moves a branch | Backlog | [#136](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/136) | [branch-context/requirements.md](branch-context/requirements.md) |
| FR-35 | **Business-rule layer**: rules and workflow steps with evidence, owner, source and status, built in reverse from code and config, forward from the PRD delta and tests, observed where logging exists; reports the gaps between intended, implemented and observed; shares FR-31's evidence model and scorecard; off by default | Backlog | [#131](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/131) | in the epic (Part B); design core in [`../design/data-layer/`](../design/data-layer/) |

---

## 6. Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|------------|--------|
| NFR-1 | Portability | Hard dependencies limited to bash, python3, PyYAML, git | Hooks run on macOS and Linux with stock tooling; optional deps (`gh`, `graphify`) degrade silently |
| NFR-2 | Compatibility | Runtime schema changes are additive only | The `phase` field was added without breaking the v1.0.29/30 change-file surface; `n` retained |
| NFR-3 | Correctness | Catalog derivation is lossless | CI proves derived `workflows.yaml` is byte-equivalent to the runtime file |
| NFR-4 | Regression safety | Breadcrumb rendering is matrix-locked | Every assertion in `ci/breadcrumb/run_matrix.sh` must pass before any hook change merges (271 across 29 cases as of 2.16.1; the script's RESULT line is authoritative) |
| NFR-5 | Tool independence | Process and docs are tool-agnostic; only enforcement hooks are tool-specific | Claude Code primary; the Codex CLI surface exists but is not maintained (FR-8) |
| NFR-6 | Language scope | Process is language-agnostic; automated enforcement checks are Python-first | Non-Python repos get the full process, docs, and gates minus language-specific checks |
| NFR-7 | Overhead | Setup cost is bounded and stated honestly | New project: 1-2 hours; existing project: about 1 day (per README) |

---

## 7. Use Cases

### UC-1: PM turns an idea into a tracked, designed feature

**Actor:** Product Manager
**Precondition:** HITL installed; project onboarded
**Flow:**
1. PM runs `/hitl:pm-add-feature` (or `/hitl:pm-design-feature` for UX-facing work) with the idea.
2. Skill probes for gaps, drafts the requirement with acceptance criteria, creates a draft GitHub issue immediately.
3. On approval, the requirement lands in `docs/01-product/prd.md` as FR-\<ID\> and the issue is updated (title only; body stays as the permanent problem statement).

**Expected outcome:** a precise, testable requirement with an audit trail from idea to issue.
**Error scenarios:** open questions are logged as "gaps to revisit" rather than silently dropped; conflicting requirements are flagged against the existing PRD before writing.

### UC-2: Architect designs from a PM ticket

**Actor:** Architect (or TA)
**Precondition:** issue exists with a problem statement
**Flow:**
1. Architect runs `/hitl:architect-design-feature <issue>`.
2. Impact analysis maps affected domains against the system manifest; ROI trigger checked.
3. HLD generated and gated on approval; then LLD, IaC plan, test case plan, decision packet.
4. TA approves via `/hitl:ta-approve`; `.hitl/current-change.yaml` records `approvals.architecture: approved`.

**Expected outcome:** implementation is unblocked only after an approved, impact-grounded design exists.
**Error scenarios:** implementation attempted before approval is blocked by the PreToolUse hook; design touching an unapproved domain is flagged by the boundary check.

### UC-3: Team onboards an existing codebase

**Actor:** Developer or Architect
**Precondition:** live codebase, no HITL artifacts
**Flow:**
1. Run `/hitl:dev-start-brownfield`; step 0 wires hooks, settings, and 4 default ADR stubs, then requires a Claude Code restart.
2. Codebase mapped; CLAUDE.md customized; system manifest generated from source; existing architecture reviewed into docs; registries seeded.
3. First change issue created; delivery loop begins.

**Expected outcome:** the existing system is governable without inventing a retroactive PRD.
**Error scenarios:** template-only manifest detected and regenerated; missing registries copied from plugin templates.

### UC-4: Production incident, fix first

**Actor:** Ops / Developer
**Precondition:** incident in production
**Flow:**
1. Incident workflow initiates (fix-first spine: the fix precedes full design ceremony).
2. Fix ships under the incident's reordered gates; incident registry updated.
3. Follow-up work (proper design, regression tests) tracked so deferred rigor is not lost.

**Expected outcome:** speed when it matters, with the paper trail caught up afterward instead of skipped.
**Error scenarios:** deferred-regression items block change completion if left dangling.

---

## 8. Success Metrics / KPIs

| Metric | Current baseline | Target | Measurement method |
|--------|:----------------:|:------:|-------------------|
| Teams onboarded and building with HITL | 2 startups (onboarded, pre-first-feature) | 2 teams shipping features through the full loop | First merged change with intact traceability chain per team |
| Process integrity in CI | Green on this repo | Green on every adopting repo | skill-lint + catalog-drift + breadcrumb matrix + manifest-drift gates |
| Traceability at merge | Not yet measured | 100% of Tier 2+ changes pass verify-traceability | `/hitl:architect-verify-traceability` outcomes |
| Gate friction | Not yet measured | Gates cleared same-day median | Issue timestamps between gate request and approval |

---

## 9. Out of Scope

- **Paid governance layer** (cross-team dashboard, managed policy hooks, audit/compliance export, SSO/RBAC): a separate product bet, out of scope for this open-source framework PRD.
- **Design-tool and tracker integrations** (Figma sync, Jira automation): explicitly fenced as a non-goal in the workflow-model design; the UX-artifact floor requires an artifact to exist, not a specific tool.
- **Non-Python automated enforcement checks**: process supports any language; automated checks are Python-first for now (NFR-6).
- **MCP write-tool gating**: known gap; MCP-mediated writes are not yet intercepted by `check-hitl-context` (tracked as an open question below).
- **Retroactive PRDs for brownfield systems**: existing behavior is documented via reverse-engineered technical docs (manifest, HLD, LLD), never a backfilled PRD.

---

## 10. Open Questions

| # | Question | Owner | Status |
|---|---------|-------|--------|
| 1 | Are the Phase-1 default gate sets right? (Cannot be validated from design alone; needs pilot data) | Architect + pilot teams | Open |
| 2 | MCP write-tool gating: how should `check-hitl-context` handle per-tool inputs? | Architect | Open |
| 3 | Skipped steps render as `·` (same glyph as open steps) in the breadcrumb; do they need a distinct glyph? | Architect | Open |
| 4 | Does commercial validation clear the GTM gate (3+ leaders, budget, trigger, 2 pilots)? | PM | Open |
| 5 | Incident-workflow gate list and establishment phasing remain defaults pending pilot | Architect | Open |

---

## How This Document Feeds the Development Process

1. **Architect reads this PRD** → creates HLDs (system architecture) and ADRs (design decisions)
2. **AI reads the HLDs** → generates LLDs (detailed component designs) for architect review
3. **AI reads the LLDs** → generates tests (TDD) and then code
4. **PM reviews the impact brief** → Section 4 (PM mental model update) tells you what changed
5. **PM reviews the demo** → accepts or requests changes based on the acceptance criteria in this PRD
