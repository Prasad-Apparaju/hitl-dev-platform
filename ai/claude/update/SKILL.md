---
description: Update the HITL plugin to the latest version. Re-runs the plugin install command to pull the latest release, shows what changed, and re-wires hooks if needed.
argument-hint: ""
disable-model-invocation: true
---

# Update HITL Plugin

---

## Step 1 — Read the current version

Run:
```bash
python3 -c "
import json, os, sys
# Try installed_plugins.json first (current Claude Code)
try:
    p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
    data = json.load(open(p))
    entry = data['plugins']['hitl@hitl'][0]
    print(entry['version']); sys.exit(0)
except: pass
# Fallback: scan settings.json for plugin path, then read plugin.json
try:
    cfg = os.path.expanduser('~/.claude/settings.json')
    data = json.load(open(cfg))
    for p in data.get('plugins', []):
        path = p if isinstance(p, str) else p.get('path', '')
        pj = os.path.join(path, '.claude-plugin/plugin.json')
        if os.path.isfile(pj):
            print(json.load(open(pj))['version']); sys.exit(0)
except: pass
print('NOT_FOUND')
"
```

If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found. Confirm it was installed with `claude plugin install hitl@hitl`."

Record the version shown as the **old version**.

---

## Step 2 — Update the plugin

Run:
```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

`marketplace update` refreshes the cached manifest so the latest release is visible. `plugin update` installs it.

---

## Step 3 — Read the new version

Run:
```bash
python3 -c "
import json, os, sys
try:
    p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
    data = json.load(open(p))
    entry = data['plugins']['hitl@hitl'][0]
    print(entry['version']); sys.exit(0)
except: pass
try:
    cfg = os.path.expanduser('~/.claude/settings.json')
    data = json.load(open(cfg))
    for p in data.get('plugins', []):
        path = p if isinstance(p, str) else p.get('path', '')
        pj = os.path.join(path, '.claude-plugin/plugin.json')
        if os.path.isfile(pj):
            print(json.load(open(pj))['version']); sys.exit(0)
except: pass
print('NOT_FOUND')
"
```

If the version **changed**, continue to Step 4.

If the version is **the same as before**, the plugin catalog cache is stale — run a cache-bust update:

```bash
# Delete the catalog cache so Claude Code fetches a fresh copy
rm -f ~/.claude/plugins/plugin-catalog-cache.json

# Re-fetch the marketplace and update
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Then re-read the version (repeat the python3 block above). If it still hasn't changed, the installed commit SHA already matches what the marketplace advertises — the user is genuinely on the latest. Say: "Already on the latest version — no changes." and stop.

If it changed after the cache bust, continue to Step 4.

Show: "Updated: **v\<old\>** → **v\<new\>**"

Then show the relevant `## [<new-version>]` section from `CHANGELOG.md` in the plugin directory. If `CHANGELOG.md` is not present, say: "Full release notes: https://github.com/Prasad-Apparaju/hitl-dev-platform/blob/main/CHANGELOG.md"

---

## Step 4 — Re-wire hooks if needed

Check whether `.hitl/hooks/` exists in the current project.

If it does not exist, follow the same hook-wiring steps as Step 0 in `/hitl:dev-start-from-prd`: create the wrapper scripts and `.claude/settings.json`.

If it already exists, check whether the wrappers use current path discovery (checks `installed_plugins.json` first):
```bash
grep "installed_plugins.json" .hitl/hooks/welcome.sh
```

If the wrappers do NOT contain `installed_plugins.json`, they are stale — using `HITL_PLATFORM_ROOT` (very old), a hardcoded path, or the old `settings.json["plugins"]` discovery from v1.0.5–1.0.8. All break on current Claude Code which stores plugin records in `~/.claude/plugins/installed_plugins.json`.

