# Consequence — round 2

**State reviewed:** `54abacb2eabd0da4a050b0e88195545084399fec` on `main` (round-1 fixes), against
`7a12355` and `v2.7.1`.
**Lens:** consequence — what does this destroy, expose, or make unrecoverable.
**Stance:** refute. Every finding below was reproduced; the command and its output are inline.

**Summary:** the two CRITICALs are gone as stated, but the fix for the first one removed the only
barrier standing in front of an already-known hole, and the test guard that would have caught the
side effect was weakened in the same commit by exactly the amount the fix needed. Four of the six
round-1 fixes are clean.

---

## CRITICAL-1 — the LENS_FLOOR fix removed the only thing stopping round-1 CRITICALs from being dropped

The findings inspection reads `latest` (the top round only, `check_review.py:465`). The lens floor
used to read `latest` too. Because a release needed two distinct lenses **in the top round**, a
narrow round 2 could not be the top round — it blocked. That coupling was the only thing making the
deciding round as broad as the round whose findings it replaced.

The fix decoupled them. `distinct` now spans `records` (all rounds); `findings` still spans `latest`.
So the shape the fix was written to permit — *"round 2 re-reviewing one fix with one lens"*, its own
comment at `check_review.py:378` — is now also the shape that erases every finding round 1 raised.

Reproduction (scratch repo, clean tree, records committed):

```
round 1  lens: fitness      verdict: do-not-ship  findings: [CRITICAL open "deletes the user database on upgrade"]
round 1  lens: consequence  verdict: do-not-ship  findings: [CRITICAL open "credentials written to world-readable log"]
round 2  lens: fitness      verdict: ship         findings: []
```

```
$ python3 old_check.py          # validator at 7a12355
[BLOCK] LENS_FLOOR: round 2 was reviewed through 1 lens (fitness) — a release needs at least 2 distinct ones. ...
Release gate: BLOCKED. An adversarial review of the exact code being shipped is required before publishing.
exit=2

$ python3 ci/adversarial/check_review.py    # validator at 54abacb
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

Two open CRITICALs on record, one of them the exact failure class this gate's own docstring cites
(*"shipped a defect that destroyed user data"*), and the gate prints that the review is cleared.
No warning fires: `RECURRING_FINDING` only speaks when a claim is *restated*, so not carrying a
finding forward is the silent path.

This is not a new hole — it is round-1 `MEDIUM-2`, accepted by `pappar` and deferred. But the
acceptance was made against a codebase where reaching it required a two-lens round 2. The same
commit that recorded the acceptance made it reachable with one record. An accepted risk whose
exploit surface widened in the commit that accepted it has not been accepted; it has been enlarged
under an old signature.

**Smallest fix:** extend the findings loop to carry earlier-round findings that are still `open` and
`CRITICAL`/`HIGH`. Two lines at `check_review.py:465`:

```python
for _p, _doc in latest:
    ...
# plus:
for _p, _doc in records:
    if _round((_p, _doc)) == top:
        continue
    for i, item in enumerate(_doc.get("findings") or []):
        if isinstance(item, dict) and str(item.get("status", "open")).lower() in OPEN_STATES \
           and str(item.get("severity", "")).upper() in BLOCKING:
            findings.append((_p, i, item))
```

---

## HIGH-2 — the release floor now counts records the gate itself would reject as reviews

Everything that counts toward the two-lens floor used to be a record in `latest`, and every record
in `latest` is validated: `reviewer.context == "clean"`, `stance == "refute"`, `reviewed_sha`
present and fresh, lens checked against the catalog. Counting `records` broke that pairing. Earlier-
round records are validated by *nothing* — none of those checks iterate `records`.

Reproduced, each a separate fixture, all with a legitimate fresh single-lens round 2:

```
### C: floor satisfied by an uncatalogued lens in an EARLIER round
    round 1 lens: zzz-not-a-lens   round 2 lens: fitness
    Release gate: adversarial review present, fresh, and cleared.      exit=0
    (no UNKNOWN_LENS warning — that loop still iterates `latest`, line 358)

