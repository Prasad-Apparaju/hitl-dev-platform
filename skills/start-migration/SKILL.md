---
name: start-migration
description: Start a migration project. Collects migration context, ingests external migration documentation as reference material, sets up the project structure, and hands off to /migrate:review-external-docs for the architect's deep review before design begins.
argument-hint: "[optional: source system name or migration description]"
---

# Start a Migration Project

Setting up a migration project for HITL AI-Driven Development. Migration is treated as a variant of brownfield: the source system is documented, the target system is designed, and external migration documentation is ingested as reference material — not as canonical HITL docs.

Work through these steps in order — pause after each and wait for confirmation before proceeding.

---

## Step 1 — Collect migration context

Ask the following questions and record the answers. Do not proceed until all four are answered:

1. **Source system:** What is being migrated? Describe the current system — language, framework, key domains, approximate size.
2. **Target system:** What is it migrating to? Describe the target architecture — new language/framework, infrastructure changes, new domains if any.
3. **Migration trigger:** Why now? (compliance requirement, vendor end-of-life, performance ceiling, architecture debt, cost — be specific)
4. **External documentation:** Do you have existing migration documentation — vendor runbooks, consultant deliverables, prior analysis, field mapping specs? If yes, list the files or describe what you have.

Record the answers in `docs/00-migration/migration-context.yaml` (create it now — this is project-level bootstrap state, separate from the per-change `.hitl/current-change.yaml`):

```yaml
# Migration project context — written once during /start-migration
# This is project-level metadata, not a per-change runtime file.
source_system: <description>
target_system: <description>
trigger: <reason>
external_docs_available: true|false
```

---

## Step 2 — Customize CLAUDE.md

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What language and framework is the TARGET system? What test framework? Any naming or formatting conventions?"
- Fill in the placeholders for the target system's conventions — migration code must follow the target standards, not the source.
- Show a diff of what changed.
- Ask: "Does this look right?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 3 — Initialize the system manifest for the target

The system manifest represents the **target** architecture — what you are building toward. The source system is documented separately.

If `docs/system-manifest.yaml` is missing or template-only:
- Ask: "What are the main domains in the TARGET system? For each, give a one-line description."
- Create `docs/system-manifest.yaml` with the target domains. Mark each as `status: provisional`.
- Say: "Manifest initialized for the target system. You'll refine domain boundaries as the design proceeds."

If a real manifest already exists, ask: "Is this manifest for the target system or the source? Let's confirm before proceeding."

---

## Step 4 — Set up migration directory structure

Create the following directories if they do not exist:

```
docs/00-migration/
  migration-context.yaml    ← written in Step 1 (project-level bootstrap state)
  external-reference/       ← external docs go here (reference only, never canonical)
  migration-review.md       ← produced by /migrate:review-external-docs (stub for now)
  migration-brief.md        ← produced by /migrate:review-external-docs (PRD-equivalent)
```

```bash
mkdir -p docs/00-migration/external-reference
```

Say: "Migration directory structure created. External docs staged in `docs/00-migration/external-reference/` are reference material — the HITL workflow generates new canonical docs from them, not from the originals."

---

## Step 5 — Ingest external documentation

If external docs are available (from Step 1):

For each external document:
- Ask the user to provide the file path or paste the content.
- Copy or save to `docs/00-migration/external-reference/<doc-name>.<ext>`.
- Do NOT edit the external docs — preserve them exactly as received.

After all docs are ingested:

```
External reference docs staged:
  docs/00-migration/external-reference/
    ├── <doc-1>
    ├── <doc-2>
    └── ...

These are reference material only. The architect's deep review (next step) will extract what is reliable, flag what is questionable, and identify gaps — before any HITL design work begins.
```

If no external docs are available: say "No external docs to ingest — the architect will design from scratch using the migration context collected in Step 1." and move on.

---

## Step 6 — Seed the registries

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

Run:
```bash
gh issue create \
  --title "Migration: [source system] → [target system]" \
  --body "Migration project initialized via HITL. Context: docs/00-migration/migration-context.yaml. External reference docs staged in docs/00-migration/external-reference/. Next: /migrate:review-external-docs produces migration-review.md and migration-brief.md before any design begins."
```

Show the issue URL.

---

## Step 8 — Confirm ready and hand off

Output this exactly:

---
**Migration project initialized.**

Project structure, conventions, target manifest, and external reference docs are in place.

**Next step — Architect deep review:**

```
/migrate:review-external-docs
```

The architect runs this to produce two documents:
- `docs/00-migration/migration-review.md` — critique of the external docs: what is reliable, what has gaps, what the HITL design should diverge from
- `docs/00-migration/migration-brief.md` — PRD-equivalent requirements for the target system

No design work (HLD/LLD) begins until both documents are approved. The migration brief is the required input for the architect design skills — it replaces `docs/01-product/prd.md` in the standard workflow.

After the review, the architect runs `/architect:design-system docs/00-migration/migration-brief.md` (full-system migration) or `/architect:design-feature` (slice-by-slice). Each resulting slice is handed to developers via the standard 31-step workflow.

**Slice criterion for migration:** every slice must be **observable** — either user-visible (PM can demo it) or verifiable (ops/QA can confirm via record counts, data consistency checks, or performance comparison).

---
