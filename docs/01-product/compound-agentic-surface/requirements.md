# Compound Agentic System Surface: Requirements

> **What** the surface must do, for **EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10)**
> (compound agentic system delivery surface). Status: **draft, v3.3 — round-10 findings addressed; pending Codex round-11**. Ships as
> **2.2.0** on the 2.x line (1.x is feature-frozen). Sub-issues:
> [#11–#20](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10).
>
> **Requirements (what) vs design (how).** This is the requirements layer: the product one-liner
> is **[FR-26](../prd.md)** in the PRD; this doc is its detailed requirements analysis (problem
> framing + the `CR-n` requirements). The **how** — topology model, validators, schema encoding —
> lives in the design package at
> [`docs/design/compound-agentic-surface/`](../../design/compound-agentic-surface/): HLD
> [`01-design.md`](../../design/compound-agentic-surface/01-design.md) **v3**, ADRs
> [`02-adrs.md`](../../design/compound-agentic-surface/02-adrs.md) (ADR-1..ADR-13, accepted), LLD
> [`03-lld.md`](../../design/compound-agentic-surface/03-lld.md) **v3.3** — round-10 findings addressed;
> pending Codex round-11 re-review. FR-26 ⇄ this doc are cross-linked; §7 traces every `CR-n` to a sub-issue.

## 1. Problem

HITL treats a change's **delivery surface** as a single choice — Web UI, mobile, API/backend,
agentic workflow, internal tool, "or a combination" (`pm-design-feature` §1; `ai/codex/AGENTS.md`).
The agentic branch assumes **one** agent: it captures a single decision path (trigger → tools →
decision points → HITL gates → output → failure modes).

Real AI products are increasingly **compound**: a *graph* of components — web/API frontends,
deterministic services, simple agents, and deep agents — with traffic routed between them, some
hops synchronous request/response and some **asynchronous agent-to-agent (A2A)**. HITL has no
first-class treatment of the *composition*: how the components are typed, where determinism ends
and stochasticity begins, how the inter-agent contracts are declared and reviewed, how privilege
and tool use are bounded per agent, and how the pieces are independently evaluated.

### Why this is HITL's lane, and where the boundary is

The emerging agent-interoperability standards express **syntax and tools but not governance**.
A2A carries capability discovery (Agent Cards) and task messages; MCP carries tool invocation.
Neither expresses *who may call an agent, with what privilege, using which approved tools, under
what review* — the governance layer. That gap is precisely what HITL fills ("agent harness / AI
control plane").

**HITL governs the build; it is not a runtime.** This surface ships design discipline, skills,
templates, manifest-schema extensions, validators/gates, generated posture views, a worked
*example design*, and a built plugin. It does **not** ship a running system, cloud infrastructure,
a messaging backbone, a live dashboard, or an eval engine — those are the product's runtime, which
the surface *requires and governs*. A runnable reference product (optionally GCP + a broker) is
tracked separately in companion epic
[#21](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/21), kept out of the framework so
no cloud/runtime opinion leaks in.

## 2. Scope of the delivery surface

A **compound agentic system** is a product whose design is a directed graph:

- **Nodes** = components, each one of three kinds:
  - *deterministic workflow / service* — same input, same output (a SaaS-style service, a
    scripted orchestration, an API);
  - *simple agent* — a single LLM-in-a-loop (ReAct / plan-and-execute) with bounded tools;
  - *deep agent* — a long-horizon agent with a planner, persistent memory, sub-agent delegation,
    and context isolation.
- **Edges** = typed interactions:
  - *sync* — request/response (HTTP/JSON-RPC), including MCP tool calls;
  - *async A2A* — message/event over a broker or A2A transport (SSE stream, webhook push,
    polling), for long-running or fan-out work.

The surface governs the **graph**, not any single node in isolation. A single-agent product stays
on the existing agentic surface; this surface applies when there is more than one component and at
least one inter-component edge.

## 3. Goals

1. **Make composition first-class.** A compound-agentic delivery surface with its own design track,
   selected the same way the other surfaces are.
2. **Right-size the components.** Force explicit classification (deterministic / simple / deep) and
   the simplest component that satisfies the task — multi-agent is not a default.
3. **Draw the determinism boundary.** Make explicit where deterministic behavior ends and
   stochastic behavior begins, and enforce a discipline at that seam.
4. **Model A2A as governed contracts.** Reuse the manifest `facade_apis` mechanism so every
   inter-component and A2A edge is a declared, reviewed, boundary-enforced contract — not an
   implicit prompt-string coupling.
5. **Bound privilege and tools per agent.** Necessary-and-sufficient privilege and an approved-tool
   set, declared, validated, and surfaced.
6. **Make the pieces independently testable.** PM/QA can evaluate a single node, a single edge, or a
   flow segment — mirroring the single-agent QA path — not only end-to-end.
7. **Stay framework-agnostic.** Govern the composition; name LangGraph, the A2A protocol, and MCP
   only as examples, never as modules HITL maintains.
8. **Keep the human current with the field.** Surface the modern capability options at each design
   decision so the PM/Architect chooses deliberately — the harness informs the design, it does not
   let the AI default to a naive implementation because the better recent option was not top of mind.

## 4. Requirements

Requirement IDs are `CR-<n>` (Compound Requirement). Each maps to sub-issues in §7.

> **Relocated (2026-07-21):** **CR-1** (surface selection / design-track routing) and **CR-19** (the
> capability menu) have moved to the **Agentic Design Advisor** ([FR-28](../prd.md);
> [`../agentic-design-advisor/requirements.md`](../agentic-design-advisor/requirements.md)). Those are
> *elicitation* — helping a human arrive at and right-size the design — which is the Advisor's job. This
> surface (#10) owns *representation, validation, and evidence*: how a compound system is declared,
> checked, and proven. Their rows below are kept as tombstones so existing references resolve.

| ID | Requirement | Priority |
|---|---|---|
| ~~CR-1~~ | **Relocated → Agentic Design Advisor (FR-28, [ADV-1/ADV-13](../agentic-design-advisor/requirements.md)).** Surface selection and the compound design track are elicitation, owned by the Advisor. | *moved* |
| **CR-2** | The design **classifies every component** as deterministic workflow / simple agent / deep agent, and justifies choosing the **simplest** kind that satisfies the task. | Must |
| **CR-3** | The design produces a **topology & routing view**: the component graph with **typed edges** (sync vs async A2A) and how traffic routes across it. | Must |
| **CR-4** | The design marks the **determinism boundary** and enforces the discipline: every *stochastic → deterministic* edge validates the stochastic output (schema/guardrail) before a deterministic component trusts it; every *deterministic → stochastic* edge sets **bounded cost and bounded authority**. | Must |
| **CR-5** | Inter-component and **A2A contracts are modeled as manifest `facade_apis`** (preconditions, error modes), enforced by the domain-boundary hook. A2A **Agent Cards** map to facade declarations; **Task** objects to the call payloads. | Must |
| **CR-6** | The design captures **compound failure modes**: non-determinism propagation across hops, cross-hop timeout/retry, cycle/loop detection, token-cost amplification (fan-out), and cross-agent trust. | Must — core part; deferred part → 2.3.0 (§4.1) |
| **CR-7** | Where a component is a **deep agent**, its design covers: a planner, persistent/virtual-filesystem memory, a **sub-agent registry** with capability descriptions, context isolation, its own HITL gates, and **never-do guardrails**. | Must |
| **CR-8** | **Compound-system testing**: per-node evals, per-edge contract tests, sub-flow/segment tests, and end-to-end tests are all defined. Every component and edge is **independently testable**. | Must — core part; deferred part → 2.3.0 (§4.1) |
| **CR-9** | **Observability + PM eval-console — a hard, gated design obligation** (2026-07-22 directive). Every agentic system must **declare** (a) OTel/OpenInference-style **cross-hop tracing** (what is traced at each hop) + a **token-cost amplification budget**, and (b) a **PM-facing eval console** — a surface (beyond the CLI adapter) where the PM runs evals and reviews results/traces. HITL **validates the declaration and gates on it** (`check_observability`; a design that omits it **fails** — same teeth as a human gate). *HITL enforces the declaration + gate + static posture view; the **product builds** the running console/trace backend (#21 is the runnable reference) — O1 governs-not-runtime preserved.* | Must (floor) |
| **CR-10** | **Framework-agnostic guardrail**: no LangGraph/A2A/MCP-specific modules ship. They appear only as named examples the pattern governs. HITL governs the build, not the runtime. | Must |
| **CR-11** | The design **names the orchestration pattern** (supervisor/orchestrator-worker, hierarchical, swarm, blackboard, sequential, hybrid) and **justifies it against task shape**, with the explicit caution that multi-agent carries material token overhead (~58% distributed to ~285% centralized in reported production) and is not a default. | Must |
| **CR-12** | **Async A2A reliability** is designed: **idempotent consumers** (exactly-once is not assumed at the broker boundary), **sagas / compensating actions** for multi-agent rollback, **dead-letter** handling, and **replay / event-sourcing** where applicable. Ties to `docs/patterns/idempotency-keys.md`. | Must — core part; deferred part → 2.3.0 (§4.1) |
| **CR-13** | Each edge carries an **agent authorization / non-human identity** decision: who may invoke the agent and what it may do once invoked, defaulting to **just-in-time, least-privilege**. | Must — core part; deferred part → 2.3.0 (§4.1) |
| **CR-14** | **Necessary-and-sufficient privilege, at declaration granularity (scoped-capability model).** Each agent declares its identity and its capability **uses** — per-use scoped: tools, memory access, and non-tool `capabilities` (KMS/model-endpoint/delegation/ambient) — each with the specific operations/resources it needs. The approved-capability registry declares each capability's **ceiling** (max grantable scope). A **validator** proves `needed = ⋃(per-use scopes)`, and flags **over-privilege** (a grant beyond `needed`), **under-privilege** (a declared use not granted), and **ceiling-violation** (a per-use scope beyond its registry ceiling). A **privilege-posture artifact** is generated (machine-readable **and** rendered). This is necessary-and-sufficient **for the declared uses**; whether the running code matches the declaration is enforced by human review + an **optional read-only runtime drift-check**. HITL governs the declaration; it does not run the live IAM plane. *(Design scoping, ADR-9/ADR-13: **edge-invocation** — "may A invoke agent B" — is governed by **CR-13's interaction `authorization`** (allowed-callers, JIT), not by this identity-privilege union. It was moved out because it is an authorization relationship between two domains, not a capability A holds; folding it into the ceiling model conflated the two and let invoke scopes bypass ceilings. The invoke decision is still declared, reviewed, and gated — under CR-13.)* | Must — core part; deferred part → 2.3.0 (§4.1) |
| **CR-15** | **Approved tool set.** An **approved-tool registry** (tool + scope + risk) exists; each agent **declares** its tools from that registry; a **gate blocks** any agent that declares an undeclared or unapproved tool. Runtime tool allow-listing is required in the product's guardrail layer. *(Design fold-in, ADR-9: tools are the `class: tool` rows of the approved-capability registry — that class **is** the approved-tool registry, the tool-class `uses` **are** the per-agent tool declarations, `check_capabilities` **is** the gate, a generated tool matrix is the `class:tool` projection, and each tool row's `runtime_ref` carries the runtime allow-list identifier. One privilege model, tool identity and runtime mapping preserved — not a separate subsystem.)* | Must |
| **CR-16** | **PM/QA-runnable independent evals — via a declared PM eval console (hard).** PM/QA can define and run evals against a single component or flow segment, backed by an **eval-dataset spec**, a **registry**, and a **reviewer gate** — mirroring the single-agent `qa-plan-tests` → `qa-verify-quality` path — plus **continuous eval from production traffic** as a maturity rung. The design must declare the **PM eval console** the PM uses to do this (paired with CR-9's observability; HITL gates on the declaration, the product builds the console). | Must — core part; deferred part → 2.3.0 (§4.1) |
| **CR-17** | **Long-running / durable execution lifecycle.** Where a component runs over minutes-to-days, the design covers its **lifecycle**: durable **checkpointing** and **resumability** across restarts, **pause-and-resume around human gates** (human-in-the-loop over long horizons), timeout/cancellation, and **idempotency on resume** (a resumed step must not re-fire side effects). The design names how state survives a crash. Durable-execution engines (Temporal-style, LangGraph checkpointing) are named as examples the pattern governs, never modules. Complements CR-12 (this is the component's own statefulness; CR-12 is the edge's reliability). | Must |
| **CR-18** | **Memory model, short- and long-term, governed.** The design declares each agent's memory: **short-term / working** (context-window budgeting, summarization/compression, sub-agent context isolation — the "context engineering" discipline; ephemeral) and **long-term / persistent** (cross-session semantic/episodic store, retrieval, and *what is written*). Long-term memory is a **governed durable store**, treated like HITL's own durable memory: writes are declared per agent (alongside tools/privileges, CR-14/CR-15), high-stakes writes carry guardrails, **PII/redaction** rules apply, and staleness/ownership are tracked. Shared-vs-isolated memory across agents is an explicit topology decision. | Must |
| ~~CR-19~~ | **Relocated → Agentic Design Advisor (FR-28, [ADV-6/ADV-11](../agentic-design-advisor/requirements.md)).** The design-time capability menu (present options with when-to/when-not, recommend the simplest that fits, record chosen + rejected, refreshable catalog, Tier-3 newer-capability scan) is elicitation, owned by the Advisor and the best-practice-advisory ([#8](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/8)). | *moved* |
| **CR-20** | **Generate baseline evals by default; make PM eval ownership the default.** For each agentic component and flow segment, HITL **generates a baseline eval set by default** — derived from the acceptance criteria (the owning `FR-n`), the component's declared contract (`facade_apis` preconditions + error modes), the determinism-boundary checks (CR-4), and the known failure modes (CR-6) — and presents it to the **PM to refine, extend, and approve** (AI drafts the starting evals; the PM owns them). The workflow **actively prompts the PM** to provide/own evals as a default expectation for agentic changes; a component shipping with **no** evals is a recorded, waived exception, not a silent gap. Baseline evals seed the eval registry and the per-segment tests (CR-8, CR-16). | Must |

### 4.1 Core-v1 scope, deferred follow-ons, and the release boundary (round-4 lock + round-5 M4)

The requirements above express the full intent. Delivery is **staged**: a **minimal sound core ships as
2.2.0**, and the heavier parts are **explicitly re-scoped to a follow-on release** (#42) — see
[`../../design/agentic-core-scope.md`](../../design/agentic-core-scope.md). Each staged CR splits into a
**core part (Must, 2.2.0)** and a **deferred part (re-scoped Should → next release, not release-gating for
2.2.0)**:

| CR | Core part — **Must, 2.2.0** | Deferred part — **re-scoped, next release (#42)** |
|---|---|---|
| **CR-6** | compound failure modes captured; sync reliability = facade `error_modes` + product runtime (honest) | design-time sync **timeout/retry declaration** checks |
| **CR-8 / CR-16 / CR-20** | **independent per-agent eval + one e2e**; PM-runnable eval-adapter *contract*; single-owner baseline generator; **the declared PM eval-console** (gated, tier-scaled) | **universal** per-component/edge coverage; **result ingestion + result-review** envelope; **multi-owner** baseline |
| **CR-9** *(observability)* | **the gated design declaration** — tracing (OTel/OpenInference required attributes) + cost budget + tier-scaled PM eval-console, validated by `check_observability` at the floor | the **runtime** trace backend + rich posture dashboard (product / #21); posture-view rendering refinements (#15) |
| **CR-12** | **declared** sagas validated (sequential) + a **compensation-gap advisory** | the **required-when** model; **`parallel`** compensation; segment↔saga linkage |
| **CR-13 / CR-14** *(privilege)* | `allowed_callers` + `authority ⊆ consumer` (an **explicit release limitation**, not full satisfaction — round-5 M8) | **delegated per-interaction authority** (what caller A may ask B to exercise) |

**Release boundary (round-5 M4).** The core **does** close **#10 / 2.2.0**: the deferred parts above are
**re-scoped out of the 2.2.0 Definition of Done** (downgraded from Must to a next-release Should, tracked in
#42) rather than left as unmet 2.2.0 Musts. So 2.2.0 ships a smaller, honestly-scoped compound surface; #42
is a distinct follow-on release (target 2.3.0). The DoD / acceptance gate (HLD §13) is scoped to the **core
part** of each CR above; it does not claim the deferred parts.

The deferred items are not dropped — they move to a tracked #10 follow-on issue (#42). The **PM eval console
+ live traces** is a **hard, gated design obligation** (2026-07-22 directive, CR-9/CR-16 at the floor): HITL
ships the declaration schema, the `check_observability` validator, the floor gate, and the static posture
view; the **product builds** the running console + trace backend, with the companion product (#21) as the
runnable reference — O1 governs-not-runtime preserved (HITL enforces it, the product runs it).

## 5. Constraints

- **Additive only** to the change-file schema and the manifest schema (2.0 rule: existing fields
  kept, new fields added; `verify` stays lossless).
- **Reuse existing mechanisms**: manifest domains + `facade_apis`, the domain-boundary hook, the
  registries pattern (test/incident → new tool + eval registries), tiered waivers, generated
  derived views (command-map / catalog / readiness register are the precedent for the posture
  matrix), reviewer subagents, and the breadcrumb. No new orthogonal machinery.
- **Governs, does not run.** Skills scaffold and validate design and config with operator
  confirmation (the `ops-apply-iac` model). No cloud-provider opinions; no shipped runtime,
  backbone, dashboard, or eval engine.
- **Tier-proportionate.** A two-component product must not drown in ceremony; a 20-agent mesh must.
  Ceremony scales with component count, edge count, and risk tier.

## 6. Non-goals

- A running multi-agent system, cloud infrastructure, or a **messaging backbone** — the product's
  runtime; the surface governs its design (companion epic #21 builds a demo separately).
- A **live dashboard** or **eval engine** — HITL generates the posture/coverage data and the static
  rendering; the live surfaces are the product's (LangSmith/Galileo/Arthur-class tools, an IAM
  console, an APM).
- **Framework-specific modules** (LangGraph, A2A SDK, MCP servers). Examples only.
- Runtime enforcement of IAM or tool allow-lists — HITL enforces at **design time** (declaration +
  validator + gate); the product enforces at **run time** (the surface requires it).

## 7. Traceability

Requirements → sub-issues → deliverables. Epic
[#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10); PRD **FR-26**.

| Sub-issue | Deliverable | Requirements |
|---|---|---|
| [#11](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/11) | HLD + ADR(s) | CR-3, CR-4, CR-5, CR-10, CR-17, CR-18 |
| [#12](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/12) | `pm-design-feature` + `AGENTS.md` surface branch | CR-2, CR-7, CR-11, CR-17, CR-18, CR-20 *(CR-1/CR-19 relocated to FR-28)* |
| [#13](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/13) | HLD & test-strategy templates + manifest schema | CR-3, CR-5, CR-7, CR-12, CR-13, CR-14, CR-15, CR-17, CR-18 |
| [#14](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/14) | Pattern doc `docs/patterns/compound-agentic-systems.md` (the capability catalog now feeds the Advisor, FR-28) | CR-4, CR-6, CR-11, CR-12, CR-17, CR-18 |
| [#15](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/15) | Agentic observability — **runtime** posture views + trace-backend reference (the design-time declaration + gate for CR-9 moved to #16 core, 2026-07-22) | CR-9 (runtime portion), CR-14, CR-15 |
| [#16](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/16) | Validators + gates + baseline-eval generator **+ `check_observability` (CR-9/CR-16 design declaration + floor gate, 2026-07-22)** | CR-4, CR-6, CR-7, CR-13, CR-14, CR-15, CR-8, **CR-9**, CR-16, CR-17, CR-18, CR-20 |
| [#17](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/17) | User docs + playbook + worked example design | CR-1..CR-20 (documentation) |
| [#18](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/18) | Website/portal update + screenshots | CR-1..CR-20 (portal) |
| [#19](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/19) | Codex two-stage validation + guide/prompt | Definition of done |
| [#20](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/20) | Release 2.2.0 (blocked by #19) | Version |

## 8. Effort scope (definition of done for the epic)

The epic is not "done" until all of the following ship, per the user's scoping:

- **Design docs**: this requirements doc, `01-design.md` (HLD), ADR(s), and the pattern doc.
- **Skills / templates / schema**: HLD and test-strategy templates; manifest schema extensions (component
  kinds, typed edges, identity + privilege, approved-tool registry); agentic-observability additions.
  *(Round-10 blocker 6 — release-decoupling: the `pm-design-feature` + `AGENTS.md` **surface-branch routing**
  is **owned by the Advisor's [#37](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/37)**, not
  #10, and is **not** a #10 release-gate. #10's core — schema + validators — runs directly on a
  **human-authored manifest** (a `check_manifest_agentic.py` entry point on a manifest file), so #10 ships
  first as 2.2.0 with no dependency on Advisor routing.)*
- **Validators / gates**: the necessary-and-sufficient privilege validator, the approved-tool gate,
  and the per-segment eval discipline — each with a regression suite under `ci/`.
- **Worked example design package** under `docs/examples/` (an example manifest, topology +
  determinism-boundary map, example A2A facade contracts, example HLD — a *design*, not a running
  app).
- **User docs & playbook** updated; **release notes** (CHANGELOG 2.2.0); **website/portal** updated
  with the surface and the determinism-boundary principle; **screenshots** refreshed where
  appropriate; the generated catalog page regenerated.
- **Codex validation**: `docs/validation-guide.md` updated + a per-feature Codex prompt; a
  two-stage validation report filed to `hitl-internal/docs/validation-reports/`.
- **Version + distribution**: bump to **2.2.0**, build the plugin, and publish on `release/2.x`.

## 9. Version

**2.2.0** — additive minor (a new delivery surface + additive schema/registries), **2.x line only**.
The 1.x line (`hitl-1x@hitl`) is feature-frozen and does not receive this.

## 10. Codex validation (two stages, gated)

Mirrors the 2.0 and platform-bootstrap campaigns. The **Release** sub-issue (#20) is blocked by the
**Validation** sub-issue (#19).

1. **Stage 1 — main repo (source).** In `hitl-dev-platform`: `derive.py verify` lossless, full
   `pytest ci/`, skill-lint, breadcrumb matrix, and the doc checks (paths, cross-refs, counts,
   YAML validity). Plus the new validators (privilege, approved-tool) and their suites.
2. **Stage 2 — built plugin.** Run the plugin repo's `scripts/build.sh`, then re-run the
   behavior/gate tests **against the built tree**, verify source↔plugin parity, and
   `claude plugin validate`. This catches build-time path/normalization defects that source-only
   checks miss.

Reports are filed to the private `hitl-internal/docs/validation-reports/`; the repeatable *how*
(guide + prompt) lives in this repo.

## 11. Success criteria

1. A product with ≥2 components routes into the compound surface and produces a topology + typed
   edges + determinism-boundary map, with each component classified and the orchestration pattern
   justified.
2. Every A2A edge is a declared manifest `facade_api`; the domain-boundary hook flags an off-contract
   agent interaction.
3. The privilege validator flags a deliberately over-privileged and a deliberately under-privileged
   agent; the approved-tool gate blocks an agent declaring an unapproved tool.
4. A PM can run an independent eval against one component and one flow segment and get a
   reviewer-gated result, without running the whole system.
5. The generated privilege + approved-tool + eval-coverage matrices render from declared data (no
   hand-maintenance).
6. Catalog `verify` stays lossless; skill-lint passes on all new/changed skills; both Codex stages
   pass (or findings are remediated) before the marketplace serves 2.2.0.

## 12. References (best-practice basis, researched 2026-07-17)

- Orchestration patterns (supervisor ~70% of production; hierarchical; swarm only for 50+
  independent subtasks; token overhead ~58–285%): [digitalapplied — 5 patterns that work in
  2026](https://www.digitalapplied.com/blog/multi-agent-orchestration-5-patterns-that-work);
  [Kore.ai — choosing an orchestration pattern](https://www.kore.ai/blog/choosing-the-right-orchestration-pattern-for-multi-agent-systems).
- A2A protocol (Agent Cards, Task objects, HTTP/JSON-RPC/SSE, sync vs async; A2A = messaging layer,
  MCP = tool layer): [niteagent — A2A 2026 guide](https://niteagent.com/blog/a2a-protocol-guide-2026/);
  [Zylos — A2A vs MCP](https://zylos.ai/research/2026-05-16-agent-to-agent-communication-protocols-a2a-mcp/).
- Event-driven / async reliability (idempotent consumers, sagas, DLQ, replay; A2A on top of EDA):
  [digitalapplied — EDA & message queues 2026](https://www.digitalapplied.com/blog/event-driven-architecture-message-queues-2026-engineering-reference);
  [Microsoft — multi-agent reference architecture, message-driven](https://microsoft.github.io/multi-agent-reference-architecture/docs/agents-communication/Message-Driven.html).
- Deep agents (planner, virtual-fs memory, sub-agent registry, context isolation; ReAct for simple,
  deep only for long-horizon): [LangChain — Deep Agents](https://www.langchain.com/deep-agents);
  [LangChain docs — Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview).
- Observability, guardrails, authorization (OTel/OpenInference tracing, layered guardrails,
  continuous eval from prod traffic, non-human identity + least-privilege control plane):
  [Arthur — agentic observability playbook 2026](https://www.arthur.ai/column/agentic-ai-observability-playbook-2026);
  [Galileo — AI agent guardrails 2026](https://galileo.ai/blog/best-ai-agent-guardrails-solutions);
  [CSA — securing the agentic control plane](https://cloudsecurityalliance.org/blog/2026/03/20/2026-securing-the-agentic-control-plane).
- Governance gap in interoperability protocols (what A2A/MCP cannot express — HITL's lane):
  [arXiv 2606.31498 — governance gaps in agent interoperability protocols](https://arxiv.org/pdf/2606.31498).
