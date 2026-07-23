# Compound Agentic System Surface: LLD — v3.2 (core scope lock)

> Implementation-precision design for sub-issues [#13](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/13)
> (manifest schema) and [#16](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/16) (validators).
> Implements HLD [`01-design.md`](01-design.md) + ADRs [`02-adrs.md`](02-adrs.md), per the Codex
> response [`04-revision-plan.md`](04-revision-plan.md) and the core scope lock
> [`../agentic-core-scope.md`](../agentic-core-scope.md). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10).
> Status: **draft, round-4 core-lock applied (v3.2), pending Codex round-5**. A developer/agent
> implements from this without a further design decision.
>
> **v3.2 changelog (round-4 core scope lock).** **M1/O6 (eval):** the round-3 broadening of coverage to
> *every* component/edge is **superseded** — it reintroduced over-governance. Core coverage = **every agent
> component + one e2e segment**; deterministic coverage is optional; universal coverage is a **deferred
> follow-on** (§6.12/§7.1). **B4 (saga):** the required-when compensation model is **deferred**; core
> validates **declared** sagas only and adds a **`check_compensation_gap` advisory** (`warning`, never
> blocks — §6.14/§6.16/§4.2) that alerts when a flow looks like it needs compensation. `saga_missing` as a
> blocker is deferred. See [`../agentic-core-scope.md`](../agentic-core-scope.md) for the full core/deferred
> boundary; delegated authority (M2) and design-time sync reliability (CR-6/M5) are likewise deferred.
>
> **v3.2 addendum (2026-07-22 hard directive) — observability + PM eval-console is now a FLOOR GATE.** Per
> the user directive that a PM eval console + live traces is a hard requirement, CR-9/CR-16 are elevated: a
> new top-level **`observability`** declaration (§4.3) is **required on any agentic system** and enforced by
> **`check_observability`** (§6.17, a blocking floor gate). This is the *design declaration + gate* — HITL
> ships it; the **product builds** the running console/trace backend (#21 reference), so O1 governs-not-runtime
> holds. This **un-defers CR-9's design-time portion from #15** (only the runtime posture backend stays #15).
>
> **v3.1 changelog (round-3 blockers — B3/B4 superseded by v3.2 above).** **B1:** the derived `interaction_matrix`/`events_*` projections
> are emitted to a **separate generated-view file**, not written back into the manifest (§2.4, §9) —
> `generate` is idempotent, no `edge_double_authored` self-conflict (test VIEW-IDEMPOTENT). **B2:**
> `long_running:true` now **requires** `resumable:true` **and** `idempotent_resume:true` (§6.10, test
> LIFE-RESUME). **B3 (SUPERSEDED by v3.2/M1 — see above):** ~~eval coverage targets every component ∪ every
> interaction ∪ segments~~ — this broadening over-governed; core coverage is now **agents + e2e** (§6.12/§7.1),
> universal coverage deferred. The `contract_test` mechanism and `result_review` gate remain (optional /
> per-ingested-result). **B4 (SUPERSEDED by v3.2/B4 — see above):** ~~saga required for a declared
> `transactional` segment~~ — required-when deferred; core validates declared sagas + a compensation-gap
> advisory. Original v3.1 text retained below for history. The v3.1 B4 was **scoped to a declared
> `transactional` segment** with
> agent/async side effects — a synchronous deterministic flow is **exempt** and stays registry-free
> (§4.2/§6.14, test SAGA-SYNC-OK); this trims the over-reach and restores additive-only. The Advisor
> (FR-28) elicits *whether* compensation is needed.
>
> **v3 changelog (round-2 blockers).** B1: the edge model is a new additive top-level `interactions`
> **list** — the existing `interaction_matrix` **map** cannot hold two edges for one domain pair, so it
> becomes a derived projection (§2, §2.4). B2: request/response/event each carry the **full** trust-leg
> struct and the validator derives the stochastic consumer **per leg** (§2.2, §6.3). B3: the privilege
> union joins memory through `uses`, edge-invocation moves to authorization (not the identity grant),
> resource-less uses get a `*` scope, and tier is a validator input (§3.1, §6.2, §6.x). B4: `segments`,
> interaction `evals`, an eval **index**, waiver file, approval schema, and a full adapter wire protocol
> are defined (§7). B5: activation is **per-check**, and every registry requirement is conditional (§0.1,
> §6.0). B6: policy + shared-store + durable-store registries exist, and requiredness-by-kind is a table
> (§4.1, §5, §6). Sagas are hoisted to a top-level list (§4.2). Full finding→fix map in
> [`04-revision-plan.md`](04-revision-plan.md).

## 0. Executable-schema note

The manifest schema file is a **descriptive** custom YAML dialect (`type`/`authored`/`optional`/nested
named types), not an executable schema language. Validation is therefore a **Python validator pipeline**
(`ci/manifest-agentic/`), not schema-language enforcement. Every field below is validated by explicit
code for **type, requiredness, enum membership, range, non-emptiness, reference resolution, and
unknown-field rejection** — never by presence alone. Grammars used throughout:

| Token | Grammar (regex) | Notes |
|---|---|---|
| `domain_name` | `^[a-z][a-z0-9_]*$` | no dots (so the first dot in a facade ref is unambiguous, m1) |
| `interaction_id` | `^[a-z][a-z0-9_-]*$` | globally unique across `interactions` |
| `duration` | `^[0-9]+(ms\|s\|m\|h)$`, value > 0 | |
| `Scope` | `^[a-z][a-z0-9_-]*:[a-z0-9/_*-]+$` | `action:resource`; resource may be `*`, `p/*`, or a literal (§6.13) |
| `facade_ref` | `^<domain_name>\.[A-Za-z0-9_.]+$` | first-dot split: `from`=before first dot, rest=facade key |
| `event_ref` | `^<domain_name>:[a-z][a-z0-9_]*$` | `producer:event_name` — colon-separated, distinct from `facade_ref` (m2) |
| `idempotency_key` | `^[a-z][a-z0-9_.]*$` | field path into the message payload |

**Unknown-field rule (B6):** within any block the schema governs, an unrecognized key is a blocker
(`code: unknown_field`), **except** keys prefixed `x_` (reserved for user extensions, ignored). Legacy
manifests contain only schema-defined keys, so this never false-blocks them.

### 0.1 Additivity and activation (B5)

Every field this LLD adds is **optional at the schema level** — a legacy manifest (no new fields) parses
and validates unchanged. Whether a *check* runs is decided **per check** by an **activation predicate**
over the data actually present (§6.0), not by a single global "agentic marker" switch. Consequence: a
manifest that uses only some new fields activates only the checks those fields govern, and requires only
the registries those checks need. A wholly deterministic manifest that adopts `kind: deterministic` and a
typed `interactions` edge activates graph-integrity checks (§6.5/6.6) but **not** the capability, boundary,
authorization, async, memory, lifecycle, deep-agent, or eval checks — and therefore needs **no** new
registry. This is what makes "additive-only; non-agentic manifests need no registry" literally true.

## 1. Files created / modified

| File | Change | Sub-issue |
|---|---|---|
| `ai/claude/generate-docs/templates/system-manifest.schema.yaml` | add top-level `interactions` (§2), `orchestration` (§4), `segments` (§7), `sagas` (§4.2); extend `DomainEntry` (§3); mark `interaction_matrix`/`depends_on`/`events_emitted`/`events_consumed` **derivable** (§2.4); reconcile facade list→map (D8) | #13 |
| `ai/shared/templates/system-manifest-template.yaml` | worked agentic example; facade map-form; template list→map reconcile (M9, D8) | #13 |
| `docs/03-engineering/approved-capabilities.yaml` (template) | capability registry w/ classes, risk, ceilings, `runtime_ref` (§5) | #13 |
| `docs/03-engineering/policies.yaml` (template) | policy registry: schemas / guardrails / actions (§5, B6) | #13 |
| `docs/03-engineering/stores.yaml` (template) | durable + shared store registry (§5, B6/M5) | #13 |
| `docs/03-engineering/evals/index.yaml` + `waivers.yaml` + `eval-adapter.yaml` + specs | eval registry, waivers, adapter contract (§7) | #13 |
| `ci/manifest-agentic/check_manifest_agentic.py` | validator pipeline (§6), value-checking, fail-closed, **per-check activated** | #16 |
| `ci/manifest-agentic/test_check_manifest_agentic.py` | regression suite (§8) | #16 |
| `tools/manifest-agentic/generate_views.py` | machine-readable + rendered posture/topology; also emits derived `interaction_matrix`/`depends_on`/`events_*` (§2.4, §9) | #15 |
| `tools/manifest-agentic/gen_baseline_evals.py` | baseline eval generator (§7.4) | #16 |
| `ai/claude/hooks/check-domain-boundary.sh` | extend to the static interaction-contract check (§6.4, honest scope in HLD §2/M11) | #16 |

Schema `version` bumps. **CR-9 observability fields ARE here now** — the top-level `observability`
declaration (§4.3) + `check_observability` floor gate (§6.17), per the 2026-07-22 hard directive (HLD §10);
only the runtime posture backend stays #15.

## 2. The edge model: top-level `interactions` list (F2, B1)

**Why a new list and not the existing map.** The manifest's `interaction_matrix` is
`map["from -> to", InteractionEntry]`. A map has one value per key, so it **cannot** represent two edges
between the same pair (a `sync_call` *and* an `event` from `billing` to `ledger`). v2 tried to make a
stable `id` inside the map value do this; it cannot. v3 adds a **new, additive, top-level list** whose
element identity is the `id`, so parallel edges are two elements. The old map is retained for legacy
manifests and is **derived** from the list when the list is present (§2.4).

```yaml
interactions:                      # NEW top-level, optional; authoritative edge model when present
  type: list[InteractionEntry]
  InteractionEntry:
    id:    { type: interaction_id }                     # unique across the list (§6.5)
    from:  { type: domain_name }                        # source domain
    to:    { type: domain_name }                        # destination domain
    kind:  { type: enum[sync_call, async_task, event] }
    facade:{ type: string }                             # facade_ref for call/task; event_ref for event (§4.1 requiredness)
    description:     { type: string }
    entity_crossing: { type: string }
    request:  { type: Leg, optional: true }             # from → to  (§2.2)
    response: { type: Leg, optional: true }             # to → from  (§2.2); FORBIDDEN when kind==event
    authorization: { type: Authorization, optional: true }   # §2.3
    async:  { type: AsyncSpec, optional: true }         # §2.1; required for async_task and reliable event
    side_effecting: { type: bool, optional: true }      # default derived from facade.mutations (§6.7); saga input
    evals:  { type: "{spec: string}", optional: true }  # eval spec path for this edge (§7)
```

### 2.1 `AsyncSpec` (CR-12, B5/M4)

```yaml
AsyncSpec:
  delivery: { type: enum[at_most_once, at_least_once] }   # NO exactly_once (broker boundary, CR-12)
  consumer_idempotent: { type: bool, optional: true }     # REQUIRED true iff delivery==at_least_once (§6.7)
  idempotency_key: { type: idempotency_key, optional: true }  # REQUIRED iff consumer_idempotent (payload field path)
  timeout: { type: duration }                             # logical task/delivery timeout, >0
  retry:   { optional: true, max: {int>=1}, backoff: {enum[linear,exponential]} }  # FORBIDDEN when delivery==at_most_once (§6.7)
  dlq:     { type: bool, optional: true }                 # REQUIRED true when delivery==at_least_once unless dlq_justification (§6.7)
  dlq_justification: { type: string, optional: true }
  replay:  { type: enum[none, event_sourced], optional: true }
```

Saga is **not** nested here (v2 mistake M3); it is a top-level object referencing interaction ids (§4.2).

### 2.2 `Leg` — the trust struct, one shape for every data leg (B2, CR-4)

A leg carries data from a **source** to a **consumer**. The same struct is used on `request`
(source=`from`, consumer=`to`), `response` (source=`to`, consumer=`from`), and the single leg of an
`event` (source=`from`, consumer=`to`). The validator derives (source, consumer) **per leg** and applies
the boundary rule to that leg's actual consumer — fixing v2's "authority always compared to callee" bug.

```yaml
Leg:
  validation:      { type: PolicyRef, optional: true }    # schema/guardrail on the data (§6.3)
  cost_bound:      { type: QuantPolicy, optional: true }   # §6.3
  authority_bound: { type: "list[Scope]", optional: true } # §6.3

QuantPolicy: { limit: {type: "int>0"}, unit: {type: enum[tokens, calls, fanout]} }
# PolicyRef = a key in policies.yaml (§5); resolves to a schema | guardrail | action (§6.8)
```

**Which legs exist, per `kind`:** `sync_call` → `request` (from→to) and `response` (to→from);
`async_task` → `request` and `response` (the response arrives over `async`); `event` → `request` only
(no `response`).

**Boundary rule (§6.3), per leg, from node `kind`:**

| leg (source→consumer) | the leg MUST be **present** and carry |
|---|---|
| consumer is **stochastic** (simple/deep agent) | `cost_bound` **and** `authority_bound`; `authority_bound ⊆ consumer.identity.privilege` |
| consumer **deterministic**, source **stochastic** | `validation` |
| both deterministic | nothing (leg may be omitted) |

**Presence is enforced (fixes the "omit the leg to skip the check" hole).** When the boundary rule
requires a control on a leg, that leg MUST be present — an omitted `request`/`response`/event leg whose
(source, consumer) triggers the rule is `code: leg_missing` (§6.3), not a silent pass. §6.3 first
determines the required legs from `kind` + endpoint kinds, then checks presence, then the sub-fields.

This covers every case the review named: a deterministic caller's **request** into an agent now has
cost/authority fields (consumer=the agent, so authority is bounded against the agent's grant); an agent
caller's **response** leg from a deterministic callee bounds authority against the **caller** agent; and
**agent→agent** is covered because the consumer is stochastic on the relevant leg (cost/authority
required), independent of the source's determinism (fixes the v2 "fan-out unbounded" gap, M10).

### 2.3 `Authorization` — non-human identity, JIT default (B2, CR-13, M1)

```yaml
Authorization:
  allowed_callers: { type: "list[domain_name]" }          # each MUST be a domain with an identity.principal (§6.4)
  audience: { type: domain_name, optional: true }         # the callee identity being invoked; defaults to `to`
  credential_mode: { type: enum[jit, static, none] }      # default expectation is jit
  credential_justification: { type: string, optional: true }  # REQUIRED when credential_mode ∈ {static, none} (§6.4)
```

Authorization names **principals**, not bare graph membership: an entry in `allowed_callers` is a domain
whose `identity.principal` is the non-human identity permitted to invoke. A caller with no `identity` may
not be an allowed caller of an agent (§6.4). `credential_mode` other than `jit` must be justified — this
is the least-privilege/JIT default made checkable.

### 2.4 Derived projections (B1, M2, D2)

When `interactions` is present it is authoritative and the generator (§9) **derives** the following into a
**separate generated-view file** (`agentic-posture/projections.*`), **not** back into the source manifest
(round-3 B1):

- `interaction_matrix[f -> t]` = a coarse projection (one entry per distinct pair; `description` =
  newline-joined interaction descriptions; `entity_crossing` = concatenation). Because the projection lives
  in its own file, `edge_double_authored` (§6.6) fires **only** when a **human hand-authors**
  `interaction_matrix` in the *manifest* alongside `interactions` — the generated view never triggers it.
- `depends_on[d]` = `{ t : ∃ interaction from d to t }` ∪ legacy import-derived deps. This one **stays an
  auto manifest field** (coarse domain list; it does not conflict with the interaction rules). When
  `interactions` is absent, `depends_on` keeps its current auto-derived meaning unchanged.
- `events_emitted` / `events_consumed` = projected from `kind: event` interactions: for an event
  interaction `from=P, to=C, facade=P:e`, the view emits `P.events_emitted[e]` with `shape` = the event
  interaction's `entity_crossing` and `consumed_by ∋ C`, and `C.events_consumed ∋ {name: e, from: P}`. If a
  **manifest** hand-authors these lists, the validator requires them to **equal** the projection
  (`code: event_projection_mismatch`, §6.6); it never silently merges. The interaction id is the key; the
  legacy lists are a generated view of it (M2).

CI runs the generator and **fails on any diff** (regenerate-and-diff), so the generated-view file can never
drift from the `interactions` source, and — because it is a separate file — running the generator twice is
idempotent (round-3 B1: no self-conflict on the second validation).

## 3. `DomainEntry` extensions (F1 capabilities, memory, lifecycle, deep-agent)

```yaml
kind: { type: enum[deterministic, simple_agent, deep_agent], optional: true }   # absent ⇒ deterministic
kind_rationale: { type: string, optional: true }   # why this is the SIMPLEST kind that fits (CR-2); required for agents in a compound manifest (§6.15)
owning_fr: { type: string, optional: true }        # e.g. "FR-26"; baseline-eval + traceability source (§7.4)

identity: { optional: true, Identity: {
  principal: { type: string },                      # the non-human identity (service account / workload id)
  privilege: { type: "list[Scope]" } } }            # the GRANTED scopes (§6.2)

uses:                       # F1 per-use capability scoping (§6.2)
  type: "list[CapabilityUse]"
  optional: true
  CapabilityUse:
    capability: { type: string }              # key in approved-capabilities.yaml
    operations: { type: "list[string]" }      # e.g. [read] — the specific ops
    resources:  { type: "list[string]", optional: true }   # e.g. [customer]; omitted ⇒ resource `*` (§6.x)
    # contributes scopes {op:resource} (or {op:*} if resources omitted); each MUST be ⊆ registry ceiling (§6.2)
```

### 3.1 Memory — declared as capability uses, value-checked (CR-18, B3/M5)

```yaml
memory: { optional: true, Memory: {
  short_term: { optional: true, Strategy: {
    strategy: { type: enum[none, summarize, compress, isolate] },
    budget_tokens: { type: "int>0", optional: true } } },   # REQUIRED unless strategy==none (§6.11)
  long_term: { optional: true, LongTerm: {
    store: { type: string },                                # resolves in stores.yaml (§6.11)
    durability: { type: enum[durable] },                    # ONLY durable is valid for long_term (§6.11)
    owner: { type: domain_name },
    retrieval: { type: enum[semantic, episodic, keyed, filesystem] },   # `filesystem` = deep-agent virtual-fs (M7)
    scope: { type: enum[isolated, shared] },
    shared_store: { type: string, optional: true },         # REQUIRED iff scope==shared; resolves in stores.yaml (§6.11)
    pii: { type: enum[none, redact, block] },               # REQUIRED; `none` needs pii_justification
    pii_justification: { type: string, optional: true },
    reads:  { type: "list[MemoryAccess]", optional: true },
    writes: { type: "list[MemoryAccess]", optional: true },
    MemoryAccess: {
      resource: { type: string },                           # store resource
      high_stakes: { type: bool, optional: true },          # write only; true ⇒ high_stakes_guardrail required (§6.11)
      provenance: { type: string, optional: true },         # write only; REQUIRED when high_stakes (M5)
      staleness:  { type: duration, optional: true } },     # read only; max acceptable age (M5)
    high_stakes_guardrail: { type: PolicyRef, optional: true } } } }
```

**Memory ⇄ privilege reconciliation (§6.2/§6.11, closes B3.1):** every `long_term.reads[].resource`
requires a matching `uses` entry `{capability: <memory-class cap over store>, operations:[read],
resources:[resource]}`; every `writes[].resource` requires the same with `operations:[write]`. A memory
read/write without the corresponding `uses` scope is **under-privilege**; a memory-class `uses` scope
with no declared read/write is **over-privilege**. Memory thus enters `needed` through `uses` and is
cross-checked against the `memory` block — one canonical scope space.

### 3.2 Lifecycle (CR-17, B6/M6)

```yaml
lifecycle: { optional: true, Lifecycle: {
  long_running: { type: bool },
  checkpoint: { type: enum[none, durable] },
  checkpoint_store: { type: string, optional: true },   # REQUIRED iff checkpoint==durable; resolves in stores.yaml, durable class (§6.10)
  resume_cursor: { type: string, optional: true },      # REQUIRED iff long_running; grammar ^[a-z0-9_.-]+$
  resumable: { type: bool, optional: true },
  idempotent_resume: { type: bool, optional: true },
  side_effect_key: { type: idempotency_key, optional: true },  # REQUIRED iff resumable AND the component is side-effecting (§6.10)
  human_gate: { type: bool, optional: true },           # declares a human-in-the-loop gate over the long horizon (the trigger field)
  human_gate_pause: { type: bool, optional: true },     # REQUIRED true iff human_gate==true (§6.10)
  timeout: { type: duration, optional: true },
  cancellation: { type: enum[cooperative, hard], optional: true } } }   # `none` is not a member; REQUIRED iff long_running (§6.10)
```

### 3.3 Deep agent (CR-7, M7)

```yaml
deep_agent: { optional: true, DeepAgent: {           # required iff kind==deep_agent (§6.9)
  planner: { type: domain_name },
  subagents: { type: "list[domain_name]" },          # REFERENCES to declared domains; their capability is the referenced domain's purpose + facades (M7)
  context_isolation: { type: bool },                  # must be true (§6.9)
  gates: { type: "list[PolicyRef]" },
  guardrails: { type: "list[PolicyRef]" } } }
# A deep agent additionally requires memory.long_term with durability:durable and retrieval:filesystem OR semantic (§6.9)

evals: { optional: true, type: "{spec: string}" }    # component-level eval spec path (§7); the inline authoring source
```

## 4. System-level additions

```yaml
orchestration: { optional: true, Orchestration: {
  pattern: { type: enum[supervisor, hierarchical, swarm, blackboard, sequential, hybrid] },
  justification: { type: string },                    # REQUIRED: task-shape fit + token-overhead ack (CR-11, §6.5)
  coordinator: { type: domain_name, optional: true }, # MUST name an agent domain fitting the pattern (§6.5)
  cycle_bound: { type: "int>0", optional: true } } }  # REQUIRED (and >0) iff the interaction graph has a cycle (§6.5)

segments: { optional: true, type: "list[Segment]", Segment: {   # eval + routing targets (§7, CR-3/8)
  id:   { type: string },
  path: { type: "list[interaction_id]" },             # consecutive; each hop's `to` == next hop's `from` (§6.5)
  e2e:  { type: bool, optional: true },                # true = an end-to-end flow (CR-8)
  transactional: { type: bool, optional: true },       # true = author-declared distributed-compensation unit (§4.2). In core this drives an ADVISORY, not a requirement (v3.2/B4)
  evals:{ type: "{spec: string}", optional: true } } }
```

### 4.1 Interaction requiredness by `kind` (m3, B6)

The schema marks fields optional for additivity; **once an interaction declares a `kind`**, these become
required (`code: interaction_incomplete`, §6.5):

| `kind` | required | forbidden |
|---|---|---|
| `sync_call` | `facade` (facade_ref), `response` | `async` |
| `async_task` | `facade` (facade_ref), `async` | — |
| `event` | `facade` (event_ref), `async` when delivery-reliable | `response` |

A `kind: async_task` with no `async` block is a blocker (§6.7). A legacy `interaction_matrix` entry (no
`kind`) is unaffected.

### 4.2 Sagas — top-level, id-keyed (CR-12, B5/M3)

```yaml
sagas: { optional: true, type: "list[Saga]", Saga: {
  id: { type: string },                               # unique
  coordinator: { type: domain_name },                 # owns/starts the saga; must be an agent or deterministic orchestrator
  order: { type: enum[sequential, parallel] },        # forward order of steps
  steps: { type: "list[SagaStep]", SagaStep: {
    interaction_id: { type: interaction_id },         # a side-effecting interaction in this saga's flow
    compensation: { type: PolicyRef },                # the compensating action (an `action` policy, §6.8)
    compensation_idempotent: { type: bool },          # must be true (§6.7)
    on_compensation_failure: { type: enum[halt, escalate] } } } } }
```

**Core disposition — validate declared, advise on gaps; the required-when model is deferred (v3.2/B4).**
The round-4 review found the required-when saga model (segment↔saga identity, overlap, parallel
compensation, requiredness inference) underspecified and not yet sound. Rather than ship an
incomplete enforcement model, the core **defers the full distributed-compensation model to a follow-on**
(see [`../agentic-core-scope.md`](../agentic-core-scope.md)) and does two proportionate things instead:

- **Validate declared sagas.** `check_saga` validates every `saga`'s well-formedness — steps resolve to
  side-effecting interactions, `compensation` resolves to an `action` policy, `compensation_idempotent ==
  true`, no two sagas cover the same interaction, `order` semantics consistent. Compensation runs in
  **reverse of `order`** for `sequential`. This is unchanged and sound.
- **Advise on compensation gaps — warn, don't enforce (the "alert users we don't support it" rule).**
  `check_compensation_gap` (§6.14) is an **advisory** (severity `warning`, never a blocker): when a flow
  has **≥2 side-effecting interactions with an agent or async/event endpoint and no declared `saga`
  covering them**, it emits *"this flow looks like it needs distributed compensation, which the core does
  not enforce yet — handle rollback deliberately or declare a `saga`."* A `segment` with `transactional:
  true` and no covering saga always triggers the advisory. This closes the round-4 B4 "silent omission"
  hole (a deferral must not silently pass flows that need compensation) without shipping the enforcement
  model. The Advisor (FR-28) asks the matching intake question so the warning is rarely a surprise.

`saga_missing` as a **blocker** — requiring a saga for a `transactional` segment — is **deferred** to the
follow-on; in core the same condition is the advisory above.

### 4.3 Observability + PM eval-console declaration (CR-9/CR-16, hard directive 2026-07-22)

Every agentic system carries a top-level **`observability`** block. HITL **validates the declaration and
gates on it** (`check_observability`, §6.17) — a design that omits it, or declares it incompletely,
**fails** (floor). HITL ships the declaration + validator + gate + the static posture view generated from
it; the **product builds** the running trace backend + PM eval console (governs-not-runtime; #21 is the
runnable reference).

```yaml
observability: { optional: true, type: "Observability", Observability: {   # required once any domain is an agent (§6.17)
  tracing: { type: "Tracing", Tracing: {
    convention: { type: enum[otel_genai, openinference] },   # the trace convention the product emits to
    hops:       { type: "list[interaction_id]" },            # which inter-component hops are traced (must ⊇ every agent-endpoint interaction)
    attributes: { type: "list[string]" } } },                # the span attributes captured (non-empty)
  cost_budget: { type: "QuantPolicy" },                      # the token-cost amplification budget (§6.8 grammar; limit > 0)
  eval_console: { type: "EvalConsole", EvalConsole: {        # the PM-facing surface (CR-16) — declared, product-built
    access:   { type: enum[ui, api] },                       # how the PM runs evals + reviews results/traces (a console, not just the CLI adapter)
    owner:    { type: string },                              # the role/team that operates it
    ref:      { type: string } } } } }                       # a pointer to the console (design doc / product component id)
```

**`approved-capabilities.yaml`** — ceilings + tool runtime mapping (F1, CR-14/15):
```yaml
schema_version: "1.0"
capabilities:                 # map[name → Capability]
  <name>:
    class:  enum[tool, memory, kms, model, delegation, ambient, service]
    risk:   enum[low, med, high]
    ceiling: list[Scope]      # maximum grantable scope (§6.2)
    runtime_ref: string       # (class==tool only) the runtime allow-list identifier — preserves CR-15 tool→runtime mapping
```
Tools are the `class: tool` rows; the **tool matrix** (§9) is the `class: tool` projection of the
capability matrix; `runtime_ref` is the product's runtime allow-list key. This is the documented CR-15
fold-in (M9), not a silent drop.

**`policies.yaml`** — every `PolicyRef` resolves here (B6):
```yaml
schema_version: "1.0"
policies:                     # map[ "<ns>:<name>" → Policy ]
  <ns:name>: { kind: enum[schema, guardrail, action], ref: string, note: string, optional: true }
# input/output validation → schema|guardrail; cost/authority live on the leg, not here;
# compensation → action; gates/guardrails/high_stakes_guardrail → guardrail (§6.8)
```

**`stores.yaml`** — durable + shared stores (B6/M5):
```yaml
schema_version: "1.0"
stores:                       # map[name → Store]
  <name>: { durability: enum[durable, ephemeral], owner: domain_name, shared: bool }
# long_term.store / checkpoint_store must resolve to durability:durable (§6.10/6.11);
# shared_store must resolve to shared:true (§6.11)
```

Eval registry files are in §7.

## 6. Validators (`ci/manifest-agentic/check_manifest_agentic.py`) — value-checking, fail-closed

Entrypoint `main(manifest, registries, tier) -> exit 0|2`. `tier ∈ {0,1,2,3}` comes from the change-file
breadcrumb (`.hitl/current-change.yaml` `tier`); absent ⇒ treated as the highest tier (fail-safe, so a
missing tier never *relaxes* a gate). `Blocker = {locus, code, message}` where `locus` is a
domain/interaction/segment/saga id; system/registry errors get reserved loci. The pipeline aggregates all
blockers, then exits 2 if any; it fails closed on unparseable/missing input, unknown enum, unresolved
reference, or any exception.

### 6.0 Per-check activation (B5)

Each check runs **iff** its predicate holds; otherwise it is skipped (not vacuously passed). A check's
required registry is loaded **only when the check activates** — so a manifest that never activates
`check_capabilities` needs no `approved-capabilities.yaml`.

| # | Check | Activates when… | Needs registry |
|---|---|---|---|
| 6.2 | `check_capabilities` | any domain has `uses`, `identity`, or `kind ∈ {simple_agent, deep_agent}` | approved-capabilities |
| 6.3 | `check_boundary_legs` | any interaction has ≥1 endpoint whose domain `kind` is an agent | policies |
| 6.4 | `check_authorization` | any interaction targets an agent, or declares `authorization` | — |
| 6.5 | `check_topology` | `interactions` present, or `orchestration`/`segments` present | — |
| 6.6 | `check_references` | `interactions` present | — |
| 6.7 | `check_async` | any interaction is `async_task`/`event`, or has an `async` block | — |
| 6.8 | `check_policy_refs` | any `PolicyRef` appears anywhere | policies |
| 6.9 | `check_deep_agent` | any domain `kind: deep_agent` | — |
| 6.10 | `check_lifecycle` | any domain has `lifecycle` | stores |
| 6.11 | `check_memory` | any domain has `memory` | stores, approved-capabilities |
| 6.12 | `check_eval_coverage` | any domain is an agent, or `segments` present (i.e. there is an agentic target) | evals index/waivers |
| 6.13 | `check_scope_grammar` | any `Scope` appears (`identity.privilege`, `uses`, `authority_bound`, ceilings) | — |
| 6.14 | `check_saga` | any `saga` **declared** (validates its well-formedness; v3.2/B4) | policies |
| 6.15 | `check_classification` | `interactions` present with ≥1 agent endpoint (a compound manifest) | — |
| 6.16 | `check_compensation_gap` *(advisory)* | ≥2 side-effecting agent/async interactions with no covering `saga`, or a `transactional` segment with no covering saga (v3.2/B4) | — |
| 6.17 | `check_observability` *(floor gate)* | any domain is an agent (an agentic system must be observable + PM-evaluable — hard directive 2026-07-22) | — |

A wholly deterministic manifest with typed `interactions` activates only 6.5/6.6 (graph integrity) and
needs **no** new registry. `check_saga` (6.14) activates **only on a declared `saga`** and validates its
well-formedness — a local sync debit→credit is a database transaction, not a saga, and stays registry-free.
The **compensation-gap advisory** (6.16) may fire on a flow with ≥2 side-effecting agent/async steps and no
saga, but it is a `warning`, never a blocker, and needs no registry — it is the honest "we don't enforce
this yet" signal (v3.2/B4). The Advisor (FR-28) elicits whether a flow needs distributed compensation.
(Tests A3, SAGA-SYNC-OK, COMP-GAP.)

### 6.2–6.14 checks

| # | Check | Blocks when… |
|---|---|---|
| 6.2 | `check_capabilities` | a `uses[].capability` not in registry; a per-use scope ⊄ its capability ceiling (ceiling-violation); `over = granted ∖ needed` non-empty; `under = needed ∖ granted` non-empty, where `needed` = ⋃(per-use scopes ∪ memory-derived scopes §3.1); at Tier 2+ an agent with `identity` but no `uses` (must scope per-use); scope containment uses §6.13 wildcard semantics |
| 6.3 | `check_boundary_legs` | for each interaction, from `kind` + endpoint kinds determine each leg's (source,consumer) and whether the §2.2 rule requires a control; **the required leg is absent** (`leg_missing`); a present stochastic-consumer leg missing `cost_bound` or `authority_bound`, or with `authority_bound ⊄ consumer.identity.privilege`; a present stochastic-source→deterministic-consumer leg missing `validation` |
| 6.4 | `check_authorization` | an interaction into an agent with no `authorization.allowed_callers`; a caller (the interaction's `from`) not in the target's `allowed_callers`; an `allowed_callers` entry that is not a domain with an `identity.principal`; `credential_mode ∈ {static,none}` without `credential_justification` |
| 6.5 | `check_topology` | duplicate `interaction.id`; an incomplete interaction (§4.1); a cycle in the interaction graph (domains as vertices, directed by from→to) with no positive `orchestration.cycle_bound`; a `coordinator` that is not a declared agent domain, or the coordinator/pattern rule below is violated; `orchestration.justification` empty; a `segment.path` whose hops are not consecutive (hop[i].to ≠ hop[i+1].from). **Coordinator/pattern rule:** `supervisor`, `hierarchical`, `blackboard` **require** a `coordinator` that is an agent; `swarm` **forbids** a coordinator (peer mesh); `sequential`, `hybrid` **allow** it optionally |
| 6.6 | `check_references` | a `facade` (facade_ref) not resolving to `to`'s `facade_apis`; an `event` `facade` (event_ref) whose producer/name/consumer do not reconcile (§2.4); a `from`/`to`/`allowed_callers`/`subagent`/`coordinator` not a declared domain; `edge_double_authored`; `event_projection_mismatch`; `eval_index_mismatch` (a hand-edited `index.yaml` differing from the projection of inline `evals.spec`, §7.1) |
| 6.7 | `check_async` | `async` on a `sync_call`; `async_task` with no `async`; `at_least_once` without `consumer_idempotent`+`idempotency_key`; `retry` present with `delivery==at_most_once`; `at_least_once` without `dlq` and without `dlq_justification`; missing/`≤0` timeout |
| 6.8 | `check_policy_refs` | any `PolicyRef` (`validation`, `compensation`, `gates`, `guardrails`, `high_stakes_guardrail`) that is empty/`TODO`/`none` or does not resolve in `policies.yaml`; a `validation` ref whose policy `kind ∉ {schema,guardrail}`; a `compensation` ref whose `kind ≠ action`; a `QuantPolicy` with `limit ≤ 0` or `unit` invalid |
| 6.9 | `check_deep_agent` | `kind:deep_agent` missing `deep_agent` or `memory.long_term`; empty planner/subagents/gates/guardrails; `context_isolation≠true`; a `subagent`/`planner` not a declared domain; `memory.long_term.retrieval ∉ {filesystem,semantic}`; `deep_agent` block on a non-deep kind |
| 6.10 | `check_lifecycle` | `long_running:true` with **`resumable≠true`**, **`idempotent_resume≠true`** (round-3 B2 — both are required for a long-running component, not optional), `checkpoint:none`, missing `resume_cursor`, missing/`≤0` `timeout`, or `cancellation` absent; `checkpoint:durable` without a `checkpoint_store` resolving to a `durable` store; `resumable:true` on a side-effecting component without `side_effect_key`; `human_gate:true` with `human_gate_pause≠true` |
| 6.11 | `check_memory` | `long_term` missing `owner`/`store`/`durability`/`retrieval`/`scope`/`pii`; `pii:none` without justification; `store`/`shared_store` unresolved (or `shared_store` not `shared:true`, or `scope:shared` without `shared_store`, or `shared_store` with `scope:isolated`); a `write.high_stakes:true` without `high_stakes_guardrail` or without `provenance`; a memory read/write not reconciled to a `uses` scope (§3.1) |
| 6.12 | `check_eval_coverage` | a **target** — in **core, every agent component + one `e2e:true` segment** (v3.2/M1 — independent per-agent eval, CR-8/CR-16; universal deterministic-component/edge coverage is **deferred**, see §7.1) — with no `evals.spec` in the index and no unlapsed waiver; no `e2e:true` segment when ≥2 components; a spec/waiver failing its schema (§7); a spec with `approval.decision != approved` used to satisfy coverage at Tier 2+; an **ingested adapter result with no reviewer `result_decision`** (the result-review gate, §7.3, applies to any ingested result). A **deterministic** component/edge is **not required** to have coverage in core, but **may** declare a `kind: contract_test` spec (§7.2), which is then validated |
| 6.13 | `check_scope_grammar` | a `Scope` not matching the grammar (§0); a memory scope not canonical `read\|write:<store>/<resource>`; a ceiling/grant/authority scope with an ill-formed wildcard |
| 6.14 | `check_saga` | (declared-saga well-formedness only, v3.2/B4) a `saga` step whose `interaction_id` is not side-effecting or not a declared interaction; `compensation` not resolving to an `action` policy; `compensation_idempotent≠true`; two sagas covering the same interaction; `order` semantics inconsistent. **`saga_missing`** (requiring a saga for a `transactional` segment) is **deferred** — in core the same condition raises the 6.16 advisory instead |
| 6.16 | `check_compensation_gap` *(advisory, `warning` — never blocks)* | a flow has **≥2 side-effecting interactions with an agent or async/event endpoint and no declared `saga`** covering them, **or** a `segment` with `transactional:true` and no covering saga → emits the compensation-gap warning (§4.2, the "alert users we don't support it" rule, v3.2/B4). Activates independently of `check_saga` |
| 6.17 | `check_observability` *(floor gate — blocks)* | **no `observability` block** on an agentic system; `tracing.hops` not ⊇ every interaction with an agent endpoint (an agent hop left untraced); empty `tracing.attributes`; `tracing.convention` not a known enum; `cost_budget` missing or `limit ≤ 0`; **no `eval_console`** (the PM eval surface, CR-16) or its `access`/`owner`/`ref` empty. §4.3 — the hard 2026-07-22 directive; HITL gates the **declaration**, the product builds the runtime |

`check_saga` is separated from `check_async` because a saga spans multiple interactions. In core it
activates **only** on a declared `saga` and validates well-formedness (v3.2/B4) — it never *requires* a
saga. The `check_compensation_gap` advisory (6.16) is what surfaces a likely-needed-but-undeclared saga, as
a `warning`. A synchronous debit→credit pair is a database-transaction concern and triggers neither. The
Advisor elicits whether distributed compensation is actually needed; the full required-when enforcement
model is a deferred follow-on ([`../agentic-core-scope.md`](../agentic-core-scope.md)).

```python
def canon(s: str) -> str:
    return s.strip().lower()

def resource_covers(ceiling_res: str, use_res: str) -> bool:
    if ceiling_res == "*":
        return True
    if ceiling_res.endswith("/*"):
        return use_res == ceiling_res[:-2] or use_res.startswith(ceiling_res[:-1])  # "p/*" covers "p" and "p/..."
    return ceiling_res == use_res

def scope_in_ceiling(scope: str, ceiling: list) -> bool:
    act, res = scope.split(":", 1)
    return any(c.split(":", 1)[0] == act and resource_covers(c.split(":", 1)[1], res)
               for c in ceiling)

def use_scopes(u: dict) -> list:                       # scopes contributed by one CapabilityUse
    out = []
    for op in u["operations"]:
        for res in (u.get("resources") or ["*"]):      # resource-less ⇒ "*", a valid Scope (fixes B3.4)
            out.append(canon(f"{op}:{res}"))
    return out

def memory_uses(domain: dict) -> list:                 # memory access as capability uses (§3.1)
    out = []
    lt = (domain.get("memory") or {}).get("long_term") or {}
    store = lt.get("store")
    for r in lt.get("reads", []):
        out.append({"capability": f"memory:{store}", "operations": ["read"],  "resources": [r["resource"]]})
    for w in lt.get("writes", []):
        out.append({"capability": f"memory:{store}", "operations": ["write"], "resources": [w["resource"]]})
    return out

def needed(domain: dict, reg: dict) -> set:
    s = set()
    for u in list(domain.get("uses", [])) + memory_uses(domain):
        cap = reg["capabilities"].get(u["capability"])         # missing ⇒ 6.2 blocker (recorded by caller)
        if not cap:
            continue
        for sc in use_scopes(u):
            if not scope_in_ceiling(sc, cap["ceiling"]):         # ceiling-violation ⇒ 6.2
                record_ceiling_violation(domain, u, sc)
            s.add(sc)
    return s
# granted = set(canon(x) for x in domain.identity.privilege)
# over  = { g for g in granted if not scope_in_ceiling(g, [n for n in needed]) }  # g not covered by any needed scope
# under = { n for n in needed  if not scope_in_ceiling(n, list(granted)) }        # a needed scope not covered by any grant
# EDGE-INVOCATION IS NOT HERE (B3.3/B3.6): who-may-invoke is authorization (§6.4), not an identity grant.
```

`over`/`under` use **mutual wildcard coverage** (no false under: a need of `read:customer/profile` is
covered by a grant of `read:customer/*`; a genuine family need is declared as a `customer/*` *use* so it
matches a `customer/*` grant exactly). A grant strictly broader than every declared need is **correctly**
over-privilege — necessary-and-sufficient means `granted` and `needed` mutually cover, not that a broad
grant is waved through. Edge-invocation authority is **not** part of the identity-privilege claim; it is
governed entirely by `check_authorization` (§6.4). This makes the privilege union closed over exactly its
declared sources: tools, memory, and non-tool capabilities (B3).

## 7. Eval coverage + adapter (F3, B4)

### 7.1 Targets and registry

- **Core mandatory targets (v3.2/M1) = every agent component + one `e2e:true` segment.** This delivers
  CR-8/CR-16's *independent per-agent eval* (every agent is separately evaluable) plus one end-to-end flow,
  without the over-governance of requiring a spec for *every* deterministic component and edge — the
  round-3 broadening that round-4 flagged as an O6 violation. Each mandatory target must have a `kind: eval`
  spec in the index or an unlapsed waiver.
  - **Deterministic components/edges are optional in core.** A team **may** declare a `kind: contract_test`
    spec for one (it is then validated and appears in the index), but coverage is **not required** for it.
    **Universal deterministic coverage** (a spec for every component ∪ every interaction) is a **deferred
    follow-on** ([`../agentic-core-scope.md`](../agentic-core-scope.md)), not core.
  - *(Which agent targets are mandatory vs waivable at a given tier is right-sized by the Advisor's floor,
    FR-28; #10 validates the declared coverage + waivers.)*
- **Where a spec path is authored:** on the target itself — `domains[d].evals.spec`,
  `interactions[i].evals.spec`, `segments[s].evals.spec`. These inline fields are the **single authoring
  source** (one source of truth, ADR-2 discipline).
- **`docs/03-engineering/evals/index.yaml`** (the registry) is a **generated projection** of those inline
  `evals.spec` declarations — `rows: [{target_type, target_id, spec_path}]`, unique on `(target_type,
  target_id)` — written by the generator (§9) and regenerate-and-diff enforced. `check_eval_coverage`
  reads the index; because the index is generated from the inline fields, the two cannot disagree (a
  hand-edited index that differs from the projection is `code: eval_index_mismatch`, §6.6). The
  discriminator is `target_type`; lookup is exact.
- **`docs/03-engineering/evals/waivers.yaml`**: `[{target_type, target_id, owner, reason, tier_limit:int,
  revisit: date}]`; a waiver is lapsed (a gap) when `revisit < today` or the change tier `> tier_limit`.

### 7.2 Eval spec (`docs/03-engineering/evals/<target_type>/<target_id>.yaml`)

```yaml
target_type: enum[component, interaction, segment]
target_id: string
kind: enum[eval, contract_test]         # round-3 B3: a deterministic component/edge satisfies coverage with a contract_test, an agent with an eval
owner: string
status: enum[baseline, extended]        # authorship maturity (generated vs human-extended)
approval:                               # the SPEC gate (before execution — distinct from status)
  reviewer: string
  date: date
  decision: enum[approved, baseline_only, rejected]
result_review:                          # the RESULT gate (after execution — round-3 B3, §7.3)
  optional: true                        # required once an adapter result is ingested (check 6.12)
  reviewer: string
  date: date
  result_decision: enum[pass, fail, waived]
cases: list[{ id: string, given: string, expect: string,
              source: enum[acceptance_criterion, facade_contract, boundary_check, failure_mode],
              edited: bool }]           # edited:true = human-owned, preserved on regeneration (§7.4)
```

`status` records who wrote the cases; `approval.decision` is what the coverage gate reads. At Tier 2+,
`baseline_only`/`rejected` does **not** satisfy coverage (6.12) — a human must approve.

### 7.3 Adapter wire protocol (`docs/03-engineering/evals/eval-adapter.yaml`)

```yaml
schema_version: "1.0"
command: list[string]        # argv, e.g. ["python", "evals/run.py"]
cwd: string                  # working directory, repo-relative
timeout: duration            # per-target hard timeout
target_binding:              # how HITL passes the target to the command
  spec_path: enum[arg, env, stdin]     # where the eval spec path goes
  env_var: string, optional            # var name when spec_path==env
result:
  location: enum[stdout, file]
  path: string, optional               # file path (may contain {target_id}) when location==file
  schema: string                       # repo-relative JSON Schema for the result envelope
exit_codes: { pass: 0, fail: 1 }       # any other code ⇒ adapter_error (fail-closed)
```

**Contract.** For a target, HITL: substitutes `{target_id}`/spec path per `target_binding`; runs `command`
in `cwd` with `timeout`; on exit-code `pass`/`fail` reads the result from `result.location`, validates it
against `result.schema` (a JSON Schema), and writes it into the spec's **`result_review`** block for a
human to sign off (round-3 B3). The **result-review gate** (6.12): once a result is ingested, the spec must
carry a `result_review.result_decision ∈ {pass, waived}` — an ingested result with no reviewer decision, or
a `fail` without a waiver, is a coverage gap. This is distinct from `approval` (which gates the *spec*
before execution); `result_review` gates the *result* after. Any other exit code, a timeout, or a
schema-invalid result is `adapter_error` (fail-closed; never counted as pass). **Security (ADR-5):** the
adapter command is repo-declared and runs **only on explicit operator confirmation** (the `ops-apply-iac`
model) — HITL never auto-executes it in CI. HITL ships the coverage gate and this contract; the product
ships the runner.

### 7.4 Baseline generator (`tools/manifest-agentic/gen_baseline_evals.py`, CR-20)

`generate(target_type, target_id, manifest, prd, out_dir) -> writes/merges a spec`:

- **owning FR**: `manifest.domains[target].owning_fr` (component) or the owning component's `owning_fr`
  (interaction/segment); looked up in `prd` for the acceptance-criterion case source.
- **case sources**: `acceptance_criterion` (from the FR), `facade_contract` (facade `preconditions` +
  `error_modes`), `boundary_check` (the §2.2 obligations on the target's legs), `failure_mode` (CR-6
  list: non-determinism propagation, cross-hop timeout/retry, cycle, fan-out cost, cross-agent trust).
- **deterministic case ids**: `f"{target_id}-{source}-{NN:02d}"`, NN in stable source order (no clock/rng).
- **merge**: by case `id`; a case with `edited: true` is never overwritten; on an id collision between a
  regenerated case and an `edited` case, the human case wins and the generator logs the drop. New
  generated cases are appended with `edited: false`, `status` stays/returns to `baseline` until a human
  extends it.
- **PM ownership (CR-20)**: the workflow step (issue #12/#16) prompts the PM to review and set
  `approval`; a component with no cases is written as a `waiver` row (recorded, not silent).

## 8. Test matrix (`test_check_manifest_agentic.py`)

| Case | Fixture | Expect |
|---|---|---|
| A1 legacy | non-agentic manifest, only `interaction_matrix` map, no new fields, no registries | exit 0 (no check activates) |
| A2 showcase | full agentic manifest, all consistent, all registries | exit 0 |
| **A3 det-typed** | deterministic domains + typed `interactions` (sync_call), **no** capability/policy/store/eval registries | exit 0 (only 6.5/6.6 activate — proves B5) |
| **SEP-PAIR** | a `sync_call` **and** an `event` between the same pair, distinct ids, in `interactions` | exit 0 (representable — proves B1) |
| **DUP-ID** | two `interactions` with the same `id` | 2 `check_topology` |
| **EDGE-DBL** | a pair in both `interactions` and hand-authored `interaction_matrix` | 2 `check_references` (edge_double_authored) |
| **EVT-JOIN** | event interaction whose hand-authored `events_emitted` disagrees with the projection | 2 `check_references` (event_projection_mismatch) |
| RESP | det caller of an agent, `response` leg present but no `validation` (consumer=det caller, source=agent) | 2 `check_boundary_legs` |
| LEG-ABSENT | det caller of an agent, `request` leg **omitted** (consumer=agent ⇒ leg required) | 2 `check_boundary_legs` (`leg_missing` — proves presence enforced) |
| REQ-COST | det caller → agent, request leg present but missing `cost_bound`/`authority_bound` (consumer=agent) | 2 `check_boundary_legs` |
| **A2A-FANOUT** | agent → agent, consumer-agent leg missing cost/authority | 2 `check_boundary_legs` (proves B2 fan-out) |
| AUTH-SCOPE | `authority_bound` ⊄ consumer `identity.privilege` | 2 `check_boundary_legs` |
| EVT-B | stochastic `event` producer → det consumer, request leg present, no `validation` | 2 `check_boundary_legs` |
| EVT-LEG-ABSENT | agent `event` producer → det consumer, `request` leg omitted | 2 `check_boundary_legs` (`leg_missing`) |
| AUTHZ | caller not in `allowed_callers` | 2 `check_authorization` |
| AUTHZ-ID | `allowed_callers` entry with no `identity.principal`; `credential_mode:none` no justification | 2 `check_authorization` |
| **OVER/UNDER/CEIL** | grant beyond needed / needed scope not granted / use ⊄ ceiling | 2 `check_capabilities` |
| **MEM-JOIN** | memory `writes` a resource with no matching `uses` write scope | 2 `check_capabilities` (under) |
| CAP-NONTOOL | KMS/delegation use declared + granted + within ceiling | exit 0 (no false over-privilege) |
| RES-LESS | a `uses` with omitted `resources` → `op:*`, within a `*` ceiling | exit 0 (grammar-valid — proves B3.4) |
| WILDCARD-CEIL | use `read:customer/profile`, ceiling `read:customer/*`, grant `read:customer/profile` | exit 0 (use within a wildcard **ceiling**; grant == need) |
| WILDCARD-FAMILY | family use `resources:[customer/*]` → need `read:customer/*`, grant `read:customer/*` | exit 0 (family use matches family grant) |
| WILDCARD-OVER | grant `read:customer/*`, need only `read:customer/profile` (specific use) | 2 `check_capabilities` (grant strictly broader than need = over-privilege) |
| TIER-DEFAULT | Tier 1 agent, capability-level `uses` (no resources) | exit 0; same at Tier 3 with `identity`, no `uses` ⇒ 2 |
| REF | dangling `facade`, dotted domain name, unresolved `subagent`/`coordinator` | 2 `check_references` / grammar |
| EXACTLY | `delivery: exactly_once` | 2 (enum reject) |
| ALO | `at_least_once` without consumer_idempotent+key | 2 `check_async` |
| ATMOST-RETRY | `at_most_once` with a `retry` block | 2 `check_async` |
| DLQ | `at_least_once`, no `dlq`, no justification | 2 `check_async` |
| ASYNC-TASK-BARE | `async_task` with no `async` | 2 `check_async` |
| RELIABLE-EVT | `kind:event` + at_least_once + idempotent consumer + dlq | exit 0 |
| **COMP-GAP** | a flow with 2 side-effecting **agent/async** interactions and no `saga` (or a `transactional` segment with no covering saga) | exit 0 with a **`warning`** from `check_compensation_gap` — advisory, never blocks (proves the v3.2/B4 "alert, don't enforce" rule) |
| **SAGA-SYNC-OK** | **synchronous** deterministic debit→credit, both `side_effecting`, no `saga`, no registries | **exit 0, no warning** — a sync deterministic flow is exempt from both `check_saga` and the compensation-gap advisory; no saga forced, no `policies.yaml` (additive-only) |
| SAGA-STEP | `saga` step missing/`none` compensation or `compensation_idempotent:false` | 2 (`check_saga` + `check_policy_refs`) |
| CYCLE | interaction cycle, no positive `cycle_bound` | 2 `check_topology` |
| SEG-ADJ | a `segment.path` with a non-consecutive hop | 2 `check_topology` |
| POLICY | `validation: TODO`; a `validation` ref of `kind:action`; `compensation` unresolved | 2 `check_policy_refs` |
| LIFE | `long_running` + `checkpoint:none`; resumable+side-effecting, no `side_effect_key`; `cancellation` absent | 2 `check_lifecycle` |
| **LIFE-RESUME** | `long_running:true` with `resumable` or `idempotent_resume` omitted/false | 2 `check_lifecycle` (both required for long-running — proves round-3 B2) |
| LIFE-GATE | `human_gate:true` with `human_gate_pause:false` (or absent) | 2 `check_lifecycle` (proves the gate trigger field drives the rule) |
| DEEP | empty subagents / `context_isolation:false` / no long_term / `durability` not durable / subagent not a domain | 2 `check_deep_agent` |
| MEM | `pii:none` no justification; `shared_store` isolated; high_stakes write no guardrail/provenance | 2 `check_memory` |
| EVAL-COV | uncovered **agent** target; lapsed waiver; no e2e segment when ≥2 components (v3.2/M1 — core targets = agents + e2e) | 2 `check_eval_coverage` |
| EVAL-DET-SKIP | a **deterministic** component with **no** spec, all agents covered, one e2e segment | exit 0 — deterministic coverage is **not required** in core (proves the v3.2/M1 trim; universal coverage is deferred) |
| EVAL-DET-OK | a deterministic component that **opts in** with a `kind: contract_test` spec | exit 0 (the contract test is validated; it was optional) |
| EVAL-RESULT | an ingested adapter result with no `result_review.result_decision` (or a `fail` without a waiver) | 2 `check_eval_coverage` (the result-review gate — applies to any ingested result) |
| EVAL-APPROVE | Tier 2 target whose only spec is `baseline_only` | 2 `check_eval_coverage` |
| SCOPE | `Read: corpus ` (space/case) and multi-colon/traversal | 2 `check_scope_grammar` |
| CLASSIFY | compound manifest, a domain with no explicit `kind`, or an agent with no `kind_rationale` | 2 `check_classification` |
| **OBSERV-MISSING** | an agentic system with **no `observability` block** (or no `eval_console`) | 2 `check_observability` — the floor gate blocks (hard directive; every agentic system must be observable + PM-evaluable) |
| **OBSERV-OK** | `observability` with `tracing.hops ⊇` all agent-endpoint interactions, non-empty attributes, positive `cost_budget`, an `eval_console{access,owner,ref}` | exit 0 (declaration complete; product builds the runtime) |
| OBSERV-GAP | `observability` present but an agent hop missing from `tracing.hops` | 2 `check_observability` (an untraced agent hop) |
| UNKNOWN | an unrecognized key (not `x_`) in a governed block | 2 (unknown_field) |
| VIEW | generator emits machine-readable + rendered posture + a **separate** `projections.*` view (not written into the manifest), stable ordering | assert artifacts + regenerate-and-diff clean |
| **VIEW-IDEMPOTENT** | run `generate` twice, then validate | exit 0 — projections live in their own file, so the second validation has no `edge_double_authored` self-conflict (proves the round-3 B1 fix) |
| Z1 | unparseable manifest / a required registry absent **while its check is active** | 2 fail-closed |

## 9. Generated views (`tools/manifest-agentic/generate_views.py`)

`generate(manifest, registries)` writes, under `docs/03-engineering/agentic-posture/`, **paired**
machine-readable + rendered artifacts: `topology.{json,md}`, `privilege-posture.{json,md}`,
`capability-matrix.{json,md}`, and `tool-matrix.{json,md}` (the `class:tool` projection, CR-15). The
**derived** `interaction_matrix`, `events_emitted`/`events_consumed` projections (§2.4) are emitted here as
a **separate generated-view file** (`projections.{json,md}`) — they are **not written back into the source
manifest** (round-3 B1: writing them into the manifest would then collide with `edge_double_authored`).
Only `depends_on` remains an auto **manifest** field (a coarse domain-level list — it does not conflict with
the interaction rules). JSON carries `schema_version` + deterministic ordering; CI runs `generate` and
**fails on a diff** (regenerate-and-diff = the "cannot drift" guarantee). Topology draws nodes by `kind`,
interaction legs typed (sync/async/event), boundary legs marked, routes/segments, and
`orchestration.pattern`. Static only (ADR-5).

## 10. LLD decisions

- **L1 (v3):** the authoritative edge model is the top-level `interactions` **list** keyed by `id`;
  `interaction_matrix`, `depends_on`, and `events_*` are derived projections (regenerate-and-diff). The
  v2 attempt to carry parallel edges inside the domain-pair map is abandoned (structurally impossible).
- **L2:** validation is a Python pipeline (§0) with **per-check activation** (§6.0); each check loads its
  registry only when active, so deterministic/non-agentic manifests need no new registry.
- **L3:** the `Leg` trust struct is uniform across request/response/event; the boundary rule is applied to
  each leg's **derived** (source, consumer), so authority is always bounded against the actual stochastic
  consumer (§2.2/§6.3).
- **L4:** `needed` privilege = ⋃(per-use scopes ∪ memory-derived scopes) with wildcard containment and
  registry ceilings; edge-invocation is an **authorization** concern (§6.4), not an identity grant; the
  N&S claim is scoped to declared uses; runtime fidelity is the read-only drift-check (HLD §4), not built
  here.
- **L5:** eval coverage reads a defined target model (`segments` + interaction `evals` + agent domains),
  an index, a waiver file, and an approval schema; the adapter wire protocol (§7.3) is fully specified and
  runs only on operator confirmation.
