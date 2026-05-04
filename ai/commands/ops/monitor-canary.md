---
description: Canary monitoring — read observability dashboards for an active canary deployment and produce a go/no-go recommendation for the next promotion step
argument-hint: "[change ID, canary percentage, and soak time elapsed]"
---

You are monitoring the canary deployment for $ARGUMENTS. Read the observability data and assess against the go/no-go criteria in the rollout plan.

1. Check each criterion in the rollout plan — error rate delta, latency delta, business metric delta
2. Compare current readings against the baseline and the thresholds specified in the rollout plan
3. Flag any criterion that is approaching or exceeding its threshold — do not wait for a breach
4. If all criteria are within thresholds after the soak time: recommend promotion to the next canary step
5. If any criterion fails: recommend pause (not immediate rollback) — document the specific metric and value so the team can investigate before deciding

Output a clear go/no-go recommendation with the metric readings that drove it. The human makes the final call.
