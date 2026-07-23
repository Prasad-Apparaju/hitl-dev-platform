# Agentic Design Advisor: LLD

> **v4.1 (2026-07-23) — one intake + recommendation report; neutral handoff.** The Advisor is **one
> `hitl:agentic-intake` command** that elicits, recommends (a report whose sections are the relevant lenses —
> not 8 commands, round-9 M9), records, and hands off a **neutral `agentic-design-handoff.yaml`**
> (`proposed_kind`s + recommendation IDs + target-path hints — **no** manifest field, not even `kind`, round-9
> B2). It **authors no manifest field**; a human authors the manifest, #10 validates it. **Removed** (the
> auto-authoring apparatus): the manifest writer, `OWNS_CHECKS`/imported-`ACTIVATES`/`floor ≡ activation`/
> `OWNERSHIP-COMPLETE`/`AUTHOR-COMPLETE`, `manifest_features`, and the `authored.*` state layer. Implements
> HLD [`01-design.md`](01-design.md) v4.1 + ADRs A5/A6. Status: **v4.1 — round-10 fixes applied.**

## 0. Grammars & conventions

| Token | Grammar (regex) | Notes |
|---|---|---|
| `entry_id` / `lens` | `^[a-z][a-z0-9-]*$` | catalog entry / report-section lens (there is one command, `hitl:agentic-intake`) |
| `lens` | one of §2.1 | the ADV-2 lens set |
| `role` | `pm\|technical_advisor\|architect\|developer\|qa\|ops` | `docs/playbook/roles.md` |
| `duration` | `^[0-9]+(d\|w\|m)$` | catalog refresh cadence |
| risk factor values | enums in §4.1 | `stakes/side_effects/data/autonomy/scale` |

Validation is a **Python package** `tools/agentic-advisor/` (the composer, floor, map) + a **catalog**
(data) + **one skill** (`hitl:agentic-intake`). The harness runs the conversation; Python does the
deterministic composition/floor/map; the catalog holds the expertise (ADR-A1/A2).

## 1. Files created / modified

| File | Change |
|---|---|
| `ai/shared/agentic/catalog.yaml` | the question/option catalog (§2), curated data — each lens's questions + `consequence` |
| `ai/claude/skills/agentic-intake/SKILL.md` | **the one command** (§3) — elicits, recommends (all lenses as report sections, §5), records, renders the map, writes the handoff |
| `tools/agentic-advisor/compose.py` | relevance → recommended report sections + recommended floor/rung (§4) |
| `tools/agentic-advisor/render_map.py` | the 2 core map renderings — terminal + Mermaid (§6); HTML/live deferred (M8) |
| `tools/agentic-advisor/records.py` | canonical state + decision record + **neutral `agentic-design-handoff.yaml`** I/O (§7) |
| `ai/claude/pm/design-feature/SKILL.md` | **integration**: gate→probe→route ≥2-component + ≥1-edge into `hitl:agentic-intake` (§8, ADV-13) |
| `ai/codex/AGENTS.md` | **integration**: the same gate→probe→route rule (§8) |
| `ci/agentic-advisor/test_catalog_lint.py` / `test_compose.py` / `test_handoff.py` / `test_advisor_e2e.py` | the suites (test plan) |

The Advisor is **one intake command** that **elicits, recommends, and records** — it **authors no manifest
field** (re-scope 2026-07-23, ADR-A5). Each lens is a **report section** (not a separate command) producing a
recommendation + a decision-record entry + a `target_path_hint` in the neutral handoff (§7); a **human**
authors the real manifest in the design phase, and **#10 validates** it. Observability + PM eval-console is
**recommended** by the Advisor and **enforced** by #10's `check_observability` on the human-authored
manifest. There is no manifest writer and no #10 change.

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
    recommend: simplest_fit        # enum[simplest_fit, none] (§5, recommendation lenses only)
    consequence:                   # keyed by answer option → list[ConsequenceItem]
      irreversible: [ {kind: floor, target: "human-gate"}, {kind: lens, target: "reliability"} ]
      reversible:   [ {kind: lens, target: "reliability"} ]
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
`ConsequenceItem` is a **tagged union** (exactly one `kind`). Because the Advisor **recommends and records**
(it authors no manifest field), a consequence points at a *recommendation* or a *decision-record entry*, not
a `#10 field`:

