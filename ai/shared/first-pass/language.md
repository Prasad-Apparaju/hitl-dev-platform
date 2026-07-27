# First Pass — language (FR-29 / CR-9)

Two voices, both respectful. The **record** voice is neutral and factual. The **resurfacing** voice is
respectful-persuasive — it surfaces the risk and invites, never blames or shames. Never use: *failed,
negligent, careless, fault, blame, lazy, should have, sloppy* (linted in `ci/first-pass/resurface.py`).

## Recording a skip (neutral)

> Recorded: **{step}** {disposition} for {change_id} — reason: "{reason}" (by {actor}, {ts}).

For a floor skip, also:

> Risk accepted by **{ack_by}**{, waiver {waiver_ref}}. This is a recorded choice, not a gate exception.

## Resurfacing (respectful-persuasive), escalating by criticality

- **standard** — at the next overlapping change:
  > A quick heads-up: last time work touched {area}, **{step}** was lightened ({disposition}, reason:
  > "{reason}"). Since this change overlaps, it may be a good moment to fold in the enhancement — happy to
  > scope it.
- **floor** — at the next overlapping change / incident:
  > Worth a careful look: **{step}** was on the recommended floor and was risk-accepted last time
  > ({reason}, by {ack_by}). Given this change touches the same area, it may be worth doing now. I can help.
- **incident** — factual, non-blaming:
  > For context, these steps were lightened in the change that touched this area: {list with reason + date}.
  > Sharing so the review has the full picture.

## Reconciliation with `challenge-stance.md`

Same stance as the framework's challenge mode: **surface the risk, respect the choice.** First Pass records
quietly during execution (challenge-stance forbids challenging mid-build) and persuades only at the decision
boundaries — the follow-up, the next overlapping change, and incident review. It generalizes challenge-stance's
existing *TODO Deferral* onto the durable skip ledger.
