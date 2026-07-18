# Compound Agentic System Surface: LLD

> Implementation-precision design for **sub-issue [#13](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/13)**
> (manifest schema extension) and the validator signatures behind
> [#16](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/16). Implements the HLD
> [`01-design.md`](01-design.md) + ADRs [`02-adrs.md`](02-adrs.md). EPIC
> [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status: **draft — architect
> review rounds 1-2 folded in** (§9). A developer/agent should be able to implement from this without a
> further design decision.

## 0. What the LLD adds over the HLD

The HLD says *what* the manifest must carry. This fixes the **exact field types, the declared-edge
model, the scope grammar, the needed-privilege algorithm, and each validator's signature + rule + exit
code**. It reconciles with the manifest's **existing** `events_emitted`/`events_consumed`/`depends_on`
model (§2.4). Round-1 review closed two blockers: edges are now **declared** (`calls`, §2.3), never
inferred (restoring ADR-2), and the determinism boundary now has **fields to read** (§2.3, restoring
ADR-7).

## 1. Files created / modified (mapped to sub-issues)

| File | Change | Sub-issue |
|---|---|---|
| `ai/claude/generate-docs/templates/system-manifest.schema.yaml` | add §2 fields (additive); reconcile the list-form template to the map form (D8) | #13 |
| `ai/shared/templates/system-manifest-template.yaml` | worked agentic example; reconcile facade form | #13 |
| `docs/03-engineering/approved-tools.yaml` (template) | new registry (§3.1) | #13 |
| `docs/03-engineering/evals/` (template) | new eval-spec dir (§3.2) | #13 |
| `ci/manifest-agentic/check_manifest_agentic.py` | validator module (§5), fail-closed | #16 |
| `ci/manifest-agentic/test_check_manifest_agentic.py` | regression suite (§6) | #16 |
| `tools/manifest-agentic/generate_views.py` | derived-view generator (§7) | #15 |

Cross-hop trace propagation + token-cost amplification budget (HLD §11 / CR-9) and the opt-in
granted-scope drift-check (HLD §6) are **out of scope here** — they land in the observability sub-issue
[#15](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/15), not #13/#16.

Schema `version` bumps; a manifest omitting every §2 field validates unchanged (case A1).

## 2. Schema field definitions

Format follows the existing schema (`type` / `authored` / `description` / `optional`). All additions are
`optional`. **Agent domain** ≡ `kind ∈ {simple_agent, deep_agent}` (used throughout §5).

### 2.1 Domain-level (`domains.<name>.*`)

```yaml
kind:
  type: enum[deterministic, simple_agent, deep_agent]
  authored: human
  optional: true          # absent ⇒ deterministic (back-compat)

identity:                 # CR-13, CR-14 — validator §5.10 requires it for agent domains
  authored: human
  optional: true
  Identity:
    principal: { type: string }
    privilege: { type: "list[Scope]", description: "GRANTED scopes (§2.5 grammar)" }

tools:        { type: list[string], authored: human, optional: true }   # each a key in approved-tools.yaml (§3.1)

memory:                   # CR-18
  authored: human
  optional: true
  Memory:
    short_term: { strategy: enum[none,summarize,compress,isolate], budget_tokens: {int, optional} }
    long_term:
      optional: true
      store:  { type: string }
      writes: { type: list[string], optional: true }
      reads:  { type: list[string], optional: true }
      pii:    { type: enum[none,redact,block], optional: true }
      scope:  { type: enum[isolated,shared] }
      shared_store: { type: string, optional: true }   # required iff scope==shared — validator §5.9

lifecycle:                # CR-17
  authored: human
  optional: true
  Lifecycle:
    long_running: { type: bool }
    checkpoint:   { type: enum[none,durable], optional: true }
    resumable:    { type: bool, optional: true }
    idempotent_resume: { type: bool, optional: true }
    human_gate_pause:  { type: bool, optional: true }
    timeout:      { type: duration, optional: true }
    cancellation: { type: enum[none,cooperative,hard], optional: true }

deep_agent:               # CR-7 — required iff kind==deep_agent (§5.6)
  authored: human
  optional: true
  DeepAgent:
    planner: { type: string }
    subagents: { type: "list[{name: string, capability: string}]" }
    context_isolation: { type: bool }
    gates: { type: list[string] }
    guardrails: { type: list[string] }

evals:        { spec: { type: string } }   # path under docs/03-engineering/evals/  (CR-8/16/20)
```

### 2.2 Facade-level (`domains.<name>.facade_apis.<name>.*`) — extends `FacadeAPI` (the callee's contract)

```yaml
transport:
  type: enum[sync, async]
  authored: human
  optional: true          # absent ⇒ sync
  description: "sync = request/response (incl. MCP). async = A2A Task (SSE/webhook/polling)."

async:                    # CR-12 — present iff transport==async (§5.4). A2A Task payload = `signature` (D8)
  authored: human
  optional: true
  AsyncSpec:
    delivery: { type: enum[at_most_once,at_least_once,exactly_once] }
    idempotency_key: { type: string, optional: true }   # REQUIRED iff delivery==at_least_once
    timeout: { type: duration }
    retry:  { type: "{max: int, backoff: enum[none,linear,exponential]}", optional: true }
    dlq:    { type: bool, optional: true }
    replay: { type: enum[none,event_sourced], optional: true }
    compensation: { type: string, optional: true }      # ref to a facade/action; REQUIRED for a multi-step async chain (§5.4)
```

### 2.3 Declared edges (`domains.<name>.calls`) — the caller side (round-1 blocker fix; ADR-2, ADR-7)

Edges are **declared, never inferred**. The caller lists what it calls; the boundary attributes live on
the edge (the caller is the party that must validate output / bound cost).

```yaml
calls:
  type: list[Edge]
  authored: human
  optional: true
  Edge:
    to: { type: string, description: "'<domain>.<facade>' target. transport is read from the callee's facade." }
    output_validation: { type: string, optional: true }    # schema/guard ref. REQUIRED iff caller is an agent (stochastic) and callee is deterministic (§5.3)
    cost_bound:      { type: string, optional: true }       # token/fan-out ceiling. REQUIRED iff caller deterministic and callee is an agent (§5.3)
    authority_bound: { type: "list[Scope]", optional: true }# scopes the callee may act with; REQUIRED with cost_bound. MUST be ⊆ the callee's identity.privilege (§5.3)
```

### 2.4 System-level

```yaml
orchestration:            # CR-11, M3
  authored: human
  optional: true
  Orchestration:
    pattern: { type: enum[supervisor,hierarchical,swarm,blackboard,sequential,hybrid] }
    coordinator: { type: string, optional: true }           # domain name
    cycle_bound: { type: int, optional: true }              # REQUIRED iff the topology graph has a cycle (§5.5)
```

### 2.5 Reconciliation with the existing event model (LLD decision L1 — round-1 major fix)

The schema already has `events_emitted`/`events_consumed` (pub/sub) and `depends_on` (dependency edges).
We do not duplicate them:

- **A2A Task edges** (a request that gets an async response) → `calls` an `async` facade (they have a
  `signature`/response contract).
- **Domain events** (fire-and-forget, no response) → the existing `events_emitted`/`events_consumed`.
  **Events are best-effort fire-and-forget**; they carry **no** delivery/dlq/replay/idempotency
  guarantees. If a hop needs those, model it as an async facade, not an event. (This removes the earlier
  unbacked claim that `AsyncSpec` applied to events — `EventEntry`/`EventRef` have no such fields.)
- **One hop is modeled exactly one way** — as a `calls` edge OR an emit/consume event pair, never both.
  §5.5 flags a hop declared both ways (else the union would double-count it for cycle detection).
- **Topology graph** (§7) = directed union of `depends_on` (domain-level) ∪ `calls` edges (facade-level,
  directed caller→callee) ∪ `events_emitted → events_consumed` pairs. A `calls` edge **collapses to its
  target domain** (`Edge.to`'s `<domain>` part) for the union/cycle graph, so all three edge sources are
  domain-to-domain.

### 2.6 Scope grammar (L2)

`Scope` = `"<action>:<resource>"`. `action` is an **open set** (the approved-tool registry is the
authority) — `check_enums` (§5.8) explicitly does **not** enum-check `Scope.action`. `resource` is a
path-like id. Memory scopes are canonical: `read:memory/<store>`, `write:memory/<store>` (per-store).
**Canonicalization before comparison:** lowercase, strip surrounding whitespace — so `read:corpus` and
`Read: corpus ` compare equal.

## 3. Registry schemas

### 3.1 `docs/03-engineering/approved-tools.yaml`
```yaml
schema_version: "1.0"
tools:                    # map[tool_name → {risk: enum[low,med,high], scopes: list[Scope]}]
  <tool_name>: { risk: low, scopes: [<Scope>, ...] }   # scopes = the COMPLETE set the tool requires (D9)
```
### 3.2 `docs/03-engineering/evals/<component>.yaml`
```yaml
component: <domain|edge|segment id>
generated_from: [FR-<n>, facade:<name>, boundary:<edge>, incident:<id>]
cases: [ { id: <id>, given: <input>, expect: <assertion>, source: enum[acceptance_criterion,facade_contract,boundary_check,failure_mode] } ]
owner: <pm_handle>                 # CR-20: PM owns; generator seeds `cases`
status: enum[baseline, extended]   # QA gate flags baseline-only
```

## 4. The needed-privilege algorithm (L3) — KeyErrors guarded (round-1 fix)

```python
def scopes(strings):                       # canonicalize (§2.6) before any set op
    return {s.strip().lower() for s in strings}

def needed_scopes(domain, approved_tools):
    s = set()
    for t in domain.get("tools", []):
        entry = approved_tools.get(t)      # missing ⇒ clean blocker from check_approved_tools (§5.1)
        if entry: s |= scopes(entry.get("scopes", []))
    lt = (domain.get("memory") or {}).get("long_term")
    if lt and lt.get("store"):
        st = lt["store"].strip().lower()
        if lt.get("writes"): s.add(f"write:memory/{st}")
        if lt.get("reads"):  s.add(f"read:memory/{st}")
    return s

# check_privilege runs only after check_identity (§5.10) confirms identity.privilege exists for agents.
granted = scopes((domain.get("identity") or {}).get("privilege", []))
over  = granted - needed_scopes(domain, approved_tools)     # over-privilege
under = needed_scopes(domain, approved_tools) - granted     # under-privilege
```

Invariant (ADR-9): every scope traces to a tool or memory source; inter-agent access is governed by
edges (§2.3), not scopes.

## 5. Validator signatures (`ci/manifest-agentic/check_manifest_agentic.py`)

**Contract (mirrors `check-platform-ready.sh`):** entrypoint `main(manifest_path, approved_tools_path)
-> exit 0|2`. Each check is `check_X(manifest, registries) -> list[Blocker]`; the entrypoint aggregates,
prints to stderr, and **fails closed** — unparseable/missing input, unknown enum, or any unexpected
exception → exit 2. Runs in CI and as an `architect-review-design` / `ops-deploy` pre-flight. "Agent
domain" ≡ `kind ∈ {simple_agent, deep_agent}`.

| # | Function | Blocks when… |
|---|---|---|
| 5.1 | `check_approved_tools` | a `domains.*.tools[]` entry is not a key in `approved-tools.yaml` |
| 5.2 | `check_privilege` | for any **agent domain**, `over` or `under` (§4) is non-empty |
| 5.3 | `check_determinism_boundary` | for a `calls` edge where caller/callee differ in determinism: agent→deterministic edge missing `output_validation`; deterministic→agent edge missing `cost_bound` or `authority_bound`; **or an `authority_bound` scope not ⊆ the callee's `identity.privilege`** (an edge cannot authorize a scope the callee never held) |
| 5.4 | `check_async_edges` | `transport:async` facade with no `async` block; `async` block on a `sync` facade; `delivery:at_least_once` with no `idempotency_key`; a **multi-step async chain** (a path of ≥2 async `calls` edges) whose initiating edge's facade has no `compensation` |
| 5.5 | `check_topology` | the directed graph (§2.5 union) has a cycle and no `orchestration.cycle_bound`; **or** a hop — the ordered (caller domain, callee domain) pair — is declared both as a `calls` edge and an event pair |
| 5.6 | `check_deep_agent` | `kind:deep_agent` missing any `deep_agent` element **or** missing `memory.long_term` |
| 5.7 | `check_lifecycle` | `lifecycle.long_running:true` missing any of checkpoint/resumable/idempotent_resume/timeout |
| 5.8 | `check_enums` | any §2 enum field holds a value outside its set (**excludes `Scope.action`**, §2.6) |
| 5.9 | `check_shared_store` | `memory.long_term.scope==shared` with no `shared_store` |
| 5.10 | `check_identity` | an **agent domain** has no `identity` (with `principal` + `privilege`) — runs before 5.2 |

`Blocker = {domain|edge, code, message}`; messages name the offending id.

## 6. Test-case matrix (`test_check_manifest_agentic.py`)

| Case | Fixture | Expect |
|---|---|---|
| A1 additivity | non-agentic manifest | exit 0 |
| A2 showcase | §2 research_agent (granted==needed) | exit 0 |
| **A3 green async** | valid async facade + idempotency + compensation | exit 0 (passing-negative) |
| **A4 green boundary** | agent→det edge with output_validation; det→agent with cost+authority | exit 0 (passing-negative) |
| B1/B2/B3 | over / under / memory-write-no-grant | exit 2 `check_privilege` |
| C1 | unapproved tool | exit 2 `check_approved_tools` |
| D1 | agent→det `calls` edge, no `output_validation` | exit 2 `check_determinism_boundary` |
| **D2** | det→agent edge, no `cost_bound`/`authority_bound` | exit 2 `check_determinism_boundary` |
| **D3** | det→agent edge whose `authority_bound` scope ∉ callee `identity.privilege` | exit 2 `check_determinism_boundary` |
| E1 | async `at_least_once`, no idempotency_key | exit 2 `check_async_edges` |
| E2 | 2-hop async chain, initiating facade no compensation | exit 2 `check_async_edges` |
| **E3** | `async` block on a `sync` facade | exit 2 `check_async_edges` |
| F1 | A→B→A calls cycle, no `cycle_bound` | exit 2 `check_topology` |
| **F2** | one hop declared as both a `calls` edge and an event pair | exit 2 `check_topology` |
| G1/G2 | deep_agent incomplete / no long_term | exit 2 `check_deep_agent` |
| H1 | long_running, no checkpoint | exit 2 `check_lifecycle` |
| **I1** | `scope:shared`, no `shared_store` | exit 2 `check_shared_store` |
| **J1** | agent domain, no `identity` | exit 2 `check_identity` |
| Z1 | unparseable manifest / missing registry | exit 2 (fail-closed) |
| Z2 | bad enum (`delivery: sometimes`) | exit 2 `check_enums` |

## 7. Derived-view generator (`tools/manifest-agentic/generate_views.py`)

`generate(manifest, registries)` writes 3 static files under `docs/03-engineering/agentic-posture/`:
`topology.md` (Mermaid: nodes coloured by `kind`; edges = sync/async/event from the §2.5 union, boundary
edges marked; `orchestration.pattern` in title; + routing table), `privilege-matrix.md` (agent ×
granted/needed/over/under), `approved-tool-matrix.md` (agent × tools, flagged). Static only (ADR-5);
regenerated in CI so it cannot drift.

## 8. Resolved design questions (were §8 open items)

- **Explicit edge declaration — RESOLVED (§2.3):** added `calls: [Edge]`; edges are declared, not
  inferred from `signature` strings (restores ADR-2). This is the single source for §5.3 direction,
  §5.4 multi-step, and §5.5 cycle detection.
- **Determinism-boundary fields — RESOLVED (§2.3):** `output_validation` / `cost_bound` /
  `authority_bound` on the edge give §5.3 something to read (restores ADR-7).
- **Open scope-action set — CONFIRMED open (§2.6):** `check_enums` exempts `Scope.action`; scope strings
  are canonicalized before comparison.

## 9. Architect review disposition (round 1)

| Finding | Disposition |
|---|---|
| **B: §5.3 reads nonexistent fields** | Fixed §2.3: `output_validation`/`cost_bound`/`authority_bound` on the `calls` edge |
| **B: edges inferred, contradicts ADR-2** | Fixed §2.3: explicit `calls: [Edge]`; §7 topology reads it; "multi-step" = ≥2 async calls in the chain |
| **M: §2.4 events reliability claim unbacked** | Fixed §2.5: events are best-effort fire-and-forget, no delivery guarantees; reliability ⇒ async facade |
| **M: double-representation of a hop** | Fixed §5.5: a hop declared both as a `calls` edge and an event pair blocks |
| **M: `shared_store`-iff-shared no validator** | Fixed §5.9 (+ test I1) |
| **M: identity-required no validator; §4 KeyErrors** | Fixed §5.10 (+ test J1); §4 uses `.get()` + canonicalization; "agent domain" defined |
| **m: §8(a) scope enum + canonicalization** | Fixed §2.6/§5.8 |
| **m: test gaps (D2/E3/F2/I1/J1, green cases A3/A4)** | Fixed §6 |
| **CR-9 observability / drift-check absent** | Confirmed out of scope for #13/#16 → tracked in #15 (§1) |

**Round 2** confirmed both blockers + all majors closed; two new items from the `calls` revision, now fixed:

| Finding (round 2) | Disposition |
|---|---|
| `authority_bound` unbounded by the privilege model (authority leak) | Fixed §2.3/§5.3: `authority_bound` MUST be ⊆ callee `identity.privilege`; validator checks containment; test D3 |
| ADR-2 no longer describes the edge model (callee facade + caller `calls`) | Fixed: ADR-2 refinement note added in `02-adrs.md` |
| §5.5/F2 hop-match key unstated | Fixed §5.5: hop = ordered (caller domain, callee domain) pair |
| §2.5 facade→domain collapse for the cycle graph | Fixed §2.5 |
