# Adversarial review — lens: `bypass` — round 2

**Target:** `54abacb2eabd0da4a050b0e88195545084399fec` (v2.8.0 RC + the round-1 fixes)
**Diffed:** `7a12355..HEAD` (the fixes) and `v2.7.1..HEAD` (the release)
**Question:** round 1 found two CRITICALs and four HIGHs. The fixes add and change checks. How do
you get around them?
**Method:** every finding below was reproduced. Scratch git repo under `mktemp -d`, and two
throwaway copies of the tree (`git archive HEAD | tar -x`) for the mutations. No tracked file in the
repo was modified — `git status --porcelain` is empty at the end of this review as it was at the
start. This report file is the only thing written.
**Baselines established first:** `python3 -m pytest ci/ -q` → **729 passed** in the repo,
**724 passed, 5 skipped** on the `git archive` snapshot used for mutations. The gate on HEAD
correctly blocks today (`REVIEW_STALE` + `VERDICT_NOT_SHIP`, exit 2).

---

## Summary

Ten reproduced findings. Two are CRITICAL, and both are consequences of the round-1 fixes rather
than survivals of the round-1 holes.

The headline: **the `LENS_FLOOR` fix traded a false block for a silent false pass.** It did not just
leave B-2 open, it removed the two warnings that made B-2 audible. And the `verified_by` on B-1 in
the shipped record describes a change to *this repo's change file*, not to the code — the exact
false-closure shape that `UNVERIFIED_FIX` was added in this release to prevent.

| # | Sev | What |
|---|---|---|
| R2-1 | CRITICAL | the release floor now counts records that nothing else in the gate validates |
| R2-2 | CRITICAL | the fix made B-2 worse: an invented lens now clears the floor with **no warning at all** |
| R2-3 | HIGH | B-1's code was never fixed; only this repo's change file was. `release-2.8.0` still silently disables both new checks |
| R2-4 | HIGH | three shipped files, including the upgrade note written for this release, now promise a rule the gate no longer enforces |
| R2-5 | HIGH | the new absence check is byte-exact and single-file; four rewordings and the other shipped copy defeat it |
| R2-6 | HIGH | the widened message-block parser hides a dead-end block behind a remedy in a branch the user never reaches |
| R2-7 | MEDIUM | the widened message collector sees 13 lines of the deploy gate and still misses 16; the *other* collector was not widened at all |
| R2-8 | MEDIUM | B-6 residue: `printf … >&2` and `echo … 1>&2` still invisible; the verbatim 2.7.1 shouting restores green |
| R2-9 | LOW | two scratch review records (`a.yaml`, `b.yaml`, `change_id: GH-100`) were committed into `.hitl/reviews/` by the fix commit |
| R2-10 | LOW | the `LENS_FLOOR` message attributes the all-rounds count to the top round |

---

## R2-1 — CRITICAL — the floor counts records that no other check ever validates

**Priority 1, answered directly: it is a hole, and the specific case you asked about is the least of
it.**

```python
distinct = sorted({canonical_lens(doc.get("lens")) for _, doc in records
                   if str(doc.get("lens", "")).strip()})
```

`records` is every record for the change. Every other record-level check in the gate — freshness,
`stance`, `reviewer.context`, `verdict`, open findings, `verified_by` — runs against `latest` (the
top round) or against the one selected record. So the set of records that can satisfy the release
floor is now *strictly larger* than the set of records the gate is willing to check anything about.

Before the fix that could not happen: everything counted toward the floor was, by construction, in
the governing round and therefore fully validated.

### Reproduction, escalating

Scratch repo, `workflow.id: release`, two commits so an old sha is genuinely stale.

**(a) the case you asked about — round 1 with two lenses, round 5 with one:**

```
$ python3 …/check_review.py --change .hitl/current-change.yaml --reviews .hitl/reviews --root .
[warn] ROUND_DEPTH: this is round 5. …
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

The two records making the "two distinct lenses" claim true reviewed `b8e4f4b9…`; what ships is
`b133bf1b…`, and `code.txt` differs between them. Nothing says so.

**(b) the second "lens" is a record the gate would reject outright if it were in the top round.**
Same setup, `GH-500-round1-user.yaml` rewritten to:

```yaml
lens: user
reviewer: {context: shared-with-the-author, …}
stance: confirm
findings:
  - {severity: CRITICAL, claim: "this deletes the user's uncommitted work on every upgrade", status: open}
