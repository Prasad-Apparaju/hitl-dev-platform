# Agentic Design Advisor: LLD

> Implementation-precision design for the **Agentic Design Advisor** (FR-28). Implements HLD
> [`01-design.md`](01-design.md) v3.2 + ADRs [`02-adrs.md`](02-adrs.md) (A1–A9), satisfying requirements
> [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). Verified by the test plan [`03-test-plan.md`](03-test-plan.md). Status: **draft,
> round-7 applied (v3.3), pending Codex re-review (round 7)**. A developer/agent implements from this
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

## 4. Composition (`compose.py`, ADR-A4) — floor = #10 activation, ONE source, COMPLETE ownership (round-7 B1)

Rounds 4–6 kept failing the same way: the Advisor maintained its **own copy** of #10's activation
predicates, and a hand copy drifted (round-6 B1: narrower predicates, and `check_deep_agent`/
`check_policy_refs`/`check_saga` had **no owning command**, so a deep-agent scenario hard-failed #10). The
round-7 fix is structural:

1. **No copy of #10's predicates.** #10's activation table (compound LLD §6.0) is the **single source**. The
   composer computes `manifest_features(scenario)` and evaluates **#10's own predicates** over those
   features — it imports `ci/manifest-agentic/activation.py` (the module that also drives #10's validator),
   so there is nothing to drift. The Advisor's only contribution is the scenario→features mapping, which is
   small and reviewable.
2. **Complete ownership.** `OWNS_CHECKS` covers **every blocking #10 check**, multi-owned where one check is
   triggered by several commands' outputs (`check_policy_refs`, `check_scope_grammar`). A build lint asserts
   `⋃ OWNS_CHECKS == {every blocking check in §6.0}` — so a check can never be activatable-but-unowned.

```python
COMMANDS = ["agentic-classify","agentic-boundary","agentic-privilege","agentic-reliability",
            "agentic-observability","agentic-memory","agentic-evals","agentic-deploy"]  # stable order (topo tie-break)

DEPENDS = {"agentic-boundary":["agentic-classify"], "agentic-privilege":["agentic-classify"],
           "agentic-reliability":["agentic-boundary"], "agentic-observability":["agentic-classify"],
           "agentic-memory":["agentic-classify"], "agentic-evals":["agentic-classify"],
           "agentic-deploy":["agentic-classify"]}

# PRIMARY checks decide floor MEMBERSHIP — a command is floor iff a primary check it owns activates.
# SECONDARY (downstream) checks — check_policy_refs, check_scope_grammar — are triggered by a floor
# command's OWN authored output (a validation/compensation PolicyRef, an authority/uses Scope). They do NOT
# pull a new command into the floor; the command that authored the triggering field owns their validity.
# (This split is the round-7 fix for a self-caught bug: without it, memory/reliability would wrongly join
# every agent flow's floor just because boundary authored a PolicyRef.)
PRIMARY_CHECKS = {
  "agentic-classify":      ["check_classification", "check_deep_agent"],   # authors deep_agent{...} when kind=deep_agent (round-6 B1)
  "agentic-boundary":      ["check_boundary_legs","check_topology","check_references","check_authorization"],
  "agentic-privilege":     ["check_capabilities"],
  "agentic-reliability":   ["check_async","check_lifecycle","check_saga"],  # round-6 B1: check_saga now owned
  "agentic-observability": ["check_observability"],
  "agentic-memory":        ["check_memory"],
  "agentic-evals":         ["check_eval_coverage"],
  "agentic-deploy":        [],                                             # no #10 check (records a decision)
}
# SECONDARY ownership (for the OWNERSHIP-COMPLETE lint only — who keeps a downstream check valid):
SECONDARY_OWNERS = {
  "check_policy_refs":   ["agentic-boundary","agentic-reliability","agentic-memory"],  # validation / compensation / guardrail refs
  "check_scope_grammar": ["agentic-privilege","agentic-boundary"],                     # uses / authority_bound scopes
}
# OWNS_CHECKS = primary ∪ secondary (every blocking check is owned by someone). check_compensation_gap is
# advisory → no floor owner.
OWNS_CHECKS = {cmd: list(PRIMARY_CHECKS[cmd]) +
                    [c for c,owners in SECONDARY_OWNERS.items() if cmd in owners]
               for cmd in PRIMARY_CHECKS}

def manifest_features(s):
    """The scenario → the manifest features #10's §6.0 predicates read. THIS is the Advisor's contribution;
    the predicates themselves are #10's."""
    return {
      "has_interactions":  len(s["edges"]) > 0,
      "orchestration_or_segments": s.get("orchestration") is not None or bool(s.get("segments")),
      "agent_endpoint":    any(is_agent(s,e["from"]) or is_agent(s,e["to"]) for e in s["edges"]),
      "into_agent":        any(is_agent(s,e["to"]) for e in s["edges"]),
      "declares_authorization": any(e.get("authorization") for e in s["edges"]),            # round-6: check_authorization also fires on this
      "any_agent":         any(c["kind"] in ("simple_agent","deep_agent") for c in s["components"]),
      "any_deep_agent":    any(c["kind"] == "deep_agent" for c in s["components"]),
      "any_async":         any(e.get("kind") in ("async_task","event") for e in s["edges"]),
      # a floor command AUTHORS these, so they WILL be present once that command is floor:
      "has_lifecycle":     s["answers"]["side_effects"] != "none" or any(c.get("long_running") for c in s["components"]),
      "has_memory":        any(c.get("memory") for c in s["components"]),
      "has_saga":          bool(s.get("sagas")),
      "has_scope":         any(c["kind"] in ("simple_agent","deep_agent") for c in s["components"]),   # privilege authors scopes
      "has_policyref":     True if any(is_agent(s,e["from"]) or is_agent(s,e["to"]) for e in s["edges"]) else False,  # boundary authors validation refs
    }

def floor_commands(s):
    """A command is floor iff a PRIMARY #10 check it owns activates — using #10's OWN predicates (import),
    not a copy. Downstream (secondary) checks do NOT determine membership (see PRIMARY_CHECKS note)."""
    from ci.manifest_agentic.activation import ACTIVATES   # THE single source (compound LLD §6.0)
    feats = manifest_features(s)
    floor = {cmd for cmd, checks in PRIMARY_CHECKS.items()
             if any(ACTIVATES[c](feats) for c in checks)}
    if human_gate_needed(s) or kill_switch_needed(s):       # non-#10 obligations (kill-switch/human-gate)
        floor.add("agentic-reliability")
    # Invariant (OWNERSHIP-COMPLETE, asserted separately): for every check ACTIVATES[c](feats) that is a
    # BLOCKER, some command in `floor` owns c (via PRIMARY or SECONDARY) — so no activated check is unauthored.
    return floor

def rung_relevant(cmd, s):
    """Genuinely-optional rungs — a command with NO firing owned check, offered when its own hint is present."""
    a = s["answers"]
    return {
      "agentic-memory":  s.get("memory_hint", False) and not any(c.get("memory") for c in s["components"]),  # hinted, not yet declared (round-6 M5)
      "agentic-deploy":  is_greenfield(s) or changes_platform(s) or adds_durable_runtime(s) or a.get("deploy_requested", False),  # M6
    }.get(cmd, False)

def compose(s, tier):
    floor    = floor_commands(s)                                # from #10 activation (imported), complete ownership
    rungs    = {c for c in COMMANDS if c not in floor and rung_relevant(c, s)}
    included = floor | rungs                                    # floor ⊆ included by construction
    order    = [c for c in topo_order(included, DEPENDS)]       # deterministic: topo, ties broken by COMMANDS index
    return {"workflow": order,                                  # exact ORDERED list (round-6 B4 tie-break)
            "floor": sorted(floor), "rungs": sorted(rungs)}
# `order` is unique: topo_order visits ready nodes in COMMANDS order, so there is one canonical workflow.
# Deterministic given s; tier affects DEPTH within a control (§4.1), not WHETHER it is floor.
```

### 4.1 The floor, tier, and depth (`floor.py`, ADR-A6)

**Which controls are floor** is decided by `floor_commands(s)` above (§4) — using **#10's imported
activation predicates** over `manifest_features(scenario)`, no tier gate and no copy. **Tier does not decide
*whether* a control is floor; it scales the *depth* required within a floor control** (the proportionate
lever, O6). The full per-command depth table (round-6 M1 — this replaces the three example functions):

| Floor command | Tier 0–1 depth | Tier 2 depth | Tier 3 depth | Enforced by (#10) |
|---|---|---|---|---|
| `agentic-observability` | `eval_console.access ∈ {report, existing_surface}`; required trace attributes on agent hops | `access == console` | `access == console` + full-graph tracing | `check_observability` (§6.17.1 `access_ok(tier)`) |
| `agentic-privilege` | `uses` per capability-class | per-capability scopes | per-capability + per-resource | `check_capabilities` granularity is not tier-gated in #10; the Advisor recommends depth, #10 validates containment either way |
| `agentic-evals` | `status: baseline` spec per agent + e2e | `approval: approved` required | approved + extended cases | `check_eval_coverage` (`approval.decision` gate at Tier ≥ 2) |
| `agentic-boundary` | validation on stochastic→det legs | + cost/authority bounds reviewed | + tighter authority ceilings | `check_boundary_legs` |

Only the rows whose **depth maps to a real #10 predicate** (observability `access_ok`, eval `approval`) are
tier-*enforced*; the others are Advisor *recommendations* at that depth, with #10 validating the invariant
(e.g. privilege containment) at any depth. This is stated honestly — the Advisor does not claim a tier rule
#10 does not implement (round-6 M1).

```python
def human_gate_needed(s):  return s["answers"]["side_effects"] == "irreversible"   # non-#10, owned by reliability
def kill_switch_needed(s): return (s["answers"]["autonomy"] in ("supervised","autonomous")
                                   and s["answers"]["side_effects"] != "none")
def observability_access(tier):  return "report" if tier <= 1 else "console"        # a valid #10 enum value (round-6 B4)
```

**`FLOOR-SUBSET` lint (retained).** `floor_commands(s) ⊆ compose(s,tier)["workflow"]` over the swept
factor-space × tiers — trivially true (`compose` unions the floor in).

**`OWNERSHIP-COMPLETE` lint (round-7 B1, replaces the unimplementable ACTIVATION-MIRROR).** Imports #10's
`ACTIVATES` module and asserts (a) every **blocking** check in it appears in some `OWNS_CHECKS` list, and
(b) every check named in `OWNS_CHECKS` is a real key of `ACTIVATES`. Because the composer **calls #10's
predicates directly** (no copy), there is nothing to compare "field-for-field" — the only failure mode is an
*unowned* activatable check, which this lint catches. A deep-agent scenario now passes: `check_deep_agent`
is owned by `agentic-classify`.

**Waiver — writes to the REAL #10 store that check reads (round-6 B3).** A floor control that #10 enforces
is dropped by the Advisor authoring a waiver entry in the store #10 **actually consults** for that check:
`check_eval_coverage` → `docs/03-engineering/evals/waivers.yaml`; **every other blocking check** →
**`manifest-waivers.yaml`** (the general per-check waiver contract added to #10, compound LLD §6 — an entry
`{code, locus, owner, reason, tier_limit, revisit}` that `main` reads to suppress a matching blocker). So a
privilege/boundary/lifecycle/observability drop is real: the Advisor writes the entry, and #10 honours it.
A floor control with **no** #10 check (the kill-switch) is waived in the decision record alone. Dropping a
floor control silently is a **blocker** (`floor_dropped_no_waiver`); a **rung** is **deferred** (recorded
`deferred`, no blocker). `waived` ≠ `deferred` (m3). `tier` from `.hitl/current-change.yaml`.

## 5. The commands (`ai/claude/skills/agentic-*`)

Each command: (a) asks its lens's catalog entries (if not already answered by the intake), (b) recommends
the simplest fit for any menu (ADR-A3), (c) **authors its output**. Independently runnable (ADV-1).

### 5.1 Command → #10 manifest fields authored

| Command | Authors (into `system-manifest.yaml`, validated by #10) |
|---|---|
| `agentic-classify` | `domains[d].kind`, `domains[d].kind_rationale` → `check_classification`; **when it classifies a `deep_agent`, it authors the `deep_agent{planner,subagents,context_isolation,gates,guardrails}` block** → `check_deep_agent` (round-6 B1 — this ownership was missing) |
| `agentic-boundary` | the **inter-component contract** — `domains[callee].facade_apis[facade_name]` (signatures + `blurb`/`mutations`/`preconditions`/`error_modes`) and `interactions[].authorization{allowed_callers, credential_mode, credential_justification}` → `check_references`/`check_authorization`; the request/response legs (`validation` **PolicyRef** → `check_policy_refs`; `cost_bound`; `authority_bound` **Scope** → `check_scope_grammar`) → `check_boundary_legs` (incl. agent→agent); `interactions`/`orchestration`/`segments` → `check_topology` |
| `agentic-privilege` | `domains[d].identity{principal, privilege:[Scope]}`, `domains[d].uses[{capability,scopes}]` → `check_capabilities`; the scopes → `check_scope_grammar` |
| `agentic-reliability` | `interactions[].async{delivery,idempotency,dlq,retry,timeout}` → `check_async`; `domains[d].lifecycle{long_running,resumable,idempotent_resume,checkpoint,checkpoint_store,resume_cursor,side_effect_key,human_gate,human_gate_pause,timeout,cancellation}` → `check_lifecycle`; `sagas` (sequential) with `compensation` **PolicyRef** → `check_saga` + `check_policy_refs` |
| `agentic-memory` | `domains[d].memory{short_term, long_term{owner,store,shared_store,durability,retrieval,scope,pii,pii_justification,reads,writes}}` + high-stakes `guardrail` **PolicyRef** → `check_memory` + `check_policy_refs` |
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
# ── layer 2: authored outputs (per command; LOSSLESS to every #10 field its owned checks read, §5.1) ──
# Field-completeness is asserted by AUTHOR-COMPLETE (§9): for each owned check, every field #10 requires
# has a home here (round-6 B2 — the previous layer omitted identity.privilege, async, sagas, policies,
# stores, orchestration, segments, deep_agent, and half of lifecycle/memory).
authored:
  facades:        [ { id, on: component_id, name, signature, blurb, mutations:[…], preconditions:[…], error_modes:[…] } ]  # → domains[].facade_apis[name] (blurb is base-schema-required, round-6 B2)
  authorizations: [ { edge_id, allowed_callers:[component_id], audience?, credential_mode: enum[jit,static,none], credential_justification? } ]  # → interactions[].authorization (field name matches the schema, round-6 B2)
  legs:           [ { edge_id, leg: enum[request,response,event], validation: PolicyRef?, cost_bound?, authority_bound?:[Scope] } ]  # → interactions[].{request,response,event}
  identities:     [ { component_id, principal, privilege:[Scope], uses:[ {capability, scopes:[Scope]} ] } ]         # → domains[].identity{principal,privilege} + domains[].uses (privilege added, round-6 B2)
  deep_agents:    [ { component_id, planner, subagents:[component_id], context_isolation: bool, gates:[PolicyRef], guardrails:[PolicyRef] } ]  # → domains[].deep_agent (round-6 B1/B2)
  async:          [ { edge_id, delivery: enum[at_most_once,at_least_once], consumer_idempotent?: bool, idempotency_key?, dlq?, dlq_justification?, retry?, timeout } ]  # → interactions[].async (round-6 B2)
  lifecycle:      [ { component_id, long_running, resumable, idempotent_resume, checkpoint, checkpoint_store?, resume_cursor?, side_effect_key?, human_gate, human_gate_pause?, timeout, cancellation } ]  # → domains[].lifecycle (all conditional fields, round-6 B2)
  memory:         [ { component_id, short_term?, long_term?: {owner, store, shared_store?, durability, retrieval, scope, pii, pii_justification?, high_stakes?: bool, guardrail?: PolicyRef, provenance?, staleness?}, reads:[…], writes:[…] } ]  # → domains[].memory (round-6 B2)
  segments:       [ { id, path:[edge_id], e2e: bool, transactional?: bool, evals?: {spec} } ]                       # → top-level segments (round-6 B2 — carries the e2e path + spec)
  orchestration:  { pattern?: enum[sequential,supervisor,hierarchical,blackboard,swarm,hybrid], coordinator?: component_id, cycle_bound?: int, justification? }  # → top-level orchestration
  sagas:          [ { id, coordinator: component_id, order: enum[sequential], steps:[{interaction_id, compensation: PolicyRef, compensation_idempotent: bool}] } ]  # → top-level sagas (sequential, round-5 M2)
  evals:          [ { target_type: enum[component,segment], target_id, kind: enum[eval], spec_path, approval?: {reviewer,date,decision} } ]  # → domains[].evals / segments[].evals
  observability:  { tracing:{ convention: enum[otel_genai,openinference], hops:[edge_id], attributes:[…] }, cost_budget:{limit,unit}, eval_console:{access: enum[report,existing_surface,console], owner, ref: ResolvableRef} }  # → top-level observability; `tracing` is NESTED to match #10 §4.3 (the spike caught a flat-vs-nested mismatch, round-8)
  policies:       [ { id: "<ns>:<name>", kind: enum[schema,guardrail,action], … } ]                                # → policies.yaml registry (every PolicyRef above resolves here, round-6 B2)
  stores:         [ { id, durable: bool, shared?: bool } ]                                                          # → stores.yaml registry (checkpoint_store/shared_store resolve here)
  kill_switch:    { scope, trigger, disables }               # declared artifact only (no #10 field, §5.2)
  deploy:         { recommend, chosen, rejected:[{opt,cost}], drivers, portability:{governance,packaging,state_export}, carry_to }  # decision record only
# ── layer 3: confirmed decisions (keyed by id; human-owned) ───────────────
decisions:  [ { id, attaches_to: <component|edge|lens id>, chosen, rejected:[…], rationale,
                depends_on:[<state field path>], state: enum[confirmed,stale,retired], override: bool } ]  # depends_on = the fields that, if changed, make this decision stale (round-6 B2)
waivers:    [ { control, store: enum[eval_waivers_yaml, manifest_waivers_yaml, decision_record],
                owner, reason, tier_limit, revisit } ]        # writes to the REAL #10 store that check reads (round-6 B3)
deferrals:  [ { rung, reason } ]                             # rungs offered but not adopted (≠ waiver, m3)
```

Note the layer-1 `components[].kind` is one of `deterministic|simple_agent|deep_agent`; the map's richer
vocabulary (datastore/external/output-store) is a **derived `role`** the writer computes deterministically
from manifest content (§6.1) — a `deterministic` domain with no `facade_apis` that only holds state → a
`datastore`; a `to`/`from` id not in `components` → an `external` actor. The renderer never invents a role;
it applies these fixed rules (round-6 M6).

### 7.1.1 Writer + merge contract (round-6 B2)

Each command's **input** is the layers-1/2 state it reads; its **output** is the `authored.*` block it owns.
The **manifest writer** (`tools/agentic-advisor/write_manifest.py`) maps `authored.*` → `system-manifest.yaml`
by a fixed key rule: **`component.id` → `domains[<id>]`, `edge.id` → the `interactions[]` element with that
`id`** (ids are stable, §7.3). Merge into an **existing** manifest is **additive and non-clobbering**: the
writer only writes keys it owns (§5.1); a hand-authored manifest field the Advisor does not own is
**preserved**; a conflict on an owned key surfaces as a diff for human confirmation (never silent
overwrite). `AUTHOR-COMPLETE` (§9) asserts that, for the LOW/HIGH/deep-agent fixtures, the writer's output
run through #10's **real** validator passes every activated check — the executable proof that the state is
sufficient.

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
  test_ownership.py           # §4 — OWNERSHIP-COMPLETE: every blocking #10 check (imported) is owned (B1)
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
