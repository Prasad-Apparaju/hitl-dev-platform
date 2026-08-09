# Ship the first version faster: First Pass

**Available now in HITL 2.4.x.** Opt in at the start of any change.

If HITL has felt heavy — too many steps between an idea and something running — First Pass is the
answer. It lets a team ship a working first version without doing every step at full depth, and
without pretending the skipped work doesn't exist.

## The short version

At the start of a change, HITL now offers you a menu. Every step in the plan gets one of four
answers:

| | |
|---|---|
| **do it now** | the default — nothing changes |
| **thin it now** | write the honest-minimal version (a *starter*), enhance later |
| **defer** | not now; a linked fast-follow ticket is created |
| **decline** | not for this change, on the record |

Answer it once, up front, in one pass. Then build.

A Tier-2 refund feature in the [worked example](../examples/first-pass/README.md) declined ROI,
wrote a one-case starter test plan instead of a full one, and declined the deploy step for a manual
v1. Impact analysis, TDD, and the reviews ran as normal. That is a materially shorter path to a
running feature.

## What you cannot skip

This is the part that makes the speed trustworthy rather than a liability.

- **The floor.** Load-bearing steps — which ones depends on the change's tier — can't be waved
  through. You can request a risk-accepted skip, but it needs the accountable role's acknowledgement
  and, where the step maps to a hard gate, a linked waiver. A skip is not a waiver.
- **TDD RED/GREEN.** Marked `no_omit`. You may thin it; you may never defer or decline it.
- **Silence.** Every lightened step is written to a skip ledger with who, why, and when. There is no
  disposition that leaves no trace.

A fail-closed validator (`ci/first-pass/check_skips.py`) enforces this, and a CI gate runs it on
every PR. A silent skip, an unauthorized floor skip, or a TDD omission exits non-zero and is
non-waivable.

## What happens to the work you skipped

It comes back — deliberately.

- **Fast-follows.** A deferral seeds a linked ticket, so it's in the backlog rather than in someone's
  memory.
- **Starters are marked.** An honest-minimal artifact is recorded as `needs-enhancement` with its path,
  so "we wrote a thin one" is visible rather than indistinguishable from "we wrote a real one."
- **Resurfacing.** At the start of a later change, unresolved skips whose area overlaps the new work
  are raised again — politely, escalating by criticality. Skipping something in the billing domain in
  March means hearing about it the next time you touch billing.

## How to use it

Run `/hitl:dev-start-change` as normal. When it shows the step plan, it offers First Pass. Accept,
answer the menu once, and go. It is **opt-in** — the default is still the full plan, and nothing about
the workflow forks. First Pass is the same steps, at their lightest honest setting.

To see it end to end before trying it, read the [worked example](../examples/first-pass/README.md):
a real change record with its ledger, a starter artifact, and the project roll-up.

## What it is not

- **Not a way around the gates.** The floor and the fail-closed validator are the point. If you need
  to cross a hard gate, that is a waiver decision with a named owner, not a disposition on a menu.
- **Not a different workflow.** No fork, no "lite mode" to maintain. The same plan, answered
  differently.
- **Not free.** You are choosing to carry work forward, and HITL will keep reminding you. That is the
  trade: speed now, with the debt written down where the team can see it.

## Why we built it

The complaint we heard was real: teams doing exploratory or low-risk work were paying ceremony costs
sized for high-risk work. The old options were to follow the whole process at full depth or to quietly
cut corners — and quiet corner-cutting is how process falls over, because nobody can see what was
actually done.

First Pass makes the third option explicit: do less, on purpose, on the record.
