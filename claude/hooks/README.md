# hooks/

**Claude Code enforcement hooks** — shell scripts that run automatically during every session.

Hooks fire at Claude Code events (PreToolUse, PostToolUse) to enforce HITL requirements in real time, before a tool call completes. Registered via `claude/plugin/plugin.json`.

| File | Trigger | What it enforces |
|------|---------|-----------------|
| `check-hitl-context.sh` | PreToolUse (Edit/Write) | Blocks source code edits unless `.hitl/current-change.yaml` exists with required fields |
| `check-domain-boundary.sh` | PreToolUse (Edit/Write) | Warns when edits fall outside the change's approved domain paths |
| `rebuild-graph.sh` | PostToolUse (Write to docs/) | Triggers incremental Graphify rebuild after every design doc edit |
| `write-session-summary.sh` | End of session | Writes session log to `docs/session-logs/` |
| `welcome.sh` | Session start | Displays the welcome banner with available commands |
| `hooks.json` | — | Hook registration file read by the Claude Code plugin |

**Git hooks** live separately in `.git/hooks/` (installed by `scripts/init-project.sh`). The pre-commit hook enforces the same HITL context check at commit time.
