# docs/

**Human-readable documentation** — playbooks, role guides, reference material, and patterns.

| Folder / File | What it contains |
|--------------|-----------------|
| `playbook/` | Process guides: workflow reference, adoption guide, common pitfalls, migration guide, AI governance, evidence taxonomy |
| `roles/` | Per-role guides: what each role does, which commands they use, and how they interact with other roles |
| `reference/` | Context model rationale — how Claude Code and Codex load context, and how HITL was designed around it |
| `patterns/` | Reusable design patterns: failure mode taxonomy, idempotency keys |
| `changes/` | Schema definitions: `change-context.schema.yaml` (the `.hitl/current-change.yaml` contract) |
| `images/` | SVG and PNG assets used by the docs |
| `quick-start.md` | Step-by-step setup for new and existing projects |
| `customization-guide.md` | Full command-to-file map — where to edit every skill, agent, hook, and template |
| `reference.md` | Quick reference card for commands and workflow steps |

Everything in this directory is for **people to read**. The AI runtime lives in `skills/` (including `skills/agents/`, `skills/commands/`, `skills/hooks/`).
