# Agentic Design Advisor: LLD

> Implementation-precision design for the **Agentic Design Advisor** (FR-28). Implements HLD
> [`01-design.md`](01-design.md) v3 + ADRs [`02-adrs.md`](02-adrs.md) (A1–A9), satisfying requirements
> [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). Verified by the test plan [`03-test-plan.md`](03-test-plan.md). Status: **draft, pending
> review**. A developer/agent implements from this without a further design decision.

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
| `tools/agentic-advisor/render_map.py` | the 3 map renderings (§6) |
| `tools/agentic-advisor/records.py` | scenario record + decision record I/O (§7) |
| `ai/claude/pm/design-feature/SKILL.md` | **integration**: route ≥2-component + ≥1-edge into `hitl:agentic-intake` (§8, ADV-13) |
| `ai/codex/AGENTS.md` | **integration**: compound-surface routing rule (§8) |
| `ci/agentic-advisor/test_catalog_lint.py` / `test_compose.py` / `test_manifest_authoring.py` / `test_advisor_e2e.py` | the suites (test plan) |

No change to #10 (`ci/manifest-agentic/`). The commands **author the manifest #10 already validates**
(§5.1); the two exceptions (kill-switch, observability) write **declared artifacts** into the decision
record (§5.2, ADR-A5).

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

### 2.3 `ConsequenceItem` — the tagged union (HLD §4.2, `CAT-SCHEMA`)

```yaml
ConsequenceItem:
  kind: enum[ classify | boundary | gate | command | floor | manifest_field | declared_artifact ]
  target: string        # command name | #10 manifest path | floor-rule id | artifact id
  note: string, optional
```
Lint (`test_catalog_lint.py`): every entry has a non-empty `consequence`; every `command` target resolves
to a real `hitl:agentic-*`; every `manifest_field` target resolves to a real #10 field/path; a
`declared_artifact` target need **not** resolve to #10 (kill-switch, observability); every `role` is real.

## 3. The intake (`hitl:agentic-intake`, ADV-1/2/3/13/15)

Two-tier (ADV-1): the intake **elicits**; the per-concern commands **decide**. The skill:

1. **Selects the surface (ADV-13).** Elicits the component/edge list first. If `components ≥ 2 and edges ≥
   1` → this is a compound system → continue; else hand back to the single-agent surface (§8).
2. **Walks the catalog adaptively (ADV-3).** For each entry whose `ask_when` holds against the scenario so
   far, asks the `question`, interprets the free-text answer into an `option` (or captures verbatim), and
   applies the entry's `consequence` to the scenario record.
3. **Composes the workflow (§4)** and **sets the floor (§4.1)**.
4. **Renders the evolving map (§6)** after each meaningful step and **writes the records (§7)**.

The harness runs the conversation; `compose.py`/`floor.py`/`render_map.py` do the deterministic work.

## 4. Composition (`compose.py`, ADR-A4)

```python
COMMANDS = ["agentic-classify","agentic-boundary","agentic-privilege","agentic-reliability",
            "agentic-observability","agentic-memory","agentic-evals","agentic-deploy"]

# dependency order (topological); each runs against prior artifacts
DEPENDS = {"agentic-boundary":["agentic-classify"], "agentic-privilege":["agentic-classify"],
           "agentic-reliability":["agentic-boundary"], "agentic-observability":["agentic-classify"],
           "agentic-memory":["agentic-classify"], "agentic-evals":["agentic-classify"],
           "agentic-deploy":["agentic-classify"]}

def relevant(cmd, s):                       # HLD §4.1 — the full table, as data
    a = s["answers"]
    return {
      "agentic-classify":     True,
      "agentic-boundary":     agent_det_seam(s),
      "agentic-privilege":    any_agent(s),
      "agentic-reliability":  a["side_effects"] != "none" or any_async(s)
                              or a["autonomy"] in ("supervised","autonomous"),
      "agentic-observability":a["stakes"] in ("customer_facing","regulated") or a["autonomy"]=="autonomous",
      "agentic-memory":       any_memory(s) or a["data"] in ("sensitive","pii"),
      "agentic-evals":        any_agent(s),
      "agentic-deploy":       True,          # a build-vs-buy call is always made for a compound system
    }[cmd]

def compose(s, tier):
    included = [c for c in COMMANDS if relevant(c, s)]
    floor    = {c for c in included if floor_mandatory(c, s, tier)}   # §4.1
    order    = topo_sort(included, DEPENDS)
    return {"workflow": order, "floor": sorted(floor),
            "rungs": [c for c in order if c not in floor]}
# Deterministic given (s, tier): same inputs → identical workflow (ADV-12, test FLOOR-DET).
```

