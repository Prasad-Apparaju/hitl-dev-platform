# Adversarial review — lens: `bypass` — round 1

**Target:** `7a123555727f92e8dc1ae3595249a552ec334dcb` (v2.8.0 RC), diffed against `v2.7.1`
**Question:** this release adds checks. How do you get around them?
**Method:** every finding below was reproduced. Scratch repos under `mktemp -d`, a throwaway copy of
the tree for the wiring mutations, both deleted. No tracked file in the repo was modified.
**Baselines established first:** the gate blocks correctly on a single-lens release
(`[BLOCK] LENS_FLOOR`), and `python3 -m pytest ci/ -q` is **723 passed, 5 skipped** on an unmutated copy.

---

## Summary

Thirteen reproduced findings. Two are CRITICAL.

The headline is not a hole in `check_review.py`. It is that **both new release-only checks were
inert for the release that introduces them** — the gate never executed on `7a12355`. Everything
below it is a hole in a check that, on this commit, was not running anyway.

| # | Sev | What |
|---|---|---|
| B-1 | CRITICAL | `LENS_FLOOR` and `UNVERIFIED_FIX` did not run on the release that ships them |
| B-2 | CRITICAL | `LENS_FLOOR` counts distinct *strings*, not distinct *lenses* |
| B-3 | HIGH | a record whose `change_id` differs only in case is dropped silently |
| B-4 | HIGH | `verified_by: no` satisfies `UNVERIFIED_FIX`; `status: accepted` skips it entirely |
| B-5 | HIGH | two fabricated empty round-2 records bury a round-1 open CRITICAL, with no warning |
| B-6 | HIGH | the no-shouting guard cannot see `printf … >&2` or `echo … 1>&2` |
| B-7 | HIGH | `test_icons_stay_out_of_the_aligned_trail` inspects zero lines; 75 real trail lines already violate it |
| B-8 | MEDIUM | the next-step guard only inspects messages that use one of four words; a comment line merges two messages |
| B-9 | MEDIUM | an unparseable record is downgraded to a warning that states something false |
| B-10 | MEDIUM | the catalog/gate agreement test is blind to hyphenated lens ids |
| B-11 | MEDIUM | the documented record filename gives one file per round; the new floor needs two |
| B-12 | LOW | the icon/substance guard is a sentence-presence check on a file no hook reads |
| B-13 | LOW | `--sha` exits 0 on a stale target |

---

## B-1 — CRITICAL — the two new release-only checks did not run on their own release

`LENS_FLOOR` and `UNVERIFIED_FIX` are both behind `is_release`, which is
`ci/adversarial/check_review.py`:

```python
wf_id = str(wf.get("id", "")).strip().lower() if isinstance(wf, dict) else ""
is_release = wf_id == "release"
```

and the only place in the shipped product that invokes the gate — `ai/claude/validate/SKILL.md:85-95`,
the `gates` step — is itself behind the same string:

```bash
WF=$(python3 -c "import yaml;d=yaml.safe_load(open('.hitl/current-change.yaml'));print((d.get('workflow') or {}).get('id',''))")
if [[ "$WF" == "release" ]]; then
  GATE="ci/adversarial/check_review.py"
  ...
fi
```

`.hitl/current-change.yaml` at `7a12355` says `workflow.id: development`.

Reproduction — the block above, run verbatim on the RC:

```
$ git rev-parse HEAD
7a123555727f92e8dc1ae3595249a552ec334dcb
$ WF=$(python3 -c "import yaml;d=yaml.safe_load(open('.hitl/current-change.yaml'));print((d.get('workflow') or {}).get('id',''))")
$ echo "$WF"
development
$ if [[ "$WF" == "release" ]]; then python3 ci/adversarial/check_review.py; else echo ">>> the if-branch was NOT taken."; fi
>>> the if-branch was NOT taken. The adversarial review gate did not run.
```

This is not a stale artifact of one commit. Across the whole range:

```
$ for c in $(git rev-list --reverse v2.7.1..HEAD); do ... done
475121c test(wiring): the fresh-project fixture ...   change_id=GH-86-release-2.7.1          wf=release
...
6b559a3 chore(hitl): retire GH-86-release-2.7.1 ...   (none)
4c9fab9 chore(hitl): open GH-88-adversarial-review-loop  change_id=GH-88-...  wf=development
92ae283 fix(adversarial-review): reports arrive by file  change_id=GH-88-...  wf=development
d655d3b fix(hooks): stop talking like a compiler ...     change_id=GH-88-...  wf=development
84bf7af chore(hitl): widen GH-88's declared scope ...    change_id=GH-88-...  wf=development
7a12355 chore(release): 2.8.0 — release notes, ...      change_id=GH-88-...  wf=development
```

