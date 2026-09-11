# Fewer steps, on the record: Fast Track

**Available since HITL 2.9.0, named Fast Track in 2.13.0.** You don't turn it on; intake offers it.

If HITL has felt heavy (too many steps between an idea and something running), Fast Track is the
answer. It gives each change the fewest steps that get it to done, and tells you what it left out.

## The short version

Tell Claude your goal in one sentence and what done looks like. HITL works out what the change
reaches, proposes a tier, and offers two sizes of the same plan:

```
  Fast Track   15 steps   what this change's own facts call for
  Full Scale   25 steps   everything that applies to a change of this shape

Recommended: Fast Track. Nothing it drops is protecting something this change touches.
```

Pick one and build. You can say "Fast Track" at any point during intake. Taking Full Scale is fine
and isn't recorded as anything.

After you pick, you can lighten individual steps further in one menu:

| | |
|---|---|
| **keep** | the default; nothing changes |
| **starter** | write the honest-minimal version now, enhance later |
| **defer** | not now; a linked follow-up ticket is created |
| **decline** | not for this change, on the record |

A tier-2 refund feature in the [worked example](../examples/first-pass/README.md) declined ROI,
wrote a one-case starter test plan instead of a full one, and declined the deploy step for a manual
v1. Impact analysis, the tests and the reviews ran as normal.

## What always stays

- **The failing test and making it pass.** They can be made thin, never dropped.
- **Deploy, promote and the retrospective**, at every tier, and more steps at higher tiers (the
  integration check from tier 2; the design packet, architecture review, QA check and rollout plan
  at tier 3). When a change touches security or dependencies, the penetration test is protected at
  any tier, and the security design review and dependency audit at tier 3. These are dropped only if a named person accepts the risk and, where the step maps to
  a hard gate, a waiver is linked. A skip is not a waiver.
- **The record.** Every step left out is written to a skip ledger with who, why and when, including
  the ones the rules left out, with the finding that decided it. Nothing leaves no trace.

A fail-closed validator (`ci/first-pass/check_skips.py`) enforces this, and a CI gate runs it on
every PR. A silent skip, an unauthorized skip of a protected step, or dropping the test cycle exits
non-zero and can't be waived.

## What happens to the work you skipped

It comes back, deliberately.

- **Follow-ups.** A deferral seeds a linked ticket, so it's in the backlog rather than in someone's
  memory.
- **Starters are marked.** A minimal artifact is recorded as `needs-enhancement` with its path, so
  "we wrote a thin one" is visible rather than indistinguishable from "we wrote a real one."
- **Resurfacing.** At the start of a later change, unresolved skips in the same area are raised
  again, politely. Skipping something in billing in March means hearing about it the next time you
  touch billing.

## How to use it

Run `/hitl:dev-start-change`, or just describe the work and Claude starts it. For a development
change, intake shows both sizes and recommends one. Shorter workflows, like a docs-only change,
skip the choice because they're already short.

To see it end to end, read the [worked example](../examples/first-pass/README.md): a real change
record with its ledger, a starter artifact, and the project roll-up.

## What it is not

- **Not a way around the gates.** The protected steps and the fail-closed validator are the point.
  Crossing a hard gate is a waiver decision with a named owner, not a menu choice.
- **Not a different workflow.** No fork, no "lite mode" to maintain. The same plan, sized to the
  change.
- **Not quieter protection.** Fast means fewer steps. What it leaves out stays on the record, and
  HITL keeps reminding you.

## Why we built it

Teams doing low-risk work were paying ceremony costs sized for high-risk work. The old options were
to follow the whole process at full depth or to quietly cut corners, and quiet corner-cutting is how
process falls over, because nobody can see what was actually done.

Fast Track makes the third option the default: do less, on purpose, on the record.

## The name

In 2.4.0 this was a mode you had to ask for, then called First Pass, where you picked steps to skip
from a menu. Since 2.9.0 it's the smaller of two sizes of the same plan, set by rules from what the
change touches. People weren't finding it under three different names, so 2.13.0 settled on the two
that appear on screen: Fast Track and Full Scale.
