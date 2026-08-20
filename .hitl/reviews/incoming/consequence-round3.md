# Adversarial review — round 3, consequence lens

- **State reviewed:** `ff879f32a6874512036d2fed5c81ff7d884337db` on `main`
- **Scope:** `git diff 54abacb..HEAD` (the round-2 fixes) inside `git diff v2.7.1..HEAD`
- **Stance:** refute. Assume the round-2 fixes are wrong, incomplete, or worse than what they replaced.
- **Lens:** consequence — what does this destroy, expose, or make unrecoverable.
- **Baseline:** `python3 -m pytest ci/ -q` → `729 passed in 51.37s`. Every fixture below passes the
  suite. None of them are covered by a test.
- **Method:** all fixtures built in `mktemp -d` throwaway git repos driven by a harness that calls
  `ci/adversarial/check_review.py` at HEAD. No tracked file was modified. Nothing was written under
  `.hitl/` except this report, which is gitignored by `.gitignore:27`.

## Verdict

**DO NOT SHIP.**

The round-2 commit closed the hole it was shown (`R2C-1`: a clean one-lens round 2 clearing a
release that carried open round-1 CRITICALs) and reopened the same hole through two other doors,
both of which exit 0 with no diagnostic. It is the third consecutive instance of the pattern named
in the brief: right about the defect, wrong about its class.

Two CRITICALs, four HIGHs, one MEDIUM. All reproduced.

---

## CRITICAL-1 — a reused finding id silently closes an open CRITICAL from an earlier round

`check_review.py:503 _identity()` treats a finding's `id` as a cross-round identity key, and
`check_review.py:511 _resolved` is a flat set of every resolved finding's id **and** claim, pooled
across all rounds. Line 529 then drops any carried-forward finding whose id **or** claim is in that
set. So a resolved finding in *any* record closes an unrelated open finding in *any other* record
that happens to share its id.

The same file already knows this is wrong. `check_review.py:437`, sixty lines above `_identity`,
says of the recurring-findings check: *"Compared on the claim, **because ids restart per round**."*
The carry-forward it introduced then keys on exactly the thing the file states does not survive a
round boundary.

This is not a hypothetical collision. `ai/shared/templates/adversarial-review-record.yaml` seeds the
example finding as `id: F1`. Every reviewer that copies the template starts at `F1`. Two rounds both
start at `F1`.

**Reproduction — ids exactly as the shipped template seeds them:**

```
r1-c.yaml  round 1  lens consequence  verdict do-not-ship
  - id: F1  severity: CRITICAL  status: open   claim: "upgrade drops the users table"
r1-b.yaml  round 1  lens bypass      verdict do-not-ship   findings: []
r2-c.yaml  round 2  lens consequence verdict ship
  - id: F1  severity: HIGH      status: fixed  verified_by: "re-ran, clean"
    claim: "the release note overstates what changed"
```

