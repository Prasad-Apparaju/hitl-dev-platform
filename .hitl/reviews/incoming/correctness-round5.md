# Round 5 — correctness lens

State reviewed: `0b6c5f7507c75594328e2bae13a39c94a5a86f84` on `main`.
Baselines: `v2.7.1..HEAD` (everything that ships), `1d4b2fd..HEAD` (the removals + doc fixes).
Full suite at HEAD: `python3 -m pytest ci/ -q` → **722 passed in 69.10s**.

Every finding below was reproduced. Command and observed output are given inline.

---

## A. Is the removal clean?

**No. Four dead or contradicting references survived the revert, two of them in files that ship into
every product repo.**

First, a correction to the brief's premise. It asks me to verify that
`git diff v2.7.1..HEAD -- ci/adversarial/check_review.py` "contains no behavioural change to how
findings, verdicts or staleness are judged."

- **Staleness: confirmed unchanged.** `_is_fresh`, `_dirty`, `_exempt`, `EXEMPT_PREFIXES`,
  `EXEMPT_PATHS`, `MIN_SHA`, `_tree`, `_looks_like_build_output` are byte-identical to v2.7.1. The
  diff touches nothing between lines 71 and 249.
- **Verdict selection: confirmed unchanged.** `adverse_in_round[0] if adverse_in_round else latest[-1]`
  is v2.7.1's rule verbatim.
- **Findings: there IS a behavioural change, and it is intended.** Findings were read from the single
  selected record; they are now read from every record whose round equals `top` (lines 448-455). This
  is feature-by-design (CHANGELOG "The gate read one reviewer's findings per round"), the
  implementation is correct, and it is strictly stricter — an extra record can only add blocks. I
  flag it because the brief asserts otherwise, not as a defect.

One asymmetry worth recording, not a finding: `reviewed_sha`, `reviewer.context`, `stance` and
`verdict` are still validated on `rec` alone, while findings now come from all of `latest`. A second
record in the governing round can therefore block the release without ever being checked for
freshness, independence or stance. The direction is safe (it can only add blocks, never clear one),
so this is a note for #92, not a round-5 finding.

---

### A1 — HIGH — `ci/adversarial/check_review.py:438-443` states the removed carry-forward rule as current behaviour, three lines above the paragraph that says it was cut

The revert (`5c741fd`) deleted the code and appended a new paragraph, but left the paragraph that
justified the deleted code. The comment block at 434-447 now says three different things, two of
which are mutually exclusive:

```
438    # An open CRITICAL or HIGH from ANY round is still open. ...
443    # by a later round declining to mention it.
444    # Findings are read from the governing round. Carrying earlier rounds forward was tried in
445    # 2.8.0 and cut ...
```

Line 438-443 is false at HEAD. Reproduced:

```
$ git diff 1d4b2fd..HEAD -- ci/adversarial/check_review.py
-    _resolved = set()
-    for _p, _doc in records:
...
-    for _p, _doc in records:
-        if _round((_p, _doc)) == top:
-            continue
+    # Findings are read from the governing round. Carrying earlier rounds forward was tried in
```

The loop that read non-top rounds is gone; `findings` is built only from `latest`. This is the
highest-leverage defect in the release because `check_review.py` is copied verbatim into every
onboarded repo (`ai/claude/update/SKILL.md:273`:
`cp "$ROOT/shared/ci/adversarial/"*.py ci/adversarial/`), and the next person to change this file
reads 438-443 as the contract.

**Fix:** delete lines 438-443.

---

### A2 — HIGH — `CHANGELOG.md:113` "Nothing that validated before this release fails now" is false; two record sets that pass on v2.7.1 block at HEAD

```
$ T=$(mktemp -d); git show v2.7.1:ci/adversarial/check_review.py > "$T/old_check.py"
  # (fixture: one commit, GH-80 release change, two round-1 records, both verdict: ship)

########## CASE A: lens "consequence" + lens "consequence-2"
  old exit=0
  new exit=2
[BLOCK] DUPLICATE_ROUND: round 1 has more than one record for lens 'consequence' ...

########## CASE B: open CRITICAL on the record the old gate did not select
  old exit=0
  new exit=2
[BLOCK] FINDING_OPEN: CRITICAL: deletes the user database — fix it, or accept it explicitly with accepted_by
```

