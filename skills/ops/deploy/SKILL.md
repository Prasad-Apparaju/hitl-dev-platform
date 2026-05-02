---
name: ops-deploy
description: Deploy a verified build artifact to a target environment following the approved rollout plan. Reads rollout strategy from .hitl/current-change.yaml and executes deployment with canary configuration where applicable.
argument-hint: "[environment: staging|canary|production] [branch or artifact reference]"
disable-model-invocation: true
---

# Deploy to Environment

Deploy a verified artifact to the specified environment, following the approved rollout plan.

**Input:** $ARGUMENTS (environment name and artifact reference)

**Refusal rule:** If `.hitl/current-change.yaml` is missing or `build.status` is not `ready`, stop: "No verified build found. Run `/ops:build` first."

---

## Step 1 — Pre-deployment checks

1. Read `.hitl/current-change.yaml` — confirm all three are true:
   - `build.status: ready` and `build.artifact` is recorded
   - `rollout_plan` is present (from the approved impact brief)
   - `iac_plan` is either empty/`none` or `iac_plan.status: applied` — do not deploy before IaC is applied
2. Confirm the target environment is healthy — check existing deployment status before deploying on top of it
3. Check for active incidents affecting this environment or the domains being deployed — prefer a graph query:
   ```
   /graphify query "active incidents in environment: <environment>"
   /graphify query "recent incidents affecting domain: <domain-name>"
   ```
   Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. If no incidents exist, say so explicitly — do not skip the check.

If any pre-check fails, list all failures and stop. Do not deploy into an active incident.

---

## Step 2 — Confirm deployment configuration

Based on the rollout plan risk level:

| Risk level | First target | Canary % | Soak time |
|-----------|-------------|----------|-----------|
| Low | production | 100% direct | — |
| Medium | staging → production | 100% | 24h staging soak |
| High | canary | 5–10% | 4h per step |
| Critical | canary | 1% | 24h per step, manual gate each step |

1. State the risk level and deployment configuration based on the rollout plan
2. Confirm with the operator: "Deploying `<artifact>` to `<environment>` at `<canary%>`. Confirm?"
3. Do not proceed without explicit confirmation

---

## Step 3 — Execute deployment

1. Read the project's deployment configuration (e.g., `deploy/`, `k8s/`, Helm charts, Terraform outputs, CI deploy job)
2. Present the exact deployment command before running it
3. On confirmation, execute the deployment
4. Monitor progress — watch for error logs or failed health checks during rollout
5. Confirm the new artifact version is serving traffic: health endpoints, version endpoints, or deployment status output

---

## Step 4 — Post-deployment verification

1. Run the manual verification scenarios from the impact brief (Section 3 — deployment-time checks)
2. Confirm the deployment is stable and no error rate spike is visible in observability
3. Update `.hitl/current-change.yaml`:

```yaml
deployment:
  environment: <environment>
  artifact: <artifact-reference>
  canary_percentage: <N or 100>
  deployed_at: <ISO timestamp>
  status: deployed
```

For canary deployments: "Deployed at `<N>%`. Run `/ops:monitor-canary` to assess go/no-go criteria before promoting."
For direct deployments: "Deployed to `<environment>`. Run manual verification from the impact brief."

---

## Important Rules

- Never deploy before IaC changes are applied — check `iac_plan.status` before every deployment
- Never skip the canary step for High or Critical risk changes
- Present the exact deployment command before running it — the operator must confirm
- Do not deploy into an environment that already has an active incident
- A deployment that fails health checks mid-rollout should be paused and investigated — not automatically rolled back without diagnosis
