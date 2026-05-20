# ai/claude/

**Claude Code slash command prompts** — the main AI runtime for the HITL workflow.

Each subdirectory is one slash command. The `SKILL.md` file inside it is the prompt Claude executes when you type that command. Skills have a frontmatter header (`name`, `description`, `argument-hint`) that the Claude Code plugin reads to register the command.

| Namespace | Commands |
|-----------|----------|
| *(root)* | `/hitl:dev:practices`, `/hitl:dev:tdd`, `/hitl:dev:apply-change`, `/hitl:dev:generate-docs`, `/hitl:dev:check-conventions`, `/hitl:dev:impact-brief`, `/hitl:dev:conclude` |
| `/hitl:dev:start-*` | `/hitl:dev:start-prd`, `/hitl:dev:start-brownfield`, `/hitl:dev:start-migration` |
| `/hitl:architect:` | `design-system`, `design-feature` |
| `/hitl:pm:` | `add-feature`, `design-feature`, `prioritize`, `report-bug`, + 4 more |
| `/hitl:qa:` | `plan-tests`, `review-tests`, `verify-quality`, `report-defect` |
| `/hitl:ops:` | `build`, `deploy`, `apply-iac` |
| `/hitl:dev:` | `review-external-docs` |

To customize a command, edit its `SKILL.md`. Note: `agents/`, `commands/`, and `hooks/` are subdirectories inside `ai/claude/` — they are part of the same AI runtime. Changes take effect on the next Claude Code session.
See [docs/customization-guide.md](../../docs/customization-guide.md) for the full command-to-file map.