Both new blocks are *correct* — they are precisely the two holes the release says it closed. The
defect is the compatibility promise, which is unqualified and bolded.

This is a regression of an already-fixed finding. Round 1 filed exactly this claim shape as
`C2-H1` ("The CHANGELOG told existing projects the upgrade is validation-neutral. Records that
passed on 2.7.1 now block at release"), status `fixed`, with `verified_by: CHANGELOG 'Note for
existing projects' now states exactly which two rules are new`. The revert removed the two rules
*and* the qualification, restoring the absolute sentence — while two other newly-blocking rules
(DUPLICATE_ROUND resolution, all-records-in-round) remain in the release.

**Fix:** replace the sentence with the two cases that newly block — a second reviewer numbered
rather than re-lensed, and an open CRITICAL/HIGH on a record that is not the round's selected one.

---

### A3 — MEDIUM — `ci/adversarial/test_check_review.py:48-49` promises the removed `UNVERIFIED_FIX` rule

```python
48        # A valid record closes a blocking finding with evidence, not just a status. `verified_by`
49        # is the reproduction re-run and its output; without it the gate blocks at release.
```

Reproduced — it does not block, and does not even warn:

```
$ # fixture: release workflow, one clean round-1 record, one finding:
$ #   {severity: CRITICAL, status: fixed}  — no verified_by, no resolved_by
BLOCKS: []
WARNS: []
```

This file ships to product repos through the same `*.py` copy as A1.

**Fix:** change 48-49 to say the field is recorded, not required.

---

### A4 — MEDIUM — `CHANGELOG.md:135` says all three cut rules "survive as written practice"; `verified_by` is written nowhere the workflow reads

```
$ grep -rn 'verified_by' ai/claude/adversarial-review/SKILL.md ai/shared/adversarial-review.md
  ABSENT
$ grep -rn 'verified_by' --include='*.md' --include='*.yaml' ai/ docs/ CHANGELOG.md
ai/shared/templates/adversarial-review-record.yaml:47
CHANGELOG.md:34
CHANGELOG.md:135
```

Checked the other two of the three, for symmetry:
- "pick a second lens from the catalog" — written, `ai/shared/adversarial-review.md:107`. Sound.
- "read the earlier rounds" — the nearest sentence is `SKILL.md:241` ("Earlier rounds stay"), which
  is about *keeping* them, not reading them. Weak but arguable.
- "record `verified_by` when you close a finding" — not written anywhere.

Worse, the single place it is documented is inside the block the template tells the user to remove:

```
38  # DELETE this example block before use. ...
47  #   verified_by: ""          # HOW YOU KNOW it is fixed ...
```

`SKILL.md` Step 6's "Rules that matter" list (reviewed_sha / reviewer.context / stance /
reproduction / verdict) omits it, and Step 7 says a finding "ends as `fixed` or as `accepted` with a
name against it" — no evidence requirement. So the practice the CHANGELOG says survives is
unreachable from the workflow that writes the record.

**Fix:** add one bullet to `SKILL.md` Step 6's rules list.

---

### A5 — MEDIUM — `ai/shared/adversarial-review.md:109-110` carries the exact numbers `CHANGELOG.md:123-127` says were a mistake

```
$ grep -rn -i 'ten CRITICAL|fourteen|three review rounds' ...
CHANGELOG.md:123:  Four rounds ... found **fourteen CRITICAL findings, every one of them inside those three rules**
CHANGELOG.md:127:  That mistake was published in an earlier draft of this note, which is corrected here.
ai/shared/adversarial-review.md:109: ... enforcing it was cut from 2.8.0 after three review rounds found
ai/shared/adversarial-review.md:110: ten CRITICALs in the enforcement itself; the redesign is issue #92.
```

The correction landed in one of the two shipped files that state it. `ai/shared/` is copied into
every product repo; the CHANGELOG is not.

**Fix:** `three review rounds` → `four`, `ten CRITICALs` → `fourteen`.

---

