# Workflow Model — Requirements

**Status:** Design (branch `design/workflow-model`). Captured before implementation, per HITL.
**Companion docs:** [01-design.md](01-design.md) · [02-rollout.md](02-rollout.md)

---

## 1. Problem

HITL's process is real and good, but the way it is *encoded* has two structural flaws:

1. **Numbered steps go stale on every change.** Steps are identified by their global position
   (`Step 19a`, "rerun steps 18–20", "Steps 10–32", "after Step 9"). A number is a *position*
   used as an *identity*, so inserting or reordering one step renumbers everything downstream and
   every reference — across ~30 docs, the breadcrumb arrays, the skill summaries — goes stale at
   once. The recent `32 → 31` sweep (three releases of churn) was a direct symptom.

2. **The process is organized around commands and roles, not the work.** `command-map.md`
   conflates three independent things — the **process** (what happens, in order), the **commands**
   (what executes a step), and the **roles** (who is accountable) — into one hand-maintained
   document. That makes it brittle and hard to specialize.

We also lack **stakeholder-legible workflow names.** "development" tells a PM nothing about what
kind of change it is or who initiates it.

## 2. The workflow contract (the mental model)

A **workflow** is a repeatable abstraction for *one whole change*. Every workflow obeys these
invariants:

- It decomposes into **phases → steps → substeps**, in order.
- Each step is **owned by a role**, and the harness has a **skill/command** to do it the right way.
- Each step **consumes the previous step's outputs** — nothing starts from nothing.
- **Handoffs are GitHub issues backed by updated documentation** — the docs are the source of
  truth; the issue is the baton.
- It all happens **inside one branch**.
- It spans **requirement → post-deployment**.
- It can **pause at any step** for human input or approval (a feature, not a stall).
- One workflow = **one whole change**, start to finish.

### Three tiers of identity (locked 2026-06-23)

Not every distinct kind of change needs its own workflow. The model has **three tiers**, so
granularity is earned (G8) rather than assumed:

| Tier | Definition | When to use it |
|---|---|---|
| **Workflow** | Owns its step sequence (its own/reordered/replaced spine). | The *structure or order* of steps genuinely differs — establishment setup, Incident (fix-first), Migration Slice (BI-driven). |
| **Profile** | A named, menu-visible **preset over the shared delivery spine**: selects conditional steps, required gates, initiator. | A recognizable change someone *initiates as a unit* (Feature, Fix, Tech Change, Upgrade, Security) — same spine, different selection. |
| **Tag** | A composable label that **tunes required-evidence** within a profile; no steps of its own. | An intent that only changes *which evidence is required* (`refactor`, `perf`, `chore`, `tooling`, `infra`). |

The profile/tag a human picks only **proposes**; **impact analysis decides** the actual steps +
required-evidence (G9), and the **floor** (G10) is enforced regardless of tier. So the tier is a
*legibility* choice, not a correctness one. Full taxonomy in [01-design.md §4](01-design.md); the
enforcement model in [03-execution-model.md](03-execution-model.md).

## 3. Goals

| # | Goal |
|---|------|
| G1 | **Kill the global counter as an identity.** Steps are identified by a stable `key` + human name + phase. Numbers, where shown at all, are *derived display*, never stored references or hand-written prose. |
| G2 | **Separate structure from execution.** A workflow defines the *process* (ordered steps + gates); commands/skills do the *work*. The two are independently refinable — editing the process must not churn the commands, and vice versa. |
| G3 | **Stakeholder-legible workflows.** Name workflows by the *kind of whole change* so any role knows, from the name alone, who initiates, what goes in, and what comes out. |
| G4 | **Cover requirement → post-deployment** for every delivery workflow. |
| G5 | **Right initiator per workflow.** PM initiates functional change; engineering initiates technical change; ops initiates incidents. |
| G6 | **Define once, derive everything.** One catalog is the single source; the overview, breadcrumb, and (later) command-map and role guides are generated from it. |
| G7 | **Specializability.** Adding a phase, step, substep, or whole workflow is a small, local catalog edit — numbering and cross-references take care of themselves. |
| G8 | **Granularity is earned, not assumed.** A distinct *workflow* must justify itself by **materially different gates or steps**. Intent that only changes a label (and shares the same steps/gates) is a **change-kind tag** on the change, not a new workflow. Cheap-to-*define* (data-driven profiles) is not cheap-to-*use* — every named workflow is cognitive load for stakeholders and a branch the classifier can get wrong. |
| G9 | **The plan is determined by impact analysis, not predetermined.** The change's type/tier/steps/required-evidence are an **output** of impact analysis done **iteratively with the human** — the workflow is a refinable *proposal + template*, not a fixed pipeline. (See [03-execution-model.md](03-execution-model.md).) |
| G10 | **A non-skippable floor + informed-consent tailoring.** Some steps can never be skipped (the *floor*); the rest are skippable only via **tiered, informed, *recorded*** consent (the harness states what you miss, by whose authority, written to the ticket). Correctness is guaranteed by **enforced required-evidence**, not by the workflow name or a tag. |

> **Scope note.** This initiative began as a narrow fix ("docs go stale when steps are renumbered";
> minimal fix = cite steps by name). It has deliberately **evolved** into a broader model redesign
> (numberless catalog, phase-ribbon breadcrumb, named taxonomy, generated views). That evolution is
> accepted — but it raises **opportunity cost** against a plugin that is still stabilizing
> (recent Windows / YAML-parsing fixes). The mitigations are: strict **phasing** (each phase ships
> independently; see [02-rollout.md](02-rollout.md)) and **executability-first** (C5 below).

## 4. Constraints

- **C1 — Preserve the self-describing, portable change file** (`current-change.yaml`, issue #11):
  it must render the breadcrumb without the installed catalog.
- **C2 — Do not gratuitously re-destabilize the change file / parser / migration.** Two bugs were
  just fixed there (v1.0.29 comment-stripping, v1.0.30 block-style + Windows). Any change to that
  surface must be additive and back-compatible, with a clear payoff.
- **C3 — Back-compatible with existing v2 change files** in live projects.
- **C4 — No regression in enforcement.** The gate/hook behavior (intake, edit-block, status
  gating) must keep working.
- **C5 — Executability precedes presentation.** A workflow is not "done" until **every step
  resolves to an executor** (a skill, `manual`, or a deliberate `guided`). Polishing the breadcrumb
  or catalog must **not** precede closing the executor gaps — three referenced skills currently do
  not exist, and two proposed steps have none (see [02-rollout.md §7](02-rollout.md)). Build the
  plumbing before the façade.

## 5. Non-goals (for this initiative / deferred to later phases)

- Generating `command-map.md` and the role guides from the catalog — *designed for, but landed in
  a later phase* (see [02-rollout.md](02-rollout.md)).
- Changing the internal behavior of any skill/command.
- Re-phasing the establishment (setup) workflows — optional enrichment, deferred.

## 6. Success criteria

- Adding or reordering a step is a **one-line catalog edit + the new step's own prose** — zero
  cross-reference churn, zero renumber sweeps.
- A stakeholder can read a workflow name and correctly state its initiator, input, and output.
- The breadcrumb shows **no global step counter**; position is conveyed by phase + name + a
  derived, drift-resistant progress signal.
- `current-change.yaml`'s schema, the breadcrumb parser, and enforcement are unaffected or only
  additively extended.