```yaml
consequence:            # map[ <option-or-"*"> -> list[ConsequenceItem] ]   ("*" = applies to any answer)
  <option>:
    - kind: enum[ classify | boundary | gate | lens | floor | recommendation | recorded_artifact ]
      target: string    # lens id (report section) | floor-rule id | recommendation id | recorded-artifact id
      note: string?      # optional; becomes a rationale line + a handoff target_path_hint
```
Lint (`test_catalog_lint.py`, `CAT-SCHEMA`): `consequence` is a non-empty option→list map; **every option in
the entry's `options` has a key** (or a `"*"` default); every list element is a valid tagged union with a
resolvable `target` — a `lens` → a real report-section lens, a `floor` → a real floor-rule id, a
`recommendation`/`recorded_artifact` → a recorded id. **No `manifest_field` kind exists** (the Advisor never
targets a #10 field — re-scope 2026-07-23); the observability and kill-switch controls are `recommendation`
entries the design must satisfy. Every `role` is real.

## 3. The intake (`hitl:agentic-intake`, ADV-1/2/3/13/15)

One command (ADV-1): `hitl:agentic-intake` **elicits**, then each lens **section recommends + records**. The skill:

1. **Assumes the compound surface — it does NOT re-select it (round-5 M1).** Surface selection already
   happened in `pm-design-feature` (the `agentic` gate → topology probe → route, HLD §3.1); the intake is
   only reached on the compound branch. It elicits the **full** component/edge detail (the probe captured
   only counts), but performs no second surface decision — the duplicate selector is removed.
2. **Walks the catalog adaptively (ADV-3).** For each entry whose `ask_when` holds against the scenario so
   far, asks the `question`, interprets the free-text answer into an `option` (or captures verbatim), and
   applies the entry's `consequence` to the scenario record.
3. **Composes the recommended workflow (§4)** and the **recommended floor (§4.1)**.
4. **Renders the evolving map (§6)** after each meaningful step and **writes the records + handoff (§7)**.

The harness runs the conversation; `compose.py`/`render_map.py`/`records.py` do the deterministic work.

## 4. Composition (`compose.py`, ADR-A4) — a RECOMMENDATION engine (re-scope 2026-07-23)

The composer recommends **which lenses this change needs** and a **recommended floor** (the controls that
shouldn't be skipped) from **Tier + risk factors** — expert judgment. It does **not** author a manifest,
import or predict #10's activation, or prove any equivalence: the Advisor recommends, and #10 enforces its
own checks at design time on the *human-authored* manifest. Relevance gives proportionality (a lens with no
scenario data contributes no report section); the floor rules give the recommended-mandatory set.

```python
# LENSES (report sections, not separate commands — round-9 M9). Stable order = topo tie-break.
LENSES = ["classify","boundary","privilege","reliability","observability","memory","evals","deploy"]

DEPENDS = {"boundary":["classify"], "privilege":["classify"], "reliability":["boundary"],
           "observability":["classify"], "memory":["classify"], "evals":["classify"], "deploy":["classify"]}

# ONE component schema everywhere (round-10 B3): the composer/map/rerun read `proposed_kind` — the same
# field the canonical state (§7.1) and fixtures use. The `classify` lens runs FIRST (DEPENDS), so
# `proposed_kind` is populated before any other lens or the floor needs `any_agent` (no circularity).
def any_agent(s):  return any(c.get("proposed_kind") in ("simple_agent","deep_agent") for c in s["components"])
def any_async(s):  return any(e.get("transport") in ("async_task","event") for e in s["edges"])  # edge transport (factual), not a design kind

def relevant(lens, s):
    """Proportionality: a lens is a report section only if the scenario has data for it.
    All scenario flags live under s["answers"] (one canonical location — round-9 M1)."""
    a = s["answers"]
    return {
      "classify":      any_agent(s),                                 # right-size the components
      "boundary":      len(s["edges"]) > 0 and any_agent(s),         # inter-component contract + boundary
      "privilege":     any_agent(s),
      "reliability":   any_async(s) or a["side_effects"] != "none"
                       or a["autonomy"] in ("supervised","autonomous"),
      "observability": any_agent(s),                                 # hard directive: any agentic system
      "memory":        a.get("memory_hint", False),                  # canonical input: answers.memory_hint (no components[].memory field)
      "evals":         any_agent(s),
      "deploy":        a.get("greenfield") or a.get("changes_platform")           # M1: read from answers
                       or a.get("adds_durable_runtime") or a.get("deploy_requested", False),  # M6
    }.get(lens, False)

# The RECOMMENDED floor — a deterministic function of the safety-relevant risk factors (expert judgment,
# NOT #10 activation). Membership uses the factors it names (round-9 M2 — honest); Tier + data/stakes/scale
# inform recommended DEPTH (§4.1), not membership. #10 enforces downstream; this is advice.
def recommended_floor(s):
    a = s["answers"]
    floor = set()
    if any_agent(s):
        floor |= {"classify", "privilege", "observability", "evals"}
    if len(s["edges"]) > 0 and any_agent(s):
        floor.add("boundary")
    if a["side_effects"] == "irreversible":                                # recommend a human gate
        floor.add("reliability")
    if a["autonomy"] in ("supervised","autonomous") and a["side_effects"] != "none":  # recommend a kill-switch
        floor.add("reliability")
    if any_async(s):                                                       # an async_task/event needs idempotency/DLQ design
        floor.add("reliability")                                          # → reliability IS floor-level advice (round-10 blocker 4)
    return floor

def compose(s):
    floor    = recommended_floor(s)
    included = {l for l in LENSES if relevant(l, s)} | floor               # floor ⊆ included report sections
    rungs    = included - floor                                            # offered, deferrable
    order    = topo_order(included, DEPENDS)                               # deterministic: topo, tie-break by LENSES index
    return {"report_sections": order, "floor": sorted(floor), "rungs": sorted(rungs)}
# Deterministic given s → identical recommendation report (ADV-12). There is NO computed `tier`→depth
# function (round-10 blocker 4 — resolved by subtraction): the report may *note* a suggested depth per
# control as advisory prose (heavier at higher Tier/stakes), but depth is a human-confirmed recommendation,
# not a computed field. The floor is a risk-factor RECOMMENDATION; #10 is the gate (ADR-A6).
```

### 4.1 The recommended floor, Tier depth, and recording a skip (ADR-A6)

The floor is **advice** (§4). Membership is fixed by the safety-relevant factors (§4 `recommended_floor`),
**not** by Tier. Separately, `Tier`/`stakes` may inform a **human-confirmed advisory *depth note*** per floor
control (a suggestion, **not** a composer input and **not** a computed field — round-10 blocker 4); the note
never changes membership. Illustrative depths:

| Recommended floor control | Tier 0–1 recommended depth | Tier 2+ recommended depth |
|---|---|---|
| `agentic-observability` | an existing approved surface **or** a generated report; basic trace attributes | a fuller PM eval **console**; richer tracing |
| `agentic-privilege` | per-capability-class bounds | per-capability (and per-resource at Tier 3) |
| `agentic-evals` | a baseline spec per agent + e2e | approved + extended cases |
| `agentic-boundary` | validation on stochastic→deterministic legs | + reviewed cost/authority bounds |

Depth is a **recommendation**; the actual enforcement is #10's on the human-authored manifest (e.g. #10's
`check_observability` `access_ok(tier)` enforces the report-vs-console rule; `check_capabilities` enforces
privilege containment at any depth). The Advisor never claims a rule #10 does not implement.

**Recording a skip — never silent; the hard gate is downstream (ADR-A6, ADV-12).** A team may skip a
recommended-floor control, but the Advisor **records the skip** in the decision record `skips: [{control,
owner, reason}]` and **surfaces it** in the handoff. The Advisor is **not** the gate — it recommends. The
**hard block-or-waive** happens at design time in **#10** (its validators + HITL's tier/waiver process,
FR-25) on the human-authored manifest. So "can't be skipped silently" holds by *recording* here, and
"hard-blocked until … or waived" holds *downstream at #10*. A **rung** not adopted is **deferred** (recorded
`deferred`); `skip` (a recommended-floor control) ≠ `deferred` (a rung) — distinct states.

