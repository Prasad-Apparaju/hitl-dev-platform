# Compound Agentic System Surface: LLD — v2

> Implementation-precision design for sub-issues [#13](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/13)
> (manifest schema) and [#16](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/16) (validators).
> Implements HLD [`01-design.md`](01-design.md) v2 + ADRs [`02-adrs.md`](02-adrs.md), per the Codex
> response [`04-revision-plan.md`](04-revision-plan.md). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10).
> Status: **draft, pending Codex re-review**. A developer/agent implements from this without a further
> design decision.

## 0. Executable-schema note (Codex B6)

The manifest schema file is a **descriptive** custom YAML dialect (`type`/`authored`/`optional`/nested
named types), not an executable schema language. Validation is therefore a **Python validator pipeline**
(`ci/manifest-agentic/`), not schema-language enforcement. Every field below is validated by explicit
code for **type, requiredness, enum membership, range, non-emptiness, reference resolution, and
unknown-field rejection** — never by presence alone (the v1 defect class). `duration` grammar:
`^[0-9]+(ms|s|m|h)$`, value > 0.

## 1. Files created / modified

| File | Change | Sub-issue |
|---|---|---|
| `ai/claude/generate-docs/templates/system-manifest.schema.yaml` | extend `InteractionEntry` (§2) + `DomainEntry` (§3); add `orchestration` (§4); reconcile facade list→map (D8) | #13 |
| `ai/shared/templates/system-manifest-template.yaml` | worked agentic example; facade-form + `description`/`purpose` + mutations reconciliation (M9) | #13 |
| `docs/03-engineering/approved-capabilities.yaml` (template) | capability registry w/ ceilings (§5) | #13 |
| `docs/03-engineering/evals/` + `eval-adapter.yaml` | eval specs, coverage, waivers, adapter contract (§7) | #13 |
| `ci/manifest-agentic/check_manifest_agentic.py` | validator pipeline (§6), value-checking, fail-closed, **activation-gated** | #16 |
| `ci/manifest-agentic/test_check_manifest_agentic.py` | regression suite (§8) | #16 |
| `tools/manifest-agentic/generate_views.py` | machine-readable + rendered posture/topology (§9) | #15 |
| `ai/claude/hooks/check-domain-boundary.sh` | extend to check interaction authorization at design-time (B2) | #16 |

Schema `version` bumps. CR-9 observability fields are **not** here (deferred to #15, HLD §10).

## 2. `InteractionEntry` extensions (the edge model, F2)

The manifest's existing top-level `interaction_matrix: map["from -> to", InteractionEntry]` is extended.
All fields additive/optional; a legacy entry (`description` + `entity_crossing` only) still validates.

```yaml
InteractionEntry:            # keyed "from -> to" in interaction_matrix
  id:            { type: string }                    # STABLE, unique; dup/cycle logic keys off this (D10)
  kind:          { type: enum[sync_call, async_task, event] }
  facade:        { type: string, optional: true }    # "<domain>.<facade>" for call/task; event ref for event. First-dot split (m1)
  description:   { type: string }                     # existing
  entity_crossing: { type: string }                   # existing
  request:                                            # caller → callee leg (B1)
    optional: true
    input_validation: { type: PolicyRef, optional: true }   # REQUIRED iff caller stochastic & callee deterministic (§6.3)
  response:                                           # callee → caller leg (B1)  — absent for kind:event
    optional: true
    output_validation: { type: PolicyRef, optional: true }  # REQUIRED iff callee stochastic & caller deterministic (§6.3)
    cost_bound:      { type: QuantPolicy, optional: true }   # REQUIRED iff deterministic→stochastic (also agent→agent, M7)
    authority_bound: { type: "list[Scope]", optional: true } # REQUIRED with cost_bound; MUST be ⊆ callee identity.privilege (§6.3)
  authorization:                                      # who may invoke (B2)
    allowed_callers: { type: list[string] }           # domain names; a caller not listed is blocked (§6.4)
    credential_mode: { type: enum[none, static, jit] }
  async: { type: AsyncSpec, optional: true }          # present for async_task and reliable event (§2.1)

# PolicyRef = "<namespace>:<name>" resolving to a declared schema/guardrail (existence-checked, §6.8)
# QuantPolicy = { limit: int>0, unit: enum[tokens, calls, fanout] }
```

### 2.1 `AsyncSpec` (CR-12, B5)

```yaml
AsyncSpec:
  delivery: { type: enum[at_most_once, at_least_once] }   # NO exactly_once (broker boundary, CR-12)
  consumer_idempotent: { type: bool, optional: true }     # REQUIRED true when delivery==at_least_once
  idempotency_key: { type: string, optional: true }       # REQUIRED when consumer_idempotent
  timeout: { type: duration }                             # >0
  retry:   { type: "{max: int>=0, backoff: enum[none,linear,exponential]}", optional: true }
  dlq:     { type: bool, optional: true }
  replay:  { type: enum[none, event_sourced], optional: true }
  saga:                                                   # per-step compensation (B5)
    optional: true
    coordinator: { type: string }                         # a domain
    steps: { type: "list[{interaction_id: string, compensation: PolicyRef, on_compensation_failure: enum[halt, escalate]}]" }
```

## 3. `DomainEntry` extensions (F1 capabilities, memory, lifecycle, deep-agent)

```yaml
kind: { type: enum[deterministic, simple_agent, deep_agent], optional: true }   # absent ⇒ deterministic

identity: { optional: true, Identity: { principal: {type: string}, privilege: {type: "list[Scope]"} } }

uses:                       # F1 per-use capability scoping (Tier 2+ required; §6.2)
  type: "list[CapabilityUse]"
  optional: true
  CapabilityUse:
    capability: { type: string }              # key in approved-capabilities.yaml (tool/kms/model/delegation/ambient/service)
    operations: { type: list[string] }        # e.g. [read] — the specific ops
    resources:  { type: list[string], optional: true }   # e.g. [customer]
    # this use contributes scopes {op:resource} for op×resource; MUST be ⊆ registry ceiling (§6.2)

memory: { optional: true, Memory: {
  short_term: { strategy: enum[none,summarize,compress,isolate], budget_tokens: {int>0, optional} },
  long_term: { optional: true,
    store: {string}, writes: {list[string], optional}, reads: {list[string], optional},
    pii: {enum[none,redact,block]},                       # REQUIRED; `none` needs `pii_justification` (§6.6)
    pii_justification: {string, optional},
    scope: {enum[isolated,shared]}, shared_store: {string, optional},   # required iff shared; resolves via shared-store registry (§6.6)
    owner: {string}, durability: {enum[ephemeral,durable]}, retrieval: {enum[none,semantic,episodic,keyed]},
    high_stakes_guardrail: {PolicyRef, optional} } }}

lifecycle: { optional: true, Lifecycle: {
  long_running: {bool},
  checkpoint: {enum[none,durable]}, checkpoint_store: {string, optional}, resume_cursor: {string, optional},
  resumable: {bool, optional}, idempotent_resume: {bool, optional}, side_effect_key: {string, optional},
  human_gate_pause: {bool, optional}, timeout: {duration, optional}, cancellation: {enum[none,cooperative,hard], optional} }}

deep_agent: { optional: true, DeepAgent: {          # required iff kind==deep_agent (§6.5)
  planner: {string},
  subagents: {type: "list[string]"},                 # REFERENCES to declared domains (not descriptions), M5
  context_isolation: {bool}, gates: {list[PolicyRef]}, guardrails: {list[PolicyRef]} }}

evals: { spec: {type: string}, optional: true }      # path under docs/03-engineering/evals/  (§7)
```

## 4. System-level

```yaml
orchestration: { optional: true, Orchestration: {
  pattern: {enum[supervisor,hierarchical,swarm,blackboard,sequential,hybrid]},
  coordinator: {string, optional},        # MUST name an agent domain fitting the pattern (§6.5)
  cycle_bound: {int>0, optional} }}        # REQUIRED (and >0) iff the interaction graph has a cycle (§6.5)
```

## 5. Registries

**`approved-capabilities.yaml`** — ceilings (F1):
```yaml
schema_version: "1.0"
capabilities:                 # map[name → {class, risk, ceiling}]
  <name>: { class: enum[tool,kms,model,delegation,ambient,service], risk: enum[low,med,high], ceiling: list[Scope] }
```
**`eval-adapter.yaml`** (§7): `{ command: string, inputs: [...], result_schema: string }`.

## 6. Validators (`ci/manifest-agentic/check_manifest_agentic.py`) — value-checking, fail-closed

Entrypoint `main(manifest, registries) -> exit 0|2`. **Activation gate (B6):** if the manifest has **no
agentic marker** (`kind`, any `interaction.kind`, `orchestration`, or an agentic block), run **nothing**
and exit 0 — this is what makes a legacy manifest (case A1) pass without the new registries, reconciling
A1/Z1. Otherwise run all checks; aggregate blockers; fail closed on unparseable/missing input, unknown
enum, unresolved reference, or any exception. `Blocker = {locus: str, code: str, message: str}` where
`locus` is a domain/interaction/edge id; system/registry errors get reserved codes.

| # | Check | Blocks when… |
|---|---|---|
| 6.1 | `check_activation` | (gate) determines whether 6.2-6.13 run |
| 6.2 | `check_capabilities` | a `uses[].capability` not in registry; a per-use scope (op×resource) ⊄ the capability ceiling; **needed** = ⋃(per-use scopes) ∪ edge-invoke scopes; over = `granted ∖ needed`; under = a use scope ∉ granted; ceiling-violation. Tier 2+ requires `uses`; lower tiers allow capability-level default |
| 6.3 | `check_boundary_legs` | a request leg (agent→det) missing `input_validation`; a response leg (agent-callee→det-caller) missing `output_validation`; a det→agent leg missing `cost_bound`/`authority_bound`; an `authority_bound` scope ⊄ callee `identity.privilege` |
| 6.4 | `check_authorization` | an interaction with no `authorization.allowed_callers`; a caller not in `allowed_callers` (from the graph); `credential_mode` invalid |
| 6.5 | `check_topology` | interaction graph (from `interaction_matrix`, keyed by `id`; `depends_on` is derived, not re-read) has a cycle and no positive `orchestration.cycle_bound`; `coordinator` absent/not-an-agent/pattern-mismatch; a hop's `id` duplicated |
| 6.6 | `check_references` | a `facade`/`allowed_callers`/`subagents`/`shared_store` that does not resolve to a declared domain/facade; an `event` producer/consumer without a matching pair |
| 6.7 | `check_async` | `async` on a `sync_call`; `at_least_once` without `consumer_idempotent`+key; missing/`≤0` timeout; negative retry.max; a `saga` step missing `compensation` for a side-effecting interaction |
| 6.8 | `check_policy_refs` | any `PolicyRef`/`QuantPolicy` (`input/output_validation`, `cost_bound`, `compensation`, `gates`, `guardrails`, `high_stakes_guardrail`) that is empty, `TODO`/`none`/`unlimited`, or does not resolve to a declared policy |
| 6.9 | `check_deep_agent` | `kind:deep_agent` missing `deep_agent` **or** `memory.long_term`; empty planner/subagents/gates/guardrails; `context_isolation:false`; a `subagent` not a declared domain; `deep_agent` on a non-agent kind |
| 6.10 | `check_lifecycle` | `long_running:true` with `checkpoint:none`, `resumable≠true`, `idempotent_resume≠true`, `timeout≤0`, or missing `checkpoint_store`/`resume_cursor`/`cancellation`/`human_gate_pause` |
| 6.11 | `check_memory` | `pii` absent, or `pii:none` without `pii_justification`; missing `owner`/`durability`; `shared_store` set with `scope:isolated` or unresolved in the shared-store registry |
| 6.12 | `check_eval_coverage` | a component/interaction/declared-segment with no `evals.spec` and no unlapsed waiver; a waiver missing owner/reason/tier-limit/expiry (§7) |
| 6.13 | `check_scope_grammar` | a `Scope` not matching `^[a-z]+:[a-z0-9/_-]+$` (single colon, nonempty parts, no traversal); memory scope not canonical `read|write:memory/<store>` |

### 6.x needed-scope algorithm (per-use, F1)
```python
def canon(s): return s.strip().lower()                      # per-token; grammar checked in 6.13
def needed(domain, reg, outbound_targets):
    s = set()
    for u in domain.get("uses", []):
        cap = reg["capabilities"].get(u["capability"])       # missing ⇒ 6.2 blocker
        if not cap: continue
        for op in u["operations"]:
            for res in (u.get("resources") or [""]):
                sc = canon(f"{op}:{res}") if res else canon(op)
                if sc not in {canon(c) for c in cap["ceiling"]}:  # ceiling-violation ⇒ 6.2
                    yield_ceiling_violation(u, sc)
                s.add(sc)
    for tgt in outbound_targets:                              # edge-invocation scopes
        s.add(canon(f"invoke:{tgt}"))
    return s
# over = granted - needed ; under = {declared-use scope} - granted ; both from 6.2
```

## 7. Eval coverage + adapter (F3, B3)

- **Target enumeration:** components (domains) ∪ interactions (by `id`) ∪ declared `segments`
  (`segments: [{id, path: [interaction_id...]}]` on the manifest). `check_eval_coverage` (6.12) requires
  each target have an `evals.spec` or an unlapsed waiver.
- **Eval spec** (`docs/03-engineering/evals/<target>.yaml`): `{ target_id, cases: [{id, given, expect,
  source: enum[acceptance_criterion,facade_contract,boundary_check,failure_mode]}], owner, status:
  enum[baseline,extended] }`.
- **Waiver:** `{ target_id, owner, reason, tier_limit: int, revisit: date }` (platform-readiness shape;
  lapsed = gap).
- **Adapter:** `eval-adapter.yaml` = `{command, inputs, result_schema}`; HITL invokes it per target, ingests
  results validated against `result_schema`, records reviewer approval. No runner shipped (ADR-5/12).
- **Baseline generator** `tools/manifest-agentic/gen_baseline_evals.py`: `generate(target, manifest, prd)
  -> writes/merges an eval spec`, deterministic, preserving human-edited cases (merge by case `id`).

## 8. Test matrix (`test_check_manifest_agentic.py`)

| Case | Fixture | Expect |
|---|---|---|
| A1 legacy | non-agentic manifest, no registry present | exit 0 (activation gate) |
| A2 showcase | full agentic manifest, all consistent | exit 0 |
| **RESP** | det caller of agent, no response `output_validation` | 2 `check_boundary_legs` |
| REQ | agent caller of det, no `input_validation` | 2 `check_boundary_legs` |
| **EVT-B** | stochastic `event` producer → det consumer, no validation | 2 `check_boundary_legs` |
| DET→AG | det→agent leg, no cost/authority | 2 `check_boundary_legs` |
| AUTHZ | caller not in `allowed_callers` | 2 `check_authorization` |
| **OVER/UNDER/CEIL** | grant beyond uses / use not granted / use ⊄ ceiling | 2 `check_capabilities` |
| CAP-NONTOOL | KMS/delegation use declared + granted | exit 0 (no false over-privilege) |
| REF | dangling `facade`, dotted name, unresolved `allowed_callers`/`subagent`/`shared_store` | 2 `check_references` |
| **EXACTLY** | `delivery: exactly_once` | 2 (enum reject) |
| ALO | `at_least_once` without consumer_idempotent | 2 `check_async` |
| RELIABLE-EVT | `kind:event` + async reliability | exit 0 |
| SAGA | ≥2-step async, side-effecting step no compensation | 2 `check_async` |
| CYCLE | interaction cycle, no positive `cycle_bound` | 2 `check_topology` |
| **DUP-ID** | duplicated interaction `id` | 2 `check_topology` |
| SEP-PAIR | a call and an event between the same domain pair (distinct ids) | exit 0 (not double-rep) |
| POLICY | `cost_bound: unlimited`, `output_validation: TODO`, empty `compensation` | 2 `check_policy_refs` |
| LIFE | `long_running` + `checkpoint:none`/`timeout:0s` | 2 `check_lifecycle` |
| DEEP | empty subagents / `context_isolation:false` / no long_term / subagent not a domain | 2 `check_deep_agent` |
| MEM | `pii:none` no justification; `shared_store` with isolated | 2 `check_memory` |
| EVAL | uncovered target; lapsed/incomplete waiver | 2 `check_eval_coverage` |
| SCOPE | `Read: corpus ` and multi-colon/traversal | 2 `check_scope_grammar` |
| VIEW | generator emits machine-readable + rendered, stable ordering | assert both artifacts |
| Z1 | unparseable manifest / missing required registry (agentic present) | 2 fail-closed |

## 9. Generated views (`tools/manifest-agentic/generate_views.py`)

`generate(manifest, registries)` writes, under `docs/03-engineering/agentic-posture/`, **paired**
machine-readable + rendered artifacts: `topology.{json,md}`, `privilege-posture.{json,md}`,
`capability-matrix.{json,md}`. JSON carries `schema_version` + deterministic ordering; CI runs
`generate` and **fails on a diff** (regenerate-and-diff = the "cannot drift" guarantee, m3). Topology
draws nodes by `kind`, interaction legs typed (sync/async/event), boundary legs marked, routes/segments,
`orchestration.pattern`.

## 10. LLD decisions

- **L1 (v2):** the edge model is the extended `interaction_matrix`; `depends_on` is a read-only
  projection; interactions carry stable `id`s. `calls` (v1) is removed.
- **L2:** validation is a Python pipeline (§0), activation-gated; presence-only checks are replaced by
  value/reference/range checks throughout.
- **L3:** `needed` privilege is per-use-scoped with registry ceilings (§6.x); the "necessary-and-sufficient"
  claim is scoped to declared uses; runtime fidelity is the read-only drift-check (HLD §4), not built here.
