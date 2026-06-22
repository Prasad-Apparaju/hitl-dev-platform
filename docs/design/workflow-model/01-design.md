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

### What a "profile" declares
A spine-profile workflow is a few lines: which steps are **included**, which gates are **required**
(vs conditional), the **initiator**, and the functional/technical/operational class. The spine is
the *superset* of steps any delivery workflow can use (so e.g. *Performance*'s baseline-measurement
step and *Upgrade*'s dependency-audit step live in the spine, conditional, switched on by those
profiles).

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
