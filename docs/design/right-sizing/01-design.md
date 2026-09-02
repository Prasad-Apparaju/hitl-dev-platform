# Right-sizing a change

**Status:** agreed, ready to build · **Issue:** #97

## What happens

```mermaid
flowchart TB
  A["1. you say what you want"] --> B["2. HITL restates it, you confirm"]
  B --> C["3. impact analysis runs"]
  C --> D["4. tier, then fast track or full scale"]
  D --> E["5. you adjust"]
  E --> F["6. build"]
  F -.->|"something is discovered"| D
  classDef pick fill:#d4edda,stroke:#3a3
  classDef gen fill:#e7e0f5,stroke:#75a
  class D,E pick
  class C gen
```

Six steps. The plan does not exist until step 3 has run, and it is not final once it does.

## 1. You say what you want

Unchanged. Intake asks, and asks again if it is unclear.

## 2. HITL restates it, you confirm

Before anything is read or planned, HITL writes back what it understood:

| | |
|---|---|
| what you want | the ask, corrected |
| in scope | what this change covers |
| out of scope | what it explicitly does not, so it can be pointed at later |
| definition of done | what counts as delivered, in the requester's terms |

Length comes from the change, not from a cap. A one-line fix has a one-line definition of done. A
feature has a list. You confirm or correct all of it.

This is the cheapest moment to catch a misread. Everything downstream is derived from this text, so
a misunderstanding here becomes a wrong impact analysis and then a wrong plan, and a wrong plan is
harder to argue with than a wrong sentence because it looks considered.

### What the definition of done is for

It is not the plan restated. The plan is how the work gets done. This is what counts as delivered,
in the requester's own words, agreed before anyone starts.

The two are written at different moments by different people and answer different questions, so
neither can stand in for the other. A completed plan does not prove the thing does what was asked.
A met definition of done does not prove it was built properly.

Three properties:

**It is attributed.** Who agreed, and when. An agreement with nobody's name on it is not one.

**Vague lines are flagged, not blocked.** "The system should be fast" cannot be shown to be met.
HITL says so, offers a sharper version, and takes whatever answer comes back. If the vague line
stays, the record says it was flagged as unverifiable and accepted anyway, with a name and a date.
That record does not require HITL to have been right about the wording, only to have asked.

**Changing it after work starts is a scope change,** routed through the existing scope-change review
rather than edited in place.

### Acceptance criteria are translated from it

Not written alongside it. The definition of done is the anchor, in the requester's language. The
criteria are the checkable translation, written once the work is understood well enough to say how
each line gets proved. Every criterion has to be something QA can actually test, because QA is who
reads them. "Works properly" is not a criterion. "Returns 400 with a message naming the missing
field" is.

Every definition-of-done line must name at least one criterion that satisfies it. A line with none
stops progress before Build begins, until it either gets a criterion or is explicitly marked as not
verifiable in this change, with a reason and a name.

The link is read in the other direction at the end. QA already verifies each criterion at the QA
post-handoff verification step and can block promotion. Because the criteria point back, those
results report against the definition of done rather than against a list of criteria the requester
never wrote: four of the five lines are verified, one was never tested.

### Where the requirement is written

| where | when |
|---|---|
| the issue description | always; HITL edits it directly, since you just approved the wording |
| the change file | always |
| the PRD | appended when the area has one; created only when the workflow is a feature |

A fix or a chore never creates a PRD. Both destinations depend on which area owns the change, so
they are written after step 3 answers that, even though the text is agreed here.

### The change file starts here as a stub

Intake writes a stub: change id, branch, the confirmed requirement and its definition of done. No
tier, no workflow steps, no plan, because none of those exist yet.

That matters for one reason beyond tidiness: the gate that blocks source edits looks for a change
file, so the stub is what protects the intake conversation itself. Step 3 fills in the rest.

The generator refuses a planless change file today. It has to learn to write a stub, and anything
reading `tier` or `workflow.steps` early has to tolerate their absence.

## 3. Impact analysis runs

**Impact analysis is not a step in the plan. It is the thing that produces the plan.** It always
runs, it cannot be ticked off, and there is no plan yet to put it in.

### It runs on every workflow, asking different questions

Impact analysis is not a manifest lookup. It is "what does this touch, and what does it demand". The
manifest is only one place that answer lives, and which questions to ask depends on the work:

| workflow | what it is asking | where it reads |
|---|---|---|
| development | what does this change reach | the manifest, the design docs, the code |
| brownfield | what security posture and CI/CD compliance exist already, and what is missing | the codebase itself |
| migration | what does changing the tech stack cost, what breaks, what has no equivalent | the source system |
| prd | what has to be created: repo, docs, structure | the product doc and the empty ground |

