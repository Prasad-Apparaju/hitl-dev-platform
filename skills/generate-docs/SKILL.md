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

2. **Generate `docs/system-manifest.yaml`** with:
   - One domain entry per identified boundary
   - File lists per domain (auto-generated)
   - Placeholder facade APIs (signature + "DRAFT — needs human review" blurb)
   - Dependency graph (from imports)
   - Convention detection (any patterns that repeat across 3+ files → candidate convention)

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

4. **STOP and ask the user to review the HLDs.** These don't need to be perfect — 70% accurate is the target. The user corrects the 30%.

### Phase R3 — LLDs (Days 3-4 equivalent)

1. **For each domain in the manifest**, generate LLDs using `templates/lld-component-template.md`:
   - Read the actual source files listed in the manifest's domain entry
   - Extract real class hierarchies, method signatures, dependencies
   - Generate class diagrams from the actual code (via AST analysis)
   - Generate sequence diagrams for the key flows

2. **Prioritize hot domains** (the ones with the most recent git commits or the most files). Mark cold domains as "DRAFT — not reviewed" if time is limited.

3. **Update `docs/02-design/technical/lld/index.md`** and **`packages.md`**.

4. **STOP and ask the user to review the LLDs.**

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
   - Fill in the cross-cutting conventions discovered in Phase R1
   - Fill in the coding standards detected from the codebase (formatter, linter, test framework)
   - Reference the system manifest

2. **Generate `convention-checks.yaml`** with project-specific checks based on the conventions discovered:
   - For each detected convention, create a check definition
   - Include all universal checks (manifest_drift, mermaid_br_tags, inline_comments)

3. **Copy the skills** to `.claude/commands/` if they don't exist:
   - `skills/dev-practices.md`
   - `workflows/apply-change.md`

4. **Present a summary** to the user:
   - "Generated X HLDs, Y LLDs, Z ADRs, 1 system manifest, 1 CLAUDE.md"
   - "Domain coverage: [list of domains]"
   - "Convention coverage: [list of detected conventions]"
   - "Items marked NEEDS VERIFICATION: [count]"
   - "Recommended next step: review the manifest domain boundaries, then the HLDs"

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
