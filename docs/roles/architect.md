# Architect Role Guide

You hold the design and integration gates. You review designs before implementation starts and verify the traceability chain before merge. On small teams you also cover the QA and Ops roles — use the `/qa:` and `/ops:` command namespaces for those activities.

## Your Commands

![Architect slash commands in Claude Code](../images/architect-commands.svg)

| Command | When to use | Gate it covers |
|---------|-------------|----------------|
| `/architect:review-design` | After the developer opens a design PR — before implementation starts | Design PR gate |
| `/architect:verify-traceability` | Final check before approving merge | Integration verification gate |

**When also covering QA:** use [`/qa:review-tests`](qa.md) and [`/qa:verify-quality`](qa.md)

**When also covering Ops:** use [`/ops:review-release`](ops.md) and [`/ops:monitor-canary`](ops.md)

## Your Two Gates

### Gate 1 — Design Review (`/architect:review-design`)
Run after the developer submits a design PR with HLD, LLD, and ADR. Check:
- LLD is precise enough to generate tests from — every method has a signature, error modes are enumerated, preconditions are explicit
- Manifest facade APIs are updated if new domain APIs are introduced
- ADRs are written for all tradeoffs — specific rationale, genuine alternatives, honest consequences

Do not approve implementation until the LLD has `status: approved` in its frontmatter.

### Gate 2 — Integration Verification (`/architect:verify-traceability`)
Final check before approving merge. Confirm the chain is unbroken:

GitHub issue exists → design PR merged → implementation matches LLD → tests cover the spec → impact brief complete → rollout plan approved

Run the feature end-to-end and ask: "Does this actually do what the design said it would?"

## Delegation When Unavailable

| Gate | Substitute | Constraint |
|------|-----------|------------|
| Design approval | Most senior engineer with domain context | Must have context on the affected domain |
| Integration verification | Most experienced engineer on the domain | Architect reviews within 48h |

Gates should not block progress for more than 24 hours.

## Further Reading

- [QA role guide](qa.md) — test review and quality verification
- [Ops role guide](ops.md) — release review and canary monitoring
- [Roles and responsibilities](../playbook/roles.md)
- [Common pitfalls and process tiers](../playbook/common-pitfalls.md)
- [Architect playbook template](../../templates/architect-playbook.md)
- [Manifest governance](../playbook/manifest-governance.md)
