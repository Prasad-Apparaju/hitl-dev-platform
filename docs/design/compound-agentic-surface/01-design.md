# Compound Agentic System Surface: Design (HLD) — v3.3 (#10 core; Advisor decoupled per the 2026-07-23 re-scope)

> Mechanism (the *how*) for the requirements in
> [`../../01-product/compound-agentic-surface/requirements.md`](../../01-product/compound-agentic-surface/requirements.md)
> (CR-1..CR-20). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). **v3.2** —
> the round-2 review rewrote the edge/leg/privilege/eval model; the **round-4** review (2026-07-22) drove
> the **core scope lock** ([`../agentic-core-scope.md`](../agentic-core-scope.md)): eval coverage → per-agent
> + e2e (universal deferred); saga → declared-only + compensation-gap advisory (required-when deferred);
> CR-6 sync reliability narrowed; delegated authority deferred. Per [`04-revision-plan.md`](04-revision-plan.md).
> Status: **draft, #10 core stable; the Advisor no longer authors this manifest (2026-07-23 re-scope) — #10 ships first as 2.2.0; pending Codex re-review (round 9)**. Targets **2.2.0**. Field-level
> precision + validator signatures are in the LLD [`03-lld.md`](03-lld.md); decisions in [`02-adrs.md`](02-adrs.md).

**Thesis (unchanged): a compound agentic system is a manifest, extended.** Each revision corrects *which*
manifest structures carry it. The round-2 review found that v2's fixes were partly asserted rather than
delivered; the load-bearing miss was structural: v2 tried to carry two edges between the same domain pair
inside `interaction_matrix`, a **map keyed by the pair**, which is impossible. v3 changes the structures
so the properties are actually realizable, and states each boundary honestly.

**Governing principle:** HITL validates **declarations, coverage, and consistency — not runtime
behavior.** Where a claim needs runtime truth (actual privilege use, actual eval results), the framework
validates the *declaration* and pushes runtime fidelity to a read-only drift-check + human review. This
keeps every mechanism inside governs-not-runtime (ADR-5).

## 1. The system model

- **Nodes = domains**, extended with `kind`: `deterministic | simple_agent | deep_agent`.
- **Edges = a new top-level `interactions` list** (not the existing `interaction_matrix` map). Each
  interaction is a list element with a stable `id`, explicit `from`/`to`, `kind`, a `facade` reference,
  request/response trust legs, authorization, and async reliability. Because element identity is the `id`,
  **two edges between the same pair are two elements** — the property v2 could not deliver (B1).
- **`interaction_matrix`, `depends_on`, and `events_emitted`/`events_consumed` become derived
  projections** of the `interactions` list (regenerate-and-diff). When a manifest has no `interactions`
  list, these keep their existing legacy meaning untouched — the change is additive (B5).
- **Orchestration** declared at system level (pattern + justification + coordinator + `cycle_bound`),
  since it is not derivable from nodes and edges (CR-11).

## 2. The interaction model (the core v3 change, B1)

Why a new list rather than extending the map: a map has one value per key, so `interaction_matrix["a ->
b"]` can hold exactly one edge. Real systems have parallel edges (a synchronous call *and* an audit event
between the same two domains). The authoritative edge model is therefore a **list** keyed by a stable,
unique interaction `id` (LLD §2). Each element carries:

- **`id`, `from`, `to`, `kind`** (`sync_call | async_task | event`).
- **`facade`** — a reference to the callee's declared `facade_apis` entry for a call/task (`signature` =
  the payload contract), or an `event_ref` (`producer:event_name`) for an event. The two reference kinds
  have distinct grammars so they cannot be confused (LLD §0, m2). For events, the reference reconciles
  **exactly** with the producer/consumer `events_*` lists by the interaction id (LLD §2.4, M2) — the
  legacy event lists are a generated view of the interaction, not a second source.
- **Request / response / event trust legs (B2).** Each data leg carries the *same* struct
  (`validation`, `cost_bound`, `authority_bound`), and the validator derives the leg's **(source,
  consumer)** and applies the boundary rule to that leg's *actual consumer* (§3). This fixes v2, where
  cost/authority lived only on the response leg and authority was always compared to the callee.
