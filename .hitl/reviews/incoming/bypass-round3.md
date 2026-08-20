# Adversarial review — round 3, bypass lens

State reviewed: `ff879f32a6874512036d2fed5c81ff7d884337db` (main)
Scope: `git diff 54abacb..HEAD` (the round-2 fixes) inside `git diff v2.7.1..HEAD` (the whole release)
Stance: refute. Reviewer context: clean.
Baseline: `python3 -m pytest ci -q` at HEAD → **729 passed**. Every finding below is reproduced
against that green suite.

All work was done in `mktemp -d` scratch: a throwaway git repo, and a `git clone` of this repo
checked out at `ff879f3`. No tracked file was modified.

**Verdict: DO NOT SHIP.**

---

## B3-1 — CRITICAL — one record of LOW typos closes every open CRITICAL and HIGH in the change

The round-2 fix added a carry-forward so an open finding survives every round. It also added
`_resolved`, which pools resolutions across **every record for the change** and keys them on
`_identity(item)` = `(id, normalised claim)`. Nothing requires the resolving finding to be the
same finding: not the same round, not the same lens, not the same severity, not the same claim,
and not carrying any evidence. Three lines above, `check_review.py` says so itself:

> `# Compared on the claim, because ids restart per round.`

Ids restart per round, and an id resolves globally. Those two facts cannot both be true safely.

**Reproduced against the live GH-92 record set.** Cloned this repo at `ff879f3`, copied the real
`.hitl/` in (minus `reviews/incoming/`), and added one file:

```
.hitl/reviews/GH-92-release-2.8.0-round3-cost.yaml
  round: 3, lens: cost, stance: refute, reviewer.context: clean, verdict: ship
  findings: seven entries, each severity LOW, status: fixed, claim "a typo" / "wording",
            ids R2B-1 R2B-2 R2B-3 R2B-4 R2C-1 R2C-2 R2C-3
```

Before:

```
$ python3 drive.py <clone>
BLOCKS: ['REVIEW_STALE', 'FINDING_OPEN' x7, 'VERDICT_NOT_SHIP']
    [BLOCK] FINDING_OPEN: CRITICAL: The floor counts records that no other check ever validates …
    [BLOCK] FINDING_OPEN: CRITICAL: The all-rounds change made the string-counting weakness …
    [BLOCK] FINDING_OPEN: CRITICAL: The LENS_FLOOR fix removed the only thing keeping round-1 …
    [BLOCK] FINDING_OPEN: HIGH: Round 1's B-1 was not fixed in code …
    [BLOCK] FINDING_OPEN: HIGH: Three shipped files promise a rule the gate no longer enforces …
    [BLOCK] FINDING_OPEN: HIGH: The release floor counts records the gate itself would reject …
```

After (the exact shipped CLI, exact output):

```
$ python3 ci/adversarial/check_review.py --change <clone>/.hitl/current-change.yaml \
      --reviews <clone>/.hitl/reviews --root <clone>
[warn] ROUND_DEPTH: this is round 3. Two rounds then a human decision is the rule …
Release gate: adversarial review present, fresh, and cleared.
EXIT=0
```

Three open CRITICALs and four open HIGHs, including the two that are currently blocking this very
release, cleared by seven `severity: LOW, status: fixed` typo entries. `verified_by` is never
required because the resolving findings are LOW. `REVIEW_STALE` also disappears, because the new
round became the governing record.

This is not a tamper you would notice in review: the added file is a well-formed, catalogued-lens,
clean-context, refute-stance record that reads as an ordinary round-3 pass.

**Smallest fix:** an id may only resolve a finding raised in the same record (or scope the key to
`(source_path, id)` / `(round_raised, id)`), and any finding used to resolve a BLOCKING one must
itself be BLOCKING and carry `verified_by`/`accepted_by`.

---

## B3-2 — CRITICAL — adding a round makes the gate weaker: every integrity rule reads only the top round

`findings` is assembled in two passes. Non-top rounds contribute only entries that are already
`status in ("open",)` **and** `severity in ("CRITICAL","HIGH")`. The top round contributes
everything. Every downstream integrity rule — severity vocabulary, status vocabulary, `verified_by`,
`accepted_by`, `findings must be a list` — then runs over that assembled list. So all of them apply
to the top round only, while the *resolution* power of a record (B3-1) applies to all rounds.

Consequence: the same bytes pass or block depending on whether one more round file exists.