### D: floor satisfied by an earlier round with a GARBAGE reviewed_sha
    round 1 reviewed_sha: deadbeefdeadbeefdeadbeef
    Release gate: adversarial review present, fresh, and cleared.      exit=0

### E: floor satisfied by a record that is not a review at all
    round 1: no reviewed_sha, reviewer.context: dirty, stance: confirm, verdict: do-not-ship
    Release gate: adversarial review present, fresh, and cleared.      exit=0
```

All three block on the `7a12355` validator with `LENS_FLOOR`. Case C is the sharpest as a
consequence: the lens that satisfies a release floor can be a string nobody recognises, and the
warning written to say so has been silenced for exactly that case. Moving the same two records into
one round makes the warning reappear:

```
$ # C fixture with both records in round 1
[warn] UNKNOWN_LENS: r1.yaml uses lens 'zzz-not-a-lens', which is not in the catalog ...
```

**Smallest fix:** count only records that pass the reviewer predicates — filter `records` by
`context == "clean"` and `stance == "refute"` before taking `distinct`, and move the UNKNOWN_LENS
loop from `latest` to `records`.

---

## HIGH-3 — the guard that would have caught the message regression was weakened to fit the fix

`test_a_hook_that_blocks_says_what_to_do_next` exists because *"stripping the way out of three
messages stayed green while a fourth still had one — the guard reported on a file that no longer
told most people what to do."* Its own docstring.

Fix #3 wrapped the remedy line in `if [[ -n "$EXPECTED" ]]; then ... fi`. An `if` is real code, so
`_message_blocks` split there and the block above lost its remedy — the guard would have failed. The
same commit made `if|elif|else|fi|then|done|do` transparent. Conditionals no longer end a message,
so **every message in an if/else chain now merges into one block**, and a block passes if any of the
merged messages names a remedy. That is the failure the test was written to forbid, restored.

Mutation M1: delete all three remedies from the branch-mismatch message in
`ai/claude/hooks/check-hitl-context.sh`, leaving it as:

```
🧭 You are on 'x', which does not match the tracked change GH-7.
   (That change does not record a branch, so I cannot tell you which one to switch to.)

Edits are paused until those agree, so pick whichever is true:
```

— a hard block on every edit in the repo, offering nothing.

```
$ python3 -m pytest ci/wiring/test_wiring.py -q -k "says_what_to_do_next or shout"
2 passed, 43 deselected in 0.06s

