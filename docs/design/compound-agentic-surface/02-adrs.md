# Compound Agentic System Surface: Architecture Decisions

> ADRs formalizing decisions **D1–D13** from [`01-design.md`](01-design.md) §11. Each records the forces,
> the decision, the **alternatives with their concrete cost**, and the consequences. **v3.2** — the
> **round-2** review rewrote ADR-2/7/9/10/11/12 and added ADR-13; the **round-4** review (2026-07-22) drove
> the **core scope lock** ([`../agentic-core-scope.md`](../agentic-core-scope.md)), which **amends ADR-11**
> (saga → declared-only + advisory) and **ADR-12** (eval → agent+e2e core, universal coverage deferred);
> see [`04-revision-plan.md`](04-revision-plan.md).
> EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status: **accepted, core-lock applied, pending Codex re-review (round 5)**.

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

## ADR-2 (D2): An edge IS an element of a new top-level `interactions` list (v3 — rewritten)

**Status:** Accepted (rewritten 2026-07-20 after Codex round-2 B1; supersedes the v2 "edge = extended
`interaction_matrix` entry" decision, which could not represent parallel edges).

**Context.** Every inter-component call and A2A edge must be a declared, reviewed, boundary-enforced
contract. The manifest already has `interaction_matrix: map["from -> to", InteractionEntry]`. v2 decided
the edge *was* an extended entry in that map, keyed by the domain pair, and claimed a stable `id` inside
the value would let two edges (a `sync_call` **and** an `event`) coexist between the same pair. A map has
**one value per key**, so this is structurally impossible — the second edge overwrites the first (Codex
B1). The whole "parallel interactions are first-class" claim was therefore undeliverable in the map.

**Decision.** The authoritative edge model is a **new, additive, top-level `interactions` list** whose
element identity is a stable, unique `id`. Each element carries explicit `from`/`to`, `kind`
(`sync_call | async_task | event`), a `facade` reference (facade_ref for call/task, event_ref for event),
request/response/event **trust legs**, an **authorization** block, and an `async` block. **Two edges
between the same pair are two list elements** — trivially representable. `interaction_matrix`,
`depends_on`, and `events_emitted`/`events_consumed` become **derived projections** of this list
(regenerate-and-diff); when a manifest has no `interactions` list, they keep their legacy meaning
untouched (so the change is additive, ADR-13).

**Alternatives and their cost.**
- *Extend `interaction_matrix` in place (v2).* Cost: the map key is the domain pair, so it cannot hold
  parallel edges no matter what fields the value carries (Codex B1); the SEP-PAIR fixture is
  unconstructable.
- *Mutate `interaction_matrix` from a map into a list.* Cost: a **breaking** change to a shipped field —
  every existing manifest's `interaction_matrix` would have to be migrated, violating additive-only
  (Codex B5). The new-list approach leaves legacy manifests untouched.
- *Edge = facade_api (v1).* Cost: a facade is callee-side and single-contract; it can't home the caller's
  trust obligations, the response-leg validation, or who-may-invoke.

**Consequences.** (+) One authoritative, human-authored edge model in which parallel edges, stable
identity, trust legs, authorization, and async all work; the legacy map/`depends_on`/`events_*` become
generated views that cannot disagree with it. (−) A generator must derive the projections and CI must
regenerate-and-diff; the boundary hook extends to the static interaction-contract check (LLD §6.4); the
pre-existing facade list→map disagreement (ADR-8) still must be reconciled.

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

## ADR-7 (D7): The determinism boundary is derived and validated per data leg (v3 — rewritten)

**Status:** Accepted (rewritten 2026-07-20 after Codex round-2 B2; supersedes the per-edge phrasing, which
put cost/authority only on the response leg and compared authority to the callee).

**Context.** The seam between deterministic components and stochastic agents is where a stochastic output
corrupts a deterministic system, or cost/authority leaks into an agent. v2 attached the controls to "the
edge" and to the response leg only: a deterministic caller's *request* into an agent had nowhere to bound
cost/authority, `authority_bound` was compared to the callee even when the stochastic consumer was the
caller, and agent→agent fan-out fell outside the "det→agent" rule entirely (Codex B2).

**Decision.** The invariant is applied to each **data-carrying leg** (request, response, event), using
that leg's derived **(source, consumer)**. If the **consumer** is stochastic, the leg requires bounded
cost **and** bounded authority, and `authority_bound ⊆ the consumer's` granted privilege. If the consumer
is deterministic and the source stochastic, the leg requires validation. A fail-closed validator enforces
this from declared `kind`s and the leg fields.

**Alternatives and their cost.**
- *Per-edge, response-leg-only (v2).* Cost: no home for request-leg delegation bounds; authority compared
  to the wrong identity; agent→agent unbounded (Codex B2).
- *Leave it as a design-review checklist.* Cost: unenforced, silently skipped under deadline pressure.

**Consequences.** (+) A checkable, fail-closed invariant at every seam, in both directions, including
agent→agent; authority is always bounded against the *actual* stochastic consumer. (−) Depends on
component `kind`s being declared accurately, and every stochastic-consumer leg must carry two more fields.

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

## ADR-9 (D9): Scoped-capability privilege — closed over tools, memory, non-tool capabilities (v3 — rewritten)

**Status:** Accepted (rewritten 2026-07-20 after Codex round-2 B3; supersedes the v2 model, whose union
was not closed — memory was declared but never joined, edge-invokes bypassed ceilings, and resource-less
uses produced grammar-invalid scopes).

**Context.** CR-14 wants necessary-and-sufficient privilege. v2 introduced per-use scopes and registry
ceilings — the right direction — but the union `needed` was not actually closed over its declared sources:
`memory.reads/writes` were declared but never entered `needed`; `invoke:<target>` was added *after* the
ceiling check so edge invocation bypassed ceilings; a use with omitted `resources` produced a bare `op`
that fails the `action:resource` scope grammar; ceilings were exact-membership so a resource family could
not be expressed; and CR-15's tool registry silently disappeared into generic capabilities (Codex B3/M9).

**Decision.** A **scoped-capability** model whose union is closed over exactly three declared sources:
**tools, memory, and non-tool `capabilities`** — all as per-use `uses: [{capability, operations,
resources}]`. **Memory reads/writes are declared as memory-class `uses`** and cross-checked against the
`memory` block, so memory enters `needed` through the same union. **Edge-invocation is removed from the
privilege set**: "who may invoke agent B" is an authorization question governed by B's
`authorization.allowed_callers` (ADR-2/§6.4), not by A's identity grant. A use with omitted resources
contributes `op:*` (a grammar-valid wildcard). The registry declares each capability's **ceiling**;
containment uses **wildcard semantics** (`read:cust/*` covers `read:cust/profile`). The validator flags
`over = granted ∖ needed`, `under = needed ∖ granted`, and `ceiling-violation`. **Tools are the
`class: tool` capabilities** (CR-15 fold-in): the tool registry is those rows, the tool declaration is the
tool-class `uses`, the gate is the same validator, and a `runtime_ref` preserves the runtime allow-list
mapping. The claim is **necessary-and-sufficient for the declared uses**; runtime fidelity is a read-only
drift-check + human review. Per-use resource scoping is required at Tier 2+ (tier is a validator input;
absent ⇒ highest tier).

**Alternatives and their cost.**
- *v2 four-source union with invoke inside it.* Cost: invoke bypassed ceilings and had no registry entry;
  memory was unjoined; bare-`op` scopes failed the grammar (Codex B3).
- *Keep CR-15 as a separate tool registry + tool model.* Cost: two overlapping privilege systems (tools
  vs capabilities) with no reconciliation — the duplication ADR-2 exists to avoid; folding tools in as a
  class with `runtime_ref` keeps one model and still preserves the runtime mapping.
- *HITL derives necessity from the code itself.* Cost: requires running/statically-analysing the runtime =
  becomes the IAM plane, crossing ADR-5.

**Consequences.** (+) A real per-use necessary-and-sufficient claim, closed over its declared sources, with
memory joined and tools preserved; ceilings with wildcards prevent silent over-grant without enumeration;
invocation authority lives in one place (authorization). (−) Per-use scoping is authoring burden (scoped to
Tier 2+); the claim is qualified by "for the declared uses," with runtime fidelity out of scope.

---

## ADR-10 (D10): Interaction identity — the `id` is the list element key (v3 — rewritten)

**Status:** Accepted (rewritten 2026-07-20 after Codex round-2 B1; supersedes v2, which placed the `id`
inside a domain-pair-keyed map value — where it could not create a second entry for the pair).

**Context.** Two legitimate interactions can exist between the same domain pair (a sync call *and* an
audit event). v2 gave each an `id` but kept them inside `interaction_matrix`, a map keyed by the pair — so
the `id` distinguished nothing the map could store (Codex B1). Identity is only real if it is the
container's key.

**Decision.** Interactions live in a **list**; each element's stable, unique `id` **is** its identity
(ADR-2). Reference resolution, parallel-edge distinction, event reconciliation, saga steps, and dedup all
key off `id`. **Cycle detection keys off the graph's domain vertices and directed `from→to` endpoints**
(not the id — ids distinguish parallel edges, not whether a cycle exists); the id is for reference and
dedup. `depends_on` is a coarse domain-level projection.

**Alternatives and their cost.** *Id inside a pair-keyed map (v2)* — cost: the map still holds one edge
per pair, so the id is inert (Codex B1). *Content-hash identity* — cost: unstable across edits, breaks
cross-references.

**Consequences.** (+) Distinct interactions between a pair are genuinely first-class; references and
sagas have a stable key; cycle logic is correct because it uses endpoints, not ids. (−) Authors assign and
maintain unique ids (validated).

---

## ADR-11 (D11): Reliable one-way events + top-level id-keyed sagas; no broker exactly-once (v3 — rewritten)

**Status:** Accepted, **amended 2026-07-22 (v3.2 core scope lock, Codex round-4 B4).** The reliable-event
model stands. The **saga required-when model is deferred to a follow-on** — round-4 found the
segment↔saga identity, overlap, parallel-compensation, and requiredness-inference underspecified and not
yet sound. In core, HITL **validates declared sagas' well-formedness** and raises a **`check_compensation_gap`
advisory** (`warning`, never a blocker) when a flow looks like it needs compensation but declares none.
The "≥2 side-effecting interactions and no covering saga is a **blocker**" clause below is **superseded** by
that advisory. See [`../agentic-core-scope.md`](../agentic-core-scope.md).
(Rewritten 2026-07-20 after Codex round-2 B6/M3/M4; supersedes v2, which nested the saga inside one
interaction's `AsyncSpec` and left ownership/order/requirement undefined.)

**Context.** A durable one-way event (at-least-once, DLQ, replay, no response) must be representable, and
`exactly_once` must not be offered at the broker boundary (CR-12). v2 got the event shape right but nested
`saga` inside a single interaction's async block, while its steps referenced *multiple* interaction ids —
so which interaction owned the saga, the forward/compensation order, and when a saga was *required* were
all undefined (Codex M3). Async combinations (at_most_once + retry, missing DLQ) were also unconstrained
(M4).

**Decision.** A reliable one-way event is `kind: event` + an `async` block; `delivery ∈ {at_most_once,
at_least_once}` only; end-to-end exactly-once = `at_least_once` + a declared **idempotent consumer**
(`consumer_idempotent` + `idempotency_key`), never a delivery flag. Async combinations are value-checked:
`async_task` requires `async`; `retry` is forbidden with `at_most_once`; `at_least_once` requires a DLQ
unless justified. **Sagas are a top-level, id-keyed list** (not nested on an edge): each has a
coordinator, a forward `order`, and `steps` referencing the **interaction ids** of the side-effecting
interactions it spans; compensation runs in reverse `order` and must itself be idempotent. **~~A flow with
≥2 side-effecting interactions and no covering saga is a blocker~~** — *superseded (v3.2/B4): this is now a
`check_compensation_gap` **advisory** (`warning`), not a blocker; the required-when enforcement model is
deferred.* "Side-effecting" is derived from the facade `mutations` (or declared), so the advisory is
checkable.

**Alternatives and their cost.** *Nest the saga on one interaction (v2)* — cost: undefined ownership, no
stable saga identity, ambiguous order, and no way to state when a saga is required (Codex M3). *Keep
events best-effort only (v1)* — cost: can't model the most common reliable async pattern. *Offer broker
`exactly_once`* — cost: a guarantee no broker delivers; misleads implementers (CR-12).

**Consequences.** (+) Reliable one-way events representable; the exactly-once claim is honest; declared
sagas have one owner, a stable id, and a defined order; compensation is per-side-effect and idempotent; a
flow that likely needs compensation but omits it is **surfaced as a warning** rather than silently passed
(the honest "we don't enforce this yet" signal). (−) The full required-when enforcement is deferred, so a
team can ship an under-compensated flow with only a warning — an accepted core limitation, tracked in the
follow-on.

---

## ADR-12 (D12): Evals — govern coverage + a wired adapter contract; ship no runner (v3 — rewritten)

**Status:** Accepted, **amended 2026-07-22 (v3.2 core scope lock, Codex round-4 M1/O6).** The target model
below is **narrowed for core**: mandatory coverage = **every agent component + one e2e segment** (CR-8/CR-16
independent per-agent eval), *not* every deterministic component and edge. The round-3 broadening to "every
component ∪ every interaction" reintroduced the over-governance the Advisor exists to prevent (O6) and is
**superseded**. Deterministic coverage is **optional** (a team may opt in with a `contract_test` spec);
**universal deterministic coverage is a deferred follow-on**. The index/waiver/approval/adapter machinery is
unchanged. See [`../agentic-core-scope.md`](../agentic-core-scope.md).
(Rewritten 2026-07-20 after Codex round-2 B4; supersedes v2, whose target model and adapter had no schema
home and no wire protocol.)

**Context.** CR-8/16/20 require independently testable components/edges/segments. Shipping an eval
*engine* would cross governs-not-runtime (ADR-5); leaving evals as prose (v1) is unbuildable. v2 named a
coverage validator and an adapter but read a `segments` field the schema never defined, put no `evals` on
interactions, defined no eval index / waiver file / reviewer-approval schema, and left the adapter as
`{command, inputs, result_schema}` with no argv/target-binding/result/exit-code contract — so nothing was
implementable (Codex B4).

**Decision.** HITL governs **coverage + gating** with real homes. **Core mandatory target model (v3.2):
every agent domain + one `e2e:true` segment** — independent per-agent eval plus one end-to-end flow.
Deterministic components/edges are **optional** targets (opt in with a `contract_test` spec, then
validated). Interactions may still carry `evals`, and the top-level `segments` list (including `e2e` flows)
is unchanged; universal deterministic coverage is a deferred follow-on. Supporting machinery: an eval
**index** (`{target_type, target_id, spec_path}`, unique per target); a **waiver file**; a per-spec
**approval block** (`reviewer`, `date`, `decision`), distinct from authorship `status`; and a **fully
wired runner-adapter contract** (`eval-adapter.yaml`: argv, cwd, timeout, target/spec binding, result
location + JSON Schema, pass/fail exit codes; any other outcome is a fail-closed adapter error). HITL
invokes the adapter **only on explicit operator confirmation** (the `ops-apply-iac` model), ingests
schema'd results, and records the reviewer's approval. A specified baseline generator seeds specs
(deterministic case ids, owning-FR/failure-mode sources, merge-by-id preserving human edits).

**Alternatives and their cost.** *Ship an eval runner* — cost: crosses ADR-5; couples to a framework.
*Prose-only target model (v2)* — cost: validator reads undefined fields; adapter unimplementable (Codex
B4). *No coverage gate* — cost: "independently testable" is unverifiable.

**Consequences.** (+) CR-8/16/20 become buildable and gated while the runtime stays the product's; a PM
can invoke one segment via the adapter on confirmation; approval (not mere authorship) is what the gate
reads. (−) Requires a declared adapter the product implements, an eval index/waiver/approval to maintain,
and a baseline generator; HITL records coverage, not results-truth.

---

## ADR-13 (D13): Per-check activation — each validator + registry activates only on its own data

**Status:** Accepted (added 2026-07-20, Codex round-2 B5).

**Context.** v2 used a single global "agentic marker" gate: if the manifest had *any* new marker (even
`kind: deterministic` or a typed deterministic `sync_call`), it ran **all** checks — and then failed a
wholly deterministic two-service manifest for a missing `approved-capabilities.yaml`. The stated boundary
is stronger: a non-agentic manifest must validate **without any new registry**. The global gate refuted
it (Codex B5).

**Decision.** There is **no** global gate. Each check has an **activation predicate** over the data it
governs, and loads its registry **only when it activates** (LLD §6.0): `check_capabilities` activates only
when a domain has `uses`/`identity`/agent `kind`; `check_boundary_legs` only when an interaction touches
an agent; `check_async` only on async/event/saga data; and so on. A legacy manifest activates nothing; a
deterministic manifest with typed `interactions` activates only graph-integrity checks and needs **no**
capability/policy/store/eval registry.

**Alternatives and their cost.** *Global marker gate (v2)* — cost: forces registries onto non-agentic
manifests, refuting additive-only (Codex B5). *Always run every check* — cost: same, worse. *Infer
activation heuristically* — cost: unpredictable; a check might silently skip when it should run.

**Consequences.** (+) "Additive-only; non-agentic manifests need no registry" is literally true, per data
kind; a manifest pays only for the machinery it uses. (−) Each check must declare and test its activation
predicate (and its skip is explicit, not vacuous-pass), which the suite covers (test A3).

---

## Decision index

| ADR | HLD decision | One-line |
|---|---|---|
| ADR-1 | D1 | Component = manifest domain (+`kind`) |
| ADR-2 | D2 | **Edge = element of a new top-level `interactions` list** (v3); the pair-keyed map/`depends_on`/`events_*` are derived projections |
| ADR-3 | D3 | Topology/privilege/tool posture are generated views (machine-readable + rendered) |
| ADR-4 | D4 | Framework-agnostic; implementations are examples only |
| ADR-5 | D5 | Governs, not runs; boundary hook stays design-time |
| ADR-6 | D6 | Capability menu always presented; recommend, never decide |
| ADR-7 | D7 | **Determinism boundary per data leg** (v3), bounded against the leg's actual stochastic consumer |
| ADR-8 | D8 | Extend the schema map form; payload = `signature` |
| ADR-9 | D9 | **Scoped-capability privilege** (v3): closed over tools/memory/non-tool caps; invoke → authorization; wildcard ceilings; CR-15 fold-in |
| ADR-10 | D10 | **Interaction identity — the `id` is the list element key** (v3); cycles key off endpoints |
| ADR-11 | D11 | **Reliable events + top-level id-keyed sagas** (v3); **core validates declared sagas + a compensation-gap advisory; required-when model deferred** (v3.2/B4); no broker exactly-once |
| ADR-12 | D12 | **Evals — coverage + a fully wired adapter contract** (v3); **core = per-agent + e2e; universal deterministic coverage deferred** (v3.2/M1); ship no runner |
| ADR-13 | D13 | **Per-check activation** (v3): each validator + registry activates only on its own data |
