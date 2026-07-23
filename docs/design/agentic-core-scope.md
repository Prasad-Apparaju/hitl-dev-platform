# Agentic surface — Core Scope Lock (round-4 response)

> Response to the round-4 Codex review (REVISIONS REQUIRED). Decision: **lock a minimal *sound* core for
> both #10 (compound surface) and FR-28 (Advisor), and defer the heavy/contested/incomplete parts to
> explicitly-tracked follow-ons.** The review confirmed the foundations are sound; the failures are in
> over-scope, an unreconciled Advisor↔#10 proportionality model, and incomplete seams. This shrinks the
> surface toward *proportionate* (the objective the review found violated) rather than patching 13 findings
> into an ever-larger design. Governs #10 (`04-revision-plan.md`) and FR-28 (`agentic-design-advisor/`).

## The clean boundary (2026-07-23 re-scope — supersedes the "reconciling principle")

Rounds 4–7 tried to make **the Advisor's floor equal #10's activation** so the Advisor could *author* a
manifest #10 would accept. Round 8 showed that seam can only be validated by the real validator, and the
product owner named the deeper problem: **auto-authoring the manifest put the PM front door into
design/implementation — the exact line HITL must hold.** So the reconciling principle is dropped along with
the auto-authoring it existed to serve. The boundary now:

- **Advisor (PM lane):** one intake that elicits, **recommends** a right-sized floor (Tier + risk expert
  judgment — the controls that shouldn't be skipped), records decisions, and **hands off** (a decision
  record + a neutral `agentic-design-handoff.yaml` — `proposed_kind`s + recommendation IDs + target-path
  hints, **not** a manifest). It authors **no** manifest field (not even `kind`) and predicts **nothing**
  about #10.
- **A human (design role):** authors the real manifest in the design phase.
- **#10 (the gate):** validates the human-authored manifest — unchanged, needs no Advisor input, ships
  independently.

There is nothing to reconcile because there are no two copies: the Advisor recommends, #10 enforces. The
observability + PM eval-console hard requirement (2026-07-22) survives cleanly — the Advisor **recommends**
it; #10's `check_observability` **enforces** it on the authored manifest.

"Deferred" (an optional rung not adopted) and "waived" (a recorded exception at #10's gate) remain distinct.

## Core v1 — #10 (compound surface)

**In:** `interactions` list edge model (parallel edges); per-leg determinism boundary **including
agent→agent** (round-4 B1/C3 fix); classification; scoped-capability privilege (declaration consistency +
ceilings, runtime-necessity honestly out of scope); interaction well-formedness (`check_topology`,
`check_references`, `check_authorization`); lifecycle safety; **independent per-agent eval coverage +
e2e** (every agent is independently evaluable — CR-8/CR-16), gated on **spec existence + approval** only —
the **adapter *execution* / result ingestion is deferred to #42** (round-9 M6: core ships the coverage gate
+ the adapter contract *shape*, not a runner that invokes evals); a **gated observability/tracing + PM
eval-console declaration** (`check_observability`, floor
— the 2026-07-22 hard directive); async reliability value-checks (idempotency/DLQ) **without saga-required
inference**; policy/store registries; per-check activation.

> **PM eval console + live traces — a HARD, GATED design obligation (user directive 2026-07-22).** The
> capability "a PM runs evals from an admin console and sees traces in observability" is **non-negotiable**.
> Under the chosen model — *HITL enforces, the product builds* — it is delivered as a **mandatory floor
> obligation**, not a deferral and not a runtime HITL ships:
> - **HITL core ships (design-time, gated):** the manifest **declaration** that every agentic system must
>   carry — (a) a cross-hop **observability/tracing plan** (what is traced at each hop, meeting the OTel
>   GenAI conventions) and (b) a **PM eval-console** capability (a PM-facing surface to run evals + review
>   results/traces, beyond the CLI adapter) — plus the **`check_observability` validator** and a **floor
>   gate**: a design that omits either **fails** (same teeth as the human gate / kill-switch). HITL also
>   generates the static posture view from the declaration.
> - **The product builds (runtime):** the actual admin UI + trace backend + eval execution. HITL ships **no**
>   dashboard/eval engine (O1 preserved) — the **companion product (#21)** delivers the runnable reference
>   the requirement is proven against; customers may run it or substitute LangSmith/Galileo/Arthur-class tools.
>
> **This elevates CR-9 (observability) and CR-16 (PM evals) to the core floor** — CR-9's design-time
> declaration + gate is **no longer deferred to #15** (only its runtime backend / rich posture dashboard
> stays product-side). See the requirements §4.1 and the Advisor floor below.

**Deferred (follow-on):** universal eval coverage over every deterministic component/edge + the
result-review envelope + multi-owner baseline generation (M1); the **saga distributed-compensation
required-when model** — segment linkage, overlap, parallel compensation, requiredness signal (B4); the
**delegated per-interaction authority** model (M2); design-time **sync timeout/retry** declarations — CR-6
narrowed to facade `error_modes` + product runtime for now (M5).

