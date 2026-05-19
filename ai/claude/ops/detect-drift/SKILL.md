---
name: ops-detect-drift
description: Compare the live environment against the IaC definition to detect configuration drift — manual changes, out-of-band deploys, or config values that have diverged from what IaC and the vault define. Run before every deployment as a pre-flight check and on a schedule to catch drift between releases. Reports a drift inventory and classifies each item by risk.
argument-hint: "[environment: staging|production] [change ID or 'scheduled']"
disable-model-invocation: true
---

# Detect Configuration Drift

Compare the live environment to the IaC definition and vault state. Drift means someone (or something) changed the running environment without going through IaC — a manual console change, an out-of-band deploy, or a config value set directly on the server. Undetected drift causes deployments to behave differently than expected and makes rollback unreliable.

**Input:** $ARGUMENTS (environment name and either a change ID for pre-deploy checks or `scheduled` for periodic runs)

---

## Progress Banners

Format: `---` line, `**Detect Drift — Step N / 4: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | IaC State Drift | `▶ IaC Drift · ○ Config Drift · ○ Secret Drift · ○ Report` |
| 2 | Config / Env Drift | `✅ IaC Drift · ▶ Config Drift · ○ Secret Drift · ○ Report` |
| 3 | Secret Drift | `✅ IaC Drift · ✅ Config Drift · ▶ Secret Drift · ○ Report` |
| 4 | Risk Report | `✅ IaC Drift · ✅ Config Drift · ✅ Secret Drift · ▶ Report` |

---

## Step 1 — IaC state drift

Run the IaC tool's plan or diff against the **current live environment** — not against a dev workspace. This shows what the IaC tool would change if applied now, which is exactly what has drifted.

| Tool | Drift detection command |
|---|---|
| Terraform | `terraform plan -detailed-exitcode` — exit code 2 = changes exist (drift) |
| Pulumi | `pulumi preview --diff` |
| Helm | `helm diff upgrade <release> <chart> -f values.yaml` (requires helm-diff plugin) |
| Kubernetes | `kubectl diff -f <manifest-dir>/` |
| AWS CDK | `cdk diff` |
| AWS CloudFormation | `aws cloudformation detect-stack-drift --stack-name <name>` |

Classify each detected change:

| Class | Meaning | Example |
|---|---|---|
| **Unauthorized change** | Live resource differs from IaC; IaC did not make this change | Someone resized an RDS instance via console |
| **Pending IaC** | IaC has been updated but not applied yet | Terraform plan shows planned changes for this release |
| **Deleted resource** | IaC defines it; it no longer exists | A K8s ConfigMap was manually deleted |
| **Extra resource** | Exists in live; not in IaC | A manually-created security group |

Only **Unauthorized changes** and **Deleted/Extra resources** are drift. Pending IaC changes are expected — note them but do not flag as drift.

Present a structured inventory:

```
IaC state drift — <environment>
────────────────────────────────
Unauthorized changes:
  ⚠️  aws_db_instance.main — allocated_storage: 100 → 200 (manual resize)
  ⚠️  k8s ConfigMap/app-config — data.MAX_CONNECTIONS: "100" → "500" (manual edit)

Extra resources (not in IaC):
  ⚠️  aws_security_group.sg-12345 — no IaC definition found

Pending IaC (expected for this release):
  ℹ️  aws_lambda_function.processor — runtime: python3.9 → python3.12

Total drift items: 2 unauthorized, 1 extra
```

---

## Step 2 — Config and environment variable drift

Check whether the live config values match what the IaC and vault define. This catches cases where an environment variable was set directly on a running container, a feature flag was toggled in the console, or a config file was edited on a server.

**Kubernetes / container environments:**
```bash
# Compare running env vars against what the IaC Deployment manifest defines
kubectl get deployment <name> -o jsonpath='{.spec.template.spec.containers[0].env}' \
  | jq -r '.[] | "\(.name)=\(.value // .valueFrom)"'
```
Diff the output against the env vars defined in the Helm values or Kubernetes manifest. Flag any variable that:
- Exists in the live deployment but not in the manifest
- Has a different value than the manifest defines
- References a secret path that has changed

**Application config files (if applicable):**
```bash
# For server-based deployments, compare running config against the config IaC deployed
diff <(ssh <server> cat /etc/app/config.yaml) infra/config/<environment>.yaml
```

**Feature flags:**
If the project uses a feature flag service (LaunchDarkly, Statsig, Unleash, etc.), compare the current flag state against what the rollout plan specifies. Flag any flag that is in a different state than expected for this environment.

Report format — same structure as Step 1:

```
Config drift — <environment>
─────────────────────────────
  ⚠️  ENV: MAX_CONNECTIONS — live: 500, manifest: 100 (set directly on container)
  ⚠️  ENV: FEATURE_NEW_CHECKOUT — live: true, rollout plan: false (flag toggled in console)
  ✅  ENV: DATABASE_URL — references vault path, consistent with manifest
