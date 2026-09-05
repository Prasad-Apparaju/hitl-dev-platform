# Verification review — offering it, running it, recording it

A verification review is a reviewer with no stake in the work, given a checklist and told to run
it. It runs in a clean context, so it has no attachment to the reasoning that produced the work,
and it reports what it verified by running, one page, then stops. "It is right" is a real answer.

It is offered at two points where work is genuinely finished and still cheap to correct
(`adv_design`, `adv_code`), and required once at `release`, where the blast radius is real.

## What it replaced, and why

Until 2.10 this was an adversarial review: the reviewer was told to assume the work was broken and
find how. That fixed reviews that confirmed everything, and overshot. Five rounds on one design
during the right-sizing work told the story: the adversarial round returned 1,588 lines and eleven
"criticals" against a 128-line plan, several of them unreproducible; three later rounds with a
constrained brief returned one page each and found a design contradiction that made the feature
unbuildable, a shipped defect, and a floor step that could never activate. The constraints found
more, not less. So the constraints stayed and the attack instruction went.

What did not change: independence, the clean context, evidence by running, findings put to a
person before anything is fixed, and the release gate.

## Why it is offered early rather than only at the end

The defects this catches are usually *design* defects — a wrong assumption, not a wrong line. The
cost of correcting one rises steeply with how much has been built on top of it. A review after the
design is settled costs the same as one at release and saves far more.

Concretely: the defect that made HITL delete users' files was the assumption that a filename proves
who wrote it. Caught at `adv_design`, that is a one-line change to a plan. Caught at release, it was
two published versions and a data-loss bug in the field.

## What to say when offering

Be brief, say what it costs, and make declining easy. Something like:

> Design's done. Want me to run a verification review on it before we build? A round takes about
> ten minutes and runs in the background while you keep working — it checks the design against
> what it claims, case by case, and comes back with one page. If something fails there may be a
> second round, and I'll show you what came back before I change anything. Or skip it — I'll note
> that we did.

Things that must be true of the offer:

- **Name the cost honestly.** It takes real time. Pretending otherwise makes the next offer easy to
  ignore.
- **Say it runs in the background.** This is the answer to the main objection.
- **Make declining a real option, once.** Ask, accept the answer, move on. Do not ask again in the
  same step.
- **Say ten minutes is a round, not the review.** A change that needs three rounds costs a working
  day. Quoting the round as the whole is how the estimate stops being believed.
- **Say they will see what failed before anything changes.**

## The brief, in one paragraph

One page. A numbered checklist: each item is one claim the work makes and how to check it, by
running where possible. Report a table of checks with the command and the result — pass, fail, or
unknown — then at most five points, ranked, each classed **stops it working**, **worth deciding**,
or **minor**. Verify numbers against the data rather than trusting the prose, and say what you
checked. Do not design the fix; point at the gap. About fifteen tool calls, or the checklist,
whichever ends first. If it is right, say so and stop.

## Presenting what came back

Findings go to the person who owns the change **before** they are fixed, because a finding can be
real, reproducible, and still not this change's problem. Deciding that is scope, and scope is
theirs.

Put every **stops it working** and **worth deciding** to them one at a time; summarise the minor
ones. For each: what fails, in a sentence, in their words — what it costs if it ships — and your
recommendation. Never the raw `claim` field, never YAML, never a term the reviewer coined without
glossing it. The reviewer wrote for you; you write for them.

They answer **fix**, **accept**, or **defer**. Accept and defer both need their name in
`accepted_by`, which is what the gate checks and what makes the decision theirs rather than yours.
Anything they have not answered stays `open`.

Keep it off the critical path. They were promised background work; a triage list they can answer
when they get to it honours that, and a blocking prompt does not.

## The lens catalog

A lens is the question a reviewer's checklist is built around. Two reviewers with the same lens
check the same things twice, so a round is a *set* of lenses, not a headcount.

**Use these ids verbatim in the record's `lens:` field.** The gate groups records by lens to catch
two reviewers filed under one, and it can only do that if the names are stable. Inventing
`consequence-2` for a second consequence reviewer defeats it.

### The base pair — always, and one of them depends on what you just finished

| Phase finished | Lens | Asks |
|---|---|---|
| design | `fitness` | Does this design satisfy the requirement it claims to? Check each case the requirement names |
| code | `correctness` | Does it do what it claims? Run it on the inputs the claims cover, and one past each edge |
| release | `upgrade` | What happens to someone who already has the old version? To the next person installing fresh? Install both |
| any | `consequence` | What does this destroy, expose, or make unrecoverable? Run the destructive path against a copy |

`consequence` runs in every phase. Blast radius does not depend on which phase you are in.

### Conditional lenses — add the ones the change earns

| Lens | Asks | Add it when |
|---|---|---|
| `security` | What does this let someone do that they should not? Try it | profile `security`; auth, secrets, permissions, a trust boundary |
| `data` | What is unrecoverable if this runs wrong once? Run it wrong once, on a copy | in-place rewrites, backfills, schema changes |
| `scalability` | What happens at a hundred times the rows, users, or calls? Measure one order up | tag `perf`; a new per-row or per-user path |
| `operability` | When this breaks at 3am, how would anyone know, and how do you undo it? Break it and look | tag `infra`; tier 2+; a new failure mode |
| `compatibility` | What breaks in repos or clients you do not control? Check one | anything shipped outward |
| `bypass` | This adds a check. How do you get around it? Try the obvious ways | the change introduces a gate, validator, or hook |
| `interfaces` | Does this hold at the boundary it crosses? Call it from the other side | multi-domain scope; a facade contract changes |
| `user` | Someone does this in normal use without reading the docs. What happens? Do that | a user-facing surface, a new command |
| `cost` | What does this spend, per call and per month? Count | new external calls, storage, or model usage |

