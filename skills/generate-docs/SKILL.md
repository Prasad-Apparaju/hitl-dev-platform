---
name: generate-docs
description: Generate HLD, LLD, ADR, system manifest, and CLAUDE.md for a new feature (forward design) or existing codebase (brownfield reverse-engineer). Use before implementation starts on any Tier 2+ change, or to bootstrap a documentation baseline for an existing repo. Creates files — do not invoke spontaneously.
argument-hint: "[feature name] | [reverse-engineer]"
disable-model-invocation: true
---

# Generate Design Documentation

## Project Context

This skill generates design documentation for any project. It supports two modes:

1. **New feature mode** — design docs for a feature that doesn't exist yet (forward-looking)
2. **Reverse-engineer mode** — design docs from an existing codebase (brownfield baseline sprint)

The user's input is: **$ARGUMENTS**

If `$ARGUMENTS` is empty, ask the user:
- "What would you like to document?"
- "Is this a **new feature** (design before code) or **existing code** (reverse-engineer into docs)?"

---

## Mode Detection

If the user says any of: "reverse engineer", "existing", "brownfield", "baseline", "document the current system", "generate from code" → use **Reverse-Engineer Mode** (Phase R below).

Otherwise → use **New Feature Mode** (Phase 1-2 below).

---

## New Feature Mode

### Phase 1 — High-Level Design (HLD)

1. **Determine the feature name** from the user's description. Use kebab-case (e.g., `campaign-scheduler`).

2. **Create `docs/02-design/technical/hld/<feature-name>.md`** using the template at `templates/hld-template.md`. The document must contain:
   - Executive summary
   - System architecture diagram (Mermaid `graph TB`)
   - Component overview table with responsibilities
   - Data flow diagrams (Mermaid `sequenceDiagram`)
   - Integration points with external systems
   - Security architecture
   - Scalability considerations
   - All diagrams must use Mermaid — no `<br/>` tags inside Mermaid blocks (Obsidian compatibility)

3. **Update `docs/02-design/technical/hld/index.md`** — add a row linking to the new HLD.

4. **STOP and ask the user to review and approve the HLD** before proceeding to Phase 2.

### Phase 2 — Low-Level Design (LLD)

Only proceed after HLD approval.

1. **Identify the components** from the approved HLD. Group into categories:
   - `controllers/` — API endpoints
   - `services/` — Business logic
   - `models/` — Data structures
   - `security/` — Auth, guards
   - `config/` — Configuration

2. **For each component**, create `docs/02-design/technical/lld/<category>/<component-name>.md` using `templates/lld-component-template.md`. Each file must include:
   - Overview + purpose
   - Mermaid class diagram
   - Method signatures with parameters, return types, descriptions
   - Mermaid sequence diagrams for complex flows
   - Usage examples
   - Links to related components

3. **Update `docs/02-design/technical/lld/index.md`** and **`packages.md`**.

4. **STOP and ask the user to approve the LLD.**

---

## Reverse-Engineer Mode — Brownfield Baseline Sprint

This mode reads the existing codebase and generates the full documentation baseline. It follows the one-week sprint structure from the HITL process but can be run in a single session.

### Phase R1 — System Manifest (Day 1 equivalent)

1. **Scan the codebase** to identify:
   - Directory structure → domain boundaries
   - Import graph → dependencies between domains
   - Public classes + method signatures → facade APIs
   - Decorators + base classes → convention patterns
   - Test files → test coverage map

2. **Generate `docs/system-manifest.yaml`** with ALL sections from `skills/generate-docs/templates/system-manifest.schema.yaml`:

   **Per domain:**
   - `purpose`: one-line description (infer from directory name + file contents)
   - `files`: all source files in the domain (auto from directory scan)
   - `lld`: path to LLD doc (will be created in Phase R3)
   - `tests`: test files that cover this domain (match by name convention)
   - `boundary_entities`: extract public dataclasses / Pydantic models / TypedDicts that are imported by OTHER domains. Include the field-level shape. Mark as "DRAFT".
   - `facade_apis`: for each public method/endpoint that other domains call, generate:
     - `signature`: actual method signature from code
     - `blurb`: "DRAFT — [one sentence inferred from docstring or method name]"
     - `mutations`: detect writes (DB inserts/updates, external API calls, file writes). Mark IRREVERSIBLE for external calls. Mark as "DRAFT — verify with architect".
     - `preconditions`: infer from parameter validation, guard clauses, decorators
     - `error_modes`: extract from try/except blocks, raise statements, HTTP status codes
   - `events_emitted`: detect patterns like event dispatching, callback invocations, webhook sends. If none found, leave empty.
   - `events_consumed`: detect event handler registrations, webhook receivers, message queue consumers.
   - `depends_on`: from import graph
   - `conventions`: which cross-cutting conventions apply (detected in step 1)
   - `last_changed`: from git log (`git log -1 --format="%ai" -- <domain-dir>`)

   **Cross-cutting section:**
   - Detect repeating patterns across 3+ files → candidate conventions
   - For each: `name`, `rule` (specific + enforceable), `affected_domains`, `enforcement` (how to check: decorator? base class? import? pattern?), `adr` (will link to ADR in Phase R4)

   **Interaction matrix:**
   - For each import that crosses a domain boundary: `"domain_a -> domain_b"` with `description` (inferred from the import context) and `entity_crossing` (the class/type being imported)

