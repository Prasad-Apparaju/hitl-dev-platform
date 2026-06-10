---
description: Start a new greenfield project from a PRD. Sets up CLAUDE.md conventions, initializes the system manifest, and prepares for /hitl:architect-design-system. Run this first on a new project before any code is written.
argument-hint: "[optional: project name or PRD path]"
disable-model-invocation: true
---

# Start a New Project (PRD)

Setting up a new greenfield project for HITL AI-Driven Development. Work through these steps in order — pause after each and wait for confirmation before proceeding.

**Quick sanity check:** If this codebase already has substantial source code, you likely want `/hitl:start-brownfield` instead. If you are migrating from one system to another, use `/hitl:start-migration`. Say so if either applies.

---

## Step 0 — Wire up HITL hooks (once per project)

Check whether `.hitl/hooks/` already exists. If it does, say "Hooks already wired — skipping." and proceed to Step 1.

If not:

1. Find the HITL platform path:
   ```bash
   python3 -c "
   import json, os, sys
   cfg = os.path.expanduser('~/.claude/settings.json')
   try:
       data = json.load(open(cfg))
       for p in data.get('plugins', []):
           path = p if isinstance(p, str) else p.get('path', '')
           if os.path.isfile(os.path.join(path, '.claude-plugin/plugin.json')):
               print(path); sys.exit(0)
   except: pass
   print('NOT_FOUND')
   "
   ```
   If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found in your Claude Code settings. Install it with: `claude plugin marketplace add pappar/hitl-claude-plugin && claude plugin install hitl@hitl`"

2. Create `.hitl/hooks/` and write a wrapper for each of these six hooks: `welcome`, `check-hitl-context`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`. Each wrapper is:
   ```bash
   #!/usr/bin/env bash
   exec bash "${HITL_PLUGIN_ROOT:-<plugin-path>}/hooks/<name>.sh" "$@"
   ```
   Replace `<plugin-path>` with the path found above and `<name>` with the hook name. Run `chmod 750` on each file.

3. Create `.claude/settings.json` only if it does not already exist:
   ```json
   {
     "hooks": {
       "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "bash .hitl/hooks/welcome.sh" }] }],
       "PreToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "bash .hitl/hooks/check-hitl-context.sh" }] }],
       "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [
         { "type": "command", "command": "bash .hitl/hooks/check-domain-boundary.sh" },
         { "type": "command", "command": "bash .hitl/hooks/rebuild-graph.sh" },
         { "type": "command", "command": "bash .hitl/hooks/sync-step-to-issue.sh" }
       ]}],
       "Stop": [{ "hooks": [{ "type": "command", "command": "bash .hitl/hooks/write-session-summary.sh" }] }]
     }
   }
   ```

4. Say: "Hooks wired. `.hitl/hooks/` and `.claude/settings.json` created. **Restart Claude Code now** so the hooks load, then re-run this command to continue setup."

---

## Step 1 — Customize CLAUDE.md

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What language and framework is this project? What test framework do you use? Any specific naming or formatting conventions?"
- Fill in the placeholders based on their answers.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 2 — Initialize the system manifest

If `docs/system-manifest.yaml` is missing or has template content:
- Ask: "What are the main domains or services in this project? For each, give a one-line description."
- Create `docs/system-manifest.yaml` with their answer. Map each domain to a plausible source path and mark as provisional.
- Say: "Manifest initialized. You'll refine domain boundaries as the system grows."

If a real manifest already exists, say: "Manifest found — skipping." and move on.

---

## Step 3 — Install Graphify

Graphify builds a queryable knowledge graph from your docs and code. HITL skills use it to look up domains, incidents, and test coverage without exhausting the context window. Install it now so it's ready when `/hitl:architect-design-system` produces docs.

```bash
uv tool install graphifyy        # install once per machine (or: pipx install graphifyy)
graphify claude install          # register /graphify skill with Claude Code
```

Ask: "Is Graphify installed? (`graphify --version`)"  
- If yes: confirm `graphify claude install` has been run and continue.
- If no: show the install command above and wait for confirmation before continuing.

Full setup reference: `shared/graphify-setup.md`

---

## Step 4 — Create your first GitHub issue

- Ask: "What's the first feature you want to build?"
- Run: `gh issue create --title "[feature name]" --body "Initial feature for [project name]. Created via HITL onboarding."`
- Show the issue URL.

---

## Step 5 — Confirm ready

Output this exactly:

---
**You're ready.**

Generate the design docs for your system before writing any code:

```
/hitl:architect-design-system
```

This produces the system manifest, HLDs, LLDs, and an initial delivery plan — demoable slices sequenced by dependency, each with a decision packet at `docs/decisions/`. The 32-step workflow reads these docs at nearly every step — they must exist before feature work starts.

After `/hitl:architect-design-system` completes:
1. Run `graphify .` to build the initial knowledge graph, then `graphify hook install` for auto-rebuild
2. Commit `graphify-out/` (excluding `manifest.json` and `cost.json`) so teammates start with the graph
3. Assign decision packets to developers — each developer picks up one packet and runs the 32-step workflow from it
4. For new features after the initial build, create a GitHub issue and run `/hitl:dev-practices`

---
