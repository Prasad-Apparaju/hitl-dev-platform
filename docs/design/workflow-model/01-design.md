# Workflow Model: Design

**Status:** Design (branch `design/workflow-model`).
**Companion docs:** [00-requirements.md](00-requirements.md) · [02-rollout.md](02-rollout.md)

This is the model. It satisfies the requirements: stable identities, derived numbers, structure
separated from execution, stakeholder-legible names.

---

## 1. The hierarchy: four levels

```
Workflow  →  Phase  →  Step  →  Substep
```

- **Workflow**: the whole process for one kind of change (e.g. `feature`, `migration`).
- **Phase**: an ordered grouping of steps within a workflow (e.g. `Verify`).
- **Step**: an ordered unit of work within a phase (e.g. *Code Review Round 2*).
- **Substep**: an optional child of a step, **one level deep** (e.g. *Architect Code Review* under
  *Code Review Round 2*). Most steps have none; substeps never nest further.

Example (excerpt of the delivery spine):
```
development spine
├─ Verify
│  ├─ Code Review Round 1
│  ├─ Code Review Round 2
│  │  └─ Architect Code Review        (substep)
│  ├─ Rerun Tests
│  └─ …
```

## 2. Identity vs. number: the core rule

> **Identity = stable `key` + human `name` + `phase`. The number is derived display, never stored
> or hand-written.**

| Layer | Identifier | Example |
|---|---|---|
| Data / anchors / deep links | stable `key` slug | `arch_review` |
| Human prose, gates, diagrams | Phase + Name | *Verify → Architect Code Review* |
| Display only (overview, breadcrumb) | derived number, computed from position | `19a` / `Verify.2a` (or none) |

Prose **never** says "Step 19a" or "rerun steps 18–20"; it says *Architect Code Review* / *rerun the
Verify reviews*. Those references survive any insertion or reorder.

## 3. The numberless catalog

`ai/shared/workflows.yaml` becomes numberless. **Phases are first-class**; steps carry a stable
`key`, a human `name`, a short `label` (for the trail), a `phase`, and an optional `substep` flag.
No `n`, no `total`; those are derived.

```yaml
development:
  title: "Development: deliver a change"
  phases: [Requirements, Design, Build, Verify, Assess, Ship, Post-Ship]
  steps:
    - { key: review1,     name: "Code Review Round 1",   label: "Rvw1",    phase: Verify }
    - { key: review2,     name: "Code Review Round 2",   label: "Rvw2",    phase: Verify }
    - { key: arch_review, name: "Architect Code Review", label: "ArchRvw", phase: Verify, substep: true, parent: review2 }
    - { key: rerun,       name: "Rerun Tests",           label: "Rerun",   phase: Verify }
```

### Derived numbering

A generator computes numbers from position. A substep declares its `parent` by key (not position) and
attaches under it; substeps don't increment the integer; they append a letter. Both global and
phase-relative forms fall out:

```
| #  | phase.step | Step                  | key         |
| 19 | Verify.2   | Code Review Round 2   | review2     |
| 19a| Verify.2a  | Architect Code Review | arch_review |
| 20 | Verify.3   | Rerun Tests           | rerun       |
```

Insert one step earlier and everything renumbers automatically; **no `key` changes, no prose
breaks.** (Prototype verified; see [02-rollout.md](02-rollout.md) §Validation.)

## 4. Three tiers: workflow, profile, tag

> **★ Decision locked (2026-06-23).** Granularity is resolved into **three tiers**, replacing the
> earlier "14 named workflows" draft. The driving rule, granularity is earned not assumed: **a thing is only its own *workflow* if
> its step *sequence/structure* differs; a named *profile* if it's a recognizable preset over the
> shared spine; otherwise a *tag* that tunes required-evidence.** This collapses the engineering-change
> sprawl (Refactor/Performance/Chore → tags) while keeping the legible ceremonies (Tech Change,
> Upgrade, Security) as profiles. See [02-rollout.md §5](02-rollout.md) for the rationale.
>
> Correctness never depended on this choice. Per [03-execution-model.md](03-execution-model.md), the
> guarantee is the **floor + enforced required-evidence**, determined by impact analysis. The tier a
> thing lands in is about **legibility and classifier accuracy**, not rigor. Tier promotion (tag →
> profile) is a one-line catalog edit; un-naming a learned profile is expensive, so the default is
> *start lean, promote on evidence of standalone use*.

