# Compound Agentic System Surface: Architecture Decisions

> ADRs formalizing the decisions **D1–D9** from
> [`01-design.md`](01-design.md) §14 (architect-approved 2026-07-17). Each records the forces, the
> decision, the **alternatives with their concrete cost**, and the consequences. EPIC
> [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status: **accepted**.

---

## ADR-1 (D1): A component IS a manifest domain (extended with `kind`)

**Status:** Accepted.

**Context.** A compound agentic system is a graph of components (deterministic services, simple agents,
deep agents). Each needs an owner, a governing design doc, boundary enforcement, and a declared public
contract. The system manifest already models exactly this for bounded contexts — domains with
`facade_apis`, enforced by the domain-boundary hook.

**Decision.** A component is a manifest **domain**, extended with a `kind` field
(`deterministic | simple_agent | deep_agent`). No separate agent model.

**Alternatives and their cost.**
- *A separate agent registry alongside the manifest.* Cost: two sources of truth to keep in sync; the
  domain-boundary hook would not cover agents (it keys off manifest domains), so agent interactions
  would be unenforced; the facade-contract model would have to be re-implemented for agents.
- *A new top-level `agents:` section in the manifest.* Cost: agents would not inherit domain-boundary
  enforcement or the facade contract for free; net-new machinery for something the domain model already
  does.

**Consequences.** (+) Agents are first-class domains — boundary enforcement, facade contracts, and LLD
linkage carry over unchanged. (−) "Domain" now spans a wide range (a scripted service and a deep agent
are both domains), so `kind` must gate which of the new fields (deep_agent, lifecycle, memory) apply —
which the completeness validators (§6) enforce.

---

## ADR-2 (D2): An inter-component / A2A edge IS a `facade_api` (extended with `transport`)

**Status:** Accepted.

**Context.** Every inter-component call and A2A edge must be a declared, reviewed, boundary-enforced
contract, not an implicit prompt-string coupling (the failure this surface exists to kill). A domain's
`facade_apis` already are its public contract, and an A2A **Agent Card** is a list of advertised
capabilities — structurally the same thing.

**Decision.** An edge is a `facade_api`, extended with `transport` (`sync | async`); the A2A Task
payload shape lives in `signature`. An agent's Agent Card *is* its facade map.

**Alternatives and their cost.**
- *A separate `edges:` / `contracts:` section.* Cost: duplicates facade semantics; the boundary hook
  keys off facades, so a parallel edge model would not be enforced.
- *Model A2A as external protocol config outside the manifest.* Cost: the contract would be neither
  reviewed nor boundary-enforced — back to implicit coupling, the exact problem.

**Consequences.** (+) Agent Cards get declaration, review, and boundary enforcement for free; async is
additive. (−) The facade schema must carry `transport` + the `async` block + the payload in `signature`,
which surfaces the pre-existing schema/template form disagreement (ADR-8).

**Refinement (2026-07-18, LLD [`03-lld.md`](03-lld.md) §2.3).** The edge is realized in **two coupled
places**: the **callee** declares the contract (its `facade_api` — `transport`, `signature`,
preconditions/error_modes), and the **caller** declares the edge itself as a `calls: [Edge]` entry that
*references* that facade (`Edge.to = "<domain>.<facade>"`) and carries the caller-side **boundary
attributes** (`output_validation`, `cost_bound`, `authority_bound`) — because the caller is the party
that must validate output and bound cost/authority. This is **not** the "separate `edges:` section"
rejected above: `calls` *references* facades, it does not redefine their contract, so declaration and
boundary enforcement still live on the facade. The split exists so the boundary invariant (ADR-7) has a
home on the party responsible for it, and so the edge graph is *declared* (never inferred from
`signature` strings). `authority_bound` MUST be ⊆ the callee's `identity.privilege` (an edge cannot
grant authority the callee never held) — validated in LLD §5.3.

---

## ADR-3 (D3): Topology, privilege, and tool posture are generated views

**Status:** Accepted.