```
$ python3 ci/adversarial/check_review.py --change <tmp>/.hitl/current-change.yaml \
      --reviews <tmp>/.hitl/reviews --root <tmp>
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

`"upgrade drops the users table"` is never printed. It is not in the block list, not in the warning
list, not counted anywhere. The gate reports the release cleared.

Three variants, all exit 0:

| fixture | shape | result |
|---|---|---|
| P2-B | two-round loop, round 2 is top, id `H1` reused for a different finding | exit 0; open CRITICAL `"credentials are written to a world-readable log"` never named |
| P2-D | **same round**, two reviewers both numbered their first finding `C1`, one accepted | exit 0; the other reviewer's open CRITICAL `"rollback leaves the schema half migrated"` never named |
| P2-A | three rounds, `C1` in r1 open, `C1` in r2 fixed | exit 0; only `ROUND_DEPTH` printed |

P2-D is the worst of the three: two reviewers per round is the design this gate exists to enforce,
and one reviewer's *accepted* MEDIUM (`"the docs page is out of date"`, `accepted_by: pappar`) closes
the other reviewer's open CRITICAL in the same round. Nothing in the template, the SKILL, or the
shared doc tells the two reviewers to coordinate their numbering, and they run in separate clean
contexts precisely so that they cannot.

**Consequence:** this is `R2C-1` restated. Round 2 blocked the release because an open CRITICAL from
round 1 could be dropped silently. The fix for it drops open CRITICALs silently, on a collision the
shipped template makes the default. It is strictly worse than the pre-fix behaviour in one respect:
before, an earlier round's findings were dropped *by design and by a documented rule* ("earlier
rounds are history"); now they are dropped by accident, while the file claims they are carried.

---

## CRITICAL-2 — earlier-round findings are never schema-validated; one wrong word disables the carry-forward

Non-top-round findings enter the `findings` list only through the collector at
`check_review.py:521-530`, which admits an item only when `status in OPEN_STATES` **and**
`severity in BLOCKING`. The schema validation that would catch a bad status or severity
(`check_review.py:551 REVIEW_MALFORMED`) runs over `findings` — i.e. over the items the collector
already admitted. Anything the collector rejects is never validated and never carried.

The result: for any record below the top round, **any** string in `status` or `severity` other than
the exact expected value makes the finding vanish, with no `REVIEW_MALFORMED`, no warning, exit 0.

**Reproduction** — round 1 consequence + upgrade, round 2 consequence clean and top, one round-1
finding varied:

| round-1 finding | gate output | exit |
|---|---|---|
| `severity: CRITICAL, status: withdrawn`, claim `"the installer wipes ~/.claude on upgrade"` | `Release gate: adversarial review present, fresh, and cleared.` | **0** |
| `severity: CRITICAL, status: unresolved` | same | **0** |
| `severity: CRITICAL, status: wont-fix` | same | **0** |
| `severity: Critical!, status: open` | same | **0** |
| `severity: P0, status: open` | same | **0** |
| `findings:` written as a mapping instead of a list | same | **0** |

The top round gets `REVIEW_MALFORMED` for every one of these. The rounds the gate now claims to
carry forward get none of them.

**Consequence:** the carry-forward is one typo deep. `status: unresolved` is a plausible honest
typo; `status: wont-fix` is a plausible honest *intent*; `severity: P0` is the vocabulary of half the
teams this validator ships to. Any of them silently converts an open CRITICAL into nothing. And it
is a one-word deliberate bypass for anyone who wants one — cheaper than editing `reviewed_sha`,
which is the thing the module docstring calls the one lie the gate exists to catch.

This is the same class as CRITICAL-1: the fix took a dependency on earlier-round records without
extending to them any of the validation that made top-round records trustworthy.

---

## HIGH-1 — there is no way to withdraw a refuted finding; the only exits are false records

`RESOLVED_STATES = ("fixed", "accepted")`. There is no state for *"round 2 could not reproduce round
1's finding; it was wrong."* Before this commit, a refuted finding simply aged out of the top round.
Now it blocks forever.

**Reproduction — round 2 correctly refutes round 1's CRITICAL:**

```
r1-c.yaml round 1 consequence: id C1 CRITICAL open "the installer wipes ~/.claude on upgrade"
r2-c.yaml round 2 consequence (top, verdict ship):
  id R2C-1 LOW fixed "round 1's C1 does not reproduce; withdrawn"
```
```
[BLOCK] FINDING_OPEN: CRITICAL: the installer wipes ~/.claude on upgrade — fix it, or accept it explicitly with accepted_by
exit=2
```

The gate's own advice is the problem. The two exits it offers are:

- `status: fixed` + `verified_by` — `verified_by` is documented as *"the reproduction above, re-run,
  and what it printed."* There is no reproduction to re-run. Writing one is fabricating evidence in
  the field the gate added specifically to stop fabricated evidence.
- `status: accepted` + `accepted_by` — a signed record that a named human is knowingly shipping a
  CRITICAL that does not exist.

Both write a falsehood into the permanent governance record. The third option — `status: withdrawn`
— exits 0 (CRITICAL-2), which means the honest disposition currently works only because the
validator does not look.

**Also blocked (P1-D): a re-scoped finding.** Round 2 restates round 1's CRITICAL in its own words
and fixes it, with its own id:

```
r1: C1 CRITICAL open  "LENS_FLOOR counts the top round only, so the normal converge loop blocks"
r2: R2C-1 CRITICAL fixed verified_by "re-ran the converge fixture: blocks []"
    claim "the floor was scoped to one round; it now spans all rounds"