| Tier | What it is | Spine | Menu-visible | Examples |
|---|---|---|---|---|
| **Workflow** | Own / reordered / replaced step sequence | its own | yes | Greenfield · Brownfield · Migration (establishment) · **Incident** (reorders: fix-first) · **Migration Slice** (replaces spine: BI-driven) · **Docs** (own short spine: documentation-only) |
| **Profile** | Named preset over the **shared delivery spine**, selects which conditional steps are on, which gates are *required*, and the initiator | shared | yes | **Feature · Enhancement · Fix · Tech Change · Upgrade · Security** |
| **Tag** | A label on a change that **tunes required-evidence** within a profile (composable, stackable) | shared | no (shown on breadcrumb) | `refactor` · `perf` · `chore` · `tooling` · `infra` |

**Why each engineering intent lands where it does:**

- **Tech Change** is the single home for engineering-initiated structural work. Refactor, perf, dead-code
  cleanup, config, CI, observability all run *its* spine; they differ only in *which evidence is
  required*, so they're **tags**, not separate profiles. (`refactor` → characterization tests +
  behavior-unchanged; `perf` → baseline + budget; `chore` → Tier-0, floors only at impact-analysis +
  docs-reconciled.)
- **Upgrade** is a **profile** (not a tag): a dependency/framework bump is *initiated as a unit* (a legible, stakeholder-facing ceremony) and carries distinctive required gates (Dependency+CVE audit, regression-heavy verify,
  staged rollout). It doesn't reorder the spine, so it isn't a workflow.
- **Security** is a **profile**: it does **not** reorder the spine (the pentest step already lives in
  Ship, a security-design review fits the existing Design phase). What distinguishes it is
  **mandatory, never-skippable gates** (`dev-review-security` design+code, Penetration Test) and a
  distinct initiator (Sec/Arch/Ops).
- **Incident** is a **workflow**: it genuinely *reorders* (fix-first → deploy → docs ≤48h).
- **Migration Slice** is a **workflow**: it *replaces* the spine's front with a migration brief +
  BI-IDs + observable-slice gate + coverage matrix.
