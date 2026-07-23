# Agentic Design Advisor: Test Plan — v3.2 (core scope lock)

> Verifies the design [`01-design.md`](01-design.md) against the requirements
> [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). **v3.2** — command + composed-workflow model (v2), round-2 fixes, then the round-4 **core
> scope lock** ([`../agentic-core-scope.md`](../agentic-core-scope.md)): **FLOOR-SUBSET** (obligation-first,
> B3), **AUTHOR-CONTRACT**/**AUTHOR-EVAL-CORE** (B1/M1), **RERUN-RECONCILE** (M4), **MAP-CORE-SCOPE** (M8
> defer), ROLE-ATTR attributes-not-gates (M9), `deferred`≠`waived` (m3). Status: **draft, pending Codex
> round 5**.

## 1. What must be true

1. **Proportionate composition** — the workflow HITL composes follows risk; low-risk is short, high-risk
   is full (ADV-3).
2. **No orphan questions** — every catalog question changes the output (ADV-4).
3. **Deterministic, honest floor** — the floor is a reproducible function of **#10's activation predicates**
   (Tier scales depth, not membership — round-5 B1); a floor command cannot be dropped silently (ADV-5/ADV-12).
4. **Recommend, not decide** — a recommendation + rationale + recorded chosen/rejected for every menu;
   overrides recorded (ADV-6/ADV-9).
5. **Commands author the manifest** — the artifacts they write make #10's per-check activation run exactly
   the right checks; **no seed, no active-validator list** (ADV-8). *(The Advisor requires no change to #10
   for its authoring; #10 separately gained `check_observability` via its own CR-9 elevation — the Advisor
   authors into it, but did not cause it. So "no #10 change **at the Advisor's behest**", not "#10 is
   frozen".)*
6. **Deploy: record + human-carry** — recommends managed by default, records, prompts a human handoff,
   provisions nothing (ADV-14).
7. **Durable + reproducible** — the decision record (scenario + composed workflow + decisions) regenerates
   from the answers; a re-run reproduces the workflow (ADV-7).

## 2. Test levels

- **Catalog lint** (static, `ci/agentic-advisor/test_catalog_lint.py`) — the question/option catalog as data.
- **Composition + floor units** (`ci/agentic-advisor/test_compose.py`) — the intake→workflow composer and
  floor function over scripted answers.
- **Manifest-authoring integration** (`ci/agentic-advisor/test_manifest_authoring.py`) — the commands'
  output run through **#10's real** `check_manifest_agentic.py`.
- **Command behavior** (skill-lint + scripted end-to-end) — the `hitl:agentic-*` commands.

## 3. Catalog lint (ADV-4, ADR-A2)

| Case | Fixture | Expect |
|---|---|---|
| CAT-CONSEQUENCE | every entry parsed | each has a **non-empty `consequence`**; an orphan question fails |
| CAT-SCHEMA | each `consequence` | is an **option→list map** (LLD §2.3): every `options` value has a key (or `"*"`); each list item is a **tagged union** (`kind` from the enum + a resolvable `target`) |
| CAT-COVERAGE | the entry set | every lens (HLD §2 + stakes/tier/compliance, cost) has ≥1 entry — including **observability**, **kill-switch**, **portability** |
| CAT-COMMANDS | each `kind:command` consequence | the command exists in the `hitl:agentic-*` set (no dangling command) |
| CAT-ACTIVATES | each `kind:manifest_field` consequence | the field/check exists in #10's real schema/check set (incl. `observability`→`check_observability`); a `kind:declared_artifact` (**kill-switch only**) is **not** required to resolve to a #10 field |
| CAT-ROLE | each entry | a valid role from `docs/playbook/roles.md` (PM/Technical Advisor/Architect/Developer/QA/Ops) |
| CAT-REFRESH | the refresh trigger | a Tier-3 fixture prompts a curated-refresh review step; **no live external call is made** (ADR-A2) |

## 4. Composition + floor (ADV-3/ADV-5/ADV-12) — floor DERIVED from #10 activation (round-5 B1)

Two **exact, constructable fixtures** with their computed `floor`/`rungs`/`workflow` (hand-run through the
§4 composer; the floor is a pure function of #10 activation, so tier does not change *which* controls are
floor — only their depth). These are the canonical low/high cases; older impossible fixtures are removed.

**Fixture LOW** (`.hitl/agentic-scenario.yaml`) — Tier-1, 2-agent, read-only, internal, greenfield:
```yaml
components: [{id: a1, name: intake, kind: simple_agent}, {id: a2, name: resolver, kind: simple_agent}]
edges:      [{id: e1, from: a1, to: a2, kind: sync_call}]
answers:    {stakes: internal, side_effects: none, data: none, autonomy: assisted, scale: small, greenfield: true}
tier: 1
```
→ **floor** = `[agentic-boundary, agentic-classify, agentic-evals, agentic-observability, agentic-privilege]`;
**rungs** = `[agentic-deploy]`; **workflow** = floor ∪ rungs. *(Honest: a 2-agent compound flow activates #10's
classification/boundary/authorization/capabilities/eval/observability checks, so those are floor, not
deferrable. Depth is minimal — observability = `report_or_existing_surface`, privilege = `per_class`, eval
= `baseline`.)*

**Fixture HIGH** — Tier-2, 4-component (2 agents), irreversible, PII, supervised, one async edge, greenfield:
```yaml
components: [{id: a1, name: intake, kind: simple_agent}, {id: a2, name: resolver, kind: simple_agent},
             {id: s1, name: account_svc, kind: deterministic}, {id: d1, name: ledger, kind: deterministic}]
edges:      [{id: e1, from: a1, to: s1, kind: sync_call}, {id: e2, from: a1, to: a2, kind: sync_call},
             {id: e3, from: a2, to: d1, kind: async_task}]
answers:    {stakes: customer_facing, side_effects: irreversible, data: pii, autonomy: supervised, scale: small, greenfield: true}
tier: 2
```
→ **floor** = `[agentic-boundary, agentic-classify, agentic-evals, agentic-observability, agentic-privilege,
agentic-reliability]` (reliability floor via `human_gate_needed` = irreversible, and `check_async` fires on
`e3`); **rungs** = `[agentic-deploy]`; **workflow** = floor ∪ rungs.

| Case | Scenario | Expect |
|---|---|---|
| **COMPOSE-LOW** | Fixture LOW | exact `floor`/`rungs`/`workflow` above; **deploy is a rung (greenfield), never floor** (no #10 check owns it) |
| **COMPOSE-HIGH** | Fixture HIGH | exact `floor`/`rungs`/`workflow` above; reliability enters the floor (irreversible ⇒ human-gate; async ⇒ `check_async`) |
| **ACTIVATION-MIRROR** | `ACTIVATES` (Advisor LLD §4) vs #10's real activation table (compound LLD §6.0) | field-for-field match; every `OWNS_CHECKS` entry is a real #10 check; a deliberate desync makes the test fail (proves floor cannot drift from #10 — B1) |
| **FLOOR-EQ-ACTIVATION** | for LOW and HIGH, author the manifest, run #10 | every floor command's owned #10 check **activates**; no floor command's check is dormant, and no dormant-check command is floor (floor ≡ activation) |
| PRUNE-DEPLOY | a change to an existing deployed system (not greenfield, no platform change) | `agentic-deploy` **not** composed (M6 — deploy is not "always") |
| **FLOOR-DET** | run Fixture HIGH twice | **identical** floor + workflow (deterministic, ADV-12) |
| **FLOOR-SUBSET** | sweep {risk-factor space} × {tier 0..3}; compute `floor_commands(s)` and `compose(s,t).workflow` | `floor ⊆ workflow` at **every** point (floor is unioned into the workflow — B3) |
| **FLOOR-BLOCK** | Tier 2 + irreversible, then drop the human gate with **no waiver** | **blocker** — a floor command can't be dropped *silently* (ADV-12) |
| **FLOOR-WAIVER** | same, but record an explicit tier-appropriate waiver (owner/reason/tier-limit/revisit) | **allowed** — the gate is dropped via a recorded **waiver**, per FR-25 (ADR-A6); the waiver lands in the decision record, state `waived` |
| FLOOR-DEFER | Fixture HIGH, then defer the offered `agentic-deploy` rung | allowed; recorded as **`deferred`** (a rung deferral, *not* a `waiver` — distinct states, round-4 m3) |
| FLOOR-WAIVER-10 | Fixture HIGH, drop the floor `agentic-evals` control via a waiver | the waiver is written to **#10's own store** (`docs/03-engineering/evals/waivers.yaml`), the Advisor mirrors a pointer in the decision record — **one** authoritative waiver #10 reads (round-5 B1); dropping it with no waiver → `floor_dropped_no_waiver` blocker |
| **KILL-SWITCH** | supervised/autonomous + side effects, no declared kill-switch | `agentic-reliability` requires one; absence blocks |
| **OBSERVABILITY** | Tier 2, no detectability declared | `agentic-observability` requires tracing + a misbehavior eval hook |

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

## 6. Manifest-authoring — the v2 replacement for the seed-contract tests (ADV-8, ADR-A5)

The critical property: the commands write manifest fields such that **#10's real activation** runs
the right checks. These tests run the authored manifest through #10's real `check_manifest_agentic.py`.

| Case | Fixture | Expect |
|---|---|---|
| **AUTHOR-LOW** | Fixture LOW's authored manifest | #10 activates exactly the LOW floor's owned checks — `check_classification`, `check_topology`/`check_references`, `check_authorization` (a1→a2 into an agent), `check_boundary_legs` (agent→agent), `check_capabilities`, `check_eval_coverage`, `check_observability`; **skips** `check_async`/`check_lifecycle`/`check_saga`/`check_memory`/`check_deep_agent`. Every activated check has an authoring command in the composed workflow (floor ≡ activation — no fictional seam) |
| **AUTHOR-HIGH** | Fixture HIGH's authored manifest | as AUTHOR-LOW plus **`check_async`** (edge `e3`); reliability authored the async fields; verified against #10 LLD §6.0 |
| **AUTHOR-CONTRACT** | Fixture HIGH's `agentic-boundary` output | authors `domains[callee].facade_apis[facade_name]` **and** `interactions[].authorization.allowed_callers`; #10 → `check_references`/`check_authorization` resolve; a missing facade/authz makes #10 block (round-4 B1) |
| **AUTHOR-EVAL-CORE** | Fixture HIGH's `agentic-evals` output | one eval spec **per agent** + one e2e segment spec; a deterministic component with no spec does **not** block (core = agents+e2e); no `result_review` gate in core (deferred, round-5 B3) |
| **AUTHOR-OBSERV** | Fixture LOW's `agentic-observability` output at Tier 1 | authors `observability` with `eval_console.access: report_or_existing_surface` + a **resolvable** `ref` + convention-required `attributes`; #10 `check_observability` **passes**; a `ref` that resolves to nothing, `attributes:["TODO"]`, or a missing `eval_console` → **blocks** (round-5 M3 — real, tier-scaled, not theater) |
| **AUTHOR-DECLARED** | the kill-switch output | recorded as a **declared artifact** in the decision record; **no** kill-switch check exists in #10 today; present, not silently omitted (ADR-A5 §7). *(Observability is no longer here — it authors a #10-validated field, see AUTHOR-OBSERV.)* |
| AUTHOR-NO-SEED | the Advisor's output artifacts | there is **no** `.hitl/agentic-profile.yaml` "active-validator set" consumed by #10; #10 activates purely from manifest content (proves the v1 fiction is gone) |
| AUTHOR-NO-DUP | the Advisor's code/output | contains **no** copy of #10's validator logic — it authors manifest fields, #10 validates |

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
| **E2E-SUPPORT** | the worked example (HLD §9), Fixture HIGH: scripted answers → floor `{classify, boundary, privilege, reliability, observability, evals}` + rung `{deploy}` → commands author the manifest → #10 activates exactly the floor's owned checks → deploy recorded + human-carry prompted |
| STANDALONE-CMD | a single command (e.g. `agentic-privilege`) run **directly** on an existing design | runs standalone (ADV-1) — this is the supported path for a **single-component** system; the full compound intake is **not** invoked for one component (routing, §ROUTE-SIMPLE). *(No single-agent E2E fixture — a single component is not the Advisor's compound domain.)* |
| **MAP-TERMINAL** | run the intake in a terminal (no browser) | a **text/box-drawing** map + getting/not-needed lines are printed inline; **no browser is required** (ADV-15) |
| **MAP-EVOLVE** | add components/decisions step by step | the map **regenerates per step** — a node/annotation/panel-item appears each step; the not-needed items show their reason |
| **MAP-MERMAID** | the decision record after a run | contains a **Mermaid** topology + getting/available/not-needed table; regenerating the record is **deterministic** (same scenario → same map, no drift) |
| **MAP-NO-SERVER** | the Advisor's runtime footprint | it **writes files / prints text only** — no live-reload server or hosted dashboard is started (ADR-A8, governs-not-runtime) |
| MAP-CORE-SCOPE | the core map deliverable | is **terminal + Mermaid only**; the rich **HTML rendering and the combined "chat + live map" mode are deferred** (no core test — round-4 M8); the core suite passes without them |

## 8. Coverage of acceptance scenarios

| Acceptance scenario (requirements §8) | Tests |
|---|---|
| 1. Non-expert → right-sized composed workflow + floor + record | E2E-SUPPORT, REC-DOC |
| 2. Low-stakes → proportionate workflow; only truly-optional commands absent | COMPOSE-LOW, PRUNE-DEPLOY (floor still ≡ #10 activation) |
| 3. High-stakes → full workflow, floor can't be dropped silently | COMPOSE-HIGH, FLOOR-BLOCK, KILL-SWITCH |
| 4. Every recommendation recorded + overridable | REC-RECORD, REC-OVERRIDE |
| 5. Commands author manifest → #10 activation runs the right checks; floor ≡ activation; observability a #10-gated field; kill-switch a declared artifact | AUTHOR-LOW, AUTHOR-HIGH, ACTIVATION-MIRROR, FLOOR-EQ-ACTIVATION, AUTHOR-OBSERV, AUTHOR-CONTRACT, AUTHOR-DECLARED, AUTHOR-NO-SEED |
| 6. Durable + re-runnable, no drift | FLOOR-DET, REC-REGEN, RERUN-RECONCILE |
| 7. Deploy: managed default, reason to build, record + human-carry, no provisioning | DEPLOY-MANAGED, DEPLOY-BUILD-REASON, DEPLOY-EXAMPLES, DEPLOY-RECORD-CARRY, DEPLOY-PORTABILITY |
| 8. Floor computation deterministic (given declared factors) | FLOOR-DET, FLOOR-SUBSET |
| 9. Floor waivable via recorded waiver, not silent drop | FLOOR-BLOCK, FLOOR-WAIVER |
| 10. (ADV-15) map renders in terminal, no browser | MAP-TERMINAL, MAP-EVOLVE |
| Portability: bind-not-embed; state/packaging/governance diligence | BIND-NOT-EMBED, DEPLOY-PORTABILITY |
| ADV-13: routing — compound in, simple out | ROUTE-COMPOUND, ROUTE-SIMPLE |
| ADV-15 renderings: Mermaid + no live server | MAP-MERMAID, MAP-NO-SERVER |
| Catalog consequence schema | CAT-SCHEMA, CAT-COMMANDS, CAT-ACTIVATES |

## 9. Out of scope for this plan

- The correctness of #10's individual validators (owned by #10's suite) — here we test only that the
  authored manifest **activates the right set** through #10's real activation.
- The pedagogical quality of the question wording (human review of the catalog content, not an automated
  test).
- Any change to platform-bootstrap (FR-25) — the deploy handoff is a human step (ADR-A7); a machine
  handoff, if ever wanted, is a separately scoped FR-25 change with its own tests.
