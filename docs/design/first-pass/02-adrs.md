# First Pass — Architecture Decision Records

> Status: **accepted + IMPLEMENTED, v1 (2026-07-27)** — decisions for FR-29 (all realized in code; 4 adversarial rounds converged). HLD: [`01-design.md`](01-design.md);
> LLD: [`03-lld.md`](03-lld.md); requirements: [`../../01-product/first-pass/requirements.md`](../../01-product/first-pass/requirements.md).

---

## ADR-1: First Pass is a mode overlay on the existing workflow, not a new workflow

**Context.** HITL has a `development` workflow (31 steps) plus setup/migration/docs workflows, each a `steps[]`
model in `workflows.yaml` seeded into `.hitl/current-change.yaml`. First Pass could be a new "express" workflow
with its own short step list, or an overlay that annotates the existing steps.

**Decision.** An **overlay**. First Pass runs the *same* determined plan; each step simply becomes answerable by
*do now / starter / defer / decline*, bounded by a criticality. No new workflow id, no forked step list.

**Alternatives.** *A separate short workflow.* Cost: two step models to keep in sync; a change that starts
express and needs to deepen would have to migrate workflows; the skip ledger would not map cleanly back to the
full plan. *A per-team config that deletes steps.* Cost: loses the record of what was skipped — the opposite of
the requirement.

**Consequences.** (+) One workflow model; deepening is just working the ledger down; the breadcrumb still shows
the whole plan with skipped steps visible. (−) The `development` workflow must carry criticality metadata even
for teams that never use First Pass (mitigated: `crit` is additive and defaults to `standard`).

---

## ADR-2: Criticality is a per-step, tier-resolved property in `workflows.yaml` (single source)

**Context.** The requirements need a `ceremony | standard | floor` taxonomy, tier-scoped (a step can be
`standard` low, `floor` high). This could live in the skills (prose), in a separate policy file, or in the step
catalog.

**Decision.** Put `crit` on each step in `workflows.yaml`, with an optional compact `crit_by_tier` override.
HITL resolves a step's effective criticality against the change's tier at plan time. The catalog is the single
source; skills and the breadcrumb read it, they do not redefine it.

**Alternatives.** *Hardcode criticality in the skills.* Cost: the drift the workflow-catalog redesign
specifically eliminated — two sources of truth. *A separate `criticality.yaml`.* Cost: a second file to keep
aligned with the step list; the natural home is the step itself.

**Consequences.** (+) No drift; the existing "required Tier 3+/recommended Tier 2+" prose becomes machine-readable
in one place; `dev-update` already remaps `steps[]` by `key`, so criticality travels. (−) `workflows.yaml` grows
a column; the awk parser must keep ignoring unknown keys (it does — it only reads `n/key/label/status/phase`).

---

## ADR-3: One skip-record dialect, shared with the Advisor (FR-28); ledger in the change record + a project roll-up

**Context.** FR-28 already records skips (`{control, owner, reason}`, never silent, skip ≠ waiver). First Pass
records skips for workflow steps. Two schemas would diverge.

**Decision.** Define **one** skip-record schema in shared prose/schema, used by both. First Pass's ledger lives
as `skips[]` in `.hitl/current-change.yaml` (per change) and is rolled up to `.hitl/skip-ledger.yaml` (per
project) for cross-change referability (CR-10).

**Alternatives.** *A First-Pass-only schema.* Cost: two dialects, two record renderers, two things to reconcile
at incident time. *Only the per-change record (no roll-up).* Cost: fails CR-10 — an incident months later
cannot easily find "what did we skip in the change that touched this area."

**Consequences.** (+) One mental model and one record format across features; the roll-up is the durable,
queryable ledger. (−) The roll-up must be maintained on each skip (a small append) and reconciled if a change is
abandoned.

---

## ADR-4: The floor is enforced by an accountable-role ack + a linked waiver — skip ≠ waiver

**Context.** A `floor` step (irreversible-ops, security/compliance at higher tiers, the fail-closed validators)
must be skippable only deliberately and never silently. Many floor steps also correspond to a hard gate (e.g.
`ci/manifest-agentic`, the security review that blocks the PR).

**Decision.** A `floor` skip requires (a) an explicit **risk-accepted** acknowledgment by the step's
**accountable role** (captured in the record with actor + reason), and (b) when the step maps to a fail-closed
gate, a **linked waiver** in the existing waiver mechanism. The skip records the choice; the waiver grants the
gate exception. They are linked by id, never conflated.

**Alternatives.** *Let a floor skip auto-grant the gate exception.* Cost: collapses skip and waiver, removing the
second human authorization exactly where it matters most — the failure this whole feature must avoid. *Forbid
floor skips entirely.* Cost: contradicts the settled "everything skippable, with a floor" decision; teams facing
a genuine, owned risk-acceptance need a recorded path, not a wall.

**Consequences.** (+) The framework's hard guarantees survive First Pass; the audit trail shows both the choice
and the authorized exception. (−) A floor skip is deliberately heavier (two artifacts) — which is the point.

---