`user` and `upgrade` are in this list because of what they caught here, not for symmetry. HITL 2.7.1
exists because a round finally looked at the upgrade path, and the feedback panel found in ordinary
use what four review rounds and an external model had missed.

### Older names

`destructiveness` → `consequence`. `migration` → `data`. `install` → `upgrade`. `perf` →
`scalability`. Records using them still validate; the gate resolves them to the canonical id.

### How many

Two is the floor and the usual answer. Add a third or fourth when the change plainly earns it; past
that you are buying rounds, not coverage, and each lens is another ten minutes and another table to
read. **At `release`, do not go below two.** The review is a floor step there, and a release looked
at through one lens is that step satisfied with very little in it. This is a rule you keep, not one
the gate enforces (#92).

### Choosing is the user's, not yours

Put the plan in the offer (see above) and let them cut or add. Two rules:

- **They pick where to look, never what will be found.** "Add a security lens" is theirs. "Skip
  consequence, the migration is fine" is pre-deciding the thing the review exists to test — take
  the deselection, and do not pass the reasoning to the reviewer.
- **A lens they drop goes in the record's `scope`**, e.g. *"security lens offered and declined"*, so
  that if something later goes wrong there it is visible that a lens for it was on the table. Not in
  `skips[]` — that records lightened workflow steps, keyed by step, and a lens is not a step.

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

At `release`, `adversarial_review` (the step keeps its key; its name is Verification Review) is a
**floor** step: required by default, and skippable only by recording an acknowledgement with a name
against it. In the change file:

```yaml
skips:
  - step: adversarial_review
    disposition: decline
    reason: "sev-1 hotfix, restoring a known-good build"
    ack_by: "who decided this"
    waiver_ref: "GH-123"        # required: this gate is fail-closed, so a name alone is not enough
```

`waiver_ref` points at wherever your team records accepted risk — an issue, a waiver file, an
incident. The rule is the framework's own: a floor skip that maps to a fail-closed gate needs a
linked waiver, because a skip is not a waiver. Skipping the release review at 2am is allowed; doing
it without anyone signing for it is not.

`ci/adversarial/check_review.py` — run by the `gates` step via `/hitl:dev-validate` — honours that
and lets the release through, printing `REVIEW_WAIVED` with the name and reason. Without `ack_by` it
is not an acknowledgement and the gate still blocks — an unattributed waiver is the absence of a
decision, written down.

There is deliberately a path here. A gate with no escape is one that gets deleted from the process
the first time it is inconvenient at 2am, and then it protects nothing.

## Where the gate actually binds

**The gate binds on whatever script actually publishes your project** — and it has to be wired
there, in your repo, by you. For HITL itself that is `scripts/release.sh` in the plugin repo, which
runs the gate and refuses on a non-zero exit, on no active change, and on an active change whose
workflow is not `release`. You have no such script unless you add the same call to yours:

```bash
python3 ci/adversarial/check_review.py || exit 2
```

That placement is the point. Everything else here is advisory: the workflow steps are instructions a
model follows, `/hitl:dev-validate` only checks when a release change happens to be active, and the
edit hook does not cover Bash. **The only thing that binds is a check on the action that publishes.**

`gates` (step 4) runs before `adversarial_review` (step 5), so its release-gate section will report
`REVIEW_MISSING` on a fresh release. That is sequencing, not a fault — but do not let it become
"gates are red on releases, carry on". The check that decides is the one in `release.sh`.

## Declining is recorded, not resisted

`adv_design` and `adv_code` are `ceremony` steps, so declining them is an ordinary skip: recorded in
the skip ledger, with a reason, exactly like any other. That record is the point.

- It resurfaces when a later change touches the same area.
- The release gate can see it, so "no reviews at any point in this change" is visible at the moment
  it matters most.

Record the reason as given. "Small change, low risk" is a legitimate reason and should be written
down as such, not editorialised.

## Running one

Run `/hitl:dev-verification-review`. It does everything below.

If you are doing it by hand: spawn a **clean-context** reviewer — a fresh agent with no history of
building the thing. Give it:

1. **What changed**, as a diff or a set of paths, and the commit sha.
2. **A checklist.** Each claim the work makes, and how to check it by running. In priority order.
3. **The evidence rule** — a result is the command and the observed output; a check that could not
   be run is unknown, never a pass.
4. **The shape and the size** — a table of checks, at most five ranked points in three classes, one
   page, and permission to say everything passed.

Two reviewers with *different* lenses beat two with the same one. Correctness and consequence are a
good default pair: they check different things and rarely overlap.

**Do not** brief a reviewer with your own conclusions. Stating what you believe is true is how you
get it repeated back to you.

## Recording the result

Write `.hitl/reviews/<change-id>-round<N>-<lens>.yaml` (one per reviewer) from the template at
`ai/shared/templates/verification-review-record.yaml`. The `reviewed_sha` is load-bearing: the
release gate fails if the code has moved since, which is what stops a review of an early draft
counting for a later one. The `checks` table is what makes the record a verification rather than an
opinion. A finding that answers for a failed check names it in `check:`, in the same record; a
failed check nobody answered for contradicts a `verified` verdict and the gate blocks.

Findings are `open`, `fixed`, or `accepted`. Accepting one is a real decision and needs a name
against it — that is what `accepted_by` is for, and the name has to belong to someone who actually
said so. Collect it at triage; do not supply it yourself. A finding nobody has answered is `open`,
and the gate blocking on it is the system working.
