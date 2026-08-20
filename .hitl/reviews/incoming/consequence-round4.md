# Adversarial review — round 4, consequence lens

- **State reviewed:** `1d4b2fd439fe9c917761bc94521c6be45a058e63` on `main`
- **Scope:** `git diff ff879f3..HEAD` (the removal) inside `git diff v2.7.1..HEAD` (the whole release)
- **Stance:** refute. Lens: consequence — what does this destroy, expose, or make unrecoverable.
- **Reviewer context:** clean.
- **Baseline:** `python3 -m pytest ci -q` at HEAD → `721 passed in 48.08s`. Every fixture below was
  built against that green suite.
- **Method:** all fixtures in `mktemp -d` throwaway git repos, driven by a differential harness that
  loads `check_review.py` from `git show v2.7.1:` and from HEAD side by side and compares block
  codes on byte-identical inputs. No tracked file was modified (`git status --porcelain` empty at
  start and finish). This report is the only file written under `.hitl/`.

## Verdict

**DO NOT SHIP.**

The removal of `LENS_FLOOR` and `UNVERIFIED_FIX` is clean *as code*: no orphan identifier, no
half-removed branch, no dead import, no test asserting a check that no longer exists. I could not
break it. That part is sound and I say so plainly.

What is not sound is everything the removal claims about itself, and the one behaviour it kept.

Three things, in order of consequence:

1. The CHANGELOG's two load-bearing factual claims about this release are both false, and both are
   reproducibly false. One of them ("nothing that validated before this release fails now") is a
   *stronger* restatement of a HIGH that round 1 already found, marked `fixed`, and recorded
   `verified_by` against. The removal commit reverted the fix and reinstated the defect.
2. Four of the ten CRITICALs are not in the removed checks. They are in the code that ships. The
   removal does not touch them, and the CHANGELOG asserts the opposite twice.
3. The one behaviour kept ships with zero test coverage — deleting it entirely does not fail a
   single test in the 721 — and it is defeated by the default finding id in the shipped template,
   by a one-word typo, and by the literal word `deferred`, which the new triage step teaches.

Four CRITICALs, four HIGHs, three MEDIUMs. All reproduced.

---

## CRITICAL-1 — "Nothing that validated before this release fails now" is false in five shapes

`CHANGELOG.md:113` states, in bold, under **Note for existing projects**:

> Run `/hitl:dev-update`. **Nothing that validated before this release fails now.**

This is the sentence an upgrading team reads before running `dev-update`. It is wrong five ways.

**Reproduction.** Scratch harness holding both validators:

```
W=$(mktemp -d); mkdir -p "$W/old" "$W/new"
git show v2.7.1:ci/adversarial/check_review.py > "$W/old/check_review.py"
cp ci/adversarial/check_review.py "$W/new/check_review.py"
```

Each fixture is a throwaway git repo with one commit, a `.hitl/current-change.yaml`, and review
records naming that commit. Both validators are called with the same `(change, reviews, sha, root)`.
Observed output:

```
B. round1 consequence + destructiveness        v2.7.1=['clean']   HEAD=['DUPLICATE_ROUND']
C. round1 security + security-2                v2.7.1=['clean']   HEAD=['DUPLICATE_ROUND']
K. round1 data + migration                     v2.7.1=['clean']   HEAD=['DUPLICATE_ROUND']
L. round1 upgrade + install                    v2.7.1=['clean']   HEAD=['DUPLICATE_ROUND']
D. r1 open CRITICAL, r2 clean ship             v2.7.1=['clean']   HEAD=['FINDING_OPEN']
H. r1 open CRITICAL, r2 ship (development)     v2.7.1=['clean']   HEAD=['FINDING_OPEN']
F'. sibling open CRITICAL sorts first          v2.7.1=['clean']   HEAD=['FINDING_OPEN']
G'. sibling unsigned acceptance sorts first    v2.7.1=['clean']   HEAD=['UNSIGNED_ACCEPTANCE']
```

Five distinct classes, none of them the acknowledged change alone:

