# Explore workflow: requirements (the WHAT)

> Status: **draft v1, 2026-09-08**. Issue #117. PRD FR number to be assigned (see open questions).
> The design (HOW) will live under `docs/design/explore-workflow/`.
> Related: #112 Fix B (absorbed here), First Pass (FR-29, `ai/shared/first-pass/`), right-sizing (#97), #105.

## Problem

HITL has no home for the phase before anyone knows what to build. Someone has a vague idea, wants to try
three things by Friday, and will only understand the repeatable version after building a throwaway one.
Every path into HITL today starts with questions that person cannot answer yet: an issue with a definition
of done, a tier, an impact record, a design approved before source can be edited. Right-sizing shortened
the plan. It did not remove the need to know the destination first.

So people do the PoC outside HITL and lose what they learned, or they fight the gate. Both lose the record,
which is the one thing HITL exists to keep. Research work has the same shape: a hypothesis, rounds of
trying, and a decision at the end. #112 asked for a research workflow; it is the same loop with a
different exit, so it lives here.

## The model

One `explore` workflow in the catalog, for work whose output is knowledge rather than a deployable change.

- **One change per exploration, many tries.** A try is a dated line in a try log, not a change. The change
  file carries the exploration from the first idea to its exit.
- **The loop is try, record, evaluate, decide.** The steps in the plan name exploration, so the breadcrumb
  reads true while someone is trying things.
- **Two exits.** *Graduate*: the output is how to build it repeatably, and the standard workflow starts from
  what was learned. *Conclude*: the output is an analysis, a model, a graph or a decision, and a one-page
  note is the deliverable.
- **Fewer guardrails, stated exactly.** Not "HITL off". What is switched off is listed below, and so is what
  stays and why.
- **Graduation is the product.** The gain is that the standard workflow starts from a better first draft.
  Graduation authors no design and approves nothing.

## Goals

- Start exploring from a one-line idea and a one-line measure, and edit source within a minute.
- Keep one light, append-only record of what was tried, what happened and what it settled.
- Force exactly one decision point, so a PoC that never ends becomes a PoC that was asked.
- Turn what was learned into a requirements draft and a proposed intake for the standard workflow.
- Give a stopped exploration a home: the one-page conclude note is the "ruled out" record #112 wants.
- Keep PoC code from reaching main or production by any path other than graduation.

## Non-goals

- **Not a mode that turns HITL off.** The change file, the branch, the try log and the deploy gate stay.
- **Not a shorter development workflow.** First Pass already does that. This has different steps, not
  fewer of the same, so nothing is skipped and nothing is recorded as skipped.
- **Not a place to ship from.** Code leaves a PoC only by graduating into the standard workflow. "Harden"
  means the standard workflow, never a promotion of the PoC as it stands.
- **Not a new review or approval.** No gate is added; the checkpoint asks a question, it does not approve.

## Requirements

| ID | Requirement | Priority |
|---|---|---|
| **EX-1** | **`explore` is a workflow in the catalog**, chosen at intake like any other, with its own steps, phases and breadcrumb. It is seeded into the change file from the catalog like every other workflow. | Must |
| **EX-2** | **Start asks two things and no more:** the idea in one line, and how you will know it worked, in one line. The second may be "I don't know yet". Both are recorded as written. A GitHub issue still exists, and its body need carry nothing beyond those two lines. | Must |
| **EX-3** | **Source is editable at once.** The edit gate's design-before-source rule does not apply to an `explore` change. The exception is keyed on the workflow id, nothing else, and the rule still holds for every other workflow. A wiring test holds the exception to `explore` only. | Must |
| **EX-4** | **Own branch, and by default its own directory.** An exploration runs on its own branch. By default its code lives under one directory (`poc/<change-id>/` proposed) so "throw away" is one command; one flag at start turns this off for a PoC that must live inside the codebase. | Must |
| **EX-5** | **One try log per exploration**, append-only, one dated line per try: what was tried, what happened, what it settled. Decisions, ruled-out paths, and any change to the idea or the measure go in the same file with a date. No other artifact is required during the exploration. The log is committed with the change so it survives the branch. | Must |
| **EX-6** | **Every session leaves a line.** A session under an `explore` change appends at least one dated line to the try log without being asked. The mechanical part (files touched, tests run) is written by the existing session-summary hook; the "what it settled" part is drafted by the driver and confirmed by the person in one line. Nothing is written as a decision on anyone's behalf. | Must |
| **EX-7** | **One checkpoint, chosen at start.** After a number of sessions or a date, both stored in the change file, the breadcrumb asks one question: graduate, keep going, or stop. "Keep going" sets the next checkpoint. The answer is recorded. Past the checkpoint with no answer, the breadcrumb shows it until one is given. Default when nobody sets it: five sessions (proposed). | Must |
| **EX-8** | **Graduate produces three drafts for a person to edit:** (a) a requirements draft: what the thing must do, learned from what worked; what it must not do, learned from what was ruled out; and the open questions that remain; (b) a proposed intake for the standard workflow, including a tier proposal and a plan from the standard sizing; (c) a disposition for the PoC code: throw away, keep as reference, or harden through the standard workflow. Graduation hands off to `pm-design-feature` or `dev-start-change` with these pre-filled. It authors no design and approves nothing. | Must |
| **EX-9** | **Conclude produces one page:** what was tried, what the measure said, the decision, and what would change the answer. It closes the change. For a research exploration this page is the deliverable. Where the exploration belongs to an epic, the note is what the epic's "spun out / ruled out" record (#112) points at. | Must |
| **EX-10** | **The production deploy gate cannot be passed** by an `explore` change, and an `explore` branch cannot merge to the default branch. Both are checked from the change file, fail closed, and say what to do instead: graduate. | Must |
| **EX-11** | **Security rules stay.** The security question is asked at start. An exploration that touches auth, secrets or personal data gets the security design review in its plan, the same rule as any other change. | Must |
| **EX-12** | **Low friction, by the existing policy.** The First Pass permission policy (routine, reversible, in-scope work proceeds without a prompt; critical actions always prompt) and brief mode apply to `explore` changes by default, keyed on the workflow id. Never `bypassPermissions`. Plain English stays on. | Must |
| **EX-13** | **Nothing is skipped and nothing is recorded as skipped.** Design docs, TDD, reviews and impact analysis are not in this workflow's plan. The skip ledger stays empty; First Pass semantics are not invoked. | Must |
| **EX-14** | **The breadcrumb reads true.** While exploring it shows the try count and the distance to the checkpoint, not a step number that never moves. After the checkpoint it shows which exit was taken. | Should |
| **EX-15** | **Reads the same for a PoC and a research round.** A research exploration usually has a hypothesis and a measure; a PoC usually has a hunch. The workflow does not ask which it is; the measure line and the exit chosen carry the difference. | Should |

