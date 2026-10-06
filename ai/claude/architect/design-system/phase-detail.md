# Design phases — worked detail

Read from Phases 2 and 5 of `/hitl:architect-design-system`. The rule each phase turns on stays
in SKILL.md; this holds the decomposition heuristics, the domain record, the challenge list and
the outline of every HLD.

## Contents

- Phase 2a — decomposition heuristics and the domain record
- Phase 2c — the challenge list
- Phase 5 — the HLD set and what each contains

---

## Phase 2a — decomposition heuristics and the domain record

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

---

## Phase 2c — the challenge list

Before presenting to the architect, challenge it yourself:

- Is any domain doing too many unrelated things? (should be split)
- Are two domains always deployed or changed together? (may belong together)
- Does any interaction require tight coupling (shared mutable state, synchronous chains of 3+)? (boundary may be wrong)
- Is there a domain with no facade APIs that other domains call? (may not be a domain — may be a library)
- Would a single developer be able to implement one of these domains without understanding the internals of the others? (if no, boundary is leaking)

---

## Phase 5 — the HLD set and what each contains

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