The three that have no manifest are not degraded cases. They are the workflows that exist to produce
one, and asking what that will take is exactly the analysis worth doing.

The output is the same shape everywhere: findings, provenance, and what the rules concluded. So
everything downstream works unchanged, because it keys off findings rather than off the manifest.

**Which area does this belong to.** The workflow was already chosen at intake, as a routing decision.
Step 3 does not revisit it; it answers which area of the system owns the work.

If no area owns it, HITL says so and asks one question: is this genuinely outside the system, like a
demo script or a CI config, or is the manifest missing an area? Outside means the fast track is the
locked floor and nothing else. Missing means HITL will not pretend it sized correctly, and offers
full scale or asks you to name the area.

**What does this change reach.** Read top-down, cheapest source first: the manifest entry, then the
design docs it points at, then source, and only where the declared picture is thin or the change
clearly goes beyond it.

The distinction that matters is between what the *area* has and what this *change* touches. An area
having tests is not a fact about your change. Your change altering behaviour those tests cover is.
Rules read the second kind, never the first, for the reason in step 4.

### What it writes

Its own file, referenced from the change file. The change file names it; if the named record is
missing or empty, that blocks. A second artifact is only safe when something notices its absence,
and data that quietly stops being written is this repo's recurring defect.

The record holds three things:

| | |
|---|---|
| the findings | which area owns it or none, what this change reaches, what depends on it, which interfaces and events are involved, what tests cover the behaviour being changed |
| provenance, per finding | manifest, design doc, or source, so a hand-written field is never presented as if it came from the code |
| what the rules concluded | which step each finding put in or left out, and why |

The third part is what makes the retrospective's feedback loop possible. You cannot ask whether a
rule was right if you never recorded what it decided.

### It also writes the acceptance criteria

The definition of done was agreed at step 2 in the requester's language. The criteria are its
checkable translation, and this is the first moment the work is understood well enough to write them.

They belong here for a structural reason, not a tidy one. Step 2 blocks progress before Build until
every definition-of-done line names a criterion. Nothing in the 34-step plan produces criteria today,
and any step that did could be unticked, which would leave a block with no producer and a stall with
no next command. Impact analysis always runs and cannot be removed, so the check can never fire
without its producer having run.

### What this costs elsewhere

`impact` is currently a step in the catalog, marked floor at tier 3. Taking it out of the plan means:

- the development workflow drops from 34 steps to 33, then back to 34 when the retrospective is
  added as a step (see progress-and-retro)
- the tier 3 locked floor goes ten → nine without `impact`, then back to ten with the retrospective
  locked. Tier 1 goes four → five, tier 2 five → six
- the check that every floor step must appear in the plan stops expecting it
- `apply-change` loses its step 3, because the work has already happened
- every step after it renumbers, so `workflow-steps.md` and anything else citing a step by number
  has to be updated in the same pass

## 4. Tier, then fast track or full scale

### The tier is decided here, once

Not at intake. HITL proposes a tier from what impact analysis found, and a human confirms or
corrects it exactly as before, with the same attribution rules.

This is the root fix for the change that started this. `FIRECRAWL_API_KEY` in an issue title is what
tiered a shell script up to a three and a half hour path. Impact analysis would have found a file in
no area, with no dependents and no callers. The evidence existed; it just arrived after the decision
that needed it. Deciding once, on evidence, means a word in the issue text can no longer outvote
what the code says.

Anything that reads the tier before the plan exists has to be found and checked as part of this.

### The choice appears only where there is something to size

Every workflow gets an impact analysis. Not every workflow gets offered two options.

HITL has eight workflows, from 34 steps down to five. Offering a fast track on a five-step process
adds a confirmation and a decision to the lightest path in the system, which is the ceremony this
work exists to remove. So the choice appears where the plan is long enough for the two options to
differ meaningfully; in practice that is `development` (34) and `platform` (17). Elsewhere the
analysis runs, and the plan is simply the plan.

### Three sets, two predicates

| | | decided by |
|---|---|---|
| every step the workflow defines | a list, not an offer | the catalog |
| the ones that **apply** to this change | this is **full scale** | `engages` |
| the ones **needed now** | this is **fast track** | `needed_now` |

Full scale is not every step. Offering a Figma comparison on a backend change, or a training plan on
a one-line fix, makes the thorough option look stupid and teaches people to distrust it.

**`engages` answers: does this step make sense here at all?** A Figma comparison needs interface
files in the change.

**`needed_now` answers: does it have to happen before this ships?** A step is in the fast track when
impact analysis found something *this change reaches* that the step protects. Three dependent areas
found, integration is in. Nothing depends on it, integration is out. A published interface is
touched, compatibility is in.

