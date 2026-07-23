# Agentic Design Advisor: LLD

> **RE-SCOPED 2026-07-23 (v4) — elicit + recommend + record + hand off. This LLD is being rewritten to the
> new model and the sections below that describe manifest AUTHORING are superseded.** Removed: the composer's
> `compose.py` **manifest-authoring apparatus** (`PRIMARY_CHECKS`/`OWNS_CHECKS`/`SECONDARY_OWNERS`, the
> imported-`ACTIVATES` floor, `floor_commands`, `manifest_features`), the **manifest writer** (§5.1
> command→field map, §7.1.1 writer/merge), `OWNERSHIP-COMPLETE`/`AUTHOR-COMPLETE`, and the canonical state's
> `authored.*` layer. **Retained + reframed:** the intake + catalog (§2/§3), the **composer as a
> recommendation engine** (which lenses are relevant + a Tier+risk recommended floor — §4), the commands as
> **recommend + record** (§5), the **decision record + manifest-skeleton handoff** (§7), the terminal+Mermaid
> map (§6), and the routing (§8). The **canonical state** keeps the scenario + **decisions/recommendations**
> (no `authored.*` manifest fields). Implements HLD [`01-design.md`](01-design.md) v4 + ADRs (A5/A6
> rewritten). Status: **v4 re-scope applied — elicit + recommend + record + hand off.**

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
| `tools/agentic-advisor/compose.py` | relevance → recommended workflow + recommended floor/rung (§4) |
| `tools/agentic-advisor/render_map.py` | the 2 core map renderings — terminal + Mermaid (§6); HTML/live deferred (M8) |
| `tools/agentic-advisor/records.py` | scenario record + decision record + **manifest-skeleton handoff** I/O (§7) |
| `ai/claude/pm/design-feature/SKILL.md` | **integration**: route ≥2-component + ≥1-edge into `hitl:agentic-intake` (§8, ADV-13) |
| `ai/codex/AGENTS.md` | **integration**: compound-surface routing rule (§8) |
| `ci/agentic-advisor/test_catalog_lint.py` / `test_compose.py` / `test_handoff.py` / `test_advisor_e2e.py` | the suites (test plan) |

The Advisor **elicits, recommends, and records** — it **does not author the manifest** (re-scope
2026-07-23, ADR-A5). Each command produces a **recommendation + a decision-record entry** and contributes
**TODO notes to a manifest skeleton** (§7); a **human** authors the real manifest in the design phase, and
**#10 validates** it. The observability + PM eval-console control is **recommended** by the Advisor and
**enforced** by #10's `check_observability` on the human-authored manifest. There is no manifest writer and
no #10 change.

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
`ConsequenceItem` is a **tagged union** (exactly one `kind`). Because the Advisor **recommends and records**
(it authors no manifest field), a consequence points at a *recommendation* or a *decision-record entry*, not
a `#10 field`:

```yaml
consequence:            # map[ <option-or-"*"> -> list[ConsequenceItem] ]   ("*" = applies to any answer)
  <option>:
    - kind: enum[ classify | boundary | gate | command | floor | recommendation | recorded_artifact ]
      target: string    # command name | floor-rule id | recommendation id | recorded-artifact id
      note: string?      # optional; becomes a rationale line + a manifest-skeleton TODO
```
Lint (`test_catalog_lint.py`, `CAT-SCHEMA`): `consequence` is a non-empty option→list map; **every option in
the entry's `options` has a key** (or a `"*"` default); every list element is a valid tagged union with a
resolvable `target` — a `command` → a real `hitl:agentic-*`, a `floor` → a real floor-rule id, a
`recommendation`/`recorded_artifact` → a recorded id. **No `manifest_field` kind exists** (the Advisor never
targets a #10 field — re-scope 2026-07-23); the observability and kill-switch controls are `recommendation`
entries the design must satisfy. Every `role` is real.

## 3. The intake (`hitl:agentic-intake`, ADV-1/2/3/13/15)

Two-tier (ADV-1): the intake **elicits**; the per-concern commands **recommend + record**. The skill:

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
scenario data contributes no command); the floor rules give the recommended-mandatory set.

