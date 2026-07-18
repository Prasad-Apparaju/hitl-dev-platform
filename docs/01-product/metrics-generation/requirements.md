# Metrics Generation: Requirements

> **What** the capability must do, for **EPIC [#22](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/22)**
> (generate framework-effectiveness metrics from HITL's durable artifacts). Status: **draft,
> pending review**. Ships as **2.3.0** on the 2.x line (1.x is feature-frozen). Sub-issues:
> [#23–#31](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/22).
>
> **Requirements (what) vs design (how).** This is the requirements layer: the product one-liner is
> **[FR-27](../prd.md)** in the PRD; this doc is its detailed requirements analysis (problem +
> `MR-n`). The **how** — derivation mechanism, register schema, report generator — lives in the
> design package at
> [`docs/design/metrics-generation/`](../../design/metrics-generation/) (`01-design.md` HLD + ADRs,
> to follow). §7 traces every `MR-n` to a sub-issue.

## 1. Problem

People ask for evidence that HITL works — escaped defects, review effort, lead time, cost, whether
coherence holds. HITL's own docs concede the gap: `docs/playbook/evidence.md` labels most claims
"not measured"; `common-pitfalls.md` says "without measurement, the strongest claims remain
hypotheses"; PRD §8's KPI table has cells reading "Not yet measured."

Yet HITL already writes the raw material as a byproduct of normal operation:

- **Change files** (`.hitl/current-change.yaml`): tier, workflow, steps, status transitions, timestamps.
- **Registries**: test, **incident**, **token-cost** (agentic observability), platform-readiness.
- **Git / PR history**: commits, reviews, merge times.
- **Gate + waiver records**: which gates blocked, waivers with owner/reason/revisit.

The gap is not the concept — it is **automated derivation**. The **token-cost registry** already
proves the pattern: a per-change metric, written at PR time and reviewed at the ROI steps. This
capability generalizes that: derive metrics from the artifacts HITL already emits — the same
"derive, don't hand-maintain" move as the command-map, catalog, readiness register, and posture
matrices.

### Why this is HITL's lane, and where the boundary is

Most AI-coding setups cannot produce effectiveness metrics because they never wrote the substrate
down. HITL did — so it is unusually well-positioned to turn its own liability (the decision-maker
review's "all assurance, no evidence") into a differentiator.

**HITL governs the build; it is not a runtime.** This capability **emits** a machine-readable
metrics register + a rendered **local** report. It does **not** ship a live dashboard, a time-series
database, or a BI product, and it does **not** phone home. A live or cross-team dashboard is the
customer's tool (Grafana/Looker/Metabase) or the **paid governance layer already fenced in PRD §9**;
this capability produces the data + static report that feed those.

## 2. Metric families

| Family | Metrics | Primary source artifacts |
|---|---|---|
| **DORA** | deployment frequency, lead time for change, change-failure rate, MTTR | change files + git/PR + incident registry + deploy records |
| **Governance** | gate pass/block rate, waiver count + aging, review rounds/change, traceability-at-merge %, tier distribution, gate friction | change files + gate/waiver records + issue timestamps |
| **Cost** | token cost per change/tier, actual vs estimate | token-cost registry |
| **Quality / outcome** | defect escape rate, rework rate, incidents per domain | incident registry ↔ changes |
| **Coherence-over-time** | manifest-drift rate, convention-violation rate, doc staleness | drift checker + registries, sampled over time |
| **Onboarding** | onboarding time to first delivered change | onboarding step timestamps |

## 3. Goals

1. **Derive, don't collect.** Metrics come out of artifacts HITL already writes; no new manual data
   entry for anything derivable.
2. **Emit, don't host.** Produce a register + a static report; leave the live dashboard to the
   customer's tools / the paid layer.
3. **Be honest by construction.** Every metric labeled by evidence class; effectiveness measured as
   before/after against a captured baseline; outputs framed as evidence, not proof.
4. **Answer the questions people actually ask.** Fill PRD §8's unmeasured cells and the
   decision-maker review's outcome questions.
5. **Stay local and private.** Derive from local repo artifacts; nothing leaves the repo.

## 4. Requirements

Requirement IDs are `MR-<n>` (Metrics Requirement). Each maps to sub-issues in §7.

| ID | Requirement | Priority |
|---|---|---|
| **MR-1** | A metrics-generation capability **derives** metrics from HITL's durable artifacts (change files, test/incident/token-cost/readiness registries, git/PR history, gate + waiver records). No new manual data entry for a derivable metric. | Must |
| **MR-2** | Output is a **machine-readable metrics register** (like the token-cost/readiness registers) **plus a rendered local report** (static, like the generated catalog page). No live dashboard, no time-series DB, no BI product ships. | Must |
| **MR-3** | A **metric catalog** defines each metric once: precise definition, source artifact(s), formula, and evidence class — so "change-failure rate" (and every metric) means exactly one thing. | Must |
| **MR-4** | **Evidence-taxonomy labeling.** Every metric carries its evidence class — **derived-from-artifacts** (objective) / **self-reported** (a human entered it) / **estimated/hypothesized** — reusing the `docs/playbook/evidence.md` taxonomy. No false precision; a self-reported number is never rendered as measured. | Must |
| **MR-5** | **DORA metrics** derived: deployment frequency, lead time for change, change-failure rate, MTTR. | Must |
| **MR-6** | **Governance metrics** derived: gate pass/block rate, waiver count + aging, review rounds per change, traceability-at-merge %, tier distribution, gate friction (time from gate-request to approval). Fills PRD §8's "Not yet measured" cells. | Must |
| **MR-7** | **Cost metrics** derived from the token-cost registry: token cost per change/tier, actual vs estimate. | Should |
| **MR-8** | **Quality/outcome metrics** derived: defect escape rate, rework rate, incidents per domain (incident registry linked back to changes). | Must |
| **MR-9** | **Coherence-over-time metrics** — the signature "is change 100 as grounded as change 1?": manifest-drift rate, convention-violation rate, doc staleness, sampled over time. | Should |
| **MR-10** | **Baseline capture at onboarding.** The pre-HITL baseline is captured at onboarding (from existing git/incident history where derivable, else self-reported and labeled MR-4), so effectiveness is reported as **before/after**, not just current-state. | Must |
| **MR-11** | **Segmentation + honest framing.** Metrics can be segmented by tier / cohort / domain / time to reduce confounding; the report frames outputs as **evidence, not proof** — process telemetry cannot cleanly isolate HITL's causal effect from confounders (team discipline, work mix). | Must |
| **MR-12** | A **PM/leadership-runnable skill** derives the register and renders the report on demand (and optionally on a schedule). | Must |
| **MR-13** | **Local and private.** Derivation reads local repo artifacts only; nothing is transmitted off-repo; the report is a local artifact. No telemetry phone-home. | Must |

## 5. Constraints

- **Additive only**: new register + report + skill; the metrics register is a new derived artifact,
  not a change to existing schemas. Reuse the token-cost/readiness-register + generated-view
  precedents.
- **Reuse existing artifacts**: change files, the four registries, git/PR, gate/waiver records — do
  not require new instrumentation the process does not already produce.
- **Governs, does not run.** No dashboard, DB, BI, or phone-home. Emit data + static report.
- **Tier-proportionate.** A small project gets current-state metrics with light ceremony; effectiveness
  before/after needs the onboarding baseline (MR-10) but is not forced on a Tier-0 pilot.

## 6. Non-goals

- A **live or cross-team dashboard**, a time-series database, or a BI/analytics product — the
  customer's tools (Grafana/Looker/Metabase) or the paid governance layer (PRD §9).
- A hosted **benchmark / telemetry service** that aggregates metrics across customers — explicitly not
  built; nothing leaves the repo.
- **Manufacturing measured-looking numbers** from self-reported or estimated inputs — barred by MR-4.
- **Causal proof** of HITL's effect — the capability produces evidence and honest caveats, not proof.

## 7. Traceability

Requirements → sub-issues → deliverables. Epic
[#22](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/22); PRD **FR-27**.

| Sub-issue | Deliverable | Requirements |
|---|---|---|
| [#23](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/23) | HLD + ADR(s) | MR-1, MR-2, MR-4, MR-13 |
| [#24](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/24) | Metric catalog + register template | MR-3, MR-4 |
| [#25](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/25) | Derive-metrics skill + report generator | MR-1, MR-2, MR-12, MR-13 |
| [#26](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/26) | Derivations: DORA/governance/cost/quality/coherence | MR-5, MR-6, MR-7, MR-8, MR-9 |
| [#27](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/27) | Baseline capture at onboarding | MR-10, MR-11 |
| [#28](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/28) | User docs + playbook + worked example | MR-1..MR-13 (documentation) |
| [#29](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/29) | Website/portal evidence update + screenshots | MR-1..MR-13 (portal) |
| [#30](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/30) | Codex two-stage validation + guide/prompt | Definition of done |
| [#31](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/31) | Release 2.3.0 (blocked by #30) | Version |

## 8. Effort scope (definition of done for the epic)

- **Design docs**: this requirements doc, `01-design.md` (HLD), ADR(s).
- **Catalog + register**: the metric catalog (definitions + evidence class + sources) and the
  metrics-register template.
- **Skill + generator**: the derive-metrics skill and the rendered-report generator; the derivations
  for all six families, each with a regression suite under `ci/`.
- **Baseline capture** wired into the three onboarding entry points.
- **User docs & playbook**: update `evidence.md`, `common-pitfalls.md`, and PRD §8; add a worked
  example report; **release notes** (CHANGELOG 2.3.0); **website/portal** evidence story;
  **screenshots** where appropriate.
- **Codex validation**: `docs/validation-guide.md` updated + a per-feature prompt; a two-stage report
  filed to `hitl-internal/docs/validation-reports/`.
- **Version + distribution**: bump to **2.3.0**, build the plugin, publish on `release/2.x`.

## 9. Version

**2.3.0** — additive minor, **2.x line only**, next after compound-agentic 2.2.0 (independent
feature; ships in either order). 1.x is feature-frozen and does not receive this.

## 10. Codex validation (two stages, gated)

Mirrors the 2.0 / platform-bootstrap / compound-agentic campaigns. Release (#31) is blocked by
Validation (#30). **Stage 1 — source**: `derive.py verify`, `pytest ci/`, skill-lint, breadcrumb
matrix, doc checks, plus the new metric-derivation suites. **Stage 2 — built plugin**: run
`scripts/build.sh`, re-run behavior tests against the built tree, source↔plugin parity,
`claude plugin validate`. Report files to `hitl-internal/docs/validation-reports/`.

## 11. Success criteria

1. Running the derive-metrics skill on a real HITL repo produces a metrics register + a rendered
   report with every metric evidence-classed.
2. PRD §8's "Not yet measured" cells (traceability-at-merge, gate friction) are now derived, not blank.
3. A project that captured an onboarding baseline can show a before/after delta for at least one DORA
   or governance metric, clearly labeled evidence not proof.
4. No metric derived from a self-reported input is rendered as measured; nothing leaves the repo.
5. Both Codex stages pass (or findings remediated) before the marketplace serves 2.3.0.

## 12. References

- HITL's own evidence taxonomy and "what we want to measure next": `docs/playbook/evidence.md`.
- The shipped derivation precedent: the token-cost registry (`ai/shared/templates/token-cost-registry-template.yaml`).
- DORA metrics (deployment frequency, lead time for change, change-failure rate, MTTR): the industry-standard delivery-effectiveness set.
- The decision-maker website review (private `hitl-internal`) — the outcome questions this capability answers.
