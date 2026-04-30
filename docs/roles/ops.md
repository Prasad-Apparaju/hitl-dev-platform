# Ops Engineer Role Guide

You own the release. You take the handoff from QA, assess deployment risk, deploy to canary, monitor go/no-go criteria, and promote or roll back. Your input at design time (canary criteria) is non-blocking; your gate at release is real — you can block any Tier 3+ change.

## Your Commands

![Ops slash commands in Claude Code](../images/ops-commands.svg)

| Command | When to use |
|---------|-------------|
| `/ops:review-release` | After the developer completes the impact brief — review rollout plan, canary criteria, observability readiness, and rollback procedure |
| `/ops:monitor-canary` | During an active canary deployment — read dashboards against go/no-go criteria and produce a promotion recommendation |

## Your Role in the Workflow

**At design time (non-blocking):** When the developer shares the impact brief draft, contribute canary criteria from the incident registry. Your past incident knowledge shapes what thresholds are tight enough for this domain.

**Before release (gate):** Run `/ops:review-release`. Check that the rollout plan has explicit canary percentages and soak times, go/no-go criteria are specific numbers (not "error rate is low"), rollback is defined, and side-effect safety is assessed for irreversible operations. Required for Tier 3+; advisory for Tier 2.

**During canary (monitoring):** Run `/ops:monitor-canary` at each promotion step. AI reads the observability data and produces a recommendation — you make the final call. If a criterion fails, pause (do not immediately roll back) and investigate. Most canary "failures" are noise or pre-existing issues; automatic rollback on noise creates churn.

**After incidents:** Update the incident registry with root cause, fix, regression test reference, and canary criteria adjustments. This feeds future releases.

## What You Do Not Own

- Application code
- Product requirements or architecture decisions
- QA verification (that is QA's gate)
- Your approval is required for Tier 3+ releases; for Tier 2, your review is non-blocking but valued

## Further Reading

- [Rollout strategy](../playbook/rollout-strategy.md)
- [Deployment gates](../playbook/deployment-gates.md)
- [Workflow reference — ship steps](../playbook/workflow-reference.md)
- [Incident registry template](../../templates/incident-registry-template.yaml)
- [Deployment manifest template](../../templates/deployment-manifest-template.yaml)