verdict: do-not-ship
```

```
$ python3 …/check_review.py --change .hitl/current-change.yaml --reviews .hitl/reviews --root .
[warn] ROUND_DEPTH: this is round 5. …
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

A `do-not-ship`, `confirm`-stance, non-independent record carrying an **open CRITICAL** about data
loss, reviewing a commit that is not what ships, is what makes this release "reviewed through two
distinct lenses". `NOT_INDEPENDENT`, `WRONG_STANCE`, `FINDING_OPEN`, `VERDICT_NOT_SHIP` and
`REVIEW_STALE` are all implemented and all decline to look at it.

**(c) on this release's own records.** Snapshot of HEAD, round-1 findings closed the way the release
would close them, one round-2 record filed at HEAD with `lens: bypass`:

```
$ python3 ci/adversarial/check_review.py --change .hitl/current-change.yaml --reviews .hitl/reviews --root .
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

v2.8.0 can ship having had exactly **one** lens read `54abacb`. The `consequence` and `upgrade`
records that clear the floor read `7a12355` — fifteen files earlier, including all of
`check_review.py`, `test_wiring.py` and the hooks they were reviewing.

### Is that acceptable?

The narrow case — round 1 with two lenses, round 2 re-reviewing one fix with one lens — is
defensible on its own, and the fix's comment is right that the old behaviour punished the normal
loop. Two things make the implementation a hole rather than a judgement call:

1. **It contradicts the gate's own load-bearing rule in its own docstring.** *"the record names the
   commit it reviewed, and the gate fails unless that matches what is about to ship."* The floor now
   accepts, as its evidence, exactly the records that rule was written to reject.
2. **It is silent.** The gate's stated purpose is *"to make skipping one impossible to do silently"*.
   It prints `Release gate: adversarial review present, fresh, and cleared.` — `fresh` is a claim
   about one lens and the sentence covers all of them.

Also: **the semantics changed with no test.** `git diff 7a12355..HEAD --stat -- ci/adversarial/`
shows `check_review.py | 15 +++--` and nothing else. `ci/adversarial/test_check_review.py` was not
touched; every lens-floor test still files both records in round 1, so all of them pass identically
before and after the change and none of them exercises it.

**Smallest fix:** keep the all-rounds count, but (i) count only records that pass the record-level
checks (`stance`, `reviewer.context`, `verdict`), and (ii) warn, naming every lens counted from a
round other than the top and the sha it reviewed. Requiring freshness of counted records would
re-break the loop the fix was made for; removing the silence would not.

---

## R2-2 — CRITICAL — the fix made B-2 worse, and shipping it in this state is not defensible

B-2 (`LENS_FLOOR` counts distinct *strings*) is recorded as `accepted` with
*"partially addressed: counting now spans all rounds."* Counting across all rounds is not a partial
fix for B-2. It is an amplification of it, because the two things that made an invented lens
*visible* are both scoped to the top round:

```python
for pth, doc in latest:          # UNKNOWN_LENS  — top round only
seen.setdefault((n, lens), [])   # DUPLICATE_ROUND — grouped per round
… for _, doc in records          # LENS_FLOOR    — every round
```

So an invented lens in a non-top round counts toward the floor and produces **no output at all**.

```
=== P3a: two invented lenses, both in the governing round (round-1 behaviour) ===
[warn] UNKNOWN_LENS: a.yaml uses lens 'zzz', … It still counts; …
[warn] UNKNOWN_LENS: b.yaml uses lens 'qqq', … It still counts; …
Release gate: adversarial review present, fresh, and cleared.
exit=0

=== P3b: round 1 lens 'bypass!', round 2 lens 'bypass' ===
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

P3b is the whole finding in two lines. One lens, spelled two ways, one character apart, clears a
*two distinct lenses* floor for a release, and the gate prints nothing — not `UNKNOWN_LENS`, not
`DUPLICATE_ROUND`, not `SHALLOW_REVIEW`. Under the pre-fix code the same two records blocked.

**Plainly, as asked: no, shipping with B-2 in this state is not defensible.** Shipping the *round-1*
version of B-2 was arguable — it counted a string it had already told you was not a lens, out loud,
in the same run, so an operator reading the output had what they needed. This version removes the
telling. A deferral is defensible when the residual risk is visible; this one is now invisible, and
it became invisible in the commit that claims to partially address it.

