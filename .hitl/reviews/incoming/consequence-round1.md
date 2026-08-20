# Adversarial review — lens: consequence — round 1

- **Target:** `7a123555727f92e8dc1ae3595249a552ec334dcb` (main), diffed against `v2.7.1`
- **Stance:** refute
- **Scope:** 25 files, ~1531 insertions
- **Verdict:** DO NOT SHIP

Every finding below was reproduced. Commands and observed output are inline. Test repos were
created with `mktemp -d`; no tracked file in the repository was modified.

Harness used for the validator findings (in the session scratchpad, not the repo):
`check_review_271.py` = `git show v2.7.1:ci/adversarial/check_review.py`,
`check_review_280.py` = the file at HEAD. Each scenario builds a fresh `git init` repo with a
`.hitl/current-change.yaml` and review records, then runs both versions against it.

---

## Summary of what I attacked

| Area | Result |
|---|---|
| 1. New blocks (`LENS_FLOOR`, `UNVERIFIED_FIX`) | **2 findings** — one blocks the normal review loop, and the escape it recommends is larger than the problem |
| 2. Fail-open in the rewritten findings loop | **Sound.** The new loop strictly widens what blocks; I found no input where 2.7.1 blocks and 2.8.0 does not |
| 3. Five rewritten hooks | **Gates intact.** Identical exit codes on every branch I could reach. But 2 findings on what the rewrite missed and what it wrote into dead code |
| 4. `.hitl/reviews/incoming/` | **2 findings** — the reports are not gitignored and are exempt from the gate's dirty check, and the brief tells reviewers that exemption exists |
| 5. Each file against itself | **3 findings** — including the exact contradiction this release exists to remove, in the file it edited, with a green test over it |

---

## CRITICAL-1 — the ordinary two-round review loop is now unshippable, and the way out is a full waiver

`LENS_FLOOR` counts distinct lenses in **the top round only** (`check_review.py:388`, `distinct`
is built from `latest`, not `records`). The skill's own Step 7 tells you that fixing a finding
makes the record stale and you must run another round against the new sha. A round-2 re-review
that confirms one fix is normally run by the lens that found it — one lens. That round is now the
governing round, and the release blocks.

The perverse consequence: a release that did **one** round with two lenses passes. A release that
did the same round and then **more** review blocks.

```
$ python3 s4.py
=== I1: r1 two lenses, r2 ONE lens re-review (the normal converge loop)
  2.7.1 exit=0 blocks=[] warns=[]
  2.8.0 exit=2 blocks=['LENS_FLOOR'] warns=['RECURRING_FINDING']
```

(fixture: round 1 = `correctness` + `consequence`, the `correctness` record carrying a CRITICAL
marked `fixed` with a real `verified_by`; round 2 = `correctness` alone, re-reviewing the fix.)

Now the escape hatch. The block's own message says: *"or record the decision to ship without one
as an acknowledged skip."* The only skip `_acknowledged_skip()` recognises is
`step: adversarial_review` — which returns from `check()` at line 268 **before every other check
runs**. Taking the advice the new block prints does not waive the second lens. It waives the whole
gate:

```
$ python3 s3.py
=== H1: release 1 lens + OPEN CRITICAL, verdict ship, no skip
  2.7.1 exit=2 blocks=['FINDING_OPEN'] warns=[]
  2.8.0 exit=2 blocks=['FINDING_OPEN', 'LENS_FLOOR'] warns=[]
=== H2: SAME + acknowledged skip {step:adversarial_review, ack_by}
  2.7.1 exit=0 blocks=[] warns=['REVIEW_WAIVED']
  2.8.0 exit=0 blocks=[] warns=['REVIEW_WAIVED']
---- H2 full 2.8.0 output ----
[warn] REVIEW_WAIVED: C is shipping WITHOUT an adversarial review.
        Acknowledged by me: only had one lens
        Recorded in the change file, and it stays there.
Release gate: PASSED ON A WAIVER — no adversarial review was honoured.
```