## ADR-5: Resurfacing generalizes challenge-stance TODO Deferral and adds triggers; it never challenges mid-build

**Context.** `challenge-stance.md` already defers-and-records in the design phase and surfaces a TODO list before
ship, and it explicitly says *do not apply challenge mode in execution phases*. First Pass needs active,
escalating resurfacing (CR-8) without nagging a team mid-build.

**Decision.** Resurfacing **extends** TODO Deferral onto the shared ledger and adds two triggers beyond
"before ship": the **next change touching the same area** and an **incident/postmortem**. Intensity escalates by
criticality. During execution, First Pass **records quietly** and does not re-litigate; persuasion happens at
design-time, at the next change, and at incident — the natural decision boundaries.

**Alternatives.** *Resurface continuously (including mid-build).* Cost: violates challenge-stance's execution
rule and becomes the ceremony teams are escaping. *Passive ledger only (surface on request).* Cost: fails the
"teeth" the settled decision requires — deferred rigor rots unseen.

**Consequences.** (+) Consistent with the existing stance; the record has teeth at the moments that matter.
(−) The "next change touches the same area" trigger needs overlap detection (LLD §6.2) — imperfect in v1
(domain + path intersection), flagged as a follow-on.

---

## ADR-6: Starters are honest-minimal and always marked `needs-enhancement`; no fabrication

**Context.** CR-13 wants HITL to give the team *something* rather than a gap, but a fabricated full artifact
(e.g. invented detailed acceptance criteria) gives false confidence — worse than an honest gap.

**Decision.** A starter is a **true minimal bar**, not a synthesized full artifact, and is always emitted
**marked `needs-enhancement`**. Canonical case: the acceptance-criteria starter is the single criterion *"a
working version of the system exists and runs."* A per-step **starter registry** defines which steps have a
sensible starter and what it is; steps without one fall back to defer/decline.

**Alternatives.** *AI-draft the full artifact.* Cost: plausible-but-wrong content presented as done — the exact
failure mode the Advisor review taught us to avoid. *No starters (skip = omit only).* Cost: loses the "give them
something to iterate on" value the user asked for.

**Consequences.** (+) Honest, iteration-friendly; reuses HITL's AI-drafts-human-refines model without
over-claiming. (−) The registry is curated, not universal — some steps only offer defer/decline.

---

## ADR-7: Permission friction maps to a scoped `acceptEdits`-style policy with a critical-action prompt list — not `bypassPermissions`

**Context.** CR-15 wants routine, reversible, in-scope reads/edits to proceed without per-action prompts, while
critical/irreversible/outward actions still prompt. Claude Code exposes permission modes (`default`,
`acceptEdits`, `bypassPermissions`, …) and allow/deny lists.

**Decision.** First Pass adopts a **scoped `acceptEdits`-style policy**: auto-allow reads and edits **within the
change's scope** (the project working tree / declared domain), and keep a **critical-action list that always
prompts** — deletes outside scope, deploys, external sends, force-push, secret access, and anything outside the
project/change scope. First Pass **does not** use `bypassPermissions` (which would drop the critical prompts too).

**Alternatives.** *Use `bypassPermissions` for speed.* Cost: removes the critical prompts — becomes "bypass all
safety," which the requirements explicitly forbid. *Change nothing (keep default prompts).* Cost: the friction
PMs are complaining about remains.

**Consequences.** (+) Friction removed from ceremony, kept on the critical — the floor logic applied to tool
permissions. (−) The critical-action list must be defined and kept current against the Claude Code permission
model (LLD §9; flagged as an open boundary). Scope detection reuses the existing domain-boundary hook.

---

## ADR-8: Keep the breadcrumb parser trivial — only `status: skipped` on steps; skip detail lives in the ledger

**Context.** The breadcrumb is rendered by a dependency-free awk parser over single-line YAML flow-maps in
`workflow.steps[]`; the workflow-catalog redesign deliberately made renderer drift "structurally impossible."
Putting rich skip detail on each step would either break the parser or complicate it.

**Decision.** Add two values — `skipped` (deferred/declined — nothing produced) and `starter` (a minimal
`needs-enhancement` artifact was produced) — to the step `status` enum, each rendered with its own glyph
(`⊘` skipped, `◐` starter, alongside `✓` done · `▶` current · `·` open). All skip detail (disposition, actor,
reason, refs) lives in the separate `skips[]` ledger keyed by step `key`. The awk parser keeps reading only
`n/key/label/status/phase` — it just maps two more `status` values to two more glyphs (a trivial change,
no structural parsing added).

**Alternatives.** *Embed skip detail per step.* Cost: multi-field or multi-line steps break the awk parser or
force a real YAML dependency in the renderers — reintroducing the drift the redesign removed. *A parallel
skipped-steps list only (no status).* Cost: the breadcrumb could not show a step as skipped inline.

**Consequences.** (+) The breadcrumb shows the whole plan with skips visible, parser unchanged; ledger carries
the detail. (−) Two places to keep consistent (step `status` ↔ ledger entry) — reconciled by the driver and a
lint.
