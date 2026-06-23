# Workflow Model: Cross-Check & Rollout

**Status:** Design (branch `design/workflow-model`).
**Companion docs:** [00-requirements.md](00-requirements.md) · [01-design.md](01-design.md)

---

## 1. Cross-check findings (against the live code)

The design was checked against the actual catalog, parser, and skills before committing to it.
Four things were found and resolved into the design.

| # | Finding (grounded) | Resolution (in the design) |
|---|---|---|
| **F1** | `ai/shared/workflows.yaml`: `development` has 7 phases; **every establishment workflow is single-phase** (`Brownfield Setup`, …). "One shared spine for all" is false. | Establishment workflows own their step sequence (Workflow tier); delivery is the shared spine with profiles/tags over it (three-tier model). [01-design §4] |
| **F2** | **Incident reorders** the spine (fix-first → deploy → docs-after); **Chore** is trivially short. Neither is a subset-in-order of the spine. | Incident is a **standalone reordered workflow**; **Chore** is now a **Tier-0 `chore` tag** on Tech Change (floors at impact-analysis + docs-reconciled), not a standalone workflow. [01-design §4] |
| **F3** | The parser (`hooks/_steps.sh`) reads stored `n` throughout (`hitl_steps`, `hitl_total`, `hitl_current_n`); the seed and `dev-update` migration both copy `s["n"]`. Dropping `n` = rewrite parser + schema + seed + migration + back-compat, re-opening the surface fixed in v1.0.29/30. | **Don't drop `n`.** The ribbon doesn't display a global number, so the counter dies at the *display* layer. Change file change is **additive** (add `phase`, keep `n`). [01-design §7]; this is the key de-risk. |
| **F4** | The full vision (catalog + three-tier taxonomy + ribbon + step enrichment + generated command-map/role-guides + prose conversion) is multi-release. | **Phase it** (below). Each phase ships independently. |

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
| **0: Capture** | This requirements + design + rollout doc set; the citation convention. | docs only | none |
| **1: Catalog** | Numberless `workflows.yaml`; first-class `phases:`; the three-tier taxonomy (delivery spine superset + 6 profiles + tags; standalone Incident; establishment trio; `chore` as Tier-0 tag). **`command` is a required field** per step; this makes every executor gap explicit. Overview generator (`tools/`). | catalog + generator + a generated overview doc | low, **data + docs only, no runtime change** |
| **1b: Executability** ⛓ | Close the gaps Phase 1 surfaced: **W1** (build or rewire `ops-review-release`, `architect-verify-traceability`, `ops-monitor-canary`) and **W2** (executors for Baseline Measurement, Dependency+CVE Audit). See §7. | skills (build/rewire) | medium, real skill work |
| **2: Breadcrumb** | Phase-ribbon banner + compact status line; add `phase` per step to the change file (additive); seed/migration derive `n`. | `_steps.sh`, `welcome.sh`, `statusline-hitl.sh`, schema (additive), generators | medium, change-file surface, **additively** (no parser rewrite) |
| **3: Generated views** | Enrich steps with `role`/`ownership`; **generate** `command-map.md` + role guides. | catalog (data) + generators | low |
| **4: Prose** | Convert remaining number-citations (`workflow-steps.md`, `SKILL.md`, gates/diagrams) to name-citations. | docs | low, tedious |

**Executability-first:** Phase **1b gates everything after it**: the breadcrumb/generated-views
polish must **not** ship while steps still point at non-existent skills. Phase 1 is the bulk of the
value (eliminates renumber churn) at zero runtime risk; **1b is the real "can we run this" work** and
must not be skipped because it's less fun than the breadcrumb. Each phase is independently shippable.

## 4. Risks & mitigations

- **R1: Re-destabilizing the change file.** *Mitigation:* additive-only (add `phase`, keep
  `n`); back-compat path for files lacking `phase`; the parser is extended, not rewritten.
- **R2: Classifier accuracy in `dev-start-change`.** The more named workflows, the more often the
  classifier (and the human) mis-route a change, a direct cost of taxonomy granularity (§5.1).
  *Mitigation:* settle granularity the earned way (fewer workflows + change-kind tags); classification is
  data-driven off the catalog; tabulate intent → workflow once.
- **R3: Spine-superset bloat.** Conditional steps for the `perf` tag / Upgrade / Security live in
  the spine (it carries 35 step-slots, most conditional). *Mitigation:* they're profile/tag-gated
  (off by default); the overview shows them as conditional. This is the deliberate trade of the
  three-tier model, one rich conditional spine instead of many lean named pipelines.
- **R4: Two unmerged doc branches.** `docs/update-workflow-docs-1.0.30` (the 31-step
  reconciliation) is still unpublished; this branch is off `main`. *Mitigation:* keep them
  independent; reconcile/merge order decided at ship time.