### A6 — LOW — removal debris in `ci/adversarial/test_check_review.py`

Two runs of six blank lines where tests were deleted (ending at lines 546 and 562), and
`_rel(tmp_path, findings, round_=1, extra_change=None)` now has a dead `extra_change` parameter —
both surviving call sites (564, 571) omit it, and both pass `findings=[]`.

**No test passes vacuously as a result of the removal.** I checked the two that survive from the cut
group (`test_round_three_says_it_should_have_been_a_decision`,
`test_two_rounds_do_not_warn`); both assert on `ROUND_DEPTH`, which is a live rule.

---

## B. Are the four features sound?

### B1 — Reviewer reports arrive by file — **sound, with one HIGH doc contradiction and one LOW**

Path coherence verified:
- The gate lists `reviews_dir` and skips anything not ending `.yaml`/`.yml`, so the `incoming/`
  subdirectory is never read as a record.
- `.gitignore` ignores `.hitl/reviews/incoming/`, and `_dirty()` exempts `.hitl/` outright
  (`EXEMPT_PREFIXES = (".hitl/",)`), so an in-flight report can neither dirty the tree nor block the
  gate — belt and braces. Correct.
- Missing report → unknown: stated at `SKILL.md:150-154` and guarded by
  `ci/wiring/test_wiring.py:376`, which is a shape match, not a byte match.
- The transcript race is warned against (`SKILL.md:148-150`) and guarded.

**B1a — HIGH — `CHANGELOG.md:65` tells the user to do the thing the two skill docs now say is
rejected.**

`1d4b2fd..HEAD` corrected the dropped-lens rule in both skill docs:

```
ai/claude/adversarial-review/SKILL.md:73  **Write a dropped lens into the record you do write.** ...
                                          It is not a workflow skip ... Filing it there produces a
                                          change file the First Pass check rejects.
ai/shared/adversarial-review.md:119       **A lens they drop goes in the record's `scope`** ... Not in
                                          `skips[]` ...
```

`CHANGELOG.md:65` was not corrected and still reads: *"a lens you drop is recorded like any other
skip."* The skill docs' claim is true — reproduced:

```
$ cat > "$T/.hitl/current-change.yaml"   # skips: [{step: security, disposition: decline, actor: pappar, reason: ...}]
$ python3 ci/first-pass/check_skips.py "$T/.hitl/current-change.yaml"
[warn] LEDGER_STEPS: skip record references unknown step 'security'
[BLOCK] UNKNOWN_STEP: skip references step 'security' not in the workflow catalog (criticality unresolvable)
EXIT=2
```

So the release notes for the lens catalog instruct a change-file shape the shipped First Pass gate
fails closed on. (Note `CHANGELOG.md:260` and `docs/announcements/…:59` use the same phrasing
correctly — they are about declining a *workflow step*, which is a step. Only line 65 is wrong.)

**Fix:** align `CHANGELOG.md:65` with `ai/shared/adversarial-review.md:119`.

**B1b — LOW — the report path is not change-id scoped while the record path is.**
`.hitl/reviews/<change-id>-round<N>.yaml` vs `.hitl/reviews/incoming/<lens>-round<N>.md`. Two changes
in one repo running the same lens at the same round overwrite each other's report. Impact is bounded
(the file is working material and the record carries the findings), but the asymmetry is unexplained
in either doc.

---

### B2 — The triage step — **sound**

`SKILL.md` Step 5 is internally consistent and consistent with `ai/shared/adversarial-review.md`
"Presenting what came back": CRITICAL/HIGH individually, MEDIUM/LOW summarised, three answers, both
`accept` and `defer` write `accepted_by`, unanswered stays `open`, non-blocking. The gate backs it —
`UNSIGNED_ACCEPTANCE` fires on `accepted` with an empty `accepted_by`, and now does so across every
record in the governing round rather than one. No contradiction found within either file or between
them.

---

### B3 — The 13-lens catalog — **sound**

`canonical_lens` mangles nothing it should not. Reproduced across the full vocabulary:

