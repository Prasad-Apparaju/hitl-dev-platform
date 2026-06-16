---
description: Onboard an existing codebase into the HITL process. Generates a documentation baseline from existing code, seeds the test and incident registries, and prepares for docs-first development going forward.
argument-hint: "[optional: path to source root or description of the codebase]"
disable-model-invocation: true
---

# Onboard an Existing Codebase

Bringing an existing codebase into HITL AI-Driven Development. Work through these steps in order — pause after each and wait for confirmation before proceeding.

**Quick sanity check:** If this is a brand-new project with no source code, use `/hitl:dev-start-from-prd` instead. If you are migrating from one system to another (not just onboarding what exists), use `/hitl:dev-start-migration`.

---

## Step 0 — Wire up HITL hooks (once per project)

Check whether `.hitl/hooks/` already exists.

**If it does — hooks are already wired. Skip sub-steps 1–3, but still run sub-steps 4–5** (gitignore and ADR stubs are idempotent and must always be present):

1. Find the plugin root (needed for the ADR copy):
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
2. Run sub-steps 4 and 5 below (gitignore + ADR stubs), then say "Hooks already wired — skipped hook creation, ensured ADR stubs present." and proceed to Step 1.

**If it does not exist — run all sub-steps:**

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

## Step 1 — Map the codebase

**Write `.hitl/current-change.yaml` now** (enables breadcrumbs immediately):
```yaml
change_id: brownfield-setup
tier: 0
status: planning
current_step:
  number: 1
  name: "Map codebase"
  phase: "Brownfield Setup"
```

List the top-level directories and identify source code locations.
- Ask: "Are these the right source directories? Anything to exclude?"
- Confirm the language and framework.

---

## Step 2 — Customize CLAUDE.md

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 2
  name: "Customize CLAUDE.md"
  phase: "Brownfield Setup"
```

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What are this project's naming conventions, test framework, and any standards AI should follow?"
- Fill in the placeholders based on their answers and the observed codebase patterns.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 3 — Generate the system manifest baseline

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 3
  name: "Generate manifest"
  phase: "Brownfield Setup"
```

If `docs/system-manifest.yaml` is missing or template-only:
- Run: `python tools/generate-manifest/generator.py --source [confirmed source dirs] --output docs/system-manifest.yaml`
- If the generator is unavailable, say so and ask: "Describe your main services and domains — I'll create the manifest manually."
- After generating, show the domain list and ask: "Review these domains. What should be added, removed, or renamed?"
- Incorporate feedback and update the manifest.

If a real manifest already exists, read it, summarize the domains, and ask: "Is this manifest still accurate? Anything outdated?"

---

## Step 4 — Review existing architecture

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 4
  name: "Arch review"
  phase: "Brownfield Setup"
```

Run `/hitl:architect-review-existing` to reconstruct the architectural decisions already in the codebase, interview the architect to confirm rationale and constraints, and document them as real ADRs before any incremental work begins.

This step produces:
- A tech stack summary
- ADR-0005+ for significant existing decisions (framework, data, auth, API style, deployment, test strategy)
- A list of architectural concerns that affect HITL compliance or first-change risk

Do not proceed to Step 6 until the architect has confirmed the ADRs are accurate.

---

## Step 5 — Verify build and deployment pipeline

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 5
  name: "Verify pipeline"
  phase: "Brownfield Setup"
```

The deployment view generated in Step 4 (Phase 4c of `/hitl:architect-review-existing`) describes the CI/CD pipeline. This step confirms it actually works before feature development begins.

**1. Identify the CI/CD system:**

Check which CI/CD configuration files exist:

| File | System |
|---|---|
| `.github/workflows/*.yml` | GitHub Actions |
| `Jenkinsfile` | Jenkins |
| `.gitlab-ci.yml` | GitLab CI |
| `.circleci/config.yml` | CircleCI |
| `.buildkite/pipeline.yml` | Buildkite |

If none found: skip to "Pipeline missing" below.

**2. Verify the build:**

Run the project's build command (infer from the tech stack confirmed in Step 2 — `npm run build`, `mvn package`, `go build ./...`, `./gradlew build`, etc.).

- ✅ Build passes → continue
- 🔴 Build fails → record the error and say: "Build is broken — fix this before feature work begins. Run `/hitl:ops-build` for a structured diagnosis."

**3. Verify the deployment path:**

Check whether the CI/CD config includes:
- A job that deploys to at least one non-production environment (staging, dev, test)
- A job or manual gate for production deploy

The 32-step workflow (`/hitl:dev-practices`) gates every PR on a passing staging deploy — if no staging job exists, that gate cannot function.