The skill already tells the reader the mechanism, which is how cheap this is to find:
`ai/claude/adversarial-review/SKILL.md:90` — *"Use the catalog's ids verbatim in the record. … a
hand-invented name defeats it silently."* The gate's `UNKNOWN_LENS` answers *"It still counts"*.

**Smallest fix:** `& set(LENSES)` on the floor set, and run the `UNKNOWN_LENS` / duplicate scan over
`records`, not `latest`.

---

## R2-3 — HIGH — B-1's code was not fixed. Only this repo's change file was.

The round-1 finding was that the release-only rules are keyed on a free-text string. The fix changed
the string in `.hitl/current-change.yaml` (`development` → `release`). Both code paths are byte-for-
byte what round 1 reported:

```
ci/adversarial/check_review.py:376   is_release = wf_id == "release"
ai/claude/validate/SKILL.md:92       if [[ "$WF" == "release" ]]; then
```

Reproduced, one record with one lens and a CRITICAL marked `fixed` with no `verified_by`:

```
=== workflow.id: 'release' ===        [BLOCK] LENS_FLOOR + [BLOCK] UNVERIFIED_FIX   exit=2
=== workflow.id: 'Release' ===        [BLOCK] LENS_FLOOR + [BLOCK] UNVERIFIED_FIX   exit=2
=== workflow.id: 'release ' ===       [BLOCK] LENS_FLOOR + [BLOCK] UNVERIFIED_FIX   exit=2
=== workflow.id: 'release-2.8.0' ===  [warn] UNVERIFIED_FIX …                       exit=0
=== workflow.id: 'release/2.8.0' ===  [warn] UNVERIFIED_FIX …                       exit=0
=== workflow.id: 'hitl-release' ===   [warn] UNVERIFIED_FIX …                       exit=0
=== workflow.id: 'development' ===    [warn] UNVERIFIED_FIX …                       exit=0
```

And the shipped `dev-validate` block, run verbatim:

```
$ WF=$(python3 -c "import yaml;d=yaml.safe_load(open('.hitl/current-change.yaml'));print((d.get('workflow') or {}).get('id',''))")
$ echo "$WF"
release-2.8.0
$ if [[ "$WF" == "release" ]]; then echo "gate would run"; else echo "(no output at all)"; fi
(no output at all: the if-branch was not taken, the gate never ran, nothing said so)
```

**Is anything stopping a repeat? No.** Nothing in the release detects a release-shaped change under
a non-release workflow. `ci/` contains no assertion about `workflow.id` at release; the only
adjacent test (`test_the_lens_floor_applies_only_to_release`) asserts the *negative* for `None`,
`development`, `docs`, `brownfield` and would pass unchanged if `is_release` were `False` always.
The actual 2.8.0 defect was not someone naming a workflow oddly — it was doing the release on the
development change that was already open, without `/hitl:dev-start-change` ever classifying it. That
path is exactly as available today as it was on `7a12355`.

**One thing worth naming plainly.** The record shipped for this finding says:

```yaml
- id: B1
  status: fixed
  verified_by: 'release now runs under GH-92-release-2.8.0 (workflow.id: release); check_review.py
    evaluates LENS_FLOOR and UNVERIFIED_FIX against it.'
```

That statement is true and it is not a verification of the claim, which is about a class of failure,
not one instance. `verified_by` was added *in this release* because *"every false closure in the
reports that prompted this carried a real commit that touched the right files; what was missing was
anyone re-running the reproduction."* The reproduction here is `workflow.id: release-2.8.0`, and
re-running it still passes. This is the release's own new check being satisfied by the shape of
closure it exists to catch, in the first record it ever guarded.

**Smallest fix:** `is_release = wf_id == "release" or wf_id.startswith(("release-", "release/"))` in
both places, and print one line whenever the gate runs with `is_release` false, so an unrecognised
workflow name is never a silent downgrade.

---

## R2-4 — HIGH — three shipped files now promise a rule the gate no longer enforces

The `LENS_FLOOR` change was made in the code and nowhere else. Checked each file against itself and
against the fix:

- `CHANGELOG.md`, the upgrade note added by the *same* release: *"On a change whose workflow is
  `release`, **a round** reviewed through fewer than two distinct lenses now fails `LENS_FLOOR`"* —
  false. R2-1(a) shows round 5 with one lens clearing.
- `ai/shared/adversarial-review.md:107`: *"**At `release` two distinct lenses are required** — …
  a review with one lens, or none, is a required step satisfied with nothing in it."* Written under
  the heading **How many** [lenses in a round]. False in the deciding round.
