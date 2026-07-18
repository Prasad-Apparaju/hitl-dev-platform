# Compound Agentic System Surface: LLD

> Implementation-precision design for **sub-issue [#13](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/13)**
> (manifest schema extension) and the validator signatures behind
> [#16](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/16). Implements the HLD
> [`01-design.md`](01-design.md) + ADRs [`02-adrs.md`](02-adrs.md). EPIC
> [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status: **draft, pending
> architect + spec-conformance review**. A developer/agent should be able to implement from this
> without a further design decision.

## 0. What the LLD adds over the HLD

The HLD says *what* the manifest must carry. This fixes the **exact field types, the scope grammar,
the needed-privilege algorithm, and each validator's signature + rule + exit code** — the pieces the
architect review deferred to LLD. It also reconciles the extensions with the manifest's **existing**
`events_emitted`/`events_consumed`/`depends_on` model (§2.4), which the HLD did not address.

## 1. Files created / modified (mapped to sub-issues)

| File | Change | Sub-issue |
|---|---|---|
| `ai/claude/generate-docs/templates/system-manifest.schema.yaml` | add the fields in §2 (additive); reconcile the list-form template to the map form (D8) | #13 |
| `ai/shared/templates/system-manifest-template.yaml` | worked agentic example; reconcile facade form | #13 |
| `docs/03-engineering/approved-tools.yaml` (template) | new registry (§3.1) | #13 |
| `docs/03-engineering/evals/` (template) | new eval-spec dir (§3.2) | #13 |
| `ci/manifest-agentic/check_manifest_agentic.py` | the validator module (§5), fail-closed | #16 |
| `ci/manifest-agentic/test_check_manifest_agentic.py` | regression suite (§6) | #16 |
| `tools/manifest-agentic/generate_views.py` | the derived-view generator (§7) | #15 |

Schema `version` bumps to the next manifest schema version; a manifest omitting every §2 field validates
unchanged (additivity gate, §6 case A1).

## 2. Schema field definitions

Format follows the existing schema (`type` / `authored` / `description` / `optional`). All additions are
`optional`. Enums written `enum[...]`.

### 2.1 Domain-level (`domains.<name>.*`)

```yaml
kind:
  type: enum[deterministic, simple_agent, deep_agent]
  authored: human
  optional: true          # absent ⇒ deterministic (back-compat)
  description: "Component kind. Gates which agent fields apply; drives the determinism boundary."

identity:                 # CR-13, CR-14
  authored: human
  optional: true          # required when kind ∈ {simple_agent, deep_agent}
  Identity:
    principal: { type: string, description: "Non-human principal id" }
    privilege: { type: "list[Scope]", description: "GRANTED scopes (see §2.5 grammar)" }

tools:                    # CR-15
  type: list[string]
  authored: human
  optional: true
  description: "Tool names; each MUST be a key in approved-tools.yaml (§3.1)."

memory:                   # CR-18
  authored: human
  optional: true
  Memory:
    short_term:
      strategy: { type: enum[none, summarize, compress, isolate] }
      budget_tokens: { type: int, optional: true }
    long_term:
      optional: true
      store: { type: string, description: "Store id; keys the memory scopes" }
      writes: { type: list[string], optional: true }
      reads:  { type: list[string], optional: true }
      pii:    { type: enum[none, redact, block], optional: true }
      scope:  { type: enum[isolated, shared] }
      shared_store: { type: string, optional: true }   # required iff scope == shared

lifecycle:                # CR-17
  authored: human
  optional: true
  Lifecycle:
    long_running: { type: bool }
    checkpoint:   { type: enum[none, durable], optional: true }
    resumable:    { type: bool, optional: true }
    idempotent_resume: { type: bool, optional: true }
    human_gate_pause:  { type: bool, optional: true }
    timeout:      { type: duration, optional: true }    # e.g. "24h"
    cancellation: { type: enum[none, cooperative, hard], optional: true }

deep_agent:               # CR-7 — required iff kind == deep_agent
  authored: human
  optional: true
  DeepAgent:
    planner: { type: string }
    subagents: { type: "list[{name: string, capability: string}]" }
    context_isolation: { type: bool }
    gates: { type: list[string] }
    guardrails: { type: list[string], description: "Never-do actions" }

evals:                    # CR-8, CR-16, CR-20
  authored: human
  optional: true
  Evals:
    spec: { type: string, description: "Path to the eval spec under docs/03-engineering/evals/" }
```

### 2.2 Facade-level (`domains.<name>.facade_apis.<name>.*`) — extends `FacadeAPI`

```yaml
transport:
  type: enum[sync, async]
  authored: human
  optional: true          # absent ⇒ sync
  description: "sync = request/response (incl. MCP tool call). async = A2A Task (SSE/webhook/polling)."

async:                    # CR-12 — present iff transport == async (validator §5.4 blocks otherwise)
  authored: human
  optional: true
  AsyncSpec:
    delivery: { type: enum[at_most_once, at_least_once, exactly_once] }
    idempotency_key: { type: string, optional: true }   # REQUIRED iff delivery == at_least_once
    timeout: { type: duration }
    retry: { type: "{max: int, backoff: enum[none, linear, exponential]}", optional: true }
    dlq: { type: bool, optional: true }
    replay: { type: enum[none, event_sourced], optional: true }
    compensation: { type: string, optional: true }      # ref to a facade/action; REQUIRED for multi-step (§5.4)
```

The A2A **Task payload contract is `signature`** (existing field; D8).

### 2.3 System-level (top of manifest)

```yaml
orchestration:            # CR-11, M3
  authored: human
  optional: true
  Orchestration:
    pattern: { type: enum[supervisor, hierarchical, swarm, blackboard, sequential, hybrid] }
    coordinator: { type: string, optional: true }       # domain name
    cycle_bound: { type: int, optional: true }          # REQUIRED iff the topology graph has a cycle (§5.5)
```

### 2.4 Reconciliation with the existing event model (LLD decision L1)

The schema already has `events_emitted` / `events_consumed` (pub/sub, fire-and-forget) and `depends_on`
(dependency edges). We do **not** duplicate them:

- **A2A Task edges** (a request that gets an async response via SSE/webhook/polling) → `facade_apis`
  with `transport: async` (they have a `signature`/response contract).
- **Domain events** (fire-and-forget notifications, no response) → the existing
  `events_emitted`/`events_consumed`. `AsyncSpec.delivery`/`dlq`/`replay` semantics apply to these too
  where declared.
- The **topology graph** (§7) is built from the union of `depends_on`, sync/async facade references,
  and `events_emitted → events_consumed` pairs — so events are first-class edges, not a second model.

### 2.5 Scope grammar (L2)

A `Scope` is a string `"<action>:<resource>"`:
- `action` ∈ `{read, write, query, invoke, ...}` (open set; the approved-tool registry defines which).
- `resource` is a path-like id.
- **Memory scopes are canonical:** `read:memory/<store>` and `write:memory/<store>` (per-store, §5.2).

## 3. Registry schemas

### 3.1 `docs/03-engineering/approved-tools.yaml`

```yaml
schema_version: "1.0"
tools:                    # map[tool_name → ToolEntry]
  <tool_name>:
    risk: enum[low, med, high]
    scopes: list[Scope]   # the COMPLETE set of scopes this tool requires (source of "needed", D9)
```

### 3.2 `docs/03-engineering/evals/<component>.yaml`

```yaml
component: <domain_name>          # or edge/segment id
generated_from: [FR-<n>, facade:<name>, boundary:<edge>, incident:<id>]
cases:
  - id: <case_id>
    given: <input/state>
    expect: <assertion>
    source: enum[acceptance_criterion, facade_contract, boundary_check, failure_mode]
owner: <pm_handle>                # CR-20: PM owns; baseline generator seeds `cases`
status: enum[baseline, extended]  # QA gate flags baseline-only (§ HLD 8)
```

## 4. The needed-privilege algorithm (L3 — the load-bearing derivation)

```python
def needed_scopes(domain: dict, approved_tools: dict) -> set[str]:
    s: set[str] = set()
    for t in domain.get("tools", []):
        s |= set(approved_tools[t]["scopes"])   # missing key ⇒ approved-tool gate (§5.1) blocks first
    lt = (domain.get("memory") or {}).get("long_term")
    if lt:
        store = lt["store"]                      # per-store granularity (D9)
        if lt.get("writes"): s.add(f"write:memory/{store}")
        if lt.get("reads"):  s.add(f"read:memory/{store}")
    return s

granted = set(domain["identity"]["privilege"])
over  = granted - needed_scopes(domain, approved_tools)   # → over-privilege blockers
under = needed_scopes(domain, approved_tools) - granted   # → under-privilege blockers
```

Invariant (ADR-9): every scope traces to a tool or memory source; a `granted` scope with no source is
genuine over-privilege. Inter-agent access is governed by edges (§5.3), not scopes.

## 5. Validator signatures (module `ci/manifest-agentic/check_manifest_agentic.py`)

**Contract (mirrors `check-platform-ready.sh`):** one entrypoint
`main(manifest_path, approved_tools_path) -> exit 0|2`. Each check is a pure function
`check_X(manifest: dict, registries: dict) -> list[Blocker]`; the entrypoint aggregates all blockers,
prints them to stderr, and **fails closed** — unparseable/missing manifest or registry, unknown enum
value, or any unexpected exception → exit 2. Runs in CI and as an `architect-review-design` /
`ops-deploy` pre-flight.

| # | Function | Rule (blocks when…) |
|---|---|---|
| 5.1 | `check_approved_tools` | a `domains.*.tools[]` entry is not a key in `approved-tools.yaml` |
| 5.2 | `check_privilege` | `over` or `under` (from §4) is non-empty for any agent domain; a `long_term.writes`/`reads` with no matching memory grant is under-privilege |
| 5.3 | `check_determinism_boundary` | a boundary edge (det↔non-det, from `kind`) lacks a declared output validation (stochastic→deterministic) or a cost+authority bound (deterministic→stochastic) |
| 5.4 | `check_async_edges` | `transport: async` with no `async` block; `delivery: at_least_once` with no `idempotency_key`; a multi-step async workflow with no `compensation`; an `async` block on a `sync` facade |
| 5.5 | `check_topology` | the graph (§7, from `depends_on` ∪ facade edges ∪ event pairs) has a cycle and no `orchestration.cycle_bound` is declared |
| 5.6 | `check_deep_agent` | `kind: deep_agent` missing the `deep_agent` block (any of planner/subagents/context_isolation/gates/guardrails) **or** missing `memory.long_term` |
| 5.7 | `check_lifecycle` | `lifecycle.long_running: true` missing any of `checkpoint`, `resumable`, `idempotent_resume`, `timeout` |
| 5.8 | `check_enums` | any §2 enum field holds a value outside its declared set |

`Blocker = {domain|edge, code, message}`; messages name the offending id (the platform-gate style).

## 6. Test-case matrix (`test_check_manifest_agentic.py`)

| Case | Manifest fixture | Expect |
|---|---|---|
| A1 additivity | non-agentic manifest (no §2 fields) | exit 0 |
| A2 showcase | the §2-HLD research_agent (granted == needed) | exit 0 |
| B1 over-privilege | grant a scope no tool/memory sources | exit 2, `check_privilege` |
| B2 under-privilege | tool needs a scope not granted | exit 2, `check_privilege` |
| B3 memory-write no grant | `writes:[x]`, no `write:memory/<store>` | exit 2, `check_privilege` |
| C1 unapproved tool | `tools:[ghost]` not in registry | exit 2, `check_approved_tools` |
| D1 unguarded boundary | stoch→det edge, no output validation | exit 2, `check_determinism_boundary` |
| E1 at_least_once no key | async, `at_least_once`, no idempotency_key | exit 2, `check_async_edges` |
| E2 multi-step no compensation | 2-hop async workflow, no compensation | exit 2, `check_async_edges` |
| F1 cycle no bound | A→B→A, no `cycle_bound` | exit 2, `check_topology` |
| G1 deep_agent incomplete | `kind: deep_agent`, no `deep_agent` block | exit 2, `check_deep_agent` |
| G2 deep_agent no memory | `deep_agent` block present, no `long_term` | exit 2, `check_deep_agent` |
| H1 lifecycle incomplete | `long_running: true`, no checkpoint | exit 2, `check_lifecycle` |
| Z1 fail-closed | unparseable manifest / missing registry | exit 2 |
| Z2 bad enum | `delivery: sometimes` | exit 2, `check_enums` |

## 7. Derived-view generator (`tools/manifest-agentic/generate_views.py`)

`generate(manifest, registries) -> writes 3 static files` under `docs/03-engineering/agentic-posture/`:
1. `topology.md` — Mermaid graph (nodes = domains coloured by `kind`; edges = sync/async/event, boundary
   edges marked; `orchestration.pattern` in the title) + a routing table.
2. `privilege-matrix.md` — agent × {granted, needed, over, under} (from §4).
3. `approved-tool-matrix.md` — agent × tools, unapproved/undeclared flagged.

Static output only (ADR-5, no live dashboard). Regenerated in CI so it cannot drift.

## 8. Open for spec-conformance review

- The scope `action` set (§2.5) is intentionally open; the approved-tool registry is the authority.
  Confirm no closed enum is needed.
- `check_determinism_boundary` needs the edge direction; `depends_on` is directional but facade calls
  are inferred from `signature` references — confirm the LLD's edge-extraction (§7) is unambiguous, or
  add an explicit `calls: [domain.facade]` field. (Candidate follow-up if edge inference proves weak.)
