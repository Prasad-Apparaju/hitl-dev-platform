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
cfg = os.path.expanduser('~/.claude/settings.json')
try:
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

If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found in your Claude Code settings. Confirm it was installed with `claude plugin install hitl@hitl`."

Record the version shown as the **old version**.

---

## Step 2 — Update the plugin

Run:
```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

These are the same commands used to install — re-running them updates the plugin to the latest release.

---

## Step 3 — Read the new version

Run:
```bash
python3 -c "
import json, os, sys
cfg = os.path.expanduser('~/.claude/settings.json')
try:
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

Then show the relevant section of `CHANGELOG.md` from the plugin directory for the new version.

---

## Step 4 — Re-wire hooks if needed

Check whether `.hitl/hooks/` exists in the current project.

If it does not exist, follow the same hook-wiring steps as Step 0 in `/hitl:dev-start-from-prd`: create the wrapper scripts and `.claude/settings.json`.

If it already exists, check whether the wrappers use dynamic path discovery (the correct pattern):
```bash
grep "claude/settings.json" .hitl/hooks/welcome.sh
```

If the wrappers do NOT contain `claude/settings.json` (i.e. they use an old hardcoded path or env var), delete `.hitl/hooks/` and re-create all six wrappers using the dynamic discovery template from Step 0 in `/hitl:dev-start-from-prd`. Say: "Hook wrappers were using a stale path pattern — recreated with dynamic discovery."

---

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