- `ai/shared/templates/adversarial-review-record.yaml:21`, inside the comment on the `lens:` field:
  *"A round is a SET of lenses … At release, two distinct lenses are required."* False.
- `ci/adversarial/check_review.py:370-372`, the comment immediately above the check: *"One lens, or
  a round of two reviewers pointed at the same question, is a required step satisfied with nothing
  in it."* The code four lines below now permits exactly that.

The changelog case is the one that matters: it is the note whose stated job is to tell upgraders
what will newly block them, and it was rewritten in this release *specifically* because an earlier
draft of it was wrong about this check.

---

## R2-5 — HIGH — the absence check is byte-exact and reads one of the two shipped copies

`_flat()` collapses hard wrapping, so splitting the sentence across lines does not work — that part
of the guard is sound. Everything else does.

**Rewordings.** Sentence appended after the new one in `ai/claude/adversarial-review/SKILL.md`, then
`pytest ci/wiring/test_wiring.py -k reviewers_hand_their_report`:

```
[1 passed]  <-- Give each reviewer a distinct, stable name so the reports are attributable.
[1 passed]  <-- Give every reviewer a distinct name so the reports are attributable.
[1 passed]  <-- Give each reviewer a **distinct name** so the reports are attributable.
[1 passed]  <-- Each reviewer needs a distinct name so the reports are attributable.
[1 failed]  <-- Give each reviewer a distinct name so the reports are attributable.
```

One comma passes. Bolding two words passes — in a file where every other instruction of this kind is
bolded. Only the byte-exact 2.7.1 sentence fails.

**The other copy.** The guard reads `ai/claude/adversarial-review/SKILL.md` and nothing else. The
sentence restored **verbatim** in `ai/shared/adversarial-review.md`, plus the comma variant in the
skill:

```
$ grep -n "Give each reviewer" ai/shared/adversarial-review.md ai/claude/adversarial-review/SKILL.md
ai/shared/adversarial-review.md:208:Give each reviewer a distinct name so the reports are attributable.
ai/claude/adversarial-review/SKILL.md:141:Give each reviewer a distinct, stable name so the reports are attributable.
$ python3 -m pytest ci/ -q
724 passed, 5 skipped in 41.92s
```

The instruction that suppressed ten reports is back in both shipped documents and the whole suite is
green.

**This is not hypothetical — half of it is already true in the tree.** `ai/shared/adversarial-review.md`
never received the #88 fix at all. Its "Running one → If you are doing it by hand" section (lines
194-212) still describes the pre-fix handover: no mention of `.hitl/reviews/incoming/` anywhere in
the file (`grep -c incoming` → 0), no warning against naming reviewers, no warning against reading a
transcript, and `Recording the result` still says one record per round —
`.hitl/reviews/<change-id>-round<N>.yaml` — which cannot carry the two lenses the same file demands
four sections earlier. A team following the shared doc gets none of the fix, and the guard added to
protect the fix cannot see them.

**Smallest fix:** assert the *property* (no instruction to name reviewers, e.g. a
`give|assign|name .{0,40}(distinct|unique|own) name` family) rather than the sentence, and run the
whole guard over both `ai/claude/adversarial-review/SKILL.md` and `ai/shared/adversarial-review.md`.
Then carry the #88 fix into the shared doc.

---

## R2-6 — HIGH — the message-block parser hides a dead end behind a branch nobody reaches

`if|elif|else|fi|then|do|done` are now non-breaking. That merges not only the two halves of one
conditional message, but **sibling conditionals** — mutually exclusive branches where only one is
ever printed.

Injected at top level in `ai/claude/hooks/check-hitl-context.sh` (syntax verified with `bash -n`):

```bash
if [[ "${HITL_DEMO_A:-}" == "1" ]]; then
  echo "🔒 This edit is blocked. The tracked state does not allow it." >&2
fi
if [[ "${HITL_DEMO_B:-}" == "1" ]]; then
  echo "FYI: /hitl:dev-start-change opens a new change when you need one." >&2
fi
```

```
MERGED BLOCK -> echo "🔒 This edit is blocked. The tracked state does not allow it." >&2 echo "FYI: /hitl:dev-start-change opens a new change when you need one." >&2
$ python3 -m pytest ci/wiring/test_wiring.py -q
45 passed in 0.41s
$ python3 -m pytest ci/ -q          # on the full snapshot
724 passed, 5 skipped in 49.75s
```

The same file under the **pre-fix** parser:

