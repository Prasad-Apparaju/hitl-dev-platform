---
description: Architect review of an existing codebase. Reads the system manifest and code to reconstruct what architectural decisions were already made, interviews the architect to confirm rationale and constraints, then documents them as real ADRs. Run during brownfield onboarding after the system manifest is generated and before incremental feature work begins.
argument-hint: "[optional: focus area or specific concern]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---

# Review Existing Architecture

Reconstructing the architectural decisions already baked into this codebase, documenting them as ADRs, and surfacing concerns before incremental feature work begins.

**Graphify pre-flight:**
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once and apply it throughout.

---

## Phase 1 — Read the landscape

**1a. Load the system manifest:**

Read `docs/system-manifest.yaml`. Summarize:
- Domains and their source paths
- Any declared API boundaries or inter-domain dependencies
- Any known gaps or placeholder entries

If no manifest exists, say: "System manifest not found. Run Step 3 of `/hitl:dev-start-brownfield` first to generate it, then re-run this skill."

**1b. Survey key technology indicators:**

Read the following files (whichever exist) to identify the technology stack:

| What to look for | Where to look |
|---|---|
| Language / runtime | `package.json`, `pom.xml`, `build.gradle`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Gemfile`, `*.csproj` |
| Web framework | Framework-specific config files, main entry point, routing files |
| Database | Migration files (`db/migrate/`, `alembic/`, `flyway/`, `liquibase/`), ORM config, connection strings in env examples |
| Auth approach | Auth middleware, `auth/`, `security/`, JWT/session config |
| API style | Route definitions — REST endpoints vs GraphQL schema vs gRPC `.proto` files |
| Deployment target | `Dockerfile`, `docker-compose.yml`, `k8s/`, `terraform/`, `serverless.yml`, `*.yaml` in `.github/workflows/` |
| Test framework | `jest.config.*`, `pytest.ini`, `spec/`, `__tests__/`, test runner in CI config |
| Key patterns | Event bus config, message queue, CQRS/event-sourcing markers, cache layer |

Use Graphify if available:
```
/graphify query "technology stack framework database auth deployment"
```

After reading, output a **Tech Stack Summary**:

```
Language/runtime:   [e.g., Java 21 / Spring Boot 3.2]
Database:           [e.g., PostgreSQL 15, Flyway migrations]
Auth:               [e.g., JWT, RS256, issued by internal auth service]
API style:          [e.g., REST, OpenAPI 3.1 spec in docs/api/]
Deployment:         [e.g., Docker → Kubernetes (GKE), Helm charts in k8s/]
Test framework:     [e.g., JUnit 5 + Mockito, Testcontainers for integration]
Notable patterns:   [e.g., Hexagonal architecture, domain events via Spring Events]
```

---

## Phase 2 — Extract architectural decisions

For each category below, read the relevant code and identify the concrete decision that was made. Do not infer intent — only record what exists.

**Decision categories:**

1. **Service architecture** — monolith, microservices, modular monolith? How are modules/services separated? Are domain boundaries clean or tangled?

2. **Data architecture** — relational vs document vs hybrid? ORM vs raw SQL? Single DB vs per-service? Shared DB across domains (a risk)?

3. **Auth and identity** — where does auth live? Centralized service or per-component? Token type and signing approach? Who issues tokens?

4. **API contract** — REST vs GraphQL vs gRPC vs event-driven? Is there a published contract (OpenAPI spec, Proto files)? Versioning approach?

5. **Cross-domain communication** — direct calls vs message queue vs event bus? Synchronous vs async? Are there circular dependencies?

6. **Deployment and infrastructure** — containerized? Orchestrated? Cloud provider? IaC tool? Is infra in this repo or a separate one?

7. **Test strategy as-built** — what test layers actually exist (unit/integration/E2E)? What coverage exists? What is conspicuously absent?

8. **Non-obvious patterns** — any patterns that deviate from the obvious approach for this stack (event sourcing, CQRS, strangler fig, saga, etc.)?

Present findings as a numbered decision list:

```
Decision 1 — Service architecture: [what exists]
Decision 2 — Data architecture: [what exists]
...
```

Then ask: "Does this match your understanding of the codebase? Any decisions I missed or got wrong?"

---

## Phase 3 — Interview the architect

For each decision identified in Phase 2, ask the following (group them — do not ask one at a time for every decision):

**Round 1 — Intent:**
> "For each of these decisions, was it:
> (a) a deliberate architectural choice, (b) inherited from a previous team or framework default, or (c) evolved over time without a formal decision?
> [list decisions]"

**Round 2 — Rationale (for deliberate choices only):**
> "For the deliberate decisions — what problem was each solving at the time? What alternatives were considered?"

**Round 3 — Constraints and regrets:**
> "Which of these decisions creates the most constraints on future changes? Are there any you would make differently today? Any that are actively causing pain?"

**Round 4 — Unknown decisions:**
> "Are there any significant architectural decisions I didn't surface that should be documented — things that would surprise a new team member or that every developer needs to know?"

Record answers alongside each decision.

---

## Phase 4 — Document as ADRs

For each decision that was deliberate, has significant constraints, or would surprise a new team member — create a real ADR in `docs/02-design/technical/adrs/`.

Use the next available number after the default stubs (start from ADR-0005 unless higher-numbered ADRs already exist).

**ADR format** (follow the same structure as `docs/02-design/technical/adrs/adr-0001-hitl-adoption.md` — use it as a reference for section headings and the ROI Estimate block):

| Field | What to fill in for brownfield ADRs |
|---|---|
| Status | `Accepted` if already in production; `Under review` if the team questions it |
| Date | Best estimate of when the decision was made — ask if unknown |
| Context | What was the situation that led to this choice? |
| Decision | What exactly was decided — specific, not vague |
| Alternatives considered | What was evaluated at the time (ask architect; OK to say "not documented" if unknown) |
| Consequences | What does this decision constrain or enable? |
| Open questions | Any active debate about whether this should change? |

**Prioritize ADRs for:**
- Decisions that constrain what developers can do (must-know before starting a change)
- Decisions with non-obvious rationale (would mislead a new developer)
- Decisions that are actively questioned by the team
- Decisions that affect HITL compliance (e.g., no integration tests = coverage gate needs adjustment)

**Skip ADRs for:**
- Framework defaults with no active decision made
- Decisions that are obvious from the code with no meaningful alternatives

After creating each ADR, confirm with the architect: "Does this accurately capture the decision and its rationale?"

---

## Phase 5 — Surface architectural concerns

Review the complete picture — system manifest, tech stack, decisions, ADRs — and identify concerns that the team should address before or during incremental HITL work.

Categorize each concern:

**🔴 Blocks or complicates HITL compliance:**
- No test layer → coverage gate in ADR-0003 needs adjustment before first Tier 2 change
- Shared database across domains → domain boundary checks will fire frequently; needs a decision about whether to enforce or loosen
- No API contract → LLD generation in `/hitl:architect-design-feature` cannot validate interface conformance

**🟡 Should be addressed within the first few changes:**
- Circular domain dependencies → map them; affected changes need extra cross-domain review
- Missing LLDs for high-churn components → run `/hitl:dev-generate-docs` before first change to each

**🟢 Worth noting but not blocking:**
- Tech debt areas where AI-generated code may drift from existing patterns
- Components where the as-built docs may not accurately reflect behavior (common in brownfield reverse-engineering)

Output the concern list and ask: "Any of these concerns a surprise? Any I missed?"

---

## Phase 6 — Produce the handoff summary

Output this exactly (fill in the blanks):

---

**Architecture review complete.**

**Decisions documented:**
[List each ADR created with its title and file path]

**Key constraints for the team:**
[2–4 bullet points — the most important things every developer must know before starting a change]

**Before your first Tier 2 change:**
[List any 🔴 concerns that need resolution — e.g., "Complete ADR-0003 (test strategy) — the coverage gate cannot be enforced until the test framework is chosen"]

**Ready for:** Step 5 of `/hitl:dev-start-brownfield` — identifying priority components for incremental documentation.

---

## Never

- Do not fabricate ADR rationale — if the architect doesn't know why a decision was made, record "rationale not documented" and mark it for future review
- Do not skip Phase 3 — real ADRs require human confirmation of intent, not just code inference
- Do not create ADRs for framework defaults that no one decided — that creates noise
- Do not proceed to Phase 4 without architect confirmation of the Phase 2 findings
