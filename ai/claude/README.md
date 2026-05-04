# ai/claude/

**Claude Code slash command prompts** — the main AI runtime for the HITL workflow.

Each subdirectory is one slash command. The `SKILL.md` file inside it is the prompt Claude executes when you type that command. Skills have a frontmatter header (`name`, `description`, `argument-hint`) that the Claude Code plugin reads to register the command.

| Namespace | Commands |
|-----------|----------|
| *(root)* | `/dev-practices`, `/tdd`, `/apply-change`, `/generate-docs`, `/check-conventions`, `/impact-brief`, `/conclude` |
| `/start-*` | `/start-prd`, `/start-brownfield`, `/start-migration` |
| `/architect:` | `design-system`, `design-feature` |
| `/pm:` | `add-feature`, `design-feature`, `prioritize`, `report-bug`, + 4 more |
| `/qa:` | `plan-tests`, `review-tests`, `verify-quality`, `report-defect` |
| `/ops:` | `build`, `deploy`, `apply-iac` |
| `/migrate:` | `review-external-docs` |

To customize a command, edit its `SKILL.md`. Note: `agents/`, `commands/`, and `hooks/` are subdirectories inside `ai/claude/` — they are part of the same AI runtime. Changes take effect on the next Claude Code session.
See [docs/customization-guide.md](../docs/customization-guide.md) for the full command-to-file map.
