# Compound Agentic System Surface: Design (HLD) — v2

> Mechanism (the *how*) for the requirements in
> [`../../01-product/compound-agentic-surface/requirements.md`](../../01-product/compound-agentic-surface/requirements.md)
> (CR-1..CR-20). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). **v2** —
> rewritten after the independent Codex review returned REVISIONS REQUIRED (6 blockers), per
> [`04-revision-plan.md`](04-revision-plan.md). Status: **draft, pending Codex re-review**. Targets **2.2.0**.
> Field-level precision + validator signatures are in the LLD [`03-lld.md`](03-lld.md); decisions in
> [`02-adrs.md`](02-adrs.md).

**Thesis (unchanged): a compound agentic system is a manifest, extended.** v2 corrects *which* manifest
structures carry it. The load-bearing v1 mistakes Codex found: the edge model duplicated the manifest's
existing `interaction_matrix`; the determinism boundary was derived from call direction rather than
dataflow, so a deterministic caller could trust an agent's stochastic response unchecked; "who may
invoke" was never modeled; and "necessary-and-sufficient privilege" was really just equality of two
authored sets. v2 fixes all four structurally.

**Governing principle (v2):** HITL validates **declarations, coverage, and consistency — not runtime
behavior.** Where a claim needs runtime truth (actual privilege use, actual eval results), the framework
validates the *declaration* and pushes runtime fidelity to a read-only drift-check + human review. This
keeps every mechanism inside governs-not-runtime (ADR-5), which Codex upheld.

## 1. The system model

- **Nodes = domains**, extended with `kind`: `deterministic | simple_agent | deep_agent`.
- **Edges = `interaction_matrix` entries** — the manifest's **existing** top-level directed edge model
  (`from -> to`, `entity_crossing`), *extended* (§2). This replaces v1's separate `calls` field, which
  duplicated it (Codex M1). `depends_on` becomes an **auto-derived projection** of the interaction model,
  not an independent source.
- **Orchestration** declared at system level (pattern + coordinator + `cycle_bound`), since it is not
  derivable from nodes and edges (CR-11).

## 2. The interaction model (F2 — the core v2 change)

Each `interaction_matrix` entry is extended. An interaction is a *single logical hop* with a stable
identity, so multiple interactions between the same domain pair are distinct (fixes the domain-pair
false-positives, M1/M2):

- **`id`** — stable interaction identifier (the double-representation and cycle logic key off this, never
  the domain pair).
- **`kind`** — `sync_call` (request/response) | `async_task` (A2A Task: request with async response via
  SSE/webhook/polling) | `event` (fire-and-forget or reliable one-way; no response).
- **`facade`** — for `sync_call`/`async_task`, a reference to the callee's declared `facade_apis` entry
  (its `signature` is the payload contract). For `event`, the emitted-event reference.
- **Request/response trust legs (B1).** An interaction carries data in up to two directions, each
  governed separately:
  - `request` leg (caller → callee): `input_validation` required when the *caller* is stochastic (an
    agent) and the callee is deterministic — the deterministic side must validate the agent-produced
    input before trusting it.
  - `response` leg (callee → caller): `output_validation` required when the *callee* is stochastic and
    the caller is deterministic — the deterministic caller must validate the agent's response before
    trusting it. (This is the exact case v1 missed.)
  - `event` has only a request leg (producer → consumer); a stochastic producer to a deterministic
    consumer requires `input_validation`.
- **`authorization` (B2)** — who may invoke: `allowed_callers` (explicit domain list — a caller not
  listed cannot invoke), `credential_mode`, and `jit` (just-in-time / least-privilege lifetime). Mere
  presence in the graph is *not* authorization.
- **`async` reliability block** — present for `async_task` and reliable `event` (§5).

Reference-integrity (LLD §5): every `facade`/target resolves to a real domain+facade; every
`allowed_callers` entry is a real domain; `event` producer/consumer names pair up.

## 3. The determinism boundary (CR-4, B1) — per leg, not per edge

The boundary is derived from node `kind` and applied to each **data-carrying leg** of every interaction
(request, response, and event), not to "the edge" as a whole:

- **stochastic-source → deterministic-consumer** leg ⇒ the consumer MUST declare validation
  (`input_validation` / `output_validation`) of that stochastic data before trusting it.
- **deterministic-source → stochastic-consumer** leg ⇒ MUST declare **bounded cost** and **bounded
  authority** (agent→agent fan-out included — cost is not limited to one direction, M7).

