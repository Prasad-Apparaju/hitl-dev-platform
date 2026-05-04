# agents/

**Claude Code subagent role definitions** — specialized AI roles invoked by skills.

Each `.md` file defines a subagent: its role, responsibilities, what it reads, and how it behaves. Skills spawn these agents to perform focused tasks (code review, spec conformance, QA verification) without cluttering the main conversation context.

| Agent | Invoked by | Role |
|-------|-----------|------|
| `spec-conformance-reviewer.md` | `/check-implementation` | Reviews implementation against LLD and system manifest |
| `architect-reviewer.md` | `/architect:review-design` | Evaluates HLD/LLD quality before implementation |
| `qa-reviewer.md` | `/qa:verify-quality` | Independent quality verification against running build |
| `ops-release-reviewer.md` | `/ops:review-release` | Assesses rollout plan and canary criteria |
| `pm-reviewer.md` | `/pm:review-progress` | Reviews progress against PRD requirements |
| `developer-implementer.md` | `/tdd` | Generates code from failing tests and LLD |

To customize an agent's behavior, edit its `.md` file directly.
