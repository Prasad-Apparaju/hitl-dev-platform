---
name: ops-apply-iac
description: Review and apply infrastructure changes defined in the IaC plan. Runs a dry-run, presents all changes for operator approval, applies on explicit confirmation, and verifies state matches the plan.
argument-hint: "[change ID or IaC directory path]"
disable-model-invocation: true
---

# Apply IaC Changes

Review and apply infrastructure changes from the change plan. This is a hard gate — apply only after the plan is reviewed and the operator explicitly approves.

**Input:** $ARGUMENTS (change ID or path to IaC directory)

---

## Step 1 — Read the IaC plan

1. Read `.hitl/current-change.yaml` — locate the `iac_plan` key
2. If `iac_plan` is absent or `"none"`: "No IaC changes in this plan — skip this step." Stop.
3. List what the plan calls for:
   - Which files are modified (e.g., `infra/rds.tf`, `k8s/deployment.yaml`, `helm/values.yaml`)
   - Change type per file: add / update / delete
   - Whether any change is destructive (data loss, replacement, downtime, irreversible)
4. Read the IaC files listed in the plan — confirm they exist and match what `iac_plan` describes. Flag any divergence.

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

Report: "IaC applied. `<summary>`. Ready to deploy with `/ops:deploy`."

---

## Important Rules

- Never skip the dry-run plan — run it on every apply, even for small changes
- The HITL approval gate in Step 3 is mandatory — never auto-apply
- Destructive changes (deletes, replacements) always require a second explicit confirmation
- If apply fails partway through, stop and report the partial state — do not retry automatically; partial state must be diagnosed first
- Record `iac_plan.status: applied` before handing off to `/ops:deploy` — the deploy skill checks this
