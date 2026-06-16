---
description: Start a new greenfield project from a PRD. Sets up CLAUDE.md conventions, initializes the system manifest, and prepares for /hitl:architect-design-system. Run this first on a new project before any code is written.
argument-hint: "[optional: project name or PRD path]"
disable-model-invocation: true
---

# Start a New Project (PRD)

Setting up a new greenfield project for HITL AI-Driven Development. Work through these steps in order — pause after each and wait for confirmation before proceeding.

**Quick sanity check:** If this codebase already has substantial source code, you likely want `/hitl:dev-start-brownfield` instead. If you are migrating from one system to another, use `/hitl:dev-start-migration`. Say so if either applies.

---

## Step 0 — Wire up HITL hooks (once per project)

Check whether `.hitl/hooks/` already exists. If it does, say "Hooks already wired — skipping." and proceed to Step 1.

If not:

1. Find the HITL plugin path:
   ```bash
   python3 -c "
   import json, os, sys
   try:
       d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
       for inst in d.get('plugins', {}).get('hitl@hitl', []):
           p = inst.get('installPath', '')
           if os.path.isfile(os.path.join(p, '.claude-plugin/plugin.json')):
               print(p); sys.exit(0)
   except: pass
   try:
       d = json.load(open(os.path.expanduser('~/.claude/settings.json')))
       for p in d.get('plugins', []):
           path = p if isinstance(p, str) else p.get('path', '')
           if os.path.isfile(os.path.join(path, '.claude-plugin/plugin.json')):
               print(path); sys.exit(0)
   except: pass
   print('NOT_FOUND')
   "
   ```
   If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found in your Claude Code settings. Install it with: `claude plugin marketplace add pappar/hitl-claude-plugin && claude plugin install hitl@hitl`"

2. Create `.hitl/hooks/` and write a wrapper for each of these seven hooks: `welcome`, `check-hitl-context`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`, `statusline-hitl`. Each wrapper discovers the plugin path at runtime — survives plugin updates, reinstalls, and version bumps:
   ```bash
   #!/usr/bin/env bash
   PLUGIN_ROOT=$(python3 -c "
   import json,os,sys
   try:
     d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
     for inst in d.get('plugins',{}).get('hitl@hitl',[]):
       p=inst.get('installPath','')
       if os.path.isfile(os.path.join(p,'.claude-plugin/plugin.json')):
         print(p);sys.exit(0)
   except:pass
   try:
     d=json.load(open(os.path.expanduser('~/.claude/settings.json')))
     for p in d.get('plugins',[]):
       path=p if isinstance(p,str) else p.get('path','')
       if os.path.isfile(os.path.join(path,'.claude-plugin/plugin.json')):
         print(path);sys.exit(0)
   except:pass
   " 2>/dev/null)
   [[ -z "$PLUGIN_ROOT" ]] && exit 0
   exec bash "$PLUGIN_ROOT/hooks/<name>.sh" "$@"
   ```
   Replace `<name>` with the hook name for each file. Run `chmod 750` on each file.

3. Create `.claude/settings.json` only if it does not already exist:
   ```json
   {
     "statusLine": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh\"",
     "hooks": {
       "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/welcome.sh\"" }] }],
       "PreToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/check-hitl-context.sh\"" }] }],
       "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/check-domain-boundary.sh\"" },
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/rebuild-graph.sh\"" },
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/sync-step-to-issue.sh\"" }
       ]}],
       "Stop": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/write-session-summary.sh\"" }] }]
     }
   }
   ```

4. Update `.gitignore` so session logs don't end up in the product repo — add the entry if not already present:
   ```bash
   grep -q "docs/session-logs" .gitignore 2>/dev/null || printf '\n# HITL session logs — operational artifacts, not product code\ndocs/session-logs/\n' >> .gitignore
   ```

5. Copy default ADR stubs into `docs/02-design/technical/adrs/` — skip any file that already exists (never overwrite existing ADRs):
   ```bash
   mkdir -p docs/02-design/technical/adrs
   for f in "$PLUGIN_ROOT/shared/templates"/adr-000*.md; do
     dest="docs/02-design/technical/adrs/$(basename "$f")"
     [[ -f "$dest" ]] || cp "$f" "$dest"
   done
   ```
   Then fill in today's date in `adr-0001-hitl-adoption.md` and `adr-0002-documentation-first.md` (replace `[fill in: project start date]` with today's ISO date).

6. Say: "Hooks wired. `.hitl/hooks/`, `.claude/settings.json`, `.gitignore`, and 4 default ADRs created in `docs/02-design/technical/adrs/`. **Restart Claude Code now** so the hooks load, then re-run this command to continue setup."

---

## Step 1 — Customize CLAUDE.md

**Write `.hitl/current-change.yaml` now** (enables breadcrumbs immediately):
```yaml
change_id: prd-setup
tier: 0
status: planning
current_step:
  number: 1
  name: "Customize CLAUDE.md"
  phase: "PRD Setup"