## 5. The lenses (report sections of the one skill `ai/claude/skills/agentic-intake/`)

Each lens is a **section of the recommendation report** (not a separate command — round-9 M9): it (a) reads
its catalog answers from the intake, (b) recommends the simplest fit for any menu (ADR-A3), (c) **records a
decision-record entry + a `target_path_hint` in the handoff**. No lens authors a manifest field.

### 5.1 Lens → recommendation + decision-record entry + target-path hint

Each lens records **what the design should do** (a recommendation) and a **`target_path_hint`** (WHERE in the
manifest the design role authors it, §7.4) — never the value, which **#10 then validates** after a human
authors it.

| Lens | Recommends + records (→ decision record + `target_path_hint` for the design role) |
|---|---|
| classify | a `proposed_kind` + rationale per component; for a deep agent, a hint to author `deep_agent{planner, subagents, context_isolation, gates, guardrails}` |
| boundary | the recommended inter-component contract — which `facade_apis` / `interactions.authorization` the design must declare, and trust-leg controls (validation on stochastic→det; cost/authority into agents) |
| privilege | recommended capability/identity bounds per agent (`identity` + least-privilege `uses`) |
| reliability | recommended async/idempotency/DLQ controls + lifecycle (human-gate, resumability) + a recommended **kill-switch** |
| memory | recommended memory/PII controls (durability, retrieval, PII handling, high-stakes guardrail) |
| evals | recommended eval coverage — a spec per **agent** + one **e2e** flow (core scope) |
| observability | a recommended observability/tracing plan + **PM eval-console** — which #10's `check_observability` enforces on the authored manifest (hard directive 2026-07-22) |

