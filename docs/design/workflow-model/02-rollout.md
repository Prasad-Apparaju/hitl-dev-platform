# Workflow Model — Cross-Check & Rollout

**Status:** Design (branch `design/workflow-model`).
**Companion docs:** [00-requirements.md](00-requirements.md) · [01-design.md](01-design.md)

---

## 1. Cross-check findings (against the live code)

The design was checked against the actual catalog, parser, and skills before committing to it.
Four things were found and resolved into the design.

| # | Finding (grounded) | Resolution (in the design) |
|---|---|---|
| **F1** | `ai/shared/workflows.yaml`: `development` has 7 phases; **every establishment workflow is single-phase** (`Brownfield Setup`, …). "One shared spine for all" is false. | Model **two families** — establishment (standalone) vs delivery (spine profiles). [01-design §4] |
| **F2** | **Incident reorders** the spine (fix-first → deploy → docs-after); **Chore** is trivially short. Neither is a subset-in-order of the spine. | Incident and Chore are **standalone short lists**, not spine profiles. [01-design §4] |
| **F3** | The parser (`hooks/_steps.sh`) reads stored `n` throughout (`hitl_steps`, `hitl_total`, `hitl_current_n`); the seed and `dev-update` migration both copy `s["n"]`. Dropping `n` = rewrite parser + schema + seed + migration + back-compat — re-opening the surface fixed in v1.0.29/30. | **Don't drop `n`.** The ribbon doesn't display a global number, so the counter dies at the *display* layer. Change file change is **additive** (add `phase`, keep `n`). [01-design §7] — this is the key de-risk. |
| **F4** | The full vision (catalog + 14 workflows + ribbon + step enrichment + generated command-map/role-guides + prose conversion) is multi-release. | **Phase it** (below). Each phase ships independently. |

## 2. Validation already done (prototype)

In a scratch prototype (not yet in-tree), confirmed:
- A numberless catalog generates a correct global + `phase.step` overview (substep `19a` ⇄
  `Verify.2a` derived).
- **Inserting one step** auto-renumbered everything downstream with **zero key changes and zero
  prose edits**.
- The phase-ribbon breadcrumb renders across all seven phases (banner + compact forms).
- The seeded `current-change.yaml` is **format-compatible with today's** (n/label/status), with
  `phase` added.

## 3. Phased rollout

| Phase | Scope | Touches | Risk |
|---|---|---|---|
| **0 — Capture** | This requirements + design + rollout doc set; the citation convention. | docs only | none |
| **1 — Catalog** | Numberless `workflows.yaml`; first-class `phases:`; the 14-workflow taxonomy (delivery spine superset + profiles; standalone Incident/Chore; establishment as-is). Overview generator (`tools/`). | catalog + generator + a generated overview doc | low — **data + docs only, no runtime change** |
| **2 — Breadcrumb** | Phase-ribbon banner + compact status line; add `phase` per step to the change file (additive); seed/migration derive `n` from the numberless catalog. | `_steps.sh`, `welcome.sh`, `statusline-hitl.sh`, schema (additive), `dev-start-change`/`dev-update` generators | medium — touches the change-file surface, but **additively** (C2) |
| **3 — Generated views** | Enrich steps with `command`/`role`/`ownership`; **generate** `command-map.md` and the role guides. | catalog (data) + generators | low |
| **4 — Prose** | Convert remaining number-citations (`workflow-steps.md`, `SKILL.md`, gates/diagrams) to name-citations. | docs | low, tedious |

Each phase is independently shippable and reversible. Phase 1 carries the bulk of the value
(eliminates renumber churn) with essentially zero runtime risk.

## 4. Risks & mitigations

- **R1 — Re-destabilizing the change file** (C2). *Mitigation:* additive-only (add `phase`, keep
  `n`); back-compat path for files lacking `phase`; the parser is extended, not rewritten.
- **R2 — Taxonomy churn in `dev-start-change`.** The workflow classifier must now choose among 14
  named workflows. *Mitigation:* classification is data-driven off the catalog; tabulate
  intent → workflow once.
- **R3 — Spine-superset bloat.** Conditional steps for Performance/Upgrade/Security live in the
  spine. *Mitigation:* they're profile-gated (off by default); the overview shows them as
  conditional.
- **R4 — Two unmerged doc branches.** `docs/update-workflow-docs-1.0.30` (the 31-step
  reconciliation) is still unpublished; this branch is off `main`. *Mitigation:* keep them
  independent; reconcile/merge order decided at ship time.

## 5. Open decisions (to settle before/within the relevant phase)

1. **Phase the establishment workflows?** Greenfield/Brownfield/Migration are single-phase today;
   grouping them (e.g. brownfield → Discover / Baseline / Kickoff) makes their ribbon meaningful.
   *Default: leave single-phase; revisit in Phase 1.*
2. **Explicit substep `parent`?** Attach a substep to its parent by `parent: review2` (stable)
   rather than positionally. *Default: positional, since substeps are rare (one in the system).*
3. **Security graduating its own gates.** Confirm Security's required gates (`dev-review-security`
   design+code, pentest) and Upgrade's (dependency/CVE audit, regression-heavy verify) when the
   profiles are written.
4. **Migration Slice specialization.** What it adds beyond a Feature: declare BI-IDs on the issue,
   update the coverage matrix, the observable-slice gate. Specialize as needed (the reason it's its
   own workflow).
5. **Versioning.** Phase 2's schema touch is additive → minor bump; confirm whether the whole
   initiative warrants a `1.1.0`.

## 6. Definition of done (for the initiative)

- Adding/reordering a step = one catalog line + the step's own prose; **no renumber sweep**.
- Breadcrumb shows **no global counter**; banner ribbon + named current step.
- `current-change.yaml` schema/parser/enforcement unchanged or only additively extended; existing
  projects keep working.
- Overview, breadcrumb, and (Phase 3) command-map/role guides are **generated** from the one
  catalog.
