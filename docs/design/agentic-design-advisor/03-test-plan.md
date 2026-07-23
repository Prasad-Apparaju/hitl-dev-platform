# Agentic Design Advisor: Test Plan — v4 (re-scope in progress)

> **RE-SCOPED 2026-07-23 — elicit + recommend + record + hand off.** The auto-authoring test families are
> **removed**: `AUTHOR-LOW/HIGH/CONTRACT/EVAL-CORE/OBSERV/COMPLETE`, `OWNERSHIP-COMPLETE`,
> `FLOOR-EQ-ACTIVATION`, `ACTIVATION-MIRROR`, `COMPOSE-DEEP` (they tested the deleted manifest-authoring seam).
> The retained families test the **new** model: intake elicitation, the **recommendation** composer + the
> Tier+risk **recommended floor**, decision-record + **manifest-skeleton handoff** correctness (a skeleton
> has TODOs and **no** authored field values; the Advisor writes no validated manifest field), routing, and
> the map. Verifies [`01-design.md`](01-design.md) v4 against the requirements (ADV-1..ADV-15). Status:
> **v4 re-scope applied — elicit + recommend + record + hand off.**

## 1. What must be true

1. **Proportionate composition** — the recommended workflow follows risk; low-risk is short, high-risk is
   full (ADV-3).
2. **No orphan questions** — every catalog question changes the output (ADV-4).
3. **Deterministic, honest recommended floor** — the floor is a reproducible function of **Tier + risk
   factors** (expert judgment, NOT #10 activation); a recommended-floor control cannot be skipped *silently*
   — a skip is recorded (owner/reason); the hard block-or-waive is **downstream at #10** (ADV-5/ADV-12).
4. **Recommend, not decide** — a recommendation + rationale + recorded chosen/rejected for every menu;
   overrides recorded (ADV-6/ADV-9).
5. **Hand off, don't author** — the output is a **decision record + a manifest skeleton** (structure +
   `TODO(design)` markers, **no** authored field values); **no `agentic-*` command writes a validated
   manifest field**; a human authors the manifest and **#10 validates** it (ADV-8, ADR-A5).
6. **Deploy: record + human-carry** — recommends managed by default, records, prompts a human handoff,
   provisions nothing (ADV-14).
7. **Durable + reproducible** — the decision record (scenario + recommended workflow + decisions) regenerates
   from the answers; a re-run reproduces the workflow (ADV-7).

## 2. Test levels

- **Catalog lint** (static, `ci/agentic-advisor/test_catalog_lint.py`) — the question/option catalog as data.
- **Composition + recommended-floor units** (`ci/agentic-advisor/test_compose.py`) — the intake→recommended
  workflow + floor over scripted answers.
- **Handoff** (`ci/agentic-advisor/test_handoff.py`) — the decision record + manifest skeleton are generated
  from the state and contain **no authored field values**.
- **Command behavior** (skill-lint + scripted end-to-end) — the `hitl:agentic-*` commands.

## 3. Catalog lint (ADV-4, ADR-A2)

