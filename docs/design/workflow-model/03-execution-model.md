# Execution Model: how a change's plan is determined and enforced

**Status:** Design (branch `design/workflow-model`).
**Companion docs:** [00-requirements.md](00-requirements.md) · [01-design.md](01-design.md) · [02-rollout.md](02-rollout.md)

This is the heart of the model. It supersedes the idea of a workflow as a *fixed pipeline*: a
change's actual plan is **determined by impact analysis, iteratively with the human**, then
**enforced**, with a **floor** that can't be tailored away.

---

## 1. The plan is an output of impact analysis, not a precondition

You can't reliably classify a change up front. The true type, tier, affected scope, and the steps
it needs only become clear after analysing the ask, reading the code, and iterating with the
requester. So:

- **Up front → a *proposal*.** From the issue text/labels, the AI proposes "this looks like a *Tech
  Change* on the payments domain." Cheap, useful, **not binding**.
- **Impact analysis → the *determination*.** The AI + human iterate; impact analysis confirms/changes
  the type, sets the tier, **adds change-specific steps**, and produces this change's
  **required-evidence** set.
- **`current-change.yaml` → the *governing plan*.** The self-describing change file records the
  *actual* tailored plan (which may extend the template). That file, not the workflow name, governs.

> The workflow/type is a **refinable proposal and a starting template, not a fixed pipeline.**

## 2. Four layers

| Layer | Fixed / flexible | What it is |
|---|---|---|
| **Floor** | **Fixed (non-skippable)** | The steps/evidence a change *must* have (§3). Cannot be analysed or tailored away. |
| **Template** | **Stable default** | A named workflow = a default plan + default required-evidence for a kind of change. The seed + shared vocabulary. |
| **Tailoring** | **Dynamic** | Impact analysis (AI + human) adds/removes steps and finalises *this change's* required-evidence. |
| **Enforcement** | **Fixed** | The final required-evidence is enforced by the gates/hooks; the floor cannot be waived. |

This deliberately sits **between** rigid pipelines (too brittle, the original complaint) and "no
workflows" (too dangerous, loses repeatability and lets the AI *under-scope*). Add up freely; tailor
down only deliberately and visibly (§4).

## 3. The floor (non-skippable): conditional on what the change touches

| # | Floor item | Applies to |
|---|---|---|
| 1 | **Impact analysis** | **every** change, *unconditional anchor*; it determines which of 2–9 apply |
| 2 | **UX design artifact** (Claude Design, a Figma file, or at minimum a screenshot/mock) | user-facing / UX-involved changes; **PM-owned** |
| 3 | **Docs-reconciled** (no drift) | changes touching documented behaviour |
| 4 | **Writing test cases** (plan + RED) | code / behaviour changes |
| 5 | **Unit testing** (exist + pass) | code / behaviour changes |
| 6 | **Code review** | code changes |
| 7 | **Security review** | auth / payments / data changes |
| 8 | **Post-deploy checks** (catch prod breakage) | changes that reach prod |
| 9 | **Regression** | could-regress changes, *hard-skip; **deferrable** (§6)* |

Only **#1 is unconditional**; impact analysis decides which of #2–9 are in *this* change's floor. A
config tweak floors at {impact analysis, docs-reconciled}; a user-facing payments change floors at the
full set. **The floor scales with the change, but never to zero.**

