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
           if os.path.isfile(os.path.join(path, 'ai/claude/plugin/plugin.json')):
               print(path); sys.exit(0)
   except: pass
   print('NOT_FOUND')
   "
   ```
   If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found in your Claude Code settings. Confirm it was installed with `claude plugin add /path/to/hitl-dev-platform`."

2. Create `.hitl/hooks/` and write a wrapper for each of these six hooks: `welcome`, `check-hitl-context`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`. Each wrapper is:
   ```bash
   #!/usr/bin/env bash
   exec bash "${HITL_PLATFORM_ROOT:-<platform-path>}/ai/claude/hooks/<name>.sh" "$@"
   ```
   Replace `<platform-path>` with the path found above and `<name>` with the hook name. Run `chmod 750` on each file.

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

## Step 1 — Map the codebase

List the top-level directories and identify source code locations.
- Ask: "Are these the right source directories? Anything to exclude?"
- Confirm the language and framework.

---

## Step 2 — Customize CLAUDE.md

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What are this project's naming conventions, test framework, and any standards AI should follow?"
- Fill in the placeholders based on their answers and the observed codebase patterns.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 3 — Generate the system manifest baseline

If `docs/system-manifest.yaml` is missing or template-only:
- Run: `python tools/generate-manifest/generator.py --source [confirmed source dirs] --output docs/system-manifest.yaml`
- If the generator is unavailable, say so and ask: "Describe your main services and domains — I'll create the manifest manually."
- After generating, show the domain list and ask: "Review these domains. What should be added, removed, or renamed?"
- Incorporate feedback and update the manifest.

If a real manifest already exists, read it, summarize the domains, and ask: "Is this manifest still accurate? Anything outdated?"

---

## Step 4 — Identify priority components for documentation

Ask: "Which components are most critical and most likely to change in the near term? List up to three."

For each component:
- Say: "I'll generate an HLD and LLD for [component]. Run `/hitl:dev-generate-docs` or I can do it now — which do you prefer?"
- If they want it now, run `/hitl:dev-generate-docs` for that component.
- Note: this is incremental — you do not need to document everything before starting work.

---

## Step 5 — Seed the registries

The 32-step workflow queries these two registries at multiple points. They must exist before `/hitl:dev-practices` is run for the first time.

**Test registry** (`docs/03-engineering/testing/test-registry.yaml`):
- Ask: "Do you have existing tests? If so, I'll create a registry stub from your test files."
- If yes: scan `tests/`, `spec/`, or equivalent; generate one entry per test file with `domain` and `path`. Leave `risk` and `covers` as DRAFT.
- If no: create an empty stub.

**Incident registry** (`docs/04-operations/incident-registry.yaml`):
- Ask: "What broke in production in the last 6 months? Describe each incident in one sentence."
- For each answer, add one entry with `description`, `domain` (best guess), and `date`.
- If they have nothing: create an empty stub and say: "You can add entries later — after each production incident, run `/hitl:ops-log-incident`."

---

## Step 6 — Install Graphify

Graphify builds a queryable knowledge graph from your docs and code. HITL skills use it to look up domains, incidents, and test coverage without exhausting the context window.

```bash
uv tool install graphifyy        # install once per machine (or: pipx install graphifyy)
graphify claude install          # register /graphify skill with Claude Code
graphify .                       # build the graph from existing code and docs
graphify hook install            # auto-rebuild on every git commit
```

Then commit the graph so teammates get it immediately:
```bash
echo "graphify-out/manifest.json" >> .gitignore
echo "graphify-out/cost.json" >> .gitignore
git add graphify-out/ .gitignore
git commit -m "chore: add graphify knowledge graph"
```

Ask: "Is Graphify installed? (`graphify --version`)"
- If yes: run the commands above and continue.
- If no: show the install command and wait for confirmation.

Full setup reference: `shared/graphify-setup.md`

---

## Step 7 — Create your first change issue

Ask: "What's the first change you want to make now that this project is onboarded?"
- Run: `gh issue create --title "[change description]" --body "First tracked change after HITL brownfield onboarding."`
- Show the issue URL.

---

## Step 8 — Confirm ready

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