> **Saga — detect-and-warn instead of silence (user request).** Deferring the full compensation model must
> **not** mean the design silently misses flows that need it. The core adds a cheap **`check_compensation_gap`
> advisory** (warning, not a blocker): when the saga-needing *pattern* is present — ≥2 side-effecting
> (non-read-only) interactions into agents/async in one flow with no declared `saga` — HITL emits *"this flow
> looks like it needs distributed compensation, which is not supported in the core yet; handle rollback
> deliberately or declare a transactional segment."* This closes the B4 "silent omission" hole (the reason
> a fail-open deferral is dangerous) without shipping the enforcement model. The Advisor intake asks the
> matching question up front so the warning is rarely a surprise.

## Core v1 — FR-28 (Advisor)

**In (re-scoped 2026-07-23, v4.1 — elicit + recommend + record + hand off; no manifest authoring):** **one
intake command** (`hitl:agentic-intake`; surface selection is external — `agentic` gate → topology probe →
route) that produces a **right-sized recommendation report** (the per-concern lenses are report *sections*,
not 8 commands — round-9 M9); a **recommended floor** = the safety-relevant risk factors (any agent →
classify/boundary/privilege/observability/evals; irreversible → human gate; supervised+side-effects →
kill-switch), Tier/data/stakes/scale informing recommended *depth* — advice, not a gate, not derived from #10
activation; a **decision record** (recommendations + chosen/rejected + recorded **skips**) and a **neutral
`agentic-design-handoff.yaml`** (components + connections + `proposed_kind`s + recommendation IDs +
target-path hints — **not** a manifest, no `kind:` field, round-9 B2); the deploy recommendation
(record + human-carry); the **terminal + Mermaid** map.

**Removed (was in, now cut — it served auto-authoring, which crossed the PM-shouldn't-design line):** the
canonical-state **writer**, `floor ≡ activation` + the imported-activation apparatus, `OWNS_CHECKS`/
`OWNERSHIP-COMPLETE`/`AUTHOR-COMPLETE`, the command→manifest-field authoring, and the seam spike's authoring
claim. **#10 is unchanged and can ship first** — it validates a **human-authored** manifest and needs no
input from the Advisor.

**Deferred (follow-on):** the **rich HTML / live-artifact combined map mode** — terminal + Mermaid is the
core; HTML/live is an optional enhancement with a defined host API (M8); advanced/optional lenses beyond
the core floor.

## Round-4 findings disposition

| Finding | Disposition |
|---|---|
| **B1** seam incomplete | **Fix-in-core** the core writers (facade + authorization authoring, agent→agent boundary, agent-target eval); the universal-coverage part is **deferred** (M1) |
| **B2** routing circular | **Fix-in-core** — agentic answer → topology probe → branch (one selector) |
| **B3** floor silently drops | **Fix-in-core** — obligation-first floor + lint rejects relevance⊂floor |
| **B4** saga↔segment / requiredness | **Defer** the full model; core validates *declared* sagas for well-formedness + adds `check_compensation_gap` **advisory** (warn when the pattern is present, don't enforce); **update ADR-11** to match |
| **M1** universal eval + result contract | **Defer** universal coverage + result envelope + multi-owner baseline; core = agent-target + e2e |
| **M2** delegated authority | **Defer**; core keeps `allowed_callers` + `authority ⊆ consumer`, honestly limited |
| **M3** scenario/catalog schema | **Fix-in-core** — full scenario schema + one reconciled `consequence` schema |
| **M4** mutation/rerun semantics | **Fix-in-core** — canonical state + merge/confirm contract |
| **M5** CR-6 sync reliability | **Fix-in-core** — narrow CR-6 honestly; stop claiming "captured on legs"; defer design-time sync declarations |
| **M6** projection inconsistency | **Fix-in-core** — ownership per field + mixed legacy/new fixture |
| **M7** tracker bodies stale | **Fix** — update #12/#13/#14/#16 bodies + #38/#41 scope |
| **M8** map over-scoped | **Defer** rich/live mode; core = terminal + Mermaid |
| **M9** role testing vs coverage | **Fix-in-core** — roles attribute, never gate whether a lens exists |
| **m1** metadata/ADR drift | **Fix** — header/version sweep; mark superseded ADR text |
| **m2** ADV ordering | **Fix** — reorder ADV-14/15 |
| **m3** "waived" overloaded | **Fix** — `deferred` (rung) vs `waiver` (floor exception) |

## Follow-on issues (deferred backlog — opened)

- **[#42](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/42)** (child of #10): universal eval
  coverage + result envelope + multi-owner baseline (M1); saga distributed-compensation model (B4);
  delegated per-interaction authority (M2); design-time sync reliability (M5).
- **[#43](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/43)** (child of #35): rich HTML /
  live-artifact "chat + live map" map mode with a defined host API (M8).

## Sequencing

1. This scope lock (confirm the core boundary).
2. Apply the **fix-in-core** set to the #10 + Advisor docs; move the **deferred** items to follow-on issues
   + notes; reconcile ADR-11, metadata, and the issue bodies.
3. Re-run the cold Codex review on the current design (rounds 5→9 have run; the Advisor was re-scoped after
   round 8, and round 9 confirmed the re-scope is sound and now applied in v4.1).

Implementation begins only when the review is clean.