- **R5: Codifying unvalidated process.** Parts of the model are first-drafts, not established
  practice: the **Incident step list**, the **establishment phasing**, the **conditional
  spine additions** (Baseline Measurement, Security Design Review, Dependency+CVE Audit), and the
  **per-profile/tag gate sets**.
  Codified design defaults get implemented as if considered. *Mitigation:* mark them "proposed" in
  the design (done), and **validate each with the team / a pilot run before Phase 1 writes them into
  the catalog**; don't let a draft become the contract by inertia.
- **R6: Priority inversion (process lesson).** This thread polished the breadcrumb and taxonomy
  (presentation) before auditing whether steps can run (substance); the audit then found missing
  executors. *Mitigation:* executability-first / Phase 1b; and as a standing habit, audit executability before
  presentation.

## 5. Open decisions (to settle before/within the relevant phase)

1. **★ Taxonomy granularity, LOCKED 2026-06-23: three-tier model.** Resolved into
   **Workflow / Profile / Tag** (see [01-design.md §4](01-design.md)):
   - **5 workflows** (own/reordered/replaced spine): Greenfield · Brownfield · Migration · Incident
     (reorders) · Migration Slice (replaces).
   - **6 profiles** (presets over the shared delivery spine): Feature · Enhancement · Fix · Tech
     Change · Upgrade · Security. *(Upgrade is a profile, initiated as a unit with distinct gates;
     Security is a profile, mandatory never-skippable gates, but it does **not** reorder the spine,
     correcting the earlier "Security reorders" claim.)*
   - **5 tags** (tune required-evidence within a profile): `refactor` · `perf` · `chore` · `tooling` ·
     `infra`.
   This reverses the earlier "split into 14" and folds engineering-change sprawl
   (Refactor/Performance/Chore) into tags on **Tech Change**. Rationale: granularity is earned, not assumed
   + correctness lives in the floor/required-evidence, not the name, so the choice is about
   legibility/classifier accuracy; promotion (tag → profile) is a cheap catalog edit, un-naming is
   not, so start lean.
2. **Explicit substep `parent`, LOCKED 2026-06-23: explicit.** Substeps carry `parent: <key>`
   (e.g. `arch_review` → `parent: review2`), not positional attachment, positional contradicts the
   redesign's own "don't rely on position" thesis, and it's one field. (Applied in
   [01-design.md §3](01-design.md).)
3. **Per-profile/tag gate sets, LOCKED as Phase-1 *defaults*, flagged for pilot validation.** The
   documented required gates are the starting contract Phase 1 writes: **Security** profile
   (`dev-review-security` design+code, pentest), **Upgrade** profile (dependency/CVE audit,
   regression-heavy verify), **`perf`** tag (baseline + budget), **`refactor`** tag (characterization +
   unchanged regression). *This is the one decision that cannot be closed from design alone*, whether
   each set is **complete** is a team/pilot judgment (R5). Resolution: ship these as defaults; the
   **first pilot run of each profile/tag confirms or amends the set** before it's treated as the
   contract. Do not let "documented" pass for "validated."
4. **Migration Slice specialization, LOCKED 2026-06-23.** It adds exactly: requirement = migration
   brief · issue declares BI-IDs · observable-slice gate · update coverage matrix. No other deltas; a
   pilot may add, but the catalog ships with these four.
5. **Versioning, LOCKED 2026-06-23: `1.1.0`.** The whole initiative ships as one minor (Phase 2's
   schema touch is additive; the breadcrumb is the user-visible headline), not scattered across
   patches.
6. **Deferred-regression blocks "complete", LOCKED 2026-06-23: confirmed.** A deferred regression
   becomes a tracked ticket (owner + due) linked to the change that **blocks "change complete"** (not
   merge/canary), or an explicit recorded architect risk-acceptance. (Finalised in
   [03-execution-model.md §6](03-execution-model.md).)
7. **UX design artifact, LOCKED 2026-06-23.** A user-facing change requires a PM-owned UX artifact,
   Claude Design / Figma / at minimum a screenshot (floor item #2,
   [03-execution-model.md §3](03-execution-model.md)). **Strictness: hard-floor on existence, never
   waiverable**, the screenshot tier is already the cheapest floor, so a trivial tweak costs one
   screenshot rather than a waiver conversation. **"User-facing" trigger: a rendered UI delta a user can
   perceive** (layout, component, styling, visible copy, interaction/flow); purely internal changes with
   no rendered delta don't trigger it. Impact analysis sets the flag and asks the PM when unsure.

