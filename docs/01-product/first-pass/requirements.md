# First Pass — Requirements (the WHAT)

> Status: **draft, v1 (2026-07-27)** — EPIC TBD, PRD **FR-29**. A right-sized, **thin-whole-first**
> (skip-with-record) delivery mode that extends the tier system: a thin pass through the whole, then deepen.
> The design (HOW) will live under `docs/design/first-pass/`.
> Related: the workflow model (shipped as 2.x), the Agentic Advisor skip pattern (FR-28), tiers, and waivers.

## Problem

HITL's value is its ceremonies — the 31-step change workflow, the gates, the reviews. But not every step earns
its cost on every change, and **some teams (PMs especially) want to ship a basic version fast and iterate**,
rather than pay full ceremony up front. Today the choices are all-or-nothing: run the whole workflow, or step
outside HITL and lose the record entirely. Teams that step outside lose exactly what HITL exists to give them —
a durable, referable trail of what was decided and what was deferred.

The ask: after HITL understands what the team is trying to accomplish and determines the workflow, let the team
**skip the steps they choose to**, **proceed to building**, and **keep a polite, durable record** of what was
skipped — so they can come back to it, decline it deliberately, or be reminded of it if something later goes
wrong. Iterate the first version through **fast-follows / follow-up tickets**.

The name reflects the intent: this is not a *faster* method that implies the full method is "slow" — it is a
**first pass** at v1 fidelity that you **deepen** over subsequent passes.

## The model (seven principles)

