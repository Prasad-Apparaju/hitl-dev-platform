# Developer Role Guide

You own the full vertical slice — docs, code, tests, IaC, and bugs. AI handles the mechanical production; you handle design judgment, review, and anything that requires understanding the system.

## Your Commands

![Developer slash commands in Claude Code](../images/developer-commands.svg)

| Command | When to use |
|---------|-------------|
| `/dev-practices` | Starting any Tier 1+ change — loads the full HITL workflow with the right steps for your change tier |
| `/generate-docs` | Before writing code — generate HLD, LLD, ADR from a feature description; or reverse-engineer docs from existing code |
| `/tdd` | After the LLD is approved — runs the RED → GREEN → REFACTOR cycle, tests first |
| `/apply-change` | Before touching code — impact analysis across components, APIs, docs, and tests |
| `/check-conventions` | At any point — runs semgrep, manifest drift, and convention checks in-chat before CI catches them |
| `/impact-brief` | When the PR is ready — generates the downstream impact brief and rollout plan for the architect to review |
| `/conclude` | After a design-room thread reaches a decision — turns the Slack thread into an ADR, GitHub issue, and HLD/LLD updates |

## Workflow in Brief

1. Open a GitHub issue
2. Run `/apply-change` — understand what you're touching
3. Run `/generate-docs` — draft HLD/LLD before writing code
4. Get architect design approval (`/architect:review-design`)
5. Run `/tdd` — tests first, then code
6. Run `/check-conventions` — fix violations before PR
7. Run `/impact-brief` — downstream impact brief + rollout plan
8. Create the PR — architect runs `/architect:verify-traceability` and `/architect:review-tests` before merge

## Further Reading

- [Full 28-step workflow](../playbook/workflow-reference.md)
- [TDD as design](../../skills/dev-practices/tdd-design.md)
- [Downstream impact](../../skills/dev-practices/downstream-impact.md)
- [Developer playbook template](../../templates/developer-playbook.md)
