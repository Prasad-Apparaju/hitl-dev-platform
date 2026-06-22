# Workflow Model — Design

**Status:** Design (branch `design/workflow-model`).
**Companion docs:** [00-requirements.md](00-requirements.md) · [02-rollout.md](02-rollout.md)

This is the model. It satisfies the requirements: stable identities, derived numbers, structure
separated from execution, stakeholder-legible names.

---

## 1. The hierarchy — four levels

```
Workflow  →  Phase  →  Step  →  Substep
```

- **Workflow** — the whole process for one kind of change (e.g. `feature`, `migration`).
- **Phase** — an ordered grouping of steps within a workflow (e.g. `Verify`).
- **Step** — an ordered unit of work within a phase (e.g. *Code Review Round 2*).
- **Substep** — an optional child of a step, **one level deep** (e.g. *Architect Code Review* under
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

## 2. Identity vs. number — the core rule

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
No `n`, no `total` — those are derived.

```yaml
development:
  title: "Development — deliver a change"
  phases: [Requirements, Design, Build, Verify, Assess, Ship, Post-Ship]
  steps:
    - { key: review1,     name: "Code Review Round 1",   label: "Rvw1",    phase: Verify }
    - { key: review2,     name: "Code Review Round 2",   label: "Rvw2",    phase: Verify }
    - { key: arch_review, name: "Architect Code Review", label: "ArchRvw", phase: Verify, substep: true }
    - { key: rerun,       name: "Rerun Tests",           label: "Rerun",   phase: Verify }
```

### Derived numbering

A generator computes numbers from position. Substeps don't increment the integer; they append a
letter. Both global and phase-relative forms fall out:

```
| #  | phase.step | Step                  | key         |
| 19 | Verify.2   | Code Review Round 2   | review2     |
| 19a| Verify.2a  | Architect Code Review | arch_review |
| 20 | Verify.3   | Rerun Tests           | rerun       |
```

Insert one step earlier and everything renumbers automatically; **no `key` changes, no prose
breaks.** (Prototype verified — see [02-rollout.md](02-rollout.md) §Validation.)

## 4. Two families of workflow

A cross-check against the catalog showed **not all workflows share one spine** — establishment
workflows are single-phase setup sequences, structurally different from delivery. So:

### Family A — Establishment (run once to stand up the project)
Standalone ordered step lists (their own phases). Not profiles over the delivery spine.

| Workflow | What to expect | Initiator |
|---|---|---|
| **Greenfield** | New system from a PRD | PM + Architect |
| **Brownfield** | Adopt an existing codebase into HITL | Architect / Lead |
| **Migration** | Stand up a target to replace a source (inventory + brief) | Architect / Lead |

### Family B — Delivery (repeatable; requirement → post-deploy; one change each)
Most are **profiles over a shared spine** (the 7-phase development sequence): each profile selects
which steps apply and which gates are *required* vs *conditional*. Two exceptions —
**Incident** (reorders: fix-first) and **Chore** (tiny) — are **standalone short lists**, not spine
subsets.

```
Delivery — functional (PM-initiated)            [spine profiles]
├─ Feature       — new capability
├─ Enhancement   — extend/change an existing capability (back-compat gate)
└─ Fix           — correct a defect (lighter spine)

Delivery — technical (engineering-initiated)    [spine profiles]
├─ Refactor      — restructure / tech-debt, behavior identical
├─ Performance   — optimize, measured against a budget
├─ Security      — hardening / remediation (review + pentest gates required)
└─ Upgrade       — dependency / framework / version (dependency audit + regression-heavy)

Delivery — migration                            [spine profile + overlay]
└─ Migration Slice — deliver one behavior from the inventory (BI-IDs + coverage matrix + observable-slice gate)

Delivery — operational                          [STANDALONE list, reordered]
└─ Incident      — production P0, fix-first, full docs within 48h

Maintenance                                     [STANDALONE short list]
└─ Chore         — trivial technical change (config value, CI tweak, routine bump): PR + conventions only
```

**3 establishment + 11 delivery/maintenance = 14 named workflows**, each one stakeholder-legible.

> **⚠ Open tension — taxonomy granularity (decision pending).** 14 workflows is the current draft,
> arrived at by splitting "Engineering Change" into Refactor / Performance / Security / Upgrade /
> Chore. Per **G8 (granularity is earned)**, the split is only justified where the **gates actually
> differ** — strongly true for **Security** (review + pentest) and arguably **Upgrade** (dependency
> audit + regression), but thin for Refactor vs Chore vs Performance, whose distinction is largely an
> *intent label*. The risk of 14: stakeholder cognitive load, fuzzy boundaries (Feature vs
> Enhancement; "a perf fix that changes an API"), and a `dev-start-change` classifier that
> mis-routes. **Recommended alternative:** collapse to a smaller set — *Feature · Fix · Tech Change ·
> Incident* (+ functional *Enhancement*) — and carry the finer intents as a **change-kind tag**,
> promoting to a first-class workflow only those whose gates genuinely diverge (Security, maybe
> Upgrade). **Status:** the tree below retains the 14 pending this decision (see
> [02-rollout.md §5](02-rollout.md)).
>
> **Note:** per [03-execution-model.md](03-execution-model.md), the taxonomy is the *proposer +
> vocabulary*, not the correctness guarantee (that's the enforced required-evidence + the floor) — so
> this decision is about **legibility**, and is *less load-bearing* than it first appeared.

### What a "profile" declares
A spine-profile workflow is a few lines: which steps are **included**, which gates are **required**
(vs conditional), the **initiator**, and the functional/technical/operational class. The spine is
the *superset* of steps any delivery workflow can use (so e.g. *Performance*'s baseline-measurement
step and *Upgrade*'s dependency-audit step live in the spine, conditional, switched on by those
profiles).

### The full tree

The **delivery spine** is shown once — the 8 spine-profile workflows select from it (see the profile
table after the tree); **Incident** and **Chore** are standalone.

> **⚠ Unvalidated proposals — not yet confirmed with the team.** Several parts of this tree are my
> drafts, not established process, and will calcify if implemented as-is: the **establishment
> phasing** (Discover/Baseline/Kickoff etc. — Q1, and itself low-value; see
> [02-rollout.md §5](02-rollout.md)), the **Incident** and **Chore** step lists (no canonical
> source), and the **conditional spine additions** (Baseline Measurement, Dependency+CVE Audit) plus
> the per-profile **gate sets**. Treat them as starting points to validate, not decisions.

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

DELIVERY SPINE   (profiles select steps + required gates)       7 phases · 34 step-slots · 1 substep
├─ Requirements
│  ├─ GitHub Issue
│  └─ Figma Review (cond)
├─ Design
│  ├─ Impact Analysis
│  ├─ ROI Estimate (cond)
│  ├─ Update Docs — HLD/LLD
│  ├─ Update IaC + Verify Scripts (cond)
│  ├─ Test Case Planning
│  ├─ Training Plan Stub (cond)
│  ├─ Decision Packet
│  ├─ Baseline Measurement (cond · Performance)
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

incident     (DELIVERY · operational — P0, fix-first, docs ≤48h)   2 phases · 7 steps   [standalone]
├─ Respond
│  ├─ Triage + assess blast radius
│  ├─ Mitigate — stop the bleeding
│  └─ Verify recovery
└─ Document (≤48h)
   ├─ Root-cause / post-mortem
   ├─ Add regression test
   ├─ Reconcile docs + ADR
   └─ Update incident registry

chore        (MAINTENANCE · trivial technical change)              1 phase · 3 steps    [standalone]
└─ Chore
   ├─ Make the change
   ├─ Convention Checks
   └─ PR + merge
```

> The spine is a **superset of 34 step-slots**; most are conditional. A baseline **Feature** runs
> ~31 of them; the conditional slots (Baseline Measurement, Dependency+CVE Audit, Penetration Test,
> ROI, Figma, IaC, Training) switch on per profile.

### Delivery profiles over the spine

| Workflow | Class | Initiator | Distinctive profile (vs. a plain Feature) |
|---|---|---|---|
| **Feature** | functional | PM | the baseline spine |
| **Enhancement** | functional | PM | starts from the existing LLD · **back-compat gate** |
| **Fix** | functional | PM / QA | lighter — skip ROI/training · defect → regression test |
| **Refactor** | technical | Dev / Arch | skip Figma/training · characterization tests first · **full regression unchanged** |
| **Performance** | technical | Dev / Arch / Ops | **+ Baseline Measurement** · perf budget on issue · before/after verify |
| **Security** | technical | Arch / Sec / Ops | **dev-review-security design + code required · Penetration Test required** |
| **Upgrade** | technical | Dev / Ops | **+ Dependency + CVE Audit · full regression required · staged rollout** |
| **Migration Slice** | migration | Arch / Lead | requirement = migration brief · **BI-IDs + coverage matrix + observable-slice gate** |

## 5. Step → command / role — structure vs. execution

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
- one step → no command (*Figma Review*, *Refactor* are manual: `command: null`);
- one command → a whole workflow (`architect-design-system` → Greenfield).

This makes `command-map.md` and the role guides **generated views** (later phase), not
hand-maintained documents.

### `command` is a **required** field — coverage must be explicit

Every step declares one of: a **skill** (`command: dev-tdd`), **`manual`** (human/run-the-suite,
no command needed), or **`guided`** (driven by a reference doc, no skill yet). Making it required
means a missing executor can't hide in prose — today `workflow-steps.md` references three skills
that **don't exist** (`ops-review-release`, `architect-verify-traceability`, `ops-monitor-canary`).

Audit of the delivery spine against the real `ai/claude/` skills:

| Bucket | Count | Examples |
|---|---|---|
| ✅ **skill** (dedicated, exists) | ~20 | Impact Analysis → `dev-apply-change`; RED/Design+/GREEN → `dev-tdd`; reviews → `dev-review-lld-adherence`; QA → `qa-verify-quality`; Ship → the ops suite; gates → `ta-approve` |
| ✋ **manual** (by design) | ~7 | Figma Review, Verify RED, Verify GREEN, Refactor, Rerun Tests, Verify PR Completeness, Figma Comparison |
| 📄 **guided** (ref doc, no skill) | ~3 | ROI Estimate, Training Plan Stub, 30/90-day ROI Check |
| ❌ **gap — referenced skill missing** | 3 | Rollout Plan → `ops-review-release`; Integration Verification → `architect-verify-traceability`; Canary monitoring → `ops-monitor-canary` |
| 🆕 **gap — new step, no executor** | 2 | Baseline Measurement (Performance); Dependency + CVE Audit (Upgrade) |

The ❌ and 🆕 rows are real work (tracked in [02-rollout.md §7](02-rollout.md)). The point of the
required field is that this table is **generated from the catalog** and stays honest — the model is
only "executable end-to-end" once every step resolves to a skill, `manual`, or a deliberate
`guided`.

## 6. The breadcrumb — no global counter

Position is shown by **phase + name + a derived, drift-resistant signal** — never a global
`Step N / 31`.

### Banner (full width) — phase ribbon, 2-line
```
HITL development ▸ CERR-12 ▸ Requirements ✓  Design ✓  Build ✓  Verify ◐  Assess ·  Ship ·  Post-Ship ·
   … ✓Conv  ✓Rvw1  ✓Rvw2  ▶ Architect Code Review  ·Rerun  ·Recncl  ·QAVfy …
```
- **Line 1** = `HITL <workflow> ▸ <change-id> ▸ <phase ribbon>`. The ribbon marks every phase
  `✓` done · `◐` here · `·` not started — it only changes when a **phase** is added.
- **Line 2** = the windowed step trail, with the **current step expanded to its full name**
  (`▶ Architect Code Review`) and neighbors as short labels. Order + `▶` carry the position; no
  numbers.

### Status line (width-constrained) — compact
```
HITL ▸ CERR-12 ▸ Verify ▸ Architect Code Review
   … ✓Rvw1 ✓Rvw2 ▶ArchRvw ·Rerun ·Recncl …
```
`<change-id> ▸ <phase> ▸ <step name>` + trail. Still no global counter.

## 7. Change-file impact — additive only

The breadcrumb no longer *displays* a global number, so the change file needn't *store* one to kill
the global counter (the counter dies at the display layer). Therefore the change file change is
**additive and low-risk**:

- **Keep** the existing self-describing block (`steps: [{ n, key, label, status }]`, `total`) — the
  seed still derives `n` from the now-numberless catalog and writes it, exactly as today. (C2/C3.)
- **Add** `phase` per step, which the ribbon needs:
  ```yaml
  steps:
    - { n: 19,  key: review2,     label: "Rvw2",    phase: Verify, status: done }
    - { n: 19a, key: arch_review, label: "ArchRvw", phase: Verify, status: current, substep: true }
  ```
- Old files without `phase` degrade gracefully (ribbon falls back to the current-phase name only).

The parser keeps reading the file (no rewrite); it gains ribbon rendering from `phase` + `status`.
Portability (C1) is preserved — `phase` is in the file, so the breadcrumb still renders without the
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