The fixture's open finding is `CRITICAL: "deletes the user database on upgrade"`. It is not
mentioned anywhere in the output. `FINDING_OPEN` vanished. The `NOTE: ... The waiver is overriding
it` line only fires when a record's **verdict** is not `ship`; a record that says `ship` while
carrying an unresolved CRITICAL produces no note at all.

So the new block's recommended remedy, applied by someone at 2am who is short one lens:
- silently drops every open CRITICAL and HIGH in the round,
- drops the staleness check,
- and writes a permanent governance record asserting the release shipped *"WITHOUT an adversarial
  review"* — which is false. A review was done. The record is now worse than the truth.

The cheaper alternative a real person will find first is to open the round-2 record and change
`lens: correctness` to `lens: upgrade`. `.hitl/` is exempt from both the dirty check and the
staleness diff, so that edit costs nothing and turns the gate green with no re-review. Before this
release there was no reason to misname a lens. Now there is one.

**Smallest fix:** build `distinct` from `records` (all rounds of this change) rather than
`latest`. One expression. It preserves the intent — the release must have been looked at through
two distinct lenses — and removes the stuck case entirely. Separately, the `LENS_FLOOR` message
should not point at `_acknowledged_skip`, because that skip is not the thing it describes.

---

## HIGH-1 — the release notes tell existing projects the upgrade is validation-neutral. It is not.

`CHANGELOG.md:113`, *Note for existing projects*: **"Records written before this release keep
validating."**

Three reproduced counter-examples, all on records that passed the gate at 2.7.1:

```
$ python3 s1.py
=== A: release, lenses correctness + correctness-2, clean
  2.7.1 exit=0 blocks=[] warns=['SHALLOW_REVIEW']
  2.8.0 exit=2 blocks=['DUPLICATE_ROUND', 'LENS_FLOOR']
=== B: release, single lens consequence, clean
  2.7.1 exit=0 blocks=[]
  2.8.0 exit=2 blocks=['LENS_FLOOR']
=== C: release, 2 lenses, CRITICAL fixed w/o verified_by
  2.7.1 exit=0 blocks=[]
  2.8.0 exit=2 blocks=['UNVERIFIED_FIX']
```

The same CHANGELOG says, 70 lines earlier, that `consequence-2` used to slip past and now resolves
(line 44) and that two distinct lenses are now required (line 76). The document contradicts itself
about the one thing an upgrading reader needs. This is the *"two contradictory claims twenty lines
apart"* class, in the release note.

The consequence is specific and reachable: someone mid-release runs `/hitl:dev-update` because the
note says records keep validating, does not re-run the gate, and discovers at `publish` that the
gate now blocks — at the point in the release workflow where the pressure to reach for the waiver
is highest. That is the path into CRITICAL-1.

**Smallest fix:** replace that sentence with what is actually true — *"a record with one lens, a
numbered duplicate lens, or a CRITICAL closed without `verified_by` will now block at release;
re-run the gate before you publish."*

Escape reachability for `UNVERIFIED_FIX` itself is fine and cheap: adding any non-empty
`verified_by` clears it (`H4`), and `.hitl/` edits do not restale the record. Note that one
character clears it (`I2`: `verified_by: "."` passes), and that flipping the finding to
`accepted` + `accepted_by` also clears it (`H5`) — the block is satisfied by a weaker claim than
the one it asks for. That is a design choice, not a defect, but it means `UNVERIFIED_FIX` buys
less than the CHANGELOG implies.

---

## HIGH-2 — the release rewrote the messages of the production-deploy gate everywhere except where a user hits it, and the test that certifies "all 42" cannot see the difference

CHANGELOG: *"All 42 of them, across five hooks, now say the same thing the way a colleague would."*

`check-platform-ready.sh` is the tier-2+ production deploy block. Only its rare
no-PyYAML-interpreter branch was rewritten. The four messages a user actually hits are inside the
hook's Python block and still shout:

```
$ bash hooks_new/check-platform-ready.sh production
HITL DEPLOY BLOCKED: platform readiness register has no items (Tier 2 production deploy).
  Run /hitl:ops-plan-platform derive to populate it.
exit=2

$ bash hooks_old/check-platform-ready.sh production      # v2.7.1
HITL DEPLOY BLOCKED: platform readiness register has no items (Tier 2 production deploy).
  Run /hitl:ops-plan-platform derive to populate it.
exit=2
```

