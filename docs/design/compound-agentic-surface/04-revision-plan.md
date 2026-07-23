# Compound Agentic System Surface: Revision Plan (response to Codex reviews)

> Two independent cold/neutral Codex design reviews have run. **Round 1** (2026-07-18) returned REVISIONS
> REQUIRED (6 blockers + 14 majors); the v2 rewrite addressed it. **Round 2** (2026-07-20) reviewed v2 and
> again returned REVISIONS REQUIRED (6 blockers + 12 majors) — the central miss was structural: v2 tried
> to carry parallel edges inside `interaction_matrix`, a map keyed by the domain pair, which is impossible.
> Reports: `hitl-internal/docs/validation-reports/2026-07-18-…-review.md` and `…2026-07-19-…-review-round2.md`.
> This document is the accepted response for **both** rounds; the **§ Round-2 fix-map** governs the current
> **v3** docs (HLD [`01-design.md`](01-design.md), ADRs [`02-adrs.md`](02-adrs.md), LLD
> [`03-lld.md`](03-lld.md)). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10).

## Unifying principle (unchanged)

**HITL validates declarations, coverage, and consistency — not runtime behavior.** Each over-reach claimed
to derive runtime truth that belongs to the product or crossed governs-not-runtime (ADR-5). Framework-
agnostic (ADR-4) and governs-not-runtime (ADR-5) were **upheld in both rounds**; the manifest-as-graph
skeleton stands. The rework is in the edge container, the trust legs, the privilege union, the eval
homes, and activation.

## v4 supersession (2026-07-23) — the Advisor no longer authors the manifest

