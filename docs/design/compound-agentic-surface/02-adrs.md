# Compound Agentic System Surface: Architecture Decisions

> ADRs formalizing decisions **D1–D12** from [`01-design.md`](01-design.md) §11. Each records the forces,
> the decision, the **alternatives with their concrete cost**, and the consequences. **v2** — ADR-2 and
> ADR-9 rewritten and ADR-10/11/12 added after the Codex review (2026-07-18); see [`04-revision-plan.md`](04-revision-plan.md).
> EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status: **accepted, pending Codex re-review**.

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

## ADR-2 (D2): An edge IS an extended `interaction_matrix` entry (v2 — rewritten)

**Status:** Accepted (rewritten 2026-07-18 after Codex review M1; supersedes the v1 "edge = facade_api"
decision, which duplicated the manifest's existing `interaction_matrix`).

**Context.** Every inter-component call and A2A edge must be a declared, reviewed, boundary-enforced
contract, not implicit coupling. The manifest **already** has a top-level directed edge model —
`interaction_matrix: map["from -> to", InteractionEntry]` — carrying `entity_crossing`. v1 added a
separate `calls` field that duplicated it (Codex M1), and asserted "edge = facade_api" — but a facade is
a *callee-side contract*, not the *edge* (it can't carry per-edge trust legs, authorization, or
distinguish two interactions between the same pair).

**Decision.** The **edge is an extended `interaction_matrix` entry**, with a stable `id`, a `kind`
(`sync_call | async_task | event`), a `facade` *reference* to the callee's contract (whose `signature`
is the payload shape), separate **request/response trust legs**, an **authorization** block (who may
invoke), and an `async` block. The **facade remains the contract**; the interaction is the **edge**.
`depends_on` becomes an auto-derived projection of this model. The v1 `calls` field is deleted.

**Alternatives and their cost.**
- *Keep v1's separate `calls` field.* Cost: duplicates the existing `interaction_matrix` (two authoritative
  edge sources with no reconciliation rule — Codex M1); the double-representation/cycle logic had to
  match on domain pairs, which cannot distinguish two real interactions between the same pair.
- *Edge = facade_api (v1).* Cost: a facade is callee-side and single-contract; it can't home the caller's
  trust obligations, the response-leg validation (Codex B1), or who-may-invoke (Codex B2).
- *A parallel `edges:` section separate from `interaction_matrix`.* Cost: same duplication, unenforced by
  the boundary hook.

**Consequences.** (+) One authoritative, human-authored, directed edge model with stable IDs; trust legs,
authorization, and async live where they belong; `depends_on` is derived so it can't disagree. (−) The
boundary hook must extend to check interaction authorization (LLD §6.4); the pre-existing facade
list→map disagreement (ADR-8) still must be reconciled.

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

## ADR-9 (D9): Scoped-capability privilege — per-use scopes + registry ceilings (v2 — rewritten)

**Status:** Accepted (rewritten 2026-07-18 after Codex review B4; supersedes the v1 tool/memory-only
"needed" set, which proved only that two authored sets were equal — not necessity or sufficiency).

**Context.** CR-14 wants necessary-and-sufficient privilege. v1 computed `needed = ⋃(tool scopes) ∪
memory scopes` — but a tool's *global* scopes over-count (a read-only user of a read/write tool was told
it "needs" write), non-tool capabilities (KMS, model endpoint, delegation, ambient) had no home and were
false-flagged, and a registry that omitted a scope made both sides agree on "sufficient" while runtime
failed. Deriving *actual* necessity requires running the code — which is the product's IAM, not the
framework's (ADR-5).

**Decision.** A **scoped-capability** model. Capability **sources** are complete: tools, memory,
non-tool `capabilities`, and edge-invocation. An agent declares each **use** with its specific scope
(`uses: [{capability, operations, resources}]`), so `needed = ⋃(per-use scopes) ∪ edge-invoke scopes`.
The **approved-capability registry declares each capability's ceiling** (maximum grantable scope); every
per-use scope MUST be ⊆ that ceiling. The validator flags over (`granted ∖ needed`), under (a declared
use not granted), and ceiling-violation. The claim is **necessary-and-sufficient for the declared uses**;
whether the code matches the declaration is a **read-only runtime drift-check + human review**, not an
IAM HITL runs. Per-use scoping is required at Tier 2+.

**Alternatives and their cost.**
- *v1 global-tool-scope model.* Cost: manufactures false over/under-privilege; no home for non-tool
  capabilities; can't establish necessity (Codex B4).
- *Narrow the claim to "declaration consistency" only.* Cost: honest but weaker — loses per-use minimality
  and the ceiling guarantee (was the alternative; rejected by product owner in favour of the full model).
- *HITL derives necessity from the code itself.* Cost: requires running/statically-analysing the runtime
  = becomes the IAM plane, crossing ADR-5.

