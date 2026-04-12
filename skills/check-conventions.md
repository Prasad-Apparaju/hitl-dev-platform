# Check Conventions

Run the convention checker against the current codebase and report violations in-chat. Wraps `tools/check-conventions/runner.py` for interactive use during development.

**Input:** $ARGUMENTS (optional — `--only <check_name>` to run a single check)

---

## Step 1 — Run the checker

```bash
python tools/check-conventions/runner.py --config convention-checks.yaml --verbose $ARGUMENTS
```

If the config file doesn't exist at `convention-checks.yaml`, check `scripts/check_conventions.py` as a fallback. If neither exists, say: "No convention checker config found. Create `convention-checks.yaml` — see the template at `templates/` in the hitl-dev-platform repo."

---

## Step 2 — Report results

Present the results grouped by status:

**Violations (must fix before merging):**
- List each violation with file path, convention name, and what's wrong
- For each, suggest the fix

**Warnings (should fix, not blocking):**
- List warnings (e.g., low comment density)

**Passing:**
- Summary count: "N checks passed"

---

## Step 3 — Offer to fix

For each violation, ask:

"Want me to fix [violation name]? I'll generate the fix and you can review."

If the user says yes, generate the fix following the project's conventions from `CLAUDE.md` and the system manifest.

---

## Important Rules

- Run from the project root, not from the tools directory
- The checker uses AST analysis — it reads code structure, not just text patterns
- Convention violations are blocking in CI. Catching them here saves a failed CI run.
- If the manifest is missing or stale (drift detected), flag it: "The manifest may be out of date. Run the manifest generator to refresh it."