```
PRE-FIX BLOCK -> echo "🔒 This edit is blocked. The tracked state does not allow it." >&2
```

Reported before, green now. The user who hits path A is stopped with no way forward, and the guard's
remedy is a sentence printed only to the user who was not stopped.

**In fairness, the widening was forced.** I ran the pre-fix parser against the *current* hooks: it
reports exactly one message, `check-hitl-context.sh: "Edits are paused until those agree, so pick
whichever is true:"` — a false positive created by the round-1 hook fix wrapping the `Switch to`
remedy in `if [[ -n "$EXPECTED" ]]`. So something had to change. Treating every shell keyword as
non-breaking is broader than the problem.

**Smallest fix:** make the break depth-aware. Record the conditional depth when a block starts;
`if`/`elif`/`else`/`fi` nested *below* that depth do not break, and an `if` that opens *at* that
depth after the depth has returned to it does. That keeps the legitimate case (a remedy inside a
branch of the message that is already open) and breaks the sibling case.

---

## R2-7 — MEDIUM — one collector was widened; the other was not, and the widened one still misses more than it sees

`_hook_messages()` was widened to `(print|block)\s*\(\s*f?"` because the echo-only scan
*"saw 8 of its lines and certified the 4 a user actually hits as fine."* In the same heredoc:

```
lines the guard NOW sees: 13
user-facing lines it still does NOT see: 16
    blockers.append(f"{iid} ({layer}): {name} — verified without evidence …
    lines.append("  delivery_ready: true cannot be honored on an empty register …
    …
```

Every `• <blocker>` bullet a user reads out of this gate is built with `blockers.append(...)` and is
still invisible. And `_message_blocks()` — the collector behind
`test_a_hook_that_blocks_says_what_to_do_next` — was **not** widened at all: it still collects only
`echo … >&2`, so none of the deploy gate's Python messages are subject to the next-step rule.

Both reproduced together in `check-platform-ready.sh` (`bash -n` clean):

```
266:        lines.append("HITL DEPLOY BLOCKED: REGISTER STATE INVALID. ALL DEPLOYS REFUSED:")
290:    print("  Nothing further can be done from here.", file=sys.stderr)
$ python3 -m pytest ci/wiring/test_wiring.py -q
45 passed in 0.44s
```

A message shouting the exact banned phrase, and the gate's only remedy replaced by a dead end, both
green.

---

## R2-8 — MEDIUM — B-6 residue

Deferred at triage and recorded as *"partially"* addressed. Confirming it is unchanged: the two
strings round 1 used, restored through the two idioms the collector still cannot see:

```
171:  printf "%s\n" "HITL CONTEXT MISMATCH: NO ACTIVE CHANGE. ALL EDITS BLOCKED." >&2
172:  echo "HITL BLOCKED: STATE INVALID. EDITS ARE BLOCKED." 1>&2
$ python3 -m pytest ci/wiring/test_wiring.py -q
45 passed in 0.42s
```

`\s*>&2` cannot match past the `1`. Noted as unchanged, not as a new finding.

---

## R2-9 — LOW — scratch records committed into the governance directory

```
$ git ls-files .hitl/reviews/
.hitl/reviews/GH-92-release-2.8.0-round1-bypass.yaml
.hitl/reviews/GH-92-release-2.8.0-round1-consequence.yaml
.hitl/reviews/GH-92-release-2.8.0-round1-upgrade.yaml
.hitl/reviews/a.yaml
.hitl/reviews/b.yaml
$ git log --oneline -1 -- .hitl/reviews/a.yaml
54abacb fix(release): round-1 review findings …
```

`a.yaml` and `b.yaml` are `change_id: GH-100`, `lens: functionality` / `fitness`, `reviewed_sha:
7a12355…` — fixtures from the round-1 reproduction, committed by the fix commit into the directory
the gate reads. Inert today (the change_id does not match), and permanent: records are kept forever.
This is B-3's other half in the flesh — a record nobody reads that nobody mentions. The
`FOREIGN_RECORD` warning round 1 proposed would have caught it the first time the gate ran.

Related, one line: `.gitignore` now excludes `.hitl/reviews/incoming/`, so the reports behind a
released review are never retained. The record's `reproduction` field becomes the only surviving
evidence for a `verified_by` claim.

---

## R2-10 — LOW — the block message attributes the all-rounds count to the top round

```
$ # round 1: lens 'bypass'.  round 2: lens '' (none recorded).
[BLOCK] LENS_FLOOR: round 2 was reviewed through 1 lens (bypass) — a release needs at least 2 …
```

