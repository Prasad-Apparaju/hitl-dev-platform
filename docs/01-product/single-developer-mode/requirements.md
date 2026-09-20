# Single Developer Mode: Requirements

> **What** HITL must do when one developer covers every engineering role and the only other people
> are an architect and a PM: resolve each step's role to a real person once, stop pretending handoffs
> exist where they do not, substitute independence where it is lost and say so in the record, and
> batch the questions the two other people must answer instead of stopping for each one. Product
> one-liner: **FR-33** in the [PRD](../prd.md) backlog table (§5.7); ticket
> [#135](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/135), status Backlog. The
> **how** (team file schema, plan resolution, substitution table, the open-questions record) is a
> design package at `docs/design/single-developer-mode/`, not started. Status: **draft v1
> (2026-09-19)**, written from a customer team's one-week measurement of HITL (§1) and the
> conversation that followed. Related: FR-29 (First Pass), the right-sizing design, EPIC
> [#22](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/22) (metrics),
> [#112](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/112) (where this stands),
> [#118](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/118) (team pulse).

## 1. Problem

The development workflow gives every change the same 31 steps, and every step carries a role: PM,
Architect, Developer, QA or Ops. Right-sizing decides which steps a change needs. Nothing decides who
is there to do them. HITL has no record of the team, so on a team of one developer plus an architect
and a PM, every QA and Ops step still reads as a handoff to someone, every review step still assumes
a second reader exists, and the developer is asked at each of those boundaries. The developer either
plays five roles in turn, which is theatre, or skips the same steps with a record on every change,
which is noise. Neither is what a one-person engineering team needs, and the tier machinery cannot
help because team shape is not change size.

**Evidence.** A customer team measured one week of HITL use from their session transcripts, on a
repository where one developer ran every step:

| Measure | Value |
|---|---|
| Changes landed | 6, five of them at tier 3 |
| Elapsed, all six | about 280 hours |
| Waiting on a human | 88% of elapsed |
| Agent active | about 35 hours |
| Structured questions the agent stopped on | 119 calls, 198 questions |
| Clock spent waiting for those answers | about 34.5 hours |
| Longest single unanswered question | over 8 hours |
| Human turns that answered an agent question | 24% of 455 |

Most of the waiting is one person asleep or elsewhere, which is the cost of any human-in-the-loop
process. The number that is HITL's to own is the last but two: the clock spent waiting for an answer
to a question the agent chose to ask was about equal to the agent's total working time. Every hour
of work cost an hour of a question sitting unanswered, and most of those questions were asked at
role boundaries that did not exist on that team.

The same measurement showed the process finding real defects at the review and test-first steps.
Design verification carried the densest work on three changes. Architecture review found guards that
could not fail. Test-first was re-cut on three changes because guards would not go red. The mode
must keep that, and lose the waiting.

**Delivery surface.** A committed team file in the product repo, plan resolution in the existing
intake, records in the existing change file, and the existing validators. No new workflow, no UI.

## 2. Users

| User | What they need |
|---|---|
| **Developer** (also QA, also Ops) | To declare the team once, run a change end to end without being handed off to themselves, and have their questions for the architect and PM collected rather than stopping on each |
| **Architect** (the customer's technical architect or technical advisor) | To see what reached them, what was verified by an agent in their absence, and what was assumed in their name, in one place per phase |
| **PM** | Acceptance, ROI and the requirements decisions, plus the assumptions made on their behalf, without being pulled into engineering steps |
| **HITL maintainer** | One catalog, one intake, one change file; the mode as a resolution rule, not a fork |

## 3. Scope

**In scope.** The `development` workflow, the three onboarding skills that would write the team file,
`start-change` plan resolution, the step records in the change file, the skills that end a turn on a
question, and the metric fields the mode must leave behind for EPIC #22.

**Out of scope.** The `platform` workflow and migration workflows (one-time checklists with their own
waiver model), any change to the catalog's steps or their floor, any per-person persona profile
(that is `ai/shared/personas.md`), and any posting to a tracker on someone's behalf.

**Slices.**

| Slice | Delivers | Requirements |
|---|---|---|
| 1 Team shape | The team file, role resolution in the plan, substitution with records, floor unchanged | SD-1 to SD-4, SD-9 |
| 2 No false handoffs | No stop at a self or none boundary; questions for the other two people batched with assumption-and-proceed | SD-5, SD-6 |
| 3 Visibility | Per-phase digest for the architect and PM; metric fields; step timestamps | SD-7, SD-8, SD-10 |

## 4. Goals

1. A one-developer team runs a tier 3 change with no turn ending on a question for a role that
   resolves to the developer.
2. Every review step that lost its second reader carries a record naming what substituted for it.
3. The architect and PM each get one packet per phase, not a stream of interruptions, and can list
   everything that was assumed in their name.
4. The protected floor is exactly as strong as before. The mode removes no step and softens no gate.
5. EPIC #22 can report, from the records alone, how much of a repository's verification was
   self-verified and how much clock the agent's questions cost.

## 5. Requirements

Requirement IDs are `SD-<n>`.

| ID | Requirement | Priority | Slice |
|---|---|---|---|
| **SD-1** | **The team is declared once per repository, with names.** A committed file (working name `.hitl/team.yaml`) lists each person and the roles they cover from the catalog's five: PM, Architect, Developer, QA, Ops. A role nobody covers is written as `none`, never left out. The three onboarding skills write it from a short question, and it can be edited by hand. It is committed, not local, because plan resolution and CI read it. A file with no named Architect or no named PM is valid but the plan says so on every change (SD-3, SD-6 depend on those two people being real). | Must | 1 |
| **SD-2** | **Every step's role resolves to a person at plan time, and the plan shows it.** `start-change` reads the team file and resolves each step to `other` (a different named person), `self` (the change's author), or `none` (no one covers the role). The resolution appears next to the step in the plan the human confirms. The catalog does not change: same steps, same `protects`, same `engages` and `needed_now`. Team shape is a third input to the plan alongside tier and profile, never a different catalog. | Must | 1 |
| **SD-3** | **A review step that resolves to `self` substitutes, and the record says what substituted.** For steps whose value is a second reader (code review rounds, the test review, the two verification reviews, QA verification) HITL runs the existing clean-context verification review with the step's checklist, and for QA verification hands the reviewer the acceptance criteria and not the code. Steps whose role is the Architect resolve to the named architect and are unchanged. The step record carries who verified (`self`, `agent`, or `self+agent`) and the review record's path. A step resolved to `self` can never be marked done with no substitution and no record; the validator rejects it. | Must | 1 |
| **SD-4** | **A role that resolves to `none` collapses into the developer's work, floor intact.** Ops and QA steps stay in the plan and the developer executes them. The floor semantics of Deploy and Promote are unchanged: a person still decides what reaches production, and that person is the developer. The handoff wording and the wait-for-role prompts on those steps are removed when the role is `none`. The record marks the step `role_covered_by: developer`. | Must | 1 |
| **SD-5** | **A boundary that is not a handoff never stops the workflow.** A step whose role resolved to `self` or `none` does not end a turn with a question addressed to a role. The only stops that remain are the plan's own confirmations (tier, plan, promote), a question only the architect or PM can answer (SD-6), and a genuine blocker such as a failing gate. Skills that today end a turn with "hand off to QA" or "ask Ops" read the resolution and continue. | Must | 2 |
| **SD-6** | **Questions for the architect or PM are batched, with assumption-and-proceed.** When a step raises a question for a role that resolved to `other`, HITL writes it to the change file (`open_questions[]`: the question, who it is for, the step, the assumption it will proceed on, a timestamp), proceeds on that assumption, and surfaces the batch at the phase boundary where that person already looks: the design packet, the PR, the release. Exceptions stop the workflow and ask now: an assumption that would be irreversible if wrong (a schema migration, an external side effect, a security posture change) or one the human marked as needing an answer first. An answer either confirms the assumption or re-plans from the step that made it. A change cannot Promote with an unconfirmed assumption; the developer can risk-accept one with a reason and their name, the same rule as a floor skip. This is the same skip-with-record pattern First Pass applies to steps, applied to questions. | Must | 2 |
| **SD-7** | **The two real handoffs each get one digest per phase.** For the architect: the design packet, the architecture review, integration verification, the open questions for them, and every step self-verified since their last digest. For the PM: requirements, acceptance, ROI, and the assumptions made in their name. The digest is written to the change file and offered as a PR description or an issue comment; it is never posted on anyone's behalf without that person confirming, the consent rule already in the progress-and-retro design. Where #112's "where this stands" record ships first, the digest is that record filtered by role, not a second primitive. | Should | 3 |
| **SD-8** | **The mode is measurable from the records.** Each change file carries: the resolution per step, who verified each review step, the count of structured questions asked, the count batched, the count confirmed and the count overturned, and the wait for each answered question. EPIC #22 derives from these the share of review steps self-verified, questions per change, ask-wait as a share of elapsed, and the assumption overturn rate. Nothing is sent anywhere; the fields are local, like every HITL record. | Should | 3 |
| **SD-9** | **The floor cannot be reached through the team file.** The team file cannot set a step's criticality, drop a step, or waive a gate. Skips still require the skip record; floor skips still require `ack_by` and, where a gate exists, a waiver. The validators that enforce this today (`ci/first-pass/check_skips.py` and its rules) run unchanged. A one-person team declaring itself does not lighten anything; it changes who executes and how that is recorded. | Must | 1 |
| **SD-10** | **Every step records when it started and when it ended.** The change file's step entries gain `started_at` and `ended_at`, written by the runtime on each transition, so elapsed and waiting per step no longer have to be reconstructed from transcripts and a step that was open overnight no longer looks like a day of work. May be delivered under EPIC #22 rather than here; it is listed because SD-8's measures depend on it. | Should | 3 |

## 6. Constraints

- **No fork.** One catalog, derived into `ai/shared/workflows.yaml` under the existing derive gate.
  Team shape is a resolution input, and the design must show it never becomes a second step list.
- **The team file is the customer's data.** It is committed in the product repo and holds real
  names. Nothing in HITL's own repository or docs carries a customer's team; examples use role
  words only.
- **The mode changes questions, not judgement.** SD-6 governs when a question is asked and how it
  is recorded. It does not license HITL to guess on a matter it would otherwise raise. The
  challenge-stance floor in `ai/shared/challenge-stance.md` applies unchanged: a risk, a cost, a
  disagreement and anything the person must decide still surface, now in the batch rather than one
  at a time.
- **Plain English.** Everything the mode says to a person follows `ai/shared/plain-english.md`.

## 7. Non-goals

- A lighter workflow for small teams. That is tier and First Pass, and both already exist.
- Inferring the team from git history or the tracker. It is declared, with names, by a person.
- Per-person writing profiles. That is personas, and it stays separate.
- A tier-calibration check when a repository lands most changes at tier 3. The measurement in §1
  raises that question, and it is a separate requirement on the intake, not on team shape.
- Any hosted view of the digests. Local records and the tracker are the surfaces.

## 8. Success measures

Measured on the repository in §1 and on any repository that declares a single developer, from the
records SD-8 leaves and the transcripts until SD-10 lands.

| Measure | Before (§1) | Target after slice 2 |
|---|---|---|
| Structured questions per change | about 20 | fewer than half, with the rest batched |
| Ask-wait as a share of elapsed | about 12%, equal to agent-active | under 5% |
| Turns ending on a question for a role that resolved to `self` or `none` | unmeasured, believed common | zero |
| Review steps done by the author with no substitution record | unmeasured | zero, validator-enforced |
| Assumptions overturned when answered | none recorded | reported; a rate above one in five sends the question back to "ask now" |

## 9. Version

| Version | Date | Change |
|---|---|---|
| draft v1 | 2026-09-19 | First draft from the customer measurement and the design conversation. Not reviewed. |

## 10. References

- Right-sizing design: `docs/design/right-sizing/01-design.md` (tier, fast track, plan resolution)
- First Pass design: `docs/design/first-pass/01-design.md` (skip-with-record, resurfacing)
- Skip record schema: `ai/shared/skip-record.md`
- Verification review pattern: `ai/shared/verification-review.md`
- Change file schema: `ai/shared/templates/change-context.schema.yaml`
- Step catalog and step costs: `tools/workflow-catalog/catalog.yaml`
- Roles table: `docs/reference.md`, section "Roles"
- Progress and retro design (consent rule for anything posted on someone's behalf):
  `docs/design/progress-and-retro/01-design.md`

## 11. Review history

None yet.