**Context.** Derived data that is hand-maintained drifts and goes silently wrong — the precedent set by
the command-map, catalog, and readiness register is to generate it.

**Decision.** The topology/routing view, the privilege-posture matrix, and the approved-tool matrix are
**generated** from the manifest + registries; they are static (no live dashboard).

**Alternatives and their cost.**
- *Hand-drawn topology diagrams / manually curated posture tables.* Cost: they drift from the manifest,
  become authoritative-looking but wrong, and reintroduce the exact drift the framework prevents.

**Consequences.** (+) Cannot drift; always reflects the manifest. (−) Requires a generator (a build
step) and forces the manifest to carry all the source data — which is what drove the §2 schema
extensions.

---

## ADR-4 (D4): Framework-agnostic — govern capabilities, name frameworks only as examples

**Status:** Accepted.

**Context.** The field moves monthly (LangGraph, the A2A protocol, deep agents, Temporal, Vercel AI
SDK). Anything framework-specific HITL ships inherits that framework's churn.

**Decision.** Govern the *capabilities* (component kinds, orchestration patterns, memory, durable
execution, A2A contracts); name concrete implementations only as examples in the capability catalog.
No framework modules or adapters ship.

**Alternatives and their cost.**
- *Ship framework-specific integrations (e.g. a LangGraph adapter).* Cost: HITL takes on that
  framework's release cadence and breaking changes as a permanent maintenance liability, endorses a
  stack, and the capability catalog rots faster with every framework version.