**Reproduced.** Scratch repo, `workflow.id: release`, round 1 (bypass + consequence) with an open
CRITICAL `deletes the user database on upgrade`, round 2 clean.

Baseline — the round-2 fix working as intended:

```
BLOCKS: ['FINDING_OPEN']
    [BLOCK] FINDING_OPEN: CRITICAL: deletes the user database on upgrade …
```

(a) Change one word in the round-1 record — `status: open` → anything the vocabulary does not know:

```
--- status: 'deferred'          --- BLOCKS: NONE   WARNS: NONE
--- status: 'triaged'           --- BLOCKS: NONE   WARNS: NONE
--- status: 'wontfix'           --- BLOCKS: NONE   WARNS: NONE
--- status: ''                  --- BLOCKS: NONE   WARNS: NONE
--- status: 'Open?'             --- BLOCKS: NONE   WARNS: NONE
--- status: 'open (deferred)'   --- BLOCKS: NONE   WARNS: NONE
```

The identical value in the **top** round is a hard block:

```
--- same 'deferred' status but in the TOP round ---
BLOCKS: ['REVIEW_MALFORMED', 'FINDING_OPEN']
```

`status: deferred` is the single most likely thing a triage pass writes. It reads as honest
bookkeeping and it deletes the finding.

(b) Same for severity — a non-top-round CRITICAL with an off-vocabulary label vanishes silently:

```
--- severity: 'Crit'      --- BLOCKS: NONE
--- severity: 'critical!' --- BLOCKS: NONE
--- severity: 'blocker'   --- BLOCKS: NONE
--- severity: 'P0'        --- BLOCKS: NONE
```

(c) Reshape `findings:` from a list into a mapping in a non-top round — every finding in the file
disappears with no message. In the top round this is `REVIEW_MALFORMED: findings must be a list`:

```
--- findings: as a MAPPING (non-top round) --- BLOCKS: NONE   WARNS: NONE
```

(d) and (e) — the round-2 fix's own evidence rules are the clearest demonstration. Identical record
content, one extra round file added, opposite verdict:

```
--- D: CRITICAL status: fixed, no verified_by, round 2 IS top ---
BLOCKS: ['UNVERIFIED_FIX']
--- C: same record, round 3 added so round 2 is no longer top ---
BLOCKS: NONE

--- E-top:    CRITICAL status: accepted, no accepted_by, round 2 IS top ---
BLOCKS: ['UNSIGNED_ACCEPTANCE']
--- E-nontop: same record, round 3 added ---
BLOCKS: NONE
```

So "closing a finding needs evidence" holds for exactly one round at a time, and running another
round retroactively removes the requirement from every earlier one. B3-1 is the sharpened form of
this; (a)–(c) are the version that needs no id collision at all.

**Smallest fix:** validate severity / status / `verified_by` / `accepted_by` / list-shape over
**all** records, not just `latest`, and treat an unrecognised `status` on a BLOCKING finding as
open rather than as absent.

---

## B3-3 — HIGH — carry-forward of R2B-3 (open): the release rules still do not run, and the new warning does not fire

The fix for R2B-3 was a warning, `RELEASE_RULES_INACTIVE`, driven by `_looks_like_a_release()`:
`change_id` containing the substring `release`, or a step key exactly `publish` or `version_bump`.
Both signals are typed by the same author, in the same file, that the rule exists to distrust. A
release cut under any other two words trips nothing.

**Reproduced.** Scratch repo, `change_id: GH-99-cut-2.9.0`, `workflow.id: development`, step keys
`rc_scope changelog bump build ship_it tag`, one lens, one CRITICAL `the installer deletes the
user database` marked `status: fixed` with no `verified_by`:

```
--- workflow.id=development, change_id has no 'release' ---
BLOCKS: NONE
WARNS: ['UNVERIFIED_FIX']          <- warning only; exit 0

--- same, but workflow.id: release ---
BLOCKS: ['LENS_FLOOR', 'UNVERIFIED_FIX']
```

No `RELEASE_RULES_INACTIVE` at all. A one-lens release with an evidence-free CRITICAL closure
exits 0 and the gate never says the release rules were off.

Also: `_looks_like_a_release(change, root)` takes `root` and never reads it —
`sed -n '/^def _looks_like_a_release/,/^    return ""/p' … | grep -c root` → `1` (the signature).
The one source of evidence the author cannot forge — the diff itself, a version bump in
`plugin.json`, a `CHANGELOG` heading, a tag — is passed in and thrown away.