## What stays switched on, and why

| Stays | Why |
|---|---|
| The change file and a GitHub issue | tracking, the breadcrumb, and the record the exits read |
| Its own branch and, by default, its own directory | a throwaway never lands on main by accident |
| The production deploy gate and the merge rule (EX-10) | a PoC does not ship |
| The security question and its review (EX-11) | a PoC can still touch secrets or personal data |
| Plain English and brief mode | the record is read by people who were not there |

## Acceptance

- A person starts an `explore` change from a one-line idea and a one-line measure (which may be "I don't
  know yet"), and edits source in the next minute, with no issue body beyond those two lines.
- Every session under the change appends at least one dated line to the try log without being asked.
- The checkpoint fires at the configured point and records the answer. Past it with no answer, the
  breadcrumb shows so.
- Graduate produces the three drafts, and `dev-start-change` on the resulting issue proposes a tier and a plan.
- Conclude produces the one-page note and closes the change.
- The edit gate still blocks source edits on the `development` workflow before design approval, and a
  wiring test proves the exception applies to `explore` only.
- An `explore` change cannot pass the production deploy gate and cannot merge to the default branch.

## Personas

- **The person with an idea** (developer, architect or PM). Wants to try things today and keep what they
  learn, without answering design questions they cannot answer yet.
- **The researcher.** Runs rounds against a measure and needs the decision and its evidence written down once.
- **The future team.** At the standard-workflow intake, or months later, needs to see what was tried, what
  was ruled out and why, without asking anyone.

## Relationship to existing mechanisms (reuse, do not reinvent)

- **The workflow catalog** (`ai/shared/workflows.yaml`, the numberless `tools/workflow-catalog/catalog.yaml`,
  the change-file generator) is where the workflow is defined and seeded. No hand-written step blocks.
- **The edit gate** (`hooks/check-hitl-context.sh` layer 3) gains one keyed exception; nothing else changes.
- **First Pass** supplies the permission policy and brief mode; explore reuses the policy files, not the ledger.
- **Right-sizing** supplies the tier proposal and plan at graduation, run at the standard intake as it is today.
- **The session-summary hook** writes the mechanical try-log line instead of, or as well as, its session record.
- **#112** owns the epic-level "Where this stands" block; the conclude note is what its "ruled out" line points at.
- **#105** decides where a try log lives when a repo is shared with people who should not see explorations.

## Open questions (for design, HOW not WHAT)

- **The plan model has no loop.** Every catalog workflow is a linear list rendered as "Step n / total". Explore
  is try, record, evaluate, decide, repeated. Either the catalog gains a repeatable step (a first) or the
  breadcrumb renders this workflow from the try log and the checkpoint instead of from step numbers (EX-14).
- **What tier an `explore` change carries.** The change file requires a tier, and a tier of 1 or below needs a
  named person. Proposed: a fixed tier the workflow sets by construction, attributed to the person who started
  it, so the sizing rules are never asked a question they cannot answer.
- **Where graduation's tier proposal comes from.** Impact analysis reads the domains a change touches. PoC code
  in `poc/<id>/` touches none of the product's domains, so a proposal "from the PoC code" is really a proposal
  from where the hardened version would land, named by the person at graduation and informed by the PoC.
- **The default directory and the domain boundary.** With `poc/<id>/` on, the allowed paths are that directory.
  With it off, what are they? A PoC inside the codebase that may touch anything is the case the domain-boundary
  hook exists to catch.
- **How the checkpoint counts sessions.** A session counter in the change file, incremented by a session hook.
- **Naming the conclude exit.** `/hitl:dev-conclude` already exists and turns a Slack thread into artifacts.
  The exit keeps the name conclude in the plan; the skill that runs it needs a name that does not collide.
- **The PRD FR number.** FR-29 is the last in the PRD. #105 and #118 both claim FR-30 and neither is in the
  PRD yet. Assign when the row is written.
- **Keying the exception on a workflow id** means a hand-edited change file could put a real change under
  `explore` to dodge the design gate. EX-10 makes that pointless for anything meant to ship; the design should
  say whether anything more is needed.
