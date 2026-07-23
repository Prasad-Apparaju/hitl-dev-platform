# Agentic Design Advisor: LLD

> Implementation-precision design for the **Agentic Design Advisor** (FR-28). Implements HLD
> [`01-design.md`](01-design.md) v3.2 + ADRs [`02-adrs.md`](02-adrs.md) (A1–A9), satisfying requirements
> [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). Verified by the test plan [`03-test-plan.md`](03-test-plan.md). Status: **draft,
> core-lock applied (v3.2), pending Codex re-review (round 5)**. A developer/agent implements from this
> without a further design decision.
>
> **v3.2 core scope lock ([`../agentic-core-scope.md`](../agentic-core-scope.md)):** `compose()` is now
> **obligation-first** so `floor ⊆ workflow` (round-4 B3, §4); the **scenario record is the canonical state**
> with stable ids + a **re-run reconcile/confirm contract** (M3/M4, §7.1/§7.3); `agentic-boundary` authors
> the **contract seam** `facade_apis` + `authorization` (B1, §5.1); the eval command authors **per-agent +
> e2e** coverage (M1, §5.1); the map is **terminal+Mermaid core**, HTML/live-combined **deferred** (M8, §6);
> integration routes via a **cheap topology probe** (B2, §8); rung `deferred` ≠ floor `waived` (m3).

## 0. Grammars & conventions

| Token | Grammar (regex) | Notes |
|---|---|---|
| `entry_id` / `command` | `^[a-z][a-z0-9-]*$` | catalog entry / `hitl:agentic-<command>` |
| `lens` | one of §2.1 | the ADV-2 lens set |
| `role` | `pm\|technical_advisor\|architect\|developer\|qa\|ops` | `docs/playbook/roles.md` |
| `duration` | `^[0-9]+(d\|w\|m)$` | catalog refresh cadence |
| risk factor values | enums in §4.1 | `stakes/side_effects/data/autonomy/scale` |

Validation is a **Python package** `tools/agentic-advisor/` (the composer, floor, map) + a **catalog**
(data) + a set of **skills** (`hitl:agentic-*`). The harness runs the conversation; Python does the
deterministic composition/floor/map; the catalog holds the expertise (ADR-A1/A2).

## 1. Files created / modified

| File | Change |
|---|---|
| `ai/shared/agentic/catalog.yaml` | the question/option catalog (§2), curated data |
| `ai/claude/skills/agentic-intake/SKILL.md` | the intake command (§3) — elicits, composes, renders the map |
| `ai/claude/skills/agentic-{classify,boundary,privilege,reliability,observability,memory,evals,deploy}/SKILL.md` | the 8 per-concern commands (§5) |
| `tools/agentic-advisor/compose.py` | relevance → workflow + floor/rung (§4) |
| `tools/agentic-advisor/floor.py` | the deterministic floor function (§4.1) |
| `tools/agentic-advisor/render_map.py` | the 2 core map renderings — terminal + Mermaid (§6); HTML/live deferred (M8) |
| `tools/agentic-advisor/records.py` | scenario record + decision record I/O (§7) |
| `ai/claude/pm/design-feature/SKILL.md` | **integration**: route ≥2-component + ≥1-edge into `hitl:agentic-intake` (§8, ADV-13) |
| `ai/codex/AGENTS.md` | **integration**: compound-surface routing rule (§8) |
| `ci/agentic-advisor/test_catalog_lint.py` / `test_compose.py` / `test_manifest_authoring.py` / `test_advisor_e2e.py` | the suites (test plan) |