| Case | Fixture | Expect |
|---|---|---|
| CAT-CONSEQUENCE | every entry parsed | each has a **non-empty `consequence`**; an orphan question fails |
| CAT-SCHEMA | each `consequence` | is an **option→list map** (LLD §2.3): every `options` value has a key (or `"*"`); each list item is a **tagged union** (`kind` from the enum + a resolvable `target`) |
| CAT-COVERAGE | the entry set | every lens (HLD §2 + stakes/tier/compliance, cost) has ≥1 entry — including **observability**, **kill-switch**, **portability** |
| CAT-COMMANDS | each `kind:command` consequence | the command exists in the `hitl:agentic-*` set (no dangling command) |
| CAT-RECOMMEND | each `kind:recommendation`/`kind:recorded_artifact` consequence | resolves to a recorded recommendation id; **no `kind:manifest_field` exists** (the Advisor targets no #10 field — re-scope 2026-07-23); observability + kill-switch are `recommendation` entries |
| CAT-ROLE | each entry | a valid role from `docs/playbook/roles.md` (PM/Technical Advisor/Architect/Developer/QA/Ops) |
| CAT-REFRESH | the refresh trigger | a Tier-3 fixture prompts a curated-refresh review step; **no live external call is made** (ADR-A2) |

## 4. Composition + recommended floor (ADV-3/ADV-5/ADV-12) — Tier + risk, NOT #10 activation

Two **exact, constructable fixtures** with their computed `floor`/`rungs`/`workflow` (hand-run through the §4
recommendation composer). The floor is the Advisor's **recommendation** from Tier + risk — advice, not a
gate; #10 enforces its own checks downstream on the human-authored manifest.

**Fixture LOW** — Tier-1, 2-agent, read-only, internal, greenfield:
```yaml
components: [{id: a1, name: intake, kind: simple_agent}, {id: a2, name: resolver, kind: simple_agent}]
edges:      [{id: e1, from: a1, to: a2, kind: sync_call}]
answers:    {stakes: internal, side_effects: none, data: none, autonomy: assisted, scale: small, greenfield: true}
tier: 1
```
→ **recommended floor** = `[agentic-boundary, agentic-classify, agentic-evals, agentic-observability,
agentic-privilege]`; **rungs** = `[agentic-deploy]`; **workflow** (ordered, topo + `COMMANDS` tie-break) =
`[agentic-classify, agentic-boundary, agentic-privilege, agentic-observability, agentic-evals, agentic-deploy]`.
*(Depth is recommended minimal — observability `access: report`, privilege per-class, eval baseline.)*

**Fixture HIGH** — Tier-2, 4-component (2 agents), irreversible, PII, supervised, one async edge:
```yaml
components: [{id: a1, name: intake, kind: simple_agent}, {id: a2, name: resolver, kind: simple_agent},
             {id: s1, name: account_svc, kind: deterministic}, {id: d1, name: ledger, kind: deterministic}]
edges:      [{id: e1, from: a1, to: s1, kind: sync_call}, {id: e2, from: a1, to: a2, kind: sync_call},
             {id: e3, from: a2, to: d1, kind: async_task}]
answers:    {stakes: customer_facing, side_effects: irreversible, data: pii, autonomy: supervised, scale: small, greenfield: true}
tier: 2
```
→ **recommended floor** = `[agentic-boundary, agentic-classify, agentic-evals, agentic-observability,
agentic-privilege, agentic-reliability]` (reliability recommended via the irreversible human-gate rule +
the async edge); **rungs** = `[agentic-deploy]`; **workflow** = floor ∪ rungs.

| Case | Scenario | Expect |
|---|---|---|
| **COMPOSE-LOW** | Fixture LOW | exact `floor`/`rungs`/`workflow` above; **deploy is a rung (greenfield), never floor** |
| **COMPOSE-HIGH** | Fixture HIGH | exact `floor`/`rungs`/`workflow` above; reliability enters the recommended floor (irreversible ⇒ human-gate; async ⇒ reliability) |
| PRUNE-DEPLOY | a change to an existing deployed system (not greenfield, no platform change) | `agentic-deploy` **not** composed (M6 — deploy is not "always") |
| **FLOOR-DET** | run Fixture HIGH twice | **identical** recommended floor + workflow (deterministic, ADV-12) |
| **FLOOR-SKIP** | Fixture HIGH, then skip the recommended `agentic-reliability` (human gate) | **recorded** in `skips: [{control, owner, reason}]` and surfaced in the handoff — never silent (ADR-A6). The Advisor does **not** block; the hard block-or-waive is downstream at **#10** on the authored manifest |
| FLOOR-SKIP-SILENT | Fixture HIGH, skip a recommended-floor control with **no** owner/reason | **blocked at the Advisor** — a skip must be recorded (owner + reason); silent skip is not allowed (ADV-12) |
| FLOOR-DEFER | Fixture HIGH, defer the offered `agentic-deploy` rung | allowed; recorded as **`deferred`** (a rung deferral, *distinct* from a `skip` of a recommended-floor control) |

## 5. Recommend-not-decide + deploy (ADV-6/ADV-9/ADV-14)

| Case | Fixture | Expect |
|---|---|---|
| REC-SIMPLEST | a menu where a simple and a complex option both fit | recommends the **simplest**; complex listed as rejected **with its cost** |
| REC-RECORD | any menu decision | record contains chosen **and** rejected + rationale |
| REC-OVERRIDE | human overrides | override + reason recorded; no silent apply |
| **DEPLOY-MANAGED** | `agentic-deploy`, low stakes + small scale + no data-residency | recommends **managed**; from-scratch rejected with its cost (ADV-14) |
| **DEPLOY-BUILD-REASON** | choose **build** with no stated driver | requires a specific reason before recording `build` |
| **DEPLOY-EXAMPLES** | the deployment menu | implementations named only as **examples**; no vendor selected, no cloud module |
| **DEPLOY-RECORD-CARRY** | a completed deploy decision | recorded in the decision record; a **human handoff to the platform track is prompted**; **nothing provisioned, no auto-handoff** (ADR-A7) |
| **DEPLOY-PORTABILITY** | a **managed** recommendation | the lock-in trade-off is surfaced and the three diligence questions (**governance / packaging / state-export**) must be answered before the decision records; an unanswered one blocks (ADV-14) |
| **BIND-NOT-EMBED** | an agent that names its model/memory/tool **provider inside agent logic** | the portability facet flags it — providers must be **bound as capabilities via config**, not embedded (ADV-2) |

## 6. Handoff — decision record + manifest skeleton, NOT a design (ADV-7/ADV-8, ADR-A5)

The critical property: the Advisor produces a **decision record + a manifest skeleton**, and **authors no
validated manifest field** — a human authors the manifest, #10 validates it. These tests assert the handoff
is a stub, not a design.

| Case | Fixture | Expect |
|---|---|---|
| **HANDOFF-SKELETON** | Fixture HIGH's generated `agentic-skeleton.yaml` | it contains component/edge **structure + `TODO(design)` markers only**, and **no authored field values** (no `facade_apis`, `identity`, `uses`, `async`, `observability`, `evals` values) — a lint asserts every leaf under `domains`/`interactions` beyond `kind`/`from`/`to`/`id` is a `TODO(design)` comment |
| **HANDOFF-TODOS** | Fixture HIGH's skeleton | every **recommended-floor control** has a matching `TODO(design)` marker keyed to its recommendation (boundary→facades/authz TODO; privilege→identity/uses TODO; observability→observability TODO; evals→eval TODO) |
| **NO-AUTHOR** | the whole Advisor package/output | **no** `agentic-*` command or tool writes a value into `system-manifest.yaml`; there is no manifest writer; grep asserts the package contains no `check_manifest_agentic` import and no `system-manifest.yaml` write path |
| **HANDOFF-HUMAN** | after a run | the human authors the manifest fields from the skeleton (out of test scope), and **#10's real validator** is what gates the result — the Advisor is not in that loop (ADR-A5) |
| **DEPLOY-RECORDED** | the kill-switch + deploy outputs | recorded as **recommendations/decisions** in the decision record (recommendation entries), not manifest fields; present, not silently omitted |
| **NO-SEED** | the Advisor's output artifacts | there is **no** `.hitl/agentic-profile.yaml` "active-validator set" and no seed consumed by #10 — #10 needs no Advisor input (proves the v1 fiction is gone and the re-scope removed authoring) |

## 7. Command + docs (ADV-1/ADV-7/ADV-10)

| Case | Check |
|---|---|
| CMD-STANDALONE | each `hitl:agentic-*` command runs **independently** (e.g. `agentic-privilege` on an existing design) and passes skill-lint |
| REC-DOC | a run writes a durable `agentic-decisions.md` (scenario + composed workflow + decisions) |
| REC-REGEN | a re-run **regenerates** the record (not appends); no drift from the answers |
| ROLE-ATTR | each catalog entry **attributes** to a real role; role attribution is **presentation only** — it never gates whether a lens/entry **exists or is covered**. The whole-scenario intake asks **every** relevant lens regardless of role; a role filter only changes *who is shown as owner*, not which lenses run (round-4 M9 — attribute, don't gate) |
| RERUN-RECONCILE | run the intake, record decisions/waivers, change one component's `kind` and add a component, re-run | derived workflow/floor **recomputed**; unchanged-input decisions **kept**; the changed-input decision **flagged stale for re-confirmation**; the new component **elicited fresh**; a removed one's decisions moved to `retired`; the human confirms a **diff before any write** — no silent overwrite (§7.3, round-4 M4) |
| **ROUTE-COMPOUND** | `pm-design-feature` with an elicited ≥2-component + ≥1-edge system | routes into `hitl:agentic-intake` (the compound branch); `AGENTS.md` rule matches (ADV-13/ADR-A9) |
| **ROUTE-SIMPLE** | a single-component product | stays on the existing single-agent surface; the Advisor is **not** invoked; the deterministic flow is unchanged |
| **E2E-SUPPORT** | the worked example (HLD §9), Fixture HIGH: scripted answers → recommended floor `{classify, boundary, privilege, reliability, observability, evals}` + rung `{deploy}` → a **decision record + a manifest skeleton** (TODOs, no authored values) → deploy recorded + human-carry prompted. A human then authors the manifest (out of scope) and #10 validates it |
| STANDALONE-CMD | a single command (e.g. `agentic-privilege`) run **directly** on an existing design | runs standalone (ADV-1) — this is the supported path for a **single-component** system; the full compound intake is **not** invoked for one component (routing, §ROUTE-SIMPLE). *(No single-agent E2E fixture — a single component is not the Advisor's compound domain.)* |
| **MAP-TERMINAL** | run the intake in a terminal (no browser) | a **text/box-drawing** map + getting/not-needed lines are printed inline; **no browser is required** (ADV-15) |
| **MAP-EVOLVE** | add components/decisions step by step | the map **regenerates per step** — a node/annotation/panel-item appears each step; the not-needed items show their reason |
| **MAP-MERMAID** | the decision record after a run | contains a **Mermaid** topology + getting/available/not-needed table; regenerating the record is **deterministic** (same scenario → same map, no drift) |
| **MAP-NO-SERVER** | the Advisor's runtime footprint | it **writes files / prints text only** — no live-reload server or hosted dashboard is started (ADR-A8, governs-not-runtime) |
| MAP-CORE-SCOPE | the core map deliverable | is **terminal + Mermaid only**; the rich **HTML rendering and the combined "chat + live map" mode are deferred** (no core test — round-4 M8); the core suite passes without them |

## 8. Coverage of acceptance scenarios

| Acceptance scenario (requirements §8) | Tests |
|---|---|
| 1. Non-expert → right-sized recommended workflow + floor + record + handoff (no PM-authored design) | E2E-SUPPORT, REC-DOC, HANDOFF-SKELETON |
| 2. Low-stakes → proportionate workflow; only truly-optional commands absent | COMPOSE-LOW, PRUNE-DEPLOY |
| 3. High-stakes → full workflow; a recommended-floor control can't be skipped silently | COMPOSE-HIGH, FLOOR-SKIP-SILENT |
| 4. Every recommendation recorded + overridable | REC-RECORD, REC-OVERRIDE |
| 5. Hand off, don't author: decision record + skeleton (TODOs, no field values); no command writes a manifest field; a human authors + #10 validates | HANDOFF-SKELETON, HANDOFF-TODOS, NO-AUTHOR, HANDOFF-HUMAN, NO-SEED |
| 6. Durable + re-runnable, no drift | FLOOR-DET, REC-REGEN, RERUN-RECONCILE |
| 7. Deploy: managed default, reason to build, record + human-carry, no provisioning | DEPLOY-MANAGED, DEPLOY-BUILD-REASON, DEPLOY-EXAMPLES, DEPLOY-RECORD-CARRY, DEPLOY-PORTABILITY |
| 8. Recommended floor deterministic (given declared factors) | FLOOR-DET |
| 9. A skipped recommended-floor control is recorded, never silent (hard gate downstream at #10) | FLOOR-SKIP, FLOOR-SKIP-SILENT |
| 10. (ADV-15) map renders in terminal, no browser | MAP-TERMINAL, MAP-EVOLVE |
| Portability: bind-not-embed; state/packaging/governance diligence | BIND-NOT-EMBED, DEPLOY-PORTABILITY |
| ADV-13: routing — compound in, simple out | ROUTE-COMPOUND, ROUTE-SIMPLE |
| ADV-15 renderings: Mermaid + no live server | MAP-MERMAID, MAP-NO-SERVER |
| Catalog consequence schema | CAT-SCHEMA, CAT-COMMANDS, CAT-ACTIVATES |

## 9. Out of scope for this plan

- The correctness of #10's validators and the human-authored manifest (owned by #10's suite) — the Advisor
  authors no manifest and this plan tests only the recommendation + record + handoff.
- The pedagogical quality of the question wording (human review of the catalog content, not an automated
  test).
- Any change to platform-bootstrap (FR-25) — the deploy handoff is a human step (ADR-A7); a machine
  handoff, if ever wanted, is a separately scoped FR-25 change with its own tests.
