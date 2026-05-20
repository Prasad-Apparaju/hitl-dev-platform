---
name: hitl:dev:check-conventions
description: Run convention checks (semgrep, secrets scan, manifest drift, Mermaid lint) against the current codebase and report violations. Use before creating a PR or when asked to verify code quality. Safe to run at any time — read-only except when the user asks to fix violations.
argument-hint: "[--only semgrep|secrets|manifest|mermaid]"
disable-model-invocation: true
---

# Check Conventions

Run convention checks against the current codebase and report violations in-chat. Uses semgrep for code rules and standalone scripts for secrets detection, manifest drift, and Mermaid checks.

**Input:** $ARGUMENTS (optional — `--only semgrep|secrets|manifest|mermaid` to run a subset)

---

## Step 1 — Run the checks

Run all four checks (or a subset if `--only` is specified):

### Semgrep (code conventions)

```bash
semgrep scan --config .semgrep/ --error
```

If semgrep is not installed, say: "Install semgrep: `pip install semgrep` or `brew install semgrep`"

### Secrets scan (blocking)

Detect hardcoded secrets, API keys, passwords, and connection strings committed to the repository.

Preferred tool — run whichever is installed:

```bash
# gitleaks (fastest, git-aware)
gitleaks detect --source . --no-git --redact

# trufflehog (deep entropy scan)
trufflehog filesystem . --only-verified --fail

# detect-secrets (baseline-aware)
detect-secrets scan --all-files | detect-secrets audit

# semgrep secret rules (if neither above is installed)
semgrep scan --config "p/secrets" --error
```

If none of these tools is installed:
```bash
# Fallback: grep for common patterns
grep -rn --include="*.py" --include="*.js" --include="*.ts" --include="*.yaml" --include="*.env" \
  -E '(password|secret|api_key|apikey|access_key|private_key)\s*[:=]\s*["\x27][^"\x27]{8,}' \
  --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="__pycache__" .
```

Flag any match as a **blocking violation** — a secret committed to the repo cannot be un-committed without a full history rewrite and credential rotation.

**What counts as a secret violation:**
- Hardcoded passwords, tokens, or API keys (non-placeholder values)
- Connection strings containing credentials (`postgresql://user:pass@host/db`)
- Private keys or certificates embedded in source files
- `.env` files committed with real values (not `.env.example` / placeholder files)

**What does NOT count:**
- Placeholder values (`"your-api-key-here"`, `"CHANGEME"`, `"<INSERT_SECRET>"`)
- Test fixtures using obviously fake credentials (`"test-password-123"`)
- References to vault paths (`"vault/secret/db_password"`, `"${DB_PASSWORD}"`)

### Manifest drift

```bash
python ci/manifest-drift/check_manifest_drift.py --source-dirs app/ src/
```

### Mermaid br tags

```bash
find docs/ -name "*.md" -exec python scripts/fix_mermaid_br_tags.py --check {} +
```

---

## Step 2 — Report results

Present the results grouped by status:

**Violations (must fix before merging):**
- List each violation with file path, rule ID, and what's wrong
- For each, suggest the fix
- Secrets violations: always list the file and line; never print the actual secret value

**Warnings (should fix, not blocking):**
- List warnings

**Passing:**
- Summary count: "N checks passed"

---

## Step 3 — Offer to fix

For each violation, ask:

"Want me to fix [violation]? I'll generate the fix and you can review."

If the user says yes, generate the fix following the project's conventions from `CLAUDE.md` and the system manifest.

For secrets violations: the fix is always to remove the hardcoded value, replace it with an environment variable reference or vault path, and rotate the leaked credential.

For Mermaid violations, offer to run the fixer: `python scripts/fix_mermaid_br_tags.py <files>`

---

## Important Rules

- Run from the project root
- Semgrep rules are in `.semgrep/` organized by category (security, correctness, best-practices)
- To add a new convention, create a semgrep rule YAML in the appropriate `.semgrep/` subdirectory
- If the manifest is missing or stale (drift detected), flag it: "The manifest may be out of date. Run the manifest generator to refresh it."
- Secrets violations are always blocking — there is no "warn and proceed" path for a committed secret