The commands **author the manifest #10 validates** (§5.1) — including the `observability` block #10's
`check_observability` floor-gates (that check was added to #10 by its own CR-9 elevation under the
2026-07-22 hard directive, not at the Advisor's behest). The one remaining exception, the **kill-switch**,
writes a **declared artifact** into the decision record (§5.2, ADR-A5).

## 2. The catalog (`ai/shared/agentic/catalog.yaml`, ADR-A2)

```yaml
schema_version: "1.0"
owner: <role|name>                 # ADV-11: a named owner
refresh_cadence: 3m                # ADV-11: periodic (independent of change events)
entries:
  - id: side-effects
    lens: irreversibility
    role: architect
    ask_when: "true"               # predicate over the scenario record (§2.2); default "true"
    question: "Does any step take an action that is hard or impossible to undo (money, an order, an
               external send, provisioning, a write to a system of record)?"
    options: [none, reversible, irreversible]     # omit ⇒ free-text captured verbatim
    guidance: "Irreversible ⇒ gate it (you can't compensate). Reversible-multistep ⇒ consider a saga."
    recommend: simplest_fit        # enum[simplest_fit, none] (§5, menu commands only)
    consequence:                   # keyed by answer option → list[ConsequenceItem]
      irreversible: [ {kind: floor, target: "human-gate"}, {kind: command, target: "agentic-reliability"} ]
      reversible:   [ {kind: command, target: "agentic-reliability"} ]
      none:         [ ]
```

### 2.1 Lenses (ADV-2 — every one has ≥1 entry; `CAT-COVERAGE`)

`right-sizing · determinism-boundary · irreversibility · human-gate · privilege · topology · reliability ·
observability · kill-switch · memory · pii · portability · evaluation · cost · deployment · stakes-tier`.

### 2.2 `ask_when` predicate grammar

A boolean expression over the **scenario record** (§7.1) fields, evaluated by a small safe evaluator
(no arbitrary code): `components.count`, `edges.count`, `answers.<factor>`, `any_agent`, and the operators
`>= <= == != and or not in`. Examples: `components.count >= 2`, `answers.side_effects != "none"`,
`any_agent and answers.data in ["sensitive","pii"]`.

### 2.3 `consequence` — one exact shape (HLD §4.2, `CAT-SCHEMA`, round-5 B4)

An entry's `consequence` is a **map keyed by answer option → a list of `ConsequenceItem`**; each
`ConsequenceItem` is a **tagged union** (exactly one `kind`). The HLD and the lint use this same shape (the
round-5 reconciliation — no more "single union" vs "option-map" disagreement):

```yaml
consequence:            # map[ <option-or-"*"> -> list[ConsequenceItem] ]   ("*" = applies to any answer)
  <option>:
    - kind: enum[ classify | boundary | gate | command | floor | manifest_field | declared_artifact ]
      target: string    # command name | #10 manifest path | floor-rule id | artifact id
      note: string?      # optional
```
Lint (`test_catalog_lint.py`, `CAT-SCHEMA`): `consequence` is a non-empty option→list map; **every option in
the entry's `options` has a key** (or a `"*"` default); every list element is a valid tagged union with a
resolvable `target` — a `command` → a real `hitl:agentic-*`, a `manifest_field` → a real #10 field/path, a
`floor` → a real floor obligation; a `declared_artifact` target need **not** resolve to #10 and is **only**
valid for the **kill-switch** (observability now authors a `manifest_field`, not a declared artifact — B4);
every `role` is real.

## 3. The intake (`hitl:agentic-intake`, ADV-1/2/3/13/15)

Two-tier (ADV-1): the intake **elicits**; the per-concern commands **decide**. The skill:

1. **Assumes the compound surface — it does NOT re-select it (round-5 M1).** Surface selection already
   happened in `pm-design-feature` (the `agentic` gate → topology probe → route, HLD §3.1); the intake is
   only reached on the compound branch. It elicits the **full** component/edge detail (the probe captured
   only counts), but performs no second surface decision — the duplicate selector is removed.
2. **Walks the catalog adaptively (ADV-3).** For each entry whose `ask_when` holds against the scenario so
   far, asks the `question`, interprets the free-text answer into an `option` (or captures verbatim), and
   applies the entry's `consequence` to the scenario record.
3. **Composes the workflow (§4)** and **sets the floor (§4.1)**.
4. **Renders the evolving map (§6)** after each meaningful step and **writes the records (§7)**.

The harness runs the conversation; `compose.py`/`floor.py`/`render_map.py` do the deterministic work.

## 4. Composition (`compose.py`, ADR-A4) — the floor is DERIVED from #10 activation (round-5 B1)

The central round-4/round-5 defect was that the Advisor floor was hand-tuned (tier gates) while #10's
per-check activation fires on manifest *content* — so a control could be an Advisor "rung" while #10 made
it mandatory, and the team would defer it into a hard #10 failure. **The fix: the floor is a pure function
of #10's activation predicates.** A command is floor **iff** a #10 check it owns will activate on the
manifest the scenario implies. This makes *floor ≡ #10 activation* by construction, not by assertion.

```python
COMMANDS = ["agentic-classify","agentic-boundary","agentic-privilege","agentic-reliability",
            "agentic-observability","agentic-memory","agentic-evals","agentic-deploy"]

DEPENDS = {"agentic-boundary":["agentic-classify"], "agentic-privilege":["agentic-classify"],
           "agentic-reliability":["agentic-boundary"], "agentic-observability":["agentic-classify"],
           "agentic-memory":["agentic-classify"], "agentic-evals":["agentic-classify"],
           "agentic-deploy":["agentic-classify"]}

# Each Advisor command OWNS the #10 checks it must author valid input for. If any owned check will
# activate, the command is mandatory — the Advisor cannot let the team defer it, because #10 will block.
OWNS_CHECKS = {
  "agentic-classify":      ["check_classification"],
  "agentic-boundary":      ["check_boundary_legs","check_topology","check_references","check_authorization"],
  "agentic-privilege":     ["check_capabilities","check_scope_grammar"],
  "agentic-reliability":   ["check_async","check_lifecycle"],          # + non-#10 kill-switch/human-gate below
  "agentic-observability": ["check_observability"],
  "agentic-memory":        ["check_memory"],
  "agentic-evals":         ["check_eval_coverage"],
  "agentic-deploy":        [],                                          # no #10 check (records a decision)
}

# #10's activation predicates, mirrored from compound LLD §6.0 over the SCENARIO-implied manifest.
# The ACTIVATION-MIRROR test (§9) asserts this dict matches #10's real activation table field-for-field,
# so the two can never drift — the single source of truth is #10; this is its projection for planning.
ACTIVATES = {
  "check_classification": lambda s: is_compound(s),                    # ≥1 agent endpoint in a compound manifest
  "check_boundary_legs":  lambda s: any_agent_endpoint(s),             # any interaction with ≥1 agent endpoint (incl. agent→agent)
  "check_topology":       lambda s: has_interactions(s),
  "check_references":     lambda s: has_interactions(s),
  "check_authorization":  lambda s: any_into_agent(s),                 # any interaction whose `to` is an agent
  "check_capabilities":   lambda s: any_agent(s),                      # any domain kind ∈ {simple_agent, deep_agent}
  "check_scope_grammar":  lambda s: any_agent(s),                      # scopes appear once an agent has uses/identity
  "check_async":          lambda s: any_async(s),
  "check_lifecycle":      lambda s: any_long_running(s),
  "check_observability":  lambda s: any_agent(s),                      # hard directive (M3): floor for any agent
  "check_memory":         lambda s: any_memory(s),
  "check_eval_coverage":  lambda s: any_agent(s),                      # every agent independently evaluable + e2e
}

def floor_commands(s):
    """A command is floor iff a #10 check it owns will activate — floor ≡ #10 activation (B1)."""
    floor = {cmd for cmd, checks in OWNS_CHECKS.items()
             if any(ACTIVATES[c](s) for c in checks)}
    # non-#10 floor obligations owned by agentic-reliability (no #10 check exists for these):
    if human_gate_needed(s) or kill_switch_needed(s):
        floor.add("agentic-reliability")
    return floor

# Genuinely-optional rungs: a command with NO firing owned-check, offered only when its own data is present.
def rung_relevant(cmd, s):
    a = s["answers"]
    return {
      "agentic-reliability": any_async(s) or a["side_effects"] != "none",   # reliability depth beyond the floor obligation
      "agentic-memory":      any_memory(s),                                  # cross-session memory is a rung (a #10 floor only once declared)
      "agentic-deploy":      is_greenfield(s) or changes_platform(s)         # M6: not "always"
                             or adds_durable_runtime(s) or a.get("deploy_requested", False),
    }.get(cmd, False)

def compose(s, tier):
    floor    = floor_commands(s)                                # derived from #10 activation (B1)
    rungs    = {c for c in COMMANDS if c not in floor and rung_relevant(c, s)}
    included = floor | rungs                                    # floor ⊆ included by construction
    order    = topo_sort(included, DEPENDS)
    return {"workflow": order, "floor": sorted(floor),
            "rungs":   sorted(rungs)}                           # rungs are disjoint from floor
# Deterministic given s (tier affects DEPTH within a control, §4.1, not WHETHER it is floor).
# floor ⊆ workflow holds for ALL s — asserted by FLOOR-SUBSET; floor == {c : owned #10 check fires}
# is asserted against #10's real activation by ACTIVATION-MIRROR (§9).
```

### 4.1 The floor, tier, and depth (`floor.py`, ADR-A6)

**Which controls are floor** is decided by `floor_commands(s)` above (§4) — a pure function of #10
activation, no tier gate. **Tier does not decide *whether* a control is floor; it scales the *depth*
required within a floor control** (the proportionate lever, O6):

```python
STAKES={"internal","customer_facing","regulated"}; SIDE={"none","reversible","irreversible"}
DATA={"none","sensitive","pii"}; AUTONOMY={"assisted","supervised","autonomous"}; SCALE={"small","large"}

# non-#10 floor obligations (owned by agentic-reliability):
def human_gate_needed(s):  return s["answers"]["side_effects"] == "irreversible"
def kill_switch_needed(s): return (s["answers"]["autonomy"] in ("supervised","autonomous")
                                   and s["answers"]["side_effects"] != "none")

# DEPTH rules — what a floor control must contain, scaled by tier (examples; full table per command §5.1):
def observability_depth(tier):       # M3: real path at all tiers, heavier at higher tiers
    return "report_or_existing_surface" if tier <= 1 else "console"   # §5.1 check_observability tier rule
def privilege_granularity(tier):     return "per_capability" if tier >= 2 else "per_class"
def eval_depth(tier):                return "extended" if tier >= 2 else "baseline"
```

**`FLOOR-SUBSET` lint (B3, retained).** Over the swept risk-factor space × `tier ∈ {0..3}`,
`floor_commands(s) ⊆ set(compose(s,tier)["workflow"])` — trivially true now (`compose` unions the floor in),
the lint guards against a future edit reintroducing an intersection.

**`ACTIVATION-MIRROR` lint (B1, new).** Asserts `ACTIVATES` matches #10's real activation predicates
(compound LLD §6.0) check-for-check, and that every check in `OWNS_CHECKS` is a real #10 check. If #10's
activation changes, this test fails until `ACTIVATES` is re-synced — so the floor cannot silently diverge
from #10 again.

**Waiver — one model per enforced control (round-5 B1).** A floor control that #10 also enforces is dropped
by writing the **#10 waiver in #10's own store** (e.g. an eval drop → `docs/03-engineering/evals/waivers.yaml`;
a privilege/boundary drop → the manifest's tier-scoped waiver), which the Advisor **authors** and mirrors a
pointer into the decision record — so there is a *single* authoritative waiver #10 reads, never two stores
to reconcile. A floor control with **no** #10 check (the kill-switch) is waived in the decision record
alone. Either way: dropping a floor control silently is a **blocker** (`floor_dropped_no_waiver`); a **rung**
is **deferred** (recorded `deferred`, no blocker). `waived` ≠ `deferred` (m3). `tier` from
`.hitl/current-change.yaml` (absent ⇒ highest tier, fail-safe).

## 5. The commands (`ai/claude/skills/agentic-*`)

Each command: (a) asks its lens's catalog entries (if not already answered by the intake), (b) recommends
the simplest fit for any menu (ADR-A3), (c) **authors its output**. Independently runnable (ADV-1).

### 5.1 Command → #10 manifest fields authored

| Command | Authors (into `system-manifest.yaml`, validated by #10) |
|---|---|
| `agentic-classify` | `domains[d].kind`, `domains[d].kind_rationale` → #10 `check_classification` |
| `agentic-boundary` | the **inter-component contract** — `domains[callee].facade_apis[facade_name]` (the called signatures, keyed by facade name — the stable key for rerun reconciliation, m2) and `interactions[].authorization.allowed_callers` — so #10's `check_references`/`check_authorization` have data (round-4 B1); the `interactions[].request/response` legs (`validation`/`cost_bound`/`authority_bound`) → `check_boundary_legs` (incl. **agent→agent** legs, whose stochastic consumer requires cost+authority); the `interactions` themselves → `check_topology` |
| `agentic-privilege` | `domains[d].identity`, `domains[d].uses` → `check_capabilities` |
| `agentic-reliability` | `interactions[].async` (delivery/idempotency), `domains[d].lifecycle` (`human_gate`, `side_effect_key`) → `check_async`/`check_lifecycle`; and any `sagas` → `check_saga` |
| `agentic-memory` | `domains[d].memory` (store/pii/durability/reads/writes) → `check_memory` |
| `agentic-evals` | `domains[agent].evals.spec` (one per **agent** — independent per-agent eval) + one `segments[e2e].evals` → `check_eval_coverage` (core scope = agents + e2e; deterministic coverage optional, universal deferred — v3.2/M1) |
| `agentic-observability` | the top-level **`observability`** block — `tracing{convention,hops,attributes}` + `cost_budget` + **`eval_console{access,owner,ref}`** → #10 `check_observability` (**floor gate**, hard directive 2026-07-22) |

### 5.2 The declared-artifact exception (ADR-A5 — no #10 target today)

| Command | Declared artifact (into the decision record, human-reviewed) | Future #10 target |
|---|---|---|
| `agentic-reliability` (kill-switch) | a `kill_switch` block: `{scope, trigger, disables}` | none scoped (no #10 kill-switch field) |

**`agentic-observability` is no longer an exception (2026-07-22 hard directive).** It authors the real
top-level `observability` block (§5.1) that #10's **`check_observability` floor-gates** — a validated
manifest field, not a declared artifact. Only the kill-switch remains a pure declared artifact.

`agentic-deploy` writes the **deployment decision** to the decision record only (ADR-A7): `{recommend,
chosen, rejected:[{opt, cost}], drivers, portability:{governance, packaging, state_export}, carry_to:
platform-ops}`. It authors **no** manifest field and provisions nothing.

## 6. The evolving map (`render_map.py`, ADR-A8)

**Core scope (round-4 M8):** `render(scenario, composed) -> {terminal, mermaid}` — one data source, **two
core renderings** (ADV-15). The `html` rendering and the combined live mode (§6.2) are a **deferred
enhancement**, kept below as the follow-on target.

- **`terminal`** — a box-drawing topology + a `getting / available / not-needed` block, re-printed by the
  intake at each meaningful step. **getting** = floor ∪ adopted rungs; **available** = offered rungs;
  **not-needed** = `COMMANDS − included`, each with its **reason** = the catalog `guidance`/`note` of the
  gating answer (e.g. saga → "irreversible → you gate, not compensate").
- **`mermaid`** — the same graph + a Markdown table, written into `agentic-decisions.md` (§7.2).
- **`html`** *(deferred)* — an optional self-contained page (static-file publishing only; no server, ADR-A8).

### 6.1 Node-type visual vocabulary

Every rendering keys a node's visual off its type, so kind reads at a glance. The set:

| Type | HTML/Mermaid icon | Terminal ASCII |
|---|---|---|
| `agent` (stochastic) | hexagon, green | `⬡ name` (or `(name)`) |
| `service` (deterministic) | chip, steel | `▢ name` (or `[name]`) |
| `datastore` | cylinder, teal | `⛁ name` (or `(=name=)`) |
| `external` (actor/system) | cloud, dashed | `☁ name` (or `{name}`) |
| `store` (output) | stacked layers | `▤ name` |
| edge: `message`/event | dashed + `✉` | `··✉··▶` |
| marker: `human_gate` | `⛊` badge on the edge | `──⛊──▶` |

The type is `domains[d].kind` for agents/services, and derived for datastore/external/store from the
component's role in the manifest (a domain with no facade that only stores data → `datastore`; an
out-of-manifest actor → `external`). The demo at artifact `efd56c28` is the reference HTML rendering.

### 6.2 Combined "chat + live map" mode (ADR-A8) — *deferred enhancement (round-4 M8)*

> **Not core.** The combined live mode is a deferred follow-on with a defined host API; core is the
> `terminal` + `mermaid` renderings above. Spec retained as the follow-on target.

On an **artifact-capable surface** (a capability the harness reports), the intake **re-publishes the `html`
rendering to the same artifact URL after each meaningful step**, so the discussion and the map update
together. It is a **live view, not an input** — the artifact is sandboxed and cannot post answers back, so
the conversation remains the sole input. On a non-capable surface (bare CLI), the intake falls back to the
`terminal` rendering (the universal baseline). Either way HITL only **generates and publishes/prints** — it
runs no server.

Deterministic from the scenario record (regenerate-and-diff), so the map never drifts.

## 7. Records (`records.py`)

### 7.1 Canonical state (`.hitl/agentic-state.yaml`) — machine-readable, the single source (round-5 B4)

**One machine-readable YAML file is the authoritative state.** It holds three layers: the **elicited facts**
(topology + risk answers), the **authored outputs** each command produces (the structured data that becomes
#10 manifest fields — this is what round-4/round-5 B4 found missing: the old record could not actually
author facades/authorization/legs), and the **confirmed decisions** (choices/overrides/waivers/deferrals,
keyed by id). `records.py`, the composer, the floor, the map, and the manifest writers all read and write
*this* file; the Markdown decision record (§7.2) is **generated from it**, never the reverse. Every element
carries a stable `id` for re-run reconciliation (§7.3).

```yaml
schema_version: "2.0"
tier: int                                                   # 0..3, from .hitl/current-change.yaml
catalog: { version: string, last_refreshed: date,          # ADV-11 freshness in machine state (m3), not prose
           freshness_reviewed: bool, stale_finding: string? }  # Tier-3 review sets these; a stale finding is recorded here
# ── layer 1: elicited facts ──────────────────────────────────────────────
components: [ { id, name, kind: enum?[deterministic,simple_agent,deep_agent], kind_rationale: string? } ]
edges:      [ { id, from: component_id, to: component_id, kind: enum?[sync_call,async_task,event], side_effecting: bool? } ]
answers:    { stakes, side_effects, data, autonomy, scale }  # §4.1 closed-enum vocabulary
lens_answers: { <lens>: { <catalog_entry_id>: <option> } }  # provenance: which entry produced which answer
# ── layer 2: authored outputs (per command; become #10 manifest fields, §5.1) ────────────────
authored:
  facades:        [ { id, on: component_id, name, signature, mutations:[…], preconditions:[…], error_modes:[…] } ]  # → domains[].facade_apis[name]
  authorizations: [ { edge_id, allowed_callers:[component_id], audience?, credential_mode: enum[jit,static,none], justification? } ]  # → interactions[].authorization
  legs:           [ { edge_id, leg: enum[request,response,event], validation_ref?, cost_bound?, authority_bound?:[Scope] } ]  # → interactions[].{request,response,event}
  identities:     [ { component_id, principal, uses:[ {capability, scopes:[Scope]} ] } ]                            # → domains[].identity + domains[].uses
  memory:         [ { component_id, store, durability, retrieval, scope, pii, reads:[…], writes:[…] } ]              # → domains[].memory
  evals:          [ { target_type: enum[component,segment], target_id, kind: enum[eval], spec_path, approval? } ]    # → domains[].evals / segments[].evals
  observability:  { convention, hops:[edge_id], attributes:[…], cost_budget:{limit,unit}, eval_console:{access,owner,ref} }  # → top-level observability (§ compound 4.3)
  lifecycle:      [ { component_id, long_running, resumable, idempotent_resume, checkpoint, human_gate } ]           # → domains[].lifecycle
  kill_switch:    { scope, trigger, disables }               # declared artifact only (no #10 field, §5.2)
  deploy:         { recommend, chosen, rejected:[{opt,cost}], drivers, portability:{governance,packaging,state_export}, carry_to }  # decision record only
# ── layer 3: confirmed decisions (keyed by id; human-owned) ───────────────
decisions:  [ { id, attaches_to: <component|edge|lens id>, chosen, rejected:[…], rationale,
                state: enum[confirmed,stale,retired], override: bool } ]
waivers:    [ { control, store: enum[eval_waivers_yaml,manifest_waiver,decision_record], owner, reason, tier_limit, revisit } ]  # B1: one store per enforced control
deferrals:  [ { rung, reason } ]                             # rungs offered but not adopted (≠ waiver, m3)
```

Every command's **input** is the layers-1/2 state it needs and its **output** is the `authored.*` block it
owns (§5.1 maps each). Because the authored data is structured, the manifest writers can emit valid #10
fields, and `records.py` can reconcile decisions by `id` without parsing prose (the round-5 B4 fix).

### 7.2 Decision record (`docs/01-product/<feature>/agentic-decisions.md`) — a GENERATED view

The Markdown decision record is **rendered from `agentic-state.yaml`** (like the map, regenerate-and-diff),
never hand-authored. It presents the scenario, the composed workflow (floor/rungs/not-needed + reasons),
every decision (`decisions[]` — chosen/rejected/rationale), waivers, deferrals, the declared kill-switch
artifact, and the deploy decision — all read from the canonical state. It is human-**readable**; the canonical
state is machine-**authoritative**. (`REC-GEN` asserts the Markdown is a pure function of the YAML.)

### 7.3 Re-run and mutation semantics (round-4 M4)

A re-run is **recompute + reconcile, human-confirm before write** — never a blind regenerate that discards
human decisions:

1. **Recompute the derived state** — `compose(scenario, tier)` is a pure function of the scenario record, so
   the workflow/floor/rungs are recomputed deterministically (ADV-12). Derived state is never hand-edited.
2. **Reconcile human-owned decisions by `id`.** Menu choices, overrides, waivers, and deferrals are keyed by
   the component/edge/lens `id` they attach to. On re-run: an id whose inputs are **unchanged** keeps its
   recorded decision; an id that is **new** is elicited fresh; an id whose **gating inputs changed** (e.g. a
   component's `kind` changed, or `side_effects` moved to `irreversible`) has its decision **flagged stale
   and surfaced for re-confirmation** — it is neither silently kept nor silently dropped (ADV-9).
3. **A removed component/edge** carries its dependent decisions to a `retired` list in the record (not
   deleted), so an audit trail survives.
4. **Human confirms before write.** The reconciled record is presented as a diff (added / changed / stale /
   retired); the human confirms, and only then is `agentic-decisions.md` **regenerated** from the confirmed
   state (ADV-7). No silent overwrite of a human decision.

This makes the record durable and re-runnable (ADV-7 acceptance scenario 6) with defined mutation
semantics, closing the round-4 M4 gap.

## 8. Integration (ADV-13, ADR-A9)

- **`pm-design-feature`**: the "what is the delivery surface?" step gains a **cheap topology probe** (two
  questions — component count; does any component call/hand-off/message another?) that runs **before** the
  surface is chosen, so there is no circularity (round-4 B2). The selector: `if probe.components ≥ 2 and
  probe.edges ≥ 1: invoke hitl:agentic-intake` (the compound branch, which then elicits the full detail); a
  single-component product continues on the existing single-agent path unchanged. The Advisor **precedes**
  the design track; it does not gate or replace it.
- **`ai/codex/AGENTS.md`**: add the **same probe-then-route rule** — the identical ≥2-component + ≥1-edge
  probe selects the compound-agentic surface and the composed workflow rather than the single-agent template.

Both are small, enumerated edits to existing files. The probe is the single selector (no separate detector);
the full `hitl:agentic-intake` fills in the complete component/edge detail only on the compound branch.

## 9. Test file layout (see `03-test-plan.md` for cases)

```
ci/agentic-advisor/
  test_catalog_lint.py        # §2 — CAT-*
  test_activation_mirror.py   # §4 — ACTIVATION-MIRROR: ACTIVATES matches #10 LLD §6.0 field-for-field (B1)
  test_compose.py             # §4/§4.1 — COMPOSE-LOW/HIGH/FLOOR-SUBSET/FLOOR-EQ-ACTIVATION/PRUNE-DEPLOY/KILL-SWITCH
  test_manifest_authoring.py  # §5.1 — AUTHOR-* (incl. AUTHOR-CONTRACT facade+authz, B1) run through #10's real check_manifest_agentic.py
  test_rerun.py               # §7.3 — RERUN-* (reconcile/stale/retired/confirm, M4)
  test_advisor_e2e.py         # E2E-SUPPORT/STANDALONE-CMD/ROUTE-*/MAP-*/DEPLOY-*
```

## 10. LLD decisions

- **L1:** the composer/floor/map are **deterministic Python** over the scenario record; the catalog is
  data; the commands are skills. This keeps the expertise reviewable (catalog), the logic testable
  (Python), and the conversation in the harness (skills) — ADR-A1/A2/A4.
- **L2:** the floor is a **union of monotone predicates** (§4.1), computed **obligation-first** so `floor ⊆
  workflow` (the `FLOOR-SUBSET` lint, round-4 B3), with a recorded-waiver escape hatch; two runs on the same
  declared factors compute the identical floor (ADV-12), but human-declared factors are a softer input
  mitigated by the categorical vocabulary.
- **L3:** commands **author manifest fields** #10 validates (§5.1) — including the **contract seam**
  (`facade_apis` + `authorization`, B1) and the **`observability` block** #10's `check_observability`
  floor-gates (hard directive); the **kill-switch** is the one remaining **declared artifact** (§5.2) with
  no #10 target yet — stated, not faked (ADR-A5).
- **L4:** ADV-13 integration is **two small edits** to `pm-design-feature`/`AGENTS.md` (§8), routed by a
  **cheap topology probe** (no circularity, B2) — precede for compound, skip for simple, never replace (ADR-A9).
- **L5 (core scope lock, round-4):** the LLD implements the **minimal sound core** — per-agent+e2e eval
  authoring (not universal), terminal+Mermaid map (HTML/live deferred), declared-saga validation via #10
  (required-when deferred). Deferred mechanisms are marked in-place and tracked in
  [`../agentic-core-scope.md`](../agentic-core-scope.md).
