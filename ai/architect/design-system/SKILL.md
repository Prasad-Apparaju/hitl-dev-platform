---
name: architect/design-system
description: Design a new system from scratch starting from a PRD. Produces domain decomposition, system manifest, system-level HLDs, foundational ADRs, domain-level LLDs, and HITL process bootstrap. Run once at project inception. After this completes, use /architect/design-feature for individual changes.
argument-hint: "[path to PRD]"
disable-model-invocation: true
---

# Design System — Greenfield Architecture from PRD

**Input:** $ARGUMENTS (path to PRD, or description of where to find it)

**Refusal rule:** If no PRD path or content is provided, stop and say: "A PRD is required to start system design. Point me to `docs/01-product/prd.md` or provide the PRD content directly."

---

## Phase 1 — PRD Analysis

### 1a. Read the PRD

Read the document at the path in $ARGUMENTS. If none given, check `docs/01-product/prd.md`.

Extract and summarize:

| Category | Extracted content |
|----------|-------------------|
| System name and purpose | |
| User personas and their primary goals | |
| Core use cases (the 3–5 workflows that matter most) | |
| Functional requirements (must-have vs nice-to-have) | |
| Non-functional requirements (performance, scale, availability, security, compliance) | |
| External integrations (systems this will call or be called by) | |
| Tech stack constraints (anything pre-decided by the organization) | |
| Explicit out-of-scope items | |
| Open questions | |

### 1b. Identify PRD gaps and interrogate NFRs

**Do not proceed past this step with any unanswered item.** Missing NFRs at design time become architecture mistakes at build time.

#### Structural gaps — ask if absent or ambiguous

- Who owns what data? Is data ownership unambiguous for each capability area?
- Which workflows cross multiple capability areas? (matters for domain boundary decisions)
- Where must operations succeed or fail together? (consistency requirements)
- Any open questions that affect architecture, not product detail?

#### NFR interrogation — mandatory if absent or vague in the PRD

Run through the full NFR checklist in `ai/shared/challenge-stance.md` (Minimum NFR Checklist section). For each NFR that is absent or vague in the PRD, ask the architect or PM now.

**One rule for unresolvable NFRs:** Ask first. If the answer cannot be obtained (early-stage project, no stakeholder available), make a stated assumption with a specific number and record it as a design risk in the gate below — do not leave it unnamed. "We don't know yet" embedded silently in an architecture is far more dangerous than an explicit assumption the team can challenge and update.

### 1c. Gate — architect confirms requirements are complete

Present the extracted summary and gaps.

**STOP:**
> "Here is what I've extracted from the PRD. Before I propose a domain breakdown, please confirm:
> 1. Are the core use cases correct and complete?
> 2. Are there NFRs I missed that will affect the architecture?
> 3. Are the external integrations listed complete?
> 4. Is the tech stack already decided, or is that an open decision?
>
> Say **"requirements confirmed"** to proceed to domain decomposition."

---

## Phase 2 — Domain Decomposition

This is the most consequential decision in the session. Domain boundary errors cascade through every subsequent artifact. Take the time to get this right.

### 2a. Propose candidate domains

From the PRD use cases and functional requirements, identify candidate domains using these heuristics:

- **Group by business capability**, not technical layer. "Billing" is a domain; "database" is not.
- **Separate by rate of change.** Capabilities that evolve independently belong in separate domains.
- **Separate by data ownership.** Each domain should own its data and be the authoritative source for it.
- **Respect transaction boundaries.** If two operations must succeed or fail together, keep them in the same domain. Avoid distributed transactions between domains.
- **Identify the core domain.** Which capability is the primary competitive differentiator? It deserves the most careful design. Supporting and generic capabilities can be simpler.

For each candidate domain, specify:
```
Domain: <name>
Purpose: <one sentence>
Owns: <what data/state this domain is the authority for>
Key responsibilities: <3-5 bullet points from the PRD>
Does NOT own: <explicit exclusions to prevent creep>
```

