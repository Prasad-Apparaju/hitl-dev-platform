---
description: Design a new system from scratch starting from a PRD. Run once at project setup, after greenfield or migration onboarding completes and before any per-change work. Produces domain decomposition, system manifest, HLDs, ADRs, LLDs, and an initial delivery plan — demoable slices sequenced by dependency, each with a decision packet ready to hand to a developer. Run once at project inception.
argument-hint: "[path to PRD]"
disable-model-invocation: true
---

# Design System — Greenfield Architecture from PRD

**Input:** $ARGUMENTS (path to PRD, or description of where to find it)

**Refusal rule:** If no PRD path or content is provided, stop and say: "A PRD is required to start system design. Point me to `docs/01-product/prd.md` or provide the PRD content directly."

---

## Startup — Status Router

Before doing anything else, check `.hitl/design-system.yaml`:

```bash
[ -f .hitl/design-system.yaml ] && grep "^status:" .hitl/design-system.yaml || echo "status: not-found"
```

Route based on the current status:

| Status | Action |
|--------|--------|
| File not found | Initialize `.hitl/design-system.yaml` with `status: initializing`, then proceed from Phase 1 |
| `initializing` | Proceed from Phase 1 |
| `awaiting-requirements` | Output the gate-pending message and STOP |
| `requirements-confirmed` | Skip to Phase 2 (Domain Decomposition) |
| `awaiting-domains` | Output the gate-pending message and STOP |
| `domains-confirmed` | Skip to Phase 3 (System Manifest) |
| `awaiting-manifest` | Output the gate-pending message and STOP |
| `manifest-confirmed` | Skip to Phase 5 (HLDs) |
| `awaiting-hld-approval` | Output the gate-pending message and STOP |
| `hld-approved` | Skip to Phase 6 (LLDs) |
| `awaiting-lld-approval` | Output the gate-pending message and STOP |
| `lld-approved` | Skip to Phase 8 (Delivery Plan) |
| `awaiting-delivery-plan` | Output the gate-pending message and STOP |
| `complete` | Output: "System design is complete. Decision packets are ready — assign them to developers to begin `/hitl:dev-tdd`." and STOP |
| `blocked` | Output the blocked message and STOP |

**Gate-pending message** (for any `awaiting-*` status):
```
Gate pending — waiting for TA approval.

Status:   [current status]

The TA must run /hitl:ta-approve to review the current artifact and advance this gate.
Once approved, re-run this command to continue to the next phase.
```

**Blocked message** (for `blocked` status):
```
This system design is blocked — a gate was rejected by the TA.

Gate:     [blocker.gate]
Finding:  [blocker.finding]

Address the finding above, then re-run this command. The skill will resume
at the rejected phase so you can rework the artifact.
```

For `blocked` status: after showing the blocked message, ask: "Are you ready to rework the [blocker.gate] artifact? Say 'yes' to resume." On confirmation, clear the `blocked` status and route to the appropriate phase.

**`.hitl/design-system.yaml` initial content** (written when file not found):
```yaml
status: initializing
prd: "[path from $ARGUMENTS]"
```

Ensure the `.hitl/` directory exists: `mkdir -p .hitl`

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

Run through the full NFR checklist in `shared/challenge-stance.md` (Minimum NFR Checklist section). For each NFR that is absent or vague in the PRD, ask the architect or PM now.

**One rule for unresolvable NFRs:** Ask first. If the answer cannot be obtained (early-stage project, no stakeholder available), make a stated assumption with a specific number and record it as a design risk in the gate below — do not leave it unnamed. "We don't know yet" embedded silently in an architecture is far more dangerous than an explicit assumption the team can challenge and update.

### 1c. Gate — architect confirms requirements are complete

Present the extracted summary and gaps.

Update `.hitl/design-system.yaml`: set `status: awaiting-requirements`.

Output:
```
Gate 1 reached — status set to 'awaiting-requirements'.

The TA must run /hitl:ta-approve to confirm requirements before domain decomposition begins.
Re-run /hitl:architect-design-system after TA approval to continue.
```

**STOP. Do not propose a domain breakdown. This session ends here.**

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

Update `.hitl/design-system.yaml`: set `status: awaiting-domains`.

Output:
```
Gate 2 reached — status set to 'awaiting-domains'.

Domain boundaries are the hardest decision to change later.
The TA must run /hitl:ta-approve to confirm the domain decomposition before manifest generation begins.
Re-run /hitl:architect-design-system after TA approval to continue.
```

**STOP. Do not generate the system manifest. This session ends here.**