v2.7.1 *was* cut through a `release` workflow (`GH-86-release-2.7.1`). v2.8.0 was not — the release
commit was made on the development change. And forcing the gate to run anyway confirms no record
exists:

```
$ python3 ci/adversarial/check_review.py --change .hitl/current-change.yaml --reviews .hitl/reviews --root .
[BLOCK] REVIEW_MISSING: no review record for GH-88-adversarial-review-loop in .hitl/reviews/
```

Two further degradations of the same string comparison, reproduced on a scratch repo with one lens
and a `CRITICAL` marked `fixed` with no `verified_by`:

```
=== workflow.id: 'release' ===        [BLOCK] LENS_FLOOR + [BLOCK] UNVERIFIED_FIX   exit=2
=== workflow.id: 'development' ===    [warn] UNVERIFIED_FIX ... cleared.            exit=0
=== workflow.id: 'release-2.8.0' ===  [warn] UNVERIFIED_FIX ... cleared.            exit=0
=== workflow.id: 'Release' ===        [BLOCK] LENS_FLOOR + [BLOCK] UNVERIFIED_FIX   exit=2
```

`release-2.8.0` — an entirely reasonable thing to name a release workflow instance — silently drops
both new checks. Nothing prints. There is no "this is a release and the floor did not apply" line
anywhere.

**Why this is the worst of the thirteen:** the escape hatch the file argues for at length
(`_acknowledged_skip`, "a gate with no escape is one that gets deleted from the process") is a
*recorded, attributed, and loudly printed* waiver. This is an unrecorded, unattributed, silent one,
reachable by naming a workflow. The gate's own docstring says its purpose "is to make skipping one
impossible to do silently." On this commit, it was skipped silently.

---

## B-2 — CRITICAL — `LENS_FLOOR` counts distinct strings, not distinct lenses

```python
distinct = sorted({canonical_lens(doc.get("lens")) for _, doc in latest if str(doc.get("lens","")).strip()})
if len(distinct) < RELEASE_LENS_FLOOR:
```

There is no membership test against `LENSES`. The floor is satisfied by any two strings that
`canonical_lens()` does not collapse — including strings that are not lenses at all.

`canonical_lens` strips `[\s_-]*\d+$` and `[\s_-]*(bis|b|two|second)$`. Anything else survives.

Setup: scratch git repo, `workflow.id: release`, two records in round 1, both `verdict: ship`,
`stance: refute`, `reviewer.context: clean`, `reviewed_sha` = HEAD.

```
=== A: lens 'consequence' + 'consequence-2'  (the case the new tests cover) ===
[BLOCK] DUPLICATE_ROUND: round 1 has more than one record for lens 'consequence' ...
[BLOCK] LENS_FLOOR: round 1 was reviewed through 1 lens (consequence) ...
exit=2

=== B: lens 'consequence' + 'consequence-ii' ===
[warn] UNKNOWN_LENS: b.yaml uses lens 'consequence-ii', which is not in the catalog ... It still counts;
Release gate: adversarial review present, fresh, and cleared.
exit=0

=== C: lens 'consequence' + 'consequence.' ===
exit=0

=== E: lens 'bypass' + 'bypass-x' ===
exit=0

=== F: lens 'bypass' + 'bypass (second pass)' ===
exit=0

=== D: lens 'zzz' + 'qqq'  (neither is a lens at all) ===
[warn] UNKNOWN_LENS: a.yaml uses lens 'zzz' ...
[warn] UNKNOWN_LENS: b.yaml uses lens 'qqq' ...
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

Case D is the clean statement of the bug: a release passes a *two distinct lenses* floor with two
lenses that do not exist, and the gate says so out loud in a warning while counting them.

The warning text is the tell. `UNKNOWN_LENS` prints *"It still counts"* — that sentence is correct
for the historical-records rationale it was written for, and it is exactly wrong under the floor
introduced in the same commit. The two features were not checked against each other.

`ci/adversarial/test_check_review.py` has `test_two_reviewers_on_one_lens_cannot_satisfy_the_release_floor`
and `test_an_unknown_lens_warns_but_never_blocks`. The first proves the floor holds against the one
suffix `canonical_lens` strips; the second proves the property that defeats it. Both pass. The suite
documents the hole rather than catching it.

**Smallest fix:** intersect with the catalog.

```python
distinct = sorted({canonical_lens(doc.get("lens")) for _, doc in latest
                   if str(doc.get("lens", "")).strip()} & set(LENSES))
