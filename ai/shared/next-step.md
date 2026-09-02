# Closing a step: say what comes next

Applies to every skill that carries out a workflow step.

A person finishing a step should never have to work out what happens now. The change file already
holds the answer: the next step's label, its phase, and the command that runs it.

## The close

Four lines at most, after the step's own output:

```
✅ RED is done.

Next: Verify RED — check the tests fail for the reason you expect.
      → /hitl:dev-tdd verify   (or say "go" and I'll run it)
```

Three parts and nothing else. What finished. What is next, in words that say what it achieves rather
than repeating its label. How to start it.

## Getting the next step

Read `.hitl/current-change.yaml`. Take the first step after the current one whose status is `open`,
and use its `command`. Skipped and starter steps are not next; they were already decided.

Three kinds of `command`, and they are not interchangeable:

| value | say |
|---|---|
| a command, e.g. `dev-tdd` | `→ /hitl:dev-tdd` |
| `manual` | this one is yours, there is no command; say what to do |
| `guided` | `say "go" and I'll walk it with you` |

Never render `manual` or `guided` as a command. `/hitl:manual` does not exist, and sending someone
to look for it costs more trust than saying nothing would have.

If the change file has no `command` for the next step, say what the step is and offer to walk it.
Five workflows declare no commands at all, so this is normal, not an error.

## When the step was the last one

Say so, and name what closes the change rather than inventing a next step.

## What not to do

**Do not list the remaining steps.** The statusline already carries the trail. A closing message that
reprints the plan is the thing that made people stop reading step output.

**Do not restate what the step did.** It just happened; they were there.

**Do not ask permission to continue.** Say what is next and stop. If they want it, they will say so.
An "shall I proceed?" at the end of every step is thirty-one interruptions in a change.

**Do not use this to nudge.** If the next step is one they chose to skip, it is not next. Skips
resurface through the mechanism built for it, in the voice defined in
`ai/shared/first-pass/language.md`, not by a step close pretending it forgot.
