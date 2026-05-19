---
name: ops-backup-database
description: Create a verified database backup before risky operations, or restore from a named backup. Detects the database engine, creates a labeled snapshot, verifies its integrity, and records the backup path in the HITL context. Restore mode executes a full restore with schema verification. Run before /ops:migrate-database, or standalone before any high-risk operation. Restore mode is used by /ops:rollback when a migration must be reversed.
argument-hint: "[backup | restore] [change ID] [optional: backup-path for restore]"
disable-model-invocation: true
---

# Database Backup and Restore

Create a verified backup before a risky operation, or restore from a named backup.

**Input:** $ARGUMENTS
- `backup <change-ID>` — create a labeled backup for this change
- `restore <change-ID>` — restore from the backup recorded for this change
- `restore <backup-path>` — restore from a specific backup path (override)

---

## Progress Banners

Format: `---` line, `**DB Backup — Step N / 3: [Name]**` or `**DB Restore — Step N / 4: [Name]**`, trail, `---`.

**Backup mode:**

| Step | Name | Banner trail |
|---|---|---|
| 1 | Detect + Connect | `▶ Detect · ○ Backup · ○ Verify` |
| 2 | Create Backup | `✅ Detect · ▶ Backup · ○ Verify` |
| 3 | Verify + Record | `✅ Detect · ✅ Backup · ▶ Verify` |

**Restore mode:**

| Step | Name | Banner trail |
|---|---|---|
| 1 | Locate Backup | `▶ Locate · ○ Assess Impact · ○ Execute · ○ Verify` |
| 2 | Assess Impact | `✅ Locate · ▶ Assess · ○ Execute · ○ Verify` |
| 3 | Execute Restore | `✅ Locate · ✅ Assess · ▶ Execute · ○ Verify` |
| 4 | Verify Schema | `✅ Locate · ✅ Assess · ✅ Execute · ▶ Verify` |

---

## Backup Mode

### Step B1 — Detect database engine and connection

1. Identify the database engine from the project config:
   - `DATABASE_URL` environment variable or `.env` files
   - IaC files (`*.tf`, `helm/values.yaml`, `docker-compose.yml`)
   - `docs/system-manifest.yaml` under the domain's `dependencies`

2. Confirm connectivity — run a lightweight check:

   | Engine | Check command |
   |---|---|
   | PostgreSQL | `psql $DATABASE_URL -c "SELECT version();"` |
   | MySQL / MariaDB | `mysql -e "SELECT VERSION();"` |
   | SQLite | `sqlite3 <db-file> "PRAGMA integrity_check;"` |
   | MongoDB | `mongosh --eval "db.adminCommand({ping: 1})"` |

   If the connection fails, stop: "Cannot reach the database. Verify connection config before running a backup."

3. Determine backup storage location in this order:
   - `BACKUP_STORAGE` env var (S3 bucket URL, GCS path, or local dir)
   - `docs/system-manifest.yaml` under `cross_cutting.backup_storage`
   - Default: `.hitl/backups/` (local, for development only — flag if not in production)

### Step B2 — Create the backup

Label format: `<change-ID>-<ISO-timestamp>` (e.g., `GH-42-2026-05-18T14-30-00Z`).

| Engine | Backup command |
|---|---|
| PostgreSQL | `pg_dump -h <host> -U <user> -Fc -f <label>.dump <database>` |
| PostgreSQL (all DBs) | `pg_dumpall -h <host> -U <user> > <label>.sql` |
| MySQL | `mysqldump --single-transaction -h <host> -u <user> -p <database> > <label>.sql` |
| SQLite | `sqlite3 <db-file> ".backup <label>.db"` |
| MongoDB | `mongodump --uri <uri> --archive=<label>.archive --gzip` |

For **cloud-managed databases**, prefer native snapshots over dump tools:
- AWS RDS: `aws rds create-db-snapshot --db-instance-identifier <id> --db-snapshot-identifier <label>`
- Cloud SQL: `gcloud sql backups create --instance=<instance> --description=<label>`
- Azure SQL: `az sql db copy ...` or use point-in-time restore

Capture the backup command output in full. Note the duration.

### Step B3 — Verify and record

1. **Verify the backup is non-empty and intact:**

   | Engine | Verification |
   |---|---|
   | PostgreSQL dump | `pg_restore --list <label>.dump | wc -l` (must be > 0) |
   | SQL dump file | Check file size (`ls -lh <label>.sql`) — must be non-trivial; optionally restore to a temp schema |
   | MongoDB archive | `mongorestore --archive=<label>.archive --gzip --dryRun` |
   | RDS snapshot | `aws rds describe-db-snapshots --db-snapshot-identifier <label>` → status must be `available` |