---

## Phase 3 — System Manifest

Generate `docs/system-manifest.yaml` from the confirmed domain breakdown. Follow the schema in `shared/templates/system-manifest.schema.yaml`.

For a greenfield system, apply these rules per domain:
- `files` and `tests`: empty arrays — no code exists yet
- `lld`: `"pending"` — updated in Phase 6
- All `facade_apis`, `boundary_entities`, and `events_*` fields: propose from PRD use cases and mark every value `DRAFT — architect to verify` — these are intended contracts, not ground truth
- `depends_on`: from the interaction matrix (Phase 2b)
- `conventions`: empty array — filled in after Phase 4 ADRs resolve

Cross-cutting section: propose conventions from tech stack decisions (if known), NFRs, and any organization-wide standards in the PRD. Mark all as DRAFT.

Interaction matrix: populate from Phase 2b.

**Important:** Every human-authored field (`facade_apis`, `boundary_entities`, `events_*`) must be marked `DRAFT — architect to verify`. These are proposals from the PRD, not ground truth. The architect fills in the real values as the first implementations run.

Update `.hitl/design-system.yaml`: set `status: awaiting-manifest`.

Output:
```
Gate 3 reached — status set to 'awaiting-manifest'.

System manifest and foundational ADRs are ready for TA review.
The TA must run /hitl:ta-approve to confirm before HLD generation begins.
Re-run /hitl:architect-design-system after TA approval to continue.
```

**STOP. Do not generate ADRs or HLDs yet. This session ends here.**

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

For each decision (decided or open), create `docs/02-design/technical/adrs/<decision-slug>.md` using `shared/templates/adr-template.md`.

For decisions already made: pre-fill `Status: Accepted`, `Decision` section, ask architect to fill in the `Rationale` (the why — what alternatives were considered and why this won).

For open decisions: fill `Status: Proposed`, list the options and their tradeoffs, leave `Decision` blank. **STOP on each open ADR and ask the architect to decide before continuing.** Architecture cannot proceed with unresolved ADRs on the list above.

Update `docs/02-design/technical/adrs/README.md` with all new ADRs.

Confirm with the architect: "Are all foundational ADRs accurate before I generate the HLDs? Say 'yes' to continue."

On confirmation, update `.hitl/design-system.yaml`: set `status: manifest-confirmed`. Then continue to Phase 5 in the same session.

---

## Phase 5 — System-Level HLDs

Generate the following HLDs using `shared/templates/hld-template.md`. Each must read from the confirmed manifest and ADRs — not from memory or general reasoning.

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

After all HLDs are written, update `.hitl/design-system.yaml`: set `status: awaiting-hld-approval`.

Output:
```
Gate 4 reached — status set to 'awaiting-hld-approval'.

All system HLDs are ready for TA review:
  [list each HLD path]

The TA must run /hitl:ta-approve to review the HLDs before LLD generation begins.
Re-run /hitl:architect-design-system after TA approval to continue.
```

**STOP. Do not generate LLDs. This session ends here.**

---

## Phase 6 — Domain-Level LLDs

For each domain in the confirmed manifest, generate a LLD at `docs/02-design/technical/lld/<domain>/<domain>.md` using `shared/templates/lld-component-template.md`.

For each LLD:
- Propose the internal structure (services, classes, data models) that would implement the domain's `facade_apis` and satisfy the use cases from Phase 1 that this domain owns
- Include: Mermaid class diagram, key method signatures with parameters and return types, sequence diagrams for the main flows, error modes, preconditions
- Mark everything as DRAFT — this is design intent, not implementation. The first implementation may reveal better designs; that is expected.
- Link back to the HLDs that govern this domain's place in the system

After each LLD, update:
- `docs/02-design/technical/lld/index.md`
- The domain's `lld` field in `docs/system-manifest.yaml`

After all domain LLDs, generate `docs/02-design/technical/lld/packages.md` — a Mermaid `graph TD` showing the domain dependency structure using the confirmed interaction matrix.

After all LLDs are written, update `.hitl/design-system.yaml`: set `status: awaiting-lld-approval`.

Output:
```
Gate 5 reached — status set to 'awaiting-lld-approval'.

All domain LLDs are ready for TA review:
  [list each LLD path]

The TA must run /hitl:ta-approve to review the LLDs before the delivery plan is assembled.
Re-run /hitl:architect-design-system after TA approval to continue.
```

**STOP. Do not begin the HITL process bootstrap or delivery plan. This session ends here.**

---

## Phase 7 — HITL Process Bootstrap

