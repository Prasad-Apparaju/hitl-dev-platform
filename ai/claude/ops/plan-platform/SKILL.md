---
description: Derive or refresh the platform readiness register, generate the platform roadmap, and verify the Definition of Ready for customer delivery. Run after onboarding completes (brownfield step 11, greenfield step 5, migration step 9), whenever platform work lands, and before declaring a project delivery-ready. Drives the platform workflow (onboarded to delivery-ready).
argument-hint: "[derive | roadmap | status | verify-ready]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---

# Plan Platform

Drive the **platform workflow** (onboarded → delivery-ready): maintain the platform
readiness register, generate the roadmap, and verify the Definition of Ready. The register
is the state; the roadmap is a generated view of it; the actual work items are ordinary
HITL changes. Design: `docs/design/platform-bootstrap/` in the HITL source repo.

**Input:** $ARGUMENTS — one of `derive`, `roadmap`, `status`, `verify-ready`. No argument:
if the register does not exist run `derive`; otherwise run `status`.

**The register:** `docs/04-operations/platform-readiness.yaml`. If missing, copy it from
the plugin template first: `cp "$PLUGIN_ROOT/shared/templates/platform-readiness-template.yaml"
docs/04-operations/platform-readiness.yaml` (same `$PLUGIN_ROOT` resolution as the other
templates; from source, `ai/shared/templates/`).

**This workflow never occupies `.hitl/current-change.yaml`.** Roadmap items are ordinary
changes that need the change file; platform progress lives only in the register.

---

## Mode: derive — build or refresh the register

1. Copy the template if the register is missing (above). Read it either way.

2. **Set `project_kind`** (ask if ambiguous): `brownfield`, `greenfield`, or `migration`.
   For migration, flip the `parity` and `cutover` items from `na` to `gap`. For the other
   kinds they stay `na`.

3. **Derive item statuses from the entry artifacts.** Record each source consulted (with
   date) in `derived_from`. By project kind:

   | Kind | Read | What it fills |
   |---|---|---|
   | brownfield | Onboarding step 5 (pipeline) and step 6 (observability) verdicts in the register (written during onboarding); the deployment view; `docs/system-manifest.yaml` | D1/E1/E3 from the pipeline verdict; F1 from the observability survey |
   | greenfield | `docs/01-product/prd.md` NFRs (SLOs → F1 targets; user tiers → environment story; compliance → F3 items); the HLD deployment view from `/hitl:architect-design-system` | Everything starts `gap`; NFRs refine item names with concrete targets |
   | migration | `analysis/source-analysis.md`, the external-docs review brief, the source system's user-facing contracts | Parity items list the concrete contracts to compare; D/E/F as greenfield for the target |

4. **Never downgrade silently.** If a previously `verified` item now looks broken, show the
   recorded evidence and ask before flipping it back to `gap`.

5. Write the register, then show a one-screen summary: per layer, counts of
   verified / gap / accepted_gap / na, and the reds first.

## Mode: roadmap — generate the work plan

1. Read the register. Collect every item with `status: gap`.

2. **Ask the operator for granularity** (default by gap count): fewer than 10 gaps → one
   umbrella issue per layer; 10 or more → one issue per item.

3. Create the GitHub issues. Each issue body must carry:
   - The register item id(s) it closes (`platform_item: D2` in a fenced yaml block)
   - Acceptance criteria derived from the item (what evidence will mark it `verified`)
   - The layer's phase in the platform workflow, so sequencing is visible
   Order issues by workflow phase: Verify → Deliver → Operate (→ Parity → Cutover).

4. Tell the operator: "Each roadmap issue is an ordinary HITL change — pick one up with
   `/hitl:dev-start-change`. When its change merges, re-run `/hitl:ops-plan-platform derive`
   to flip the item to `verified` with the change as evidence."

## Mode: status — render the ribbon

Read the register and render the platform phase ribbon (skip Parity/Cutover unless
`project_kind: migration`):

```
platform: Survey ● · Verify ◐ (D1 ✓ D2 ✗ D3 ✗) · Deliver ○ · Operate ○ · Ready ○
delivery_ready: false — 5 gaps (3 red), 1 waiver (F2, revisit 2026-09-01)
```

List open waivers with owner and revisit date. If any revisit date has passed, flag it
first: a lapsed waiver is treated as an open `gap` by the deploy gate.

## Mode: verify-ready — the Definition of Ready gate

Walk every applicable layer (include parity/cutover only for migration):

1. Every item is `verified` (with non-empty evidence) or `accepted_gap` (with a complete,
   unlapsed waiver: owner + revisit + tier_limit + reason). `na` is valid ONLY for the
   Parity/Cutover items on a non-migration project — never for the canonical D/E/F items,
   and never on a migration. The canonical item set (D1-F3; plus P1-C3 on migration) must
   all be present.
2. The four pillars hold, and you state the evidence for each out loud:
   docs core reviewed and stable · tests including E2E passing · observability established
   and verified · CI/CD stable including one exercised progressive release.
3. If all pass: set `delivery_ready: true`, announce it, and note the statusline chip will
   disappear. If not: list exactly what is missing and stop. **Never set `delivery_ready`
   by hand or on partial evidence** — this flag releases the production deploy gate.

---

## Refusal rules

- `roadmap` before the register exists → "Run `derive` first."
- Asked to mark an item `verified` without evidence → refuse; point at the item's
  acceptance criteria.
- Asked to set `delivery_ready` directly → refuse; run `verify-ready`.
