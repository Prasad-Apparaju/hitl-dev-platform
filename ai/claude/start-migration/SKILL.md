---
description: Start a migration project. Collects migration context, ingests external migration documentation as reference material, sets up the project structure, and hands off to /hitl:dev-review-external-docs for the architect's deep review before design begins.
argument-hint: "[optional: source system name or migration description]"
disable-model-invocation: true
---

# Start a Migration Project

Setting up a migration project for HITL AI-Driven Development.

**Migration is not brownfield.** In brownfield you work *inside* the existing codebase — it is the live product. In migration the source codebase is being *replaced*: it is read-only reference. Only behaviors transfer to the target, never code. The behavioral inventory (`docs/00-migration/source-behavioral-inventory.md`) is the only bridge between the two systems.

Work through these steps in order — pause after each and wait for confirmation before proceeding.

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

6. Say: "Hooks wired. `.hitl/hooks/`, `.claude/settings.json`, `.gitignore`, and 8 baseline ADRs created in `docs/02-design/technical/adrs/`. **Restart Claude Code now** so the hooks load, then re-run this command to continue setup."

---

## Step 1 — Collect migration context

**Write `.hitl/current-change.yaml` now** (before asking questions — this enables breadcrumbs immediately):

```yaml
schema_version: "2.0"
change_id: migration-setup
tier: 3
status: planning
workflow:
  id: migration
  total: 9
  steps:
    - { n: 1, key: collect_context, label: "Context",    phase: "Migration Setup", status: current }
    - { n: 2, key: claude_md,       label: "CLAUDE.md",  phase: "Migration Setup", status: open }
    - { n: 3, key: manifest,        label: "Manifest",   phase: "Migration Setup", status: open }
    - { n: 4, key: dir_setup,       label: "DirSetup",   phase: "Migration Setup", status: open }
    - { n: 5, key: source_analysis, label: "SrcAnal",    phase: "Migration Setup", status: open }
    - { n: 6, key: ext_docs,        label: "ExtDocs",    phase: "Migration Setup", status: open }
    - { n: 7, key: seed_registries, label: "Registries", phase: "Migration Setup", status: open }
    - { n: 8, key: create_issue,    label: "Issue",      phase: "Migration Setup", status: open }
    - { n: 9, key: confirm_ready,   label: "Ready",      phase: "Migration Setup", status: open }
current_step:
  number: 1
  name: "Collect migration context"
  phase: "Migration Setup"
```

> **Breadcrumb advancement:** at the start of each step below, edit `.hitl/current-change.yaml`
> to set the previous step's `status: done` and the current step's `status: current`, and update
> `current_step` to match.

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

**Regardless of whether CLAUDE.md was just created or already existed, append the following block.** This rule must be present in every session so the agent never silently copies source code:

```markdown
## Migration — source code is read-only

The source codebase (location recorded in `docs/00-migration/migration-context.yaml`) is
reference only. It is being replaced, not extended.

**Never copy, import, port, or adapt source code into the target.** All target behaviors
must be implemented from scratch. The behavioral inventory at
`docs/00-migration/source-behavioral-inventory.md` is the only bridge: each BI-NNN entry
describes what the target must do; how it does it is a fresh design decision.

If source code helps you understand a behavior, read it — then implement the behavior
anew in the target language, framework, and style.
```

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
  migration-context.yaml          ← written in Step 1 (project-level bootstrap state)
  source-behavioral-inventory.md  ← written in Step 5 (source of truth for migration coverage)
  external-reference/             ← external docs go here (reference only, never canonical)
  migration-review.md             ← produced by /hitl:dev-review-external-docs (stub for now)
  migration-brief.md              ← produced by /hitl:dev-review-external-docs (PRD-equivalent)
