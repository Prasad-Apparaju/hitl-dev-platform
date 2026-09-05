# HITL for developers — your first change

You've opened a project that uses HITL. Something told you to read this. Here's the short version:

**HITL makes Claude follow your team's delivery process instead of improvising one.** You still work in Claude Code exactly as before. The difference is that Claude now knows what step you're on, what has to happen before code gets written, and what can't be skipped.

## You don't have to remember any of this

Start the way you always do. Say *"fix the login bug"* and Claude takes it from there — it already knows this project uses HITL, because the project tells it at the start of every session.

What you'll see is Claude proposing an issue and a plan before it writes code, rather than editing files immediately. Agree, and work proceeds normally.

There's a backstop underneath. If Claude tries to edit code with no agreed change, the edit is **blocked**, not merely discouraged. You'll see:

```
HITL BLOCKED: no active change for this project/branch.
```

That's the system working. Run `/hitl:dev-start-change` and carry on.

So the commands below are for when you want to drive rather than be walked. This guide walks one change end to end so you know what to expect.

---

## Before anything else

Check whether the plugin is installed:

```
/hitl:help
```

If you get a command directory, you're set — skip to [Your first change](#your-first-change).

If nothing happens, install it once per machine:

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code. That's the whole setup — it applies to every project on your machine, and the project itself needs no changes from you.

---

## The one command worth knowing

```
/hitl:dev-start-change
```

Claude will offer this itself when you start work. Run it directly when you'd rather begin there — it's the front door for every piece of work: features, bug fixes, refactors, spikes. It does four things:

1. Helps you pick or create the issue you're working on
2. Picks the right workflow for that issue and sizes it (a **tier**, 1–3)
3. Shows you the full ordered plan before anything is written
4. Writes `.hitl/current-change.yaml`, which is what makes Claude follow the plan

You don't need to know which workflow or tier is right. It asks, and it explains its reasoning.

**There are 58 HITL commands. These are the ones worth knowing:**

| Command | When |
|---|---|
| `/hitl:dev-start-change` | Starting any piece of work |
| `/hitl:help` | You don't know which command to use |
| `/hitl:dev-switch-context` | Moving between issues or branches |
| `/hitl:dev-update` | Updating the plugin |
| `/hitl:dev-preferences` | HITL is too wordy or too terse for you |
| `/hitl:dev-draft-for` | Writing a message for one particular person |

The other 52 are for specific roles and moments. HITL invokes what it needs. Don't memorize them.

---

## Your first change

Say you're fixing a bug: the invoice total is wrong when a discount applies.

### 1. Start it

```
/hitl:dev-start-change
```

Claude asks what you're working on. Describe it in your own words, or give it an issue number. If no issue exists yet, it will help you write one — that conversation is normal chat, and nothing is blocked while you have it.

### 2. Agree on the size

For a contained bug fix, HITL proposes **tier 1**. Tier drives how much process applies:

| Tier | Roughly |
|---|---|
| 1 | Contained. One area, reversible, low blast radius |
| 2 | Normal feature work. Crosses a boundary or touches shared code |
| 3 | High-stakes. Security, data migration, anything hard to undo |

If it guesses wrong, say so — you can set the tier yourself, and HITL records that you set it and why.

### 3. Read the plan

HITL shows the whole plan up front. The development workflow is 32 steps across 7 phases:

```
Requirements → Design → Build → Verify → Assess → Ship → Post-Ship
```

A 32-step plan for a one-line bug fix reads heavier than it is:

