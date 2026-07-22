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

## Round-3 fix-map (v3.1 — the current work)

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
| **M12** CR-9 deferred but acceptance claims all CRs | Acceptance gate **explicitly scoped to CR-1..CR-8, CR-10..CR-20**; CR-9 depends on #15. HLD §10/§13 |
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
2. Round-2 response (this fix-map) → **v3 docs**: HLD, LLD, ADRs (done in this pass).
3. Internal architect-reviewer pass with an explicit instruction to check every validator field against
   the real schema types and every test fixture for representability (the discipline that missed B1).
4. **Re-run the same cold Codex prompt (round 3)** → converge.

**Implementation does not begin** until the Codex re-review is clean (APPROVE or accepted minors only).