$ python3 -m pytest ci/wiring/test_wiring_OLD.py -q -k "says_what_to_do_next"   # helper at 7a12355
E       AssertionError: these messages stop someone and never name a next step:
E           check-hitl-context.sh: echo "" >&2 echo "Edits are paused until those agree, so pick whichever is true:
1 failed, 44 deselected
```

The shipped hook is fine today — the mutation is mine. The finding is that the guard is now blind to
this class permanently, for every hook, and it went blind in the commit whose purpose was message
quality. A weakened guard is invisible exactly until it matters.

**Smallest fix:** revert the `if|elif|else|fi|then|done|do` clause in `_message_blocks`
(`test_wiring.py:437`) and remove the conditional from the hook message instead — compute the line
into a variable before the block:

```bash
SWITCH_LINE=""
[[ -n "$EXPECTED" ]] && SWITCH_LINE="  • Working on ${CHANGE_ID}? Switch to '${EXPECTED}'."
```

---

## MEDIUM-4 — the extended shouting guard reads only the first line of each call

Fix #4's guard extension matches `(print|block)\s*\(\s*f?"` — the *opening* line of a call. All four
messages it was written for are multi-line calls. Anything on a continuation line is invisible.

Mutation M4b — add a second argument to the unparseable-register `block(...)`, leaving the polite
first line intact:

```
154:              "HITL DEPLOY BLOCKED: REGISTER PARSE FAILURE, ABORTING DEPLOY PIPELINE.",
```

```
$ python3 -m pytest ci/ -q
724 passed, 5 skipped in 41.97s

$ bash check-platform-ready.sh production 2
🔒 Deploy stopped: I cannot read the readiness register, so I cannot say this is ready.
HITL DEPLOY BLOCKED: REGISTER PARSE FAILURE, ABORTING DEPLOY PIPELINE.
  The file is docs/04-operations/platform-readiness.yaml. Fix it, or re-run /hitl:ops-plan-platform derive.
exit=2
```

A full revert of the file to `7a12355` *is* caught (`test_hooks_do_not_shout_their_internal_state`
fails, 723 passed), so the guard works on the shape it was tested against and misses the shape the
file is actually written in.

**Smallest fix:** in `_hook_messages`, also take any line matching `^\s*f?"` that follows a matched
`print(`/`block(` line — or scan the heredoc as a joined region rather than line by line.

---

## MEDIUM-5 — the release note now describes behaviour that does not ship

`CHANGELOG.md:118`: *"On a change whose workflow is `release`, a round reviewed through fewer than
two distinct lenses now fails `LENS_FLOOR`"*. The Added bullet says the same: *"a round with one lens
is a required step satisfied with nothing in it."* Both describe the pre-fix per-round rule.

```
### fixture: round 1 = fitness only, round 2 = consequence only. Every round has ONE lens.
$ python3 ci/adversarial/check_review.py
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

This paragraph is round-1's `C2-H1`, marked `fixed` with `verified_by: "CHANGELOG 'Note for existing
projects' now states exactly which two rules are new"` — verified against the semantics the same
commit then changed. The consequence is not over-compliance; it is that a reader is told the top
round is independently floor-checked, which is the assumption CRITICAL-1 depends on being false.

**Smallest fix:** *"a release reviewed through fewer than two distinct lenses across all its rounds
now fails `LENS_FLOOR`"*, in both places.

---

## MEDIUM-6 — the CRITICAL fix shipped with no test

```
$ git diff --stat 7a12355..HEAD -- ci/adversarial/test_check_review.py
(empty)
```

Every `LENS_FLOOR` test builds its records through `_multi`, which writes them all into a single
round. Neither new behaviour is covered: not the converge loop passing, not a single-lens release
still blocking across rounds. The record's `verified_by` cites re-run fixtures; those fixtures were
not committed. The next person to touch this function has nothing telling them which of the two
readings is intended — and `check_review.py` contradicts itself on the point (LOW-9).

---

## LOW-7 — fix #3 guarded one of the two empty-able variables in the same two lines

`CURRENT_BRANCH` is empty on a detached HEAD (rebase, bisect, `git checkout <sha>`, most CI
checkouts) and is interpolated unguarded in the block the fix rewrote:

```
$ git checkout -q HEAD~1 && git branch --show-current
(empty)
$ echo '{"tool_name":"Edit","tool_input":{"file_path":"src/a.py"}}' | bash check-hitl-context.sh
🧭 You are on '', but the tracked change GH-7 lives on 'main'.
...
  • Working on something else here? /hitl:dev-switch-context points HITL at this branch.
exit=2
```

Same defect class, same two lines, other variable — plus a remedy that cannot be followed
(`dev-switch-context` has no branch to point at). `grep -rn "detach\|show-current" ci/` returns
nothing: no test anywhere covers detached HEAD. The new test in `test_concluded_change.py` asserts
`"''" not in p.stderr`, which is the right property, but its fixture is on `issue/42-something`
where `CURRENT_BRANCH` cannot be empty.

The `hitl_branch_gone` branch is safe — `hitl_branch_gone` returns 1 when `expected` is empty
(`_steps.sh:204`), so `${EXPECTED}` there is non-empty by construction. `hitl-gate.sh` and
`welcome.sh` interpolate `CURRENT_BRANCH` the same way, but both are informational and neither
blocks.

---

## LOW-8 — two scratch fixtures were committed into governance state, and they will block a future change

`.hitl/reviews/a.yaml` and `.hitl/reviews/b.yaml` are throwaway test records (`scope: s`,
`reviewer: {model: m, spawned_by: x, brief: b}`) committed to `main` under `change_id: GH-100`. This
repo issues `GH-N` ids and is at #92.

Their lenses are `functionality` and `fitness` — the alias map resolves both to `fitness`, so they
are a duplicate pair:

```
### a future GH-100 release with its own round-2 record
[BLOCK] DUPLICATE_ROUND: round 1 has more than one record for lens 'fitness'
        (.hitl/reviews/a.yaml, .hitl/reviews/b.yaml). ...
exit=2
### same, with a.yaml/b.yaml removed — only the real finding remains
[BLOCK] LENS_FLOOR: ...
```

A hard release block naming two files nobody on that change wrote, telling them to stop numbering a
lens they did not number. **Smallest fix:** `git rm .hitl/reviews/a.yaml .hitl/reviews/b.yaml`.

---

## LOW-9 — `check_review.py` contradicts itself, 50 lines apart

```
328:    # The newest round is the one that decides. Earlier rounds are history.
378:        # ALL rounds, not just the top one. ...
```

Both govern the same record set in the same function. This is the intra-file contradiction class the
brief added at `SKILL.md:114` in this very release, and it is the root of CRITICAL-1: the file states
both rules and implements each one somewhere.

---

## LOW-10 — the new SKILL.md guard asserts a string, not a property

`assert not re.search(r"(?i)give each reviewer a distinct name", body)` catches a verbatim revert
(confirmed: reverting line 140 fails the test) but not a reword:

```
$ # SKILL.md line 140 -> "Name each reviewer distinctly so the reports are attributable."
$ python3 -m pytest ci/wiring/test_wiring.py -q -k "hand_their_report_over"
1 passed, 44 deselected
```

Low, because the regression it guards is a specific sentence in a specific file. Noting it because
the brief described these edits as phrase→property; this one went the other way.

---

## Sound

- **Fix #1's stated property holds.** A genuinely single-lens release still blocks: round 1 fitness,
  round 2 fitness → `[BLOCK] LENS_FLOOR`, exit 2.
- **Fix #2 is clean.** The acknowledged skip still passes (exit 0), `REVIEW_WAIVED` still fires, and
  the adverse-verdict note still names the record it is overriding. The new message correctly stops
  pointing people at it. (It still discards open findings silently — pre-existing, and the message is
  now honest about that, which is the improvement.)
- **Fix #4 is behaviourally identical.** 84/84 environment × tier × register combinations return the
  same exit code on `v2.7.1` and `HEAD`; all 60 tests in `test_check_platform_ready.py` pass against
  both scripts. Fail-closed is intact — deleting the `total_items == 0` block fails two tests.
- **The `_says_empty` / `_says_unreadable` helpers are not weakened.** They accept both wordings by
  design, and the behaviour underneath is still asserted: removing the empty-register fail-closed
  fails `test_delivery_ready_flag_on_empty_register_blocks` and `test_empty_layers_blocks`.
- **The new `test_concluded_change.py` test is real.** Fails against the `7a12355` hook, passes
  against `HEAD`.
- **The SKILL.md self-contradiction (round-1 MEDIUM-1) is genuinely gone.** No remaining instruction
  to name reviewers anywhere in the file.
- **`.gitignore` for `.hitl/reviews/incoming/` is correct** and does not affect the gate: `_exempt`
  already covers the whole `.hitl/` prefix, so freshness was never sensitive to it either way.

---

## VERDICT: DO NOT SHIP

CRITICAL-1 alone. A release can now pass the gate with unresolved CRITICAL findings on record and
print *"adversarial review present, fresh, and cleared"* — through the exact workflow shape the fix
was written to enable, in the tool whose stated purpose is that this cannot happen silently.

**Smallest change that would fix it:** the two-line addition at `check_review.py:465` carrying
earlier-round `open` CRITICAL/HIGH findings into the inspection (patch in CRITICAL-1 above). That
turns the widened floor from a hole into what it was meant to be — a converge loop where narrowing
round 2 costs you nothing except the findings you actually closed.

HIGH-3 should go with it: it is a one-line revert in `_message_blocks` plus a two-line change in the
hook, and leaving it means the next message regression ships green.