**Smallest fix:** derive the signal from `root` (a `version` change in `ai/claude/plugin/plugin.json`
between the reviewed sha and HEAD), and make it a block rather than a warning when it disagrees
with `workflow.id`.

---

## B3-4 — HIGH — carry-forward of R2B-4 (open): the naming "shape" regex is fitted to the four rewordings the round-2 report listed

The comment claims it now matches "the SHAPE: an instruction to give reviewers names, however it is
phrased." It matches the four examples in the round-2 report and little else.

**Reproduced** end to end on a clone at `ff879f3`, appending one sentence to
`ai/claude/adversarial-review/SKILL.md` and running
`python3 -m pytest ci/wiring/test_wiring.py -q -k reviewers_hand`:

```
[1 passed]  Each reviewer gets a distinct, stable name so you can message it later.
[1 passed]  Reviewers must have distinct names.
[1 passed]  Pass a `name:` to each Agent call so the reviewers stay addressable.
[1 passed]  Set a distinct name for each reviewer.
[1 passed]  Give each of the reviewers a distinct name.
[1 passed]  Name the reviewers so they can be addressed later.
[1 passed]  **Give** each reviewer a distinct name.
[1 passed]  Spawn the reviewers with distinct names.
[1 passed]  | reviewer | give it a distinct name |
[1 failed]  Give each reviewer a distinct name.        <- only the literal 2.7.1 sentence
```

Nine of ten. The third one is the form an author is *most* likely to write, because it is the
operational instruction rather than the prose one, and bolding the verb (`**Give**`) is enough on
its own.

The negation lookback is separately defeatable. `\b(do not|don't|never|no)\s*$` over the preceding
24 characters, applied to text that `_flat()` has collapsed to single spaces, means any preceding
line ending in a bare negation word disarms the check for the sentence after it — and the literal
2.7.1 sentence then passes:

```
[1 passed]  "### Do not\nGive each reviewer a distinct name."
[1 passed]  "Is a shared name acceptable? The answer is no\n\nGive each reviewer a distinct name."
[1 passed]  "Reviewers get names? Never\n\nGive each reviewer a distinct name."
[1 failed]  "> **Do not**\n> Give each reviewer a distinct name."   (bold negation not recognised)
[1 failed]  "Do not skip step 3 — give each reviewer a distinct name."
```

A `### Do not` heading with the instruction on the next line is not an exotic construction; it is
how the rest of this skill is written. Note the last two also show the check failing in the *other*
direction — a genuine negation that is bolded or interrupted is reported as an instruction.

**Smallest fix:** stop asserting a string. The property is "the skill does not tell the caller to
pass a name". Assert it where it is machine-checkable — no `name:` / `name =` argument in any
Agent-spawn example in the skill — rather than by pattern-matching English.

---

## B3-5 — HIGH — round-1 C1 is recorded fixed on evidence for a different half of its claim

C1 (CRITICAL) claimed two things: the floor counted the top round only, **and** "the escape it
advises waives the whole gate and silently discards open CRITICALs". Its reproduction field records
exactly the second half: *"with an acknowledged adversarial_review skip an OPEN CRITICAL 'deletes
the user database on upgrade' produced blocks: none and was never mentioned."*

`verified_by` says: *"Message no longer points at the adversarial_review skip."* That answers where
the message points, not what the waiver discards.

**Reproduced at HEAD.** Scratch repo, `workflow.id: release`, an attributed skip
(`step: adversarial_review, ack_by: me`), and one record carrying an open CRITICAL with
`verdict: ship`:

```
--- waiver + a record whose verdict is 'ship' but carries an OPEN CRITICAL ---
BLOCKS: NONE
WARNS: ['REVIEW_WAIVED']
```

The waiver path returns before findings are read at all. The `NOTE:` added by `_adverse_verdict`
keys on `verdict`, never on findings, so a record that says `ship` while carrying open CRITICALs
produces no note. The behaviour C1 documented is unchanged; only the sentence that pointed at it
was removed. This is the priority-1 shape: a real open CRITICAL suppressed by a resolution whose
evidence addresses a different claim.

**Smallest fix:** in the `ack` branch, enumerate open BLOCKING findings across all records in the
`REVIEW_WAIVED` warning. The waiver may still pass; it must not be silent about what it is passing.

---

## B3-6 — MEDIUM — the hook-message guards collect by syntax, so four of six ways to shout stay green