Follow the instructions in Phase R5 of the `generate-docs` skill exactly. This sets up the process infrastructure:

1. **Generate `CLAUDE.md`** from `shared/templates/CLAUDE.md.template` — inline the cross-cutting conventions from the ADRs and manifest
2. **Generate `convention-checks.yaml`** — create checks from the conventions established in Phase 4 ADRs
3. **Install the plugin or copy skills** — so `/architect/design-feature`, `/hitl:dev-tdd`, `/hitl:dev-generate-docs`, etc. are available
4. **Copy CI actions** to `.github/workflows/`
5. **Generate `.github/ISSUE_TEMPLATE/technical-change.md`** from `shared/templates/issue-template.md`
6. **Set up Graphify** — for systems with 4+ domains, the doc set produced by this session will exceed context window limits on future queries. Install before team onboarding (see `shared/graphify-setup.md` for full instructions):
   ```bash
   uv tool install graphifyy        # install once per machine
   graphify claude install          # register /graphify skill with Claude Code
   graphify .                       # build initial graph → graphify-out/graph.json
   graphify hook install            # auto-rebuild on every git commit
   ```
   Commit `graphify-out/` (excluding `manifest.json` and `cost.json`) so teammates get the graph on `git pull`. The PostToolUse hook in this project also rebuilds incrementally after doc writes during a session.
7. **Generate `docs/README.md`** — table of contents linking all HLDs, LLDs, ADRs, and the manifest

---

## Phase 8 — Initial Delivery Plan

The design is complete. Now translate it into an ordered set of work packets — one per slice — that developers can pick up and execute independently using the 31-step workflow.

### 8a. Decompose each domain into initial slices

For each domain in the approved manifest, propose the minimum set of implementation slices that builds the domain's foundational capability. A slice is a unit of work one developer can complete in 2–5 days that produces something observable.

For each proposed slice:

```
Slice:        <domain>-<N> (e.g. billing-1)
Domain:       <domain name> — one domain only
Delivers:     <what gets built in this slice>
Demo check:   What does the PM see at the end of this slice?
              Valid: user-visible feature or measurable outcome (record counts, latency, error rate)
              Invalid: "nothing visible yet" → extend or merge with an adjacent slice
Dependencies: which other slices must complete first (from interaction matrix)
```

**Rule:** If a slice cannot answer the demo check with something concrete, it is too narrow. Extend it forward to the next observable boundary or merge it with the slice that completes the visible outcome.

### 8b. Sequence the slices

Order all slices from all domains into a delivery sequence:

- Slices with no dependencies → parallel, earliest sprint
- Slices that depend on facade APIs from another domain → after that domain's foundational slice
- Slices that share mutable state or contracts → sequential, not parallel

Present as a table:

| Order | Slice ID | Domain | Delivers | Demo check | Parallel with |
|-------|----------|--------|----------|------------|---------------|
| 1 | domain-a-1 | | | | domain-b-1 |
| 1 | domain-b-1 | | | | domain-a-1 |
| 2 | domain-c-1 | | | | — |

### 8c. Gate — delivery plan review

Update `.hitl/design-system.yaml`: set `status: awaiting-delivery-plan`.

Output:
```
Gate 6 reached — status set to 'awaiting-delivery-plan'.

Delivery plan is ready for TA review: [N] slices across [M] domains.

The TA must run /hitl:ta-approve to confirm the delivery plan before decision packets are generated.
Re-run /hitl:architect-design-system after TA approval to continue.
```

**STOP. Do not generate decision packets. This session ends here.**

### 8d. Generate decision packets

After Gate 6 is approved, generate one decision packet per confirmed slice using the exact YAML schema and greenfield defaults documented in [decision-packet.md](decision-packet.md). That reference also covers issue/file naming, the `pm_mental_model` handoff signal, and the final `status: complete` update.

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
│ DELIVERY PLAN                                       │
│  Slices: N  |  Parallel tracks: N  |  Packets: N   │
├─────────────────────────────────────────────────────┤
│ NEXT STEPS                                          │
│  1. Fill in DRAFT fields in manifest and ADRs       │
│  2. Assign decision packets to developers           │
│     — each developer receives one packet and runs   │
│       the standard 31-step workflow from it         │
│  3. Run /hitl:dev-generate-docs reverse-engineer after the   │
│     first sprint to reconcile design vs. built      │
└─────────────────────────────────────────────────────┘
```

---

## Important Rules

- Open ADRs on the foundational decision list (tech stack, data storage, auth, API style, deployment model) must be resolved before HLDs are generated.
