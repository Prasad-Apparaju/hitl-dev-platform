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
3. **Deterministic, honest floor** — the floor is a reproducible function of Tier + risk; a high-risk
   change cannot drop a floor command (ADV-5/ADV-12).
4. **Recommend, not decide** — a recommendation + rationale + recorded chosen/rejected for every menu;
   overrides recorded (ADV-6/ADV-9).
5. **Commands author the manifest** — the artifacts they write make #10's *unmodified* per-check
   activation run exactly the right checks; **no seed, no #10 change** (ADV-8).
6. **Deploy: record + human-carry** — recommends managed by default, records, prompts a human handoff,
   provisions nothing (ADV-14).
7. **Durable + reproducible** — the decision record (scenario + composed workflow + decisions) regenerates
   from the answers; a re-run reproduces the workflow (ADV-7).

## 2. Test levels

- **Catalog lint** (static, `ci/agentic-advisor/test_catalog_lint.py`) — the question/option catalog as data.
- **Composition + floor units** (`ci/agentic-advisor/test_compose.py`) — the intake→workflow composer and
  floor function over scripted answers.
- **Manifest-authoring integration** (`ci/agentic-advisor/test_manifest_authoring.py`) — the commands'
  output run through **#10's real, unmodified** `check_manifest_agentic.py`.
- **Command behavior** (skill-lint + scripted end-to-end) — the `hitl:agentic-*` commands.

## 3. Catalog lint (ADV-4, ADR-A2)

| Case | Fixture | Expect |
|---|---|---|
| CAT-CONSEQUENCE | every entry parsed | each has a **non-empty `consequence`**; an orphan question fails |
| CAT-SCHEMA | each `consequence` | is a valid **tagged union** (HLD §4.2): a `kind` from the enum + a resolvable `target` |
| CAT-COVERAGE | the entry set | every lens (HLD §2 + stakes/tier/compliance, cost) has ≥1 entry — including **observability**, **kill-switch**, **portability** |
| CAT-COMMANDS | each `kind:command` consequence | the command exists in the `hitl:agentic-*` set (no dangling command) |
| CAT-ACTIVATES | each `kind:manifest_field` consequence | the field/check exists in #10's real schema/check set; a `kind:declared_artifact` (kill-switch/observability) is **not** required to resolve to a #10 field |
| CAT-ROLE | each entry | a valid role from `docs/playbook/roles.md` (PM/Technical Advisor/Architect/Developer/QA/Ops) |
| CAT-REFRESH | the refresh trigger | a Tier-3 fixture prompts a curated-refresh review step; **no live external call is made** (ADR-A2) |

## 4. Composition + floor (ADV-3/ADV-5/ADV-12)

Scripted-answer fixtures; assert the composed command list, the floor, and reproducibility.

| Case | Scripted answers | Expect |
|---|---|---|
| **COMPOSE-LIGHT** | 1 component, no side effects, internal, no PII (HLD §9.6) | *(1 component ⇒ not compound ⇒ routed to the single-agent surface, Advisor not invoked)* — as a composer unit-test: workflow = `agentic-classify` (+ offered `agentic-evals`); saga/async/deep/deploy **not** composed |
| **OBSERV-FLOOR** | a **low-stakes 2-agent read-only** compound flow (internal, no side effects, Tier 1) | `agentic-observability` **is in the floor** at **minimal depth** (basic trace + simple PM eval-console) — proves observability is floor for **any** agentic system (hard directive), presence non-negotiable, depth scales; still no saga/deep/reliability |
| **COMPOSE-HEAVY** | 4 components (2 agents), irreversible, PII, supervised, Tier 2 (HLD §9.3) | floor = classify, boundary, privilege, reliability(gate+kill-switch), observability, evals, deploy; `agentic-memory` **offered**; saga/async/deep **not** composed |
| PRUNE-SIDEEFFECT | side effects = none | no reliability/saga/idempotency command composed |
| PRUNE-SINGLE | single component | no boundary/topology/privilege-by-edge command composed |
| **FLOOR-DET** | run COMPOSE-HEAVY's answers twice | **identical** floor + workflow (deterministic, ADV-12) |
| **FLOOR-RULE** | matrix over {stakes × side_effects × data × autonomy × scale} | each floor matches the §5 rule table (union/precedence) |
| **FLOOR-SUBSET** | sweep {risk-factor space} × {tier 0..3}, for each compute `floor_commands` and `compose().workflow` | `floor ⊆ workflow` at **every** point — no `(s,tier)` where a floor rule fires but its command is absent (obligation-first, round-4 B3); e.g. `data==pii` on a non-agent path still forces `agentic-privilege` in |
| **FLOOR-BLOCK** | Tier 2 + irreversible, then drop the human gate with **no waiver** | **blocker** — a floor command can't be dropped *silently* (ADV-12) |
| **FLOOR-WAIVER** | same, but record an explicit tier-appropriate waiver (owner/reason/tier-limit/revisit) | **allowed** — the gate is dropped via a recorded **waiver**, per FR-25 (ADR-A6); the waiver lands in the decision record, state `waived` |
| FLOOR-DEFER | COMPOSE-HEAVY, then defer the offered `agentic-memory` rung | allowed; recorded as **`deferred`** (a rung deferral, *not* a `waiver` — distinct states, round-4 m3) |
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

The critical property: the commands write manifest fields such that **#10's unmodified activation** runs
the right checks. These tests run the authored manifest through #10's real `check_manifest_agentic.py`.

