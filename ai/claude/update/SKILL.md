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

If it already exists, check whether the wrappers use dynamic path discovery (the correct pattern):
```bash
grep "claude/settings.json" .hitl/hooks/welcome.sh
```

If the wrappers do NOT contain `claude/settings.json`, they are stale — either using `HITL_PLATFORM_ROOT` (the old env-var pattern from `init-project.sh`) or a hardcoded absolute path (an older Step 0 pattern). Both break when the platform isn't cloned at the expected path or the plugin version changes.

Delete `.hitl/hooks/` and re-create all six wrappers using the dynamic discovery template from Step 0 in `/hitl:dev-start-from-prd`. Say:

"Hook wrappers were stale (`HITL_PLATFORM_ROOT` or hardcoded path pattern detected) — recreated with dynamic discovery. Hooks now read `~/.claude/settings.json` at runtime to locate the plugin, so they survive version updates and work on any machine without env vars."

---

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