```

with `UNKNOWN_LENS` promoted to a block when `is_release`, since after this change an unknown lens
at release silently contributes nothing to the floor and the reviewer deserves to be told why.

---

## B-3 — HIGH — a `change_id` that differs only in case is dropped, silently

Record collection is an exact, case-sensitive string compare:

```python
if str(doc.get("change_id", "")).strip() == change_id:
    records.append((path, doc))
```

Records that do not match are not counted, not warned about, and not mentioned. A reviewer who types
the change id in lowercase files a `do-not-ship` with an open `CRITICAL` into the correct directory
under the correct filename, and the gate passes without a word.

```
=== L: change file says GH-99; the consequence record says gh-99 ===
  .hitl/reviews/a.yaml                    lens bypass,      ship, no findings
  .hitl/reviews/b.yaml                    lens user,        ship, no findings
  .hitl/reviews/GH-99-r1-consequence.yaml change_id: gh-99, verdict do-not-ship,
                                          findings[0] CRITICAL "this destroys the user's
                                          uncommitted work", status open
[warn] SHALLOW_REVIEW: .hitl/reviews/b.yaml is round 1 with zero findings. ...
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

The filename says `GH-99`. Whitespace *is* handled — `change_id: "GH-99 "` blocks correctly (case M,
`[BLOCK] FINDING_OPEN` + `[BLOCK] VERDICT_NOT_SHIP`). Case is not.

This is the residual of a fix made in this same commit. `_claimed_without_record` carries the comment
*"Match the change_id FIELD, as every other lookup here does. Matching the filename let a valid record
be honoured and reported missing in the same run."* Moving everything to the field was right; the
consequence is that a field/filename disagreement is now invisible everywhere instead of noisy
somewhere.

**Smallest fix:** `.strip().lower()` on both sides, and emit a `[warn] FOREIGN_RECORD` for any
`.yaml` in the reviews directory whose `change_id` does not match — a record nobody reads should
never be a record nobody mentions.

---

## B-4 — HIGH — `UNVERIFIED_FIX`, and an honest judgement of whether it earns its place

The check is `not str(f.get("verified_by", "")).strip()`. Any non-empty stringification passes.

```
=== G: verified_by: x ===                            exit=0, no warnings
=== H: verified_by: no ===                           exit=0, no warnings
=== I: verified_by: 'I did not re-run the reproduction' ===  exit=0, no warnings
```

Case H is the one worth pausing on. YAML parses bare `no` as boolean `False`; `str(False)` is
`"False"`, which is non-empty. **Writing `no` in the field that asks whether you verified it is
accepted as verification.** That is not a determined attacker — that is a plausible typo direction.

And the check does not have to be defeated at all, because `fixed` is not the only resolution:

```
=== J: the CRITICAL is marked `status: accepted, accepted_by: x` instead of `fixed` ===
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

`verified_by` is required only on `state == "fixed"`. One word turns a CRITICAL into an accepted
finding, and `accepted_by` was already required before this release — so the new check adds nothing
on the path that avoids it, and the path that avoids it is *cheaper* than faking a `verified_by`.

**Is the check worth having, given the above?** Partly, and it is worth being precise about which
part.

- As a *machine* gate: no. It cannot distinguish evidence from a character, it is off by default
  (B-1), it is off outside `release`, and it is sidestepped by a one-word status change (J). Nothing
  it blocks could not be unblocked in five seconds by someone who wanted to.
- As a *record*: yes, and this is the real argument. The field is durable and human-readable. When a
  release goes wrong, `verified_by: no` and `verified_by: x` are damning in a way that a missing
  field is not — an absent field reads as an oversight, a filled-in worthless one reads as a choice.
  That is a genuine deterrent against a *self-deceiving* author, which is who the docstring says the
  check is for ("the honest answer and the convenient one were indistinguishable"). It is no
  deterrent at all against a dishonest one, and the docstring should not imply otherwise.

Keep it. Two cheap changes stop it from over-promising: reject values shorter than ~20 characters or
matching `^(x|n/?a|no|none|true|yes|false|done|ok)$` case-insensitively, and require *something* on
`accepted` CRITICALs too — a reason, not just a name — so J stops being the cheap door.

---

## B-5 — HIGH — round inflation buries an open CRITICAL, and round 2 is the silent seam

Only the top round is read. Nothing requires that a blocking finding from an earlier round was
resolved, carried forward, or even acknowledged.

```
=== N: round 1 = the real review; rounds 2 = two fabricated empty records ===
  GH-99-r1-consequence.yaml  round 1  do-not-ship  CRITICAL "destroys uncommitted work"  status open
  a2.yaml                    round 2  lens bypass  ship  findings: []
  b2.yaml                    round 2  lens user    ship  findings: []
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

