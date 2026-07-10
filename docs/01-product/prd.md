# HITL AI-Driven Development - Product Requirements Document

**Product:** HITL (Human-In-The-Loop) AI-Driven Development Platform
**Version:** 2026-07-09
**Status:** Draft
**Author:** Prasad (PM)
**Last Updated:** 2026-07-09

> **Provenance note:** this PRD was reverse-engineered from the shipped product (plugin v1.0.30 surface plus the locked workflow-model design on branch `design/workflow-model`). It baselines what HITL *is* so that future requirements have something to diff against. New requirements append here via `/hitl:pm-add-feature`; this document does not retroactively justify past decisions (the design docs and ADRs do that).

---

## 1. Executive Summary

HITL is a document-driven delivery model for teams that use AI heavily in non-trivial software work, packaged as a Claude Code plugin with a parallel Codex CLI surface. AI produces code faster than teams can review it, and does so confidently even when wrong. HITL makes that speed safe by organizing the team around documentation as the shared source of truth: AI generates; humans shape, review, and decide.

The product gives each role (PM, Architect, Technical Advisor, Developer, QA, Ops) AI-powered skills that do the legwork of their step in the delivery process, enforcement hooks and CI gates that keep the process honest without relying on memory or discipline, and a traceability chain from requirement to production (issue → PRD → HLD/LLD → code → tests → deployment) that can be audited after the fact.

Success looks like: teams adopt HITL and ship AI-assisted changes where every change is traceable to an approved design, review gates are demonstrably enforced rather than aspirational, and the process survives team growth and personnel change because it lives in the harness, not in people's heads.

---

## 2. Problem Statement

Four related pains, felt by teams using AI coding tools at scale:

1. **Review cannot keep up with generation.** AI writes code faster than humans review it, and presents wrong code as confidently as right code. Unreviewed AI code reaches production, or review becomes a rubber stamp.
2. **Siloed AI sessions drift.** Each AI session invents its own patterns. Without a shared source of truth, a codebase accumulates inconsistent conventions until a rewrite is cheaper than a fix.
3. **Process exists but is not enforced.** Teams write down their process, then bypass it under deadline pressure. Nobody can tell, from the outside, whether the process was actually followed for any given change.
4. **Leadership cannot prove control.** When an auditor, regulator, or customer security review asks "prove your AI-assisted changes were reviewed and traceable," most teams have nothing to show but git blame and good intentions. (This is the buyer trigger identified in `docs/business/go-to-market-framing.md`.)

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

- **5 workflows** own their step sequence: Greenfield, Brownfield, Migration (establishment), Incident (fix-first), Migration Slice.
- **6 profiles** are named presets over the shared delivery spine: Feature, Enhancement, Fix, Tech Change, Upgrade, Security.
- **5 tags** tune required evidence within a profile: `refactor`, `perf`, `chore`, `tooling`, `infra`.

The human's profile/tag choice only proposes; impact analysis decides the actual steps and required evidence, and a floor of never-skippable steps is enforced regardless. The harness is a force-multiplier, not a rulebook: the owner supplies judgment, the harness supplies legwork, context, and rigor.

The product surface delivering this: 51 role skills, 32 commands, 7 subagent role definitions, 9 enforcement hooks, CI workflow templates, document templates, and a numberless workflow catalog from which the runtime process, the command map, and the breadcrumb are all derived.

---

## 5. Functional Requirements

### 5.1 Workflow Engine and Catalog

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-1 | The process is defined once in a numberless catalog (steps identified by stable key + name + phase, never by global position) | Must Have | Inserting or reordering a catalog step requires zero edits to other docs; `tools/workflow-catalog/` derivation reproduces the runtime `workflows.yaml` losslessly, verified in CI |
| FR-2 | Profiles and tags resolve to a concrete step plan via impact analysis, with the floor enforced regardless of what the human selected | Must Have | Resolution engine tests pass; a change tagged `chore` still hits impact-analysis and docs-reconciled floors |
| FR-3 | Each catalog step declares its executing command and accountable role; the human-readable command map is generated, not hand-maintained | Must Have | `docs/command-map.generated.md` regenerates without drift in CI |
| FR-4 | Every session shows a phase-ribbon breadcrumb of where the change stands (phases + named steps, no global numbering) | Must Have | Breadcrumb matrix (`ci/breadcrumb/`, 204 assertions across 22 cases) passes, including the no-phase fallback |

