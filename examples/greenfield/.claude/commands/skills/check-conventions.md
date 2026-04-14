# Check Conventions

Run convention checks against the current codebase and report violations in-chat. Uses semgrep for code rules and standalone scripts for manifest drift and Mermaid checks.

**Input:** $ARGUMENTS (optional — `--only semgrep|manifest|mermaid` to run a subset)

---

## Step 1 — Run the checks

Run all three checks (or a subset if `--only` is specified):

### Semgrep (code conventions)

```bash
semgrep scan --config .semgrep/ --error
```

If semgrep is not installed, say: "Install semgrep: `pip install semgrep` or `brew install semgrep`"

### Manifest drift

```bash
python scripts/check_manifest_drift.py
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

**Warnings (should fix, not blocking):**
- List warnings

**Passing:**
- Summary count: "N checks passed"

---

## Step 3 — Offer to fix

For each violation, ask:

"Want me to fix [violation]? I'll generate the fix and you can review."

If the user says yes, generate the fix following the project's conventions from `CLAUDE.md` and the system manifest.

For Mermaid violations, offer to run the fixer: `python scripts/fix_mermaid_br_tags.py <files>`

---

## Important Rules

- Run from the project root
- Semgrep rules are in `.semgrep/` organized by category (security, correctness, best-practices)
- To add a new convention, create a semgrep rule YAML in the appropriate `.semgrep/` subdirectory
- Convention violations are blocking in CI. Catching them here saves a failed CI run.
- If the manifest is missing or stale (drift detected), flag it: "The manifest may be out of date. Run the manifest generator to refresh it."