```

```bash
mkdir -p docs/00-migration/external-reference
```

Say: "Migration directory structure created. External docs staged in `docs/00-migration/external-reference/` are reference material — the HITL workflow generates new canonical docs from them, not from the originals."

---

## Step 5 — Analyze source codebase

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 5
  name: "Analyze source codebase"
  phase: "Migration Setup"
```

The source codebase is the ground truth for what the target must **do** — not for how to build it. This step extracts a **behavioral inventory**: the definitive list of APIs, domain behaviors, data contracts, and integration points that the target system must reproduce. Migration is only complete when every item in the inventory is covered.

**Read-only rule:** the source code is reference material only. After this step, it must not influence the target's implementation — only the BI-NNN entries do. If source code clarifies a behavior during development, read it; then implement the behavior from scratch.

**Locate the source code:**

Ask: "Where is the source system's code?"
- **(A)** A directory in this repo at path: ___
- **(B)** A separate local repository at path: ___
- **(C)** Remote-only or inaccessible — I'll describe its behavior from memory or docs

**If A or B — read the source code:**

1. Read the top-level structure to orient, then focus on:

   | What to extract | Where to look |
   |---|---|
   | Exposed APIs | REST routes, GraphQL schema, gRPC `.proto` files, event topics published |
   | Core domain logic | Services, use cases, domain objects, business rule implementations |
   | Data contracts | DB schema, migration files, ORM models, key data shapes |
   | Integration points | Outbound HTTP clients, queue consumers, webhook handlers, third-party SDKs |
   | Auth and access control | Who can call what — roles, scopes, ownership rules |
   | Background jobs | Scheduled tasks, workers, async processors |

2. Use Graphify if available on the source repo:
   ```
   /graphify query "API endpoints domain services data models integrations auth"
   ```

3. Produce `docs/00-migration/source-behavioral-inventory.md`:

```markdown
# Source Behavioral Inventory — [Source System Name]

**Extracted from:** [repo path or URL]
**Extraction date:** [today's date]
**Status:** DRAFT — review with source system owner before use as migration target

## API surface

| ID | Endpoint / contract | Type | Domain | Notes |
|---|---|---|---|---|
| BI-001 | GET /users/{id} | REST | User | Returns user profile |

## Core behaviors

| ID | Behavior | Domain | Source location | Notes |
|---|---|---|---|---|
| BI-010 | Calculate order total with tax | Order | OrderService.java:45 | Includes promotional discount logic |

## Data contracts

| ID | Entity | Storage | Key fields | Notes |
|---|---|---|---|---|
| BI-020 | User | users table (PostgreSQL) | id, email, tenant_id | Multi-tenant — tenant_id on every query |

## Integration contracts

| ID | Integration | Direction | Protocol | Notes |
|---|---|---|---|---|
| BI-030 | Payment gateway | Outbound | REST | Stripe v3, async webhook confirmation |

## Background jobs

| ID | Job | Schedule / trigger | Domain | Notes |
|---|---|---|---|---|
| BI-040 | Invoice generation | Nightly 02:00 UTC | Billing | |

## Auth and access control

| ID | Rule | Scope | Notes |
|---|---|---|---|
| BI-050 | Admins can delete any user | Admin role | Non-admins see 403 |

## Known gaps

[Behaviors that could not be determined from code alone — require source system owner clarification]
```

Ask: "Does this inventory capture everything the source system does? Anything I missed or got wrong?"

Incorporate feedback and finalize. This file is the migration's definition of done — the target must implement every BI entry.

**If C — source is inaccessible:**

Ask: "Describe the source system's key APIs, core business behaviors, data contracts, and integration points. I'll structure them as the behavioral inventory."

Record what the user provides. Mark every entry `confidence: low — from description only`. Say: "The behavioral inventory is based on your description since the source code isn't available. Treat it as a starting point — expand it whenever a gap is discovered during development."

Write `docs/00-migration/source-behavioral-inventory.md` with entries marked `confidence: low`.

---

## Step 6 — Ingest external documentation (optional)

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 6
  name: "Ingest external docs"
  phase: "Migration Setup"