```
$ python3 -c "... for l in LENSES: print(l, '->', canonical_lens(l))"
OK fitness, correctness, consequence, upgrade, security, data, scalability,
   operability, compatibility, bypass, interfaces, user, cost      (13/13 identity)
destructiveness -> consequence   migration -> data   install -> upgrade
perf -> scalability              functionality -> fitness           (5/5 correct)
'CONSEQUENCE-2' -> 'consequence'  'correctness_2' -> 'correctness'  'data two' -> 'data'
'install-2' -> 'upgrade'          'perf2' -> 'scalability'          '' -> ''
```

The `[\s_-]*(bis|b|two|second)$` stripper is the only sharp edge — I checked all 13 ids and all 5
aliases against it and none ends in a stripped token. Duplicate detection resolves before grouping
(`check_review.py:335`), and `UNKNOWN_LENS` warns rather than blocks, so pre-catalog records keep
validating. `ci/wiring/test_wiring.py:320-340` asserts the catalog, `LENSES` and `LENS_ALIASES`
agree in both directions and uses `[a-z-]+` for alias names, so a hyphenated alias is not skipped.

---

### B4 — 46 rewritten hook messages — **behaviourally sound; two MEDIUMs in the vocabulary and its guard**

**Exit codes and control flow: verified identical to v2.7.1 on every reachable path.**

```
$ for h in check-domain-boundary check-hitl-context check-platform-ready rebuild-graph write-session-summary; do
    diff <(git show v2.7.1:ai/claude/hooks/$h.sh | grep -o 'exit [0-9]\|sys.exit\|return [0-9]') \
         <(grep -o 'exit [0-9]\|sys.exit\|return [0-9]' ai/claude/hooks/$h.sh) && echo "$h IDENTICAL"; done
check-domain-boundary   IDENTICAL exit set
check-hitl-context      IDENTICAL exit set
check-platform-ready    IDENTICAL exit set
rebuild-graph           IDENTICAL exit set
write-session-summary   IDENTICAL exit set
```

The only new control flow is the two `if [[ -n "$EXPECTED" ]]` guards in `check-hitl-context.sh`
(153, 161). Both sit inside the layer-2 branch, which `exit 2`s unconditionally at line 167, so
neither guard can change the exit status. Under `set -euo pipefail` a false `if` is not an error.

**Empty-variable interpolation: no regression, and one genuine improvement.**
`EXPECTED` was the real hole and is now guarded — the fix is correct and the fallback branch at
156-157 says plainly that no branch is recorded. `CHANGE_ID` (145, 154, 156) and `STATUS` (188) can
still be empty when the field is present with no value (`grep "^status:"` matches, `awk '{print $2}'`
prints nothing), but v2.7.1 interpolated the same two variables in the same conditions, so the
exposure is unchanged. In `check-domain-boundary.sh`, `ALLOWED_PATHS` is guaranteed non-empty by the
guard at line 94 before the loop at 127 prints it. No message in the five scripts interpolates a
variable that this release newly made emptiable.

**B4a — MEDIUM — a sixth hook still speaks in the old voice, for the same condition, and the guard
cannot see it.**

`ai/claude/hooks/hitl-gate.sh:34-49` prints, for a branch↔change mismatch:

```
  ⚠️  HITL — BRANCH ↔ CHANGE MISMATCH
  ...
  This branch is operating under a change that doesn't match it ...
  Source edits are blocked until this is realigned. Do NOT trust prior analysis in context.
```

`check-hitl-context.sh:154` now phrases the *same* condition as *"🧭 You are on 'x', but the tracked
change GH-n lives on 'y'."* A user hitting a mismatch sees both, in two voices.

The no-shouting guard cannot catch it. `_hook_messages()` (`test_wiring.py:406-419`) collects only
`echo "…" >&2` and `(print|block)(f?"` lines; this message is a `cat <<DIRECTIVE` heredoc:

```
$ grep -rn 'cat <<' ai/claude/hooks/*.sh
ai/claude/hooks/_steps.sh:250:  cat <<'DIRECTIVE'
ai/claude/hooks/hitl-gate.sh:34:  cat <<DIRECTIVE
```

This is the same class as round-1 `C2-H2` — where the echo-only scan certified `check-platform-ready.sh`
clean while its four user-facing Python messages still shouted. That fix widened the scan to
`print(`/`block(` and stopped short of heredocs. Two of three output mechanisms are now covered.