```
```
[BLOCK] FINDING_OPEN: CRITICAL: LENS_FLOOR counts the top round only, so the normal converge loop blocks
exit=2
```

That is the actual round-1→round-2 transition in this very repo, with the claim reworded. A round-2
reviewer runs in a clean context with its own brief; it writes its own claims in its own words and
numbers them from its own template. Matching round 1 verbatim is behaviour nothing asks for and
nothing could reliably produce.

**Consequence:** the release loop's normal terminal states — *the finding was wrong* and *the
finding was restated and fixed* — are both unreachable without either editing the historical record
or writing something untrue. Round 3 of this very release will hit this: `R2B-2` (*"shipping in this
state is not defensible"*) has no `fixed` or `accepted` disposition that is honest.

---

## HIGH-2 — the carry-forward is undocumented, and the shipped docs contradict it

Three shipped artefacts still describe the pre-commit behaviour, and one of them is the file every
reviewer copies:

- `ai/shared/templates/adversarial-review-record.yaml:12` — `round: 1  # highest round decides;
  **earlier rounds are history**`. Now false for findings. The template also seeds `id: F1`, which
  is the collision in CRITICAL-1.
- `ai/claude/adversarial-review/SKILL.md:238` — *"If they said DO NOT SHIP and you fixed everything,
  that is a **new round**, not an edit to theirs."* Editing the earlier record is now the only
  escape from HIGH-1, and the SKILL forbids it.
- `check_review.py:340` — the code's own comment: *"The newest round is the one that decides.
  Earlier rounds are history."* Still sits 180 lines above the code that makes earlier rounds
  decisive.

`grep -rn -i "carry\|carried\|any round\|all rounds\|earlier round" ai/claude/adversarial-review/SKILL.md
ai/shared/adversarial-review.md ai/shared/templates/adversarial-review-record.yaml` returns nothing
describing the new rule, nothing telling a reviewer that ids must now be unique across rounds, and
nothing telling anyone how to close a carried-forward finding.

**Consequence:** this is the wiring-defect class this repo named and shipped a suite for (2.5.0,
`ci/wiring/test_wiring.py`). The behaviour changed; the three documents that teach the behaviour did
not, and one of them now instructs the exact thing that breaks. A reviewer following the shipped
template produces colliding ids by default and is told the earlier round is history.

---

## HIGH-3 — `_is_a_review()` silently disqualifies genuine reviews, and the same run says it does not

`check_review.py:407` requires four properties before a record counts toward the release lens floor.
Three of them (`stance`, `reviewer.context`, `reviewed_sha`) are otherwise enforced only on the
selected top record. A record failing any of them below the top round is dropped from the floor with
**no message at all**, and `LENS_FLOOR` then misdiagnoses.

**Reproduction A — the file contradicts itself in one run.** Release, round 1, two genuine
clean-context refuting reviews, second on a real-but-uncatalogued lens:

```
[warn] UNKNOWN_LENS: r1-supply.yaml uses lens 'supply-chain', which is not in the catalog
       (shared/adversarial-review.md). It still counts; the id is what lets the gate group reviewers...
[BLOCK] LENS_FLOOR: round 1 was reviewed through 1 lens (consequence) — a release needs at least 2
        distinct ones... pick a second lens from the catalog... and run it.
exit=2
```

`check_review.py:379` prints **"It still counts"**. `check_review.py:410` is what makes it not count.
Same value, same run, thirty lines apart.

**Reproduction B — silent, in an earlier round.** r1 = `consequence` + `supply-chain`, r2 =
`consequence` (top):

```
[BLOCK] LENS_FLOOR: round 2 was reviewed through 1 lens (consequence) — a release needs at least 2
        distinct ones, across all its rounds... pick a second lens from the catalog and run it.