```

---

## Step 3 — Secret drift

Check whether secret references in the live environment point to the same vault paths and versions as the IaC defines. This detects:
- Secrets rotated in the vault but not yet redeployed (old version still live)
- Secret paths that were changed in the vault but not updated in IaC
- Secrets set directly as environment variables instead of vault references

**Vault reference checks:**

| Secret manager | Check command |
|---|---|
| HashiCorp Vault | `vault kv get -field=value <path>` — compare path and version against IaC |
| AWS Secrets Manager | `aws secretsmanager describe-secret --secret-id <name>` — check `VersionId` matches what was deployed |
| AWS SSM Parameter Store | `aws ssm get-parameter --name <name>` — verify version and last-modified |
| GCP Secret Manager | `gcloud secrets versions describe latest --secret=<name>` |
| Azure Key Vault | `az keyvault secret show --name <name> --vault-name <vault>` |

Flag:
- Any live secret reference that points to a stale version (vault has a newer version that was not redeployed)
- Any environment where a secret value is set as a plain env var instead of a vault reference
- Any vault path referenced in IaC that no longer exists in the vault

Report:

```
Secret drift — <environment>
─────────────────────────────
  ⚠️  DATABASE_PASSWORD — vault has version 5, live deployment uses version 3 (rotation not redeployed)
  ❌  API_KEY — set as plain env var "sk-abc123...", not a vault reference
  ✅  STRIPE_SECRET_KEY — vault path consistent, version current
```

A `❌` (plain env var containing a secret value) is always a blocker — it must be remediated before deployment.

---

## Step 4 — Risk report and action

Classify the full drift inventory:

| Severity | Criteria | Action |
|---|---|---|
| **Blocker** | Plain secret in env var; unauthorized change to auth, payments, or data layer | Must fix before deploying — drift of this type means the deployment target is not in a known state |
| **High** | Unauthorized infra change that affects this deployment's domains; stale secret version | Investigate and remediate before deploying — the change may conflict with the release |
| **Medium** | Unauthorized change to unrelated domain; extra resource not referenced by this change | Document and schedule IaC reconciliation; can proceed with deployment with lead approval |
| **Low** | Config value differs by a non-functional amount; stale IaC from an older release | Note for next IaC apply; proceed |

Present the risk-rated summary:

```
Drift risk summary — <environment>
────────────────────────────────────
  ❌ BLOCKER (1):   API_KEY set as plain env var — must remediate before deploy
  ⚠️ HIGH (1):      RDS instance resized without IaC — may affect connection pool config
  ℹ️ MEDIUM (1):    Extra security group sg-12345 — unrelated to this change
  ✅ LOW (0):

Recommendation: BLOCKED / PROCEED WITH CAUTION / CLEAR
```

Update `.hitl/current-change.yaml`:

```yaml
drift_check:
  environment: <environment>
  checked_at: <ISO timestamp>
  iac_drift_items: <N>
  config_drift_items: <N>
  secret_drift_items: <N>
  blockers: <N>
  result: blocked | caution | clear
  findings:
    - severity: blocker
      item: "API_KEY set as plain env var"
      action: "Move to vault, redeploy"
```

For **scheduled** runs (no active deployment): post findings to the team channel and open a GitHub issue for any HIGH or BLOCKER items:
```bash
gh issue create \
  --title "Config drift detected in <environment> [<severity>]" \
  --label "ops,drift" \
  --body "Drift detected during scheduled check on <date>.

**Findings:**
<drift inventory>

Run /ops:detect-drift <environment> for the full report."
```

---

## When to Run

| Context | How to trigger | Gate |
|---|---|---|
| Before every Tier 2+ deployment | `/ops:detect-drift <environment> <change-ID>` | `/ops:deploy` checks `drift_check.result: clear\|caution` — blocks on `blocked` |
| Scheduled (between releases) | `/ops:detect-drift <environment> scheduled` | Not a gate — raises issues for remediation |
| After a suspected manual change | On demand | Not a gate — investigation tool |

Recommended schedule for production: daily. Staging: weekly or before any deployment.

---

## Important Rules

- Drift in a domain unrelated to the current change is still reported — it is the Ops lead's call whether to proceed, not the deployer's
- A `blocked` result from this skill must be resolved before `/ops:deploy` runs — deploying on top of unknown drift means the deployment's behaviour is unpredictable
- "We'll fix the drift after the release" is not acceptable for BLOCKER items — the risk is compounded, not deferred
- After remediating drift (applying IaC to reconcile), re-run this skill to confirm `result: clear` before deploying