- **`authorization` (B2, CR-13)** — who may invoke, as **non-human identity**: `allowed_callers` are
  domains that must each declare an `identity.principal`; `credential_mode` defaults to `jit` and a
  `static`/`none` mode must be justified. Graph membership is not authorization.
- **`async` reliability block** — present for `async_task` and reliable `event` (§5).
- **`side_effecting`** — marks an interaction with irreversible effects (default derived from the
  facade's `mutations`); the saga model reads it (§5).

Reference-integrity (LLD §6.6): every `facade`/target resolves to a real domain+facade; every
`allowed_callers` entry is a real domain with an identity; event references reconcile; a pair authored in
both `interactions` and the legacy map is a blocker (one source of truth).

**A2A Agent Card / Task mapping, and what the hook actually enforces (CR-5, M11) — stated honestly.** The
manifest governs the *governance* slice of an A2A Agent Card, not the whole card: the callee's
`facade_apis` entry is the **capability + Task payload contract** (`signature` = the Task shape,
`preconditions`/`error_modes` = the guarantees), and the interaction's `authorization` is the who-may-call
decision. The card's **protocol/endpoint/transport/security-scheme/version** are the product's **runtime**
configuration, not manifest fields — HITL does not model them (governs-not-runtime). The design-time
`check-domain-boundary.sh` hook is likewise honest about its reach: it is a **static contract check** — at
Edit/Write time it flags a cross-domain reference that has no declared `interactions` entry + facade, and
an `interactions` entry whose facade does not resolve. It **cannot** observe a live A2A call; runtime
allow-listing is the product's guardrail layer (CR-15 `runtime_ref`). So CR-5 is delivered as "the
governed contract is declared, reference-checked, and boundary-hooked at design time," not as runtime A2A
enforcement.

## 3. The determinism boundary (CR-4, B2) — per leg, consumer-derived

The boundary is derived from node `kind` and applied to each **data-carrying leg** (request, response,
event), using that leg's own (source, consumer):

- **consumer is stochastic** (an agent) ⇒ the leg MUST declare **bounded cost** and **bounded authority**,
  and the `authority_bound` MUST be ⊆ **that consumer's** granted privilege. This is delegation into an
  agent, so it applies to a deterministic caller's *request* into an agent, a deterministic callee's
  *response* back to an agent caller, **and agent→agent** (the consumer is stochastic regardless of the
  source) — closing v2's unbounded-fan-out gap (M10).
- **consumer is deterministic and source is stochastic** ⇒ the leg MUST declare **validation** of the
  stochastic data before the deterministic side trusts it.
- **both deterministic** ⇒ no boundary control.

All validation/bound references are typed and existence-checked (LLD §6.3/§6.8): a `validation` resolves
to a `schema`/`guardrail` policy, a `cost_bound` is a `QuantPolicy`, an `authority_bound` is scopes ⊆ the
consumer's grant.

## 4. Scoped-capability privilege (F1, CR-14, B3)

A genuine necessary-and-sufficient claim **at declaration granularity**, honest about its runtime limit.

- **Capability sources for the privilege claim (complete and closed):** `tools`, `memory` access, and
  non-tool **`capabilities`** (KMS, model-endpoint, delegation, ambient fs/network/process/env, direct
  service access) — all declared as per-use `uses` entries. **Memory reads/writes are declared as memory-
  class `uses` and cross-checked against the `memory` block** (LLD §3.1), so memory enters `needed`
  through the same union (fixes v2, where memory was declared but never joined, B3).
- **Edge-invocation is *not* an identity grant.** "May domain A invoke agent B" is an **authorization**
  question, governed by B's `authorization.allowed_callers` (§2, LLD §6.4), not by A's privilege set.
  Removing it from the privilege union closes v2's "invoke bypasses ceilings" contradiction (B3).
- **Per-use scoping:** each *use* declares `{capability, operations, resources}`; `needed = ⋃(per-use
  scopes)`. A read-only use of a read/write capability needs only `read:…`. A use with omitted resources
  contributes `op:*` — a **grammar-valid** wildcard scope (fixes v2's bare-`op` invalid scope, B3).
- **Registry = ceiling:** the approved-capability registry declares each capability's **maximum**
  grantable scope; every per-use scope MUST be ⊆ that ceiling under **wildcard containment** (`read:cust/*`
  covers `read:cust/profile`), so a ceiling can express a resource family without enumeration.
- **Tools (CR-15) are the `class: tool` capabilities.** The approved-tool registry is those rows; the
  per-agent tool declaration is the tool-class `uses`; the gate is `check_capabilities` on them; a
  generated **tool matrix** is the `class:tool` projection; a `runtime_ref` preserves the runtime allow-
  list mapping the product enforces. This is a documented fold-in, not a silent drop (M9).
- **Validator (LLD §6.2):** `over = granted ∖ needed`, `under = needed ∖ granted` (both under wildcard
  containment), `ceiling-violation = a per-use scope ⊄ its ceiling`. Posture generated **machine-readable
  + rendered**.
- **Tier-proportionate:** per-use resource scoping is required at **Tier 2+**; lower tiers may declare
  capability-level `uses` (no resources ⇒ `op:*`), so it does not become box-ticking. Tier is a validator
  input (from the change-file breadcrumb; absent ⇒ highest tier, fail-safe).
- **Honest limit (ADR-5):** proves the *declared* per-use set is minimal, consistent, and within ceiling.
  It does **not** prove the running code matches the declaration — that is a **read-only runtime
  drift-check** + human review, never an IAM HITL runs.

## 5. Async reliability, events, sagas (CR-12, B6/M3/M4)

- A **reliable one-way event** is `kind: event` + an `async` block (delivery, DLQ, replay, idempotency).
  Fire-and-forget events omit reliability. `delivery ∈ {at_most_once, at_least_once}` — **`exactly_once`
  is not offered** at the broker boundary (CR-12); end-to-end exactly-once = `at_least_once` + a declared
  **idempotent consumer** (`consumer_idempotent` + `idempotency_key`), not a delivery flag.
- **Value-checked combinations (LLD §6.7, M4):** `async_task` requires an `async` block; `retry` is
  forbidden with `at_most_once`; `at_least_once` requires a DLQ unless justified; timeouts are positive.
- **Sagas are a top-level, id-keyed model (LLD §4.2, M3)** — not a string nested on one edge. A `saga`
  has a coordinator, a forward `order`, and `steps` referencing the **interaction ids** of the
  side-effecting interactions it spans; compensation runs in reverse order and must itself be idempotent.
  **Core disposition — validate declared, advise on gaps; required-when model deferred (v3.2/B4).** Round-4
  found the saga *required-when* model (segment↔saga identity, overlap, parallel compensation, requiredness
  inference) not yet sound, so the core **defers the enforcement model** ([`../agentic-core-scope.md`](../agentic-core-scope.md))
  and instead: (a) `check_saga` validates every **declared** saga's well-formedness; (b) a
  **`check_compensation_gap` advisory** (`warning`, never a blocker) fires when a flow has ≥2 side-effecting
  agent/async interactions and no covering saga — the honest *"looks like this needs distributed
  compensation, which the core doesn't enforce yet"* signal that closes the "silent omission" hole. A
  **synchronous, deterministic** flow triggers neither (a database-transaction concern). The Advisor (FR-28)
  elicits *whether* a flow needs distributed compensation up front so the advisory is rarely a surprise.
- **Sync vs async reliability boundary (CR-6, ADR-5).** The design value-checks the reliability *contract*
  that cannot be a plain retry — **async** delivery/idempotency/DLQ/replay and cross-flow compensation
  (sagas). A **synchronous** call's own timeout/retry is product **runtime** config (like a connection
  pool), so HITL does not schema-validate a timeout number; the sync cross-hop failure mode is *surfaced*
  through the callee facade's `error_modes` and bounded by the leg's `cost_bound`/`cycle_bound`. **Honest
  narrow (v3.2/M5):** a **design-time sync timeout/retry declaration** check is **deferred** — the core does
  not claim to capture sync reliability "on the legs." CR-6's failure modes that the core *does* capture at
  design time: non-determinism propagation → boundary legs; async timeout/retry → the async contract; cycles
  → `cycle_bound`; fan-out cost → consumer-stochastic `cost_bound`; cross-agent trust → authorization. Sync
  timeout/retry *values* remain product runtime.

## 6. Eval coverage + adapter (F3, CR-8/16/20, B4)

HITL governs **coverage and gating**; the product runs the evals (governs-not-runtime).

- **Core targets = every agent + one e2e segment (v3.2/M1).** The **coverage validator** blocks an
  **agent** component with no eval spec and no unlapsed waiver, and requires at least one `e2e:true` segment
  for a multi-agent system — this is CR-8/CR-16's *independent per-agent eval*, without the over-governance
  of requiring a spec for every deterministic component and edge (the round-3 broadening round-4 flagged as
  an O6 violation). Deterministic components/edges are **optional** targets (opt in with a `contract_test`
  spec); **universal coverage is a deferred follow-on** ([`../agentic-core-scope.md`](../agentic-core-scope.md)).
  Targets have real homes (LLD §7): agent domains, interactions (each may carry `evals`), and declared
  `segments` (a top-level list of routes, including `e2e:true` flows).
- **Registry + waivers + approval (LLD §7.1/§7.2):** an eval **index** (`{target_type, target_id,
  spec_path}`, unique per target), a **waiver file** (owner, reason, tier-limit, revisit), and an
  **approval block** on each spec (`reviewer`, `date`, `decision`). `status: baseline|extended` is
  authorship maturity; `approval.decision` is the gate — `baseline_only` does not satisfy coverage above
  Tier 1.
- **Runner-adapter contract fully wired (LLD §7.3):** `eval-adapter.yaml` specifies argv, cwd, timeout,
  how the target/spec is bound (arg/env/stdin), where the result is read (stdout/file), the result-schema
  to validate against, and pass/fail exit codes; any other outcome is a fail-closed adapter error. HITL
  invokes it **only on explicit operator confirmation** (the `ops-apply-iac` model), ingests schema'd
  results, and records reviewer approval. No runner ships.
- **Baseline generator (LLD §7.4, CR-20):** a specified function (path, signature, deterministic case
  ids) that seeds cases from the owning `FR-n` (via a domain `owning_fr`), facade contracts, boundary
  checks, and CR-6 failure modes; merges by case id preserving human-edited cases; a no-evals component
  is a recorded waiver; the workflow prompts the PM to own and approve.

## 7. Enforcement (LLD §6) — value-checks, fail-closed, per-check activated

Validators check **values and references, not mere presence**: `long_running:true` requires a real
durable checkpoint store + resume cursor + a meaningful cancellation mode (not `none`) + a `side_effect_key`
when a resumable step has side effects; a `deep_agent`'s subagents are references to declared domains with
durable filesystem/semantic memory; every `PolicyRef` resolves in `policies.yaml`; every store resolves in
`stores.yaml`. Each validator is fail-closed with a stable blocker code.

**Per-check activation (B5, resolves the additivity contradiction).** There is **no** global "agentic
marker" switch. Each check runs only when the data it governs is present, and loads its registry only
then (LLD §6.0). A legacy non-agentic manifest activates nothing and exits 0. A **deterministic** manifest
that adopts `kind: deterministic` + a typed `interactions` edge activates only the graph-integrity checks
and needs **no** capability/policy/store/eval registry — so "additive-only; non-agentic manifests need no
registry" is literally true, not merely true for untouched legacy files.

## 8. Generated views (CR-3/CR-14, M11)

Generated from the manifest + registries: a **topology/routing view** (nodes by `kind`; interaction legs
typed; boundary legs marked; `orchestration.pattern`; routes/segments), a **privilege-posture** output,
an **approved-capability matrix**, and a **tool matrix** (the `class:tool` projection, CR-15) — each
emitted **machine-readable (JSON/YAML) and rendered (Markdown)** with a schema version, deterministic
ordering, and a CI regenerate-and-diff. The derived `interaction_matrix`/`depends_on`/`events_*`
projections are regenerated the same way. Static only (ADR-5).

## 9. Memory, deep agents, lifecycle (CR-7/17/18, M5/M6/M7)

Declared per agent and **value-validated** (LLD §3.1–3.3/§6.9–6.11): long-term memory carries owner, a
**durable** store (ephemeral is rejected for long-term), retrieval mode, PII policy (explicit `none` needs
justification), and — for high-stakes writes — a guardrail and **write provenance**; reads may declare a
**staleness** bound; shared memory resolves `shared_store` through the store registry with one owner, and
every read/write reconciles to a privilege `use` (§4). Lifecycle requires meaningful durable
checkpoint/resume/idempotency/cancellation/human-gate values. Deep agents require a planner, subagents as
domain references (their capability description is the referenced domain's `purpose` + facades), gates,
guardrails, `context_isolation: true`, and durable filesystem/semantic long-term memory.

## 10. Observability + PM eval-console (CR-9/CR-16) — a floor gate (hard directive 2026-07-22)

Per the directive that a **PM eval console + live traces is a hard requirement**, the **design-time
declaration + gate** is now **in this package** (no longer deferred): every agentic system carries a
top-level **`observability`** block (LLD §4.3) — cross-hop tracing (OTel GenAI / OpenInference convention,
the traced hops, span attributes), a token-cost amplification budget, and a **PM eval-console** declaration
(the surface the PM uses to run evals + review results/traces, CR-16). **`check_observability`** (LLD §6.17)
is a **blocking floor gate**: a missing or incomplete declaration fails.

Split, honestly (governs-not-runtime, O1): **HITL ships** the declaration schema, the validator, the floor
gate, and the **static posture view** generated from the declaration. **The product builds** the running
trace backend + the live console + the eval execution — with the **companion product ([#21](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/21))** as the runnable reference. So HITL enforces
that the system is observable + PM-evaluable; it does not itself run the dashboard/eval engine. **#15**
keeps only the **runtime** posture-backend refinements (the existing token-cost registry measures *HITL
development-change* spend, not product-agent fan-out — the product extension lives there). The acceptance
gate (§13) now **includes CR-9**; **CR-1/CR-19 remain relocated to the Agentic Design Advisor (FR-28)**.

## 11. Decisions (v3 — locked as ADRs)

| # | Decision | Note |
|---|---|---|
| D1 | Component = manifest domain (+`kind`) | unchanged |
| **D2** | **Edge = element of a new top-level `interactions` list** (id + from/to + kind + facade + trust legs + authorization + async); `interaction_matrix`/`depends_on`/`events_*` are derived projections | **rewritten in v3** — the domain-pair *map* cannot hold parallel edges (B1); the list can |
| D3 | Topology/privilege/tool posture are generated views, machine-readable + rendered | unchanged |
| D4 | Framework-agnostic | unchanged (upheld) |
| D5 | Governs, not runs; validators + static views only | unchanged (upheld); anchors F1/F3 limits |
| D6 | Capability menu always presented; recommend, never decide | **relocated to the Agentic Design Advisor (FR-28)** — the menu is elicitation (was CR-19); ADR-6 stays as the recorded rationale |
| **D7** | Determinism boundary derived, applied **per data leg**, bounded against the leg's **actual stochastic consumer** | **strengthened in v3** (B2) |
| D8 | Extend the schema map form of `facade_apis`; reconcile the template | unchanged; scope enumerated in LLD (M9) |
| **D9** | **Scoped-capability privilege**: per-use scopes + registry ceilings; memory joined via `uses`; edge-invocation moved to authorization; N&S *for declared uses*; runtime = drift-check | **rewritten in v3** (B3) |
| **D10** | **Interaction identity**: stable `id` as the list element key; dup/cycle/reconciliation key off it | **rewritten in v3** — id is the *list key*, not a field inside a pair-keyed map (B1) |
| **D11** | **Reliable one-way events** as `kind: event` + async; **sagas top-level, id-keyed**, per-step idempotent compensation; no broker exactly-once | **strengthened in v3** (B6/M3/M4) |
| **D12** | **Evals: govern coverage + adapter contract**; real target model (segments/interaction evals), index, waivers, approval, wired adapter; ship no runner | **strengthened in v3** (B4) |
| **D13** | **Per-check activation**: each validator + its registry activate only on the data they govern | **new in v3** (B5) |

## 12. What changed from v2 (Codex round-2 response)

Round-2 blockers resolved above and in the LLD: **B1** (edge model → additive `interactions` list; the map
becomes a projection), **B2** (full per-leg trust struct; consumer derived per leg), **B3** (privilege
union closed over tools/memory/non-tool capabilities; invoke → authorization; `op:*` scopes; wildcard
ceilings; tier input; CR-15 fold-in), **B4** (segments + interaction evals + index + waivers + approval +
wired adapter + generator spec), **B5** (per-check activation; conditional registries), **B6** (policy +
store registries; requiredness-by-kind; value blockers; unknown-field rule). Majors M1–M12 and minors
m1–m4 are mapped in [`04-revision-plan.md`](04-revision-plan.md); the LLD carries their field-level fixes.
CR-9 was deferred to #15 in v3; **per the 2026-07-22 hard directive it is now a floor gate in this package**
(`check_observability`, §10 / LLD §6.17) — only its runtime backend stays #15. ADR-2/D2, ADR-9/D9, ADR-10/D10
rewritten; ADR-13/D13 added (per-check activation).

## 13. Acceptance criteria (implementation gate)

1. A legacy non-agentic manifest (no new fields) validates unchanged and exits 0; **and** a deterministic
   manifest that adopts `kind`/typed `interactions` validates with **no** new registry (per-check
   activation, B5).
2. Coverage is honest about *how* each requirement is met — not every CR is a validator:
   - **Validated by a fail-closed `ci/` validator** (this package, #13/#16): CR-3, CR-4, CR-5, CR-7,
     CR-12, CR-13, CR-14, CR-15, CR-17, CR-18, **CR-9** (`check_observability` — the design declaration +
     floor gate), and the mechanical parts of CR-6/CR-8/CR-16/CR-20 — each with a regression suite;
     presence-only checks are gone.
   - **Delivered as a generator/adapter** (this package): CR-3/CR-14 views, CR-8/CR-16 eval coverage +
     adapter, CR-20 baseline generator.
   - **Delivered as a workflow/pattern-doc artifact gated by its own sub-issue** (not a `ci/` validator):
     the *justification* prose of CR-2/CR-11 and the pattern/catalog doc parts of CR-6 (#14). **Surface
     selection (was CR-1) and the capability menu (was CR-19) are relocated to the Agentic Design Advisor
     (FR-28)** and are gated there, not here. The
     classification-completeness of CR-2 and the `orchestration.justification` presence of CR-11 *are*
     validated here.
   - **CR-9 (observability + PM eval-console)** is now **validated here** by `check_observability` (a floor
     gate on the `observability` declaration, §10); only its **runtime** trace-backend/console is out of
     package (product-built, #21 reference; #15 keeps the runtime posture refinements).
   This criterion passes when each CR is met by the mechanism named above, no CR is silently claimed to
   have a validator it does not, and every `ci/` validator has its suite.
3. The showcase manifest: a deterministic caller of an agent is blocked without response `validation`; a
   request/response/agent→agent leg into an agent is blocked without cost+authority bounds; an
   over/under/ceiling-violating capability declaration is blocked; a memory write with no matching use is
   blocked; an unauthorized or identity-less caller is blocked; a reliable one-way event validates; a
   two-side-effect flow without a covering saga emits the **`check_compensation_gap` advisory (warning, not
   a block)** — the required-when block is deferred to #42 (v3.2/B4); an agentic system with no
   `observability` block is blocked (`check_observability`, floor gate).
4. Topology, privilege, capability, and tool views generate machine-readable + rendered, and the derived
   `interaction_matrix`/`depends_on`/`events_*` projections regenerate-and-diff clean (cannot drift).
5. The eval coverage validator blocks an uncovered **agent** target, a `baseline_only` target above Tier 1,
   and a multi-agent system with no e2e segment. **Result ingestion / PM-invokes-a-segment is deferred to
   #42** (round-5 B3) — core ships the coverage gate + the adapter *contract shape*, not execution; the core
   validator never runs the adapter or blocks on a result.
6. `SEP-PAIR` (a call and an event between the same pair, distinct ids) validates — the parallel-edge
   property is realizable — and the cold Codex re-review returns APPROVE (or only accepted minors) before implementation begins.