No output at all. Not one warning line. The two guards that might have spoken are both tuned away
from this:

- `SHALLOW_REVIEW` fires only at `round <= 1`.
- `ROUND_DEPTH` fires only at `round >= 3`.
- `RECURRING_FINDING` needs the same claim in *consecutive* rounds — an empty round 2 has no claims.

Round 2 is the one round number with no coverage, and it is the cheapest number to write. Two empty
records, and a `do-not-ship` with an open CRITICAL disappears without trace.

"The newest round decides" is a defensible design. "The newest round decides and the previous
round's unresolved CRITICALs are never mentioned again" is not, and the gate already has the
machinery to say so — `_adverse_verdict()` finds exactly this and is called only on the waiver path.

**Smallest fix:** call `_adverse_verdict()` on the non-waiver path too and warn when a *lower* round
carries a blocking finding that no record in the top round mentions.

---

## B-6 — HIGH — the no-shouting guard cannot see two ordinary shell idioms

`_hook_messages()` collects only lines matching `echo\s+".*"\s*>&2` after `.strip()`. Anything else
that writes to stderr is invisible to `test_hooks_do_not_shout_their_internal_state`.

The exact strings the guard's own docstring names as the offence, restored via `printf` and `1>&2`:

```
$ # in a throwaway copy of the tree
114:  printf "%s\n" "HITL CONTEXT MISMATCH: NO ACTIVE CHANGE. ALL EDITS BLOCKED." >&2
115:  echo "HITL BLOCKED: STATE INVALID. EDITS ARE BLOCKED." 1>&2
$ python3 -m pytest ci/wiring/test_wiring.py -q
45 passed in 0.41s
```

`1>&2` is not exotic — it is the same redirect written explicitly, and `\s*>&2` cannot match past
the `1`.

Separately, the two patterns are narrow enough that shouting survives even inside a plain `echo`:
`"HITL [A-Z]{2,}` requires the literal string `HITL` immediately after the quote, and
`"[A-Z]{3,}[A-Z ]{6,}:` requires a trailing colon.

```
114:  echo "FATAL CONTEXT ERROR - NO ACTIVE CHANGE FOR THIS PROJECT BRANCH TUPLE" >&2
115:  echo "ALL EDITS ARE BLOCKED. REALIGN THE CONTEXT AND RETRY." >&2
116:  echo "ERROR CODE E_NO_ACTIVE_CHANGE - SEE THE PROTOCOL SPECIFICATION" >&2
$ python3 -m pytest ci/wiring/test_wiring.py -q -k "shout or says_what_to_do"
2 passed, 43 deselected in 0.05s
```

Drop the word HITL and use a dash instead of a colon and the rule is gone. This is the shape the
commit `d655d3b` set out to prevent, reproduced against the guard added to prevent it.

**Smallest fix:** widen the collector to `(echo|printf)\b.*(1?>&2|>&2)` and drop the `HITL` and
trailing-colon anchors — flag any all-caps run of three or more words inside a stderr string.

---

## B-7 — HIGH — the aligned-trail guard inspects zero lines, and the rule is already broken in ship

`test_icons_stay_out_of_the_aligned_trail` looks for lines containing `·` **and** (`Phase` or `→`),
in `workflow-steps.md` under two directories.

```
ai/claude/dev-practices/workflow-steps.md exists
   lines the guard inspects: 0
   lines containing '·' at all: 0
ai/shared/workflow-steps.md MISSING
```

