---
name: start
description: Entry point for the HITL platform. Run this first, or any time you are unsure what to do next. Detects project state and guides you through new project setup or brownfield onboarding.
---

# HITL — Get Started

You are the entry point for the HITL platform. Follow these steps exactly.

---

## Step 1 — Silently assess project state

Before saying anything, check:

1. Does `CLAUDE.md` contain real content or still have template placeholders (`{{coding_standards}}`, `{{#conventions}}`)?
2. Does `docs/system-manifest.yaml` exist with real domain definitions, or is it missing / template-only?
3. Is there source code? Check for `src/`, `app/`, `lib/`, or files matching `*.py`, `*.ts`, `*.js`, `*.go`, `*.java`.
4. Are there any HLDs or LLDs in `docs/02-design/`?

Use these four signals to set a **recommended path** (A or B) before presenting the choice.

---

## Step 2 — Present the choice

Respond with exactly this structure (fill in the bracketed parts):

---
**Welcome to HITL AI-Driven Development.**

Here's what I found in this project:
[1–2 sentence summary: what exists and what's missing. Be specific — e.g. "CLAUDE.md has template placeholders. No source code yet." or "Source code exists in src/. No system manifest or design docs yet."]

**Which situation fits?**

**A — New project** — Starting from scratch or early stage with minimal code.
→ Set up conventions, create the system manifest, and build docs-first from day one.
[Add "(recommended)" if no source code was found]

**B — Brownfield onboarding** — Existing codebase you want to bring into the HITL process.
→ Generate a documentation baseline from the existing code, then move to docs-first going forward.
[Add "(recommended)" if source code was found]

Type **A** or **B** to continue, or describe your situation and I'll route you.

---

---

## Path A — New Project Setup

Work through these steps in order. Pause after each and wait for the user to confirm before proceeding.

### A1. Customize CLAUDE.md

If `CLAUDE.md` has template placeholders:
- Ask: "What language and framework is this project? What test framework do you use? Any specific naming or formatting conventions?"
- Fill in `{{coding_standards}}` and `{{#conventions}}` based on their answers.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

### A2. Initialize the system manifest

If `docs/system-manifest.yaml` is missing or has template content:
- Ask: "What are the main domains or services in this project? For each, give a one-line description."
- Update `docs/system-manifest.yaml` with their answer. Map each domain to a plausible source path and note it as provisional.
- Say: "Manifest initialized. You'll refine domain boundaries as the system grows."

If a real manifest already exists, say: "Manifest found — skipping." and move on.

### A3. Create your first GitHub issue

- Ask: "What's the first feature you want to build?"
- Run: `gh issue create --title "[feature name]" --body "Initial feature for [project name]. Created via HITL onboarding."`
- Show the issue URL.

### A4. Confirm ready

Output this exactly:

---
**You're ready.**

Before writing any feature code, generate the design docs for your system:

```
/architect/design-system
```

This produces the system manifest, HLDs, and LLDs from your PRD. The 30-step workflow reads these docs at nearly every step — they must exist before feature work starts.

For every change after that:

1. Create a GitHub issue
2. Run `/dev-practices` — the 30-step workflow starts here
3. Design (HLD → LLD) before writing code
4. Code → tests → PR

Run `/architect/design-system` now if you have a PRD, or `/dev-practices` if you already have LLDs in place.

---

---

## Path B — Brownfield Onboarding

Work through these steps in order. Pause after each and wait for confirmation before proceeding.

### B1. Map the codebase

List the top-level directories and identify source code locations.
- Ask: "Are these the right source directories? Anything to exclude?"
- Confirm the language and framework.

### B2. Customize CLAUDE.md

Same as A1 above, tailored to the existing codebase's conventions.

### B3. Generate the system manifest baseline

If `docs/system-manifest.yaml` is missing or template-only:
- Run: `python tools/generate-manifest/generator.py --source [confirmed source dirs] --output docs/system-manifest.yaml`
- If the generator is unavailable, say so and ask: "Describe your main services and domains. I'll create the manifest manually."
- After generating, show the domain list and ask: "Review these domains. What should be added, removed, or renamed?"
- Incorporate their feedback and update the manifest.

If a real manifest already exists, read it, summarize the domains, and ask: "Is this manifest still accurate? Anything outdated?"

### B4. Identify priority components for documentation

Ask: "Which components are most critical and most likely to change in the near term? List up to three."

For each component:
- Say: "I'll generate an HLD and LLD for [component]. Run `/generate-docs` or I can do it now — which do you prefer?"
- If they want it now, run `/generate-docs` for that component.
- Note: This can be done incrementally. You don't need to document everything before starting work.

### B5. Seed the registries

The 30-step workflow queries two registries at multiple points. They need to exist before `/dev-practices` is run for the first time.

**Test registry** (`docs/03-engineering/testing/test-registry.yaml`):
- Ask: "Do you have existing tests? If so, I'll create a test registry stub from your test files."
- If yes: scan `tests/`, `spec/`, or equivalent; generate one entry per test file with `domain` and `path`. Leave `risk` and `covers` as DRAFT.
- If no: create an empty stub.

**Incident registry** (`docs/04-operations/incident-registry.yaml`):
- Ask: "What broke in production in the last 6 months? Describe each incident in one sentence."
- For each answer, add one entry to the incident registry with `description`, `domain` (best guess), and `date`.
- If they have nothing, create an empty stub. Say: "You can add entries later — after each production incident, run `/ops:log-incident`."

### B6. Create your first change issue

Ask: "What's the first change you want to make now that this project is onboarded?"
- Run: `gh issue create --title "[change description]" --body "First tracked change after HITL brownfield onboarding."`
- Show the issue URL.

### B7. Confirm ready

Output this exactly:

---
**Brownfield baseline established.**

You are starting incrementally: manifest and priority component docs exist, registries are seeded. Undocumented components will need their LLDs created when you first change them (`/generate-docs` for that component).

**What this means for your first changes:**
- Treat AI output from steps 5, 10, and 14 as drafts — the docs are new and may not yet reflect actual behavior. Increase human review scrutiny until the docs have been corrected through real use.
- If `/dev-practices` stops with "no LLD found" on an undocumented component, run `/generate-docs` for that component, then resume.

For every change going forward:

1. Create a GitHub issue
2. Run `/dev-practices` — the 30-step workflow starts here
3. Update HLD/LLD if the design changes
4. Code → tests → PR

Run `/dev-practices` now to start your first change, or ask me anything about the process.

---
