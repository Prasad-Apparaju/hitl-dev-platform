# ai/claude/

**Claude Code slash command prompts** — the main AI runtime for the HITL workflow.

Each subdirectory is one slash command. The `SKILL.md` file inside it is the prompt Claude executes when you type that command. Skills have a frontmatter header (`name`, `description`, `argument-hint`) that the Claude Code plugin reads to register the command.

| Namespace | Commands |
|-----------|----------|
| *(root)* | `/hitl:dev-practices`, `/hitl:tdd`, `/hitl:apply-change`, `/hitl:generate-docs`, `/hitl:check-conventions`, `/hitl:impact-brief`, `/hitl:conclude`, `/hitl:review-lld-adherence`, `/hitl:review-security`, `/hitl:ta-approve` |
| `/hitl:start-*` | `/hitl:start-prd`, `/hitl:start-brownfield`, `/hitl:start-migration` |
| `/hitl:architect-` | `design-system`, `design-feature`, `review-code` |
| `/hitl:pm-` | `add-feature`, `design-feature`, `prioritize`, `report-bug`, + 4 more |
| `/hitl:qa-` | `plan-tests`, `review-tests`, `verify-quality`, `report-defect` |
| `/hitl:ops-` | `build`, `deploy`, `apply-iac`, `backup-database`, `migrate-database`, + 6 more |
| `/hitl:migrate-` | `review-external-docs` |

To customize a command, edit its `SKILL.md`. Note: `agents/`, `commands/`, and `hooks/` are subdirectories inside `ai/claude/` — they are part of the same AI runtime. Changes take effect on the next Claude Code session.
See [docs/customization-guide.md](../../docs/customization-guide.md) for the full command-to-file map.