| Case | Fixture | Expect |
|---|---|---|
| **AUTHOR-LIGHT** | COMPOSE-LIGHT's authored manifest | #10 activates only classification (+ graph integrity); **no** capability/boundary/saga/async checks; **no new registry required**; **#10 unchanged** |
| **AUTHOR-HEAVY** | COMPOSE-HEAVY's authored manifest | #10 activates `check_classification`, `check_topology`+`check_references` (interactions present), `check_authorization` (interactions target agents), `check_boundary_legs`, `check_capabilities`, `check_lifecycle`, `check_eval_coverage`, **`check_observability`** (agent present — the floor gate, hard directive); **skips** `check_saga`/`check_async`/`check_deep_agent`; verified against #10 LLD §6.0 |
| **AUTHOR-CONTRACT** | COMPOSE-HEAVY's `agentic-boundary` output | authors `domains[callee].facade_apis[]` **and** `interactions[].authorization.allowed_callers`; run through #10 → `check_references` resolves the facades and `check_authorization` resolves the callers (proves the contract seam is authored, round-4 B1); a missing facade/authz would make #10 block |
| **AUTHOR-EVAL-CORE** | COMPOSE-HEAVY's `agentic-evals` output | authors one eval spec **per agent** + one e2e segment spec (core scope); a **deterministic** component with no spec does **not** block #10 (`check_eval_coverage` core = agents+e2e, v3.2/M1) |
| **AUTHOR-OBSERV** | COMPOSE-HEAVY's `agentic-observability` output | authors the top-level `observability` block (`tracing{convention,hops,attributes}` + `cost_budget` + `eval_console{access,owner,ref}`); run through #10 → **`check_observability` passes**; removing the block or the `eval_console` → #10 **blocks** (the floor gate, hard directive) |
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
| **E2E-SUPPORT** | the worked example (HLD §9): scripted answers → composed 6-command floor + 1 offered rung → commands author the manifest → #10 activates the expected checks → deploy recorded + human-carry prompted |
| E2E-TRIVIAL | HLD §9.6: single summarizer, internal → near-empty workflow, L0 floor, team barely touched |
| **MAP-TERMINAL** | run the intake in a terminal (no browser) | a **text/box-drawing** map + getting/not-needed lines are printed inline; **no browser is required** (ADV-15) |
| **MAP-EVOLVE** | add components/decisions step by step | the map **regenerates per step** — a node/annotation/panel-item appears each step; the not-needed items show their reason |
| **MAP-MERMAID** | the decision record after a run | contains a **Mermaid** topology + getting/available/not-needed table; regenerating the record is **deterministic** (same scenario → same map, no drift) |
| **MAP-NO-SERVER** | the Advisor's runtime footprint | it **writes files / prints text only** — no live-reload server or hosted dashboard is started (ADR-A8, governs-not-runtime) |
| MAP-CORE-SCOPE | the core map deliverable | is **terminal + Mermaid only**; the rich **HTML rendering and the combined "chat + live map" mode are deferred** (no core test — round-4 M8); the core suite passes without them |

## 8. Coverage of acceptance scenarios

| Acceptance scenario (requirements §8) | Tests |
|---|---|
| 1. Non-expert → right-sized composed workflow + floor + record | E2E-SUPPORT, REC-DOC |
| 2. Low-stakes → short workflow, heavy commands absent | COMPOSE-LIGHT, PRUNE-*, E2E-TRIVIAL |
| 3. High-stakes → full workflow, floor can't be dropped silently | COMPOSE-HEAVY, FLOOR-BLOCK, KILL-SWITCH |
| 4. Every recommendation recorded + overridable | REC-RECORD, REC-OVERRIDE |
| 5. Commands author manifest → #10 activation runs the right checks; observability authored as a #10-gated field; kill-switch recorded as a declared artifact | AUTHOR-LIGHT, AUTHOR-HEAVY, AUTHOR-OBSERV, AUTHOR-CONTRACT, AUTHOR-DECLARED, AUTHOR-NO-SEED |
| 6. Durable + re-runnable, no drift | FLOOR-DET, REC-REGEN |
| 7. Deploy: managed default, reason to build, record + human-carry, no provisioning | DEPLOY-MANAGED, DEPLOY-BUILD-REASON, DEPLOY-EXAMPLES, DEPLOY-RECORD-CARRY, DEPLOY-PORTABILITY |
| 8. Floor computation deterministic (given declared factors) | FLOOR-DET, FLOOR-RULE |
| 9. Floor waivable via recorded waiver, not silent drop | FLOOR-BLOCK, FLOOR-WAIVER |
| 10. (ADV-15) map renders in terminal, no browser | MAP-TERMINAL, MAP-EVOLVE |
| Portability: bind-not-embed; state/packaging/governance diligence | BIND-NOT-EMBED, DEPLOY-PORTABILITY |
| ADV-13: routing — compound in, simple out | ROUTE-COMPOUND, ROUTE-SIMPLE |
| ADV-15 renderings: Mermaid + no live server | MAP-MERMAID, MAP-NO-SERVER |
| Catalog consequence schema | CAT-SCHEMA, CAT-COMMANDS, CAT-ACTIVATES |

## 9. Out of scope for this plan

- The correctness of #10's individual validators (owned by #10's suite) — here we test only that the
  authored manifest **activates the right set** through #10's real, unmodified activation.
- The pedagogical quality of the question wording (human review of the catalog content, not an automated
  test).
- Any change to platform-bootstrap (FR-25) — the deploy handoff is a human step (ADR-A7); a machine
  handoff, if ever wanted, is a separately scoped FR-25 change with its own tests.