### 2b. Map the interaction structure

For each pair of domains that must exchange data:
- What data crosses the boundary? (the boundary entity)
- Which direction does the call go?
- Is the interaction synchronous (request/response) or asynchronous (event)?
- How often? (per request vs. background vs. scheduled)

Draw the interaction matrix:
```
domain_a → domain_b: [what crosses, why, sync/async]
```

Flag any circular dependencies — they indicate a boundary is in the wrong place.

### 2c. Challenge the decomposition

Before presenting to the architect, challenge it yourself:

- Is any domain doing too many unrelated things? (should be split)
- Are two domains always deployed or changed together? (may belong together)
- Does any interaction require tight coupling (shared mutable state, synchronous chains of 3+)? (boundary may be wrong)
- Is there a domain with no facade APIs that other domains call? (may not be a domain — may be a library)
- Would a single developer be able to implement one of these domains without understanding the internals of the others? (if no, boundary is leaking)

### 2d. Gate — architect confirms domain breakdown

Present the proposed domains and interaction map.

**STOP:**
> "Here is my proposed domain breakdown. Domain boundaries are the hardest decision to change later — please review carefully:
>
> [present domain list and interaction matrix]
>
> Specifically:
> 1. Is each domain's data ownership clear and non-overlapping?
> 2. Are there any circular dependencies I should resolve differently?
> 3. Any domains that should be merged (too small / always change together)?
> 4. Any domains that should be split (too many responsibilities)?
>
> Say **"domains confirmed"** to generate the system manifest."

Do not proceed until the architect explicitly confirms. If the architect requests changes, revise and re-present before continuing.

---

## Phase 3 — System Manifest

Generate `docs/system-manifest.yaml` from the confirmed domain breakdown. Follow the schema in `ai/generate-docs/templates/system-manifest.schema.yaml`.

For each domain:

```yaml
<domain-name>:
  purpose: "<confirmed one-line description>"
  files: []                        # empty — no code exists yet
  lld: "pending"                   # updated in Phase 6
  tests: []                        # empty — no tests yet
  boundary_entities:
    <EntityName>:                  # data types that cross domain boundaries
      shape: |                     # propose field shapes from PRD use cases
        # DRAFT — architect to verify
        field_name: type
      consumed_by: [<domain>, ...]
      note: "DRAFT — shape inferred from PRD; verify before first implementation"
  facade_apis:
    <method_name>:                 # propose from PRD requirements
      signature: "DRAFT: <proposed_signature>"
      blurb: "DRAFT — <inferred from PRD>"
      mutations: ["DRAFT — verify"]
      preconditions: ["DRAFT — verify"]
      error_modes: ["DRAFT — verify"]
  depends_on: [<domain>, ...]      # from interaction matrix
  events_emitted: []               # architect fills in if event-driven
  events_consumed: []
  conventions: []                  # filled in after Phase 4 ADRs
```

Cross-cutting section: propose conventions based on tech stack decisions (if known), NFRs, and any organization-wide standards mentioned in the PRD. Mark all as DRAFT.

Interaction matrix: populate from Phase 2b.

**Important:** Every human-authored field (`facade_apis`, `boundary_entities`, `events_*`) must be marked `DRAFT — architect to verify`. These are proposals from the PRD, not ground truth. The architect fills in the real values as the first implementations run.

**STOP:**
> "System manifest draft is ready. The facade APIs and boundary entities are proposals — they are the intended public contracts, not final ones. Please review:
> 1. Are the boundary entities the right shapes?
> 2. Are the facade API signatures approximately right?
> 3. Are the domain dependencies correct?
>
> Say **"manifest approved"** to proceed to ADRs."

---

## Phase 4 — Foundational ADRs

### 4a. Identify required decisions

From the PRD, the confirmed domains, and any tech stack constraints already known, identify every major architectural decision that must be made before the first line of code:

