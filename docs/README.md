# docs/

**Human-readable documentation** — playbooks, role guides, reference material, and patterns.

| Folder / File | What it contains |
|--------------|-----------------|
| `01-product/` | Requirements — the **what**. HITL's own PRD (`prd.md`, product `FR-n`) plus per-feature requirements analysis (`<feature>/requirements.md`, the `CR-n` for a feature, cross-linked to its `FR-n`). |
| `playbook/` | Process guides: workflow reference, adoption guide, common pitfalls, migration guide, AI governance, evidence taxonomy |
| `roles/` | Per-role guides: what each role does, which commands they use, and how they interact with other roles |
| `reference/` | Context model rationale — how Claude Code and Codex load context, and how HITL was designed around it |
| `patterns/` | Reusable design patterns: failure mode taxonomy, idempotency keys, compound-agentic systems |
| `design/` | Design — the **how**. Design packages (HLD, ADRs) for HITL's own evolution: `workflow-model/` (shipped as 2.0), `platform-bootstrap/` (issue #21, shipped 2.1.x), `compound-agentic-surface/` (EPIC #10, shipped 2.2.0), `agentic-design-advisor/` (EPIC #35, shipped 2.3.0), `first-pass/` (FR-29, shipped 2.4.0). Each package's *what* lives under `01-product/<feature>/requirements.md`. |
| `announcements/` | Release announcements written for users, not contributors: what shipped, what it changes, how to use it |
| `images/` | SVG and PNG assets used by the docs |
| `releasing.md` | Maintainer runbook: how a version gets from this repo to `claude plugin install hitl@hitl` — the twelve release steps with the exact commands, the two gates, the waiver path, and what has gone wrong before |
| `validation-guide.md` | Independent-reviewer / Codex guide to verifying a release: requirement→design→test map plus the exact checks to run |
| `getting-started.md` | **Start here if you're a developer on a project that uses HITL.** One change walked end to end: the one command you need, what the breadcrumb means, and how to run a lighter process on small work |
| `usage-guide.md` | Scenario reference: new project, brownfield, migration, enhancement, bug fix, incident |
| `quick-start.md` | Setup for a *new* project, from the platform repo (see the note at its top — if you installed via `claude plugin install`, use `getting-started.md`) |
| `customization-guide.md` | Full command-to-file map — where to edit every skill, agent, hook, and template |
| `reference.md` | Quick reference card for commands and workflow steps |

Everything in this directory is for **people to read**. The AI runtime lives in `ai/claude/` (including `ai/claude/agents/`, `ai/claude/commands/`, `ai/claude/hooks/`).
