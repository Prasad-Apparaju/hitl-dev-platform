# Workflow Model: Design Package

A redesign of how HITL encodes its workflows: **stable identities instead of positional numbers**,
**structure (workflow → phase → step → substep) separated from execution (commands)**, and a
**stakeholder-legible set of named workflows**. Captured before implementation, per HITL.

Read in order:

| Doc | What it covers |
|---|---|
| [00-requirements.md](00-requirements.md) | The problem (number staleness, command/process conflation), the workflow contract, goals, constraints, non-goals. |
| [01-design.md](01-design.md) | The **structure**, hierarchy, numberless catalog + derived numbering, the three-tier taxonomy (workflow / profile / tag) + full tree, step→command/role + coverage audit, the phase-ribbon breadcrumb, the change-file impact, and the citation convention. |
| [03-execution-model.md](03-execution-model.md) | **How a change's plan is determined and enforced**, impact-analysis-driven plans, the floor/template/tailoring/enforcement layers, the non-skippable floor, tiered informed-skip waivers, required-evidence enforcement, docs-reconciled + deferred-regression rules. *(The heart of the model, read after 01.)* |
| [02-rollout.md](02-rollout.md) | The cross-check against live code (findings + resolutions), prototype validation, the phased rollout (incl. Phase 1b executability), command-coverage + execution-model work items, risks, and open decisions. |
| [04-harness-acceptance-criteria.md](04-harness-acceptance-criteria.md) | **Harness-wide quality bar**: Anthropic's standards for `SKILL.md` files (Part A) and the hooks/commands/settings the plugin installs (Part B), as MUST/SHOULD/EVAL/VERIFY acceptance criteria. Broader than workflow encoding; a CI gate as the redesign lands. |

**Status:** Design on branch `design/workflow-model`. Phase 0 (this capture) is the only thing done
so far, no catalog/runtime changes yet.
