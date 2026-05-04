# commands/

**Lightweight Claude Code slash commands** — simpler than skills, no frontmatter.

Commands are single `.md` files with a prompt. Unlike skills (which have structured frontmatter and multi-phase workflows), commands are short focused prompts for specific operations. Claude Code loads them as slash commands via the plugin manifest.

| Command | What it does |
|---------|-------------|
| `architect/review-design.md` | Review HLD/LLD/ADR — approve design before implementation |
| `architect/verify-traceability.md` | Verify issue→design→code→tests→brief chain before merge |
| `ops/review-release.md` | Assess rollout plan and canary criteria before release |
| `ops/monitor-canary.md` | Read dashboards for active canary, produce go/no-go |
| `check-implementation.md` | Two-round spec conformance review (invokes `spec-conformance-reviewer` agent) |
| others | See subdirectories for PM, QA, and workflow commands |

The distinction from `claude/`: commands are stateless one-shot prompts; skills orchestrate multi-step workflows with approval gates and produce artifacts.
