---
description: "Validate all ops artifacts for a change — migration scripts, IaC files, deployment configs, and rollback coverage — before they are needed in production. Run at two points in the workflow: after Step 6 (syntax validation + dev dry-run) and at Step 26 integration verify (full readiness gate including rollback coverage and tested-in-dev evidence). Blocks PR merge if any required artifact is missing, invalid, or untested."
argument-hint: "[change ID or PR link] [--level syntax | dev | full]"
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


# Verify Ops Scripts

Validate that all ops artifacts for this change exist, are syntactically valid, pass a dry-run, and have rollback coverage before they're needed in production.

**Input:** $ARGUMENTS
- `<change-ID> --level syntax` — Step 6 exit check: existence + syntax + dev dry-run
- `<change-ID> --level full` — Step 26 gate: syntax + dev test + rollback coverage + deployment config validity
- Default level if omitted: `full`

**Refusal rule:** If `.hitl/current-change.yaml` has no `iac_plan` key, stop: "No IaC plan found — run `/hitl:dev-apply-change` first to identify what ops artifacts are required."

---

## Required tools

This skill shells out to external CLIs. Only the tools matching the artifacts present in the change are needed — run a check, and if its CLI is missing, report which one to install rather than failing silently.

- **IaC validation / dry-run:** `terraform`, `pulumi`, `helm`, `kubectl`, `cdk` (whichever the project uses)
- **DB migrations:** `flyway`, `liquibase`, `alembic`, `python` (Django `manage.py`), `psql` (raw SQL)
- **Deployment config:** `docker` (compose), `actionlint` or `yamllint`, `bash`, `python3`
- **Secrets scan (one of):** `gitleaks`, `trufflehog`, or `semgrep`

---

## Progress Banners

