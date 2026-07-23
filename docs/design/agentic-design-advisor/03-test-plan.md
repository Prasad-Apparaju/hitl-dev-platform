# Agentic Design Advisor: Test Plan — v4.1 (one intake · recommendation report · neutral handoff)

> Verifies the design [`01-design.md`](01-design.md) (HLD v4.1) + ADRs against the requirements
> [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). **This plan was rewritten for v4.1** (round-10) — the auto-authoring and 8-command test
> families are gone. The Advisor is **one `hitl:agentic-intake` command** that produces a **recommendation
> report** + a **neutral `agentic-design-handoff.yaml`**; it authors **no** manifest field. There is **no**
> per-lens command, **no** manifest skeleton, and **no** #10 field in any Advisor output. Status: **v4.1.**

## 1. What must be true

1. **One intake, a proportionate report.** There is one command, `hitl:agentic-intake`; the recommendation
   report's sections are the relevant lenses; low-risk is short, high-risk full (ADV-1/ADV-3).
2. **No orphan questions.** Every catalog question changes the report (ADV-4).
3. **Deterministic, honest recommended floor.** The floor is a reproducible function of the **safety-relevant
   risk factors** (topology, side effects, autonomy, async) — **not** #10 activation, **no** `tier`-computed
   depth. A recommended-floor control cannot be **skipped silently** — a skip is recorded (owner/reason); the
   hard block-or-waive is **downstream at #10** (ADV-5/ADV-12).
4. **Recommend, not decide.** A recommendation + rationale + recorded chosen/rejected for every menu;
   overrides recorded (ADV-6/ADV-9).
5. **Hand off, don't author.** The output is a **decision record + a neutral `agentic-design-handoff.yaml`**
   (`proposed_kind`s + neutral `connections` + recommendation IDs + `target_path_hint`s). It contains **no**
   `system-manifest.yaml` field — no `kind`, no `domains`, no `interactions`, no authored legs. A human
   authors the manifest; **#10 validates** it (ADV-8, ADR-A5).
6. **Deploy lens: record + human-carry.** The deploy lens recommends managed by default, records, prompts a
   human handoff, provisions nothing (ADV-14). It is a report section, not a command.
7. **Durable + reproducible.** The decision record regenerates from the canonical state; a re-run reproduces
   the report (ADV-7).

## 2. Test levels

- **Catalog lint** (`ci/agentic-advisor/test_catalog_lint.py`) — the question/option catalog as data.
- **Composition + recommended-floor units** (`ci/agentic-advisor/test_compose.py`) — the intake → report
  sections + floor over scripted answers, run against the **canonical** scenario shape (`proposed_kind` /
  `transport`).
- **Handoff** (`ci/agentic-advisor/test_handoff.py`) — the neutral `agentic-design-handoff.yaml` is generated
  from the state and contains **no** manifest field.
- **Intake behavior** (skill-lint + scripted end-to-end) — the one `hitl:agentic-intake` command.

## 3. Catalog lint (ADV-4, ADR-A2)