- **`DUPLICATE_ROUND` on alias pairs.** `canonical_lens()` is new in this release and resolves
  `destructiveness→consequence`, `migration→data`, `install→upgrade`, `perf→scalability`. A 2.7.1
  round reviewed through `consequence` + `destructiveness` — two different words, and the shipped
  doc calls these "older names that still appear in records written before the catalog existed" —
  was clean at 2.7.1 and now blocks. This is not disclosed anywhere. It is not the behavioural
  change the release admits to. It hits precisely the records the alias map exists to accommodate.
- **`DUPLICATE_ROUND` on numbered reviewers.** `security` + `security-2` was the obvious 2.7.1-era
  way to file two reviewers; it validated. It now blocks.
- **`FINDING_OPEN` from an earlier round** — the acknowledged change, which the CHANGELOG describes
  *nine lines after* asserting nothing fails. It also fires on `development`, `docs` and
  `brownfield` changes (fixture H), not only `release`.
- **`FINDING_OPEN` / `UNSIGNED_ACCEPTANCE` from a sibling record in the top round.** Whether these
  fired at 2.7.1 depended on `sorted(os.listdir())` — the sibling had to sort last. Rename the file
  and the same records flip from clean to blocking.

**Why this is CRITICAL rather than a doc nit.** This exact defect is round 1's `C2-H1`, recorded in
`.hitl/reviews/GH-92-release-2.8.0-round1-consequence.yaml:29` as HIGH, `status: fixed`, with a
`verified_by` describing the corrected note. Commit `1d4b2fd` deleted that corrected note and
replaced it with an absolute claim that is false in *more* shapes than the one round 1 caught —
because the removal only reasoned about `LENS_FLOOR` and `UNVERIFIED_FIX` and forgot that
`canonical_lens` and the carry-forward also change validation outcomes. A finding closed on evidence,
reopened wider, by the commit that closed the round.

The consequence is specific: a team reads "nothing fails", runs `dev-update` mid-release, and their
release gate blocks on records they cannot change without rewriting review history.

---

## CRITICAL-2 — four of the ten CRITICALs are in the code that ships, and the CHANGELOG says twice that they are not

`CHANGELOG.md:120` and `:131`:

> Three rounds of independent review found **ten CRITICAL findings, every one of them inside those
> two checks** — and none anywhere else in this release.
>
> What did ship from that work, because it is independent of both rules and **found nothing in three
> rounds**: an open CRITICAL or HIGH now survives every round…

**Reproduction.** Count the CRITICALs in the reports on disk:

```
grep -n "^## " .hitl/reviews/incoming/bypass-round3.md
  16:## B3-1 — CRITICAL — one record of LOW typos closes every open CRITICAL and HIGH in the change
  75:## B3-2 — CRITICAL — adding a round makes the gate weaker: every integrity rule reads only the top round
grep -n "^## " .hitl/reviews/incoming/consequence-round3.md
  26:## CRITICAL-1 — a reused finding id silently closes an open CRITICAL from an earlier round
  86:## CRITICAL-2 — earlier-round findings are never schema-validated; one wrong word disables the carry-forward
```

Round 1 contributes 3 (B-1, B-2, C1), round 2 contributes 3 (R2B-1, R2B-2, R2C-1) — those six are
inside `LENS_FLOOR`. Round 3 contributes 4, and **all four are inside the carry-forward block that
ships**, `check_review.py:444-479`. Ten total, six in the removed checks, four in the retained one.

The second claim is stronger and worse. The carry-forward did not exist during rounds 1 and 2:

```
git log --oneline -S"_resolved" -- ci/adversarial/check_review.py
  ff879f3 fix(adversarial-review): round-2 findings — an open finding survives every round (#95)
```

It landed in `ff879f3`. Round 3 reviewed exactly `ff879f3` — both round-3 reports name it as the
state reviewed — and found four CRITICALs in it. "Found nothing in three rounds" is a claim about
code that existed for one round and failed it.

**Consequence.** The stated justification for keeping this behaviour while cutting the other two is
"it is the part that survived review". It is the part that failed the only review it ever had. The
decision to keep it was made on a false premise, and the CHANGELOG carries that premise to every
reader as the release's own account of what happened. Findings III through VI below are the four
CRITICALs in question, independently reproduced by me rather than taken on the round-3 reports'
word — every one still fires at `1d4b2fd`.

