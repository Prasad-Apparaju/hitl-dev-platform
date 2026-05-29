# Developer Role Guide

You own the full vertical slice — docs, code, tests, IaC, and bugs. AI handles the mechanical production; you handle design judgment, review, and anything that requires understanding the system.

## Your Commands

![Developer slash commands in Claude Code](../images/developer-commands.svg)

| Command | When to use |
|---------|-------------|
| `/hitl:dev-practices` | Starting any Tier 1+ change — loads the full HITL workflow with the right steps for your change tier |
| `/hitl:dev-generate-docs` | Before writing code — generate HLD, LLD, ADR from a feature description; or reverse-engineer docs from existing code |
| `/hitl:dev-tdd` | After the LLD is approved — generates tests from the LLD, gets your review, then generates the implementation code. Full RED → GREEN → REFACTOR cycle. **This is the command for writing code.** |
| `/hitl:dev-apply-change` | Before touching code — impact analysis across components, APIs, docs, and tests |
| `/hitl:dev-check-conventions` | At any point — runs semgrep, manifest drift, and convention checks in-chat before CI catches them |
| `/hitl:dev-check-implementation` | After TDD — two-round spec conformance review comparing implementation against the LLD and manifest |
| `/hitl:dev-impact-brief` | When the PR is ready — generates the downstream impact brief and rollout plan for the architect to review |
| `/hitl:dev-conclude` | After a design-room thread reaches a decision — turns the Slack thread into an ADR, GitHub issue, and HLD/LLD updates |

## What you receive

The architect hands you a **decision packet** at `docs/decisions/issue-<N>.yaml`. It contains your GitHub issue number, the single domain you're working in, the LLD path that is your implementation spec, the test plan, and the rollout risk level. Read it before opening Claude Code — it is your starting point for everything.

## Workflow in Brief

1. Read your decision packet — `docs/decisions/issue-<N>.yaml`
2. Open the LLD it references — that document drives tests, code, and review
3. Run `/hitl:dev-apply-change` — initialize the change context
4. Run `/hitl:dev-tdd` — generates tests from the LLD, you review them, then it generates the implementation code
5. Run `/hitl:dev-check-conventions` — fix violations
6. Run `/hitl:dev-check-implementation` — two-round spec conformance review against the LLD
7. Run `/hitl:architect-review-code` — architect reviews on GitHub; this creates the PR
8. Run `/hitl:dev-impact-brief` — downstream impact brief + rollout plan added to the PR
9. Architect runs `/hitl:architect-verify-traceability` before merge

## Setup Note: Graphify (recommended for large codebases)

On projects with many domains, install [Graphify](https://github.com/safishamsi/graphify) so the HITL skills query the knowledge graph instead of reading the full `system-manifest.yaml` each time. This is especially valuable for `/hitl:dev-apply-change`, `/hitl:dev-tdd`, and `/hitl:dev-impact-brief` on large systems.

```bash
uv tool install graphifyy
graphify claude install
graphify .
```

## Progress Breadcrumbs

`/hitl:dev-tdd` shows a 7-phase breadcrumb trail through the full Red → Green → Refactor cycle. The human review phase (Phase 2) is an explicit stop — the breadcrumb stays on Review until you approve the tests.

![/hitl:dev-tdd progress breadcrumbs](../images/tdd-flow.svg)

## Further Reading

- [Full 32-step workflow](../playbook/workflow-reference.md)
- [TDD as design](../../ai/claude/dev-practices/tdd-design.md)
- [Downstream impact](../../ai/claude/dev-practices/downstream-impact.md)
- [Developer playbook template](../playbook/developer-playbook.md)
