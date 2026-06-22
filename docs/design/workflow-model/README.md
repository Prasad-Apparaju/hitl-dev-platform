# Workflow Model — Design Package

A redesign of how HITL encodes its workflows: **stable identities instead of positional numbers**,
**structure (workflow → phase → step → substep) separated from execution (commands)**, and a
**stakeholder-legible set of named workflows**. Captured before implementation, per HITL.

Read in order:

| Doc | What it covers |
|---|---|
| [00-requirements.md](00-requirements.md) | The problem (number staleness, command/process conflation), the workflow contract, goals, constraints, non-goals. |
| [01-design.md](01-design.md) | The model — hierarchy, numberless catalog + derived numbering, the two workflow families, the 14-workflow taxonomy, step→command/role, the phase-ribbon breadcrumb, the change-file impact, and the citation convention. |
| [02-rollout.md](02-rollout.md) | The cross-check against live code (4 findings + resolutions), prototype validation, the 5-phase rollout, risks, and open decisions. |

**Status:** Design on branch `design/workflow-model`. Phase 0 (this capture) is the only thing done
so far — no catalog/runtime changes yet.