---

## CRITICAL-3 — the kept behaviour has no test; deleting it entirely passes the whole suite

`ff879f3` added **nothing** to `ci/adversarial/test_check_review.py`:

```
git show ff879f3 --stat -- ci/adversarial/test_check_review.py
(no output — the file is not in the commit)
```

**Reproduction — mutation test.** Clone to scratch, delete the entire carry-forward loop
(`check_review.py:461-471`, the twelve lines that assemble earlier-round findings), leaving
`findings = []`:

```
Baseline (unmutated clone):  716 passed, 5 skipped in 42.32s
Mutated (behaviour deleted): 716 passed, 5 skipped in 43.46s
```

Identical. The only behavioural change in HITL 2.8.0 can be removed in full and the 721-test suite
does not notice.

**Consequence.** The next person to touch `check_review.py` has no signal. `test_check_review.py`
lost 6 tests in the removal and gained none; the release's net effect on that file is 139 lines
added at `7a12355` and 72 deleted at `1d4b2fd`, none of them covering what ships. Round 2 already
raised this as a MEDIUM ("the CRITICAL fix shipped with no test",
`GH-92-release-2.8.0-round2-consequence.yaml:32`) and it is still open and still true.

---

## CRITICAL-4 — one word in an earlier round deletes an open CRITICAL, and the word is one the new triage step teaches

`check_review.py:461-471` carries an earlier round's finding forward only if
`status.strip().lower() in OPEN_STATES` and `severity.strip().upper() in BLOCKING`. Anything else is
skipped by `continue` — never validated, never reported. The schema checks that would catch it
(`REVIEW_MALFORMED` at `:488` and `:493`) run over the assembled list, which by then contains only
top-round entries plus the ones that already passed the filter. So the vocabulary is enforced in the
top round and unenforced everywhere else.

**Reproduction.** r1 = one CRITICAL `deletes the user database on upgrade`, verdict do-not-ship;
r2 = clean, verdict ship. Only r1's `status` string varies:

```
r1 CRITICAL status='open',     r2 clean ship   v2.7.1=['clean']   HEAD=['FINDING_OPEN']
r1 CRITICAL status='deferred', r2 clean ship   v2.7.1=['clean']   HEAD=['clean']
r1 CRITICAL status='triaged',  r2 clean ship   v2.7.1=['clean']   HEAD=['clean']
r1 CRITICAL status='wontfix',  r2 clean ship   v2.7.1=['clean']   HEAD=['clean']
r1 CRITICAL status='Open?',    r2 clean ship   v2.7.1=['clean']   HEAD=['clean']
```

Same for severity, and for a malformed `findings` block:

```
Q3. r1 severity 'Criticl', r2 clean            HEAD=['clean']
S.  r1 findings is a mapping, r2 clean         HEAD=['clean']
```

The identical `status: 'opne'` in the **top** round is a hard `REVIEW_MALFORMED`. So the gate's
strictness is inverted: the round most likely to be sloppy (an old one, edited during triage) is the
one it does not check.

**Why `deferred` specifically.** This release introduces the triage step, whose three answers are
**fix / accept / defer** (`SKILL.md:200`). The table maps defer to `status: accepted`, but `deferred`
is the word the step puts in the agent's mouth, it is a plausible YAML value, it reads as honest
bookkeeping, and it silently deletes the finding. The feature that generates the word and the code
that mishandles it shipped in the same release and were never checked against each other.

---

## HIGH-1 — the default finding id in the shipped template closes an unrelated open CRITICAL

`_identity()` at `check_review.py:444` keys a finding on `(id, normalised claim[:60])`, and
`_resolved` at `:452` is a flat set pooled across **every** record for the change. A carried-forward
finding is dropped if its id **or** its truncated claim appears anywhere in that set — same round or
not, same lens or not, same severity or not, same claim or not.

Sixty lines above, the same file states the premise that makes this unsafe:

```
check_review.py:378   # ... Compared on the claim, because ids restart per round.
```

