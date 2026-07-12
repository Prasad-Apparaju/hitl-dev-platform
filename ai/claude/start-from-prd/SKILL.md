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

2. Create `.hitl/hooks/` and write a wrapper for each of these eight hooks: `welcome`, `hitl-gate`, `check-hitl-context`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`, `statusline-hitl`. (The shared `_steps.sh` library is sourced by the renderers from the plugin directly — it does not need a wrapper.) Each wrapper discovers the plugin path at runtime — survives plugin updates, reinstalls, and version bumps:
   ```bash
   #!/usr/bin/env bash
   # Resolve a working Python. On Windows `python3` is the Microsoft Store stub (on PATH but
   # runs nothing), so probe candidates and smoke-test each; the stub fails `import sys`.
   PY=""
   for _c in python3 python py; do
     if command -v "$_c" >/dev/null 2>&1 && "$_c" -c "import sys" >/dev/null 2>&1; then PY="$_c"; break; fi
   done
   [[ -z "$PY" ]] && exit 0
   PLUGIN_ROOT=$("$PY" -c "
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
   # Pass the resolved interpreter + force UTF-8 stdout so hooks don't re-probe or crash on
   # the breadcrumb glyphs (Windows Python defaults to cp1252). See issue #14.
   export HITL_PY="$PY" PYTHONUTF8=1 PYTHONIOENCODING=utf-8
   exec bash "$PLUGIN_ROOT/hooks/<name>.sh" "$@"
   ```
   Replace `<name>` with the hook name for each file. Run `chmod 750` on each file.

3. Create `.claude/settings.json` only if it does not already exist:
   ```json
   {
     "statusLine": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh\"",
     "hooks": {
       "SessionStart": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/hitl-gate.sh\"" }] }],
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

**Write `.hitl/current-change.yaml` now** (enables breadcrumbs immediately) with the embedded
`prd` workflow block — copied from the catalog at `ai/shared/workflows.yaml` (workflow `prd`):
```yaml
schema_version: "2.0"
change_id: prd-setup
tier: 0
status: planning
workflow:
  id: prd
  total: 5
  steps:
    - { n: 1, key: claude_md,        label: "CLAUDE.md", phase: "PRD Setup", status: current }
    - { n: 2, key: manifest,         label: "Manifest",  phase: "PRD Setup", status: open }
    - { n: 3, key: create_issue,     label: "Issue",     phase: "PRD Setup", status: open }
    - { n: 4, key: confirm_ready,    label: "Ready",     phase: "PRD Setup", status: open }
    - { n: 5, key: platform_roadmap, label: "Platform",  phase: "PRD Setup", status: open }
current_step:
  number: 1
  name: "Customize CLAUDE.md"
  phase: "PRD Setup"
```

> **Breadcrumb advancement:** at the start of each step below, edit `.hitl/current-change.yaml`
> to set the previous step's `status: done` and the current step's `status: current`, and update
> `current_step` to match. This keeps the status-line/banner trail in sync.

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

**Install the manifest drift checker** so `/hitl:dev-check-conventions` and the copied `ci/workflows/*.yml` templates (which reference it by repo path) can keep the manifest honest as code lands:

```bash
mkdir -p ci/manifest-drift
PLUGIN_ROOT=$(python3 -c "
import json,os,sys
try:
  d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
  for inst in d.get('plugins',{}).get('hitl@hitl',[]):
    p=inst.get('installPath','')
    if os.path.isfile(os.path.join(p,'.claude-plugin/plugin.json')):
      print(p);sys.exit(0)
except:pass
" 2>/dev/null)
if [[ -n "$PLUGIN_ROOT" && -f "$PLUGIN_ROOT/shared/ci/manifest-drift/check_manifest_drift.py" ]]; then
  [[ ! -f ci/manifest-drift/check_manifest_drift.py ]] && \
    cp "$PLUGIN_ROOT/shared/ci/manifest-drift/"*.py ci/manifest-drift/
  echo "Manifest drift checker installed at ci/manifest-drift/."
else
  echo "Drift checker not found in the plugin — skip; /hitl:dev-check-conventions will note it is absent."
fi
```

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
**Governance is up.**

Generate the design docs for your system before writing any code:

```
/hitl:architect-design-system
```

This produces the system manifest, HLDs, LLDs, and an initial delivery plan — demoable slices sequenced by dependency, each with a decision packet at `docs/decisions/`. The 31-step workflow reads these docs at nearly every step — they must exist before feature work starts.

Then **build the Graphify knowledge graph** (if Graphify is installed):
```bash
graphify .              # build graph from code + docs
graphify hook install   # auto-rebuild on every git commit
```
Then commit: `git add graphify-out/ && git commit -m "chore: add graphify knowledge graph"` (add `graphify-out/manifest.json` and `graphify-out/cost.json` to `.gitignore` first).
If Graphify is not yet installed, install it now (`uv tool install graphifyy && graphify claude install`) or skip — HITL skills work without it but perform better with it. See `shared/graphify-setup.md`.

Come back here when the design docs exist — Step 5 stands up the platform.

---

## Step 5 — Generate the platform roadmap

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 5
  name: "Generate platform roadmap"
  phase: "PRD Setup"
```

Governance can gate changes, but nothing exists yet to verify, deliver, or operate them:
no pipeline, no environment, no dashboards. That standup work is the **platform workflow**
(onboarded → delivery-ready), tracked in `docs/04-operations/platform-readiness.yaml`.

Run `/hitl:ops-plan-platform derive` now. It reads the PRD's NFRs and the HLD deployment
view from Step 4 (SLOs → observability targets; user tiers → environment story; compliance
→ security items), writes the readiness register, and then generates the roadmap issues
(`/hitl:ops-plan-platform roadmap`). Each roadmap issue is an ordinary HITL change.

Then output this exactly:

---
**You're ready.**

- Platform roadmap issues exist — they are ordinary HITL changes; the deploy path comes up
  as they complete. Tier 2+ **production** deploys stay blocked until the register says
  `delivery_ready: true` (staging is never blocked).
- Assign decision packets to developers — each developer picks up one packet and runs the
  31-step workflow from it.
- For new features after the initial build, create a GitHub issue and run `/hitl:dev-practices`.
- Track platform progress any time with `/hitl:ops-plan-platform status`.

---
