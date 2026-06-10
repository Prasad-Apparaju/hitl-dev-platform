---
description: Update the HITL plugin to the latest version. Pulls the latest changes from the plugin repo, shows what changed, and re-wires hooks if needed.
argument-hint: ""
disable-model-invocation: true
---

# Update HITL Plugin

---

## Step 1 — Find the plugin

Run:
```bash
python3 -c "
import json, os, sys
cfg = os.path.expanduser('~/.claude/settings.json')
try:
    data = json.load(open(cfg))
    for p in data.get('plugins', []):
        path = p if isinstance(p, str) else p.get('path', '')
        if os.path.isfile(os.path.join(path, 'ai/claude/plugin/plugin.json')):
            print(path); sys.exit(0)
except: pass
print('NOT_FOUND')
"
```

If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found in your Claude Code settings. Confirm it was installed with `claude plugin add /path/to/hitl-dev-platform`."

---

## Step 2 — Pull the latest version

Record the current version before pulling:
```bash
python3 -c "import json; d=json.load(open('<plugin-path>/ai/claude/plugin/plugin.json')); print(d['version'])"
```

Pull:
```bash
git -C <plugin-path> pull
```

Show the git output. If already up to date, say "Already up to date — no changes." and stop.

If changes were pulled, record the new version:
```bash
python3 -c "import json; d=json.load(open('<plugin-path>/ai/claude/plugin/plugin.json')); print(d['version'])"
```

Show: "Updated: **v\<old\>** → **v\<new\>**"

---

## Step 3 — Show what changed

```bash
git -C <plugin-path> log --oneline ORIG_HEAD..HEAD
```

Print each commit as a bullet point.

---

## Step 4 — Re-wire hooks if needed

Check whether `.hitl/hooks/` exists in the current project.

If it does not exist, follow the same hook-wiring steps as Step 0 in `/hitl:start-prd`: create the wrapper scripts and `.claude/settings.json`.

If it already exists, check whether the wrappers point to the correct plugin path:
```bash
grep "HITL_PLATFORM_ROOT" .hitl/hooks/welcome.sh
```

If the fallback path in the wrappers does not match `<plugin-path>`, say: "Hook wrappers exist but point to a different path. Re-run `/hitl:start-prd` (or the appropriate start skill) to recreate them."

---

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