Byte-identical. Remaining occurrences: `check-platform-ready.sh:153, 260, 285, 295`.

The guard added in this release, `test_hooks_do_not_shout_their_internal_state`
(`ci/wiring/test_wiring.py:401`), collects only lines matching `echo "..." >&2`. Applied to
`check-platform-ready.sh` it sees 8 lines — all of them the ones that were rewritten — and reports
zero offenders:

```
$ python3 -c '<the test'"'"'s own _hook_messages regex, applied to check-platform-ready.sh>'
--- offenders per the test's regex: []
```

The file contradicts itself: one message in a colleague's voice, four in capitals, in the same
hook. A test exists that asserts otherwise and is scoped to bash echoes.

**Smallest fix:** either rewrite the four Python-side messages, or narrow the CHANGELOG claim to
the hooks it is true of. The test should scan `print(`/`block(` too, or it will keep certifying
this.

---

## MEDIUM-1 — the exact contradiction this release exists to remove is still in the file, and the new test written to prevent it passes

`ai/claude/adversarial-review/SKILL.md`:

```
 94: **Do not give the reviewers names.** A named agent becomes an addressable peer rather than a task
140: Give each reviewer a distinct name so the reports are attributable.
```

46 lines apart, in the file this commit rewrote, on the defect the CHANGELOG opens with (*"The
reviewers' reports were not reaching anyone. The skill told you to give each reviewer a name"*).
Line 140 was left standing.

`test_reviewers_hand_their_report_over_through_a_file` (`ci/wiring/test_wiring.py:344`) asserts the
*warning* is present. It never asserts the contradicting instruction is gone:

```
$ python3 -m pytest ci/ -q
728 passed in 45.49s
```

An LLM reading this skill top to bottom reaches Step 3, is told not to name reviewers, reads six
more paragraphs, and is told to name them. The one nearest the action wins about half the time.
The reproduced failure mode from the CHANGELOG — ten reviewers, 13k-25k characters each, nothing
delivered — is one coin-flip away from recurring, and this diff is the fix for it.

This is also the finding the brief asked for by name: check each file against itself. The
instruction to do that was added in this same commit, at SKILL.md line 114.

**Smallest fix:** delete line 140. One line.

---

## MEDIUM-2 — the validator now punishes the only bookkeeping that makes it safe

Two rules in `check_review.py`, ~120 lines apart, pull opposite ways:

- Findings are inspected for the **top round only** (`latest`, line 458). A round-1 CRITICAL that
  round 2 does not restate is forgotten.
- `RECURRING_FINDING` (line 396) warns when the same claim appears in **consecutive** rounds.

So carrying a finding forward — the only thing that stops it being dropped — triggers the warning
that says a human should re-scope the change. And not carrying it forward is silently rewarded:

```
$ python3 s5.py
=== J1: r1 OPEN CRITICAL, r2 two clean lenses that omit it
  2.7.1 exit=0 blocks=[] warns=[]
  2.8.0 exit=0 blocks=[] warns=[]
Release gate: adversarial review present, fresh, and cleared.
```

The fixture's round-1 finding is an **open** `CRITICAL: "data loss on upgrade"`. Round 2 does not
mention it. The gate prints *"adversarial review present, fresh, and cleared."*

This behaviour is pre-existing (2.7.1 does the same), so it is not a regression. It is in scope
because this release fixed the sibling of exactly this bug — *"the gate read one reviewer's
findings per round... a second reviewer's unresolved CRITICAL shipped unseen"* — one dimension
over, across reviewers, and left it standing across rounds. In the diff's own words: right about
the defect, wrong about its class.

`RECURRING_FINDING` also fires on a finding correctly carried forward as `fixed`:

```
=== I3: same claim in r1 and r2 (round-1 CRITICAL carried forward as fixed)
  2.8.0 exit=0 blocks=[] warns=['RECURRING_FINDING']
```

It compares claims regardless of status, so it will fire on most multi-round reviews. It shares an
output stream with `REVIEW_WAIVED`, the one warning nobody should learn to skim past.

**Smallest fix:** carry unresolved CRITICAL/HIGH forward from earlier rounds when the later round
does not restate them, and exclude findings whose status is `fixed`/`accepted` from
`RECURRING_FINDING`.

---

## MEDIUM-3 — reviewer reports land in a directory that is not ignored and that the gate is blind to, and the brief tells the reviewer so

The skill now sends every reviewer's raw report to `.hitl/reviews/incoming/<lens>-round<N>.md`.

```
$ git check-ignore -v .hitl/reviews/incoming/foo.md ; echo exit=$?
exit=1                      # not ignored
```

`.gitignore` deliberately does not ignore `.hitl/` wholesale (it ignores only `*.tmp`,
`*.migrated`, `first-pass-choices.json`, `backups/`). And `_dirty()` in the gate exempts `.hitl/`
by prefix (`EXEMPT_PREFIXES = (".hitl/",)`), so the one check that normally catches unreviewed
content in the working tree — *"the build packages the working tree, so this would ship
unreviewed"* — specifically cannot see these files.

Net effect: N reviewer reports, each a complete written map of the product's weaknesses including
every finding marked `accepted` or deferred (i.e. the known-unfixed list), sit untracked and
un-ignored in a repo during a release, invisible to the gate, one `git add -A` away from being
published. This repo publishes to a public remote.

Worse, the skill instructs that the reason be **put in the brief**. `SKILL.md:126`, item 8 of
*"Each brief must contain, in this order"*:

> **Working rules** — scratch directories only, restore anything touched, never modify tracked
> files. Writing its own report file is the one exception, and `.hitl/` is exempt from the gate's
> uncommitted-changes check for exactly this reason.

That sentence tells an adversarial agent, in its own brief, which directory the release gate does
not look at. The reviewer needs to know it may write its report. It does not need to know the gate
is blind there. I verified the consequence is real: a `skips:` block added to
`.hitl/current-change.yaml` — same exempt directory — turns a blocked release green with no
staleness or dirty complaint (`H2` above). Nothing sandboxes a subagent's writes to the path it
was given.

**Smallest fix:** add `.hitl/reviews/incoming/` to `.gitignore`, and cut the clause after *"the
one exception"* from the brief template. Both are one line.

---

## LOW-1 — the rewritten boundary-error message is unreachable; what a user sees is a YAML traceback

`check-domain-boundary.sh:88-90` was rewritten to *"⚠️ I could not read
.hitl/current-change.yaml..."*. It cannot run. `set -euo pipefail` is in effect (line 9) and the
message sits behind `PYEXIT=$?` after an assignment from command substitution — `set -e` kills the
script at the assignment, so `PYEXIT` is never evaluated:

```
$ printf ':::not yaml:::\n  - [\n' > .hitl/current-change.yaml
$ echo '{"tool_name":"Edit","tool_input":{"file_path":"src/a.py"}}' | bash hooks_new/check-domain-boundary.sh
HITL_PARSE_ERROR: while parsing a flow node
expected the node content, but found '<stream end>'
  in ".hitl/current-change.yaml", line 3, column 1
new exit=1
                                    # v2.7.1: byte-identical, exit=1
```

Not a regression, and exit 1 vs 2 means the edit is still allowed either way. It matters only
because this is the commit titled *"stop talking like a compiler to someone who was editing a
file"*, and the message it actually leaves in front of that person is a Python YAML traceback,
in the same file it edited.

---

## LOW-2 — `DUPLICATE_ROUND` now blocks two legitimately distinct names and tells the user to stop doing something they did not do

Alias collapse happens before duplicate detection, so a round using an old name and its canonical
partner is reported as one lens filed twice:

```
=== F: release, lenses install + upgrade   → 2.8.0 blocks ['DUPLICATE_ROUND','LENS_FLOOR']
=== G: release, lenses data + migration    → 2.8.0 blocks ['DUPLICATE_ROUND','LENS_FLOOR']
```

Blocking is arguably right — they *are* the same lens. The message is not: it says *"`data-2`
counts as `data`: pick a second lens ... instead of numbering this one."* Nobody numbered
anything. Someone who used `migration` because the catalog's *Older names* section says it still
resolves gets told to stop numbering.

---

## LOW-3 — the onboarding docs still print the old hook output

```
$ grep -n "HITL BLOCKED" docs/getting-started.md site/getting-started.html
docs/getting-started.md:16:HITL BLOCKED: no active change for this project/branch.
site/getting-started.html:303:    <pre><code>HITL BLOCKED: no active change for this project/branch.</code></pre>
```

The hook now prints *"🔒 Nothing is tracked for this branch yet, so edits are paused."* (verified
by running it). The first document a new user reads shows output they will never see, in a release
that touched five other site pages.

---

## Areas I attacked and found sound

- **The rewritten findings loop does not fail open.** I ran the same fixtures through both
  versions across eight shapes — a non-selected record with an open CRITICAL, with a non-list
  `findings`, with an invalid severity, with an unsigned acceptance, a single record with
  `findings: "oops"`, `findings: null`. Every case is either identical or blocks in 2.8.0 where
  2.7.1 passed. I found no input where 2.7.1 emits a block code that 2.8.0 does not.
  (`E2`–`E8`: `FINDING_OPEN`, `REVIEW_MALFORMED`, `REVIEW_MALFORMED`, `UNSIGNED_ACCEPTANCE` all
  newly caught.) The rename inside the loop is consistent; `rec` is always a member of `latest`,
  so nothing the old code inspected is now unread.
- **`canonical_lens` does not mangle the catalog.** All 13 ids round-trip unchanged; all 5 aliases
  resolve to their documented target. The suffix-stripping regexes do not collide with any real
  lens id.
- **`is_release` detection is correct.** `workflows.yaml` defines `id: release`; the gate parses
  YAML rather than grepping, so the `id: "release"` quoting hazard documented in
  `validate/SKILL.md:89` does not apply here.
- **The five hooks still gate identically.** A differential matrix across eleven conditions —
  no change file, `.hitl/` bootstrap path, missing required field, branch mismatch, branch gone,
  status blocking source, status allowing docs, malformed YAML, path outside/inside
  `allowed_paths` — produced identical exit codes on v2.7.1 and HEAD in every case. The message
  rewrite did not move a control-flow branch. `check-domain-boundary.sh` still advises rather than
  blocks; `rebuild-graph.sh` still backgrounds and exits 0.
- **The lens catalog is genuinely tied to the code.** `check_review.py`'s claim that "a test
  asserts these ids match the catalog" is true: `ci/wiring/test_wiring.py:317-341` parses
  `ai/shared/adversarial-review.md` and checks both directions plus the alias map.
- **`.hitl/reviews/incoming/*.md` is not parsed by the gate.** `os.listdir` is non-recursive and
  filters on `.yaml`/`.yml`, so a hostile `.md` there cannot become a review record. The exposure
  is the one in MEDIUM-3, not gate input.
- **`plugin.json` is valid JSON at 2.8.0** and the regenerated catalog page contains the `release`
  workflow the generator's new `check_order_covers` guard was added to catch.
- **Full suite green:** `python3 -m pytest ci/ -q` → `728 passed in 45.49s`.

---

## VERDICT: DO NOT SHIP

Two things must change. Both are small.

1. **`ci/adversarial/check_review.py`, `LENS_FLOOR`:** count distinct lenses across `records`
   (every round of the change) instead of `latest` (the top round only). One expression. This
   removes the case where a release is blocked *for having done a second round of review*, and
   with it the pressure toward a waiver that discards open CRITICALs. The message should also stop
   pointing at the acknowledged skip, which waives the entire gate rather than the missing lens.

2. **`ai/claude/adversarial-review/SKILL.md:140`:** delete *"Give each reviewer a distinct name so
   the reports are attributable."* One line. It directly contradicts line 94 and re-arms the
   reports-never-arrive failure this release was written to fix.

Everything else on this list is worth fixing but does not have to gate the release. If only one
more is taken, take HIGH-1: the upgrade note is what decides whether an existing project re-runs
the gate before publishing, and it currently tells them not to bother.