### 4.1 The floor function (`floor.py`, ADR-A6)

```python
# risk-factor vocabulary (enumerated — categorical, so elicitation variance is bounded, not zero)
STAKES = {"internal","customer_facing","regulated"}; SIDE = {"none","reversible","irreversible"}
DATA = {"none","sensitive","pii"}; AUTONOMY = {"assisted","supervised","autonomous"}; SCALE = {"small","large"}

FLOOR_RULES = {   # command/obligation -> predicate(scenario, tier) ; union precedence (HLD §5)
  "agentic-classify":     lambda s,t: True,
  "agentic-boundary":     lambda s,t: agent_det_seam(s),
  "agentic-privilege":    lambda s,t: t >= 2 or s["answers"]["data"] in ("sensitive","pii") or lethal_trifecta(s),
  "human-gate":           lambda s,t: s["answers"]["side_effects"] == "irreversible",     # via agentic-reliability
  "kill-switch":          lambda s,t: s["answers"]["autonomy"] in ("supervised","autonomous")
                                      and s["answers"]["side_effects"] != "none",          # declared artifact (§5.2)
  "agentic-observability":lambda s,t: t >= 2 or s["answers"]["autonomy"] == "autonomous",
  "agentic-evals":        lambda s,t: t >= 2 and s["answers"]["stakes"] in ("customer_facing","regulated"),
}
def floor_mandatory(cmd, s, tier):
    # map obligation-level rules (human-gate, kill-switch) onto their owning command
    owners = {"human-gate":"agentic-reliability", "kill-switch":"agentic-reliability"}
    return any(rule(s, tier) for name, rule in FLOOR_RULES.items()
               if (owners.get(name, name) == cmd))
```