```python
COMMANDS = ["agentic-classify","agentic-boundary","agentic-privilege","agentic-reliability",
            "agentic-observability","agentic-memory","agentic-evals","agentic-deploy"]  # stable order (topo tie-break)

DEPENDS = {"agentic-boundary":["agentic-classify"], "agentic-privilege":["agentic-classify"],
           "agentic-reliability":["agentic-boundary"], "agentic-observability":["agentic-classify"],
           "agentic-memory":["agentic-classify"], "agentic-evals":["agentic-classify"],
           "agentic-deploy":["agentic-classify"]}

def any_agent(s):  return any(c["kind"] in ("simple_agent","deep_agent") for c in s["components"])
def any_async(s):  return any(e.get("kind") in ("async_task","event") for e in s["edges"])

def relevant(cmd, s):
    """Proportionality: a command is composed only if the scenario has data for its lens."""
    a = s["answers"]
    return {
      "agentic-classify":      any_agent(s),                                # right-size the components
      "agentic-boundary":      len(s["edges"]) > 0 and any_agent(s),        # inter-component contract + boundary
      "agentic-privilege":     any_agent(s),
      "agentic-reliability":   any_async(s) or a["side_effects"] != "none"
                               or a["autonomy"] in ("supervised","autonomous"),
      "agentic-observability": any_agent(s),                               # hard directive: any agentic system
      "agentic-memory":        any(c.get("memory") for c in s["components"]) or s.get("memory_hint", False),
      "agentic-evals":         any_agent(s),
      "agentic-deploy":        s.get("greenfield") or s.get("changes_platform")
                               or s.get("adds_durable_runtime") or a.get("deploy_requested", False),  # M6
    }.get(cmd, False)

# The RECOMMENDED floor — a deterministic function of Tier + risk (expert judgment, NOT #10 activation).
# Each rule recommends a control as non-skippable. #10 enforces its own checks downstream; this is advice.
def recommended_floor(s, tier):
    a = s["answers"]
    floor = set()
    if any_agent(s):
        floor |= {"agentic-classify", "agentic-privilege", "agentic-observability", "agentic-evals"}
    if len(s["edges"]) > 0 and any_agent(s):
        floor.add("agentic-boundary")
    if a["side_effects"] == "irreversible":                                # human gate
        floor.add("agentic-reliability")
    if a["autonomy"] in ("supervised","autonomous") and a["side_effects"] != "none":  # kill-switch
        floor.add("agentic-reliability")
    return floor

def compose(s, tier):
    floor    = recommended_floor(s, tier)
    included = {c for c in COMMANDS if relevant(c, s)} | floor             # floor ⊆ included
    rungs    = included - floor                                            # offered, deferrable
    order    = topo_order(included, DEPENDS)                               # deterministic: topo, tie-break by COMMANDS index
    return {"workflow": order, "floor": sorted(floor), "rungs": sorted(rungs)}
# Deterministic given (s, tier): same inputs → identical recommended workflow (ADV-12).
# There is no floor≡activation claim: the floor is a Tier+risk RECOMMENDATION, #10 is the gate (ADR-A6).
```

### 4.1 The recommended floor, Tier depth, and recording a skip (ADR-A6)

The floor is **advice** (§4). **Tier scales the recommended *depth*** of a floor control, not membership:

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

## 5. The commands (`ai/claude/skills/agentic-*`)

Each command: (a) asks its lens's catalog entries (if not already answered by the intake), (b) recommends
the simplest fit for any menu (ADR-A3), (c) **records a decision-record entry + a manifest-skeleton TODO**.
No command authors a validated manifest field. Independently runnable (ADV-1).

### 5.1 Command → recommendation + decision-record entry + skeleton TODO

Each command records **what the design must do** (a recommendation) and drops a `# TODO(design): …` into the
manifest skeleton (§7) for the human to author, which **#10 then validates**.

| Command | Recommends + records (→ decision record + skeleton TODO for the design role) |
|---|---|
| `agentic-classify` | a recommended `kind` + rationale per component; for a `deep_agent`, a TODO to author `deep_agent{planner, subagents, context_isolation, gates, guardrails}` |
| `agentic-boundary` | the recommended inter-component contract — which `facade_apis` and `interactions.authorization` the design must declare, and the trust-leg controls (validation on stochastic→det; cost/authority into agents) |
| `agentic-privilege` | the recommended capability/identity bounds per agent (`identity` + least-privilege `uses`) |
| `agentic-reliability` | recommended async/idempotency/DLQ controls + lifecycle (human-gate, resumability) + a recommended **kill-switch** |
| `agentic-memory` | recommended memory/PII controls (durability, retrieval, PII handling, high-stakes guardrail) |
| `agentic-evals` | recommended eval coverage — a spec per **agent** + one **e2e** flow (core scope) |
| `agentic-observability` | a recommended observability/tracing plan + **PM eval-console** — which #10's `check_observability` enforces on the authored manifest (hard directive 2026-07-22) |