Ids restart per round; an id resolves globally. Both cannot be true.

**Reproduction.**

```
M. r2 reuses id F1 for an unrelated fix        v2.7.1=['clean']   HEAD=['clean']
N. control: r2 uses id F9                      v2.7.1=['clean']   HEAD=['FINDING_OPEN']
```

Fixture M: r1 carries `id: F1`, CRITICAL, open, "deletes the user database on upgrade". r2 carries
`id: F1`, LOW, fixed, "typo in a log line". The CRITICAL vanishes. Change one character of the id
(fixture N) and it blocks.

This is not an exotic collision. `ai/shared/templates/adversarial-review-record.yaml:39` seeds the
example finding as `id: F1`. Every record written from the template starts at F1.

The claim path collides too, at 60 normalised characters:

```
O. 60-char claim prefix collision              v2.7.1=['clean']   HEAD=['clean']
   norm A: the release gate does not verify that the reviewer was indep
   norm B: the release gate does not verify that the reviewer was indep
```

Two genuinely different findings, one LOW-fixed in a later round, and the CRITICAL is gone.

---

## HIGH-2 — an unsigned acceptance in an earlier round closes a CRITICAL, and adding a round is what makes it work

`_resolved` accepts `status: accepted` with no regard for `accepted_by`. The `UNSIGNED_ACCEPTANCE`
check at `:499` runs only over the assembled list, which excludes earlier-round entries that were
already dropped as resolved. So the two rules are in the same file, forty lines apart, disagreeing.

**Reproduction.**

```
R.  r1 CRITICAL accepted, no accepted_by, r2 clean   v2.7.1=['clean']              HEAD=['clean']
R2. same but single round                            v2.7.1=['UNSIGNED_ACCEPTANCE'] HEAD=['UNSIGNED_ACCEPTANCE']
```

The identical record blocks on its own and passes once a second round exists. Adding review makes
the gate weaker.

**Consequence.** `accepted_by` is described by the skill as "the whole point of this step"
(`SKILL.md:202`) and by the template as "accepting risk is someone's decision". The ownership
property it exists to create evaporates on the next round, silently. Nobody is named, and nothing
says so.

---

## HIGH-3 — every committed record's reproduction points into a gitignored file

The new file-based delivery writes reviewer reports to `.hitl/reviews/incoming/<lens>-round<N>.md`.
That directory is ignored:

```
git check-ignore -v .hitl/reviews/incoming/bypass-round2.md
  .gitignore:27:.hitl/reviews/incoming/   .hitl/reviews/incoming/bypass-round2.md
```

Every committed record for this change delegates its evidence there:

```
grep -rn "reviews/incoming" .hitl/reviews/*.yaml
  round1-bypass.yaml:35:      reproduction: See .hitl/reviews/incoming/bypass-round1.md B-3, B-5, B-6, B-7, B-8.
  round1-upgrade.yaml:46:     reproduction: See .hitl/reviews/incoming/upgrade-round1.md F6-F12.
  round1-consequence.yaml:50: reproduction: See .hitl/reviews/incoming/consequence-round1.md MEDIUM-1..3, LOW-1..3.
  round2-bypass.yaml:20:      reproduction: See .hitl/reviews/incoming/bypass-round2.md R2-1, escalating fixtures.
  round2-consequence.yaml:28: reproduction: See .hitl/reviews/incoming/consequence-round2.md fixtures C, D, E.
```

Five of five records. `git ls-files .hitl/reviews/` returns only the five YAML files; not one report.

The template says of `reproduction`: *"the command and observed output. A finding nobody reproduced
is a guess."* The committed records contain neither a command nor an output — only a pointer to
material that `git clean -xdf`, a fresh clone, or a different machine destroys permanently.

**Why this is a consequence finding and not bookkeeping.** Three open CRITICALs and four open HIGHs
in this change now block the gate. Under the kept carry-forward they block *every future round* until
someone resolves them. The only record of why they are real is untracked. And the largest decision in
this release — cutting two checks — rests entirely on `bypass-round3.md` and `consequence-round3.md`,
which have **no review record at all** (`.hitl/reviews/` contains rounds 1 and 2 only) and are
themselves ignored. Round 3 exists nowhere a reader of this repository can find it.

