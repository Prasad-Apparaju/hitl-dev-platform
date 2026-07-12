# Ops Engineer Role Guide

You own the release. You take the handoff from QA, assess deployment risk, deploy to canary, monitor go/no-go criteria, and promote or roll back. Your input at design time (canary criteria) is non-blocking; your gate at release is real — you can block any Tier 3+ change.

## Your Commands

![Ops slash commands in Claude Code](../images/ops-commands.svg)

**`/hitl:ops-review-release`** — After the developer completes the impact brief, review the rollout plan, canary criteria, observability readiness, and rollback procedure. Required for Tier 3+.
```
/hitl:ops-review-release

Review the rollout plan for issue #42 — payments refund flow.
Confirm canary percentages and soak times are appropriate, go/no-go
criteria are specific measurable numbers, and rollback is defined.
```

**`/hitl:ops-apply-iac`** — When the change plan includes infrastructure changes, review and apply them with a dry-run gate before any deployment.
```
/hitl:ops-apply-iac

Apply the IaC changes for the payments domain in issue #42.
Run a dry-run first and show me all adds, updates, and deletes
before I confirm the apply.
```

**`/hitl:ops-build`** — Build the app from the release branch, verify the CI artifact, and run a smoke check. Run before every deployment.
```
/hitl:ops-build

Build the release artifact from branch feat/42-refund-flow.
Verify the CI run passed, confirm the artifact digest matches,
and run the smoke suite.
```

**`/hitl:ops-deploy`** — After build and IaC are verified, deploy to the target environment per the approved rollout plan.
```
/hitl:ops-deploy

Deploy issue #42 — payments refund flow — per the approved rollout plan.
Start at 5% canary. Show me the exact deployment command before running it.
```

**`/hitl:ops-monitor-canary`** — During an active canary, read dashboards against go/no-go criteria and produce a promotion or hold recommendation.
```
/hitl:ops-monitor-canary

Monitor the canary for issue #42. Read the payments error rate and
p99 latency dashboards. Compare against the go/no-go criteria in the
approved rollout plan and tell me whether to promote or hold.
```

**`/hitl:ops-plan-platform`** — After onboarding (and any time platform work lands), maintain the platform readiness register and its generated roadmap: what stands between "changes can be made" and "changes can be delivered to customers". `derive` builds/refreshes the register, `roadmap` turns gaps into phased GitHub issues, `status` renders the ribbon, `verify-ready` checks the Definition of Ready. Tier 2+ **production** deploys are hard-blocked until the register says `delivery_ready: true` (or every open gap carries a recorded waiver); staging is never blocked.
```
/hitl:ops-plan-platform status

Show me the platform readiness ribbon, the open gaps by layer,
and any waivers that are about to lapse.
```

## Your Role in the Workflow

**At design time (non-blocking):** When the developer shares the impact brief draft, contribute canary criteria from the incident registry. Your past incident knowledge shapes what thresholds are tight enough for this domain.

**Before release (gate):** Run `/hitl:ops-review-release`. Check that the rollout plan has explicit canary percentages and soak times, go/no-go criteria are specific numbers (not "error rate is low"), rollback is defined, and side-effect safety is assessed for irreversible operations. Required for Tier 3+; advisory for Tier 2.

**IaC changes:** If the change plan includes infrastructure changes, run `/hitl:ops-apply-iac` before deployment. This runs a dry-run plan, presents all changes (adds, updates, deletes) for your approval, and applies only after explicit confirmation. Destructive changes require a second confirmation. The deploy command blocks until IaC shows `status: applied`.

**Build:** Run `/hitl:ops-build` to verify the release branch has a passing CI run and a clean artifact. The skill checks the artifact digest against CI output, runs a smoke check, and records the artifact reference in the HITL context. Never deploy an artifact whose origin you cannot trace to a CI run.

**Deploy:** Run `/hitl:ops-deploy` once build and IaC are verified. The skill reads the rollout plan risk level, confirms the canary configuration with you, presents the exact deployment command before running it, and guides post-deployment verification. For canary deployments it hands off to `/hitl:ops-monitor-canary`.

**During canary (monitoring):** Run `/hitl:ops-monitor-canary` at each promotion step. AI reads the observability data and produces a recommendation — you make the final call. If a criterion fails, pause (do not immediately roll back) and investigate. Most canary "failures" are noise or pre-existing issues; automatic rollback on noise creates churn.

**After incidents:** Update the incident registry with root cause, fix, regression test reference, and canary criteria adjustments. This feeds future releases.

## What You Do Not Own

- Application code
- Product requirements or architecture decisions
- QA verification (that is QA's gate)
- Your approval is required for Tier 3+ releases; for Tier 2, your review is non-blocking but valued

## Progress Breadcrumbs

`/hitl:ops-deploy` shows a 4-step breadcrumb trail. Step 2 (Confirm Config) is an explicit confirmation gate — the skill presents the canary configuration and waits for your approval before executing.

![/hitl:ops-deploy progress breadcrumbs](../images/ops-deploy-flow.svg)

## Further Reading

- [Rollout strategy](../playbook/rollout-strategy.md)
- [Deployment gates](../playbook/deployment-gates.md)
- [Workflow reference — ship steps](../playbook/workflow-reference.md)
- [Incident registry template](../../ai/shared/templates/incident-registry-template.yaml)
- [Deployment manifest template](../../ai/shared/templates/deployment-manifest-template.yaml)