`_hook_messages()` collects only `echo "…" >&2` and `(print|block)("…`. `_message_blocks()` collects
only bash echoes. Anything else a hook writes to a person is invisible to both guards.

**Reproduced** by appending a line to `ai/claude/hooks/check-hitl-context.sh` on the clone and
running `-k "shout or what_to_do"`:

```
[1 failed, 1 passed]  echo "HITL CONTEXT MISMATCH" >&2                       <- caught
[2 passed]            echo "HITL CONTEXT MISMATCH" 1>&2                      <- green
[2 passed]            printf "%s\n" "HITL CONTEXT MISMATCH" >&2              <- green
[2 passed]            msg="HITL CONTEXT MISMATCH"; echo "$msg" >&2           <- green
[2 passed]            cat >&2 <<EOF … HITL CONTEXT MISMATCH … EOF            <- green
[1 failed, 1 passed]  python3 -c 'print("HITL CONTEXT MISMATCH")'            <- caught
```

`printf` to a user is not hypothetical here — `ai/claude/hooks/welcome.sh:60,61,64,69,70` already
prints user-facing lines that neither guard has ever seen. This is the same class as R2B-5 (open,
MEDIUM: "one collector widened and the other not"), one level broader: it is not that one collector
lagged, it is that both enumerate syntax instead of asserting the property.

**Smallest fix:** one collector, matching any line that writes to fd 2 or to stdout in a hook,
shared by both guards.

---

## Areas I attacked and could not break

- **Freshness.** `REVIEW_STALE` held under every probe: branch/tag names rejected as
  `reviewed_sha`, short shas, prefix matching, unreachable commits without a `reviewed_tree`. It is
  still the load-bearing rule and it still holds. (`reviewed_tree` lets a fabricated 7-hex sha pass
  when the tree genuinely matches what ships — content-equivalent, so not a defect.)
- **Lens canonicalisation and DUPLICATE_ROUND.** `consequence-2`, `consequence_bis`, case and
  whitespace variants all collapse correctly; I found no way to file two same-lens reviewers in one
  round undetected.
- **The waiver's owner requirement.** `_acknowledged_skip` genuinely requires an attributed field;
  an unsigned skip is ignored, not honoured. (The silence about findings is B3-5, not this.)
- **`UNBACKED_REVIEW` suppression.** A stub record does disable it — but the stub then trips
  `REVIEW_MALFORMED`, `NOT_INDEPENDENT`, `WRONG_STANCE`, `VERDICT_NOT_SHIP` and `LENS_FLOOR`. Not a
  usable path.
- **The dirty-tree check.** `.hitl/` exemption is correctly scoped; the build-output exemption
  covers only untracked paths under `dist/ build/ out/ target/ node_modules/ .venv/ __pycache__/`,
  and this repo publishes from none of them.
- **`_is_a_review()` (priority 2).** I could construct records satisfying all four fields that are
  not reviews — but that is the attestation limit the module docstring already declares, and it is
  already on the record as R2B-1/R2C-2, both open. I found no *new* structural hole in it, so I am
  not filing one. The reason the floor is not my headline is that B3-1 and B3-2 make it moot: a
  release does not need to fake the floor when it can erase the findings.

---

## Verdict

**DO NOT SHIP.**

Round 2's fix is directionally right and its centre is inverted: it gave every record in the change
the power to *close* a finding, while leaving the power to *validate* a finding with the top round
alone. The result is that the loop this release exists to strengthen now weakens the gate each time
it runs — one more round file retroactively removes the evidence requirement from every earlier
one (B3-2 d/e), and one more record of typos with recycled ids clears the whole ledger (B3-1,
reproduced on this release's own open CRITICALs, exit 0).

**Smallest change that would fix the blocking pair:**

1. In `check_review.py`, move the per-finding validation loop (severity vocabulary, status
   vocabulary, `verified_by`, `accepted_by`, `findings` list-shape) so it runs over **every**
   record in `records`, not only `latest`; and treat a `status` outside `open/fixed/accepted` on a
   BLOCKING finding as open rather than skipping it.
2. Scope `_resolved` to the record that raised the finding — key it on `(source, id)` rather than a
   bare id — and require any finding used to close a BLOCKING one to be BLOCKING itself and carry
   `verified_by` or `accepted_by`.

Those two edits are in one function and close B3-1 and B3-2 together. B3-3, B3-4 and B3-5 are
carry-forwards whose round-2 fixes are cosmetic; they need a decision, not necessarily code, before
this ships.