2. Compute or record a checksum: `sha256sum <backup-file>` (for file-based backups).

3. Update `.hitl/current-change.yaml`:

```yaml
database_backup:
  engine: <postgresql | mysql | sqlite | mongodb | rds | cloud-sql>
  backup_label: <label>
  backup_path: <full path or cloud resource ARN/URL>
  backup_checksum: <sha256 or "cloud-managed">
  backup_size: <human-readable size>
  taken_at: <ISO timestamp>
  verified: true
```

Report: "Backup complete. Label: `<label>`. Size: `<size>`. Verified. Ready for migration or deployment."

---

## Restore Mode

### Step R1 — Locate the backup

1. If `restore <change-ID>` was given: read `database_backup.backup_path` from `.hitl/current-change.yaml`
2. If `restore <backup-path>` was given: use the provided path directly
3. Confirm the backup file or cloud snapshot exists and is accessible
4. Verify checksum if available: `sha256sum -c` against `database_backup.backup_checksum`

If the backup cannot be found or checksum fails, stop: "Backup not found or integrity check failed. Do not proceed with restore — locate a verified backup first."

### Step R2 — Assess restore impact

Before restoring, the operator must understand what will happen:

```
Restore impact assessment
──────────────────────────
  Backup taken at:     <timestamp>
  Current time:        <now>
  Data written since:  ~<duration> — any writes in this window will be lost

  Known side effects from this window:
    <read from iac_plan.migrations side-effects or rollback notes in .hitl/current-change.yaml>

  Services that must be stopped before restore:
    <identify from system-manifest.yaml — any service writing to this database>
```

**STOP. Confirm with the operator:**
> "Restoring this backup will lose all data written since `<timestamp>`. This cannot be undone.
>
> Services that write to this database must be stopped or put in maintenance mode first.
>
> Type **RESTORE** to confirm, or **CANCEL** to abort."

Do not proceed without explicit `RESTORE` confirmation.

### Step R3 — Execute restore

1. Stop or isolate dependent services (put them in maintenance mode, reduce replica count to 0, or use a feature flag) — confirm this is done before starting the restore.

2. Run the restore:

   | Engine | Restore command |
   |---|---|
   | PostgreSQL (custom format) | `pg_restore -h <host> -U <user> -d <database> -c <label>.dump` |
   | PostgreSQL (SQL dump) | `psql -h <host> -U <user> -d <database> < <label>.sql` |
   | MySQL | `mysql -h <host> -u <user> -p <database> < <label>.sql` |
   | SQLite | `sqlite3 <db-file> ".restore <label>.db"` |
   | MongoDB | `mongorestore --uri <uri> --archive=<label>.archive --gzip --drop` |
   | RDS snapshot | `aws rds restore-db-instance-from-db-snapshot --db-instance-identifier <id> --db-snapshot-identifier <label>` |
   | Cloud SQL | `gcloud sql instances restore-backup <instance> --backup-id=<id>` |

3. If restore fails mid-way, stop immediately and escalate — do not retry or attempt to patch the partial state.

### Step R4 — Verify and record

1. Run the same connectivity check from Step B1 — confirm the database is responding.

2. Verify the schema matches the pre-migration LLD (or the known stable schema):
   ```sql
   -- PostgreSQL: check key tables exist and have expected columns
   SELECT column_name, data_type FROM information_schema.columns
   WHERE table_name = '<key-table>';
   ```

3. Run a representative read query to confirm data is present and intact.

4. Restart the dependent services stopped in Step R3. Verify they come up healthy.

5. Update `.hitl/current-change.yaml`:

```yaml
database_backup:
  restored_at: <ISO timestamp>
  restored_from: <backup_path>
  restore_verified: true
```

Report: "Restore complete. Schema verified. Services restarted. Database is in the state from `<backup_taken_at>`."

---

## Important Rules

- Never restore without reading the impact assessment — the operator must know what data will be lost
- For production restores: always stop dependent services before starting the restore
- If restore fails partway, do not restart services against a partially-restored database — escalate immediately
- Cloud-managed snapshots (RDS, Cloud SQL) are preferred over file dumps for production — they are atomic and faster to restore
- After a restore in production, run `/ops:post-deploy-monitor` for at least 1 hour to confirm stability