exit=2
```

No `UNKNOWN_LENS` at all — that warning is emitted only for `latest`. Two lenses were run; the gate
says one; there is nothing in the output pointing at the record it rejected or why.

**Reproduction C — a genuine review with a slightly verbose context field.**
`reviewer.context: "clean (fresh subagent)"` on the second round-1 record:

```
[warn] SHALLOW_REVIEW: ...r1-consequence.yaml is round 1 with zero findings...
[BLOCK] LENS_FLOOR: round 1 was reviewed through 1 lens (consequence)...
exit=2
```

No `NOT_INDEPENDENT` either — that check runs only on the selected record. The review is silently
disqualified as a review while never being told it is not one.

**Consequence:** the block message's remedy is *"pick a second lens from the catalog and run it"* —
addressed to someone who already ran two. The undiagnosable failure mode is the one where people
reach for the escape, and the escape here is the `adversarial_review` skip, which waives the entire
gate including every open finding. The message tells them not to. Under HIGH-1 and this, it will
still be the shortest path out.

---

## HIGH-4 — `RELEASE_RULES_INACTIVE` does not fire on the release it was written for

`_looks_like_a_release()` (`check_review.py:56`) fires on `"release" in change_id` or on step keys
exactly equal to `publish` / `version_bump`. The defect it responds to is `B-1` / `U-H3` / `R2B-3`:
the 2.8.0 release ran with `workflow.id: development` and both release-only rules silently off.

**Reproduction — replay the actual failing state, `7a12355`:**

```
$ git show 7a12355:.hitl/current-change.yaml
change_id: GH-88-adversarial-review-loop
workflow: { id: development, ... }
$ git show 7a12355:.hitl/current-change.yaml | grep -E '^\s+key:' | sort -u
key:adv_code adv_design arch_review conventions deploy design_plus docs figma figma_compare green
iac impact impact_brief integration_verify issue packet promote qa_verify reconcile red refactor
rerun review1 review2 roi roi_30 roi_90 rollout test_plan test_review training verify_green verify_pr verify_red
```

No `"release"` in the change_id. No `publish`, no `version_bump`. Running the gate at HEAD against
that exact change file with one valid review record:

```
[warn] SHALLOW_REVIEW: ...
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

**No `RELEASE_RULES_INACTIVE`.** The detector added to catch this release does not catch this
release.

**Both other directions also reproduce:**

- *False accusation.* A development change to fix a typo on the release-notes page,
  `change_id: GH-101-fix-release-notes-typo`, `workflow.id: development` →
  `[warn] RELEASE_RULES_INACTIVE: this change looks like a release (change_id names a release)`.
  Its remedy — *"Set workflow.id to 'release' if it is one"* — would, if followed, switch on
  `LENS_FLOOR` and `UNVERIFIED_FIX` for a change that is not a release. In a repo whose subject
  matter *is* the release gate, this false positive is routine.
- *Miss.* A real release in a product repo, `change_id: GH-77-cut-v3.0.0`, steps
  `bump_version` / `npm_publish` / `tag` / `announce`, `workflow.id: development` → no warning,
  exit 0. The key set is matched by exact string equality; `bump_version` is not `version_bump`.

**Consequence, independent of the heuristic's accuracy:** this is a warning, and the shipped
invocation is `python3 ci/adversarial/check_review.py || exit 2`
(`ai/shared/adversarial-review.md:168`, `ai/claude/dev-practices/workflow-steps.md:287`). Only the
exit code is consumed. A release with `workflow.id: development` passes with exit 0 whether or not
the warning prints. `R2B-3` asked for the release-only rules to stop keying on a free-text string;
what shipped is a printed sentence about the string, on stdout, that nothing reads. `R2B-3` remains
`status: open` in `.hitl/reviews/GH-92-release-2.8.0-round2-bypass.yaml` and is one of the eight
`FINDING_OPEN` blocks the gate reports against HEAD right now.

---

## MEDIUM-1 — the "match the SHAPE" naming guard still matches strings, and false-positives on a prohibition

`ci/wiring/test_wiring.py:363` replaced a byte-exact check with a three-alternative regex, commented
*"Match the SHAPE: an instruction to give reviewers names, however it is phrased."* It does not.

```
CAUGHT  'Give each reviewer a distinct name.'
PASSES  'Each reviewer gets a distinct name.'
PASSES  'Label each reviewer with a distinct name.'
PASSES  'Pass a distinct name to each reviewer.'
PASSES  'Use a stable name per reviewer so you can address it later.'
PASSES  'Spawn them with distinct names: r1-consequence, r1-bypass.'
PASSES  'The reviewers should each be given a name.'
CAUGHT  'You must never, under any circumstances, give each reviewer a name.'
```

Round 2 found four rewordings that passed the byte-exact check. Five pass the shape check. The
negation guard is a fixed 24-character lookbehind (`test_wiring.py:368`), so a correctly worded
prohibition with an intervening clause is flagged as the instruction it forbids — the guard would
block a doc edit that strengthens the very rule it protects. The consequence is a false assurance:
the comment now asserts a property the code does not have, which is what the round-2 finding was
about.

