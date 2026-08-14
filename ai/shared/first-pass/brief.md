# First Pass — brief mode (FR-29 / CR-14)

An interaction directive, not tooling. A `first_pass: true` change puts the driver in brief mode: say less,
ask less, and let the artifacts carry the detail. The user chose a thin first pass; narrating it at full
length spends the time the mode was meant to save.

Referenced by `/hitl:dev-start-change` and the workflow driver skills.

## The rules

1. **Do not restate the plan you are about to run.** The step plan was shown at intake and the breadcrumb
   shows position. Repeating it is the single largest source of session prose.
2. **Do not re-ask an answered question.** Tier, workflow, disposition and issue were settled at intake.
   If an answer exists in `.hitl/current-change.yaml`, read it; do not ask again.
3. **One-line confirmations.** "Recorded: ROI declined." not a paragraph explaining what recording means.
4. **Surface decisions and records, nothing else.** What was decided, what was written down, what needs a
   human. Not the reasoning that got there, unless asked.
5. **One menu, one pass.** Dispositions are collected through the single menu, never as a step-by-step
   interview.
6. **Tables and lists over prose** for anything enumerable.
7. **No preamble.** Do not announce what you are about to do and then do it.

## Where brief mode does NOT apply

- **The resurfacing voice at boundaries.** Resurfacing is allowed to persuade, and persuasion needs enough
  words to carry the risk. See `language.md`.
- **Anything a human must decide.** A floor skip, a waiver, an approval gate, or a risk acceptance gets the
  full context it needs. Brevity is for narration, never for consent.
- **Errors and blockers.** State what went wrong, what it means, and the way out. A one-line error that
  leaves someone stuck is not brevity, it is a support ticket.

## Test

`COMPAT-3` in the First Pass test plan. The observable behaviour: a change run under brief mode produces
materially less session output than the same change run without it, and no decision, record, or blocker is
lost from that output.
