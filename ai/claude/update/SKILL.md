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

If the version is the same as before, say: "Already on the latest version — no changes." and stop.

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

Delete `.hitl/hooks/` and re-create all seven wrappers (including `statusline-hitl`) using the dynamic discovery template from Step 0 in `/hitl:dev-start-from-prd`.

Also check `.claude/settings.json` for the `$CLAUDE_PROJECT_DIR` fix and the `statusLine` entry:
```bash
grep "CLAUDE_PROJECT_DIR" .claude/settings.json
grep "statusLine" .claude/settings.json
```

If `CLAUDE_PROJECT_DIR` is absent, the hook commands use relative paths and fail when Claude Code's cwd differs from the project root. If `statusLine` is absent, the persistent HITL breadcrumb is missing. In either case, delete `.claude/settings.json` and re-create it from the template in Step 0 of `/hitl:dev-start-from-prd`.

Say:

"Hook wrappers and settings.json re-created with current patterns. Wrappers now check `~/.claude/plugins/installed_plugins.json` first (current Claude Code) with fallback to legacy `settings.json`. Hook commands now use `$CLAUDE_PROJECT_DIR` for reliable path resolution. `statusLine` added for persistent HITL breadcrumb."

---

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