The **deploy** lens records the **deployment decision** (ADR-A7): `{recommend, chosen, rejected:[{opt,cost}],
drivers, portability:{governance, packaging, state_export}, carry_to: platform-ops}`. A human carries it to
the platform/ops track; it provisions nothing and authors no manifest field.

## 6. The evolving map (`render_map.py`, ADR-A8)

**Core scope (round-4 M8):** `render(scenario, composed) -> {terminal, mermaid}` — one data source, **two
core renderings** (ADV-15). The `html` rendering and the combined live mode (§6.2) are a **deferred
enhancement**, kept below as the follow-on target.

- **`terminal`** — a box-drawing topology + a `getting / available / not-needed` block, re-printed by the
  intake at each meaningful step. **getting** = floor ∪ adopted rungs; **available** = offered rungs;
  **not-needed** = `LENSES − included`, each with its **reason** = the catalog `guidance`/`note` of the
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

**`role` is a single, directly-elicited, required enum on each component** (round-10 blocker 7 — total and
single-valued by construction; no derivation from `proposed_kind` + flags, so there is no flag-conflict or
"unclassified component selects none" case, and no dependency on `proposed_kind` being set yet). The intake
asks one question per component — *"what is this: an agent, a service, a datastore, an external system, or
an output store?"* — so `role ∈ {agent, service, datastore, external, store}` is always exactly one value.
An external system or output store the flow talks to is **elicited as a component** with `role: external` /
`role: store`, so `edges.from/to` always resolve to a `components[].id`. The map vocabulary:

| `role` | meaning | icon |
|---|---|---|
| `agent` | a stochastic component (LLM-in-a-loop) | hexagon |
| `service` | a deterministic component with behavior | chip |
| `datastore` | a component that holds state, no logic | cylinder |
| `external` | a system outside the team's build | cloud/dashed |
| `store` | an output sink the flow writes to | stacked |

