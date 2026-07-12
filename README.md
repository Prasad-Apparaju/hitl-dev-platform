
# HITL AI-Driven Development

![HITL platform overview — Human-AI convergence loop, shared team memory, and AI executing from docs](docs/images/hitl-dev-platform-infographic.svg)

## What this is

A document-driven delivery model for teams that use AI heavily in non-trivial software work. AI produces code faster than teams can review it — and does so confidently even when wrong. This process makes that speed safe by organizing the team around documentation as the shared source of truth. AI generates; humans shape, review, and decide.

**Where this is especially useful:** migrations, cross-domain feature work, AI/agentic systems, regulated or high-audit environments, and platform teams introducing shared conventions.

**Where a reduced version is more realistic:** normal SaaS feature teams, internal tools, and full-stack product teams shipping weekly. The most valuable subset for these teams: shared AI rules, docs-first for non-trivial changes, traceability for important decisions, and explicit rollout notes for risky releases. See the [Adoption Ladder](#adoption-ladder) for a lightweight entry path.

**Where this is not a good fit as written:** understaffed startups, teams without good CI or test discipline, teams where most work is small bugfixes and iterative UX changes, or teams without an architect or senior lead who can own the review gates.

> **AI tool note:** This guide uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the primary AI coding tool. The process works with any AI coding assistant that supports auto-loaded project rules. The principles and workflow are tool-agnostic; only the enforcement hooks are tool-specific.

> **Language note:** Enforcement tooling currently targets Python codebases. The process and documentation workflow are language-agnostic — only the automated checks are Python-first.

**Yes, this looks like waterfall.** Design before code. That is intentional. Waterfall failed because the gap between "design done" and "working software" was months. With AI, that gap is often much shorter — you get waterfall's rigor with less wait. Without this discipline, AI-generated code drifts: each session invents its own patterns, and by the time you have customers, you face a rewrite that is much harder than designing coherently from the start.

---

## Repo Map

```
hitl-dev-platform/
│
│  ── AI runtime (Claude Code loads and executes these) ──────────────────────────
├── ai/claude/
│   ├── [skill folders]   Slash command prompts — /hitl:dev-practices, /hitl:dev-tdd, /hitl:architect-*, /hitl:pm-*, /hitl:qa-*, /hitl:ops-*
│   ├── agents/           Subagent role definitions (code reviewer, QA verifier, ops reviewer, etc.)
│   ├── commands/         Lightweight single-purpose prompts (review-design, verify-traceability, etc.)
│   └── hooks/            Enforcement hooks — fire at PreToolUse/PostToolUse during every Claude session
│
│  ── Codex CLI (parallel surface for OpenAI Codex users) ──────────────────────
├── ai/codex/                AGENTS.md, hooks, install script — mirrors the Claude Code skill surface
│
│  ── CI enforcement (workflows + scripts they invoke) ──────────────────────────
├── ci/
│   ├── workflows/        Copyable CI workflow templates — copy to .github/workflows/ in your product repo
│   └── manifest-drift/   Manifest drift checker (invoked by CI workflows)
│
│  ── Developer tooling (run from the command line) ─────────────────────────────
├── tools/
│   ├── [tool folders]    Python tools: preflight checker, manifest generator
│   └── scripts/          init-project.sh — bootstraps a product repo
│
│  ── Human-readable documentation ─────────────────────────────────────────────
├── docs/
│   ├── [playbook etc.]   Playbooks, role guides, patterns, reference, quick-start
│   └── examples/         Worked examples of the process applied to specific project types
├── ai/shared/templates/            Document templates to copy into product repos (PRD, ADR, manifest, etc.)
```

---

## Use This In Your Project

Once installed, this is the welcome banner that appears at the start of every Claude Code session:

![HITL welcome banner — shown at the start of every Claude Code session](docs/images/welcome-banner.svg)

Pick the path that matches where you are:

| Situation | Start here | Time |
|-----------|-----------|------|
| **New project** — want conventions and docs-first from day one | [Quick Start — New Project](docs/quick-start.md#quick-start--new-project) | 1-2 hours |
| **Existing project** — want to adopt the process on a live codebase | [Quick Start — Existing Project](docs/quick-start.md#quick-start--existing-project) | 1 day to set up |
| **Migrating a backend** — using AI to rewrite or modernise a system | [Migration Guide](docs/playbook/migration-guide.md) | Varies by system size |
| **Just the conventions layer** — one `CLAUDE.md` and shared AI rules, nothing else | [Adoption Ladder — Level 1](#adoption-ladder) | 1 hour |
| **Not sure** — want to understand what you're getting into first | [Adoption Ladder](#adoption-ladder) → pick a level | Start at Level 1 |

### By Role

| Role | Commands | Guide |
|------|----------|-------|
| **Developer** | `/hitl:dev-practices`, `/hitl:dev-generate-docs`, `/hitl:dev-tdd`, `/hitl:dev-apply-change`, `/hitl:dev-check-conventions`, `/hitl:dev-impact-brief`, `/hitl:dev-conclude`, `/hitl:dev-review-lld-adherence`, `/hitl:dev-review-security` | [Developer guide](docs/roles/developer.md) |
| **Product Manager** | `/hitl:pm-add-feature`, `/hitl:pm-design-feature`, `/hitl:pm-prioritize`, + 6 more | [PM guide](docs/roles/pm.md) |
| **Architect** | `/hitl:architect-design-system`, `/hitl:architect-design-feature`, `/hitl:architect-review-code` | [Architect guide](docs/roles/architect.md) |
| **Technical Advisor** | `/hitl:ta-approve` | Approve/reject design gates (scope, HLD, LLD, decision packet) |
| **QA Engineer** | `/hitl:qa-plan-tests`, `/hitl:qa-review-tests`, `/hitl:qa-verify-quality`, `/hitl:qa-report-defect` | [QA guide](docs/roles/qa.md) |
| **Ops Engineer** | `/hitl:ops-build`, `/hitl:ops-deploy`, `/hitl:ops-plan-platform`, `/hitl:ops-apply-iac`, `/hitl:ops-rollback`, + 8 more | [Ops guide](docs/roles/ops.md) |

---

## Prerequisites

| Dependency | Required | Used by |
|---|---|---|
| `bash` | Hard | All hooks |
| `python3` | Hard | All hooks (JSON/YAML parsing) |
| `PyYAML` (`pip install pyyaml`) | Hard | `check-domain-boundary.sh`, `write-session-summary.sh` — hooks silently no-op if missing |
| `git` (inside a git repo) | Hard | `write-session-summary.sh`, overall workflow |
| `gh` (GitHub CLI) | Recommended | Step → issue comment sync in `sync-step-to-issue.sh`; skipped silently if absent |
| `graphify` (`pip install graphifyy`) | Optional | `rebuild-graph.sh`; skipped silently if absent |

Claude Code itself must be installed. No SSH key or GitHub account is needed to install this plugin — see [Troubleshooting](#troubleshooting) if the install fails.

---

## Install

**First time — install the plugin:**

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code after installing.

**To update later — ask Claude:**

```
/hitl:dev-update
```

That's it. `/hitl:dev-update` pulls the latest version, shows what changed, and tells you when to restart. Do not re-run the install commands to update.

---

## What happens when you install

The plugin is installed at the user level — it's available across all your Claude Code sessions. Here's exactly what that means:

**What is global (affects all projects):**
- `/hitl:*` commands appear in Claude Code's command palette everywhere. This is a current limitation of how Claude Code loads plugin skills — there is no per-project skill visibility yet. If you run a HITL command in a non-HITL project, the skill detects the missing `.hitl/` directory and stops with a setup prompt rather than doing anything.

**What is per-project (opt-in only):**
- Enforcement hooks (context checks, domain boundary, session summary) only fire in projects where you explicitly ran a start skill. They are wired into `.hitl/hooks/` and `.claude/settings.json` inside the project directory. No `.hitl/` directory means no hooks, no banner, no HITL activity of any kind.

**Net result:** Installing the plugin adds commands to your palette. Nothing enforces anything, blocks anything, or injects any output into any project until you opt that project in by running a start skill.

---

## Opting a project in

Open Claude Code in your project directory and run the command that matches your situation:

| Situation | Command |
|-----------|---------|
| New project — greenfield from a PRD | `/hitl:dev-start-from-prd` |
| Existing codebase — adopt the process | `/hitl:dev-start-brownfield` |
| Migrating a system | `/hitl:dev-start-migration` |
| Already set up — start a change | `/hitl:dev-practices` |

### Optional: Graphify (knowledge graph — recommended for Level 4+ systems)

The HITL process works fully without Graphify. On systems with many domains or large design doc sets, [Graphify](https://github.com/safishamsi/graphify) acts as a retrieval accelerator: skills run targeted graph queries instead of reading the full `system-manifest.yaml` on every operation, cutting token cost and keeping AI grounded when docs would otherwise exceed the context window.

```bash
uv tool install graphifyy
graphify claude install
```

**Billing note for Claude subscription users (no API key):** The initial build (`graphify .`) runs LLM extraction over your docs. Graphify's auto-detect skips the subscription backend — pass it explicitly to avoid charging API credits:

```bash
graphify . --directed --no-viz --backend claude-cli     # initial build
graphify extract . --backend claude-cli                 # headless re-extraction
```

Do **not** put `ANTHROPIC_API_KEY` in `.env` if you are on a subscription — that routes builds to the paid API. The PostToolUse hook (`rebuild-graph.sh`) does code AST re-extraction only and never calls an LLM, so it is always free.

If you have an API key and want to use it: `graphify . --directed --no-viz` (no extra flag needed).

The PostToolUse hook triggers an incremental rebuild automatically after every design doc edit.

---

## Troubleshooting

### `claude plugin install` fails with "Host key verification failed"

`marketplace add` succeeds but `plugin install` tries SSH and fails on machines with no GitHub SSH key configured:

```
✘ Failed to install plugin "hitl@hitl": Failed to clone repository:
  No ED25519 host key is known for github.com and you have requested strict checking.
  Host key verification failed.
  fatal: Could not read from remote repository.
  Please make sure you have the correct access rights and the repository exists.
```

The repo is public — the error is about SSH, not permissions. Fix:

```bash
# Trust GitHub's host key
ssh-keyscan github.com >> ~/.ssh/known_hosts

# Force GitHub clones over HTTPS (needed when no SSH key is present)
git config --global --add url."https://github.com/".insteadOf "git@github.com:"
git config --global --add url."https://github.com/".insteadOf "ssh://git@github.com/"

# Retry
claude plugin install hitl@hitl
```

> Note: use `--add` on both `git config` calls so the second doesn't overwrite the first.

This is a known gap in `claude plugin install` — `marketplace add` already falls back to HTTPS automatically; `plugin install` does not yet.

---

## Opting a project out

To stop HITL from running in a specific project, remove the two things Step 0 created:

```bash
# Remove hook wiring (hooks stop firing immediately)
rm -rf .hitl/hooks/
rm .claude/settings.json   # or edit it to remove the "hooks" block if you have other hooks

# Optionally remove all HITL tracking files
rm -rf .hitl/
```

The plugin itself and its commands are unaffected — other opted-in projects continue to work.

## Removing the plugin entirely

```bash
# 1. Uninstall the plugin
claude plugin uninstall hitl@hitl

# 2. Clean up any projects you had opted in
rm -rf .hitl/hooks/ .claude/settings.json .hitl/
```

Restart Claude Code after uninstalling. The `/hitl:*` commands will disappear from the palette.

---

## What you get by adopting this

| Outcome | How |
|---------|-----|
| **Every piece of code traces back to a reviewed decision** | Issue → design PR → LLD → code → tests → traceability check at integration verification |
| **AI generates code that matches what the team agreed** | LLD is the spec AI executes. Convention checker + TDD + two-round review enforce compliance. |
| **New team members onboard from docs, not from "ask the senior dev"** | HLDs, LLDs, ADRs, and the system manifest ARE the onboarding material |
| **You can change any part of the system without breaking other parts** | System manifest scopes each domain. Facade APIs define the contracts between them. |
| **QA and Ops are never surprised by a deployment** | Downstream impact brief communicates what changed. Canary criteria come from the incident registry. |
| **Past mistakes don't repeat** | Test registry and incident registry capture every lesson. Impact analysis queries them before every change. |
| **You know whether a technical investment paid off** | ROI estimation at the start, 30/90-day verification after. Actual outcomes documented in the ADR. |
| **Architects delegate without losing coherence** | HLD → LLD decomposition creates disjoint knowledge packets. Developers implement from their LLD alone. |

## Core Concepts in Brief

> AI makes code cheap. This process makes decisions durable.

Design decisions are captured in version-controlled documents — HLDs, LLDs, ADRs, and a System Manifest. All downstream activity (code generation, testing, deployment) is driven from those documents. AI implements what the team agreed; it does not invent it.

→ [Full concepts and rationale](docs/playbook/core-concepts.md) | [Roles and responsibilities](docs/playbook/roles.md) | [System manifest](docs/playbook/system-manifest.md)

## Core Workflow in Brief

1. **Requirements**: GitHub issue (with ROI estimate for Tier 3+ changes)
2. **Design**: Impact analysis → HLD/LLD update → test plan → QA/Ops input → Design PR merge
3. **Build (TDD)**: Generate tests first (RED) → human review → generate code (GREEN) → refactor → convention checks
4. **Verify**: Two-round AI code review → architect code review on GitHub PR → reconcile docs against implementation
5. **Assess + Ship**: Downstream impact brief → risk-rated rollout plan → verify PR completeness → lead integration verification → canary deploy

Of the 31 steps (plus the 19a architect substep): 10 AI-driven, 11 AI-assisted, 11 human-only. Not every change uses all of them — see the [process tiers](docs/playbook/common-pitfalls.md#61-process-tiers-by-change-type) for which steps to abbreviate.

→ [Full 31-step workflow reference](docs/playbook/workflow-reference.md) | [Process overview](docs/playbook/process-overview.md)

---

## Adoption Ladder

**Start here.** You do not need the full process on day one. Pick the level that matches where your team is right now; add layers as the team matures and you see value.

| Level | What you adopt | What you get | Effort |
|---|---|---|---|
| **1. Shared AI rules** | `CLAUDE.md` with coding standards + conventions | Every AI session follows the same rules. Convention drift stops. | 1 hour |
| **2. Docs-first for non-trivial changes** | HLD/LLD before code. ADRs for decisions. | Design is reviewed before code exists. Rework drops. | 1 day |
| **3. Decision packets + traceability** | Decision packet per change. PR template with checkboxes. Traceability CI. | Every PR traces to a reviewed decision. Nothing ships undocumented. | 1 day |
| **4. System manifest + domain facades** | Manifest with domains, files, facades, conventions. Manifest drift checker. | AI stays scoped. Cross-domain drift detected. New team members onboard from the manifest. | 1 week |
| **5. Full workflow** | Incident registry, test registry, rollout planning, ROI checks, deployment gates. | Past mistakes don't repeat. Deployments are risk-rated. Investments are measured. | 1-2 weeks |

Levels 1–3 are the minimum viable adoption — shared conventions, docs-first design, and basic traceability, without the full 31-step workflow.

---

## Deeper Reading

| Topic | Playbook |
|-------|---------|
| Why this process exists + the problem it solves | [Core concepts](docs/playbook/core-concepts.md) |
| Role definitions and responsibilities | [Roles](docs/playbook/roles.md) |
| System manifest and AI context management | [System manifest](docs/playbook/system-manifest.md) |
| Full 31-step workflow + design room | [Workflow reference](docs/playbook/workflow-reference.md) |
| Process tiers, pitfalls, architect scaling | [Common pitfalls](docs/playbook/common-pitfalls.md) |
| Adoption checklist | [Adoption checklist](docs/playbook/adoption-checklist.md) |
| Brownfield adoption baseline sprint | [Adoption guide](docs/playbook/adoption-guide.md) |
| AI governance and security | [AI governance](docs/playbook/ai-governance.md) |
| Evidence taxonomy and open questions | [Evidence](docs/playbook/evidence.md) |
| Manifest ownership and CI enforcement | [Manifest governance](docs/playbook/manifest-governance.md) |
| Skills, commands, agents, hooks — full map | [Customization guide](docs/customization-guide.md) |
| Context model rationale | [Context models](docs/reference/context-models/README.md) |

---

## Known Limitations

- **Enforcement tooling is Python-first.** Manifest drift detection, import analysis, and Semgrep rules target Python codebases. The process and documentation workflow are language-agnostic.
- **CI workflows under `ci/workflows/` are copyable templates.** They are not active for this platform repo. Copy to `.github/workflows/` in your product repo after generating `docs/system-manifest.yaml`.
- **The process depends on human review.** AI generates artifacts faster, but the value comes from humans actually reviewing, challenging, and correcting those artifacts before they become code. Without that review, the process is just faster drift.
- **`/hitl:*` commands appear in the palette in all projects.** Claude Code does not yet support per-project plugin skill visibility — skills from a user-scoped plugin are global. All non-setup skills exit immediately with a setup prompt if run outside a HITL project, so there is no unintended behaviour, but the commands are visible everywhere. Project-scoped install (`claude plugin install hitl@hitl --scope project`) would solve this but has active bugs in Claude Code. Tracked in [pappar/hitl-claude-plugin#5](https://github.com/pappar/hitl-claude-plugin/issues/5); upstream: [#60512](https://github.com/anthropics/claude-code/issues/60512), [#61866](https://github.com/anthropics/claude-code/issues/61866), [#14202](https://github.com/anthropics/claude-code/issues/14202).