- Most steps are quick, and many won't apply to your change
- You can right-size the plan before you start — see [First Pass](#first-pass-going-light) below

### 4. Watch the breadcrumb

From here on, every prompt shows where you are:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HITL development ▸ BUG-412 ▸ Requirements ✓  Design ◐  Build ◐  Verify ·  Ship ·
  ▸ Build: Write Failing Test   ·   tier 1

  ✓Issue ✓Impact ◐TestPlan ▶ Write Failing Test ·Green ·Conv ·Rvw1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Top line: workflow, your change, and a ribbon of phases. Middle: the step you're on. Bottom: a window onto the trail — where you've been and what's next.

The glyphs:

| Glyph | Meaning |
|---|---|
| `✓` | Done |
| `▶` | You are here |
| `·` | Still ahead |
| `⊘` | Skipped, and recorded |
| `◐` | Started thin, needs enhancement later |

### 5. Work

Just work. Ask Claude to write the test, fix the bug, run the suite — normally. HITL advances the breadcrumb as steps complete and tells you when something needs to happen before you go further.

Two steps in the Build phase can never be dropped: writing the failing test (`red`) and making it pass (`green`). You can make them thin, but not absent — that's the TDD spine.

### 6. Ship

`deploy` and `promote` are **floor** steps at every tier. They can't be skipped silently. Everything before them can be lightened.

---

## First Pass: going light

A one-line fix shouldn't carry the same process as a payments migration. First Pass is how you right-size the plan, before you start rather than by quietly abandoning it halfway.

When you start a change, you can lighten the plan in one pass. For each step you choose:

| Choice | What happens |
|---|---|
| **Do now** | Normal |
| **Starter** (`◐`) | HITL drafts an honest minimal version now; you enhance it later |
| **Defer** | Skipped now, becomes a fast-follow ticket |
| **Decline** | Skipped deliberately, not coming back |

Three rules make this safe rather than a loophole:

1. **A skip is recorded, never silent.** HITL can always tell you exactly what was skipped, by whom, when, and why.
2. **There's a floor.** Load-bearing steps — irreversible operations, and security work at higher tiers — need an explicit acknowledgement from the accountable person, and sometimes a waiver. You can still proceed; you just can't do it quietly.
3. **Skips come back politely.** When a later change touches the same area, or something goes wrong, HITL reminds you what was skipped there. It's a reminder, not a lecture.

In a First Pass change Claude also talks less, and stops asking permission for routine in-scope reads and edits. Irreversible, out-of-scope, and outward-facing actions still ask.

**Think of it as a thin pass through the whole thing, which you then deepen** — not a faster, worse method.

---

## When HITL stops you

You'll hit this at least once:

```
⛔ HITL — NO ACTIVE CHANGE FOR THIS BRANCH
```

This means Claude is about to edit files with no active change. Run `/hitl:dev-start-change`.

You are **not** blocked from talking. Discussing the problem, reading code, exploring, shaping an issue — all fine. The gate is specifically about writing code with no agreed plan.

Other things you may see:

| Message | What to do |
|---|---|
| `⚠ branch=… ≠ CHANGE-ID` | Your branch and change file disagree. `/hitl:dev-switch-context` |
| A step won't advance | Something the step requires hasn't happened. Claude will say what |
| A skip needs acknowledgement | You're skipping a floor step. Confirm explicitly, or pick a lighter option |

---

## What HITL keeps, and where

Everything lives in `.hitl/` in the repo, and **it is committed on purpose**:

| File | What it is |
|---|---|
| `current-change.yaml` | The active change: issue, tier, workflow, step plan, position |
| `skip-ledger.yaml` | The durable record of what's been skipped across changes |

It's committed because the plan is shared. Your reviewer, your CI, and the next person to touch that code can all see what was decided. Working files and scratch are ignored — only the record is kept.

---

## Common situations

| Situation | Do this |
|---|---|
| Switching to a different issue | `/hitl:dev-switch-context` |
| You don't know which command | `/hitl:help` |
| Picking up someone's half-finished change | Open the branch — the breadcrumb tells you where they stopped |
| You want a lighter plan for this change | Restart intake and right-size it with First Pass |
| HITL feels wrong about your change | Say so. Tier and workflow are proposals, and it records that you overrode it |
| Plugin seems out of date | `/hitl:dev-update` |

---

## The honest summary

HITL is a process your team agreed to, made legible to the AI so it stops improvising a different one each session.

The cost is real: intake takes a few minutes, and some steps feel like overhead on small work. The return is that changes arrive with their requirements, design decisions, tests, and review evidence attached — and that six months later, the reasoning is still there.

If it's too heavy for the work in front of you, that's what First Pass is for. Use it. Being honest about what you skipped is the point; skipping silently is the thing HITL exists to prevent.

---

## Where to go next

| You want | Read |
|---|---|
| A specific scenario (migration, incident, brownfield) | [usage-guide.md](usage-guide.md) |
| Every command, grouped by role | `/hitl:help`, or [command-map.md](command-map.md) |
| To adapt HITL to your team | [customization-guide.md](customization-guide.md) |
| To bring an existing codebase into HITL | `/hitl:dev-start-brownfield` |
