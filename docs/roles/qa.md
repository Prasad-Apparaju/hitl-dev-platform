# QA Engineer Role Guide

You own quality verification — independently, after the developer hands off. Your input at design time is non-blocking (contributing test scenarios to the plan); your gate post-handoff is a real block. Nothing promotes to Ops without your approval on Tier 2+ changes.

## Your Commands

![QA slash commands in Claude Code](../images/qa-commands.svg)

| Command | When to use |
|---------|-------------|
| `/qa:plan-tests` | At design time — review the LLD and query incident history to contribute test scenarios before the TDD cycle starts (non-blocking) |
| `/qa:review-tests` | After RED test generation (step 10) — formal review before implementation begins; verify ACs, LLD edge cases, and incident registry regressions |
| `/qa:verify-quality` | After the developer handoff — independent quality verification against the running build; you block or approve promotion |
| `/qa:report-defect` | When verify-quality finds a blocking issue — structured defect report with AC reference, reproduction steps, and severity |

## Your Role in the Workflow

**At design time (non-blocking):** Run `/qa:plan-tests` when the LLD is shared. Query the incident registry for the domain, identify edge cases and failure modes the developer may miss, and produce a prioritized list of test scenarios. Regression-required scenarios (from past incidents) must be in the test plan before the TDD cycle starts. This is input, not a gate — but the developer must acknowledge each scenario.

**After RED test generation (gate):** Run `/qa:review-tests` after step 10 generates the test suite — before implementation begins. Verify every acceptance criterion has a test, every LLD error mode is exercised, and all relevant incident regressions from the registry are present. The test registry must be updated. Do not approve implementation until coverage is complete.

**After handoff (gate):** Run `/qa:verify-quality`. The developer has delivered a stable build. You run independent verification — verify each AC against the running build, run exploratory testing beyond the happy path, and probe failure modes from the incident registry. If anything fails, run `/qa:report-defect` and block promotion.

**When blocking:** Run `/qa:report-defect` for every issue that blocks promotion. A block without a filed defect is not actionable — the developer cannot prioritize or fix what is not documented. After fixes, a full re-run of `/qa:verify-quality` is required before lifting the block.

## What You Do Not Own

- Writing implementation code
- Architectural decisions (that is the architect)
- Release and deployment decisions (that is Ops)
- You add tests when gaps are found — you do not delete developer-written tests without an explicit reason

## Progress Breadcrumbs

`/qa:verify-quality` shows a 5-step breadcrumb trail. Step 5 (Block or Approve) is the gate — the breadcrumb does not advance past it until you file all defects or post the approval comment.

![/qa:verify-quality progress breadcrumbs](../images/qa-verify-quality-flow.svg)

## Further Reading

- [Common pitfalls — process tiers](../playbook/common-pitfalls.md)
- [Workflow reference — QA steps](../playbook/workflow-reference.md)
- [Test registry template](../../ai/templates/test-registry-template.yaml)
- [Incident registry template](../../ai/templates/incident-registry-template.yaml)