`role` (map vocabulary) and `proposed_kind` (the classify lens's classification recommendation) are distinct
single-valued fields — `role` is elicited directly; the renderer reads the **scenario** only (no manifest
yet). A `ROLE-TOTAL` test asserts every component has exactly one `role`. The demo at artifact `efd56c28` is
the reference HTML rendering.

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

### 7.1 Canonical state (`.hitl/agentic-state.yaml`) — the scenario + the decisions (re-scope 2026-07-23)

**One machine-readable YAML file is the authoritative state**, holding two layers: the **elicited facts**
(topology + risk answers) and the **recommendations + confirmed decisions** (keyed by id). There is **no
`authored.*` manifest-fields layer** — the Advisor does not author manifest fields; it records
recommendations and generates the neutral **`agentic-design-handoff.yaml`** (§7.4). `records.py`, the
composer, and the map read/write *this* file; the decision record (§7.2) and the handoff (§7.4) are
**generated from it**.

```yaml
schema_version: "3.0"
tier: int                                                   # 0..3, from .hitl/current-change.yaml
catalog: { version: string, last_refreshed: date, freshness_reviewed: bool, stale_finding: string? }  # ADV-11 freshness (m3)
# ── layer 1: elicited facts ──────────────────────────────────────────────
components: [ { id, name, role: enum[agent,service,datastore,external,store],   # REQUIRED, directly elicited — total & single-valued (§6.1, blocker 7)
               proposed_kind: enum?[deterministic,simple_agent,deep_agent], rationale: string? } ]  # the classify lens's classification RECOMMENDATION (not a manifest `kind`)
edges:      [ { id, from: component_id, to: component_id, transport: enum?[sync_call,async_task,event], side_effecting: bool? } ]  # `transport` (a factual edge property, not a design kind); from/to always resolve — every node is a component (M8)
answers:    { stakes, side_effects, data, autonomy, scale,               # §4 closed-enum vocabulary
              greenfield: bool?, changes_platform: bool?, adds_durable_runtime: bool?,   # deploy relevance (M1 — one location)
              deploy_requested: bool?, memory_hint: bool? }              # all composition flags live here
lens_answers: { <lens>: { <catalog_entry_id>: <option> } }  # provenance: which entry produced which answer
# ── layer 2: recommendations + decisions (keyed by id; human-owned) ───────
recommendations: [ { id, lens, control, text, target_path_hint: string,  # what the design should do + WHERE (a manifest-path hint, not a value)
                     kind: enum[floor,rung,recorded_artifact] } ]        # floor = recommended-mandatory; rung = offered
decisions:  [ { id, attaches_to: <component|edge|lens id>, chosen, rejected:[…], rationale,
                depends_on:[<state field path>], state: enum[confirmed,stale,retired], override: bool } ]  # depends_on = fields that, if changed, make this stale (§7.3)
skips:      [ { control, owner, reason } ]                   # a recommended-floor control the team chose to skip — recorded, never silent (ADR-A6)
deferrals:  [ { rung, reason } ]                             # a rung offered but not adopted (≠ skip, distinct states)
deploy:     { recommend, chosen, rejected:[{opt,cost}], drivers, portability:{governance,packaging,state_export}, carry_to }
```

The map's richer vocabulary is the **directly elicited** `components[].role` (§6.1) — asked as one question
per component at elicitation time (a required single-valued enum), never derived from `proposed_kind`+flags
and never from a manifest (there is none). The Advisor **records skips**, not
`manifest-waivers` — the hard waive-or-block is #10's, downstream on the human-authored manifest (ADR-A6).

### 7.2 Decision record (`docs/01-product/<feature>/agentic-decisions.md`) — a GENERATED view

The Markdown decision record is **rendered from `agentic-state.yaml`** (regenerate-and-diff), never
hand-authored. It presents the scenario, the recommended workflow (floor/rungs/not-needed + reasons), every
decision (chosen/rejected/rationale), recorded skips, deferrals, and the deploy decision — all read from the
canonical state. (`REC-GEN` asserts the Markdown is a pure function of the YAML.)

### 7.3 Re-run and mutation semantics (round-4 M4)

A re-run is **recompute + reconcile, human-confirm before write** — never a blind regenerate that discards
human decisions:

1. **Recompute the derived state** — `compose(scenario)` is a pure function of the scenario record (no `tier`
   input — round-10 blocker 4), so
   the workflow/floor/rungs are recomputed deterministically (ADV-12). Derived state is never hand-edited.
2. **Reconcile human-owned decisions by `id`.** Menu choices, overrides, skips, and deferrals are keyed by
   the component/edge/lens `id` they attach to. On re-run: an id whose inputs are **unchanged** keeps its
   recorded decision; an id that is **new** is elicited fresh; an id whose **gating inputs changed** (e.g. a
   component's `proposed_kind` changed, or `side_effects` moved to `irreversible`) has its decision **flagged stale
   and surfaced for re-confirmation** — it is neither silently kept nor silently dropped (ADV-9).
3. **A removed component/edge** carries its dependent decisions to a `retired` list in the record (not
   deleted), so an audit trail survives.
4. **Human confirms before write.** The reconciled record is presented as a diff (added / changed / stale /
   retired); the human confirms, and only then are `agentic-decisions.md` **and the handoff (§7.4)**
   **regenerated** from the confirmed state (ADV-7). No silent overwrite of a human decision.

This makes the record durable and re-runnable (ADV-7 acceptance scenario 6) with defined mutation
semantics, closing the round-4 M4 gap.

### 7.4 The design handoff — a NEUTRAL file, not a manifest (ADV-8, round-9 B2)

The handoff is **`docs/01-product/<feature>/agentic-design-handoff.yaml`** — explicitly **NOT**
`system-manifest.yaml`. It carries **recommendations and hints only**: no `system-manifest.yaml` field
appears, **not even `kind`** (a component kind is a design classification the architect must author). A
component carries its **elicited `role`** (the required map enum) and a `proposed_kind` (a recommendation),
an edge is a neutral `connection` with a factual `transport`, and every control is a recommendation id with a
**target-path hint** telling the design role *where* to author it.

```yaml
# GENERATED by the Agentic Design Advisor — a RECOMMENDATION HANDOFF, not a design.
# The design role authors system-manifest.yaml ANEW from this; #10 validates that. Nothing here is a manifest field.
schema_version: "1.0"
feature: refund-assistant
components:                                  # role = elicited map enum (required); proposed_kind = a RECOMMENDATION, never a `kind:` field
  - { id: intake_agent,   role: agent, proposed_kind: simple_agent,  rationale: "bounded classify task" }
  - { id: resolver_agent, role: agent, proposed_kind: simple_agent,  rationale: "bounded draft task" }
connections:                                 # neutral — NOT `interactions`; `transport` is the factual edge property
  - { from: intake_agent, to: resolver_agent, transport: async_task }
recommendations:                             # the floor/rungs by id; ONE representation — each carries its own
                                             # target_path_hint (a WHERE-to-author string, not a value). m2 fix:
                                             # no separate `target_paths` list, so there is nothing to keep in sync.
  - { id: r-priv-1,  lens: privilege,     control: "least-privilege identity+uses per agent", depth_note: per_class,
      target_path_hint: "domains[<agent>].identity + .uses" }
  - { id: r-bound-1, lens: boundary,      control: "validate the proposed refund before the service trusts it",
      target_path_hint: "interactions[].response.validation + callee facade_apis" }
  - { id: r-obs-1,   lens: observability, control: "tracing + PM eval-console", depth_note: report,
      target_path_hint: "top-level observability{tracing,eval_console}  (#10 check_observability enforces)" }
  - { id: r-eval-1,  lens: evals,         control: "per-agent + one e2e eval",
      target_path_hint: "domains[<agent>].evals + segments[e2e].evals" }
skips: []                                    # a recorded skip {control,owner,reason} — NOT a #10 waiver
```
`recommendations[].id` is unique; each has exactly one `target_path_hint` (a manifest *path*, never a value);
`depth_note` is an **advisory** annotation (a human-confirmed suggestion, not a computed field — round-10
blocker 4). `HANDOFF-REF-INTEGRITY` (§9) asserts id uniqueness and that every hint is a path string.

Every value is a `proposed_*` recommendation or a `*_hint` — **no valid manifest field**. A human authors
the real manifest; **#10 validates** it. `HANDOFF`/`NO-AUTHOR` (§9) assert the file contains **no**
`system-manifest.yaml` field value (no `kind`, no `interactions`) and that every recommended-floor control
has a `recommendations` entry + exactly one inline `target_path_hint`.

## 8. Integration (ADV-13, ADR-A9)

One selector sequence, exactly as ADR-A9 (round-6 M3 — no other ordering appears here):

1. **`agentic` gate** — `pm-design-feature`'s existing "what is the delivery surface?" answer. **Not
   agentic** ⇒ the deterministic/single flow runs unchanged and the probe does not fire (so a 2-service
   deterministic app never misroutes).
2. **topology probe** (agentic only) — two questions: component count; does any component call/hand-off/
   message another?
3. **route** — `if probe.components ≥ 2 and probe.edges ≥ 1: invoke hitl:agentic-intake` (compound branch,
   which then elicits full detail); else the existing single-agent path.

**`ai/codex/AGENTS.md`** gets the identical gate→probe→route rule. The full `hitl:agentic-intake` does
**not** re-select the surface (LLD §3) — it only fills in detail on the compound branch. Two small enumerated
edits; no separate detector.

## 9. Test file layout (see `03-test-plan.md` for cases)

```
ci/agentic-advisor/
  test_catalog_lint.py        # §2 — CAT-*
  test_compose.py             # §4 — COMPOSE-LOW/HIGH (recommended workflow + floor), PRUNE-DEPLOY, FLOOR-SKIP
  test_handoff.py             # §7.4 — HANDOFF/NO-AUTHOR (neutral: role + proposed_kind + connection transport + inline hints; NO manifest field), REC-GEN
  test_rerun.py               # §7.3 — RERUN-* (reconcile/stale/retired/confirm incl. a proposed_kind change, M4)
  test_advisor_e2e.py         # E2E-SUPPORT/ROUTE-*/MAP-*/DEPLOY-*
```

## 10. LLD decisions

- **L1:** the composer/map are **deterministic Python** over the scenario record; the catalog is data; the
  commands are skills. Expertise reviewable (catalog), logic testable (Python), conversation in the harness
  (skills) — ADR-A1/A2/A4.
- **L2:** the floor is a **risk-factor recommendation** — membership from agent presence, edges, irreversible
  side-effects, autonomy+side-effects, and async (§4/§4.1); `Tier`/`stakes` inform only an **advisory depth
  note**, never membership (round-10 blocker 4). It is advice, not a gate; a skip is **recorded** (never
  silent), and the hard block-or-waive is **downstream at #10** on the human-authored manifest (ADR-A6). Two
  runs on the same declared factors recommend the identical floor (ADV-12).
- **L3:** the intake's **lens sections recommend + record** (§5.1) and contribute `proposed_*` entries +
  `target_path_hint`s to the **neutral handoff** (§7.4) — they **author no manifest field**, and there is
  **no manifest skeleton**. A human authors the manifest; **#10 validates** it. Observability is
  recommended (Advisor) + enforced (#10 `check_observability`); the kill-switch is a recorded recommendation
  (ADR-A5). No manifest writer, no floor≡activation, no #10 change.
- **L4:** ADV-13 integration is **two small edits** to `pm-design-feature`/`AGENTS.md` (§8), routed by a
  **cheap topology probe** (no circularity, B2) — precede for compound, skip for simple, never replace (ADR-A9).
- **L5 (core scope):** terminal+Mermaid map (HTML/live deferred, #43); the deferred compound-side items
  (universal eval, saga required-when, delegated authority) are #10/#42 concerns, not the Advisor's — the
  Advisor only *recommends* the core controls. See [`../agentic-core-scope.md`](../agentic-core-scope.md).
