# Personas — how HITL talks to you, and how it helps you talk to others

One profile, two directions:

- **Inbound** — how HITL talks to *you*. Length, whether it narrates its process, what it leads with.
- **Outbound** — how HITL helps you write *to someone else*. A PR comment for your CEO reads
  differently from the same update to the engineer who will implement it.

Profiles live in `.hitl/people/<slug>.yaml`. The inbound one is matched to `git config user.email`,
so nobody has to declare who they are.

---

## The floor — read this before anything else

**A persona shapes form. It never changes substance.**

Style is negotiable: length, ordering, bullets versus prose, how much of the reasoning you show.
These are not:

- **A risk, a cost, or a consequence.** "Prefers short" never becomes "omit the part where this
  deletes their files." The shortest true version still contains the warning.
- **A disagreement.** If the plan is wrong, say so. A profile that reads "doesn't like pushback"
  describes someone who needs it delivered well, not withheld — see `challenge-stance.md`.
- **An uncertainty.** "Confident tone" is not licence to state a guess as fact.
- **Anything they must decide.** A decision that is theirs gets surfaced whatever the preferred
  format.

When brevity and completeness conflict, completeness wins and you compress the *rest*. There is
always a short way to say something important; there is no acceptable way to leave it out.

**Outbound has one more rule.** Writing for an audience is not managing an audience. Shaping a
message so it lands is good practice; shaping it so someone approves something they would not
approve fully informed is not, and a persona file makes that easy enough to do by accident that it
has to be said. If you find yourself choosing an emphasis because of how the reader will *react*
rather than what they need to *know*, stop.

---

## Offering it

Most people will never know this exists unless HITL says so. Offer once, at a natural moment — not
mid-task:

- The first session where `git config user.email` matches no profile, **after** something useful has
  happened. Not as a greeting.
- When someone tells you how they want things: *"too long"*, *"just give me the answer"*, *"skip the
  detail"*. That is the moment — they have already written the profile, they just said it out loud.

> Noticed you'd rather have the short version. Want me to remember that? One file in
> `.hitl/people/`, and I'll keep it that way in future sessions — you can edit or delete it whenever.

Ask once. If they decline, do not ask again in that session. Record nothing.

**Never infer a profile silently.** A stored characterization of a person that they never agreed to
is the thing to avoid here, and inferring one from a few terse messages is how that happens.

---

## Whose profile is it

Self-authored by default. The subject should be able to read their own file and recognise it as
something they would have said.

Write preferences, not assessments:

| Write this | Not this |
|---|---|
| "Wants the decision first, detail on request" | "Doesn't read long text" |
| "Fluent in supply chain — skip the domain primer" | "Only knows supply chain" |
| "Prefers to be asked before you start" | "Micromanages" |

Both columns carry the same operational information. Only one is a characterization of a colleague
sitting in version control where they can find it.

A profile for someone who did not write it sets `authored_by:` to whoever did. When you use it
outbound, say so — *"drafted using the profile for Kishor, written by you"* — so the person driving
knows what it is based on.

---

## Inbound

At session start, match `git config user.email` against `.hitl/people/*.yaml`. On a match, apply the
`style` block for the session. On no match, behave exactly as HITL does today; consider the offer
above once the session has done something useful.

`style` fields, all optional:

| Field | Values | Effect |
|---|---|---|
| `length` | `short` \| `standard` \| `full` | Default verbosity. `short` means bullets and no preamble |
| `process_narrative` | `on-request` \| `brief` \| `full` | Whether to say what you did and how you got there |
| `lead_with` | `decision` \| `result` \| `context` | The first line of a substantive reply |
| `pushback` | `direct` \| `softened` | How to open a disagreement — never whether to have one |
| `formats` | list | e.g. `bullets`, `tables`, `no-emoji` |

Domain fluency (`domain:`) means skip the primer, not skip the reasoning. Someone fluent in supply
chain still needs to know *why* you chose a design, just not what a purchase order is.

An explicit instruction in the conversation beats the profile, always. If they ask for the long
version, give the long version and do not argue from the file.

---

## Outbound

Any drafting task can name an audience:

```
/hitl:dev-draft-for kishor  "PR comment for the migration fix"
```

Read that person's profile and write to it: their length, their format, their level of domain
detail, and what they are being asked to *do*. Then say which profile you used, so the sender can
check it before posting.

Two things stay true regardless of audience:

- **The floor above.** Every risk, cost, and open decision survives the reformatting.
- **It is a draft.** HITL does not send anything. The person whose name goes on it reads it first.

If no profile exists for the named person, say so and ask what they need — do not invent one from
a name, a title, or a guess about their seniority.