```

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What language and framework is this project? What test framework do you use? Any specific naming or formatting conventions?"
- Fill in the placeholders based on their answers.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 2 — Initialize the system manifest

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 2
  name: "Initialize manifest"
  phase: "PRD Setup"
```

If `docs/system-manifest.yaml` is missing or has template content:
- Ask: "What are the main domains or services in this project? For each, give a one-line description."
- Create `docs/system-manifest.yaml` with their answer. Map each domain to a plausible source path and mark as provisional.
- Say: "Manifest initialized. You'll refine domain boundaries as the system grows."

If a real manifest already exists, say: "Manifest found — skipping." and move on.

---

## Step 3 — Create your first GitHub issue

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 3
  name: "Create GitHub issue"
  phase: "PRD Setup"
```

- Ask: "What's the first feature you want to build?"
- Run: `gh issue create --title "[feature name]" --body "Initial feature for [project name]. Created via HITL onboarding."`
- Show the issue URL.

---

## Step 4 — Confirm ready

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 4
  name: "Confirm ready"
  phase: "PRD Setup"
```

Output this exactly:

---
**You're ready.**

Generate the design docs for your system before writing any code:

```
/hitl:architect-design-system
```

This produces the system manifest, HLDs, LLDs, and an initial delivery plan — demoable slices sequenced by dependency, each with a decision packet at `docs/decisions/`. The 32-step workflow reads these docs at nearly every step — they must exist before feature work starts.

After `/hitl:architect-design-system` completes:

1. **Build the Graphify knowledge graph** (if Graphify is installed):
   ```bash
   graphify .              # build graph from code + docs
   graphify hook install   # auto-rebuild on every git commit
   ```
   Then commit: `git add graphify-out/ && git commit -m "chore: add graphify knowledge graph"` (add `graphify-out/manifest.json` and `graphify-out/cost.json` to `.gitignore` first).
   If Graphify is not yet installed, install it now (`uv tool install graphifyy && graphify claude install`) or skip — HITL skills work without it but perform better with it. See `shared/graphify-setup.md`.

2. **Set up the build and deployment pipeline** before any code is written:
   - The deployment view in the architect's HLD is the spec — use it to provision CI/CD (GitHub Actions, Jenkins, GitLab CI, etc.) with build, test, and deploy-to-staging jobs at minimum
   - Provision at least one target environment (staging) — the 32-step workflow gates every PR on a passing staging deploy
   - Verify: a commit triggers the pipeline and produces a deployable artifact
   - Run `/hitl:ops-apply-iac` to apply the IaC that provisions the pipeline and environments
   - Do not include a production deploy job without an explicit manual approval gate

3. Assign decision packets to developers — each developer picks up one packet and runs the 32-step workflow from it.
4. For new features after the initial build, create a GitHub issue and run `/hitl:dev-practices`.

---
