---
name: ops-rollback
description: Execute a rollback of a deployed canary or partial release. Reads the current deployment state and rollout plan, assesses side effects, presents the rollback procedure for operator confirmation, executes, and verifies stability. Use when /ops:monitor-canary recommends a pause and the team decides to roll back rather than investigate forward.
argument-hint: "[change ID or environment]"
disable-model-invocation: true
---

# Execute Rollback

Roll back a deployed change to the previous stable state. This skill is invoked at Step 29 when the team decides to roll back rather than promote.

**Input:** $ARGUMENTS (change ID or environment name)

**Refusal rule:** If the deployment state in `.hitl/current-change.yaml` does not show an active deployment (`deployment.status: deployed`), stop: "No active deployment found for this change — nothing to roll back."

---

## Progress Banners

Format: `---` line, `**Rollback — Step N / 4: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Assess Side Effects | `▶ Assess · ○ Plan · ○ Execute · ○ Verify` |
| 2 | Confirm Plan | `✅ Assess · ▶ Plan · ○ Execute · ○ Verify` |
| 3 | Execute | `✅ Assess · ✅ Plan · ▶ Execute · ○ Verify` |
| 4 | Verify + Record | `✅ Assess · ✅ Plan · ✅ Execute · ▶ Verify` |

---

## Step 1 — Assess side effects before rolling back

Read `.hitl/current-change.yaml`:
- `deployment.artifact` — the deployed artifact
- `deployment.canary_percentage` — what percentage of traffic is affected
- `deployment.deployed_at` — when it was deployed (time window of exposure)
- `iac_plan.migrations` — whether a database migration ran
- `rollout_plan.rollback_path` — the pre-defined rollback procedure

**Before rolling back, assess what the rollback cannot undo:**

| Side effect type | Question to answer |
|---|---|
| Database migrations | Were any migrations run? Is a rollback migration defined, or does rollback require restoring the backup? |
| External API calls | Did the new code make any external API calls (payments, emails, webhooks) during the canary window? Are those calls idempotent or irreversible? |
| Data writes | Did the new code write to the database during the canary window? Is that data compatible with the previous code version? |
| Feature flags | Is the change behind a flag that can be toggled off before rolling back the artifact? |

Present the side effect assessment clearly. The operator must understand what rollback will and will not fix before confirming.

Check the incident registry for this domain — if a past incident describes a similar rollback failure, flag it:
```
/graphify query "rollback incidents for domain: <domain-name>"
```

---

## Step 2 — Confirm the rollback plan

Identify the previous stable artifact:
1. Read `build.artifact` from the previous deployment in `.hitl/current-change.yaml`, or check the deployment history of the environment (e.g., `kubectl rollout history`, deployment logs, container registry tags)
2. Confirm the previous artifact is still available (not garbage-collected)
3. If a database migration ran and has no rollback migration: state explicitly that artifact rollback alone will not restore the prior schema — a backup restore may be required

Present the rollback plan:

```
Rollback plan — <ChangeID>
─────────────────────────
  Current artifact:   <current-artifact>
  Rollback to:        <previous-artifact>
  Canary at rollback: <N>% of traffic affected
  Deployed since:     <duration>

  Side effects that rollback WILL NOT undo:
    - <list each irreversible effect>

  Database:
    - <No migration ran — no DB action needed>
    - <Migration ran, rollback migration exists — will apply>
    - <Migration ran, no rollback migration — manual backup restore required>
    - <Migration ran, data written — assess compatibility>
```

**STOP. Confirm with the operator:**
> "Review the rollback plan above. Understand the side effects that cannot be undone.
>
> Type **ROLLBACK** to confirm, or type **HOLD** to pause and investigate first."

Do not proceed without explicit `ROLLBACK` confirmation. The operator must read the side effects — do not summarize or minimize them.

---

## Step 3 — Execute rollback

**Application rollback:**

| Platform | Rollback command |
|---|---|
| Kubernetes | `kubectl rollout undo deployment/<name>` |
| Helm | `helm rollback <release> <revision>` |
| ECS | Update task definition to previous revision |
| Docker Compose | `docker compose up -d` with previous image tag |
| Heroku | `heroku releases:rollback` |

Monitor the rollout: confirm the previous artifact is serving traffic and the new artifact has been removed from all nodes.

**Database rollback (if applicable):**

- If a rollback migration exists: run it using the same migration tool as the forward migration, then verify the schema matches the previous LLD
- If no rollback migration exists: run `/ops:backup-database restore <change-ID>` — this reads `database_backup.backup_path` from `.hitl/current-change.yaml`, assesses data loss from the window between backup and now, requires `RESTORE` confirmation, executes the restore, and verifies the schema
- If schema compatibility is acceptable (old code can read new schema): accept divergence and document it explicitly in the rollback record — skip the restore

**Feature flag (if applicable):**
Toggle the flag off immediately as a first step — this stops new users from hitting the new code path while the artifact rollback proceeds.

---

## Step 4 — Verify stability and record

1. Confirm the previous artifact version is running: check health endpoints, version endpoints, or deployment status
2. Run the smoke suite against the rolled-back environment:
   ```bash
   npx playwright test tests/e2e/smoke/ --project=chromium
   ```
3. Check the go/no-go criteria from the rollout plan — confirm they are back within baseline thresholds
4. Verify the rollback did not cause new failures (e.g., schema mismatch between old code and new schema)

Update `.hitl/current-change.yaml`:

```yaml
deployment:
  status: rolled-back
  rolled_back_at: <ISO timestamp>
  rolled_back_to: <previous-artifact>
  rollback_reason: "<one-line reason from monitor-canary output>"
  side_effects_unresolved:
    - "<list any side effects that could not be undone>"
```

Post a comment on the GitHub issue:
```bash
gh issue comment <issue-number> \
  --body "## ⏪ Rolled Back

**Rolled back to:** <previous-artifact>
**Reason:** <reason from monitor-canary>
**Time in canary:** <duration>

**Unresolved side effects:** <list or 'none'>

Next: investigate the failure, fix, and re-run from Step 25."
```

If side effects were unresolved, open a follow-up incident with `/ops:incident`.

---

## Important Rules

- Do not auto-rollback on transient noise — the decision to roll back is always human-made after reviewing `/ops:monitor-canary` output
- Never rollback without reviewing the side effects first — a rollback can make things worse if data was written that the old code cannot read
- If rollback itself fails partway through, stop and escalate — do not attempt to re-deploy the new artifact to "fix" the rollback failure
- After rollback, the issue must be re-routed: fix the root cause, then re-run from Step 25