| Decision area | Options | Must decide now? |
|---|---|---|
| Primary language and framework | | Yes — affects conventions, LLDs |
| Data storage (type and product) | | Yes — affects domain schemas |
| Authentication and authorization approach | | Yes — cross-cutting, affects every domain |
| API style (REST / GraphQL / gRPC / events) | | Yes — affects facade API shapes |
| Deployment model (monolith / services / serverless) | | Yes — affects domain boundaries |
| Observability stack (logging, tracing, metrics) | | Yes — affects cross-cutting conventions |
| Data consistency model (sync / eventual) | | Yes if multi-domain writes exist |

Ask the architect: "Which of these are already decided by your organization? Which are open decisions that we should work through now?"

### 4b. Create ADR stubs

For each decision (decided or open), create `docs/02-design/technical/adrs/<decision-slug>.md` using `ai/templates/adr-template.md`.

For decisions already made: pre-fill `Status: Accepted`, `Decision` section, ask architect to fill in the `Rationale` (the why — what alternatives were considered and why this won).

For open decisions: fill `Status: Proposed`, list the options and their tradeoffs, leave `Decision` blank. **STOP on each open ADR and ask the architect to decide before continuing.** Architecture cannot proceed with unresolved ADRs on the list above.

Update `docs/02-design/technical/adrs/README.md` with all new ADRs.

**STOP after all foundational ADRs:**
> "Foundational ADRs are in place. Open decisions are resolved. Please confirm the ADRs accurately reflect the decisions made before I generate the HLDs."

---

## Phase 5 — System-Level HLDs

Generate the following HLDs using `ai/templates/hld-template.md`. Each must read from the confirmed manifest and ADRs — not from memory or general reasoning.

**Always generate:**

1. **System architecture** (`docs/02-design/technical/hld/system-architecture.md`)
   - Overall component topology and deployment model (from ADR)
   - Domain map as Mermaid `graph LR` or `graph TD`
   - External integration points (every external system named)
   - Data flows across domain boundaries (from interaction matrix)
   - Sequence diagrams for the 2–3 most critical use cases from Phase 1

2. **Data architecture** (`docs/02-design/technical/hld/data-architecture.md`)
   - Storage technology choices (from ADRs)
   - Data ownership map — which domain owns which tables/collections
   - Cross-domain data access patterns
   - Migration and backup strategy at high level
   - Data retention and compliance requirements from NFRs

3. **Security architecture** (`docs/02-design/technical/hld/security-architecture.md`)
   - Authentication and authorization approach (from ADR)
   - Data isolation between tenants or users (if applicable from PRD)
   - Secrets management approach
   - Network security model (what is public, what is internal)
   - Compliance requirements from PRD NFRs

**Generate if applicable:**

4. **API architecture** (`docs/02-design/technical/hld/api-architecture.md`) — if the system has an external-facing API
   - API style (from ADR)
   - Endpoint surface overview — one row per domain's external API
   - Auth flow sequence diagram
   - Versioning and backwards compatibility approach

5. **Observability architecture** (`docs/02-design/technical/hld/observability-architecture.md`) — if NFRs specify SLA, availability, or incident response requirements
   - Logging structure (format, levels, what to always include)
   - Distributed tracing approach
   - Key metrics per domain
   - Alerting thresholds from NFRs

Update `docs/02-design/technical/hld/index.md` after all HLDs.

**STOP after each HLD:**
> "HLD: [name] is ready for review. Check:
> 1. Does this match the decisions in the ADRs?
> 2. Are the diagrams accurate?
> 3. Any architectural concerns at this level?
>
> Say **"[name] HLD approved"** to continue."

Do not generate LLDs until all HLDs are approved.

---

## Phase 6 — Domain-Level LLDs

For each domain in the confirmed manifest, generate a LLD at `docs/02-design/technical/lld/<domain>/<domain>.md` using `ai/templates/lld-component-template.md`.