3. **Present the manifest to the user for review.** Ask:
   - "Are these domain boundaries correct?"
   - "Any domains that should be merged or split?"
   - "Any conventions I missed?"

4. **Revise based on feedback.** The manifest is the foundation — getting domain boundaries right here prevents cascading errors in HLDs/LLDs.

### Phase R2 — HLDs (Days 2-3 equivalent)

1. **For each major system area**, generate an HLD using `templates/hld-template.md`:
   - Read the actual source code for that area
   - Extract the architecture from what EXISTS, not what should exist
   - Use real class names, real endpoints, real data flows
   - Mark anything uncertain as "INFERRED — needs verification"

2. Typical HLDs to generate:
   - System architecture (overall component topology)
   - Data architecture (models, relationships, storage)
   - API architecture (endpoints, auth flow)
   - Any domain-specific architecture (agents, pipelines, etc.)

3. **Update `docs/02-design/technical/hld/index.md`** with all new HLDs.

4. **STOP and ask the user to review the HLDs.** These don't need to be perfect — approximately 70% accurate is the target (observed in initial projects; accuracy improves as conventions are documented). The user corrects the remainder.

### Phase R3 — LLDs (Days 3-4 equivalent)

1. **For each domain in the manifest**, generate LLDs using `templates/lld-component-template.md`:
   - Read the actual source files listed in the manifest's domain entry
   - Extract real class hierarchies, method signatures, dependencies
   - Generate class diagrams from the actual code (via AST analysis)
   - Generate sequence diagrams for the key flows

2. **Prioritize hot domains** (the ones with the most recent git commits or the most files). Mark cold domains as "DRAFT — not reviewed" if time is limited.

3. **Update `docs/02-design/technical/lld/index.md`** — add a navigation table with one row per LLD, organized by domain.

4. **Generate `docs/02-design/technical/lld/packages.md`** — a Mermaid `graph TD` showing the domain dependency structure with subgraphs for each domain's key components. Use the interaction matrix from the manifest to draw edges.

5. **STOP and ask the user to review the LLDs.**

### Phase R4 — ADRs (Days 4-5 equivalent)

1. **Detect implicit decisions** from the code:
   - Framework choices (from dependencies/imports)
   - Architectural patterns (from class hierarchies, decorators)
   - Data storage choices (from model definitions, configs)
   - Authentication/authorization approach (from middleware/guards)
   - Error handling patterns (from try/catch patterns, error classes)

2. **For each detected decision**, generate a forensic ADR using `templates/adr-template.md`:
   - Context: "Based on the code, this system uses [X]"
   - Decision: "The decision appears to be [Y]"
   - Rationale: "The likely rationale is [Z]"
   - Mark as "INFERRED — NEEDS VERIFICATION" in the status field
   - The architect fills in the actual rationale during review

3. **Ask the user** for any decisions they remember that aren't visible in the code:
   - "Why was [framework] chosen over alternatives?"
   - "Why does [module] use [pattern] instead of [alternative]?"
   - "Are there any decisions that aren't reflected in the code?"

4. **Update `docs/02-design/technical/adrs/README.md`** with all new ADRs.

### Phase R5 — Process Setup (Day 5 equivalent)

1. **Generate `CLAUDE.md`** from the template at `templates/CLAUDE.md.template`:
   - Fill in the cross-cutting conventions discovered in Phase R1 (inline, not just links)
   - Fill in the coding standards detected from the codebase:
     - Language + framework (from imports / package.json / pyproject.toml)
     - Formatter (detect black, prettier, etc. from config files)
     - Linter (detect ruff, eslint, etc.)
     - Test framework (detect pytest, jest, etc.)
     - Type checker (detect mypy, tsc, etc.)
   - Include the 7-line preflight check (verbatim from template)
   - Reference the system manifest

