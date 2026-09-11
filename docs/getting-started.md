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

1. Asks for your goal and helps you pick or create the issue for it
2. Picks the right workflow, sizes it (a **tier**, 1–3), and offers **Fast Track** or **Full Scale**
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

Claude asks for the goal in one sentence and what done looks like. Answer in your own words, or give it an issue number. If no issue exists yet, it helps you write one from that sentence. That conversation is normal chat, and nothing is blocked while you have it.

Claude then says back what it understood: what you want, what's in and out of scope, and what counts as done. Correct it if it's wrong. This is the cheapest moment to catch a misread.

### 2. Agree on the size

Claude works out what your change actually reaches (which areas, which interfaces, whether data moves) and proposes a **tier** from that, saying which finding drove it. For a contained bug fix it proposes **tier 1**:

| Tier | Roughly |
|---|---|
| 1 | Contained. One area, reversible, low blast radius |
| 2 | Normal feature work. Crosses a boundary or touches shared code |
| 3 | High-stakes. Security, data migration, anything hard to undo |

If it guesses wrong, say so. You can set the tier yourself, and HITL records that you set it and why.

### 3. Pick Fast Track or Full Scale

The development workflow has 34 steps across 7 phases, plus 4 that appear only when a change needs them (security design, dependency audit, penetration test, performance baseline):

```
Requirements → Design → Build → Verify → Assess → Ship → Post-Ship
```

Your change rarely needs all of them, so HITL offers two sizes of the same plan:

```
  Fast Track   15 steps   what this change's own facts call for
  Full Scale   25 steps   everything that applies to a change of this shape

Recommended: Fast Track. Nothing it drops is protecting something this change touches.
```

It lists what Fast Track leaves out, most consequential first, and tells you what any step protects if you ask. Taking Full Scale instead is fine. See [Fast Track](#fast-track-the-fewest-steps) below for what always stays.

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

<a id="first-pass-going-light"></a>

## Fast Track: the fewest steps

A one-line fix shouldn't carry the same process as a payments migration. Fast Track is the fewest steps that get this change to done, and HITL tells you what it left out.

You don't have to ask for it. For a development change, intake offers Fast Track and Full Scale side by side and recommends one. You can also say "Fast Track" at any point during intake. Shorter workflows, like a docs-only change, skip the choice because they're already short.

**How it picks.** Rules read what your change touches. A step drops out when your change gives it nothing to protect: no interface files, no callers, no UI. Each step it drops carries the finding that dropped it, like "no interface files in this change".

**What always stays:**

| Steps | Rule |
|---|---|
| Write the failing test, make it pass | Always stay. They can be made thin (one test), never dropped |
| Deploy, promote, the retrospective | Dropped only if a named person accepts the risk |
| Integration check (tier 2 and up); design packet, architecture review, QA check and rollout plan (tier 3) | Same: a named person accepts the risk |
| Penetration test (any tier), security design review and dependency audit (tier 3), when the change touches security or dependencies | Same: a named person accepts the risk |

**Lightening further.** After you pick, you can lighten individual steps in one menu:

| Choice | What happens |
|---|---|
| **Keep** | Normal. This is the default |
| **Starter** (`◐`) | HITL drafts an honest minimal version now; you enhance it later |
| **Defer** | Skipped now, becomes a follow-up ticket |
| **Decline** | Skipped deliberately, not coming back |

Three rules make this safe rather than a loophole:

1. **A skip is recorded, never silent.** HITL can always tell you exactly what was left out, by whom, when, and why.
2. **There's a floor.** The steps in the table above need an explicit acknowledgement from the accountable person, and sometimes a waiver. You can still proceed; you just can't do it quietly.
3. **Skips come back politely.** When a later change touches the same area, HITL reminds you what was skipped there. It's a reminder, not a lecture.

When anything is left out, Claude also talks less and stops asking permission for routine reads and edits inside the change's scope. Irreversible, out-of-scope and outward-facing actions still ask.

**Fast means fewer steps, never quieter protection.**

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
| You want a lighter plan for this change | Say "Fast Track" during intake, or restart intake and pick it |
| HITL feels wrong about your change | Say so. Tier and workflow are proposals, and it records that you overrode it |
| Plugin seems out of date | `/hitl:dev-update` |

---

## The honest summary

HITL is a process your team agreed to, made legible to the AI so it stops improvising a different one each session.

The cost is real: intake takes a few minutes, and some steps feel like overhead on small work. The return is that changes arrive with their requirements, design decisions, tests, and review evidence attached — and that six months later, the reasoning is still there.

If it's too heavy for the work in front of you, that's what Fast Track is for. Use it. Being honest about what you skipped is the point; skipping silently is the thing HITL exists to prevent.

---

## Where to go next

| You want | Read |
|---|---|
| A specific scenario (migration, incident, brownfield) | [usage-guide.md](usage-guide.md) |
| Every command, grouped by role | `/hitl:help`, or [command-map.md](command-map.md) |
| To adapt HITL to your team | [customization-guide.md](customization-guide.md) |
| To bring an existing codebase into HITL | `/hitl:dev-start-brownfield` |