`agentic-deploy` records the **deployment decision** in the decision record (ADR-A7): `{recommend, chosen,
rejected:[{opt, cost}], drivers, portability:{governance, packaging, state_export}, carry_to: platform-ops}`.
A human carries it to the platform/ops track; it provisions nothing and authors no manifest field.

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

The type is the scenario `components[d].kind` for agents/services, and a derived `role` for
datastore/external/store computed from the scenario (a component the intake marked state-only → `datastore`;
a `to`/`from` id not in `components` → an `external` actor). The renderer applies fixed rules over the
**scenario** (it never reads a manifest — there is none yet). The demo at artifact `efd56c28` is the
reference HTML rendering.

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
recommendations and generates a manifest *skeleton* (§7.4). `records.py`, the composer, and the map read/write
*this* file; the decision record (§7.2) and the skeleton (§7.4) are **generated from it**.

```yaml
schema_version: "3.0"
tier: int                                                   # 0..3, from .hitl/current-change.yaml
catalog: { version: string, last_refreshed: date, freshness_reviewed: bool, stale_finding: string? }  # ADV-11 freshness (m3)
# ── layer 1: elicited facts ──────────────────────────────────────────────
components: [ { id, name, kind: enum?[deterministic,simple_agent,deep_agent], kind_rationale: string?, role: enum?[agent,service,datastore,external,store] } ]  # `role` for the map (§6.1), derived at elicitation
edges:      [ { id, from: component_id, to: component_id, kind: enum?[sync_call,async_task,event], side_effecting: bool? } ]
answers:    { stakes, side_effects, data, autonomy, scale }  # §4 closed-enum vocabulary
lens_answers: { <lens>: { <catalog_entry_id>: <option> } }  # provenance: which entry produced which answer
# ── layer 2: recommendations + decisions (keyed by id; human-owned) ───────
recommendations: [ { id, lens, control, text, skeleton_todo: string,      # what the design should do + the TODO written into the skeleton
                     kind: enum[floor,rung,recorded_artifact] } ]         # floor = recommended-mandatory; rung = offered
decisions:  [ { id, attaches_to: <component|edge|lens id>, chosen, rejected:[…], rationale,
                depends_on:[<state field path>], state: enum[confirmed,stale,retired], override: bool } ]  # depends_on = fields that, if changed, make this stale (§7.3)
skips:      [ { control, owner, reason } ]                   # a recommended-floor control the team chose to skip — recorded, never silent (ADR-A6)
deferrals:  [ { rung, reason } ]                             # a rung offered but not adopted (≠ skip, distinct states)
deploy:     { recommend, chosen, rejected:[{opt,cost}], drivers, portability:{governance,packaging,state_export}, carry_to }
```

The map's richer vocabulary is the elicited `components[].role` (§6.1) — computed by fixed rules over the
scenario at elicitation time, never from a manifest (there is none). The Advisor **records skips**, not
`manifest-waivers` — the hard waive-or-block is #10's, downstream on the human-authored manifest (ADR-A6).

### 7.2 Decision record (`docs/01-product/<feature>/agentic-decisions.md`) — a GENERATED view

The Markdown decision record is **rendered from `agentic-state.yaml`** (regenerate-and-diff), never
hand-authored. It presents the scenario, the recommended workflow (floor/rungs/not-needed + reasons), every
decision (chosen/rejected/rationale), recorded skips, deferrals, and the deploy decision — all read from the
canonical state. (`REC-GEN` asserts the Markdown is a pure function of the YAML.)

### 7.3 Re-run and mutation semantics (round-4 M4)

A re-run is **recompute + reconcile, human-confirm before write** — never a blind regenerate that discards
human decisions:

1. **Recompute the derived state** — `compose(scenario, tier)` is a pure function of the scenario record, so
   the workflow/floor/rungs are recomputed deterministically (ADV-12). Derived state is never hand-edited.