Format: `---` line, `**Verify Ops Scripts — Step N / 4: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Inventory | `▶ Inventory · ○ Syntax · ○ Dev Dry-run · ○ Rollback + Record` |
| 2 | Syntax Validation | `✅ Inventory · ▶ Syntax · ○ Dev Dry-run · ○ Rollback + Record` |
| 3 | Dev Dry-run / Test | `✅ Inventory · ✅ Syntax · ▶ Dev Dry-run · ○ Rollback + Record` |
| 4 | Rollback Coverage + Record | `✅ Inventory · ✅ Syntax · ✅ Dev Dry-run · ▶ Rollback + Record` |

Steps 3 and 4 are skipped at `--level syntax`; Step 4 rollback coverage is required at `--level full`.

---

## Step 1 — Inventory expected artifacts

Read `.hitl/current-change.yaml` to determine what should exist:

```
Ops artifact inventory — <ChangeID>
─────────────────────────────────────
IaC changes:        <yes / no — list files from iac_plan>
DB migrations:      <yes / no — list files from iac_plan.migrations>
Deployment config:  <files referenced in rollout_plan>
Rollback migration: <expected for each destructive migration>
Observability:      <dashboard and alert config files, if applicable>
```

For each expected artifact, confirm the file exists on disk. Flag any that are missing:

```
❌ MISSING: infra/migrations/0042_add_user_flags.sql
✅ EXISTS:  infra/terraform/main.tf
❌ MISSING: infra/migrations/0042_rollback.sql  (rollback for destructive migration)
```

If any artifact is missing, stop at this step: "Required ops artifacts are missing. Create them before proceeding — do not advance to TDD or code review with incomplete ops scripts."

---

## Step 2 — Syntax validation

Validate each artifact can be parsed by its tool. None of these commands apply changes — they only check syntax.

**IaC:**

| Tool | Syntax check |
|---|---|
| Terraform | `terraform validate` (after `terraform init`) |
| Pulumi | `pulumi preview --suppress-outputs` (auth required) |
| Helm | `helm lint <chart-dir>` |
| Kubernetes manifests | `kubectl apply --dry-run=client -f <manifest>` |
| AWS CDK | `cdk synth` |

**Database migrations:**

| Tool | Syntax check |
|---|---|
| Flyway | `flyway validate` |
| Liquibase | `liquibase validate` |
| Alembic | `alembic check` |
| Django | `python manage.py migrate --check` |
| Raw SQL | Parse for syntax errors: `psql --file=<file> --no-psqlrc -c '\quit'` (connects but does not execute DML) |

**Deployment config:**

| Config type | Syntax check |
|---|---|
| Docker Compose | `docker compose config` |
| GitHub Actions / CI | `actionlint .github/workflows/*.yml` or `yamllint` |
| Shell scripts | `bash -n <script>` |
| JSON/YAML configs | `python3 -m json.tool` / `python3 -c "import yaml; yaml.safe_load(open('<file>'))"`  |

**Secrets scan of ops artifacts (blocking):**

Ops scripts frequently touch credentials — connection strings in migrations, deploy tokens in CI scripts, API keys in Terraform variables. Scan all ops artifacts for hardcoded secrets before they reach the repo:

```bash
# Preferred: run whichever is installed
gitleaks detect --source . --no-git --redact \
  --include-path "infra/" --include-path "deploy/" --include-path ".github/workflows/"

# Alternative
trufflehog filesystem infra/ deploy/ .github/ --only-verified --fail

# Semgrep fallback
semgrep scan --config "p/secrets" infra/ deploy/ .github/ --error
```

Flag any match as a **blocking violation** — hardcoded secrets in ops scripts are a BLOCKER equivalent to a plain env var detected by `/hitl:ops-detect-drift`. The fix is always: move the value to vault, reference it via environment variable or secrets manager injection.

Report each result:

```
Syntax validation results
─────────────────────────
  ✅ terraform validate       — valid
  ✅ helm lint                — 0 warnings
  ❌ alembic check            — ERROR: revision 0042 references missing dependency 0041
  ✅ bash -n deploy.sh        — valid
  ❌ secrets scan             — BLOCKER: deploy/scripts/init.sh line 14 contains hardcoded API_KEY
```

Block on any failure. If `--level syntax` was specified, stop here and record the result (see Step 4 for recording).

---

## Step 3 — Dev dry-run and test in dev environment

Run each script against a **development or staging environment** — not production. This is the difference between "the script parses" and "the script actually works."

**IaC dry-run:**

| Tool | Dev plan command |
|---|---|
| Terraform | `terraform plan -out=tfplan` against dev workspace |
| Pulumi | `pulumi preview` against dev stack |
| Helm | `helm upgrade --dry-run --debug <release> <chart>` against dev cluster |
| Kubernetes | `kubectl apply --dry-run=server -f <manifest>` against dev cluster |
| CDK | `cdk diff` against dev environment |

Capture the full plan output. Flag:
- Any resource that would be **destroyed** unexpectedly
- Any resource replacement (destroy + create)
- Any plan that touches resources outside the expected scope

**Database migration test — apply and revert in dev:**

1. Apply the migration to the dev database:
   ```bash
   # Note the schema version before
   alembic current   # or equivalent
   # Apply
   alembic upgrade head
   ```
2. Verify the schema matches the LLD — run the same column/index checks as `/hitl:ops-migrate-database` Step 5
3. Run a representative subset of the application's unit tests against the migrated schema (just enough to confirm the app code is compatible with the new schema — not the full suite)
4. **Revert** — apply the rollback migration or restore from a dev database snapshot:
   ```bash
   alembic downgrade -1   # or equivalent rollback migration
   ```
5. Confirm the schema is back to its pre-migration state

If the migration cannot be reverted (no rollback migration and no dev snapshot), flag it:
> "Migration `<file>` has no revert path tested in dev. Either add a rollback migration or document why schema rollback is unnecessary for this change before proceeding to Step 26."

**Deployment config test:**

For shell scripts or CI/CD configs, run any available self-test or linter:
```bash
# Shell scripts with test flags
./deploy.sh --dry-run 2>&1

# CI syntax
gh workflow run <workflow> --dry-run   # if supported
```

Report results in the same format as Step 2.

---

## Step 4 — Rollback coverage and record

**Rollback coverage check (required at `--level full`):**

For every destructive database migration (column drop, table drop, data transform, type change), verify one of the following exists:
- A corresponding rollback migration file (naming convention: `<N>_rollback.sql` or `downgrade` function in the migration tool)
- Explicit documentation that the old application code is schema-compatible (runs correctly on the new schema without the rollback being applied)
- A backup strategy entry in `.hitl/current-change.yaml` under `database_backup` confirming `/hitl:ops-backup-database` will be run before migration

Flag any destructive migration that has none of these: "No rollback path for `<migration-file>`. Add a rollback migration or document the compatibility strategy before this change can be merged."

**Record the verification result:**

Update `.hitl/current-change.yaml`:

```yaml
ops_scripts:
  verified_at: <ISO timestamp>
  level: <syntax | full>
  iac_valid: true
  migrations_valid: true
  migrations_tested_in_dev: true   # only at --level full
  rollback_covered: true           # only at --level full
  deployment_config_valid: true
  findings:
    - "<any warnings or conditional findings>"
```

**If all checks pass:**
Report: "Ops scripts verified (`<level>`). IaC: ✅ Migration: ✅ Rollback: ✅ Deployment config: ✅. Ready to proceed."

**If any check fails:**
List every failure with the specific file and the exact error. Do not set `ops_scripts.verified_at`. Do not let the workflow advance past the current gate until all failures are resolved.

---

## When to Run

| Workflow step | Level | Gate |
|---|---|---|
| After Step 6 (IaC scripts written) | `--level syntax` | Exit criterion for Step 6 — do not start TDD with broken scripts |
| Step 26 (Integration verify) | `--level full` | PR merge gate — `ops_scripts.verified_at` must exist and `rollback_covered: true` |

---

## Important Rules

- A syntax-valid script is not a tested script — both levels are required before merge
- Dev dry-run failures are often caused by stale state or missing dependencies in the dev environment — diagnose before dismissing as environment noise
- Migration revert in dev is not optional for destructive migrations — "we'll handle rollback if needed in production" is not a rollback plan
- The dev test in Step 3 must use a database that has the same schema as the last production migration — not a fresh empty schema
