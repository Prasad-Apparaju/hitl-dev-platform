---
description: Review and apply infrastructure changes defined in the IaC plan. Runs a dry-run, presents all changes for operator approval, applies on explicit confirmation, and verifies state matches the plan.
argument-hint: "[change ID or IaC directory path]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---


# Apply IaC Changes

Review and apply infrastructure changes from the change plan. This is a hard gate — apply only after the plan is reviewed and the operator explicitly approves.

**Input:** $ARGUMENTS (change ID or path to IaC directory)

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Step 1 — Read the IaC plan

1. Read `.hitl/current-change.yaml` — locate the `iac_plan` key
2. If `iac_plan` is absent or `"none"`: "No IaC changes in this plan — skip this step." Stop.
3. List what the plan calls for:
   - Which files are modified (e.g., `infra/rds.tf`, `k8s/deployment.yaml`, `helm/values.yaml`)
   - Change type per file: add / update / delete
   - Whether any change is destructive (data loss, replacement, downtime, irreversible)
4. Identify which application components depend on the infrastructure being changed — prefer a graph query:
   ```
   /graphify query "components depending on infrastructure: <resource-name>"
   /graphify query "services affected by changes to <database|queue|bucket|network>: <resource-name>"
   ```
   Fall back to reading `docs/system-manifest.yaml` directly and checking `dependencies` entries if the graph is unavailable. Include the blast radius in the approval summary (Step 3).
5. Read the IaC files listed in the plan — confirm they exist and match what `iac_plan` describes. Flag any divergence.

---

## Step 2 — Run a dry-run plan

Identify the IaC tool from the project structure and run the appropriate plan command:

| Tool | Detection | Plan command |
|------|-----------|-------------|
| Terraform | `*.tf` files | `terraform plan -out=tfplan` |
| Pulumi | `pulumi.yaml` | `pulumi preview` |
| Helm | `Chart.yaml` | `helm upgrade --dry-run --debug` |
| kubectl | `*.yaml` manifests | `kubectl diff -f <manifest>` |
| AWS CDK | `*.cdk.ts` | `cdk diff` |

Capture and display the full plan output. If the plan fails to run, stop and report the error.

---

## Step 3 — Review and approve (HITL gate)

Present a structured summary:

```
Infrastructure changes to apply
────────────────────────────────
  ADD:    <list resources being created>
  CHANGE: <list resources being updated — what property changes>
  DELETE: <list resources being destroyed>

Affected components:  <list of application services that depend on changed resources>
Destructive changes:  <yes — list them | no>
Estimated downtime:   <yes — resource and estimated duration | no>
Rollback path:        <describe how to revert if apply fails>
```

Ask: "Review the plan above. Type **APPLY** to confirm, or describe what needs to change."

Do not proceed until the operator types `APPLY` or an equivalent clear confirmation.

**If any deletion or resource replacement is present**, require a second confirmation:
"This plan destroys or replaces: `<list>`. This may be irreversible. Type **CONFIRMED** to proceed."

---

## Step 4 — Apply

1. Run the apply command:

| Tool | Apply command |
|------|--------------|
| Terraform | `terraform apply tfplan` |
| Pulumi | `pulumi up` |
| Helm | `helm upgrade <release> <chart> -f values.yaml` |
| kubectl | `kubectl apply -f <manifest>` |
| AWS CDK | `cdk deploy` |

2. Capture the full apply output and display it
3. On success, confirm the actual resources changed match the plan

---

## Step 5 — Verify state

1. Confirm infrastructure is healthy post-apply:
   - Terraform: `terraform show` and check resource status
   - kubectl: `kubectl get <resource>` — verify STATUS is Running/Ready
   - Databases: verify connectivity and schema version match expectations
2. Run any post-apply smoke checks defined in the IaC plan
3. Update `.hitl/current-change.yaml`:

```yaml
iac_plan:
  status: applied
  applied_at: <ISO timestamp>
  apply_output: <summary — N resources added, M changed, K deleted>
```

Report: "IaC applied. `<summary>`. Ready to deploy with `/hitl:ops-deploy`."

---

## Step 6 — Update the deployment view

Check whether `docs/02-design/technical/hld/deployment-view.md` exists.

**If it does not exist:** say "No deployment view found — run `/hitl:architect-review-existing` to generate one from your IaC files." and stop.

**If it exists**, compare what was just applied (from Step 3's plan summary) against the current document:

| What changed in the apply | What to update in deployment-view.md |
|---|---|
| New or removed service / container | Services and Containers table + Infrastructure Diagram |
| New or removed external dependency | External Dependencies table |
| Environment added, removed, or endpoint changed | Environments table |
| CI/CD workflow changed | CI/CD Pipeline diagram |
| Cloud provider, orchestration layer, or IaC tool changed | Summary paragraph + regenerate via Phase 4c |
| Config tuning, secret rotation, version bump of existing service | No update needed |

If any topology-visible change was applied, update the affected sections in place — do not regenerate the entire document unless the changes are structural enough to warrant it. After editing:
- Re-validate: `grep -n '<br' docs/02-design/technical/hld/deployment-view.md` must return empty
- Ask: "Does the updated deployment view look accurate?"

If no topology change occurred, say: "Deployment view unchanged — no update needed." and stop.

---

## Important Rules

- Never skip the dry-run plan — run it on every apply, even for small changes
- The HITL approval gate in Step 3 is mandatory — never auto-apply
- Destructive changes (deletes, replacements) always require a second explicit confirmation
- If apply fails partway through, stop and report the partial state — do not retry automatically; partial state must be diagnosed first
- Record `iac_plan.status: applied` before handing off to `/hitl:ops-deploy` — the deploy skill checks this