For each LLD:
- Propose the internal structure (services, classes, data models) that would implement the domain's `facade_apis` and satisfy the use cases from Phase 1 that this domain owns
- Include: Mermaid class diagram, key method signatures with parameters and return types, sequence diagrams for the main flows, error modes, preconditions
- Mark everything as DRAFT — this is design intent, not implementation. The first implementation may reveal better designs; that is expected.
- Link back to the HLDs that govern this domain's place in the system

After each LLD, update:
- `docs/02-design/technical/lld/index.md`
- The domain's `lld` field in `docs/system-manifest.yaml`

After all domain LLDs, generate `docs/02-design/technical/lld/packages.md` — a Mermaid `graph TD` showing the domain dependency structure using the confirmed interaction matrix.

**STOP after each LLD:**
> "LLD for [domain] is ready. Check:
> 1. Are the method signatures precise enough that a developer could generate tests directly from this?
> 2. Do the facade APIs match what's in the manifest?
> 3. Are the error modes and preconditions complete?
>
> Say **"[domain] LLD approved"** to continue."

---

## Phase 7 — HITL Process Bootstrap

Follow the instructions in Phase R5 of the `generate-docs` skill exactly. This sets up the process infrastructure:

1. **Generate `CLAUDE.md`** from `ai/templates/CLAUDE.md.template` — inline the cross-cutting conventions from the ADRs and manifest
2. **Generate `convention-checks.yaml`** — create checks from the conventions established in Phase 4 ADRs
3. **Install the plugin or copy skills** — so `/architect/design-feature`, `/tdd`, `/generate-docs`, etc. are available
4. **Copy CI actions** to `.github/workflows/`
5. **Generate `.github/ISSUE_TEMPLATE/technical-change.md`** from `ai/templates/issue-template.md`
6. **Set up Graphify** — for systems with 4+ domains, the doc set produced by this session will likely exceed context window limits on future queries. Install before team onboarding:
   ```bash
   pip install graphifyy && graphify install
   graphify . --directed --no-viz
   python3 -m graphify.serve graphify-out/graph.json
   ```
   The PostToolUse hook rebuilds the graph incrementally as docs change.
7. **Generate `docs/README.md`** — table of contents linking all HLDs, LLDs, ADRs, and the manifest

---

## Output Summary

Present a completion summary:

```
┌─────────────────────────────────────────────────────┐
│ SYSTEM DESIGN COMPLETE — [System Name]              │
├─────────────────────────────────────────────────────┤
│ Domains: N  |  HLDs: N  |  LLDs: N  |  ADRs: N    │
├─────────────────────────────────────────────────────┤
│ ARTIFACTS                                           │
│  System manifest:  docs/system-manifest.yaml        │
│  HLDs:             docs/02-design/technical/hld/    │
│  LLDs:             docs/02-design/technical/lld/    │
│  ADRs:             docs/02-design/technical/adrs/   │
│  CLAUDE.md:        repo root                        │
│  Convention checks: convention-checks.yaml          │
│  CI:               .github/workflows/               │
│  Graphify:         [installed / not required]       │
├─────────────────────────────────────────────────────┤
│ NEEDS ARCHITECT ATTENTION BEFORE FIRST FEATURE      │
│  • Facade API blurbs (DRAFT): N fields              │
│  • Boundary entity shapes (DRAFT): N fields         │
│  • ADR rationale sections: N docs                   │
│  • LLD method signatures (DRAFT): N domains         │
├─────────────────────────────────────────────────────┤
│ NEXT STEPS                                          │
│  1. Fill in DRAFT fields in manifest and ADRs       │
│  2. Run /architect/design-feature for first change  │
│     — the first real implementation will correct    │
│     DRAFT fields and calibrate the design           │
│  3. Run /generate-docs reverse-engineer after the   │
│     first sprint to reconcile design vs. built      │
└─────────────────────────────────────────────────────┘
```

---

## Important Rules

- Open ADRs on the foundational decision list (tech stack, data storage, auth, API style, deployment model) must be resolved before HLDs are generated.