1. **Skip-with-record, never skip-in-silence.** A skipped step is always recorded — never quietly dropped.
   A skip is a *record of a choice*, not a granted exception (a skip ≠ a waiver — see FR-28 / #10).
2. **The floor is protected.** Most steps are freely skippable; a small, tier-scoped set of **load-bearing**
   steps (irreversible-ops, security/compliance at higher tiers, the fail-closed validators) can still be
   skipped — but only via an explicit, **authorized risk-accepted** record, never a light or silent one.
3. **First Pass extends tiers, it does not replace them.** HITL still tiers the change; First Pass lets a team
   skip *within or below* what the tier prescribes, on their own recorded authority, bounded by the floor.
4. **The record has teeth.** Skipped steps resurface **politely and proactively** at defined trigger points
   (the follow-up ticket, the next change touching the same area, and incident/postmortem), with an intensity
   that scales with the step's criticality. The intent is to *convince*, never to coerce or shame.
5. **Ship v1, iterate deliberately.** First Pass is built for "basic version now, refine later": a deferred step
   becomes a tracked follow-up, so the first version ships without the deferred rigor being lost.
6. **Prefer a starter over an omission.** Where HITL can, First Pass **gives the team 'something'** — an *honest
   minimal* starter flagged *needs-enhancement* — rather than a blank gap. The starter is a true minimal bar,
   not a fabricated full artifact: for acceptance criteria it is simply *"a working version of the system"*; for
   a test plan, a skeleton. The fast-follow becomes *enhance this*, not *create this from nothing*.
7. **Get out of the way.** In First Pass, HITL keeps communication **brief** and friction **low**: terse prompts,
   minimal narration, and no permission ceremony for routine, reversible, in-workspace work — it prompts only
   for the genuinely critical. Momentum, not ceremony, is the point; the record — not the chatter — is what
   must be complete.

## Alignment with HITL's delivery philosophy

HITL already **thinks holistically and implements incrementally** — the whole is reasoned through in
requirements + design, then delivered in execution slices. First Pass **leverages** that philosophy rather than
breaking it: it is a **thin pass through the whole** (a *walking skeleton* — the AC starter "a working system,"
a skeleton design), followed by incremental deepening via slices *and* the fast-follow enhancements of the
starters and deferrals. You never stop thinking about the whole; you capture it at v1 fidelity first and deepen it.

This gives the disposition rule its principle:

- For the **holistic-thinking** steps (requirements, design), prefer a **starter** (think-the-whole-thin) over
  an omission — a thin whole beats an un-thought whole.
- Reserve **skip** (defer / decline) for **execution and ceremony overhead** that a given change genuinely does
  not need.
- The **floor** (CR-2/CR-5) is the part of the holistic thinking that must not even be thinned below a bar —
  safety, security, irreversibility.

## Goals

- Let a team right-size a specific change by skipping steps HITL surfaces as skippable, and proceed to build.
- Make every skip a durable, neutral-language record: what, who, why, when, and deferred-vs-declined.
- Protect a load-bearing floor so First Pass can never silently omit a safety/security/irreversible gate.
- Resurface skipped choices proactively, politely, and proportionately — so deferred rigor is not forgotten.
- Support iteration via fast-follows / follow-up tickets seeded from the skip record.
- Let HITL, at any later point (especially an incident), point precisely to what was skipped, by whom, and why.

## Non-goals

- **Not** a global "turn HITL off" switch. First Pass is per-step, opt-in, and always leaves a record; the
  default for any change remains the full determined plan.
- **Not** a replacement for tiers, or a second parallel ceremony-scaling system.
- **Not** silent auto-skipping. HITL never skips a step on the team's behalf; the team chooses, HITL records.
- **Not** a way to bypass a hard CI gate without the corresponding authorized waiver (skip ≠ waiver; a floor
  skip that maps to a fail-closed gate still needs the existing human-authored waiver).
- **Not** a judgment engine. Records and reminders are respectful and non-blaming by construction.
- **Not** "bypass all permissions." Reduced permission friction (CR-15) applies only to routine, reversible,
  in-scope work; critical/irreversible/outward actions still prompt. Low friction is not no guardrails.
- **Not** a quality claim on starters. A `starter` artifact (CR-13) is explicitly marked *needs-enhancement*;
  it is a head start to iterate on, never presented as complete or approved.

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| **CR-1** | **First Pass is a mode of the determined workflow.** After HITL determines the step plan for a change (as today, tiered), the team may mark individual steps to skip and proceed to build. First Pass is opt-in per step; the unmarked default is the full plan. **Amended 2026-08-13 — tier-gated batch decline.** At **tier 0 or 1 only**, HITL may present the `ceremony` steps pre-marked as `decline` with a reason filled in, so one confirmation records the set. This is the sole exception to "the unmarked default is the full plan", and it is bounded: it applies to `ceremony` steps only (no `standard`, no `floor`, no `no_omit`); it requires an explicit tier 0/1 declaration carrying `tier_set_by` and `tier_reason`; **nothing is written until a human confirms**, so declining to answer still runs the full plan; and each resulting record carries the confirming person as `actor`, never the agent. Rationale: at tier 0/1 the ceremony set is the same every time, and requiring nine identical manual declines per bug fix was the friction that pushed teams out of the process entirely — which costs more governance than the exception does. | Must |
| **CR-2** | **Every workflow step carries a criticality.** Each step is one of `ceremony` (freely skippable), `standard` (skippable with a light record), or `floor` (load-bearing — skippable only via an authorized risk-accepted record). Criticality is **tier-scoped**: a step may be `standard` at a low tier and `floor` at a high one. HITL surfaces each step's criticality when presenting the plan. | Must |
| **CR-3** | **A skip is always recorded, never silent.** Each skip records `{step, criticality, actor, reason, timestamp, disposition: deferred / declined / starter}` in the change record. A step cannot be skipped without producing this record. | Must |
| **CR-4** | **A skip is not a waiver.** A recorded skip grants no exception to any downstream hard gate. A `floor` skip that corresponds to a fail-closed gate still requires the existing human-authored waiver (owner + reason + revisit) — the two are linked, not conflated. | Must |
| **CR-5** | **The floor is protected.** A `floor` step can never be skipped by the light path. Skipping it requires an explicit **risk-accepted** acknowledgment by the **accountable role** for that step (e.g., a security gate → the security/TA owner), captured in the record. HITL will not let a `floor` step be omitted without it. | Must |
| **CR-6** | **Disposition: defer, decline, or starter.** A skipped step's disposition is explicit and recorded: **defer** (intend to return), **decline** (choose never to do it), or **starter** (accept an honest minimal version now, enhance later — CR-13). Disposition is later changeable (a declined step can be re-opened; a starter can be enhanced). A step may **restrict** its allowed dispositions: a step marked *no-omit* (e.g. the TDD RED/GREEN steps — test-first is a HITL cornerstone) may be thinned to a **starter** but never deferred or declined. | Must |
| **CR-7** | **Deferred steps become fast-follows.** A deferred step seeds a **follow-up ticket**, linked to the originating change and the skip record, so the deferred work is tracked as a backlog item rather than lost. The team may group or defer ticket creation, but the linkage is preserved. | Must |
| **CR-8** | **Skips resurface proactively, at defined triggers.** HITL raises recorded skips — politely, escalating by criticality — at: (a) the follow-up ticket, (b) the **next change touching the same code/domain**, and (c) an **incident/postmortem** on the affected area. The intent is to convince, never to block or blame. | Must |
| **CR-9** | **Polite, non-judgmental language throughout.** The skip record and every resurfacing use respectful, neutral language when recording and respectful-but-persuasive language when reminding. No blaming, no shaming; reconciled with the framework's challenge-stance (surface the risk, respect the choice). | Must |
| **CR-10** | **The skip ledger is durable and referable.** All skips for a change (and across a project) are queryable. At any later point — especially an incident — HITL can point to exactly which steps were skipped, their disposition, actor, reason, and timestamp. | Must |
| **CR-11** | **Authority scales with criticality.** Who may skip a step scales with its criticality: `ceremony`/`standard` skips are the team's to make; a `floor` skip requires the accountable role's acknowledgment (CR-5). The actor is always captured. | Should |
| **CR-12** | **Iteration is first-class.** First Pass explicitly supports "ship a basic v1, then iterate": the skip ledger is the deferred-rigor backlog, and fast-follows / follow-up tickets are the mechanism to work it down over subsequent changes. | Should |
| **CR-13** | **Prefer a starter over an omission.** For an artifact-producing step, First Pass offers a **`starter`** disposition: an **honest minimal** version now — never a fabricated full artifact — marked **needs-enhancement** and recorded. For **acceptance criteria** the starter is the single criterion **"a working version of the system exists and runs"** (a v1 "it works" bar); the specific behavioral / edge-case criteria are deferred to the enhancement pass. The fast-follow (CR-7) *enhances* the starter. A step with no honest minimal starter falls back to defer/decline. | Should |
| **CR-14** | **Brief communication, menu-driven.** In First Pass, HITL keeps interaction terse — minimal narration, short prompts, no restating of what it is about to do, and it does not re-ask a question already answered. Dispositions are collected through a **single menu** presented once (the whole plan, each step's allowed options pre-set by its criticality) — not a step-by-step interview. It surfaces only what the team must decide (a disposition, a floor acknowledgment) and the record it kept. Verbosity is not the governance; the record is. | Should |
| **CR-15** | **Minimal permission friction — critical-only prompts.** In First Pass, routine, reversible, **in-scope** operations (reading the project, editing project files within the change's scope) proceed **without per-action permission prompts**. HITL still prompts for the genuinely **critical**: irreversible or destructive actions, anything outside the project/change scope, and outward-facing actions (deploys, external sends, force-push, secret access). This mirrors the floor (CR-2/CR-5): friction is removed from ceremony, never from the critical. First Pass **never** means "bypass all safety." | Should |
| **CR-16** | **The plan visibly reflects First Pass.** The workflow breadcrumb shows the **whole** plan (steps are never hidden) with skipped and starter steps **visually distinct** from done / current / open — so anyone reading the trail sees at a glance what was lightened, and a later-resolved starter/deferral shows as completed. | Should |

## Personas

- **PM (primary).** Wants a basic version or enhancement shipped fast to validate, then iterate — without losing the governance trail or being blocked by ceremony that does not fit this change.
- **Engineering lead / accountable role.** Owns the floor: must acknowledge any load-bearing skip and is the one HITL reminds when a deferred step's risk becomes relevant.
- **The future team (including future-self).** At the next change or an incident, needs to see exactly what prior rigor was skipped and why, stated plainly.

## Relationship to existing mechanisms (reuse, don't reinvent)

- **The Agentic Advisor skip (FR-28)** is the working prototype for the record: `{control, owner, reason}`,
  never silent, skip ≠ waiver, neutral language. This feature generalizes that pattern from one feature to the
  whole workflow. The skip-record schema should be a shared concept, not a second dialect.
- **Tiers** already scale ceremony by risk; First Pass extends them (CR-2 / principle 3), it does not duplicate them.
- **Waivers (#10)** remain the mechanism for a hard-gate exception; a floor skip links to a waiver (CR-4).
- **The workflow model** (`workflows.yaml` + `workflow.steps[]` in `.hitl/current-change.yaml`) is where step
  criticality and skip state live; the change-record schema gains a skip ledger.
- **The issue/ticket model** provides fast-follows (CR-7).

## Open questions (for the design phase — HOW, not WHAT)

- The exact per-step criticality assignment across the 31-step workflow, per tier (design + `workflows.yaml`).
- The skip-record and ledger schema, and where it lives in `.hitl/current-change.yaml` + a project-level roll-up.
- The "next change touching the same area" trigger — how HITL detects the overlap (domain/manifest/path).
- The resurfacing language templates and escalation ladder.
- Whether declined (permanent) skips ever expire or are periodically re-offered.
- How First Pass interacts with the strict-mode gate / merge gates that hard-block today.
- The exact **critical-action boundary** for CR-15 (which operations always prompt) and how it maps onto the
  Claude Code permission model (permission modes / allow-lists) without weakening the floor.
- Which steps have a sensible **auto-draft starter** (CR-13) and the quality bar / marking for a starter artifact.