Round 2 was reviewed through zero lenses. The count is across all rounds; the sentence says it is
about `round %s`. Someone acting on this message looks at the wrong round.

---

## Areas I attacked and found sound

- **Freshness.** Untouched by the fixes and still load-bearing: `REVIEW_STALE` fires correctly on
  HEAD today, branch/tag names in `reviewed_sha` are still rejected, and the `reviewed_tree`
  fallback still requires an exact tree match. It is the reason R2-1 is a hole rather than a
  catastrophe — the *deciding* record must still be fresh.
- **The empty-`expected_branch` hook fix** (`check-hitl-context.sh`) is correct: the block stays
  hard, `''` never reaches the user, the two remedies that still apply survive, and
  `test_a_change_with_no_recorded_branch_never_says_switch_to_nothing` exercises the real hook in a
  real repo rather than grepping for a sentence.
- **The `check-platform-ready` test rewrite** to `_says_empty` / `_says_unreadable` is the right
  direction — properties, not phrases — and it kept the fail-closed assertion
  (`"derived from items that are not there"`) that carries the actual rule. It still blocks in every
  case it blocked before.
- **`_flat()`** genuinely defeats the hard-wrap evasion; that half of R2-5's guard is sound.
- **Fail-closed behaviour** on empty / non-mapping / unparseable records and on unexpected
  exceptions is unchanged and still exits 2.
- **The rest of the wiring suite.** Reachability, wrapper markers, hook completeness and onboarding
  agreement all still hold; I found no mutation that broke the underlying property while keeping
  them green, beyond the ones reported above.

---

## VERDICT: DO NOT SHIP

Not because round 1's holes are still open — most were consciously deferred to #92 and that is a
legitimate call. Because **two of the six fixes made the thing they touched weaker than it was
before**:

- `LENS_FLOOR` was blocking one lens loudly. It now clears one lens silently, counting records that
  no other check in the gate will look at (R2-1), and it removed the warnings that made the deferred
  B-2 audible (R2-2).
- `_message_blocks` was reporting a dead-end message. It now merges it with a sibling branch (R2-6).

And the finding closed as `fixed` with `verified_by` (R2-3) was closed by editing this repo's change
file, not the code — which is the precise failure mode `UNVERIFIED_FIX` was added in this release to
prevent, occurring in the first record it guarded.

### The smallest change that would fix it

Four edits, none structural. Everything else can follow in #92.

1. **R2-1 + R2-2**, `ci/adversarial/check_review.py`, one block:
   ```python
   counted = [(p, d) for p, d in records
              if str(d.get("stance", "")).strip().lower() == "refute"
              and str((d.get("reviewer") or {}).get("context", "")).strip().lower() == "clean"]
   distinct = sorted({canonical_lens(d.get("lens")) for _, d in counted
                      if str(d.get("lens", "")).strip()} & set(LENSES))
   ```
   and move the `UNKNOWN_LENS` loop from `latest` to `records`, and warn — not block — naming any
   lens counted from a round other than the top, with the sha it reviewed. That keeps the loop the
   fix was written to unbreak and removes the silence, which is the gate's stated purpose.
   Add the test that the semantic change shipped without: a release whose top round has one lens.

2. **R2-3**, two lines: `is_release = wf_id == "release" or wf_id.startswith(("release-", "release/"))`
   in `check_review.py`, the same condition in `ai/claude/validate/SKILL.md:92`, and one printed line
   whenever the gate runs with `is_release` false so the downgrade is never silent. Then re-open B1
   as `open`; its `verified_by` does not describe a fix to the defect.

3. **R2-4**, three sentences: `CHANGELOG.md`, `ai/shared/adversarial-review.md:107`,
   `ai/shared/templates/adversarial-review-record.yaml:21` — say what the gate does, whichever way
   (1) resolves.

4. **R2-6**, depth-aware break in `_message_blocks` (see the finding).

R2-5 is the one I would not let slide to #92 either, because half of it is already live: the shared
document that ships to every product repo never received the #88 fix, and the guard added to protect
that fix reads the other file.

**One thing to keep.** The round-1 fix to `_hook_messages` and the `_says_empty`/`_says_unreadable`
rewrite are both the right kind of change — they replaced a phrase match with a property. Every
finding above is a case where the same commit did the opposite: fixed the instance
(`workflow.id`, one sentence, one collector) and left the class.
