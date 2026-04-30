# Architect Role Guide

You hold the quality gates. You review designs before implementation, verify the traceability chain before merge, and — because the team is small — also cover QA and Ops responsibilities. Your four commands map directly to the four gates you own in the workflow.

## Your Commands

![Architect slash commands in Claude Code](../images/architect-commands.svg)

| Command | When to use | Gate it covers |
|---------|-------------|----------------|
| `/architect:review-design` | After the developer opens a design PR — before implementation starts | Design PR gate |
| `/architect:review-tests` | After the TDD cycle — before the PR is created | QA gate |
| `/architect:review-release` | After the impact brief — before merge on Tier 2+ changes | Ops / release gate |
| `/architect:verify-traceability` | Final check before approving merge | Integration verification gate |

## Your Four Gates

### Gate 1 — Design Review (`/architect:review-design`)
Run after the developer submits a design PR with HLD, LLD, and ADR. Check:
- LLD is precise enough to generate tests from (every method has a signature, error modes are enumerated)
- Manifest facade APIs are updated if new domain APIs are introduced
- ADRs are written for all tradeoffs — not strawmen, not "because it's simpler"

Do not approve implementation until the LLD has `status: approved` in its frontmatter.

### Gate 2 — QA Review (`/architect:review-tests`)
Run after the developer completes the TDD cycle. Check:
- Every acceptance criterion has a test
- Every LLD error mode is exercised
- Incident regressions from the registry are present
- Test registry is updated with all new tests

### Gate 3 — Release Review (`/architect:review-release`)
Run after the developer completes the impact brief. Required for Tier 2+. Check:
- Risk level is correctly rated against the risk matrix
- Canary criteria are specific numbers tied to specific metrics (not "error rate is low")
- Rollback procedure is defined and side-effect safety is assessed
- Observability is verified — the change is visible in dashboards

### Gate 4 — Integration Verification (`/architect:verify-traceability`)
Final check before approving merge. Confirm the chain is unbroken:
- GitHub issue exists → design PR merged → implementation matches LLD → tests cover the spec → impact brief complete → rollout plan approved

Run the feature end-to-end and ask: "Does this actually do what the design said it would?"

## Delegation When Unavailable

| Gate | Substitute | Constraint |
|------|-----------|------------|
| Design approval | Most senior engineer with domain context | Must have context on the affected domain |
| QA review | Any team member | Round 2 verify waits for architect return (max 24h) |
| Release review | Senior engineer | Documents judgment calls for architect post-review |
| Integration verification | Most experienced engineer on the domain | Architect reviews within 48h |

Gates should not block progress for more than 24 hours.

## Further Reading

- [Roles and responsibilities](../playbook/roles.md)
- [Common pitfalls and process tiers](../playbook/common-pitfalls.md)
- [Architect playbook template](../../templates/architect-playbook.md)
- [Manifest governance](../playbook/manifest-governance.md)