The message is also factually wrong in a way the new one is not: it says *"Source edits are
blocked"*, but `check-hitl-context.sh` layer 2 blocks **all** guarded edits, not just source.

**Fix:** rewrite `hitl-gate.sh:34-49`, and add a heredoc arm to `_hook_messages()`.

**B4b — MEDIUM — the six-icon vocabulary defines ⚠️ as a meaning nothing uses.**

`ai/claude/preferences/SKILL.md:369` (and `CHANGELOG.md:97`) gloss the set as
*"🔒 paused, 🧭 where you are, ⚠️ irreversible, ✅ done, 🔄 working, 📝 saved."*

```
$ grep -rn '⚠️' ai/claude/hooks/*.sh
check-domain-boundary.sh:88:  echo "⚠️  I could not read .hitl/current-change.yaml, ..."
hitl-gate.sh:36:              ⚠️  HITL — BRANCH ↔ CHANGE MISMATCH
$ grep -rl '⚠️' ai/ | wc -l
33
```

Neither hook use is irreversible, and the other 33 shipped files use ⚠️ uniformly for
*unavailable / uncertain / diverged*. The five other glyphs match their gloss exactly. So one sixth
of a vocabulary the release introduces is documented with a meaning zero shipped messages honour.

**Fix:** change the gloss to "⚠️ something needs your attention", or find an irreversible message to
mark.