**Dropped** (was open decision): *phase the establishment workflows.* Low value, a setup workflow
runs **once** and you're never lost in it; the ribbon earns its keep on the repeated delivery flow.
Greenfield/Brownfield/Migration stay single-phase. (The tree's phasing of them is now marked a
proposal in [01-design.md](01-design.md) and will likely be removed.)

## 6. Definition of done (for the initiative)

- Adding/reordering a step = one catalog line + the step's own prose; **no renumber sweep**.
- Breadcrumb shows **no global counter**; banner ribbon + named current step.
- `current-change.yaml` schema/parser/enforcement unchanged or only additively extended; existing
  projects keep working.
- Overview, breadcrumb, and (Phase 3) command-map/role guides are **generated** from the one
  catalog.
- **Every step resolves to an executor**, a skill, `manual`, or a deliberate `guided` (§7).
- **Every workflow, profile, and tag is verified to run end to end, and its breadcrumb shows the
  correct status in every case.** A test matrix seeds a real `current-change.yaml` per case and runs
  the renderers (`welcome.sh`, `statusline-hitl.sh`): each phase of each workflow, profile/tag
  conditional steps switched on, substeps, skipped steps, deferred-regression, and branch-mismatch.
  No case may render a wrong or empty trail. This runs in CI so it can't regress.

---

## 7. Command-coverage work items

Surfaced by auditing the spine against the real `ai/claude/` skills (see
[01-design.md §5](01-design.md)). Until these resolve, the model is not executable end-to-end.
Making `command` a **required catalog field** (Phase 1) makes the gap explicit per step; closing the
gaps is its own track (parallel to Phase 3).

### W1: Missing referenced skills (build, rewire, or mark manual)
`workflow-steps.md` references three skills that **do not exist**:

| Step | Referenced | Decision needed |
|---|---|---|
| Risk-Rated Rollout Plan | `ops-review-release` | build the skill, or fold rollout review into `dev-impact-brief` §5 + a TA/ops gate |
| Integration Verification | `architect-verify-traceability` | build it, or assign to `architect-review-existing` / a manual lead check |
| Canary monitoring (in Deploy) | `ops-monitor-canary` | build it, or fold into `ops-deploy` / `ops-post-deploy-monitor` |

### W2: New steps needing an executor
| Step | Workflow | Decision needed |
|---|---|---|
| Baseline Measurement | `perf` tag | new thin skill vs. capture in the issue/manual |
| Dependency + CVE Audit | Upgrade | new skill vs. fold into Impact Analysis (`dev-apply-change`) |

### W3: Guided steps (no skill today)
ROI Estimate, Training Plan Stub, 30/90-day ROI Check, keep `guided` (reference docs), or give each
a thin command. *Default: keep guided unless a command adds real value.*

### W4: Manual steps
UX Design Artifact, Verify RED/GREEN, Refactor, Rerun Tests, Verify PR Completeness, Figma Comparison:
confirm they stay `manual` (run-the-suite / human judgment). *Default: yes.*

### W5: Execution model (the floor + informed-skip + enforcement): see [03-execution-model.md](03-execution-model.md)
The biggest substance, not yet built. Spans Phase 1 (metadata) and a new enforcement work-stream:
- **Per-step metadata** (Phase 1, data): `floor` (+ condition `code|prod|docs`), `skip_authority`
  (`never|architect|dev`), `rationale`/`skip_warning`.
- **Extend `required_evidence`** (schema, additive): add `docs_reconciled`; impact analysis writes the
  per-change required set; gates enforce it.
- **Informed-skip flow** in the planning skill (`dev-apply-change`/`dev-start-change`): state the cost
  from `rationale`, require a substantive reason, write a structured **waiver**
  (`{step, decided_by, role, when, reason}`) to the **issue comment** + `current-change.yaml`
  (`status: skipped`). Reject floor/unauthorised skips.
- **Hook enforcement**: `check-hitl-context` (or a new gate) blocks closing a change with a missing
  required-evidence item *unless* a valid waiver exists; the floor is never waivable.
- **Docs-reconciled closing gate** (drift): non-skippable for changes touching documented behaviour.
- **Deferred-regression tracking**: a deferred regression becomes a linked ticket that blocks
  "change complete" (not merge), surfaced as `regression: deferred → #ticket`. *(Confirmed 2026-06-23.)*
- **Skip telemetry**: surface skips in PR/breadcrumb + a skip log; track patterns.

> **Taxonomy is now demoted** (§5.1): per the execution model, correctness is the floor +
> enforced required-evidence, not the workflow name. Settle granularity for *legibility*; it no longer
> blocks the rest.

W1 and W2 are the only true blockers to "executable end-to-end"; W3/W4 are deliberate `guided`/
`manual` classifications.