The round-5→7 fix-maps below repaired the **Advisor↔#10 auto-authoring seam** (imported activation, the
manifest writer, `floor ≡ activation`, `OWNS_CHECKS`/`OWNERSHIP-COMPLETE`/`AUTHOR-COMPLETE`, and "the Advisor
authors the general waiver"). **All of that is superseded**: rounds 8–9 removed auto-authoring entirely — the
**Advisor recommends** and a **human authors** the manifest, which **#10 validates** (see FR-28 requirements
§12 + `../agentic-core-scope.md`). What **stands on the #10 side**: its schema, per-check activation
(computed solely from the human-authored manifest + tier + registries + waiver files — *no Advisor
dependency*), the general `manifest-waivers.yaml` contract (authored by a **human**), the observability floor
gate, the segment-scoped compensation-gap advisory, and the eval coverage gate (spec existence + approval;
adapter execution → #42). Read the round-5→7 entries below as history of the (now-removed) seam.

## Round-7 fix-map (v3.3 — structural root-cause fixes, superseded on the Advisor side by v4)

Round-6 returned REVISIONS REQUIRED (4 blockers + 7 majors + 4 minors): the round-5 "floor ≡ activation"
fix was itself defective — a hand copy of #10's activation table that drifted, with `check_deep_agent`/
`check_policy_refs`/`check_saga` unowned. Round-7 attacks the root cause rather than re-transcribing:

| Round-6 finding | Disposition (v3.3 round-7) |
|---|---|
| **B1** floor ≡ activation false (drifted copy + unowned checks) | The Advisor **imports #10's activation module** (`ci/manifest-agentic/activation.py`) — **no copy** to drift; `OWNS_CHECKS` completed (deep-agent/policy/saga/scope), `OWNERSHIP-COMPLETE` lint asserts every blocking check is owned. Compound LLD §6.0 (single source); Advisor LLD §4 |
| **B2** canonical state can't author a valid manifest | `authored.*` completed to be **lossless** to every #10 field (identity.privilege, async, sagas, policies, stores, orchestration, segments, deep_agent, full lifecycle/memory, facade `blurb`, `credential_justification`); id-based merge contract; `AUTHOR-COMPLETE` runs the writer output through #10's **real** validator. Advisor LLD §7.1/§7.1.1 |
| **B3** waiver escape hatch doesn't exist | Added a **general `manifest-waivers.yaml`** contract to #10 that every blocking check consults (compound LLD §6); the Advisor writes to it — the "floor is waivable" claim is now real |
| **B4** fixture activations wrong | Fixed AUTHOR-LOW (+scope_grammar), AUTHOR-HIGH (+policy_refs/lifecycle), AUTHOR-OBSERV (valid `access` enum); exact **ordered** workflow via topo tie-break; added COMPOSE-DEEP + AUTHOR-COMPLETE |
| **B5** release boundary not applied to authorities | Re-scoped **CR rows, PRD FR-26, HLD §13** (saga→advisory, PM-invoke→#42); core = 2.2.0, deferred → 2.3.0 |
| **M1** observability theater / no depth table | Honest: `ResolvableRef` is a **declaration** not runtime proof (O1); real **per-command tier-depth table** (Advisor LLD §4.1); `access` enum fixed |
| **M2** result-review half-deferred | Fully moved to #42: adapter execution out of the core file list, L5, HLD gate |
| **M3** routing two sequences | One gate→probe→route sequence in HLD/ADR/**LLD §8** (removed the ungated wording) |
| **M4** compensation-gap flow undefined | Core flow = a **declared `segment`** only; coordinator-chain heuristic deferred to #42 |
| **M5** memory unreachable rung | Added a `memory_hint` state so memory is an offered rung before declaration |
| **M6** map vocabulary underivable | Added a derived component `role` (datastore/external/output-store) computed by fixed rules from manifest content |
| **M7** trackers stale | Rewrote #10/#12/#16/#35/#37/#40 (this pass) |

## Round-5 fix-map (v3.3 — mechanism-level convergence)

Round-5 (2026-07-22) reviewed v3.2 and returned REVISIONS REQUIRED (4 blockers + 8 majors + 3 minors). The
central finding: the core lock's *reconciling principle* (Advisor floor ≡ #10 activation) was **asserted but
not delivered** — the Advisor floor was still hand-tuned with Tier gates that contradict #10's content-based
activation. This round fixes the **mechanisms**, not the prose. #10-side changes:

| Round-5 finding | Disposition in v3.3 |
|---|---|
| **B3** result-review deferred but still blocking in core | Removed the result-review gate + `EVAL-RESULT` from core; result ingestion/envelope deferred to #42; core gates on **spec existence + approval** only. LLD §6.12/§7.2/§7.3 |
| **B3** e2e baseline needs multi-owner (deferred) | Core generates single-owner (per-agent) baselines only; the **e2e spec is hand-authored** (multi-owner generation → #42). LLD §7.4 |
| **M2** saga `parallel` in core but parallel-compensation deferred | Removed `parallel` from core (`order: sequential` only, → #42). LLD §4.2 |
| **M2** compensation-gap "flow" undefined | Defined deterministically: a declared `segment.path`, or a coordinator chain; else no flow/no advisory. LLD §4.2, tests COMP-GAP-SEG/COORD/NONE |
| **M3** observability gate toothless-or-disproportionate | Made real + tier-scaled: convention-**required** trace attributes, a **`ResolvableRef`** console `ref`, and a **tier rule** (Tier≤1 = report/existing surface; Tier≥2 = console). LLD §4.3/§6.17/§6.17.1 |
| **M4** core defers Musts vs unchanged 2.2.0 DoD | **Re-scoped**: deferred parts downgraded Must→next-release (#42); core **closes 2.2.0**. Requirements §4.1 |
| **M5** `depends_on` still auto-written to source manifest | `depends_on` is a **projection** when `interactions` present (legacy auto only when absent); added MIXED + DEP-DOUBLE fixtures. LLD §2.4 |
| **M8** delegated authority | CR-13/14 core is an **explicit release limitation**, not full satisfaction. Requirements §4.1 |

## Round-4 fix-map (v3.2 — core scope lock)

Round-4 (2026-07-22) reviewed v3.1 **against the original objectives** and returned REVISIONS REQUIRED (4
blockers + 9 majors + 3 minors). The central finding: the design had **over-scoped** — most acutely, the
round-3 broadening of eval coverage to *every* component/edge reintroduced the over-governance the Advisor
exists to prevent (O6). Rather than patch 13 findings into a still-larger design, the accepted response is
to **lock a minimal sound core and defer the heavy/contested parts** — see
[`../agentic-core-scope.md`](../agentic-core-scope.md) for the full core/deferred boundary and the
per-finding disposition. The #10 changes in v3.2:

| Round-4 finding | Disposition in v3.2 (core) |
|---|---|
| **M1 / O6** — universal eval coverage over every component/edge is over-governance; no result contract | **Trim:** eval coverage is scoped to **agent targets + one e2e** (independent per-agent eval, CR-8/CR-16). Universal deterministic coverage + result-review envelope + multi-owner baseline → **deferred follow-on**. LLD §6.12/§7; ADR-12 |
| **B4** — saga↔segment identity + requiredness underspecified; ADR-11 stale | **Defer** the required-when compensation model; core validates **declared** sagas only and adds a **`check_compensation_gap` advisory** (warn, don't enforce, when ≥2 side-effecting steps have no saga). **ADR-11 rewritten** to match. LLD §6.14 |
| **B1 (core part)** — agent→agent boundary leg gap | Confirm the determinism boundary fires on **agent→agent** legs, not only det/external seams. LLD §6.3 |
| **M2** — authority checks the grantee, not the delegation | **Defer** delegated per-interaction authority; core keeps `allowed_callers` + `authority ⊆ consumer`, **honestly labelled limited**. LLD §6.3/§6.4 |
| **M5** — CR-6 sync timeout/retry disposition is false ("captured on legs") | **Narrow CR-6 honestly:** sync reliability = facade `error_modes` + product runtime; drop the design-time sync-declaration claim. Deferred. Requirements CR-6; HLD §3 |
| **M6** — projection model half-reconciled | Specify **ownership per field** (interactions authoritative; matrix/`events_*`/`depends_on` generated-view-only) + a **mixed legacy/new fixture**. LLD §2.4 |
| **m1** — version metadata inconsistent; ADR-11 superseded text | Header/version sweep; mark superseded ADR passages. |

Deferred #10 items are tracked in **[#42](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/42)**
(universal eval + result envelope + multi-owner baseline; saga distributed-compensation; delegated
authority; design-time sync reliability). The Advisor's matching v3.2 changes (obligation-first floor,
non-circular routing, terminal+Mermaid map, scenario/decision schema) are in
[`../agentic-design-advisor/`](../agentic-design-advisor/).

**Post-lock hard directive (2026-07-22) — observability + PM eval-console is now a FLOOR GATE.** Separate
from the round-4 trims, the user directed that *a PM eval console + live traces is a hard requirement*
(model: **HITL enforces, the product builds**). This **elevates CR-9/CR-16 to the floor** and **un-defers
CR-9's design-time portion from #15**: a new top-level **`observability`** declaration (LLD §4.3) is
**required on any agentic system** and enforced by a **blocking `check_observability` floor gate** (LLD
§6.17; HLD §10). HITL ships the declaration + validator + gate + static posture view; the **product** builds
the running console + trace backend (#21 reference), so **O1 governs-not-runtime holds**. #15 keeps only the
runtime posture backend. The Advisor's `agentic-observability` becomes a **floor** command authoring that
field (presence non-negotiable, depth tier-scaled — the proportionate reading).

## Round-3 fix-map (v3.1 — superseded in part by the core lock above)

Round-3 reviewed the v3 docs and returned REVISIONS REQUIRED with 4 blockers (converging: 6→6→4). All
addressed in **v3.1**, informed by the right-sizing reframe (the Advisor, FR-28):

| Round-3 finding | Disposition in v3.1 |
|---|---|
| **B1** — the generator writes derived `interaction_matrix`/`events_*` *back into the manifest*, colliding with `edge_double_authored` (generation isn't idempotent) | Projections are emitted to a **separate generated-view file** (`agentic-posture/projections.*`), never into the source manifest; `edge_double_authored` fires only on **hand-authored** coexistence; projected `description`/`shape` specified. LLD §2.4/§9; test VIEW-IDEMPOTENT |
| **B2** — `long_running:true` doesn't require `resumable`/`idempotent_resume` (CR-17 bypassable) | `check_lifecycle` now **requires both** for a long-running component. LLD §6.10; test LIFE-RESUME |
| **B3** — eval coverage targets only agents/agent-edges (CR-8 says *every* component/edge); no result-review gate | Targets = **every component ∪ every interaction ∪ segments**; deterministic targets satisfied by a `kind: contract_test` spec; added a **`result_review` gate** (reviewer decision on the ingested result, distinct from spec `approval`). LLD §6.12/§7.1-7.3; tests EVAL-DET-OK/EVAL-RESULT |
| **B4** — `check_saga` fires on wholly-deterministic sync flows → forces `policies.yaml` (refutes additive-only) and over-extends CR-12 | **Trimmed:** a saga is required only for a **declared `transactional` segment** with agent/async side effects; a synchronous deterministic flow is **exempt** and stays registry-free. The Advisor elicits whether distributed compensation is needed; #10 validates declared sagas. This is the over-engineering trim the whole session pointed at. LLD §4.2/§6.14; HLD §5; test SAGA-SYNC-OK |

The v3.1 disposition supersedes the v2 saga-activation fix (which had over-corrected an internal-review
false-negative by firing on any side-effecting flow — round-3 caught it).

> **Superseded by the round-4 core scope lock (above):** the v3.1 **B3** row (eval coverage → *every*
> component ∪ interaction ∪ segment) over-governed and is replaced by **agents + e2e** (M1/O6); the v3.1
> **B4** row (a saga *required* for a `transactional` segment) is replaced by **declared-saga validation +
> a compensation-gap advisory** (required-when deferred). The rows are kept for history.

## Round-2 fix-map (v3)

Round-2 verdict: REVISIONS REQUIRED. Six blockers, twelve majors, four minors. Disposition in v3:

| Round-2 finding | Disposition in v3 |
|---|---|
| **B1** — `interaction_matrix` map can't hold parallel edges; `id` inside a pair-keyed value is inert; SEP-PAIR unconstructable | **New additive top-level `interactions` list** keyed by `id`; parallel edges = two elements; the map/`depends_on`/`events_*` become **derived projections** (regenerate-and-diff). ADR-2/D2, ADR-10/D10 rewritten; LLD §2/§2.4; SEP-PAIR now constructable (test) |
| **B2** — cost/authority only on response leg; authority compared to callee not the stochastic consumer; agent→agent fan-out unbounded | **Uniform `Leg` struct** (`validation` + `cost_bound` + `authority_bound`) on request/response/event; validator derives (source, consumer) **per leg**; cost+authority required whenever the **consumer** is stochastic, `authority_bound ⊆ that consumer's` grant. ADR-7/D7 rewritten; LLD §2.2/§6.3 |
| **B3** — privilege union not closed: memory unjoined, invoke bypasses ceilings, resource-less scope invalid, tier default undefined, CR-15 tools vanished | **Union closed over tools/memory/non-tool caps** via `uses`; **memory joined** through memory-class uses (§3.1); **invoke moved to authorization** (not the identity grant); resource-less ⇒ `op:*`; **wildcard ceilings**; **tier is a validator input**; **CR-15 fold-in** (`class: tool` + `runtime_ref` + tool matrix). ADR-9/D9 rewritten; LLD §3.1/§6.2/§6.x |
| **B4** — eval validator reads `segments`/`evals` the schema never defines; no index/waiver/approval; adapter unimplementable | **Add `segments` (top-level), `evals` on interactions**; **eval index + waiver file + per-spec approval block**; **fully wired adapter** (argv/cwd/timeout/binding/result-schema/exit-codes, operator-confirmed); **baseline generator spec**. ADR-12/D12 rewritten; LLD §7 |
| **B5** — global activation gate forces registries onto deterministic manifests using new markers | **Per-check activation predicates** (LLD §6.0); each registry loads only when its check activates; deterministic+typed-`interactions` needs **no** new registry. **ADR-13/D13 added**; test A3 |
| **B6** — "every field value-checked" overstated; no policy/shared-store registry; requiredness rules missing | **`policies.yaml` + `stores.yaml` registries**; **requiredness-by-kind table** (§4.1); value blockers for lifecycle/memory/async/authorization; **unknown-field rule**. LLD §5/§6 |
| **M1** authorization names domains not principals; no JIT default | `allowed_callers` must be domains with an `identity.principal`; `credential_mode` defaults `jit`, `static`/`none` needs justification; `audience`. LLD §2.3/§6.4 |
| **M2** event reconciliation has no stable join | Event interactions are authoritative; `events_emitted`/`events_consumed` are **projections keyed by interaction id**; hand-authored lists must equal the projection (`event_projection_mismatch`). LLD §2.4/§6.6 |
| **M3** saga ownership/id/order/required-when undefined | **Sagas hoisted to a top-level id-keyed list** with coordinator, forward `order`, steps→interaction ids; required when a flow has ≥2 side-effecting interactions; compensation reverse-order + idempotent. ADR-11/D11; LLD §4.2/§6.7 |
| **M4** async combos underdesigned | `async_task` requires `async`; `retry` forbidden with `at_most_once`; `at_least_once` requires DLQ unless justified; `idempotency_key` grammar. LLD §2.1/§6.7 |
| **M5** memory provenance/staleness claimed, absent | Add `provenance`/`staleness`/`high_stakes` on `MemoryAccess`; long_term must be `durable`; reconcile to `uses`. HLD §9; LLD §3.1/§6.11 |
| **M6** lifecycle doesn't establish durable pause/resume safety | Require `side_effect_key` (resumable+side-effecting), `human_gate_pause:true` with a human gate, `cancellation≠none`, `checkpoint_store` resolving to a durable store. LLD §3.2/§6.10 |
| **M7** deep-agent lost capability descriptions; allows ephemeral memory | Subagents are domain refs whose capability description **is** the referenced domain's `purpose`+facades; long_term must be `durable` + `filesystem`/`semantic` retrieval (virtual-fs). LLD §3.3/§6.9 |
| **M8** CR-1/2/11/19 remain design-track prose; acceptance overclaims | CR-2 classification-completeness + CR-11 `orchestration.justification` are now checks; **CR-1/CR-19 relocated to the Agentic Design Advisor (FR-28)** — they are elicitation, not enforcement; **acceptance criterion 2 is rescoped** to name validators *or* generators *or* workflow artifacts, not "every CR has a validator." HLD §13 |
| **M9** CR-15 silently weakened | Documented **fold-in** in CR-15 text + ADR-9: tools are `class: tool` capabilities with `runtime_ref`; tool matrix is a projection. Requirements CR-15; LLD §5 |
| **M10** CR-6 routing/loop/fan-out/sync reliability incomplete | Fan-out covered by consumer-stochastic cost bound (§6.3); sync `timeout`/`retry` on legs; `cycle_bound` declared, **product enforces at runtime** (documented boundary); segment adjacency checked. HLD §3/§5; LLD §6.5 |
| **M11** CR-5 overclaims Agent Card / hook enforcement | Explicit mapping: facade governs capability/signature; endpoint/security/version are product-runtime config; the design-time hook does a **static contract check** (declared-interaction ↔ facade), stated honestly. HLD §2; LLD §6.4 |
| **M12** CR-9 deferred but acceptance claims all CRs | *(v3 disposition, later superseded)* Acceptance gate scoped to exclude CR-9; CR-9 depended on #15. **Superseded by the 2026-07-22 hard directive** — CR-9's design declaration + `check_observability` floor gate are now **in this package** (see the post-lock note above); only its runtime backend stays #15. HLD §10/§13 |
| **m1** first-dot facade vs unrestricted domain names | `domain_name` grammar forbids dots; first-dot split is unambiguous. LLD §0 |
| **m2** `facade` conflates two reference kinds | Distinct `facade_ref` (`domain.facade`) vs `event_ref` (`producer:event`) grammars. LLD §0 |
| **m3** "all optional" vs required id/kind | Requiredness-by-kind table: once a `kind` is declared, its fields are required. LLD §4.1 |
| **m4** requirements metadata stale | Header refreshed (HLD v3 / ADR-1..13 accepted / LLD v3). Requirements header |

## Round-1 fix-map (superseded, kept for history)

Round 1 produced the v2 docs (interaction-matrix extension, per-leg legs, scoped-capability, eval
coverage+adapter, activation rule). Round 2 found several of those fixes were asserted rather than
delivered — most importantly that extending the pair-keyed map could not deliver parallel edges (B1). The
v3 disposition above supersedes the round-1 dispositions wherever they conflict; the round-1 report
remains on file.

## Sequencing

1. Round-1 response → v2 docs (done).
2. Round-2 response → v3 docs (done).
3. Round-3 response → v3.1 docs (done).
4. Round-4 response → **v3.2 core lock**: trim eval to agent+e2e, defer saga model + add compensation-gap
   advisory, narrow CR-6, confirm agent→agent boundary, reconcile projections + ADR-11 + metadata; move
   deferred items to a follow-on issue (this pass).
5. **Re-run the cold Codex prompt (round 5) on the locked core only** → converge.

> **Note on the round-3 B3 fix (universal eval coverage):** that broadening is **superseded** by the v3.2
> core lock (M1/O6) — it over-corrected into over-governance. Core coverage = agent targets + e2e;
> universal coverage is deferred.

**Implementation does not begin** until the Codex re-review is clean (APPROVE or accepted minors only).