`.gitignore:26` justifies the exclusion: *"They are working material, not governance state — the
record under `.hitl/reviews/` is what counts."* That is true only if the record stands alone. It
does not.

---

## HIGH-4 — a dropped lens is now taught as a skip, and the sentence warning against that skip was deleted in the same commit

New in this release, in two shipped files:

```
ai/claude/adversarial-review/SKILL.md:73  **A dropped lens is a skip.** Record it like any other, …
ai/shared/adversarial-review.md:119       - **A lens they drop is a skip**, recorded like any other, …
```

`_acknowledged_skip()` at `check_review.py:165` matches on `step == "adversarial_review"` with any
attribution field, and returns early with a waiver — no findings inspected, exit 0.
`adversarial_review` is the literal step key in the release workflow and in this repo's own
`.hitl/current-change.yaml:50`. "Record it like any other" plus that step name is a full gate waiver.

**Reproduction.** One open CRITICAL, one skip entry whose reason is a dropped lens:

```
skips: [{step: adversarial_review, ack_by: pappar, reason: "dropped the security lens - covered by the pentest"}]
findings: [{id: F1, severity: CRITICAL, status: open, claim: "deletes the user database on upgrade"}]

HEAD blocks= NONE
    [warn] REVIEW_WAIVED: GH-1 is shipping WITHOUT an adversarial review.
            Acknowledged by pappar: dropped the security lens - covered by the pentest
```

Exit 0. The CRITICAL is never named.

The waiver behaviour itself is unchanged from v2.7.1 — that is not the finding. The finding is that
this release adds the instruction that leads someone there, and `1d4b2fd` deleted the only sentence
in the codebase that warned against it:

```
git diff ff879f3..HEAD -- ci/adversarial/check_review.py
-                "        Do NOT reach for the adversarial_review skip to clear this: that waives "
-                "the whole gate, including every open finding, and records that no review "
-                "happened at all — which would be false."
```

Removing the check removed the warning. Nothing inherited it.

---

## MEDIUM-1 — the shipped docs state the opposite of the shipped behaviour, and the behaviour is documented nowhere

```
grep -rn "carry\|earlier round\|any round\|survives every round" \
  ai/claude/adversarial-review/SKILL.md ai/shared/adversarial-review.md \
  ai/shared/templates/adversarial-review-record.yaml
```

Returns nothing about the carry-forward. The only shipped statement on the subject contradicts it:

```
ai/shared/templates/adversarial-review-record.yaml:12
  round: 1     # highest round decides; earlier rounds are history
```

`check_review.py:326` still says the same thing — *"The newest round is the one that decides. Earlier
rounds are history"* — 118 lines above the comment that says the opposite. Meanwhile `SKILL.md:239`
says *"Earlier rounds stay — the trajectory across rounds is evidence in itself."* Three shipped
files, two positions.

The only description of the new behaviour is in `CHANGELOG.md`, which is not what anyone reads while
writing a record.

## MEDIUM-2 — `verified_by` is a field nobody is told to write and nothing reads

The template keeps `verified_by` and tells you to fill it in because "the next round reads it".
`SKILL.md` Step 6 ("Write the record") lists the rules that matter and never mentions it. Step 4 and
Step 5 never tell a later round to read it. No code reads it. It is a field with no writer and no
reader, retained so the CHANGELOG's "Fixed" section has something to point at — and that section
still opens with *"Marking a finding fixed required no evidence at all"* under the heading **Fixed**,
which it is not.

## MEDIUM-3 — the no-shouting guard is defeated by two leading spaces

`ci/wiring/test_wiring.py:431` matches `r'"HITL [A-Z]{2,}'` — the shout must abut the opening quote.

**Reproduction.** In a scratch clone, replace the rewritten layer-1 message in
`check-hitl-context.sh` with:

```
  echo "  HITL BLOCKED: no active change for this project/branch. ALL EDITS ARE BLOCKED." >&2
```