Validation and bound references are **typed and existence-checked**, not free strings (M12): a
`cost_bound` is a quantitative policy, an `output_validation` resolves to a schema/guardrail, an
`authority_bound` is scopes ⊆ the callee's grant.

## 4. Scoped-capability privilege (F1, CR-14, B4)

A genuine necessary-and-sufficient claim **at declaration granularity**, honest about its runtime limit.

- **Capability sources (complete):** `tools`, `memory` access, non-tool **`capabilities`** (KMS,
  model-endpoint, delegation/impersonation, ambient fs/network/process/env, direct service access), and
  **edge-invocation** (`invoke:<domain>`, derived from the agent's outbound interactions). Every
  privilege an agent holds must trace to one of these.
- **Per-use scoping:** the agent declares each *use* with its specific scope —
  `uses: [{capability, operations, resources}]` — not just the capability name. `needed = ⋃(per-use
  scopes)`. A read-only use of a read/write capability needs only `read:…` (fixes the false
  over-privilege).
- **Registry = ceiling:** the approved-capability registry declares each capability's **maximum**
  grantable scope; every per-use scope MUST be ⊆ that ceiling — a **ceiling-violation** blocks (using a
  capability beyond its approval).
- **Validator (LLD §5):** `over = granted ∖ needed`; `under = a declared use not in granted`;
  `ceiling-violation = a per-use scope ⊄ its ceiling`. Posture generated **machine-readable + rendered**
  (M11).
- **Honest limit (ADR-5):** proves the *declared* per-use set is minimal, consistent, and within ceiling.
  It does **not** prove the running code matches the declaration — that is a **read-only runtime
  drift-check** + human review, never an IAM HITL runs.
- **Proportionate:** per-use scoping is required at **Tier 2+**; lower tiers may declare capability-level
  scopes and default per-use, so it does not become box-ticking.

## 5. Async reliability + events (CR-12, B5)

- A **reliable one-way event** is representable: `kind: event` + an `async` block (delivery, DLQ, replay,
  idempotency) — it was unrepresentable in v1. Fire-and-forget events omit the block.
- `AsyncSpec`: `delivery ∈ {at_most_once, at_least_once}` — **`exactly_once` is not offered** at the
  broker boundary (CR-12); end-to-end exactly-once is achieved by `at_least_once` + a declared
  **idempotent consumer** (`consumer_idempotent: true` + key), not by a delivery flag.
- **Sagas:** compensation is **per side-effecting step** (each step declares its compensating action),
  with a coordinator and compensation-failure handling — not one string on the initiating edge. Async
  paths (chains, fan-out, joins, cycles) are enumerated from the interaction graph by `id`.
- All reliability fields are value-checked (positive timeouts/retries; `dlq`/`replay` justified when
  the delivery semantics require them).

## 6. Eval coverage + adapter (F3, CR-8/16/20, B3)

HITL governs **coverage and gating**; the product runs the evals (governs-not-runtime).

- **Targets** are enumerable: every component, every interaction, and declared **flow segments** (routes
  through the interaction graph). A **coverage validator** blocks a target with no eval spec and no
  waiver.
- **Waiver schema** (structured, like platform-readiness): owner, reason, tier-limit, expiry — a lapsed
  waiver is a coverage gap.
- **Runner-adapter contract:** `eval_adapter: {command, inputs, result_schema}` — a declared interface
  HITL invokes into the product's eval runner; HITL ingests results (schema'd) and records reviewer
  approval. "PM runs an eval on one segment" = PM invokes the adapter for that segment's spec.
- **Baseline generator (CR-20):** a specified function (path, signature, deterministic inputs) that seeds
  eval cases from acceptance criteria + facade contracts + boundary checks + failure modes, preserving
  PM edits on regeneration; a no-evals component is a recorded waiver, and the reviewer gate can flag
  "baseline-only."

## 7. Enforcement (LLD §5) — value-checks, fail-closed, conditionally activated

Validators check **values and references, not mere presence** (Codex M3/M5/M12): `long_running:true`
requires a real durable checkpoint + resume cursor (not `checkpoint:none`); a `deep_agent`'s subagents
are references to declared domains (not empty lists); policy strings resolve to real
schemas/guardrails/actions. Each validator is fail-closed with a stable blocker code.

**Activation rule (B6, resolves the A1/Z1 additivity contradiction):** the agentic validators and the
capability-registry requirement fire **only when an agentic marker is present** (any `kind`,
`interaction.kind`, `orchestration`, or an agentic block). A legacy non-agentic manifest has no markers,
skips them entirely, and exits 0 — additive-only is true because the checks *activate* rather than always
requiring the new registries.

