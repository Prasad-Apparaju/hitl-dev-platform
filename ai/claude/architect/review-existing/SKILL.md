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

9. **Observability as-built** — what structured logging library is in use and what format (JSON, plain text)? Are metrics emitted (Prometheus, Datadog, CloudWatch)? Is there distributed tracing (OpenTelemetry, Datadog APM, Jaeger)? Error tracking (Sentry, Rollbar)? Are dashboards and alert rules defined in the repo? Is there a documented on-call routing structure?

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

### 4a — Review baseline ADR stubs first

Before creating any new ADRs, check what the plugin has already provided:

```bash
ls docs/02-design/technical/adrs/adr-000*.md 2>/dev/null
```

**Expected baseline stubs (created by `/hitl:dev-start-brownfield` Step 0):**

| File | Status | What to do |
|---|---|---|
| `adr-0001-hitl-adoption.md` | Pre-filled | Confirm the project start date is correct |
| `adr-0002-documentation-first.md` | Pre-filled | Confirm it applies as-is |
| `adr-0003-test-strategy.md` | **Stub — needs architect input** | Fill in the test framework, coverage threshold, and any exceptions for this project |
| `adr-0004-change-tier-policy.md` | **Stub — needs architect input** | Confirm or adjust the default tier thresholds for this project's risk profile |
| `adr-0005-observability-strategy.md` | **Stub — needs architect input** | Fill in the observability stack found in Phase 1b and Decision 9: logging, metrics, tracing, error tracking, alerting, on-call routing, token cost registry |

If any of these files are missing, copy them now from the plugin:
```bash
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
mkdir -p docs/02-design/technical/adrs
for f in "$PLUGIN_ROOT/shared/templates"/adr-000*.md; do
  dest="docs/02-design/technical/adrs/$(basename "$f")"
  [[ -f "$dest" ]] || cp "$f" "$dest"
done
```

Ask the architect to fill in ADR-0003, ADR-0004, and ADR-0005 now. ADR-0003 and ADR-0004 gate the first Tier 2 change. ADR-0005 gates the first Tier 2 production deploy (required by `/hitl:ops-setup-observability`). Do not proceed to Phase 5 without all three accepted.

### 4b — Create ADRs for decisions from Phase 3

For each decision that was deliberate, has significant constraints, or would surprise a new team member — create a real ADR in `docs/02-design/technical/adrs/`.

Use the next available number after the baseline stubs (start from ADR-0005 unless higher-numbered ADRs already exist).

**ADR format** (follow the same structure as `adr-0001-hitl-adoption.md` — confirmed present from 4a above — use it as the reference for section headings and the ROI Estimate block):

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

### 4c — Generate deployment view HLD

Using the infrastructure files already read in Phase 1b (Dockerfile, docker-compose.yml, k8s/, terraform/, serverless.yml, CI/CD configs) and the deployment decision confirmed in Phase 3, generate `docs/02-design/technical/hld/deployment-view.md`.

**If no infrastructure files were found in Phase 1b** (no Dockerfile, no k8s/, no terraform/, no CI/CD config): skip this step and flag it in Phase 5 as a 🟡 concern: "Deployment not captured in IaC or config — deployment view cannot be generated."

**Otherwise**, create the file with this structure (fill in from the actual manifests — do not leave template placeholders):

```markdown
# Deployment View

> Generated from IaC and deployment config during brownfield onboarding.
> Update this document when infrastructure changes.

## Summary

[One paragraph: cloud provider, orchestration layer, key deployment technology — e.g. "Deployed as Docker containers orchestrated by Kubernetes on GKE. Infrastructure managed with Terraform. CI/CD via GitHub Actions."]

## Environments

| Environment | URL / endpoint | Notable differences from production |
|---|---|---|
| Production | [from IaC/config] | — |
| Staging | [from IaC/config] | [e.g., single replica, smaller DB tier] |
| Development | local / docker-compose | [e.g., no TLS, mock external services] |

Fill each row from what the IaC and CI/CD config actually say — leave a cell blank only when the information is genuinely absent from the files.

## Infrastructure Diagram

<!-- Node labels must be single-line. Quote labels containing (), -, or /. No <br/> tags. -->
\`\`\`mermaid
graph TB
  subgraph prod["Production"]
    ing["Ingress / Load Balancer"] --> api["API Service"]
    api --> db[("Database")]
    api --> cache[("Cache")]
  end
  ext["External Services"] --> api
\`\`\`

Replace the template nodes above with actual services and components from k8s/ or terraform/. Include: ingress/load balancer, application services, databases, caches, queues. Group by environment where relevant.

## Services and Containers

| Service | Image / runtime | Port | Replicas | Purpose |
|---|---|---|---|---|
| [from Dockerfile or k8s Deployment manifests] | | | | |

## External Dependencies

| Service | Type | Used for |
|---|---|---|
| [third-party APIs, managed cloud services, identity providers — from env examples and connection configs] | | |

## CI/CD Pipeline

<!-- Node labels must be single-line. No <br/> tags. -->
\`\`\`mermaid
flowchart LR
  commit["Git commit"] --> ci["CI: test + build"]
  ci --> staging["Deploy staging"]
  staging --> gate{"Manual gate?"}
  gate -- yes --> approval["Approval"]
  gate -- no --> prod["Deploy production"]
  approval --> prod
\`\`\`

Replace this template with the actual pipeline steps from the CI/CD config files.

## Gaps and Notes

- [Infrastructure not yet captured in IaC]
- [Environments referenced in code but absent from config]
- [Anything the architect clarified verbally in Phase 3 that does not appear in files]
```

After saving the file:
- Update `docs/02-design/technical/hld/index.md` — add a row for the deployment view. If the index file does not exist, create it:
  ```markdown
  # HLD Index

  | Document | Scope | Status | Date |
  |---|---|---|---|
  | [Deployment View](deployment-view.md) | System-wide | Baseline | [today's ISO date] |
  ```
- Validate: run `grep -n '<br' docs/02-design/technical/hld/deployment-view.md` — output must be empty.

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

**Deployment view:** [path to deployment-view.md if generated, or "skipped — no IaC files found"]

**Key constraints for the team:**
[2–4 bullet points — the most important things every developer must know before starting a change]

**Before your first Tier 2 change:**
[List any 🔴 concerns that need resolution — e.g., "Complete ADR-0003 (test strategy) — the coverage gate cannot be enforced until the test framework is chosen"]

**Ready for:** Step 7 of `/hitl:dev-start-brownfield` — identifying priority components for incremental documentation.

---

## Never

- Do not fabricate ADR rationale — if the architect doesn't know why a decision was made, record "rationale not documented" and mark it for future review
- Do not skip Phase 3 — real ADRs require human confirmation of intent, not just code inference
- Do not create ADRs for framework defaults that no one decided — that creates noise
- Do not proceed to Phase 4 without architect confirmation of the Phase 2 findings
