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
ls .hitl/people/ 2>/dev/null
```

Match `$ARGUMENTS`'s first token against the filenames and the `name:` field, case-insensitively.

**If there is no profile, stop and ask.** Do not invent one from their name, their title, or an
assumption about seniority — a guessed persona is a stereotype with a filename. Offer instead:

> No profile for Kishor yet. Tell me how he likes things — length, whether he wants the reasoning,
> what he needs to decide — and I'll draft to that. I can save it as a profile afterwards if you want.

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
| `notes` | Free text in their own words — read it last and let it override the rows above |

**Compress the reasoning, never the consequence.** If it will not fit, the reasoning goes and the
risk stays. There is always a short way to say something important.

Write in the sender's voice, not HITL's. This goes out under their name.

---

## Step 4 — Hand it over with its provenance

Show the draft, then one line naming what it was based on:

> Drafted from `.hitl/people/kishor.yaml` (written by Kishor). Short, decision-first, no process detail.

If the profile was written *about* the person rather than by them, say that explicitly — the sender
should know the draft is shaped by someone's reading of the recipient, not the recipient's own
stated preference.

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