Both read the change's reach, never the area's paperwork. That distinction is the whole point. Rules
keyed to whether an area *has* a design doc, dependents and tests give identical answers for every
change to that area, so a one-line fix in the best-documented part of the system would draw the
longest plan, and documenting an area would make every future change to it more expensive. A new
feature in a new area would draw almost nothing, because it has no history to match on. Both
backwards.

### What is locked

- **The tier floor**, plus the test-first cycle, plus the retrospective. Five steps at tier 1, six at
  tier 2, ten at tier 3. These cannot be unticked.
- **Anything `needed_now` put in.** These can be unticked, but not with one click. See step 5.

Risk is handled by the tier and by nothing else. A risky change is a high tier, a high tier locks
more, and the gap between the two options closes on its own. There is no second list of dangerous
categories, because a rule matching the word `API_KEY` is what caused this in the first place.

Both options are shown with the difference between them, and one line saying which is recommended
and why. The recommendation is advice. Taking full scale instead is not recorded.

### Where a rule is silent

Rules first, judgement second. Where a rule answers, that is the answer, and it is testable. Where
no rule fits, HITL decides and says so in one line, such as "dropping the Figma comparison, this
change touches no interface files." The override is shown rather than buried, so a bad call gets
argued with and becomes a rule next time.

### The catalog data

Each step carries three lines. Two exist already and are unchanged:

| line | what it is |
|---|---|
| `protects` | the sentence shown next to the step |
| `forgo_cost` | high, medium or low; orders the steps that are not in the fast track |
| `engages` + `needed_now` | the two rules above |

`engages` exists on all 38 steps and does not yet do its job. Twenty-one development steps say
`always`, which decides nothing. Five key off profiles, which never reach the runtime, so they can
never fire. Four match folder patterns, which is guesswork about what a path means. Only three key
off a real fact, and one off a tag. Every one gets rewritten, and `needed_now` is authored alongside
it in the same pass. Some will be wrong at first, and step 6 is how they get corrected.

## 5. You adjust

The list is tickable. A step put there by the tier floor cannot be unticked. Anything else can.

Two ways a step leaves the plan, and they are recorded differently because they are different acts:

| | recorded as |
|---|---|
| **the fast track did not include it** | HITL's decision, with the rule that decided it as the reason. No prompt. |
| **you unticked it** | your decision, with a disposition and your reason, asked at that moment |

Unticking a step that `needed_now` put in opens one short prompt asking which of the three (a thin
version now, later with a ticket, or not at all) and why. That is what the pull request checker
reads, and it refuses to pass without both. Asking in the moment costs an interruption per removal,
which is bearable only because the fast track is usually right.

Locked steps are shown, greyed, with their reason next to them. Hiding them would mean you cannot
see what HITL decided on your behalf.

## 6. Build, and re-plan as you learn

**The plan is not final.** Implementation and testing discover things the plan did not account for,
and the plan changes when they do.

HITL proposes a **delta**, never the whole list again: what it now thinks should be added, and the
finding that caused it. You deselect from the delta the same way, must-haves stay locked, removals
are recorded the same way.

A step the fast track left out is not gone. It is not-yet, and it comes back when a finding calls
for it.

### When it interrupts

| | |
|---|---|
| **a finding makes a dropped step load-bearing** | raised immediately; carrying on is the expensive mistake |
| **everything else** | accumulates and is put to you at the next phase move, as one small delta |

This is also what makes the rest of this design tolerable. Being approximately right at step 4 is
good enough when step 4 can happen again. Most of the risk in a wrong fast track is not that
something is missed, but that it is missed permanently.

## What gets deleted

Already done, in `8561080`: `rank.py`, `plan_select.py`, `test_rank.py`, `selection.md`,
`right-sizing.md` and `first-pass-choices.md`, the intake changes that called them, and the version
stamps. The catalog data was kept and is guarded by two wiring tests.

## What we are watching after this ships

**The friction is back on the light path.** Asking for a reason at each untick is the same cost named
in #97: the cheap path asks for paperwork while the expensive one asks for nothing. It only stays
cheap if the fast track is right often enough that unticking is rare. If the rules are poor, this
shows up as people quietly taking full scale because it asks fewer questions.

**Every change now runs an impact analysis up front.** That is what it takes for the plan to be
built on what is actually there. If it is slow on small changes, the fix is to make the top-down read
stop earlier, not to make it skippable, because a skippable plan-generator leaves no plan.

## Not in scope

- Changing what the floor protects.
- Making profiles and tags filter the plan.