---

## Areas checked and found sound

- **Freshness (`_is_fresh`, `_exempt`, `_tree`, `MIN_SHA`).** Not touched by this commit; the
  branch-name rejection, the `.hitl/` exemption, and the `reviewed_tree` fallback all behave as
  documented. This remains the load-bearing rule and it holds.
- **The waiver path (`_acknowledged_skip`) and its `UNCOMMITTED_CHANGES` guard.** Unchanged and
  correct; the waiver still cannot cover an uncommitted tree.
- **`DUPLICATE_ROUND` and `canonical_lens` suffix stripping.** Behave as round 1 described; the
  known `b`/digit weakness is `U-M`, already `accepted`.
- **`_claimed_without_record`, `_adverse_verdict`, unreadable-record handling.** Unchanged, and I
  found no new consequence in them.
- **`RECURRING_FINDING`.** Correct as written — and notably it uses claim-only matching, which is
  the identity rule `_identity` should have used.

---

## Findings

| id | severity | claim | status |
|---|---|---|---|
| R3C-1 | CRITICAL | A reused finding id closes an unrelated open CRITICAL from another round — including between two reviewers in the same round — at exit 0, with the collision made the default by the shipped template's `id: F1` | open |
| R3C-2 | CRITICAL | Earlier-round findings are never schema-validated; any status or severity outside the exact vocabulary silently disables the carry-forward at exit 0 | open |
| R3C-3 | HIGH | No state exists for a refuted or re-scoped finding; the gate's only exits write a falsehood into the permanent record, and the honest one (`withdrawn`) works only via R3C-2 | open |
| R3C-4 | HIGH | The carry-forward is undocumented and contradicted by the shipped template (`earlier rounds are history`, `id: F1`) and by SKILL.md:238, which forbids the only escape | open |
| R3C-5 | HIGH | `_is_a_review` silently disqualifies genuine reviews on criteria enforced nowhere else below the top round; `UNKNOWN_LENS` prints "It still counts" in the same run that blocks because it did not | open |
| R3C-6 | HIGH | `RELEASE_RULES_INACTIVE` does not fire on `7a12355`, the release it was written for; it false-accuses non-releases and misses product-repo releases; and it is a warning nothing consumes | open |
| R3C-7 | MEDIUM | The "match the SHAPE" naming guard still lets five rewordings through and flags a correctly worded prohibition | open |

---

## Smallest change that would fix it

**For the two CRITICALs — five lines in `check_review.py`, no new concepts:**

1. `_identity()` (line 503): drop the id from the identity tuple, or scope it to `(round, id)`.
   Claim-only matching is what the file's own `RECURRING_FINDING` code already does and what the
   comment at line 437 already justifies. This kills R3C-1 outright.
2. The carry-forward filter (line 528): change `status in OPEN_STATES` to
   `status not in RESOLVED_STATES`, and drop the `severity in BLOCKING` pre-filter so unrecognised
   severities reach the `REVIEW_MALFORMED` check at line 551 instead of vanishing. Fail closed
   rather than open. This kills R3C-2.

**For R3C-3, three more lines:** add `withdrawn` to the status vocabulary with a required
`withdrawn_by` and a reason, exactly as `accepted`/`accepted_by` already works. Without it, step 2
above makes the honest disposition impossible rather than merely undocumented.

**For R3C-4, three edits, no code:** correct `adversarial-review-record.yaml:12`, change the
template's example id to something round-scoped (`R1-F1`), and add one paragraph to SKILL.md Step 7
stating that an open CRITICAL/HIGH survives every round until it is fixed, accepted or withdrawn,
and how a later round closes one.

**For R3C-5, one line:** emit a warning naming each record excluded from the floor and the reason.
It is the difference between a block someone can act on and a block someone routes around.

**For R3C-6:** either make it a block for `workflow.id != 'release'` when the heuristic fires, or
delete it. A warning on a stdout stream nothing reads is not a control, and its presence is now
being counted as the answer to `R2B-3`.

R3C-7 is the cheapest to fix and the least urgent; it can ride the follow-up issue with `U-M`,
`B-6..B-12`.