**Consequences.** (+) Durable, no lock-in; HITL stays a governance layer above any framework. (−) HITL
gives no head-start on a specific framework, and the capability catalog must be actively maintained
(the staleness cost, tracked in [#8](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/8)).

---

## ADR-5 (D5): Governs, does not run

**Status:** Accepted.

**Context.** The recurring line that keeps HITL coherent: a live dashboard, a message backbone, and an
eval engine are the product's runtime, not the framework's. The platform-bootstrap design already
locked "HITL does not own infrastructure."

**Decision.** HITL validates the design and emits **static** views; it ships no runtime dashboard,
messaging backbone, or eval engine, and does not phone home. The domain-boundary hook stays
**design-time** (checks a declared facade; never inspects live traffic).

**Alternatives and their cost.**
- *Ship a live posture dashboard / an eval engine / a broker.* Cost: HITL becomes a runtime product
  competing with Grafana/LangSmith/Kafka, inherits their ops burden, crosses into the customer's infra,
  and violates the "does not own infrastructure" constraint.

**Consequences.** (+) Stays in lane, cloud-agnostic, minimal ops surface; the emitted register + static
report feed the customer's own tools. (−) The live dashboard and eval execution are the customer's to
build; the runnable proof lives in the separate companion demo
([#21](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/21)).

---

## ADR-6 (D6): The capability menu is always presented; recommend, never silently decide

**Status:** Accepted.

**Context.** The AI defaults to the simplest, most-familiar implementation, and the newer/better option
(deep agents, A2A, durable execution) may be in neither the AI's instincts nor the human's head. "AI
proposes, humans decide."

**Decision.** At each design decision with materially different modern options, the harness **always
presents the menu** (with when-to / when-not) and records chosen + rejected. It **may recommend but
never silently decides.**

**Alternatives and their cost.**
- *Let the AI auto-pick the "best" option.* Cost: naive defaults win, the human loses both the decision
  and the learning, and an always-pick-the-fancy-option bias breeds over-engineering.
- *Present options only when the AI is unsure.* Cost: the AI is most naively confident exactly when it
  is wrong, so the human would never see the menu in the cases that matter.

**Consequences.** (+) The human stays in control and current; decisions are recorded and reviewable.
(−) More decision points for the human — mitigated by the "when-not" guidance so the menu can actively
say "the simple option is right here" (upholding ADR/CR-2's "simplest that works"). Requires the
curated catalog (ADR-4's maintenance cost).

---

## ADR-7 (D7): The determinism boundary is derived and validated

**Status:** Accepted.

**Context.** The seam between deterministic components and stochastic agents is where a stochastic
output corrupts a deterministic system, or cost/authority leaks into an agent. This must be a checkable
invariant, not a prose reminder.

**Decision.** Boundary edges are **derived** from component `kind`s; a fail-closed validator requires
output validation on every stochastic→deterministic edge and bounded cost + authority on every
deterministic→stochastic edge.

**Alternatives and their cost.**
- *Leave it as a design-review checklist.* Cost: unenforced, silently skipped under deadline pressure —
  the precise failure mode HITL exists to eliminate; no teeth.

**Consequences.** (+) A checkable, fail-closed invariant at the exact seam that matters. (−) Depends on
component `kind`s being declared accurately, and adds a gate to the design.

---

## ADR-8 (D8): Extend the schema (map) form of `facade_apis`; payload = `signature`; reconcile the template

**Status:** Accepted.

**Context.** Two forms of `facade_apis` already exist and disagree: the authoritative schema
(`system-manifest.schema.yaml`) defines a **map** keyed by name with `signature`/`blurb`/`mutations`;
the older template uses a flat **list**. An A2A Task payload also needs a declared home.

**Decision.** Extend the **schema map form**; the A2A Task payload/contract shape lives in `signature`;
reconcile the older list-form template to match as part of implementation.

**Alternatives and their cost.**
- *Extend the template list form.* Cost: diverges from the authoritative schema, drops
  `signature`/`blurb`/`mutations`, and leaves an async edge with no payload contract to review.
- *Leave both forms and pick per-doc.* Cost: inherits and deepens an existing inconsistency;
  implementers would not know which to follow.

**Consequences.** (+) One authoritative form; the A2A payload has a home. (−) Requires a template
reconciliation task that touches existing docs/examples using the list form (a tracked implementation
step, not a silent inheritance).

---

## ADR-9 (D9): Every agent privilege traces to a tool scope or a memory scope (no orphan channel; per-store)

**Status:** Accepted.

**Context.** The privilege validator needs an independently **computable** "needed" set to flag over-
and under-privilege. Round-2 review showed that without a complete source model, legitimate reads (e.g.
`read:corpus`) are false-flagged as over-privilege.

**Decision.** `needed = ⋃(approved-tools[t].scopes for t in tools) ∪ {read|write:memory/<store> per
long_term store}`, at **per-store** granularity. Every privilege an agent holds must trace to a tool
scope or a memory scope; there is **no orphan-privilege channel** — inter-agent access is governed by
edges (ADR-2), not free-floating scopes.

**Alternatives and their cost.**
- *Let agents declare a free-form "needed privileges" list.* Cost: it is just a second copy of
  `granted` — nothing independent to reconcile against, so over/under can never be flagged (the B1
  blocker returns).
- *Cover only tool scopes (not memory).* Cost: a declared memory write with no matching grant would
  pass, breaking the memory↔privilege invariant.

**Consequences.** (+) `needed` is computable; over/under-privilege and the memory↔privilege invariant
are all enforced by one validator. (−) Every agent capability must be modeled as a tool, a memory
access, or an edge — a genuinely tool-less, memory-less privilege has no home; accepted, because agent
capability in this model *is* tools + memory + edges.

---

## Decision index

| ADR | HLD decision | One-line |
|---|---|---|
| ADR-1 | D1 | Component = manifest domain (+`kind`) |
| ADR-2 | D2 | Edge = `facade_api` (+`transport`); Agent Card = facade map |
| ADR-3 | D3 | Topology/privilege/tool posture are generated views |
| ADR-4 | D4 | Framework-agnostic; implementations are examples only |
| ADR-5 | D5 | Governs, not runs; boundary hook stays design-time |
| ADR-6 | D6 | Capability menu always presented; recommend, never decide |
| ADR-7 | D7 | Determinism boundary derived + fail-closed validated |
| ADR-8 | D8 | Extend the schema map form; payload = `signature` |
| ADR-9 | D9 | Privilege traces to tool/memory scopes; per-store; no orphan channel |
