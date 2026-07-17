# docs/

**Human-readable documentation** — playbooks, role guides, reference material, and patterns.

| Folder / File | What it contains |
|--------------|-----------------|
| `01-product/` | HITL's own PRD (`prd.md`) — the product baseline and **product-level requirements** (`FR-n`); new product requirements append here. (Per-feature *design* requirements — the `CR-n` analysis that feeds an HLD — live with their design under `design/<feature>/00-requirements.md`, cross-linked to the owning `FR-n`.) |
| `playbook/` | Process guides: workflow reference, adoption guide, common pitfalls, migration guide, AI governance, evidence taxonomy |
| `roles/` | Per-role guides: what each role does, which commands they use, and how they interact with other roles |
| `reference/` | Context model rationale — how Claude Code and Codex load context, and how HITL was designed around it |
| `patterns/` | Reusable design patterns: failure mode taxonomy, idempotency keys |
| `design/` | Design packages for HITL's own evolution: `workflow-model/` (shipped as 2.0), `platform-bootstrap/` (issue #21, shipped 2.1.x), `compound-agentic-surface/` (EPIC #10, draft — targets 2.2.0) |
| `changes/` | Schema definitions: `change-context.schema.yaml` (the `.hitl/current-change.yaml` contract) |
| `images/` | SVG and PNG assets used by the docs |
| `validation-guide.md` | Independent-reviewer / Codex guide to verifying a release: requirement→design→test map plus the exact checks to run |
| `quick-start.md` | Step-by-step setup for new and existing projects |
| `customization-guide.md` | Full command-to-file map — where to edit every skill, agent, hook, and template |
| `reference.md` | Quick reference card for commands and workflow steps |

Everything in this directory is for **people to read**. The AI runtime lives in `ai/claude/` (including `ai/claude/agents/`, `ai/claude/commands/`, `ai/claude/hooks/`).
