---
description: Run database schema migrations safely before deploying the new application version. Verifies a backup exists, runs a dry-run, presents all schema changes for operator approval, executes the migration, and verifies the resulting schema. Conditional — only run when the change includes database migrations.
argument-hint: "[change ID or migration file path]"
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


# Migrate Database

Execute database schema migrations for a change. This runs after IaC is applied and before the new application artifact is deployed — the application must not deploy against a schema it does not expect.

**Input:** $ARGUMENTS (change ID or specific migration file path)

**Refusal rule — no backup:** If no backup has been taken and the migration includes destructive changes (column drops, table drops, data transforms), stop: "No backup confirmed. A verified backup must exist before running a destructive migration."

**Skip condition:** If `.hitl/current-change.yaml` has no `iac_plan.migrations` entries, stop: "No database migrations in this change plan — skip this step."

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Progress Banners

Format: `---` line, `**DB Migration — Step N / 5: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Read Plan | `▶ Read Plan · ○ Backup · ○ Dry-run · ○ Apply · ○ Verify` |
| 2 | Verify Backup | `✅ Read Plan · ▶ Backup · ○ Dry-run · ○ Apply · ○ Verify` |
| 3 | Dry-run | `✅ Read Plan · ✅ Backup · ▶ Dry-run · ○ Apply · ○ Verify` |
| 4 | Apply | `✅ Read Plan · ✅ Backup · ✅ Dry-run · ▶ Apply · ○ Verify` |
| 5 | Verify Schema | `✅ Read Plan · ✅ Backup · ✅ Dry-run · ✅ Apply · ▶ Verify` |

---

## Step 1 — Read the migration plan

1. Read `.hitl/current-change.yaml` under `iac_plan.migrations`:
   - Migration files (paths), ordered by execution sequence
   - For each migration: classify as **additive** (new column, new table, new index) or **destructive** (drop column, drop table, rename column, type change, data transform)
2. Read each migration file — present a plain-English summary of every schema change
3. Check the target environment and database connection string from the IaC config or project environment files
4. Identify which application services depend on the schema being changed:
   ```
   /graphify query "services reading or writing table: <table-name>"
   ```
   Fall back to `docs/system-manifest.yaml` → domain `boundary_entities`.

Present the full migration summary before proceeding.

---

## Step 2 — Take a verified backup

Run `/hitl:ops-backup-database backup <change-ID>` before proceeding. This creates a labeled, verified snapshot and records `database_backup.backup_path` in `.hitl/current-change.yaml`.

**For additive-only migrations:** A backup taken within 24h is acceptable if one already exists and is recorded in `.hitl/current-change.yaml` under `database_backup`. If none is recorded, run the backup skill now.

**For any destructive migration:** A fresh backup is mandatory — taken within the last 60 minutes. Run `/hitl:ops-backup-database backup <change-ID>` regardless of any prior backups.

Do not proceed to Step 3 until `database_backup.verified: true` is set in `.hitl/current-change.yaml`.

---

## Step 3 — Dry-run

Run the migration tool in dry-run / preview mode:

| Tool | Detection | Dry-run command |
|------|-----------|----------------|
| Flyway | `flyway.conf` | `flyway migrate -dryRunOutput=<file>` |
| Liquibase | `liquibase.properties` | `liquibase updateSQL` |
| Alembic | `alembic.ini` | `alembic upgrade head --sql` |
| Django | `manage.py` | `python manage.py migrate --plan` |
| Raw SQL | `.sql` files | Review SQL without executing |

Display the full dry-run output. For each change, confirm:
- The sequence of operations is correct
- No unintended tables or columns are affected
- Destructive steps are clearly identified

**STOP. Ask the operator:**
> "Review the migration plan above. Any surprises or schema changes not expected for this feature?
>
> Type **MIGRATE** to confirm, or describe what needs to change."

Do not proceed without explicit `MIGRATE` confirmation.

For destructive steps, require a second confirmation: "This migration will drop or alter: `<list>`. This may be irreversible without a rollback migration. Type **CONFIRMED** to proceed."

---

## Step 4 — Apply

1. Execute the migration:

| Tool | Apply command |
|------|--------------|
| Flyway | `flyway migrate` |
| Liquibase | `liquibase update` |
| Alembic | `alembic upgrade head` |
| Django | `python manage.py migrate` |
| Raw SQL | `psql -h <host> -U <user> -d <database> -f <file>` |

2. Capture and display the full migration output
3. If the migration fails partway through:
   - Stop immediately — do not retry
   - Report the exact failure and partial state
   - Do NOT deploy the new application version until migration state is resolved
   - Assess whether a rollback migration is possible or whether the backup must be restored

---

## Step 5 — Verify schema

1. Run a schema introspection to confirm the resulting schema matches the LLD:
   ```sql
   -- PostgreSQL
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name = '<table>';

   -- Check indexes
   SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '<table>';
   ```
   Compare against the LLD's entity definitions.

2. Run any post-migration smoke queries defined in the migration files or LLD (verify row counts, check constraints, test a representative read).

3. Update `.hitl/current-change.yaml`:

```yaml
iac_plan:
  migrations:
    status: applied
    applied_at: <ISO timestamp>
    files_applied:
      - <migration-file-1>
    schema_verified: true
    backup_path: <path-or-bucket-key>
```

Report: "Migration complete. Schema verified. Ready to deploy with `/hitl:ops-deploy`."

---

## Important Rules

- Never deploy the new application version before the migration completes and is verified — the app must not run against an unexpected schema
- If the migration fails partway, do not continue to deployment — diagnose and resolve the partial state first
- Destructive migrations always require a fresh backup (within 60 minutes) and double confirmation
- Record the backup path in `.hitl/current-change.yaml` — this is the restore target if rollback is needed