## 8. Generated views (CR-3/CR-14, M11)

Generated from the manifest + registries: a **topology/routing view** (nodes by `kind`; interaction legs
typed; boundary legs marked; `orchestration.pattern`; routes/segments), a **privilege-posture** output,
and an **approved-capability matrix** — each emitted **machine-readable (JSON/YAML) and rendered
(Markdown)** with a schema version, deterministic ordering, and a CI regenerate-and-diff so they cannot
drift. Static only (ADR-5).

## 9. Memory, deep agents, lifecycle (CR-7/17/18, M3/M4/M5)

Declared per agent and **value-validated**: long-term memory carries owner, durability, retrieval policy,
write provenance, high-stakes-write guardrails, and a required `pii` policy (explicit `none` needs
justification); shared memory resolves `store` vs `shared_store` through a shared-store registry with one
owner. Lifecycle requires meaningful durable checkpoint/resume/idempotency/cancellation/human-gate values.
Deep agents require nonempty planner/subagents (as domain refs)/gates/guardrails and `context_isolation:
true` + `memory.long_term`.

## 10. Observability (CR-9) — deferred, stated

Cross-hop tracing + the token-cost amplification budget are **out of this design package**, tracked in
[#15](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/15). Note (Codex M8): the existing
token-cost registry measures *HITL development-change* spend, not product-agent per-node/per-edge fan-out
— #15 must add a product-agent extension, not reuse it as-is.

## 11. Decisions (v2 — to lock as ADRs)

| # | Decision | Note |
|---|---|---|
| D1 | Component = manifest domain (+`kind`) | unchanged |
| **D2** | **Edge = extended `interaction_matrix` entry** (id + kind + facade + trust legs + authorization + async); `calls` deleted; `depends_on` is a projection | **rewritten in v2** — replaces "edge = facade_api"; the facade is the *contract*, the interaction is the *edge* |
| D3 | Topology/privilege/tool posture are generated views, machine-readable + rendered | +machine-readable (M11) |
| D4 | Framework-agnostic | unchanged (upheld) |
| D5 | Governs, not runs; validators + static views only | unchanged (upheld); anchors F1/F3 limits |
| D6 | Capability menu always presented; recommend, never decide | unchanged |
| D7 | Determinism boundary derived, applied **per data leg** | strengthened (B1) |
| D8 | Extend the schema map form of `facade_apis`; reconcile the template | unchanged; scope enumerated in LLD (M9) |
| **D9** | **Scoped-capability privilege**: per-use scopes + registry ceilings + complete sources; necessary-and-sufficient *for declared uses*; runtime = drift-check | **rewritten in v2** (B4) |
| **D10** | **Interaction identity**: stable `id`; dup/cycle logic keys off it, not domain pairs | new (M1/M2) |
| **D11** | **Reliable one-way events** as `kind: event` + async; no broker exactly-once | new (B5) |
| **D12** | **Evals: govern coverage + adapter contract**, ship no runner | new (B3, F3) |

## 12. What changed from v1 (Codex round-1 response)

Blockers B1 (per-leg boundary), B2 (authorization model), B3 (eval coverage+adapter), B4 (scoped-capability
privilege), B5 (reliable events + real sagas), B6 (value-checks + activation rule) resolved above. Majors
M1-M14 mapped in [`04-revision-plan.md`](04-revision-plan.md); the LLD carries their field-level fixes.
CR-9 (M8) explicitly deferred to #15. ADR-2/ADR-9 are rewritten; ADR-10/11/12 added (interaction identity,
reliable events, eval-adapter boundary).

## 13. Acceptance criteria (implementation gate)

1. A legacy non-agentic manifest (no agentic markers) validates unchanged and exits 0 (activation rule).
2. Every CR-1..CR-20 has a value-checking, fail-closed validator or a specified generator/adapter, each
   with a `ci/` regression suite; presence-only checks are gone.
3. The showcase manifest: a deterministic caller of an agent is blocked without response `output_validation`;
   an over/under/ceiling-violating capability declaration is blocked; an unauthorized caller is blocked; a
   reliable one-way event validates; a saga without per-step compensation is blocked.
4. Topology, privilege, and capability views generate machine-readable + rendered, cannot drift.
5. The eval coverage validator blocks an uncovered target; the adapter contract lets PM invoke one segment.
6. The re-run cold Codex review returns APPROVE (or only accepted minors) before implementation begins.