The file it guards contains no `·` at all. The breadcrumb half of the guard asserts nothing.

The breadcrumbs are elsewhere, and they already carry the thing the guard forbids:

```
$ grep -rn "·" ai/ --include=*.md | grep -c "✅"
75
$ grep -rn "·" ai/ --include=*.md | head -3
ai/claude/pm/design-feature/SKILL.md:60:| 1 | `▶ Discovery · ○ Journey · ○ Edge Cases · ○ Design · ...` |
ai/claude/pm/design-feature/SKILL.md:61:| 2 | `✅ Discovery · ▶ Journey · ○ Edge Cases · ○ Design · ...` |
ai/claude/pm/design-feature/SKILL.md:62:| 3 | `✅ Discovery · ✅ Journey · ▶ Edge Cases · ○ Design · ...` |
```

75 trail lines across `pm/design-feature`, `pm/add-feature`, `qa/verify-quality`,
`architect/review-code`, `architect/design-feature/progress-banners.md`, `ops/*` and
`hooks/_steps.sh` / `welcome.sh` / `statusline-hitl.sh`.

And `✅` is exactly the failure mode the docstring describes:

```
'✅' U+2705 east_asian_width=W  in guard range= False
'❌' U+274C east_asian_width=W  in guard range= False
'⚠'  U+26A0 east_asian_width=N  in guard range= False
'▶'  U+25B6 east_asian_width=A  in guard range= False
```

The class is `[\U0001F300-\U0001FAFF]`. Every glyph HITL actually uses in an aligned trail sits below
it. `✅` and `❌` are `east_asian_width=W` — **double-width, which is the stated reason for the rule** —
and both are invisible to the check.

The statusline half is live but equally porous:

```
$ printf 'echo "✅ ❌ ⚠️ ▶️"\n' >> ai/claude/hooks/statusline-hitl.sh
$ python3 -m pytest ci/wiring/test_wiring.py -q -k icons
2 passed, 43 deselected in 0.05s
```

`statusline-hitl.sh:65` already ships a `⚠`.

This guard is worse than absent. It is green, it names a real risk, and it certifies 75 existing
violations.

**Smallest fix:** find trail lines by the `·` separator alone across all of `ai/`, and widen the
class to `[←-⯿\U0001F000-\U0001FAFF️]` minus an explicit allowlist of the
single-width glyphs the design intends (`○ ▶ ⊘ ◐ →`). Expect it to go red on first run; that is the
finding.

---

## B-8 — MEDIUM — the next-step guard checks only messages that use one of four words, and a comment merges two of them

`test_a_hook_that_blocks_says_what_to_do_next` skips any block not matching
`(?i)paused|blocked|stopped|on hold`. A dead-end message that avoids those four words is never
examined:

```
176:    echo "Refused. This edit is not permitted in the current state." >&2
$ python3 -m pytest ci/wiring/test_wiring.py -q -k "says_what_to_do or shout"
2 passed, 43 deselected in 0.06s
```

One message, no remedy, both guards green.

Second, the message-boundary rule. `_message_blocks` treats blanks, comments and `while IFS=` as
non-breaking, so a single comment line welds two unrelated messages into one block and the second
one's remedy satisfies the first:

```
    echo "Everything is blocked here." >&2
    # nothing to see
    echo "Unrelated note: /hitl:ta-approve exists." >&2

MERGED BLOCK -> echo "Everything is blocked here." >&2 echo "Unrelated note: /hitl:ta-approve exists." >&2
$ python3 -m pytest ci/wiring/test_wiring.py -q -k says_what_to_do
1 passed, 43 deselected in 0.03s
```

The docstring says *"Per MESSAGE, not per file. Checking the whole file passes as soon as any one
message names a remedy."* The guard moved that failure from file scope to comment-block scope; it did
not remove it.

Also worth noting: `HITL_PY` is in the remedy pattern, so a message that merely mentions the
environment variable counts as naming a next step.

---

## B-9 — MEDIUM — an unparseable record is downgraded on a filename convention, with a false warning

`MALFORMED` escalates only when `os.path.basename(path).startswith(change_id + "-")`. A record for
this change whose filename does not lead with the change id is demoted to a warning — and the
warning asserts something the gate cannot know:

