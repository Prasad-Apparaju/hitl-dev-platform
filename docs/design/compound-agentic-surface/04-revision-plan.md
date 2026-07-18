# Compound Agentic System Surface: v2 Revision Plan (response to Codex design review)

> Independent Codex design review (2026-07-18, cold/neutral prompt) returned **REVISIONS REQUIRED** with
> 6 blockers + 14 majors — several structural and missed by 5 internal architect rounds. Report:
> `hitl-internal/docs/validation-reports/2026-07-18-compound-agentic-design-codex-review.md`. This is
> the accepted response: the three design forks (decided by judgment), the unifying principle, and a
> fix-map from each finding to where it lands. The HLD ([`01-design.md`](01-design.md)), ADRs
> ([`02-adrs.md`](02-adrs.md)), and LLD ([`03-lld.md`](03-lld.md)) are revised **per this plan**, then
> the same cold Codex prompt is re-run. EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10).

## Unifying principle

**HITL validates declarations, coverage, and consistency — not runtime behavior.** Every over-reach in
v1 claimed to derive *runtime truth* (necessary privilege, actual eval results, actual tool use) that
belongs to the product or crosses the governs-not-runtime line (ADR-5). Each fix narrows the claim to
what a design-time framework can honestly prove and pushes runtime truth to the product plus an optional
drift-check. Framework-agnostic (ADR-4) and governs-not-runtime (ADR-5) were **upheld** by the review;
the manifest-as-graph skeleton stands. The rework is in the edge model, the privilege claim, the eval
design, and validator depth.

## Design forks (decided)

**F2 — Interaction model (edge layer).** Extend the manifest's **existing** top-level
`interaction_matrix` (directed, human-authored, keyed `from -> to`, carries `entity_crossing`) as the
**single authoritative edge model**. Delete the v1 `calls` field (it duplicated `interaction_matrix` —
Codex M1). Each interaction gains: a stable `id` (distinguishes multiple interactions between one pair),
`kind` (`sync_call | async_task | event`), `facade` (ref for call/task kinds), **separate request/response
trust legs** (`input_validation`, `output_validation`), an `authorization` block (who-may-invoke), and
the `async` reliability block. `depends_on` becomes an auto-derived projection. Cycle/dup logic keys off
`id`, not domain pairs. Closes B1, B2, B5, M1, M2, most of M7.

**F1 — Privilege.** Narrow CR-14 from "necessary-and-sufficient" to **"declared-capability consistency +
least-privilege review."** Validator proves every grant traces to a declared source and every declared
use has a grant; necessity-vs-actual-code is human review + an **optional runtime drift-check** (declared
vs granted-at-runtime, read-only). Complete the source model: add a `capabilities` block (non-tool:
KMS/model-endpoint/delegation/ambient) and **edge-invocation scopes** (`invoke:<domain>` sourced from
outbound interactions). needed = ⋃(tool ∪ memory ∪ capability ∪ edge-invoke scopes). Closes B4.

**F3 — Evals.** HITL governs **coverage + an adapter contract**, ships no runner. Add: the eval spec, a
**coverage validator** (every component/interaction/declared segment has an eval spec or a structured
waiver), a **waiver schema** (owner/reason/tier/expiry, like platform-readiness), and a **runner-adapter
contract** (`eval_adapter: {command, inputs, result_schema}`) HITL invokes into the product's runner.
"PM runs evals" ⇒ "PM invokes the declared adapter; HITL records coverage + reviewer approval." Closes B3,
resolves the CR-16 boundary tension.

## Fix-map (Codex finding → disposition)