```

Present the following choice to the user:

---
**Step 6 is optional — choose one:**

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

## Step 7 — Seed the registries

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 7
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

## Step 8 — Create the migration tracking issue

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 8
  name: "Create tracking issue"
  phase: "Migration Setup"
```

Run:
```bash
gh issue create \
  --title "Migration: [source system] → [target system]" \
  --body "Migration project initialized via HITL. Context: docs/00-migration/migration-context.yaml. Behavioral inventory (source of truth): docs/00-migration/source-behavioral-inventory.md. External reference docs staged in docs/00-migration/external-reference/. Next: /hitl:dev-review-external-docs produces migration-review.md and migration-brief.md before any design begins."
```

Show the issue URL. Then update `.hitl/current-change.yaml`: set `change_id: GH-<issue-number>` (replace the `migration-setup` placeholder).

---

## Step 9 — Confirm ready and hand off

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 9
  name: "Confirm and hand off"
  phase: "Migration Setup"
```

Output this exactly:

---
**Migration project initialized.**

Project structure, conventions, target manifest, behavioral inventory, and external reference docs are in place.

**Next step — Architect deep review:**

```
/hitl:dev-review-external-docs
```

The architect runs this to produce two documents:
- `docs/00-migration/migration-review.md` — critique of the external docs: what is reliable, what has gaps, what HITL design should diverge from
- `docs/00-migration/migration-brief.md` — PRD-equivalent requirements for the target system, including a behavior coverage matrix keyed to BI IDs from the behavioral inventory

No design work (HLD/LLD) begins until both documents are approved. The migration brief is the required input for the architect design skills — it replaces `docs/01-product/prd.md` in the standard workflow.

After the review, the architect runs `/hitl:architect-design-system docs/00-migration/migration-brief.md` (full-system migration) or `/hitl:architect-design-feature` (slice-by-slice).

**Before the first development slice begins — generate the platform roadmap:**

Initialize the platform readiness register:
`mkdir -p docs/04-operations && cp "$PLUGIN_ROOT/shared/templates/platform-readiness-template.yaml" docs/04-operations/platform-readiness.yaml`,
set `project_kind: migration` (this activates the migration-only **Parity** and **Cutover**
layers: golden-dataset harness, shadow-run, cutover plan with rollback-to-legacy, dual-run
window, legacy sunset — a migration is not done when the code is ported; it is done when
the legacy system is off).

Then run `/hitl:ops-plan-platform derive` — it reads the source analysis and the external-docs
review, seeds the parity items with the concrete user-facing contracts to compare, and
generates the roadmap issues (pipeline, staging environment, observability, parity harness,
cutover plan). Each roadmap issue is an ordinary HITL change. Tier 2+ **production** deploys
of the target stay blocked until the register says `delivery_ready: true`.

Observability for the target system is item F1 of the readiness register (dashboards,
alerting, on-call; record the chosen stack in
`docs/02-design/technical/adrs/adr-0005-observability-strategy.md`, and copy
`shared/templates/token-cost-registry-template.yaml` to
`docs/04-operations/token-cost-registry.yaml` for agentic observability).
`/hitl:ops-setup-observability` gates each slice's production deploy and requires those
tools to exist — the roadmap sequences that standup before the first production slice.

Each resulting slice is then handed to developers via the standard 31-step workflow, and must declare which BI IDs it covers.

**Slice criterion for migration:** every slice must be **observable** — either user-visible (PM can demo it) or verifiable (ops/QA can confirm via record counts, data consistency checks, or performance comparison).

**Migration is complete when:** every BI entry in `docs/00-migration/source-behavioral-inventory.md` has status `Complete` or `Descoped` in the migration brief's coverage matrix, **and** the readiness register's Parity and Cutover layers are green — parity proven against the legacy system, cutover executed, legacy sunset recorded. Ported code with the legacy still running is not a finished migration.

---