```
=== O: the consequence reviewer's record has a YAML typo, filename is lens-first ===
[warn] UNREADABLE_RECORD: .hitl/reviews/consequence-round1.yaml could not be parsed (not this change — ignored)
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

The file's `change_id` **is** `GH-99`. The gate could not parse it, so it guessed from the filename
and told the operator a fact that is false. Correct wording would be *"could not be parsed; its
filename does not identify a change, so it was ignored"* — which reads as something to look at
rather than something to move past.

---

## B-10 — MEDIUM — the catalog/gate agreement test is blind to hyphenated lens ids

`test_the_lens_catalog_and_the_gate_agree` parses the catalog table with `` ^\| `([a-z]+)` \| ``.

```
$ # add `| `blast-radius` | Who else is on fire when this fails? | any tier 3 change |` to the catalog
$ python3 -m pytest ci/wiring/test_wiring.py -q -k lens_catalog
1 passed, 44 deselected in 0.07s
```

A lens can be documented, offered to users, and unknown to the gate — which is the precise drift
this test exists to catch.

The same function's *alias* regex was widened for exactly this reason, with a comment saying so:

```python
# `[a-z-]+`, not `[a-z]+`: a hyphenated older name (`blast-radius`) is exactly the kind of
# alias someone adds, and the narrower class skipped it silently.
aliases = set(re.findall(r"`([a-z][a-z-]*)` →", doc[start:]))
```

The fix was applied to one of the two regexes in the function and not the other. Checking a file
against itself finds this in about thirty seconds.

**Smallest fix:** `[a-z][a-z-]*` in both table patterns.

---

## B-11 — MEDIUM — the documented record filename gives one file per round; the new floor needs two

Four shipped locations name the record file, all singular per round:

```
ai/claude/adversarial-review/SKILL.md:219  `.hitl/reviews/<change-id>-round<N>.yaml` and fill it in.
ai/claude/adversarial-review/SKILL.md:225  echo ".hitl/reviews/${CHANGE}-round1.yaml   reviewed_sha: ${SHA}"
ai/shared/adversarial-review.md:216        Write `.hitl/reviews/<change-id>-round<N>.yaml` from the template at
ai/shared/templates/adversarial-review-record.yaml:1  # ... .hitl/reviews/<change-id>-round<N>.yaml
```

A record carries exactly one `lens:`. `DUPLICATE_ROUND` requires the two round reviewers to be in
separate records. `LENS_FLOOR` requires two of them at release. **Follow Step 6 literally and you
produce one record per round, which cannot clear the floor added in the same commit.**

Whatever second filename someone improvises is unspecified, and B-9 makes the improvisation matter:
`GH-99-round1-user.yaml` is escalated on malformation, `consequence-round1.yaml` is not.

This is the mechanism by which B-2 stops being a theoretical attack. An author who cannot make the
documented path work, and who sees `UNKNOWN_LENS` say *"It still counts"*, has been shown the way
around.

**Smallest fix:** `<change-id>-round<N>-<lens>.yaml`, in all four places, with one line saying one
record per reviewer.

---

## B-12 — LOW — the icon/substance guard is a sentence-presence check on a file no hook reads

`test_turning_icons_off_cannot_remove_a_warning` greps `ai/claude/preferences/SKILL.md` for the
phrase *"icon is never the only thing"*. It asserts nothing about the hooks, which are where the
glyphs actually appear.

```
$ # hook message changed so the glyph carries the risk and the sentence does not
114:  echo "⚠️  Continuing here rewrites .hitl/ and drops your uncommitted work." >&2
115:  echo "Nothing is tracked for this branch yet, so edits are paused." >&2
$ grep -c "icon is never the only thing" ai/claude/preferences/SKILL.md
1
$ python3 -m pytest ci/wiring/test_wiring.py -q
45 passed in 0.41s
```

Turn icons off in that project and the destructive consequence is the thing that disappears.

To be fair to the release: the hooks as shipped **do** comply — strip `🔒 🧭 ✅ ⚠️` from every message
in `check-hitl-context.sh`, `check-domain-boundary.sh` and `check-platform-ready.sh` and the
sentences still carry their full meaning. The rule is honoured today. It is the guard that has no
grip on it tomorrow.

---

## B-13 — LOW — `--sha` exits 0 on a stale target

```
$ python3 check_review.py --root .                 # HEAD moved past the reviewed commit
[BLOCK] REVIEW_STALE: ... reviewed 8263d3514d34 but 3b6c2fcb95a0 is about to ship — file.txt changed since.
exit=2
$ python3 check_review.py --root . --sha 8263d351...
[warn] TARGET_NOT_HEAD: checked 8263d3514d34, but HEAD is 3b6c2fcb95a0. This is NOT a verdict on what would ship.
Release gate: adversarial review present, fresh, and cleared.
exit=0
```

The warning is honest and prominent, and the documented call site (`python3 ci/adversarial/check_review.py || exit 2`)
passes no `--sha`. Noted for completeness; the exit code should probably be 2 when the target is not
HEAD, since a warning cannot stop a `||`.

---

## Areas I attacked and found sound

- **Freshness.** The load-bearing rule holds. Branch and tag names in `reviewed_sha` are rejected by
  `re.fullmatch(r"[0-9a-fA-F]{7,40}")`; a leading `-` is rejected; a moved tree blocks with
  `REVIEW_STALE`; the `reviewed_tree` fallback requires an exact tree match. I could not get a stale
  record past it without `--sha` (B-13).
- **Whitespace and case on scalar fields.** `stance`, `verdict`, `reviewer.context`, `severity`,
  `status` are all `.strip().lower()`/`.upper()` compared. `change_id` is the sole exception (B-3).
- **`UNSIGNED_ACCEPTANCE`.** Fires correctly on every `accepted` finding regardless of severity or
  release status.
- **Fail-closed on malformed input.** An empty file, a non-mapping document, a non-list `findings`,
  a non-mapping `reviewer`, and an unexpected exception in `main()` all produce exit 2. A record for
  this change is never treated as absent when it is unreadable *and* correctly named.
- **`UNCOMMITTED_CHANGES`, including on the waiver path.** The waiver explicitly does not cover a
  dirty tree, which is the right call and is implemented.
- **`_exempt`.** Correctly covers both `.hitl` (the untracked-directory form `git status` emits) and
  `.hitl/`, so writing the record does not make the record stale. Verified against a real repo where
  `git status --porcelain` reports `?? .hitl/reviews/`.
- **Reviewer independence and stance.** Attestations, and the docstring says so plainly rather than
  claiming more. No complaint.
- **The rest of the wiring suite.** Reachability, wrapper-marker consistency, hook completeness, and
  onboarding-path agreement all hold; I could not find a mutation that broke the underlying property
  while keeping those guards green. `python3 -m pytest ci/ -q` → **723 passed, 5 skipped** on a clean
  copy of the tree.

---

## VERDICT: DO NOT SHIP

Not because a determined attacker can beat these checks — the file says so honestly up front, and
that is fine. Because **the two checks this release is named for did not run on this release**, and
because the one that would have run counts strings it has already told you are not lenses.

### The smallest change that would fix it

Three edits. Nothing structural.

1. **B-1** — `ai/claude/validate/SKILL.md:90`: delete the `if [[ "$WF" == "release" ]]` wrapper so
   the gate always runs, and `ci/adversarial/check_review.py:~330`:
   `is_release = wf_id.startswith("release")`. Then re-cut 2.8.0 with a `release`-workflow change
   file, as 2.7.1 was, and let the gate you are shipping pass its own release.

2. **B-2** — one line, `ci/adversarial/check_review.py`:
   ```python
   distinct = sorted({canonical_lens(doc.get("lens")) for _, doc in latest
                      if str(doc.get("lens", "")).strip()} & set(LENSES))
   ```
   and make `UNKNOWN_LENS` a block when `is_release`, so a lens that no longer counts says so.

3. **B-3** — compare `change_id` case-insensitively, and emit `[warn] FOREIGN_RECORD` for every
   `.yaml` in the reviews directory whose `change_id` does not match the change under review.

B-7 should be in the same pass — it is currently certifying 75 live violations, which makes it the
most misleading green in the suite — but it is the only one of the thirteen that will go red on
first run, so it is a fix with a tail. B-4, B-5, B-9, B-10 and B-11 are each a few lines and can
follow.

**One thing to keep.** The docstring at the top of `check_review.py` — *"It cannot verify that a
review was genuinely adversarial... Anyone determined to fake this can"* — is the most valuable
paragraph in the diff. Every finding above is a case of some *other* part of the release quietly
promising more than that paragraph does. Fix the code to match the docstring, not the other way
round.
