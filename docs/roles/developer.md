# Developer Role Guide

You own the full vertical slice — docs, code, tests, IaC, and bugs. AI handles the mechanical production; you handle design judgment, review, and anything that requires understanding the system.

## Your Commands

![Developer slash commands in Claude Code](../images/developer-commands.svg)

**`/hitl:dev-tdd`** — **This is the command for writing code.** Generates tests from the LLD, pauses for your review, then generates the implementation. Full RED → GREEN → REFACTOR cycle.
```
/hitl:dev-tdd

I have been assigned GitHub issue #42. Read the decision packet at
docs/decisions/issue-42.yaml and tell me what I am building,
what domain I am in, and what the test plan requires me to cover.
```

**`/hitl:dev-apply-change`** — Impact analysis before touching code. Identifies affected components, APIs, docs, and tests.
```
/hitl:dev-apply-change 42

Initialise the change context for issue #42 — payments refund flow.
```

**`/hitl:dev-check-conventions`** — Runs semgrep, manifest drift, and convention checks in-chat before CI catches them.
```
/hitl:dev-check-conventions

Check the code I just wrote in src/payments/ against the LLD and
system manifest conventions. Flag any violations.
```

**`/hitl:dev-check-implementation`** — Two-round spec conformance review comparing implementation against the LLD and manifest.
```
/hitl:dev-check-implementation

Review my implementation against docs/02-design/technical/lld/payments/refund-flow.md.
Round 1: structure, security, LLD adherence. Round 2: edge cases and test completeness.
```

**`/hitl:dev-impact-brief`** — Generates the downstream impact brief and rollout plan. Run when the PR is ready.
```
/hitl:dev-impact-brief

Generate the impact brief for issue #42 — payments refund flow.
Include what flows changed, risk assessment, QA scenarios, PM mental model update,
and rollout strategy.
```

**`/hitl:dev-generate-docs`** — Generate HLD, LLD, ADR from a feature description, or reverse-engineer docs from existing code.
```
/hitl:dev-generate-docs

Generate an LLD for the refund flow in the payments domain based on
docs/02-design/technical/hld/payments.md and GitHub issue #42.
```

**`/hitl:dev-conclude`** — Turns a design-room Slack thread into an ADR, GitHub issue, and HLD/LLD updates.
```
/hitl:dev-conclude

We decided in Slack to use idempotency keys for all refund API calls.
Create an ADR and update the payments LLD to reflect this.
```

**`/hitl:dev-practices`** — Loads the full HITL workflow for any Tier 1+ change. Use when you want Claude to walk you through every step.
```
/hitl:dev-practices

I am implementing a refund flow for issue #42. What tier is this
and what steps do I need to follow?
```

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