2. **Reconcile human-owned decisions by `id`.** Menu choices, overrides, skips, and deferrals are keyed by
   the component/edge/lens `id` they attach to. On re-run: an id whose inputs are **unchanged** keeps its
   recorded decision; an id that is **new** is elicited fresh; an id whose **gating inputs changed** (e.g. a
   component's `kind` changed, or `side_effects` moved to `irreversible`) has its decision **flagged stale
   and surfaced for re-confirmation** — it is neither silently kept nor silently dropped (ADV-9).
3. **A removed component/edge** carries its dependent decisions to a `retired` list in the record (not
   deleted), so an audit trail survives.
4. **Human confirms before write.** The reconciled record is presented as a diff (added / changed / stale /
   retired); the human confirms, and only then are `agentic-decisions.md` **and the skeleton (§7.4)**
   **regenerated** from the confirmed state (ADV-7). No silent overwrite of a human decision.

This makes the record durable and re-runnable (ADV-7 acceptance scenario 6) with defined mutation
semantics, closing the round-4 M4 gap.

### 7.4 The design handoff — a manifest SKELETON (ADV-8)

The Advisor's handoff artifact is a **manifest skeleton** (`docs/01-product/<feature>/agentic-skeleton.yaml`),
generated from the canonical state — a **structural stub the design role fleshes out**, never a valid
manifest:

```yaml
# GENERATED by the Agentic Design Advisor — a HANDOFF, not a design.
# Author the fields below in the design phase; #10 validates the result. The Advisor does NOT author these.
domains:
  intake_agent:   { kind: simple_agent }   # TODO(design): identity{principal,privilege} + least-privilege uses (rec: privilege)
  resolver_agent: { kind: simple_agent }    # TODO(design): facade_apis for what it exposes (rec: boundary)
interactions:
  - { id: e1, from: intake_agent, to: resolver_agent }  # TODO(design): facade + trust legs + authorization.allowed_callers (rec: boundary)
# TODO(design): top-level `observability` block — tracing + PM eval-console (rec: observability; #10 check_observability enforces)
# TODO(design): eval spec per agent + one e2e segment (rec: evals)
```

It carries **only structure + `TODO(design)` markers keyed to the recommendations** (§7.1 `skeleton_todo`),
with **no authored field values**. A human authors the real fields; **#10 validates** the authored manifest.
`HANDOFF` (§9) asserts the skeleton contains no validated field value and that every recommended-floor
control has a matching TODO.

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
  test_handoff.py             # §7.4 — HANDOFF (skeleton has TODOs + NO authored field values), REC-GEN
  test_rerun.py               # §7.3 — RERUN-* (reconcile/stale/retired/confirm, M4)
  test_advisor_e2e.py         # E2E-SUPPORT/STANDALONE-CMD/ROUTE-*/MAP-*/DEPLOY-*
```

## 10. LLD decisions

- **L1:** the composer/map are **deterministic Python** over the scenario record; the catalog is data; the
  commands are skills. Expertise reviewable (catalog), logic testable (Python), conversation in the harness
  (skills) — ADR-A1/A2/A4.
- **L2:** the floor is a **Tier + risk recommendation** (§4/§4.1) — advice, not a gate; a skip is
  **recorded** (never silent), and the hard block-or-waive is **downstream at #10** on the human-authored
  manifest (ADR-A6). Two runs on the same declared factors recommend the identical floor (ADV-12).
- **L3:** commands **recommend + record** (§5.1) and contribute TODOs to a manifest **skeleton** (§7.4) — they
  **author no manifest field**. A human authors the manifest; **#10 validates** it. Observability is
  recommended (Advisor) + enforced (#10 `check_observability`); the kill-switch is a recorded recommendation
  (ADR-A5). No manifest writer, no floor≡activation, no #10 change.
- **L4:** ADV-13 integration is **two small edits** to `pm-design-feature`/`AGENTS.md` (§8), routed by a
  **cheap topology probe** (no circularity, B2) — precede for compound, skip for simple, never replace (ADR-A9).
- **L5 (core scope):** terminal+Mermaid map (HTML/live deferred, #43); the deferred compound-side items
  (universal eval, saga required-when, delegated authority) are #10/#42 concerns, not the Advisor's — the
  Advisor only *recommends* the core controls. See [`../agentic-core-scope.md`](../agentic-core-scope.md).
