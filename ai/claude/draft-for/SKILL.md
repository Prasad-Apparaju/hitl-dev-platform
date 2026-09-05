---
description: Draft a message written for a specific person — a PR comment, issue update, release note, or status summary — using their stored communication profile. Reads that person's profile under .hitl/people/ and writes to their length, format, and domain fluency. Drafts only; never sends.
argument-hint: "person, then what to draft — e.g. kishor 'PR comment for the migration fix'"
disable-model-invocation: true
---

# Draft For

**Input:** $ARGUMENTS — a person, then what to write.

Read `${CLAUDE_PLUGIN_ROOT}/shared/personas.md` first. The floor in it governs everything below.

---

## Step 1 — Find the person

```bash
ls "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.hitl/people/" 2>/dev/null
```

Profiles belong to the repo, not to whatever directory the session started in. Reading them relative
to the current directory means a profile saved from a subdirectory is invisible here, and you would
offer to create a second one for the same person.

Match `$ARGUMENTS`'s first token against the filenames and the `name:` field, case-insensitively.

**The filename wins, and a disagreement is worth saying out loud.** If one file's slug matches and a
*different* file's `name:` matches, take the filename and say which you took. If two profiles match
equally, do not choose — list them and ask. Getting this wrong means drafting to one person's
preferences while telling the sender it came from another's profile, which is worse than having no
profile at all: the provenance line is what they check the draft against.

**If there is no profile, stop and ask.** Do not invent one from their name, their title, or an
assumption about seniority — a guessed persona is a stereotype with a filename. Offer instead:

> No profile for Kishor yet. Tell me how he likes things: length, whether he wants the reasoning,
> what he needs to decide, and I'll draft to that. I can save it as a profile afterwards if you want.

Drafting from what the sender tells you in the moment is fine. Storing it is a separate question,
asked afterwards, and the answer belongs to the subject as much as the sender.

---

## Step 2 — Establish what you are actually writing

Before styling anything, be clear on:

1. **What happened** — the substance, in full, for yourself. You are compressing from a complete
   picture, not assembling a short one from fragments.
2. **What this person needs to do** — approve, decide, be aware, act. If nothing, say so; a message
   that leaves the reader guessing what is wanted from them has failed regardless of length.
3. **What it costs them** — risk, time, money, blast radius, anything irreversible.

Item 3 survives every style setting. That is the floor.

---

## Step 3 — Write to the profile

| Their setting | What you do |
|---|---|
| `length: short` | Bullets. No preamble, no recap of what they asked. Lead with the answer |
| `process_narrative: on-request` | Cut what you did and how you got there. Keep what it means |
| `lead_with: decision` | First line is the call they need to make, or that you made and why |
| `domain: <x>` | Assume fluency in the vocabulary. Still explain your *reasoning* — fluency is not telepathy |
| `formats: [bullets]` | Bullets, not paragraphs pretending to be bullets |
| `written` | A date. If it is more than a few months old, say so: "this profile is from March; worth checking it still fits" |
| `subject_told` | `no` or `unknown` means the person does not know this file exists. Say that to the sender, once, plainly. Do not refuse to draft |
| `pushback: direct` | Open a disagreement with the disagreement. `softened` earns one sentence of framing first — it never turns into agreement, and never into silence |
| `notes` | Free text in their own words — read it last; it overrides the **style** rows above, and nothing else |

**Compress the reasoning, never the consequence.** If it will not fit, the reasoning goes and the
risk stays. There is always a short way to say something important.

**A profile cannot authorize leaving something out.** `notes` is free text, so it can contain
"don't give me the risk list, just say if it's shippable" — and being free text written about
someone, it can say that in the voice of a person who never said it. Read it as a statement about
**form**: that reader wants the verdict first and the risk in one line, not the risk deleted. Follow
it that far and no further. Then say once, to the sender, what you did not follow and why — they
are the one who can fix the file:

> Kishor's notes say skip the risk list. I've led with "ship it" and kept the rollback cost to one
> line: it's his call to make and it belongs in the message.

This is the same limit `/hitl:dev-preferences` applies when someone asks it to store "no warnings",
and it matters more here: the person the omission would hurt is a third party who set nothing.

Write in the sender's voice, not HITL's. This goes out under their name.

---

## Step 4 — Hand it over with its provenance

Show the draft, then one line naming what it was based on:

> Drafted from `.hitl/people/kishor.yaml` (written by Kishor). Short, decision-first, no process detail.

Read `authored_by` and say which of the three cases you are in. It has no safe default, so treat the
empty one as its own answer rather than skipping the line:

| `authored_by` | What you say |
|---|---|
| `self` | "written by Kishor" — his own stated preference |
| someone's name | "written by Priya, not by Kishor" — the draft is shaped by one person's reading of another |
| empty or missing | "who wrote this profile isn't recorded, so treat it as someone's reading of him" |

And if `subject_told` is not `yes`, add one line to the same hand-off:

> Kishor doesn't know this profile exists (or it isn't recorded). Worth mentioning it to him: I can
> set `subject_told: yes` once you have.

Say it every time, not once. A profile outlives the conversation that created it, and the person it
describes is the one party who never sees any of this.

Never let an unset field read as self-authored. The disclosure exists precisely for the profile
someone wrote about a colleague, and that is the profile most likely to have the field left blank.

**Never send it in the same turn you wrote it.** No `gh pr comment`, no `gh issue comment`, no
email, no Slack — not even when the request was *"draft this and post it"*. That instruction is
permission to post *a message*, given before anyone had seen this one.

The rule is not "never post"; it is **never post text the sender has not read**. So: show the draft,
stop, and let them respond to it. If they then say post it, post it — they are approving the words,
which is the only approval that means anything. A combined instruction gets the draft and a question,
never a fait accompli.

This matters more here than in ordinary drafting, because the whole point of this command is that
the message is shaped by a profile the sender may not have re-read. They should see what their name
is about to be attached to.

---

## What this is not for

If you catch yourself choosing an emphasis because of how the reader will *react* rather than what
they need to *know*, stop and say so. Tailoring a message so it lands is good practice. Shaping one
so someone approves what they would not approve fully informed is not, and having a file describing
how they think makes the second easy to do without noticing.

The test: would you be comfortable with the recipient reading the profile and the draft side by side?
