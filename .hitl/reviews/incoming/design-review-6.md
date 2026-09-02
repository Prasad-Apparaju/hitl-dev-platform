# Design review 6 — right-sizing, progress-and-retro

## What I checked against the tools, not the prose

All the arithmetic in both docs is right.

- 8 workflows in `ai/shared/workflows.yaml`, longest 34 steps, shortest 5. `development` has 34 step
  entries. `platform` is 17 steps with `crit: null` on every one and no `step_costs` entries.
- Locked-set counts: resolving `crit`/`crit_by_tier` through `check_skips.resolve_crit` gives floor
  2/2/3/8/8 at tiers 0..4, plus `no_omit` on `red` and `green`. So tier 1 = 4, tier 2 = 5, tier 3 = 10,
  and tier 3 without `impact` = 9. Every number in both docs matches, including retro taking them to
  5/6/10.
- `impact` is the only step in any workflow with `command: dev-apply-change`.
- `engages` on 38 `step_costs` entries: 21 `always`, 4 paths, 8 profiles, 2 tags, 3 `multi_domain`.
  Subtract the four filed `cond:` steps and you get exactly the doc's 21/4/5/1/3, summing to 34.
  The characterisation is accurate.

## Five things, ranked

**1. The handoff between `start-change` and `apply-change` is not written down, and the two skills'
current order contradicts the new one. This stops it working.** Today `start-change` runs 3b tier →
4 plan → 4b First Pass → 5 branch → 6 write change file, then routes into `apply-change`, which
creates the branch again (2a), does its own impact analysis (3), and initialises the change file
with `tier` "from Step 3" and `current_step: {number: 3}` (7). The new order needs `apply-change` to
run between `start-change` step 2 and step 4b, before the plan and before the tier exist, and then
return. Nothing in either doc says who invokes whom, what happens to `apply-change` 2a and 7, or how
control comes back. There is also a direct conflict of principle: 4b's stated rule is that nothing
is written before the human confirms, and the new step 3 writes the plan into the change file first.

**2. Step 7a cannot move as one unit. This stops it working.** `--append` folds *this change's* skips
into `.hitl/skip-ledger.yaml`; the resurfacing half reads *earlier* changes. Moved to the new step 3,
the change has no skips yet — they are decided at step 5 — so the append half runs on an empty set and
this change's skips never reach the durable ledger. `check_skips` then raises `ROLLUP` for every skip
record. The doc reasons only about the resurfacing half and calls the whole thing a move. Its own line
applies: data that quietly stops being written is this repo's recurring defect.

**3. "Cannot be unticked" is not what floor means in the mechanism being reused. This is worth
deciding.** `check_skips` lets a floor step be skipped with `ack_by` plus, for a hard-gate step, a
`waiver_ref`; 4b's own menu offers floor steps "keep · request risk-accepted skip". Both docs assert
floor steps cannot be unticked, and progress-and-retro's entire argument for floor-at-every-tier
("being floor is the only thing that actually holds") rests on that. Either the reused validator
changes — contradicting "reused unchanged" — or the claim is softer than stated.

**4. The tier moves to step 4, but the sites that set it earlier are left as an exercise. This is
worth deciding.** The doc says "anything that reads the tier before the plan exists has to be found",
and names none of them. They are: `start-change` 3b (the confirm-tier step this design deletes without
saying so), the Step 6 generator's `TIER=2` default with `tier_set_by`/`tier_reason`, and
`apply-change` Step 7. Related: a stub with no `tier` makes `check_skips` emit `INVALID_TIER` and
resolve everything at tier 4. "Tolerate their absence" is asserted; the fail-closed default is not
mentioned.

**5. `step_costs` exists twice, and only the authoring copy is named. This is minor.** It is in both
`tools/workflow-catalog/catalog.yaml` and `ai/shared/workflows.yaml`, and `ci/wiring/test_wiring.py`
asserts the two stay consistent. The rewrite of all 38 `engages` plus new `needed_now`, and the new
retro step, have to land in the spine, in `step_costs`, and through `derive.py`/`verify`. The docs say
"the catalog" as if there were one.

## Could someone build it?

Not as written, because of 1 and 2. Everything else — the two predicates, the record shape, the
locked sets, the delta model, the retro's inputs — is specified tightly enough to implement. What is
missing is the sequencing contract between the two skills and the change file's states: which skill
owns the stub, which owns the branch, which writes the plan, at what point 7a's two halves each run,
and what a validator sees if it runs between step 2 and step 4. That is a page, not a redesign.

## Two changes walked through

**Small fix in a documented area, tier 1.** Restate, stub, impact analysis finds one area, no
dependents, tests that cover the behaviour; `needed_now` drops integration; locked set is deploy,
promote, RED, GREEN, retro — 5, matching the doc. Sensible. Where it goes wrong is the record, not the
prompt: one confirmation still has to produce ~25 ledger entries, each needing an actor, a reason, and
a disposition from `{defer, decline, starter}`. `defer` without a `followup_ref` raises
`DEFER_NO_FOLLOWUP`, so the cheap answer is `decline` everywhere, which writes a human declining 25
steps they never looked at — and #98's retrospective then reads exactly that list as "what was left
out and why". There is no disposition meaning "the rule says this cannot apply here".

**New published interface, three dependents, tier 3.** Impact analysis finds the dependents and the
interface, `needed_now` pulls in integration and compatibility, the floor is 9 plus retro = 10. Comes
out right. Where it goes wrong is step 6: the tier is decided "here, once" at step 4 and step 6 only
ever proposes step deltas. A finding that makes a dropped step load-bearing is usually evidence the
tier was wrong, and there is no path from a build-time finding back to the tier — the one decision
that changes what is locked.

## Is this converging?

Yes. The findings are smaller than earlier rounds': four of the five are about wiring two existing
skills together and one is a duplicated data file, and every number and every claim about the reused
subsystems that I could check held up. Nothing here questions the shape of the design. Fix 1 and 2,
settle 3 and 4 in a sentence each, and this is buildable — I would stop reviewing after that pass.