### 5.2 Role Skills and Commands

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-5 | Each role has skills covering its full journey (PM: 10 skills; Architect: design-system, design-feature, review-code, review-design, verify-traceability; Dev: practices, TDD, generate-docs, apply-change, reviews; QA: plan/review/verify; Ops: build, deploy, IaC, rollback, monitor) | Must Have | Every step in the command map with a non-manual executor resolves to an existing skill, command, or agent; skill-lint CI gate passes |
| FR-6 | Skills consume the previous step's outputs (issue, PRD entry, HLD, LLD) so no step starts from a blank page | Must Have | Architect design-feature reads the issue; dev-tdd reads the approved LLD; qa-plan-tests reads acceptance criteria from the PRD |
| FR-7 | Independent review runs in a separate context from generation (reviewer subagents: architect, PM, QA, ops-release, spec-conformance) | Must Have | Spec-conformance review runs in a different context window from the implementer |
| FR-8 | A Codex CLI surface mirrors the Claude Code skill surface for OpenAI Codex users | Should Have | `ai/codex/` install script wires AGENTS.md and hooks in a product repo |

### 5.3 Enforcement and Gates

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-9 | Hooks enforce process at tool-use time: no implementation without a valid `.hitl/current-change.yaml` and approved design; domain boundaries checked on write | Must Have | Editing `src/` without an approved LLD is blocked by the PreToolUse hook; cross-domain writes outside the approved manifest domain are flagged |
| FR-10 | Design gates require explicit human approval (scope, HLD, LLD, decision packet) recorded in the change file | Must Have | `approvals.architecture: approved` must be present before implementation skills proceed; `/hitl:ta-approve` records the decision |
| FR-11 | Hooks degrade gracefully: optional dependencies missing means silent no-op, never a broken session | Must Have | With PyYAML absent, `check-domain-boundary.sh` no-ops; with `gh` absent, issue sync is skipped silently |
| FR-12 | CI gates catch drift the hooks cannot: catalog drift, skill-lint, breadcrumb matrix, manifest drift | Must Have | `ci/workflows/` templates run green on this repo; a manifest/code mismatch fails the drift check |

### 5.4 Traceability and Audit

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-13 | Every change carries an unbroken chain: issue → PRD requirement → HLD/LLD → code → tests → deployment record | Must Have | `/hitl:architect-verify-traceability` confirms the chain intact before merge |
| FR-14 | Step completion is synced to the GitHub issue as comments, making progress visible without asking anyone | Should Have | `sync-step-to-issue.sh` posts step transitions when `gh` is available |
| FR-15 | Session activity is summarized to session logs automatically | Should Have | `write-session-summary.sh` writes to `docs/session-logs/` on session end |
| FR-16 | Downstream impact of a change is captured as an impact brief the PM can read (what changed, in their mental model) | Must Have | `/hitl:dev-impact-brief` produces the brief; PM review is a step in the delivery spine |

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

---

## 6. Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|------------|--------|
| NFR-1 | Portability | Hard dependencies limited to bash, python3, PyYAML, git | Hooks run on macOS and Linux with stock tooling; optional deps (`gh`, `graphify`) degrade silently |
| NFR-2 | Compatibility | Runtime schema changes are additive only | The `phase` field was added without breaking the v1.0.29/30 change-file surface; `n` retained |
| NFR-3 | Correctness | Catalog derivation is lossless | CI proves derived `workflows.yaml` is byte-equivalent to the runtime file |
| NFR-4 | Regression safety | Breadcrumb rendering is matrix-locked | 204 assertions across 22 cases must pass before any hook change merges |
| NFR-5 | Tool independence | Process and docs are tool-agnostic; only enforcement hooks are tool-specific | Claude Code primary, Codex CLI surface maintained in parallel |
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
| Commercial validation (GTM gate) | 0 of target | 3+ leaders describe the same governance product, name budget + trigger; 2 paid pilots | Validation interviews per `docs/business/customer-validation-script.md` |

---

## 9. Out of Scope

- **Paid governance layer** (cross-team dashboard, managed policy hooks, audit/compliance export, SSO/RBAC): separate product bet, gated on validation interviews. See `docs/business/go-to-market-framing.md`.
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