| Case | Fixture | Expect |
|---|---|---|
| CAT-CONSEQUENCE | every entry | a non-empty `consequence`; an orphan question fails |
| CAT-SCHEMA | each `consequence` | an **option→list map** (LLD §2.3): every `options` value has a key (or `"*"`); each item is a tagged union (`kind` from the enum + a resolvable `target`) |
| CAT-COVERAGE | the entry set | every lens (HLD §2 + stakes/tier/compliance, cost) has ≥1 entry — incl. **observability**, **kill-switch**, **portability** |
| CAT-LENS | each `kind:lens` consequence | the target resolves to a real report-section lens; **no `kind:command`/`manifest_field` exists** (one command; the Advisor targets no #10 field) |
| CAT-RECOMMEND | each `kind:recommendation`/`recorded_artifact` | resolves to a recorded id; observability + kill-switch are `recommendation` entries |
| CAT-ROLE | each entry | a valid role from `docs/playbook/roles.md` |
| CAT-REFRESH | the refresh trigger | a Tier-3 fixture prompts a curated-refresh review; **no live external call** (ADR-A2) |

## 4. Composition + recommended floor (ADV-3/ADV-5/ADV-12) — safety factors, NOT #10 activation

Two **canonical-shaped** fixtures (`proposed_kind` / `transport` — the same schema the composer, map, and
records use; round-10 B3). The floor is the Advisor's **recommendation** — advice, not a gate.

**Fixture LOW** — Tier-1, 2-agent, read-only, internal, greenfield:
```yaml
components: [{id: a1, role: agent, proposed_kind: simple_agent}, {id: a2, role: agent, proposed_kind: simple_agent}]
edges:      [{id: e1, from: a1, to: a2, transport: sync_call}]
answers:    {stakes: internal, side_effects: none, data: none, autonomy: assisted, scale: small, greenfield: true}
tier: 1
```
→ **floor** = `[boundary, classify, evals, observability, privilege]`; **rungs** = `[deploy]`; **report
sections** (ordered) = `[classify, boundary, privilege, observability, evals, deploy]`. *(Verified by running
the LLD §4 composer against this exact canonical state — no `KeyError`.)*

**Fixture HIGH** — Tier-2, 4-component (2 agents), irreversible, PII, supervised, one async edge, greenfield:
```yaml
components: [{id: a1, role: agent, proposed_kind: simple_agent}, {id: a2, role: agent, proposed_kind: simple_agent},
             {id: s1, role: service, proposed_kind: deterministic}, {id: d1, role: datastore, proposed_kind: deterministic}]
edges:      [{id: e1, from: a1, to: s1, transport: sync_call}, {id: e2, from: a1, to: a2, transport: sync_call},
             {id: e3, from: a2, to: d1, transport: async_task}]
answers:    {stakes: customer_facing, side_effects: irreversible, data: pii, autonomy: supervised, scale: small, greenfield: true}
tier: 2
```
→ **floor** = `[boundary, classify, evals, observability, privilege, reliability]` (reliability recommended
via the irreversible human-gate rule **and** the async edge — round-10 blocker 4); **rungs** = `[deploy]`;
**report sections** = `[classify, boundary, privilege, reliability, observability, evals, deploy]`.

| Case | Scenario | Expect |
|---|---|---|
| **COMPOSE-LOW** | Fixture LOW | exact floor/rungs/report above; deploy is a rung (greenfield), never floor; runs from the **canonical `proposed_kind`** state |
| **COMPOSE-HIGH** | Fixture HIGH | exact floor/rungs/report above; reliability in the floor (irreversible ⇒ gate; async ⇒ reliability advice) |
| **CANONICAL-RUN** | the composer over a state with `proposed_kind`/`transport` (no `kind`) | runs with **no `KeyError`** — one component schema across composer/state/fixtures/map/rerun (round-10 B3) |
| PRUNE-DEPLOY | a change to an existing deployed system (not greenfield, no platform change) | the deploy lens is **not** a section (M6 — not "always") |
| FLOOR-DET | run Fixture HIGH twice | identical floor + report (deterministic; `compose(s)` takes no `tier` — no computed depth) |
| **FLOOR-SKIP** | Fixture HIGH, then skip the recommended reliability (human gate) | recorded in `skips: [{control, owner, reason}]`, surfaced in the handoff; the Advisor **does not block** and grants **no** exception — the hard block-or-waive is downstream at **#10** (ADR-A6, blocker 5) |
| FLOOR-SKIP-SILENT | skip a recommended-floor control with **no** owner/reason | rejected — a skip must be recorded (owner + reason); silent skip not allowed (ADV-12) |
| FLOOR-DEFER | defer the offered `deploy` rung | allowed; recorded as **`deferred`** (a rung deferral, distinct from a floor **`skip`**) |
| ASYNC-RELIABILITY | a reversible, assisted flow with one async edge | reliability **is** in the recommended floor (any async ⇒ reliability advice — blocker 4), consistent with `relevant()` |

## 5. Recommend-not-decide + the deploy lens (ADV-6/ADV-9/ADV-14)

| Case | Fixture | Expect |
|---|---|---|
| REC-SIMPLEST | a menu where a simple and a complex option both fit | recommends the **simplest**; complex listed as rejected **with its cost** |
| REC-RECORD | any menu decision | record has chosen **and** rejected + rationale |
| REC-OVERRIDE | human overrides | override + reason recorded; no silent apply |
| **DEPLOY-MANAGED** | the deploy lens, low stakes + small scale + no data-residency | recommends **managed**; from-scratch rejected with its cost (ADV-14) |
| DEPLOY-BUILD-REASON | override toward build | requires a specific reason; recorded |
| DEPLOY-PORTABILITY | a managed recommendation | requires the three portability answers (governance/packaging/state) |
| DEPLOY-RECORD-CARRY | after the decision | recorded + a human prompted to carry it to platform/ops; **nothing provisioned or auto-handed-off** |

## 6. The handoff — neutral, no manifest field (ADV-8, round-10 B2)

The handoff is `agentic-design-handoff.yaml`, explicitly **not** `system-manifest.yaml` (LLD §7.4).

| Case | Fixture | Expect |
|---|---|---|
| **HANDOFF-NEUTRAL** | the generated handoff for Fixture HIGH | contains `components` (with `proposed_kind` + `role`), neutral `connections` (`from`/`to`/`transport`), `recommendations` (ids + `target_path_hint`s); it is valid YAML and self-consistent |
| **NO-AUTHOR** | the generated handoff | contains **no** `kind:`, **no** `domains`, **no** `interactions`, **no** authored legs/scopes/policies — **no `system-manifest.yaml` field value** anywhere (the boundary; a lint rejects any manifest-shaped key) |
| HANDOFF-REF-INTEGRITY | recommendation IDs + `target_path_hint`s | every recommendation id is unique; every `target_path_hint` names a plausible manifest path (a *location*, not a value); a dangling/duplicate id fails |
| HANDOFF-HUMAN | the design step | a human authors the real manifest from the handoff; **#10 validates it** — the handoff is not run through #10 by the Advisor |
| NO-SEED | the Advisor's outputs | there is **no** `.hitl/agentic-profile.yaml` or active-validator seed consumed by #10; #10 needs no Advisor input |

## 7. Records, re-run, map (ADV-7/ADV-10/ADV-15)

| Case | Check |
|---|---|
| REC-DOC | a run writes `agentic-decisions.md` (scenario + report + decisions) |
| REC-REGEN | a re-run **regenerates** the record (not appends); no drift |
| **RERUN-RECONCILE** | change a component/answer and re-run | the report is recomputed; unchanged decisions kept; a changed-input decision flagged stale for re-confirm; a removed one → `retired`; recorded **skips** (not "waivers") are reconciled; human confirms a diff before write |
| ROLE-ATTR | each catalog lens attributes to a real role; a role filter is presentation-only, never gating which lens exists |
| **STANDALONE-LENS** | re-run the intake scoped to one lens (e.g. privilege) on an existing design | runs — the supported single-lens path (there is **no** `hitl:agentic-privilege` command); the full intake is not invoked for a single component |
| MAP-TERMINAL | run the intake in a terminal | a text/box-drawing map + getting/not-needed lines printed inline; no browser |
| MAP-MERMAID | the decision record | a Mermaid topology + table; regenerating is deterministic |
| **ROLE-TOTAL** | every component's `role` | exactly one value from `{agent,service,datastore,external,store}` (directly elicited, required); no derivation, no conflict, no unset — total & single-valued (blocker 7) |
| MAP-CORE-SCOPE | the core map deliverable | terminal + Mermaid only; rich HTML + combined mode **deferred** (#43); core suite passes without them |
| MAP-NO-SERVER | the Advisor's footprint | writes files / prints only — no live-reload server (ADR-A8) |

## 8. Coverage of acceptance scenarios (requirements §8.2)

| Acceptance scenario | Tests |
|---|---|
| 1. Non-expert → one intake → report + floor + record + neutral handoff, no PM-authored design | E2E-INTAKE, HANDOFF-NEUTRAL, NO-AUTHOR |
| 2. Low-stakes → short report; observability recommended at minimal depth | COMPOSE-LOW, PRUNE-DEPLOY |
| 3. High-stakes → full report; a floor **skip** is recorded (no #10 exception) | COMPOSE-HIGH, FLOOR-SKIP, FLOOR-SKIP-SILENT |
| 4. Every recommendation recorded + overridable | REC-RECORD, REC-OVERRIDE |
| 5. Recommendation + handoff, not a design (no manifest field, no `kind`) | HANDOFF-NEUTRAL, NO-AUTHOR, NO-SEED |
| 6. Durable + re-runnable | REC-REGEN, RERUN-RECONCILE |
| 7. Deploy: managed default, reason to build, record + carry, no provisioning | DEPLOY-MANAGED, DEPLOY-BUILD-REASON, DEPLOY-PORTABILITY, DEPLOY-RECORD-CARRY |
| 8. Floor recommendation deterministic given declared factors | FLOOR-DET, COMPOSE-LOW/HIGH |
| 9. A skipped floor control is recorded (owner/reason), never silent; no #10 exception | FLOOR-SKIP, FLOOR-SKIP-SILENT |
| 10. (ADV-15) map renders in terminal, no browser | MAP-TERMINAL, MAP-MERMAID, ROLE-TOTAL |

**Removed for v4.1** (they tested the deleted models): `AUTHOR-*`, `OWNERSHIP-COMPLETE`, `FLOOR-EQ-ACTIVATION`,
`ACTIVATION-MIRROR`, `COMPOSE-DEEP`, `FLOOR-SUBSET`, `CMD-STANDALONE`/per-command tests, `CAT-COMMANDS`, and
`HANDOFF-SKELETON` (the manifest-skeleton family). The Advisor authors nothing, so there is nothing to
author-test.