> **UX design artifact (#2).** For any change a user can see, the PM owns a concrete UX artifact before
> build: ideally a Claude Design output or a Figma file, at minimum an annotated screenshot or mock
> attached to the issue. The *form* is tiered (full design preferred, screenshot the floor); the
> artifact's *existence* is the gate. It is required-evidence (`ux_artifact`) and is what the Ship-phase
> Figma/UX comparison checks the built UI against. Whether it is hard-floor or architect-waiverable for
> trivial UI tweaks is an open sub-decision (see [02-rollout.md §5](02-rollout.md)).

## 4. Tailoring & the informed-skip mechanism

You can **add** steps freely. **Removing** a non-floor step is **informed consent, recorded**, never
a silent omission and never a hard wall.

### Tiered skip authority
"Ask the user" is too permissive, so skip authority is tiered:

| Tier | Examples | Who may skip |
|---|---|---|
| **Floor, never skippable** | the §3 items (for the change's shape) | nobody; the harness says *"can't be skipped,"* not *"here's what you miss"* |
| **Skip needs architect/TA** | a review round, rollout plan, a Tier-3 gate | dev **proposes**, architect **approves** (recorded) |
| **Dev may skip (informed)** | ROI estimate, training stub, Figma compare | the requester, after the harness shows the cost |

### How it works
1. **Each step carries a `rationale` / "what you miss" string** in the catalog, so the harness can
   state the cost vividly.
2. The **AI runs the skip conversation in the planning skill** (hooks can't talk), explains the
   cost, requires a *substantive* reason ("skip" alone is rejected).
3. The decision is a **structured waiver**: `{ step, decided_by, role, when, reason, risk_acknowledged }`
   → posted as a **GitHub issue comment** (human audit trail) **and** written to
   `current-change.yaml` (`status: skipped` + reason, so the breadcrumb and gates see it).
4. The **enforcement hook respects an *authorised, recorded* waiver** and blocks an unauthorised or
   floor skip. (The hook checks "is there a valid waiver for this missing evidence?"; it doesn't ask.)

### Skip-fatigue defenses (so "flexible" ≠ "optional")
- **Require a substantive reason**; reject lazy/empty ones.
- **Route high-stakes skips to a *different* person** (architect), self-approval is the corruption vector.
- **Make skips loud**, surfaced in the PR description, the breadcrumb, and a per-change skip log.
- **Track skip *patterns***. A team that always skips step X is a signal: fix the step (too heavy) or
  flag the team (cutting corners). Skips become process telemetry, not silent exceptions.

## 5. Enforcement is `required_evidence`, not the tag/name

The dependable mechanism already exists: **`required_evidence` in `current-change.yaml`, enforced by
the gates/hooks** (schema today: `tests_red`, `tests_green`, `spec_conformance_review`, `qa_review`,
`downstream_impact_brief`, `rollout_plan`, `ops_review`, to be extended, e.g. `docs_reconciled`,
`ux_artifact`).

```
type/tag    →  PROPOSES a required-evidence set
impact analysis (AI + human)  →  CONFIRMS / EXTENDS it for THIS change
required_evidence + gates/hooks  →  ENFORCE it (can't close the change without it / a valid waiver)
```

A bare **tag enforces nothing, but neither does a *workflow name*** if chosen wrong. The guarantee is
the *enforced required-evidence*, regardless of how it was proposed. (This is why the Security
"workflow vs tag" debate dissolves: what matters is that the security gates land in this change's
enforced required-evidence.)

## 6. Two special rules

- **Docs-reconciled is a (near-)universal closing gate.** Any change touching documented behaviour
  cannot be marked complete until the manifest/LLD/ADRs match reality. Drift-prevention is *floor*,
  not a step a light tier can skip. This answers the standing "where does doc-update happen for every
  change?" concern.
- **Deferred regression ≠ dropped.** Regression may be deferred to keep a change moving, but only as a
  **tracked ticket (owner + due) linked to the change**, that **blocks "change complete"** (you may
  canary-deploy with it pending; you may not call the change *done*), or an explicit, recorded
  architect risk-acceptance. It stays visible as `regression: deferred → #ticket` until it lands.
  *(Confirmed 2026-06-23.)*

## 7. What this does to the taxonomy

It **demotes it.** The named tiers, **5 workflows + 6 profiles + 5 tags** (locked 2026-06-23; see
[01-design.md §4](01-design.md)), are the **proposer + stakeholder vocabulary**, not the thing that
guarantees correctness. Because rigor lives in impact-analysis → required-evidence → enforcement + the
floor, the *only* reason a thing is a workflow vs a profile vs a tag is **legibility and classifier
accuracy**: a **workflow** has a different step *sequence*, a **profile** is a recognizable preset over
the shared spine, a **tag** only tunes required-evidence. This is exactly why the "Security: workflow
or tag?" debate dissolved into "Security is a *profile*": the security gates land in the enforced
required-evidence either way.

## 8. New catalog metadata this implies

Each step gains (Phase 1 / Phase 3):
- `floor: true | false` (+ the condition under which it floors, e.g. `when: code | prod | docs`);
- `skip_authority: never | architect | dev`;
- `rationale` / `skip_warning`, the "what you miss" text for the skip dialogue;
- (already planned) `command`, `role`, `ownership`.

These are what let the planning skill conduct the informed-skip conversation and the hook enforce it.