```
python3 -m pytest ci/wiring/test_wiring.py -q -k "shout or next"  →  2 passed
python3 -m pytest ci -q                                           →  716 passed, 5 skipped
```

A fully capitalised internal-state shout, in the exact hook the guard was written for, passes the
entire suite. `printf`, single quotes, heredocs and variables are also outside the collector
(`_hook_messages` matches only `echo "…" >&2` and `print(`/`block(`). The 46 rewritten messages are
correct today and unprotected tomorrow.

---

## Areas checked and found sound

- **The removal itself, as code.** `grep -rn "LENS_FLOOR|UNVERIFIED_FIX|RELEASE_RULES_INACTIVE|
  _looks_like_a_release|RELEASE_LENS_FLOOR"` over the tree hits only historical review records. No
  orphan reference, no dangling branch, no unreachable code, no doc or template promising either
  check. `is_release`/`wf_id` are gone entirely; `check_review.py` no longer reads `workflow` except
  in `_claimed_without_record`. No test was left asserting a removed code path, and no test now
  passes vacuously *because of the removal* — the six deleted tests were deleted, not neutered.
  Leftovers are cosmetic: `_multi(workflow_id=…)` and `_rel(extra_change=…)` are now dead
  parameters, and the deletions left 4-6 blank-line runs and orphaned `_rel` from its section
  heading.
- **Hook exit codes.** Ran `check-hitl-context.sh` at v2.7.1 and at HEAD across six scenarios
  (no change / missing field / branch mismatch / mismatch with no `expected_branch` / design not
  approved / bootstrap path). Exit codes identical in all six. The bootstrap exemption
  (`.hitl/*|.claude/*`) matches what the new message promises. The domain-boundary hook's
  "the edit went through — this is a note, not a block" is accurate: it is PostToolUse and exits 0.
- **The lens catalog.** The 13 ids in `check_review.py:46` match the catalog in
  `ai/shared/adversarial-review.md` exactly, both directions. (`functionality→fitness` remains the
  undocumented fifth alias — already open as round 1's `U-M`.)
- **The catalog page generator.** `check_order_covers` does what it claims; regeneration in a clean
  clone is byte-identical to the committed page; the new `getting-started.html` nav target exists.
- **Site copy.** `index.html`'s release-gate claim describes freshness binding and the signed
  waiver, not a lens floor. It did not inherit the over-promise.

---

## Smallest change that would fix it

Not a redesign. Four edits, none of them touching the validator's logic:

1. **`CHANGELOG.md:113`** — replace *"Nothing that validated before this release fails now"* with the
   five shapes that do fail: alias and numbered lens pairs in one round now collide
   (`DUPLICATE_ROUND`), an earlier round's open CRITICAL/HIGH now blocks on every workflow, and a
   sibling record's open finding or unsigned acceptance now blocks regardless of filename order.
2. **`CHANGELOG.md:120,131`** — say four of the ten CRITICALs are in the carry-forward that ships,
   that round 3 found them at `ff879f3`, and that they are open. Delete "found nothing in three
   rounds".
3. **`check_review.py:461-471`** — make the earlier-round filter fail loud instead of quiet: any
   earlier-round finding whose `status` or `severity` is outside the vocabulary, or whose `findings`
   is not a list, raises `REVIEW_MALFORMED` exactly as it does in the top round. Three lines. This
   closes CRITICAL-4 and half of HIGH-2, and it is the one change that cannot make a passing record
   fail without also telling the author exactly which word is wrong.
4. **`adversarial-review-record.yaml:12`** — `# highest round decides; an open CRITICAL or HIGH from
   ANY round still blocks until it is fixed or accepted`. And drop the "a dropped lens is a skip"
   instruction from `SKILL.md:73` / `adversarial-review.md:119`, or bind it to a step key that is not
   `adversarial_review`.

HIGH-1 (id collision) and HIGH-3 (gitignored evidence) are the two that genuinely belong to the #92
redesign rather than to this release — but HIGH-3 costs one line of `.gitignore` to stop the bleeding,
and leaving it is choosing to lose the evidence for three open CRITICALs the moment anyone runs
`git clean -xdf`.