| Finding | Disposition |
|---|---|
| **B1** boundary uses call direction, not dataflow | F2: per-interaction request/response trust legs; `output_validation` on the response leg; applies to every data-carrying interaction incl. events |
| **B2** who-may-invoke / facade enforcement no model | F2: `authorization` block per interaction (allowed callers, credential mode, JIT); reference-integrity validator (`facade`/`to` resolves); boundary-hook change added to the LLD change list |
| **B3** evals are prose | F3: coverage validator + waiver schema + runner-adapter contract + result/reviewer schemas + tests |
| **B4** "necessary-and-sufficient" false | F1: narrow claim; add `capabilities` + edge-invoke sources; optional drift-check |
| **B5** async can't do reliable one-way; weak validators | F2: `kind: event` + reliability makes durable one-way events representable; drop unqualified `exactly_once` (broker boundary); per-step saga/compensation; consumer-idempotence declaration; value-check retry/timeout/dlq |
| **B6** validators check presence; A1/Z1 additivity contradiction; schema dialect | LLD: value/reference/range/nonempty/unknown-field checks; **activation rule** — agentic checks + registry requirement fire only when an agentic marker (`kind`/interaction `kind`/`orchestration`) is present, so legacy manifests exit 0; pin the executable validation pipeline + exact dialect |
| **M1** `interaction_matrix` duplicated/unreconciled | F2 (authoritative model) + rewrite ADR-2 decision text (not just a refinement note) |
| **M2** topology is adjacency, not routing | F2: entrypoints, route/segment ids, fan-out/join, response/callback routes on the interaction model |
| **M3** lifecycle accepts unsafe values | LLD: value-checks (`long_running` ⇒ `checkpoint≠none`, `resumable=true`, `idempotent_resume=true`, `timeout>0`, `cancellation`, `human_gate_pause`); declare checkpoint store/format + resume cursor + side-effect key |
| **M4** memory governance/shared-store | LLD: add owner/staleness/durability/retrieval/write-provenance/high-stakes-guardrail; `pii` required (may be explicit `none` with justification); reconcile `store` vs `shared_store` via a shared-store registry with one owner |
| **M5** deep-agent syntactic | LLD: nonempty/true value-checks; subagents are references to declared domains; reject `deep_agent` on non-agent kinds |
| **M6** CR-2/11/19 human gate + catalog unspecified | Add `pm-design-feature`/`AGENTS.md` + capability-catalog schema + decision-record schema (rationale + rejected) to the LLD change list; TA-gate contract |
| **M7** CR-6 gaps | F2 covers fan-out bounds + interaction-level timeout/retry; add transitive-nondeterminism check across response/event legs; require positive `cycle_bound` |
| **M8** CR-9 registry semantics | Keep deferred to #15 but state it explicitly; the token-cost registry needs a product-agent extension (not the dev-change registry) — scope note in #15 |
| **M9** additive not end-to-end | LLD activation rule (B6) + enumerate the full D8 template/schema reconciliation (facade shape + `description`/`purpose` + mutations placement) |
| **M10** approved-tool "undeclared" semantics | LLD: distinguish unknown-registry-key vs declared-but-unused-in-impl (drift, optional) vs runtime-allow-list evidence; risk gets a policy hook |
| **M11** machine-readable posture missing | LLD: generator emits machine-readable (JSON/YAML) + rendered; deterministic ordering, schema version, drift-comparison |
| **M12** unchecked policy strings | LLD: typed policy references + existence/nonempty/range validators for cost/output_validation/compensation/planner/gates/guardrails/authority |
| **M13** canonicalization example is wrong | LLD: fix — canonicalize per token around the colon (not whole-string), single-colon + nonempty-part grammar, forbid traversal |
| **M14** test matrix gaps | LLD: add response-direction boundary, boundary events/deps, dangling `to`, legacy-no-registry, false/none controls, reliable one-way event, `exactly_once`, separate call+event same pair, event-pair mismatch, `interaction_matrix` conflict, invalid scope, eval coverage/waiver, machine-readable view, shared-store disagreement, nonpositive numerics |
| **m1–m4** dotted facade parsing, orchestration refs, view guarantees, LLD/ADR status | LLD: first-dot parsing + canonical ids; validate `coordinator` names an agent fitting the pattern; specify source-of-truth + CI regenerate-and-diff; add an explicit approval point + real ADRs for the new edge/privilege/eval decisions |

## Sequencing

1. **This plan + narrow CR-14** (done).
2. **HLD v2** — the interaction model (F2), privilege claim (F1), eval coverage/adapter (F3), request/response trust, authorization, ADR-2 rewrite.
3. **LLD v2** — field defs on `interaction_matrix`; value/reference validators; activation rule (A1/Z1); executable dialect; expanded test matrix.
4. **ADRs** — rewrite ADR-2 decision; add ADRs for the interaction-id model, the narrowed privilege claim, and the eval-adapter boundary.
5. **Re-run the same cold Codex prompt** → converge.

Not-yet-fixed until the above lands; **implementation does not begin** until Codex re-review is clean.