2. **Generate `convention-checks.yaml`** with project-specific checks:
   - For each convention detected in Phase R1, create a check definition using the appropriate check type:
     - Subclass pattern → `subclass_method_check`
     - Required import pattern → `import_check`
     - Required co-occurrence → `pattern_check`
     - File content requirement → `file_contains`
   - Include all universal checks: `manifest_drift`, `mermaid_br_tags`, `inline_comments`

3. **Install the plugin** (preferred) or copy skills to `.claude/skills/` if they don't exist:
   - Install: add this repo as a Claude Code plugin so skills are auto-discovered
   - Manual copy: `cp -r skills/ <your-repo>/.claude/skills/`
   - Key skills: `skills/dev-practices/SKILL.md` — the 30-step workflow; `skills/apply-change/SKILL.md` — impact analysis

4. **Copy CI actions** to `.github/workflows/` if they don't exist:
   - `convention-check.yml` — runs convention checker, manifest drift detection, and Mermaid checks on every PR

5. **Generate `.github/ISSUE_TEMPLATE/technical-change.md`** from `templates/issue-template.md`:
   - Pre-filled with the ROI estimation section
   - Includes downstream impact brief prompts
   - Includes training plan link placeholder

6. **Set up Obsidian compatibility** (if docs/ exists):
   - Create `docs/.obsidian/app.json` with `useMarkdownLinks: true`, `newLinkFormat: "relative"`
   - Add `.obsidian/` and `docs/.obsidian/` to `.gitignore`

7. **Identify training plan candidates** — scan the codebase for capabilities that would benefit from a training plan:
   - Any custom framework or abstraction used across 3+ files
   - Any external system integration (API clients, SDKs)
   - Any architectural pattern that deviates from the framework default
   - For each candidate, create a stub at `docs/03-engineering/training/<name>.md` using `templates/training-plan-template.md` with module outlines and reading lists pointing to the just-generated LLDs

8. **Generate the docs README** — `docs/README.md` with:
   - A table of contents linking to all HLDs, LLDs, ADRs, training plans
   - The arc42-style directory structure explanation
   - Quick links to the system manifest and CLAUDE.md

9. **Present a completeness summary** to the user:

   ```
   ┌─────────────────────────────────────────────┐
   │ BASELINE GENERATION COMPLETE                │
   ├─────────────────────────────────────────────┤
   │ System manifest:  1 file, N domains         │
   │ HLDs:             X files                   │
   │ LLDs:             Y files                   │
   │ ADRs:             Z files (W forensic)       │
   │ Training plans:   T stubs                   │
   │ CLAUDE.md:        1 file, N conventions     │
   │ Convention checks: 1 config, M checks       │
   │ CI actions:       2 workflows               │
   │ Issue template:   1 file                    │
   ├─────────────────────────────────────────────┤
   │ NEEDS HUMAN REVIEW:                         │
   │ • Manifest facade blurbs (DRAFT): N items   │
   │ • Manifest mutations (DRAFT): N items       │
   │ • Manifest boundary entities: N items       │
   │ • Forensic ADRs (INFERRED): W items         │
   │ • Training plan stubs: T items              │
   ├─────────────────────────────────────────────┤
   │ RECOMMENDED NEXT STEPS:                     │
   │ 1. Review manifest domain boundaries        │
   │ 2. Fill in facade blurbs + mutations        │
   │ 3. Verify forensic ADRs with the team       │
   │ 4. Apply the process to one real change     │
   └─────────────────────────────────────────────┘
   ```

---

## Important Rules

- Use **Mermaid** for ALL diagrams — never ASCII art
- **No `<br/>` tags** inside Mermaid code blocks (breaks Obsidian rendering)
- Follow the templates for consistent formatting
- Do NOT generate implementation code — only documentation
- Each phase requires explicit user approval before proceeding
- In reverse-engineer mode, extract from ACTUAL code — do not invent or idealize
- Mark anything uncertain as "INFERRED — needs verification"
- The system manifest's human-authored fields (blurbs, mutations, preconditions) should be marked as "DRAFT" for the architect to fill in
- If a domain is too large to document fully, document the public interface and mark internals as "DRAFT"
