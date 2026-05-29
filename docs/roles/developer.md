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

When the architect completes the design and the TA approves it, GitHub posts a **"Ready for Development"** comment on your assigned issue. That comment contains your decision packet path, your domain, your LLD, and the exact prompt to paste into Claude Code. The issue is your starting point — you do not need to navigate the repo manually.

The decision packet (`docs/decisions/issue-<N>.yaml`) contains your GitHub issue number, the single domain you're working in, the LLD path that is your implementation spec, the test plan, and the rollout risk level. Claude reads it for you when you run `/hitl:dev-tdd`.

## Workflow in Brief

1. Open your assigned GitHub issue — find the "Ready for Development" comment and copy the starting prompt
2. Run `/hitl:dev-tdd` with that prompt — Claude reads the decision packet, loads the LLD, and confirms what you're building before writing any tests
3. Run `/hitl:dev-apply-change` — initialize the change context
4. Continue the TDD cycle — tests, review, then implementation code
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
