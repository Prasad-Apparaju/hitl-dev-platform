---
description: Iteratively validate and fix everything produced in the current session. Runs checks, fixes failures, re-validates — repeats until all checks pass. Run before declaring any task complete.
argument-hint: ""
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

# Validate Work

Run checks on everything produced or modified in this session. Follow the loop: **check → fix → re-check → repeat until all pass.**

---

## Step 1 — Inventory

List every file created or modified in this session. Group by type:

- **Source code** (`.py`, `.ts`, `.go`, `.java`, `.rb`, etc.)
- **Tests** (files in `tests/`, `spec/`, `__tests__/`, etc.)
- **Documentation** (`.md` files, not in `ai/` paths)
- **YAML / JSON** (config, manifests, registries)
- **Scripts / hooks** (`.sh`, `.py` scripts, hook files)
- **Skill or agent instruction files** (`.md` in `ai/` paths or `.claude/`)

If nothing was produced, output "Nothing to validate — session produced no artifacts." and stop.

---

## Step 2 — Run checks

Run every applicable check below for each group. Record each result as **PASS** or **FAIL** with a one-line note.

### Source code
- Run the test suite. Every test that was passing before this session still passes (no regressions).
- New/modified code is covered by tests.
- Linter/formatter reports zero errors.
- Run the happy path manually with a representative input and confirm the expected output.

### Tests
- All new/modified test files execute without error.
- Each test name describes behavior (not implementation detail).
- No `test.skip` or `xit` left without a comment explaining why.
- Coverage gate met (≥90% if the project enforces it).

### Documentation (`.md`)
- Every file path mentioned in the doc exists on disk — run `ls <path>` for each.
- Every bash command shown in a code block executes without error.
- No `{{placeholder}}` left unfilled: `grep -n '{{' <file>`
- No `<br/>` inside Mermaid code blocks: `grep -n '<br' <file>`
- If the doc appears in an index, table of contents, or `SUMMARY.md`, that index is updated.
- Cross-references resolve: if the doc says "see §N.M" or links to another file, confirm the heading/file exists.

### YAML / JSON
- Parses without error:
  - YAML: `python3 -c "import yaml; yaml.safe_load(open('<file>'))"`
  - JSON: `python3 -c "import json; json.load(open('<file>'))"`
- No `{{placeholder}}` left unfilled: `grep -n '{{' <file>`
- Schema-required fields present (check against schema comments or adjacent valid files).

### Scripts / hooks (`.sh`, executable `.py`)
- Executes with a representative input without error.
- Has correct permissions — execute bit set: `ls -la <file>` shows `x`.
- Shebang line present on line 1.
- For hook scripts: `.hitl/` guard is present (`[[ -d ".hitl" ]] || exit 0`).

### Skill / agent instruction files (`.md` in `ai/` or `.claude/`)
- YAML frontmatter parses: `python3 -c "import yaml; yaml.safe_load(open('<f>').read().split('---')[1])"`
- Every `/hitl:*` command name referenced exists in `ai/claude/plugin/plugin.json` skills list.
- Every file path referenced (e.g. `docs/system-manifest.yaml`, `workflow-steps.md`) exists on disk.
- No `{{placeholder}}` left unfilled.
- If the skill is new: it is listed in `ai/claude/plugin/plugin.json`.

---

## Step 3 — Fix all failures

For each **FAIL**:
1. Identify the root cause.
2. Fix it — edit the file, re-run the command, update the reference.
3. Mark it pending re-check.

Do not skip failures. Do not mark something PASS without running the check.

---

## Step 4 — Re-check

Re-run Step 2 for every item that was FAIL or was fixed. Include anything that might be affected by the fixes (e.g., if you edited a doc to fix a broken path, re-check the whole doc group).

---

## Step 5 — Repeat

Go back to Step 3 if any failures remain. Keep iterating until all checks pass.

---

## Step 6 — Report

Output:

```
Validation complete — all checks passed.

Checked: <N> items across <groups>
Fixed during validation: <N> items (or "none")
Unresolvable: <list with reason, or "none">
```

If a failure genuinely cannot be fixed locally (requires a live external service, a missing dependency, or a human decision), list it explicitly under "Unresolvable" with the reason. Do not silently skip it.

---

## Never

- Do not report done if any fixable check is FAIL.
- Do not skip the re-check after fixing.
- Do not declare "it should work" — run the check and show the output.
- Do not summarize what you think the output will be — run it and quote the actual result.
