# Adversarial review — offering it, running it, recording it

An adversarial review is a reviewer given the opposite job from a normal one: **refute this, don't
confirm it.** It runs in a clean context, so it has no attachment to the reasoning that produced the
work, and it reports only what it reproduced by running.

It is offered at two points where work is genuinely finished and still cheap to correct
(`adv_design`, `adv_code`), and required once at `release`, where the blast radius is real.

## Why it is offered early rather than only at the end

The defects this catches are usually *design* defects — a wrong assumption, not a wrong line. The
cost of correcting one rises steeply with how much has been built on top of it. A review after the
design is settled costs the same as one at release and saves far more.

Concretely: the defect that made HITL delete users' files was the assumption that a filename proves
who wrote it. Caught at `adv_design`, that is a one-line change to a plan. Caught at release, it was
two published versions and a data-loss bug in the field.

## What to say when offering

Be brief, say what it costs, and make declining easy. Something like:

> Design's done. Want me to run an adversarial review on it before we build? It takes about ten
> minutes, runs in the background while you keep working, and it's looking for reasons this is
> wrong rather than reasons it's right. Or skip it — I'll note that we did.

Three things that must be true of the offer:

- **Name the cost honestly.** It takes real time. Pretending otherwise makes the next offer easy to
  ignore.
- **Say it runs in the background.** This is the answer to the main objection. The user keeps
  working while it runs; nothing is blocked.
- **Make declining a real option, once.** Ask, accept the answer, move on. Do not ask again in the
  same step.

## When to encourage more strongly

Offer normally, but say what you noticed when the work has the shape that reviews catch:

- it changes something **destructive or irreversible** — deleting, overwriting, migrating, publishing
- it touches **security, auth, or data the user cannot recover**
- the change is **large** or crosses several domains
- you are **reasoning about someone else's behaviour** — what a team will name a file, what an agent
  will do with an instruction. That class of assumption is where this pays best.

One extra sentence is enough: *"This one deletes files in the user's repo, so I'd lean towards
running it."* Say it once. Pressing after a decline is how a useful prompt becomes noise people
learn to dismiss.

## When it is required rather than offered

At `release`, `adversarial_review` is a **floor** step. A release can still proceed without one, but
only through the explicit acknowledgement path — never silently. See
`ci/adversarial/check_review.py`, which the `publish` step runs.

## Declining is recorded, not resisted

`adv_design` and `adv_code` are `ceremony` steps, so declining them is an ordinary skip: recorded in
the skip ledger, with a reason, exactly like any other. That record is the point.

- It resurfaces when a later change touches the same area.
- The release gate can see it, so "no reviews at any point in this change" is visible at the moment
  it matters most.

Record the reason as given. "Small change, low risk" is a legitimate reason and should be written
down as such, not editorialised.

## Running one

Run `/hitl:dev-adversarial-review`. It does everything below.

If you are doing it by hand: spawn a **clean-context** reviewer — a fresh agent with no history of building the thing. Give it:

1. **What changed**, as a diff or a set of paths, and the commit sha.
2. **A refuting brief.** Tell it to assume the work is broken and find how. Name the specific things
   most likely to be wrong, in priority order.
3. **A rule that findings must be reproduced** — the command and the observed output. A finding
   nobody reproduced is a guess, and acting on guesses is how review becomes theatre.
4. **Permission to say it found nothing** in an area. Reviews that must produce findings produce
   invented ones.

Two reviewers with *different* lenses beat two with the same one. Correctness and destructiveness
are a good default pair: they catch different classes and rarely overlap.

**Do not** brief a reviewer with your own conclusions. Stating what you believe is true is how you
get it repeated back to you.

## Recording the result

Write `.hitl/reviews/<change-id>-round<N>.yaml` from the template at
`ai/shared/templates/adversarial-review-record.yaml`. The `reviewed_sha` is load-bearing: the
release gate fails if the code has moved since, which is what stops a review of an early draft
counting for a later one.

Findings are `open`, `fixed`, or `accepted`. Accepting one is a real decision and needs a name
against it — that is what `accepted_by` is for.