Also verified sound: `preferences/SKILL.md` no longer contradicts itself about what "plain text"
can turn off — `278` ("An icon is never the only thing carrying a warning") and `369-373` ("tells
**Claude** to drop them … does not change the hooks") now agree, and `test_turning_icons_off_cannot_remove_a_warning`
pins the first.

---

### B5 — The portal — **one MEDIUM cross-page disagreement, one MEDIUM against plugin.json, two LOWs**

The generated page is trustworthy. `python3 tools/scripts/generate-catalog-page.py` reproduces
`site/catalog.html` byte-identically (`git status --short` empty after), and `check_order_covers`
is a real build failure, not a comment. The new version test is not vacuous:

```
$ python3 -c "...d['version']='2.9.0'..."   # mutate plugin.json
$ python3 -m pytest ci/wiring/test_wiring.py::test_the_portal_agrees_with_itself_about_the_current_version -q
FAILED  ci/wiring/test_wiring.py:526: AssertionError
```

Version agreement holds across all nine pages: every 2.x reference is `v2.8.0`, matching
`plugin.json` (`version: 2.8.0`); the six `v1.1.1` hits are the legacy line.

**B5a — MEDIUM — `site/getting-started.html:241` disagrees with the generated catalog about the
development workflow, twice, in its own file.**

```
site/getting-started.html:241  "The development workflow is 32 steps across 7 phases"
site/getting-started.html:242  "A 32-step plan for a one-line bug fix ..."
site/catalog.html:127          "31 steps + 3 substeps · 7 phases"
site/going-ai-native.html:491  "31 steps"
```

`32` was correct when development was 31 steps + 1 substep. It is now 34 rows. The final commit
(`0b6c5f7`, "the four hand-maintained pages drifted from the generated one again") reconciled
`architecture`, `compare`, `going-ai-native` and `index` — `getting-started.html` is the fifth
hand-maintained page, is in the nav on every page including the generated one, and was not in the
set. The new wiring test only compares version strings, so it does not cover counts.

**B5b — MEDIUM — "52 skills" disagrees with `plugin.json`, which declares 53.**

```
$ python3 -c "import json;print(len(json.load(open('ai/claude/plugin/plugin.json'))['skills']))"
53
$ grep -rn '52 skills' site/
site/architecture.html:182
site/going-ai-native.html:228
```

The 53rd is `ai/claude/adversarial-review`, added by `16f68d5` (the release-workflow commit); the
"52" dates from `69bfd6b`. The portal refresh in this release updated the versions on both pages and
left the count. Cross-checked "6 reviewer agents" — 6 agent files plus a README, correct.

**B5c — LOW — `site/index.html` "What's new … newest first" tops out at 2.7 while its own footer
says "current release: v2.8.0".** None of this release's content — the review loop, the lens
catalog, the triage step — appears anywhere on the portal.

**B5d — LOW — `site/compare.html` footer cites "CHANGELOG 2.0.0–2.7.1" while the statcard on the
same page reads "2.x — v2.8.0 · CURRENT".** Escapes the new test because it has no `v` prefix.

---

## Known and already recorded — not re-litigated

Both reproduced; both already in the trail, so neither is a round-5 finding.

- `check-domain-boundary.sh:87-92` is unreachable. Under `set -euo pipefail` the failing command
  substitution at line 58 exits the script before `PYEXIT` is read — confirmed with a minimal
  script: `bash t.sh; echo "script exit=$?"` → `script exit=1`, the `REACHED PYEXIT` line never
  printed. Round 1, `C2-M`, `accepted_by: pappar`, deferred.
- `_message_blocks` over-merges. `check-hitl-context.sh` yields four blocks, one of them 1001 chars
  spanning the ✅ merged-branch message and both 🧭 mismatch variants, so
  `test_a_hook_that_blocks_says_what_to_do_next` cannot tell them apart. Round 2, bypass lens, still
  `open`. I confirmed the currently-shipped text is fine on every branch — this weakens the guard,
  not the product.

---

## Areas checked and found sound

- Staleness and verdict-selection logic in `check_review.py`: byte-identical to v2.7.1.
- The all-records-in-round findings change: correctly implemented, strictly stricter.
- `canonical_lens`: no catalog id or alias mangled; 13/13 and 5/5 correct.
- `.hitl/reviews/incoming/` gitignoring: coherent with both the gate's record scan and `_dirty()`.
- Missing report treated as unknown: stated and shape-guarded.
- The triage step: internally consistent and consistent with the shared doc and the gate.
- The record template: consistent with the post-removal gate on every line.
- Hook exit codes and control flow: identical to v2.7.1 across all five rewritten scripts.
- Empty-variable interpolation in the five rewritten scripts: no regression; `EXPECTED` improved.
- Catalog page generation and its `check_order_covers` build failure.
- Version agreement across all nine portal pages and `plugin.json`.
- 722/722 tests pass; the two new wiring tests I mutation-checked are not vacuous.

---

## Verdict

**DO NOT SHIP** — on documentation correctness, not behaviour. Nothing here breaks at runtime. But
this is a release whose entire subject is a governance workflow, and it ships: a validator carrying a
paragraph describing behaviour it does not have (A1), release notes instructing a change-file shape
the shipped First Pass gate fails closed on (B1a), and a bolded compatibility guarantee that two
demonstrated fixtures falsify (A2).

**Smallest change that would fix it — four edits, all text, no code:**

1. `ci/adversarial/check_review.py` — delete lines 438-443.
2. `CHANGELOG.md:113` — replace *"Nothing that validated before this release fails now"* with the two
   cases that newly block: a second reviewer numbered rather than re-lensed, and an open
   CRITICAL/HIGH on a record that is not the round's selected one.
3. `CHANGELOG.md:65` — replace *"a lens you drop is recorded like any other skip"* with the corrected
   rule already in `ai/shared/adversarial-review.md:119`.
4. `ai/shared/adversarial-review.md:109-110` — `three review rounds` → `four`, `ten CRITICALs` →
   `fourteen`.

A2 is the only one of the four that needs judgement rather than transcription. The rest are
transcription.

**Ship-blocking on their own: A1, A2, B1a.** A3, A4, A5, B4a, B4b, B5a, B5b are MEDIUM and would be
reasonable fast-follows. A6, B1b, B5c, B5d are LOW.

One structural observation for the scope conversation, offered rather than filed: five of the eleven
findings above (A1, A2, A3, A4, A5) are text left behind by the revert, and two more (B1a, B5a) are
one file corrected while its twin was not. This release's remaining defect population is
overwhelmingly *"the fix landed in n-1 of n places."* A grep-level pass over every sentence that
names `verified_by`, a lens skip, a round count, or a step count would close most of it in one
sitting, and is a cheaper next move than a round 6.