**Waiver (ADR-A6):** a floor command may be dropped only with a recorded waiver
`{target, owner, reason, tier_limit:int, revisit:date}` (HITL's existing waiver shape) written to the
decision record. Composition marks a dropped-with-waiver command `waived`; dropped-without-waiver is a
**blocker** (`floor_dropped_no_waiver`). `tier` is read from `.hitl/current-change.yaml` (absent ⇒ highest
tier, fail-safe — same rule as #10).

## 5. The commands (`ai/claude/skills/agentic-*`)

Each command: (a) asks its lens's catalog entries (if not already answered by the intake), (b) recommends
the simplest fit for any menu (ADR-A3), (c) **authors its output**. Independently runnable (ADV-1).

### 5.1 Command → #10 manifest fields authored

| Command | Authors (into `system-manifest.yaml`, validated by #10) |
|---|---|
| `agentic-classify` | `domains[d].kind`, `domains[d].kind_rationale` → #10 `check_classification` |
| `agentic-boundary` | `interactions[].request/response` legs (`validation`/`cost_bound`/`authority_bound`) → `check_boundary_legs`; the `interactions` themselves → `check_topology`/`check_references`/`check_authorization` |
| `agentic-privilege` | `domains[d].identity`, `domains[d].uses` → `check_capabilities` |
| `agentic-reliability` | `interactions[].async` (delivery/idempotency), `domains[d].lifecycle` (`human_gate`, `side_effect_key`) → `check_async`/`check_lifecycle`; and any `sagas` → `check_saga` |
| `agentic-memory` | `domains[d].memory` (store/pii/durability/reads/writes) → `check_memory` |
| `agentic-evals` | `domains[d].evals.spec`, `segments[].evals` → `check_eval_coverage` |

### 5.2 The declared-artifact exceptions (ADR-A5 — no #10 target today)

| Command | Declared artifact (into the decision record, human-reviewed) | Future #10 target |
|---|---|---|
| `agentic-reliability` (kill-switch) | a `kill_switch` block: `{scope, trigger, disables}` | none scoped (no #10 kill-switch field) |
| `agentic-observability` | a `observability` block: `{traces:[hops], evals:[misbehavior], otel: true}` | #10 CR-9, lands with **#15** |

`agentic-deploy` writes the **deployment decision** to the decision record only (ADR-A7): `{recommend,
chosen, rejected:[{opt, cost}], drivers, portability:{governance, packaging, state_export}, carry_to:
platform-ops}`. It authors **no** manifest field and provisions nothing.

## 6. The evolving map (`render_map.py`, ADR-A8)

`render(scenario, composed) -> {terminal, mermaid, html}` — one data source, three renderings (ADV-15):

- **`terminal`** — a box-drawing topology + a `getting / available / not-needed` block, re-printed by the
  intake at each meaningful step. **getting** = floor ∪ adopted rungs; **available** = offered rungs;
  **not-needed** = `COMMANDS − included`, each with its **reason** = the catalog `guidance`/`note` of the
  gating answer (e.g. saga → "irreversible → you gate, not compensate").
- **`mermaid`** — the same graph + a Markdown table, written into `agentic-decisions.md` (§7.2).
- **`html`** — an optional self-contained page (static-file publishing only; no server, ADR-A8).

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

### 6.2 Combined "chat + live map" mode (ADR-A8)

On an **artifact-capable surface** (a capability the harness reports), the intake **re-publishes the `html`
rendering to the same artifact URL after each meaningful step**, so the discussion and the map update
together. It is a **live view, not an input** — the artifact is sandboxed and cannot post answers back, so
the conversation remains the sole input. On a non-capable surface (bare CLI), the intake falls back to the
`terminal` rendering (the universal baseline). Either way HITL only **generates and publishes/prints** — it
runs no server.

Deterministic from the scenario record (regenerate-and-diff), so the map never drifts.

## 7. Records (`records.py`)

### 7.1 Scenario record (`.hitl/agentic-scenario.yaml`)

```yaml
components: [ {name, kind: enum?[deterministic,simple_agent,deep_agent]} ]
edges:      [ {from, to, kind: enum?[sync_call,async_task,event]} ]
answers:    { stakes, side_effects, data, autonomy, scale, ... }   # §4.1 vocabulary
tier: int                                                          # from the change file
```

### 7.2 Decision record (`docs/01-product/<feature>/agentic-decisions.md`, ADR-style)

Holds: the scenario, the composed workflow (floor/rungs/not-needed + reasons), every menu decision
(chosen + rejected + rationale), any waivers, the declared artifacts (§5.2), and the deploy decision.
**Regenerated** (not appended) on a re-run so it never drifts from the answers (ADV-7).

## 8. Integration (ADV-13, ADR-A9)

- **`pm-design-feature`**: the "what is the delivery surface?" step gains a branch — after the components
  are elicited, `if components ≥ 2 and edges ≥ 1: invoke hitl:agentic-intake` (the compound branch); a
  single-component product continues on the existing single-agent path unchanged. The Advisor **precedes**
  the design track; it does not gate or replace it.
- **`ai/codex/AGENTS.md`**: add a routing rule — the same ≥2-component + ≥1-edge trigger selects the
  compound-agentic surface and the composed workflow rather than the single-agent template.

Both are small, enumerated edits to existing files (no new detector — the trigger reads the intake's own
elicited counts).

## 9. Test file layout (see `03-test-plan.md` for cases)

```
ci/agentic-advisor/
  test_catalog_lint.py        # §2 — CAT-*
  test_compose.py             # §4/§4.1 — COMPOSE-*/FLOOR-*/PRUNE-*/KILL-SWITCH/OBSERVABILITY
  test_manifest_authoring.py  # §5.1 — AUTHOR-* run through #10's real check_manifest_agentic.py
  test_advisor_e2e.py         # E2E-SUPPORT/E2E-TRIVIAL/ROUTE-*/MAP-*/DEPLOY-*
```

## 10. LLD decisions

- **L1:** the composer/floor/map are **deterministic Python** over the scenario record; the catalog is
  data; the commands are skills. This keeps the expertise reviewable (catalog), the logic testable
  (Python), and the conversation in the harness (skills) — ADR-A1/A2/A4.
- **L2:** the floor is a **union of monotone predicates** (§4.1) with a recorded-waiver escape hatch; two
  runs on the same declared factors compute the identical floor (ADV-12), but human-declared factors are a
  softer input mitigated by the categorical vocabulary.
- **L3:** commands **author manifest fields** #10 already validates (§5.1); kill-switch/observability are
  **declared artifacts** (§5.2) with no #10 target until #15 — stated, not faked (ADR-A5).
- **L4:** ADV-13 integration is **two small edits** to `pm-design-feature`/`AGENTS.md` (§8) — precede for
  compound, skip for simple, never replace (ADR-A9).