**Consequences.** (+) A real per-use necessary-and-sufficient claim within declared uses; non-tool
capabilities modeled; ceilings prevent silent over-grant. (−) Per-use scoping is authoring burden (scoped
to Tier 2+); runtime fidelity is explicitly out of scope (drift-check territory), so the claim is
qualified by "for the declared uses."

---

## ADR-10 (D10): Interaction identity — stable `id`, not domain-pair matching

**Status:** Accepted (added 2026-07-18, Codex M1/M2).

**Context.** Two legitimate interactions can exist between the same domain pair (a sync call *and* an
audit event). Keying dedup/cycle detection on the `(from, to)` pair (v1) both false-blocks that pair as
"double representation" and can't tell one logical interaction represented twice from two distinct ones.

**Decision.** Every interaction carries a stable, unique `id`. Double-representation and cycle detection
key off `id`. A `depends_on` projection collapses to domains only for a coarse dependency view.

**Alternatives and their cost.** *Domain-pair keys (v1)* — cost: the false-positive/false-negative above.
*Content-hash identity* — cost: unstable across edits, breaks cross-references.

**Consequences.** (+) Distinct interactions between a pair are first-class; cycle logic is precise.
(−) Authors must assign stable ids (validated unique).

---

## ADR-11 (D11): Reliable one-way events as `kind: event` + async; no broker exactly-once

**Status:** Accepted (added 2026-07-18, Codex B5).

**Context.** v1 declared all events best-effort and said reliable hops must be request/response facades —
making a durable one-way event (order-created: at-least-once, DLQ, replay, no response) unrepresentable.
v1 also offered `exactly_once` delivery, which is not achievable at the broker boundary (CR-12).

**Decision.** A reliable one-way event is `kind: event` + an `async` block. `delivery ∈ {at_most_once,
at_least_once}` only; end-to-end exactly-once = `at_least_once` + a declared **idempotent consumer**, not
a delivery flag. Sagas declare **per-step** compensation with a coordinator and compensation-failure
handling.

**Alternatives and their cost.** *Keep events best-effort only* — cost: can't model the most common
reliable async pattern. *Offer broker `exactly_once`* — cost: a guarantee no broker delivers; misleads
implementers (CR-12).

**Consequences.** (+) Reliable one-way events representable; the exactly-once claim is honest;
compensation is per-side-effect. (−) More async fields to author and value-check.

---

## ADR-12 (D12): Evals — govern coverage + adapter contract; ship no runner

**Status:** Accepted (added 2026-07-18, Codex B3, F3).

**Context.** CR-8/16/20 require independently testable components/edges/segments. Shipping an eval
*engine* would cross governs-not-runtime (ADR-5); leaving evals as prose (v1) is unbuildable.

**Decision.** HITL governs **coverage + gating**: a target model (components ∪ interactions ∪ segments),
a coverage validator (every target has an eval spec or an unlapsed waiver), a waiver schema, and a
**runner-adapter contract** (`eval_adapter: {command, inputs, result_schema}`) HITL invokes into the
*product's* runner, ingesting schema'd results + reviewer approval. A baseline generator seeds specs.

**Alternatives and their cost.** *Ship an eval runner* — cost: crosses ADR-5; couples to a framework.
*Prose only (v1)* — cost: unbuildable (Codex B3). *No coverage gate* — cost: "independently testable"
is unverifiable.

**Consequences.** (+) CR-8/16/20 become buildable and gated while the runtime stays the product's; PM
can invoke one segment via the adapter. (−) Requires a declared adapter the product implements; HITL
records coverage, not results-truth.

---

## Decision index

| ADR | HLD decision | One-line |
|---|---|---|
| ADR-1 | D1 | Component = manifest domain (+`kind`) |
| ADR-2 | D2 | **Edge = extended `interaction_matrix` entry** (v2); facade = the contract; `calls` deleted |
| ADR-3 | D3 | Topology/privilege/tool posture are generated views (machine-readable + rendered) |
| ADR-4 | D4 | Framework-agnostic; implementations are examples only |
| ADR-5 | D5 | Governs, not runs; boundary hook stays design-time |
| ADR-6 | D6 | Capability menu always presented; recommend, never decide |
| ADR-7 | D7 | Determinism boundary derived + fail-closed validated (per data leg) |
| ADR-8 | D8 | Extend the schema map form; payload = `signature` |
| ADR-9 | D9 | **Scoped-capability privilege** (v2): per-use scopes + registry ceilings; N&S for declared uses |
| ADR-10 | D10 | Interaction identity — stable `id`, not domain-pair matching |
| ADR-11 | D11 | Reliable one-way events as `kind: event` + async; no broker exactly-once |
| ADR-12 | D12 | Evals — govern coverage + adapter contract; ship no runner |