- ✅ Staging deploy job exists → proceed
- 🟡 No staging deploy job → note it: "The HITL staging gate will need a manual workaround until a staging deploy job is added."
- 🔴 No deploy jobs at all → treat same as pipeline missing below

**Pipeline missing or broken:**

If no CI/CD config exists, or the build fails and cannot be quickly fixed, say:

> "No working build pipeline found. This is a 🔴 concern — the 32-step workflow requires a passing build and a staging deploy path before a PR can be closed.
>
> Options:
> - Scaffold a CI/CD config now: describe your hosting target (GitHub Actions → AWS/GCP/Azure/Railway/Fly.io) and I'll generate a starter pipeline
> - Set it up manually and re-run this step when ready
> - Proceed and accept that the build and deploy steps of the 32-step workflow will need manual execution until the pipeline exists"

If they want a scaffold, generate a minimal CI/CD config (build → test → deploy-to-staging) using the tech stack from Step 2 and the deployment target from the deployment view. Do not include a production deploy job without an explicit approval gate.

---

## Step 6 — Identify priority components for documentation

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 6
  name: "Priority docs"
  phase: "Brownfield Setup"
```

Ask: "Which components are most critical and most likely to change in the near term? List up to three."

For each component:
- Say: "I'll generate an HLD and LLD for [component]. Run `/hitl:dev-generate-docs` or I can do it now — which do you prefer?"
- If they want it now, run `/hitl:dev-generate-docs` for that component.
- Note: this is incremental — you do not need to document everything before starting work.

---

## Step 7 — Seed the registries

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 7
  name: "Seed registries"
  phase: "Brownfield Setup"
```

The 32-step workflow queries these two registries at multiple points. They must exist before `/hitl:dev-practices` is run for the first time.

**Test registry** (`docs/03-engineering/testing/test-registry.yaml`):
- Ask: "Do you have existing tests? If so, I'll create a registry stub from your test files."
- If yes: scan `tests/`, `spec/`, or equivalent; generate one entry per test file with `domain` and `path`. Leave `risk` and `covers` as DRAFT.
- If no: create an empty stub.

**Incident registry** (`docs/04-operations/incident-registry.yaml`):
- Ask: "What broke in production in the last 6 months? Describe each incident in one sentence."
- For each answer, add one entry with `description`, `domain` (best guess), and `date`.
- If they have nothing: create an empty stub and say: "You can add entries later — after each production incident, run `/hitl:ops-incident`."

---

## Step 8 — Build Graphify knowledge graph (optional)

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 8
  name: "Graphify"
  phase: "Brownfield Setup"
```

Graphify builds a queryable knowledge graph from your docs and code. HITL skills use it to look up domains, incidents, and test coverage without exhausting the context window.

Run `graphify --version` to check if it is installed.

**If installed:** run the per-project commands now:
```bash
graphify .              # build the graph from existing code and docs
graphify hook install   # auto-rebuild on every git commit
```

Then commit so teammates get it immediately:
```bash
echo "graphify-out/manifest.json" >> .gitignore
echo "graphify-out/cost.json" >> .gitignore
git add graphify-out/ .gitignore
git commit -m "chore: add graphify knowledge graph"
```

**If not installed:** say "Graphify not found — skipping. Install it when convenient with `uv tool install graphifyy && graphify claude install`, then run `graphify .` in this repo. HITL skills fall back gracefully without it. See `shared/graphify-setup.md`." and continue to Step 8.

---

## Step 9 — Create your first change issue

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 9
  name: "Create issue"
  phase: "Brownfield Setup"
```

Ask: "What's the first change you want to make now that this project is onboarded?"
- Run: `gh issue create --title "[change description]" --body "First tracked change after HITL brownfield onboarding."`
- Show the issue URL.

---

## Step 10 — Confirm ready

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 10
  name: "Confirm ready"
  phase: "Brownfield Setup"
```

Output this exactly:

---
**Brownfield baseline established.**

You are starting incrementally: manifest and priority component docs exist, registries are seeded. Undocumented components will need their LLDs created when you first change them — run `/hitl:dev-generate-docs` for that component, then resume.

**What this means for your first changes:**
- Treat AI output from steps 5, 10, and 14 as drafts — the docs are new and may not yet reflect actual behavior. Increase human review scrutiny until the docs have been corrected through real use.
- If `/hitl:dev-practices` stops with "no LLD found" on an undocumented component, run `/hitl:dev-generate-docs` for that component, then resume. This friction decreases naturally as each component gets its first doc pass through real use.

For every change going forward:
1. Create a GitHub issue — or use `/hitl:pm-add-feature` / `/hitl:pm-design-feature` to shape requirements first
2. Run `/hitl:dev-practices` — the 32-step workflow starts here
3. Update HLD/LLD if the design changes
4. Code → tests → PR

---