Delete `.hitl/hooks/` and re-create all **eight** wrappers (`welcome`, `hitl-gate`, `check-hitl-context`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`, `statusline-hitl`) using the dynamic discovery template from Step 0 in `/hitl:dev-start-from-prd`.

Also check `.claude/settings.json` for the `$CLAUDE_PROJECT_DIR` fix, the `statusLine` entry, and the `SessionStart` → `hitl-gate.sh` hook:
```bash
grep "CLAUDE_PROJECT_DIR" .claude/settings.json
grep "statusLine" .claude/settings.json
grep "hitl-gate" .claude/settings.json
```

If `CLAUDE_PROJECT_DIR` is absent, the hook commands use relative paths and fail when Claude Code's cwd differs from the project root. If `statusLine` is absent, the persistent HITL breadcrumb is missing. If `hitl-gate` is absent, the session-start change-intake gate won't fire. In any of these cases, delete `.claude/settings.json` and re-create it from the template in Step 0 of `/hitl:dev-start-from-prd`.

Say:

"Hook wrappers and settings.json re-created with current patterns. Wrappers now check `~/.claude/plugins/installed_plugins.json` first (current Claude Code) with fallback to legacy `settings.json`. Hook commands now use `$CLAUDE_PROJECT_DIR` for reliable path resolution. `statusLine` and the `SessionStart` change-intake gate are wired."

---

## Step 4.5 — Migrate the change file to the current workflow schema

If `.hitl/current-change.yaml` exists, migrate its content to the current workflow definition.
This is what keeps the breadcrumb correct after the workflow's steps change between versions
(e.g. the brownfield workflow growing from 8 → 11 steps). It is HITL: it shows a diff and
**requires confirmation** before writing.

Requires `python3` with PyYAML. The generator remaps by each step's stable `key`, so completion
status survives renumbering. It is **surgical**: it only replaces the `workflow:` block (writing
steps as single-line flow maps — the format the breadcrumb parser reads) and upserts the version
stamps. Every other line, **including all inline comments**, is left byte-for-byte intact — the
file is never round-tripped through a YAML dumper. It writes a proposed
`.hitl/current-change.yaml.migrated` and prints a diff — it does **not** overwrite anything yet.

```bash
CATALOG="${CLAUDE_PLUGIN_ROOT:-.}/shared/workflows.yaml"
[[ -f "$CATALOG" ]] || CATALOG="ai/shared/workflows.yaml"
# Resolve a working Python (Windows-safe: python3 is the MS Store stub there). See issue #14.
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
NEW_VER=$("$PY" -c "import json; print(json.load(open('${CLAUDE_PLUGIN_ROOT:-.}/.claude-plugin/plugin.json'))['version'])" 2>/dev/null || echo "0.0.0")

"$PY" - "$CATALOG" "$NEW_VER" << 'PY'
import sys, re, yaml
catalog_path, new_ver = sys.argv[1], sys.argv[2]
F = ".hitl/current-change.yaml"
text = open(F).read()                       # raw text — preserved verbatim except the bits we splice
doc = yaml.safe_load(text) or {}            # parse is READ-ONLY; we never dump the doc back
catalog = yaml.safe_load(open(catalog_path))["workflows"]

# Determine the workflow id.
wf = doc.get("workflow", {}) or {}
wf_id = wf.get("id")
if not wf_id:
    phase = (doc.get("current_step") or {}).get("phase", "")
    wf_id = {"PRD Setup":"prd","Brownfield Setup":"brownfield","Migration Setup":"migration",
             "Migration Review":"migration_review"}.get(phase, "development")

cat = catalog[wf_id]
old_steps = {str(s.get("key")): s for s in wf.get("steps", [])}
old_cur_n = (doc.get("current_step") or {}).get("number")
old_cur_key = next((str(s["key"]) for s in wf.get("steps", []) if s.get("status")=="current"), None)

new_steps, diff = [], []
for s in cat["steps"]:
    key = s["key"]
    if key in old_steps:
        status = old_steps[key].get("status", "open"); tag = "  keep"
    else:
        status = "open"
        if isinstance(old_cur_n, int) and str(s["n"]).rstrip("a").isdigit() and int(str(s["n"]).rstrip("a")) < old_cur_n:
            status = "done"
        tag = "+ added"
    new_steps.append({"n": s["n"], "key": key, "label": s["label"], "status": status})
    diff.append(f"  {tag:7} {str(s['n']):>3} {key:<18} {status}")

# Ensure exactly one 'current': prefer the old current key; else the first non-done step.
if not any(s["status"]=="current" for s in new_steps):
    target = next((s for s in new_steps if s["key"]==old_cur_key), None) \
          or next((s for s in new_steps if s["status"]!="done"), new_steps[0])
    target["status"] = "current"
for k in (k for k in old_steps if k not in {s["key"] for s in new_steps}):
    diff.append(f"  - removed {'':>3} {k}")

# Build the new workflow block as TEXT — single-line flow maps (the only format _steps.sh parses).
wb = ["workflow:", f"  id: {wf_id}", f'  version: "{new_ver}"', f"  total: {cat['total']}", "  steps:"]
for s in new_steps:
    wb.append(f'    - {{ n: {s["n"]}, key: {s["key"]}, label: "{s["label"]}", status: {s["status"]} }}')
wb = "\n".join(wb) + "\n"

# Splice: replace the existing top-level `workflow:` block, or insert it if absent (pre-v2 file).
pat = re.compile(r"(?ms)^workflow:.*?(?=^\S|\Z)")
if pat.search(text):
    out = pat.sub(lambda m: wb, text, count=1)
elif re.search(r"(?m)^current_step:", text):
    out = re.sub(r"(?m)^current_step:", wb + "current_step:", text, count=1)
elif re.search(r"(?m)^source_artifacts:", text):
    out = re.sub(r"(?m)^source_artifacts:", wb + "source_artifacts:", text, count=1)
else:
    out = text.rstrip("\n") + "\n" + wb

# Upsert the scalar version stamps (replace the line in place, or prepend if missing).
def upsert(text, key, val):
    line = f'{key}: "{val}"'
    return re.sub(rf"(?m)^{key}:.*$", lambda m: line, text, count=1) if re.search(rf"(?m)^{key}:", text) else line + "\n" + text
out = upsert(out, "schema_version", "2.0")
out = upsert(out, "hitl_version", new_ver)

open(F + ".migrated", "w").write(out)
print(f"Workflow: {wf_id}  →  {cat['total']} steps (was {wf.get('total','?')})")
print("Step migration (remapped by key):"); print("\n".join(diff))
print(f"\nProposed file written to {F}.migrated (comments + other fields preserved) — review above.")
PY
```

Show the diff to the user. If they confirm, apply it:
```bash
mv .hitl/current-change.yaml.migrated .hitl/current-change.yaml
git add .hitl/current-change.yaml && git commit -m "chore(hitl): migrate change file to workflow schema v$NEW_VER"
```
If they decline, delete `.hitl/current-change.yaml.migrated` and leave the original untouched.
If the file already has `schema_version: "2.0"` and `workflow.version` equals the current plugin
version, skip this step and say "Change file already on the current workflow schema."

---

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