- **Docs** is a **workflow** (added 2.0, plugin issue #19): a documentation-only change has its own
  short 6-step spine (issue → scope → draft → domain-routed review → reconcile cross-refs → merge),
  no code or TDD. Chosen only when a change touches nothing but docs; a mixed docs+code change stays
  on the delivery spine, which already reconciles docs. This closes the gap where docs changes either
  owed the full delivery trail or bypassed HITL entirely.

**Key safety property (the classifier trap):** the tag/profile a human *picks* only **proposes**;
**impact analysis decides by what the change actually touches.** A "refactor" that turns out to alter
an API response is re-classified to Fix/Enhancement and the functional steps switch back on. The
label can't suppress the floor. (See [03-execution-model.md §5](03-execution-model.md).)

**Tally: 6 workflows + 6 profiles + 5 tags** (Docs added in 2.0), versus 14 flat workflows. Profiles
and tags share one spine, so the maintenance + classifier surface is the workflows + the spine, not
25 things.

### What a "profile" declares
A spine-profile is a few lines: which steps are **included**, which gates are **required** (vs
conditional), the **initiator**, the functional/technical class, and any **always-on tags**. The spine
is the *superset* of steps any delivery profile can use (so *Upgrade*'s Dependency+CVE Audit step and
the `perf`-tag's Baseline Measurement step live in the spine, conditional, switched on by the profile
or tag).

### The full tree

The **delivery spine** is shown once; the **6 profiles** select from it (see the profile table after
the tree); **Incident** is a standalone reordered workflow. **Chore is no longer a standalone
workflow**; it's a Tier-0 `chore` tag on Tech Change, floored only at impact-analysis + docs-reconciled.

> **⚠ Unvalidated proposals, not yet confirmed with the team.** Several parts of this tree are my
> drafts, not established process, and will calcify if implemented as-is: the **establishment
> phasing** (Discover/Baseline/Kickoff etc., Q1, and itself low-value; see
> [02-rollout.md §5](02-rollout.md)), the **Incident** step list (no canonical source), and the
> **conditional spine additions** (Baseline Measurement, Dependency+CVE Audit) plus the per-profile
> **gate sets**. Treat them as starting points to validate, not decisions.

```
greenfield   (ESTABLISHMENT · new system from a PRD)            1 phase · 4 steps
└─ Setup
   ├─ Customize CLAUDE.md
   ├─ Initialize manifest
   ├─ Create GitHub issue
   └─ Confirm ready

brownfield   (ESTABLISHMENT · onboard an existing codebase)     3 phases · 11 steps
├─ Discover
│  ├─ Map the codebase
│  ├─ Customize CLAUDE.md
│  ├─ Generate system manifest
│  └─ Review existing architecture
├─ Baseline
│  ├─ Verify build + deployment pipeline
│  ├─ Set up observability
│  ├─ Priority component docs
│  ├─ Seed registries
│  └─ Graphify (optional)
└─ Kickoff
   ├─ Create first change issue
   └─ Confirm ready

migration    (ESTABLISHMENT · stand up a target to replace a source)   3 phases · 9 steps
├─ Setup
│  ├─ Collect migration context
│  ├─ Customize CLAUDE.md
│  ├─ Initialize system manifest
│  └─ Set up directory structure
├─ Analyze
│  ├─ Analyze source codebase
│  └─ Ingest external docs (optional)
└─ Kickoff
   ├─ Seed registries
   ├─ Create tracking issue
   └─ Confirm and hand off

DELIVERY SPINE   (profiles select steps + required gates)       7 phases · 35 step-slots · 1 substep
├─ Requirements
│  ├─ GitHub Issue
│  └─ UX Design Artifact (cond · user-facing; PM-owned: Claude Design / Figma / screenshot)
├─ Design
│  ├─ Impact Analysis
│  ├─ ROI Estimate (cond)
│  ├─ Update Docs, HLD/LLD
│  ├─ Update IaC + Verify Scripts (cond)
│  ├─ Test Case Planning
│  ├─ Training Plan Stub (cond)
│  ├─ Decision Packet
│  ├─ Baseline Measurement (cond · `perf` tag)
│  ├─ Security Design Review (cond · Security)
│  └─ Dependency + CVE Audit (cond · Upgrade)
├─ Build
│  ├─ Generate Tests (RED)
│  ├─ Human Reviews Tests
│  ├─ Tests Improve Design
│  ├─ Verify RED
│  ├─ Generate Code (GREEN)
│  ├─ Verify GREEN
│  ├─ Refactor
│  └─ Convention Checks
├─ Verify
│  ├─ Code Review Round 1
│  ├─ Code Review Round 2
│  │  └─ Architect Code Review   (substep)
│  ├─ Rerun Tests
│  ├─ Reconcile Docs
│  └─ QA Post-Handoff Verification
├─ Assess
│  ├─ Downstream Impact Brief
│  └─ Risk-Rated Rollout Plan
├─ Ship
│  ├─ Verify PR Completeness
│  ├─ Integration Verification
│  ├─ Figma Comparison (cond)
│  ├─ Build, Migrate, Apply IaC, Deploy
│  ├─ Penetration Test (cond · Security)
│  └─ Promote or Rollback
└─ Post-Ship
   ├─ 30-day ROI Check (cond)
   └─ 90-day ROI Check (cond)

incident     (DELIVERY · operational, P0, fix-first, docs ≤48h)   2 phases · 7 steps   [standalone]
├─ Respond
│  ├─ Triage + assess blast radius
│  ├─ Mitigate, stop the bleeding
│  └─ Verify recovery
└─ Document (≤48h)
   ├─ Root-cause / post-mortem
   ├─ Add regression test
   ├─ Reconcile docs + ADR
   └─ Update incident registry
```

> The spine is a **superset of 35 step-slots**; most are conditional. A baseline **Feature** runs
> ~31 of them; the conditional slots (Baseline Measurement, Security Design Review, Dependency+CVE
> Audit, Penetration Test, ROI, Figma, IaC, Training) switch on per profile **or tag**.

### Delivery profiles over the spine

The **6 profiles** below select steps + required gates from the shared spine. **Tags** (`refactor`,
`perf`, `chore`, `tooling`, `infra`) stack on top of a profile (usually Tech Change) to tune
required-evidence, they are not rows here. **Migration Slice** is a *workflow* (it replaces the spine
front), listed for completeness.

| Profile | Class | Initiator | Distinctive profile (vs. a plain Feature) |
|---|---|---|---|
| **Feature** | functional | PM | the baseline spine |
| **Enhancement** | functional | PM | starts from the existing LLD · **back-compat gate** |
| **Fix** | functional | PM / QA | lighter, skip ROI/training · defect → regression test |
| **Tech Change** | technical | Dev / Arch | engineering-initiated structural work · skip Figma/ROI/training · tags refine: `refactor` → characterization tests + behavior-unchanged; `perf` → Baseline Measurement + budget; `chore` → Tier-0 |
| **Upgrade** | technical | Dev / Ops | **+ Dependency + CVE Audit · full regression required · staged rollout** |
| **Security** | technical | Arch / Sec / Ops | **dev-review-security design + code required (never-skippable) · Penetration Test required** |
| *Migration Slice* (workflow) | migration | Arch / Lead | requirement = migration brief · **BI-IDs + coverage matrix + observable-slice gate** |

### How the three tiers are encoded in the catalog

The shape below documents the **target encoding**; it is **not** the live `ai/shared/workflows.yaml`
yet. Writing it is **Phase 1** (catalog), which is gated by **Phase 1b executability** (build the plumbing before the façade), so this
subsection is the contract Phase 1 implements, not a change to ship now.

A **workflow** owns its `phases` + `steps` (the establishment trio, Incident, Migration Slice, already
how today's catalog is shaped). The **shared delivery spine** is one workflow entry; **profiles** and
**tags** are declared *against* it:

```yaml
# One shared spine (the superset of step-slots; most steps carry a `cond` key).
delivery_spine:
  title: "Delivery, one change, requirement → post-deploy"
  phases: [Requirements, Design, Build, Verify, Assess, Ship, Post-Ship]
  steps:
    - { key: impact,    name: "Impact Analysis",      label: "Impact",  phase: Design }
    - { key: baseline,  name: "Baseline Measurement",  label: "Basln",  phase: Design,  cond: true }
    - { key: sec_design,name: "Security Design Review", label: "SecDsn", phase: Design,  cond: true }
    - { key: cve_audit, name: "Dependency + CVE Audit", label: "CVE",    phase: Design,  cond: true }
    - { key: pentest,   name: "Penetration Test",       label: "Pentest",phase: Ship,    cond: true }
    # … the rest of the 35 slots …

# Profiles: a named preset over the spine. A few lines each.
profiles:
  feature:      { class: functional, initiator: PM }    # the baseline spine selection
  tech_change:  { class: technical,  initiator: Dev, exclude: [figma, roi, training] }
  upgrade:      { class: technical,  initiator: Dev, on: [cve_audit], required_evidence: [cve_audit, full_regression] }
  security:     { class: technical,  initiator: Sec, on: [sec_design, pentest],
                  required_evidence: [security_review, pentest], skip_authority: { security_review: never } }

# Tags: stack on a profile, tune required-evidence only (no own steps/phases).
tags:
  refactor: { on: [characterization], required_evidence: [behavior_unchanged] }
  perf:     { on: [baseline],          required_evidence: [perf_budget_met] }
  chore:    { tier: 0 }   # floors only at impact-analysis + docs-reconciled
```

The classifier in `dev-start-change` proposes `{workflow | profile, tags[]}`; **impact analysis
finalises the included steps + `required_evidence`** (the profile/tag values are a *starting set*, not
the contract, see [03-execution-model.md §5](03-execution-model.md)). `current-change.yaml` records
the resolved `profile`, `tags`, and `required_evidence`, additively, alongside the existing `workflow`
block (§7); no parser rewrite.

## 5. Step → command / role: structure vs. execution

Each step carries the metadata that lets the **process** stay separate from the **work**:

```yaml
- key: green
  name: "Generate Code (GREEN)"
  phase: Build
  role: dev            # who owns it
  command: dev-tdd     # what executes it (one command may serve several steps; some steps have none)
  ownership: ai        # ai | ai+human | human
```

Relationships are **many-to-many** and the catalog states each once:
- one command → many steps (`dev-tdd` → RED, Tests-Improve-Design, GREEN);
- one step → no command (*UX Design Artifact*, *Refactor* are manual: `command: null`);
- one command → a whole workflow (`architect-design-system` → Greenfield).

This makes `command-map.md` and the role guides **generated views** (later phase), not
hand-maintained documents.

### `command` is a **required** field: coverage must be explicit

Every step declares one of: a **skill/command** (`command: dev-tdd` or `command: ops/review-release`),
**`manual`** (human/run-the-suite, no command needed), or **`guided`** (driven by a reference doc, no
skill yet). Making it required means a missing executor can't hide in prose. The field must resolve
against **commands + agents**, not just `SKILL.md` dirs, an earlier audit wrongly flagged three steps
as having no executor (`ops-review-release`, `architect-verify-traceability`, `ops-monitor-canary`)
because it only looked for skill dirs; all three exist as command files delegating to agents (see
[02-rollout.md §7](02-rollout.md)).

Audit of the delivery spine against the real `ai/claude/` skills:

| Bucket | Count | Examples |
|---|---|---|
| ✅ **skill** (dedicated, exists) | ~20 | Impact Analysis → `dev-apply-change`; RED/Design+/GREEN → `dev-tdd`; reviews → `dev-review-lld-adherence`; QA → `qa-verify-quality`; Ship → the ops suite; gates → `ta-approve` |
| ✋ **manual** (by design) | ~7 | UX Design Artifact, Verify RED, Verify GREEN, Refactor, Rerun Tests, Verify PR Completeness, Figma Comparison |
| 📄 **guided** (ref doc, no skill) | ~3 | ROI Estimate, Training Plan Stub, 30/90-day ROI Check |
| ❌ **gap, referenced skill missing** | 3 | Rollout Plan → `ops-review-release`; Integration Verification → `architect-verify-traceability`; Canary monitoring → `ops-monitor-canary` |
| 🆕 **gap, new step, no executor** | 2 | Baseline Measurement (Performance); Dependency + CVE Audit (Upgrade) |

The ❌ and 🆕 rows are real work (tracked in [02-rollout.md §7](02-rollout.md)). The point of the
required field is that this table is **generated from the catalog** and stays honest, the model is
only "executable end-to-end" once every step resolves to a skill, `manual`, or a deliberate
`guided`.

## 6. The breadcrumb: no global counter

Position is shown by **phase + name + a derived, drift-resistant signal**, never a global
`Step N / 31`.

### Banner (full width): phase ribbon, 2-line
```
HITL development ▸ CERR-12 ▸ Requirements ✓  Design ✓  Build ✓  Verify ◐  Assess ·  Ship ·  Post-Ship ·
   … ✓Conv  ✓Rvw1  ✓Rvw2  ▶ Architect Code Review  ·Rerun  ·Recncl  ·QAVfy …
```
- **Line 1** = `HITL <workflow> ▸ <change-id> ▸ <phase ribbon>`. The ribbon marks every phase
  `✓` done · `◐` here · `·` not started, it only changes when a **phase** is added.
- **Line 2** = the windowed step trail, with the **current step expanded to its full name**
  (`▶ Architect Code Review`) and neighbors as short labels. Order + `▶` carry the position; no
  numbers.

### Status line (width-constrained): compact
```
HITL ▸ CERR-12 ▸ Verify ▸ Architect Code Review
   … ✓Rvw1 ✓Rvw2 ▶ArchRvw ·Rerun ·Recncl …
```
`<change-id> ▸ <phase> ▸ <step name>` + trail. Still no global counter.

## 7. Change-file impact: additive only

The breadcrumb no longer *displays* a global number, so the change file needn't *store* one to kill
the global counter (the counter dies at the display layer). Therefore the change file change is
**additive and low-risk**:

- **Keep** the existing self-describing block (`steps: [{ n, key, label, status }]`, `total`), the
  seed still derives `n` from the now-numberless catalog and writes it, exactly as today. This keeps the change-file and parser surface stable and stays back-compatible with existing v2 files.
- **Add** `phase` per step, which the ribbon needs:
  ```yaml
  steps:
    - { n: 19,  key: review2,     label: "Rvw2",    phase: Verify, status: done }
    - { n: 19a, key: arch_review, label: "ArchRvw", phase: Verify, status: current, substep: true }
  ```
- Old files without `phase` degrade gracefully (ribbon falls back to the current-phase name only).

The parser keeps reading the file (no rewrite); it gains ribbon rendering from `phase` + `status`.
Portability is preserved: `phase` is in the file, so the breadcrumb still renders without the
catalog.

## 8. The citation convention (the durable rule)

1. **Identity = stable `key` + name + phase.** Never a number.
2. **Numbers are derived output**, computed from position; never stored as references or written in
   prose.
3. **Prose, gates, diagram nodes cite by name** (and phase when ambiguous). Diagram node *ids* use
   the stable `key`, so edges never break on renumber.
4. **Deep links/anchors use the `key` slug.**
5. **Numbers appear in exactly two places, both generated:** the overview table and the breadcrumb
   (and the breadcrumb shows no *global* number at all).
