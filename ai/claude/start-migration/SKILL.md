---
description: Start a migration project. Collects migration context, ingests external migration documentation as reference material, sets up the project structure, and hands off to /hitl:dev-review-external-docs for the architect's deep review before design begins.
argument-hint: "[optional: source system name or migration description]"
disable-model-invocation: true
---

# Start a Migration Project

Setting up a migration project for HITL AI-Driven Development. Migration is treated as a variant of brownfield: the source system is documented, the target system is designed, and external migration documentation is ingested as reference material — not as canonical HITL docs.

Work through these steps in order — pause after each and wait for confirmation before proceeding.

---

## Step 0 — Wire up HITL hooks (once per project)

Check whether `.hitl/hooks/` already exists. If it does, say "Hooks already wired — skipping." and proceed to Step 1.

If not:

1. Find the HITL plugin path:
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

2. Create `.hitl/hooks/` and write a wrapper for each of these six hooks: `welcome`, `check-hitl-context`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`. Each wrapper resolves the plugin path dynamically from `~/.claude/settings.json` so it survives plugin updates and reinstalls without any hardcoded path:
   ```bash
   #!/usr/bin/env bash
   PLUGIN_ROOT=$(python3 -c "
   import json,os,sys
   cfg=os.path.expanduser('~/.claude/settings.json')
   try:
     data=json.load(open(cfg))
     for p in data.get('plugins',[]):
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

## Step 1 — Collect migration context

**Write `.hitl/current-change.yaml` now** (before asking questions — this enables breadcrumbs immediately):

```yaml
change_id: migration-setup
tier: 3
status: planning
current_step:
  number: 1
  name: "Collect migration context"
  phase: "Migration Setup"
```

Ask the following questions and record the answers. Do not proceed until all four are answered:

1. **Source system:** What is being migrated? Describe the current system — language, framework, key domains, approximate size.
2. **Target system:** What is it migrating to? Describe the target architecture — new language/framework, infrastructure changes, new domains if any.
3. **Migration trigger:** Why now? (compliance requirement, vendor end-of-life, performance ceiling, architecture debt, cost — be specific)
4. **External documentation:** Do you have existing migration documentation — vendor runbooks, consultant deliverables, prior analysis, field mapping specs? If yes, list the files or describe what you have.

Record the answers in `docs/00-migration/migration-context.yaml` (create it now — this is project-level bootstrap state, separate from the per-change `.hitl/current-change.yaml`):

```yaml
# Migration project context — written once during /hitl:start-migration
# This is project-level metadata, not a per-change runtime file.
source_system: <description>
target_system: <description>
trigger: <reason>
external_docs_available: true|false
```

---

## Step 2 — Customize CLAUDE.md

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 2
  name: "Customize CLAUDE.md"
  phase: "Migration Setup"
```

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What language and framework is the TARGET system? What test framework? Any naming or formatting conventions?"
- Fill in the placeholders for the target system's conventions — migration code must follow the target standards, not the source.
- Show a diff of what changed.
- Ask: "Does this look right?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 3 — Initialize the system manifest for the target

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 3
  name: "Initialize system manifest"
  phase: "Migration Setup"
```

The system manifest represents the **target** architecture — what you are building toward. The source system is documented separately.

If `docs/system-manifest.yaml` is missing or template-only:
- Ask: "What are the main domains in the TARGET system? For each, give a one-line description."
- Create `docs/system-manifest.yaml` with the target domains. Mark each as `status: provisional`.
- Say: "Manifest initialized for the target system. You'll refine domain boundaries as the design proceeds."

If a real manifest already exists, ask: "Is this manifest for the target system or the source? Let's confirm before proceeding."

---

## Step 4 — Set up migration directory structure

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 4
  name: "Set up directory structure"
  phase: "Migration Setup"
```

Create the following directories if they do not exist:

```
docs/00-migration/
  migration-context.yaml    ← written in Step 1 (project-level bootstrap state)
  external-reference/       ← external docs go here (reference only, never canonical)
  migration-review.md       ← produced by /hitl:dev-review-external-docs (stub for now)
  migration-brief.md        ← produced by /hitl:dev-review-external-docs (PRD-equivalent)
```

```bash
mkdir -p docs/00-migration/external-reference
```

Say: "Migration directory structure created. External docs staged in `docs/00-migration/external-reference/` are reference material — the HITL workflow generates new canonical docs from them, not from the originals."

---

## Step 5 — Ingest external documentation (optional)

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 5
  name: "Ingest external docs"
  phase: "Migration Setup"
```

Present the following choice to the user:

---
**Step 5 is optional — choose one:**

**A — Copy docs into this repo** (`docs/00-migration/external-reference/`)
> Best when: the reference repo is private, may become unavailable, or team members lack access.
> What happens: you provide file paths or paste content; I copy them as-is. No editing.
> Downside: files can drift from the source of truth over time.

**B — Link only (skip copy)**
> Best when: the reference repo is public and key decisions are already captured in `system-manifest.yaml` and `migration-context.yaml` (which Steps 3–4 produce).
> What happens: I verify the `poc_reference` links in `migration-context.yaml` are live and confirm key architectural decisions are reflected in the manifest. No file copy.
> Downside: future sessions need network access to the reference repo.

**C — No external docs**
> The architect will design from scratch using the migration context collected in Step 1.

---

**If A:** For each external document, ask the user to provide the file path or paste the content. Copy or save to `docs/00-migration/external-reference/<doc-name>.<ext>`. Do NOT edit the external docs — preserve them exactly as received. Then print the staged file list.

**If B:** Verify `poc_reference.repo` in `migration-context.yaml` is reachable (`curl -sI <url> | head -1` or `gh repo view <repo>`). Confirm key decisions are present in `system-manifest.yaml` (check `key_decisions` block or `robustness_primitives`). Report: "Reference links verified. Key decisions captured in manifest. No file copy needed." and move on.

**If C:** Say "No external docs to ingest — the architect will design from scratch." and move on.

---

## Step 6 — Seed the registries

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 6
  name: "Seed registries"
  phase: "Migration Setup"
```

**Test registry** (`docs/03-engineering/testing/test-registry.yaml`):
- Ask: "Do you have existing tests for the source system? I'll create a registry stub."
- If yes: generate one entry per test file. Mark all as `status: DRAFT — pre-migration`.
- If no: create an empty stub.

**Incident registry** (`docs/04-operations/incident-registry.yaml`):
- Ask: "What broke in the SOURCE system in the last 6 months? These become regression targets in the target system."
- For each: add one entry with `description`, `domain`, `date`, and `migration_regression: true`.
- If none: create an empty stub.

---

## Step 7 — Create the migration tracking issue

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 7
  name: "Create tracking issue"
  phase: "Migration Setup"
```

Run:
```bash
gh issue create \
  --title "Migration: [source system] → [target system]" \
  --body "Migration project initialized via HITL. Context: docs/00-migration/migration-context.yaml. External reference docs staged in docs/00-migration/external-reference/. Next: /hitl:dev-review-external-docs produces migration-review.md and migration-brief.md before any design begins."
```

Show the issue URL. Then update `.hitl/current-change.yaml`: set `change_id: GH-<issue-number>` (replace the `migration-setup` placeholder).

---

## Step 8 — Confirm ready and hand off

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 8
  name: "Confirm and hand off"
  phase: "Migration Setup"
```

Output this exactly:

---
**Migration project initialized.**

Project structure, conventions, target manifest, and external reference docs are in place.

**Next step — Architect deep review:**

```
/hitl:dev-review-external-docs
```

The architect runs this to produce two documents:
- `docs/00-migration/migration-review.md` — critique of the external docs: what is reliable, what has gaps, what the HITL design should diverge from
- `docs/00-migration/migration-brief.md` — PRD-equivalent requirements for the target system

No design work (HLD/LLD) begins until both documents are approved. The migration brief is the required input for the architect design skills — it replaces `docs/01-product/prd.md` in the standard workflow.

After the review, the architect runs `/hitl:architect-design-system docs/00-migration/migration-brief.md` (full-system migration) or `/hitl:architect-design-feature` (slice-by-slice). Each resulting slice is handed to developers via the standard 32-step workflow.

**Slice criterion for migration:** every slice must be **observable** — either user-visible (PM can demo it) or verifiable (ops/QA can confirm via record counts, data consistency checks, or performance comparison).

---
