# Upgrade review — 2.9.0 RC, round 3 (c6adfc4)

Lens: someone already on 2.8.0, and the next fresh install.
Base: `git diff 07bda66..HEAD` (the round-2 sequencing change) and `git diff v2.8.0..HEAD`.
HEAD = `c6adfc43d90de3d5788c70b3b8e51a5343f6445f` on `main`.

Method: a real 2.8.0-era product repo built by `tools/scripts/init-project.sh` off a `v2.8.0`
worktree; a real 2.9.0 plugin built by `../hitl-claude-plugin/scripts/build.sh` into a scratch copy;
the whole intake → apply-change → selection path run against both. Every finding below was
reproduced; commands and observed output are inline. Nothing in the source tree or `.hitl/` was
modified; all writes were in `mktemp`-style scratch dirs.

**Verdict: DO NOT SHIP.**

The round-2 fix does what it claims — a project that upgrades without refreshing its catalog is not
silently lightened, and I could not break that from any path. But moving the selection to
apply-change step 3a introduced a new failure the round-1/round-2 defects hid, and it left three
files describing the version that was deleted. Two findings round 2 named by name are unfixed.

---

## Summary

| # | Severity | Finding |
|---|---|---|
| U1 | **HIGH** | `plan_select.py apply` will mark the **current** step `skipped`. Nothing then has status `current`, so `welcome.sh` and `statusline-hitl.sh` both lose the step trail for the rest of the change and print "run `/hitl:dev-update` to migrate this change to the self-describing workflow format" — a file already in that format, and an instruction that cannot fix it. |
| U2 | **HIGH** | The coherence challenge is dead for **5 of the 11** dependencies, including the RED/GREEN pair that both the CHANGELOG and `selection.md` use as their worked example. `kept = asked \| {locked}` puts `red`, `green` and `deploy` in `kept` unconditionally, so nothing that needs them can ever be reported. CHANGELOG:58 "Eleven such dependencies challenge the selection and take an answer" is false. |
| U3 | **HIGH** | The tier-0/1 First Pass path lost its writer. `plan_select.py choices` is invoked by **no shipped file**; `first-pass-choices.md:14` says "the command is in `selection.md`" and round 2 deleted it from there; `test_wiring.py` now *forbids* any writer of that file under `start-change/`. Intake Step 6 still reads `CHOICES` (`SKILL.md:223`). A confirmed "decline all eleven ceremony steps" at tier 0/1 is discarded silently. |
| U4 | **HIGH** | *(round-2 finding, quoted in that report, not fixed)* `start-change/SKILL.md:102` still tells the model "the generator … refuses a tier 2+ without them when the shape probe said the change was trivial". No such refusal exists at HEAD, in the same file, 130 lines later. |
| U5 | **HIGH** | The intake shape probe is **not** removed. `right-sizing.md:18` ships a `git diff` probe, wired from intake Step 3b, which runs before Step 5 creates the branch. Reproduced: it returns zero lines. The decision table has no row for an empty result and both rows that match "non-source only" propose the lighter tier. CHANGELOG:86 "Both the probe and that refusal are removed rather than patched" is false. |
| U6 | MEDIUM | `apply` is a one-way ratchet. Re-running it keeping **every** step leaves all 26 steps `skipped` with 26 decline records attributed to a named human. There is no undo through the tool. |
| U7 | MEDIUM | The selection functions for **1 of the 8 shipped workflows**. 53 of 87 shipped step keys have no `forgo_cost`/`protects`, so `docs`, `release`, `brownfield`, `migration`, `migration_review`, `prd` and `platform` never collapse, render an empty "what you'd lose" column, and write skip records reading `(rank medium): no reason recorded`. Nothing says so. |
| U8 | MEDIUM | CHANGELOG:93-94 "a project that has not refreshed its copy gets the plan in catalog order, which is what it got before" is false and contradicts CHANGELOG:69-70 in the same entry. It is leftover from the pre-round-2 draft, in the paragraph written for exactly this lens. |
| U9 | MEDIUM | *(round-2 G4, not fixed)* `selection.md:101` "The floor can be unticked … reachable from here for the first time." The tool cannot express it: an unticked floor step yields no skip, no record and no prompt. |
| U10 | MEDIUM | *(round-2 G5, same contradiction, new location)* Intake `SKILL.md:160` says above tier 1 First Pass "is opt-in and the full plan is the default". apply-change 3a runs the selection unconditionally at every tier and declines **21 of 34** steps at tier 2 by default. The upgrade note never mentions this. |
| U11 | MEDIUM | `plan_select.py apply` never sets `first_pass`, so `migrate_project.py` — run by `dev-update` Step 3b — reports every change the new tool wrote as "lightened without declaring `first_pass` … It will now fail." It does not fail (`check_skips` exits 0 with a warn). A guaranteed false alarm telling users to edit or revert a correct record. |
| U12 | LOW | *(round-2 G7, and regressed)* `ci/retired-tests.sha256`'s `test_rank.py` hash is stale **again** — round 1 fixed it, round 2 edited `test_rank.py` and did not update it. CHANGELOG:76 "Fixed … a stale retired-test hash" is false at HEAD. |
| U13 | LOW | `selection.md:9-10` "Shown at intake … Called from Step 4" — contradicted by its own next section, three lines below. |
| U14 | LOW | `render()` truncates `protects` at 56 chars mid-word. Half the "what you'd lose" column ends in a comma or a cut word. |
| U15 | LOW | `apply` prints "wrote N skip records" where N is the total in the file, not what it wrote. Observed "wrote 3" after writing 2. |
| U16 | LOW | A phase whose steps were all declined renders `✓` in the breadcrumb ribbon, identical to a completed phase. Newly reachable: at tier 2 the default selection declines all of Assess and Post-Ship. |
| U17 | INFO | `/Users/Prasad_1/Projects/hitl-claude-plugin/shared/ci/first-pass/__pycache__/` exists in the publishing repo's working tree. `build.sh`'s own post-build assertion fails on it. The next real release build will stop with "BUILD FAILED" until it is deleted. |

---

## Areas I could not break — stated plainly

- **Priority 1, the un-refreshed upgrade case: the round-2 fix holds.** With the plugin at 2.9.0 and
  the repo's `ci/first-pass/workflows.yaml` still at 2.8.0, `sizable()` returns False, nothing
  collapses, and the whole 29-step plan is shown. No silent lightening. I could not make a plan
  collapse without `step_costs` from any input I tried.
- **Priority 2, packaging: sound.** `plan_select.py` and `rank.py` ship under
  `shared/ci/first-pass/`, land via both `init-project.sh` and `dev-update` Steps 3b/4.6, and run
  correctly from every copied location (plugin root with cwd = product repo; product repo's own
  copy). No `.py` packaged under `shared/` shadows a stdlib module name — checked mechanically
  against `sys.stdlib_module_names`, not by eye.
- **Priority 3, no corruption of an older change file.** `apply` against the real `v2.8.0`
  `.hitl/current-change.yaml` preserved `done` statuses, the existing floor skip with its `ack_by`
  and `waiver_ref`, and the YAML anchor/alias pair; both the repo's 2.8.0 `check_skips.py` and the
  2.9.0 one accept the result (exit 0). Formatting is rewritten (flow → block style) and the one
  comment in the file is lost, but nothing is corrupted.
- **Priority 4, the removal list.** Nothing that ships into a synced directory is uncovered:
  `build.sh` and `init-project.sh`'s `hitl_copy_tools` both filter `test_*`, verified by a fresh
  `init-project.sh` run producing zero `test_*.py` anywhere in the target. `ci/wiring/` is synced by
  nothing. The only defect is U12, which is inert for the same reason.
- **`/hitl:dev-update` converges.** Steps 3b and 4.6 run verbatim against the 2.8.0 repo, install
  `plan_select.py` + `rank.py`, refresh `workflows.yaml` to the 2.9.0 catalog, and the selection then
  renders fully with ranks and `protects`. Confirmed end to end.
- The suite is green at HEAD: `791 passed in 49.19s`.

---

## Reproductions

### Setup (used by everything below)

```bash
git worktree add --detach $S/src280 v2.8.0
bash $S/src280/tools/scripts/init-project.sh $S/proj --tool claude --name demo   # a 2.8.0 repo
cp -R ~/Projects/hitl-claude-plugin $S/plug290 && rm -rf $S/plug290/.git
HITL_SOURCE_DIR=~/Projects/hitl-dev-platform bash $S/plug290/scripts/build.sh    # the 2.9.0 plugin
# an authentic 2.8.0 change file, from the Step 6 generator lifted out of v2.8.0's SKILL.md
python3 $S/gen280.py development GH-1 issue/1-add-thing 2.8.0 2 $S/nope.json "" "" \
  > $S/proj/.hitl/current-change.yaml
```

### U1 — the selection can kill the breadcrumb

At apply-change 3a the current step is whatever intake left. `issue` is step 1 and is **offered**,
not locked, so unticking it is an ordinary choice ("we're not filing an issue for this").

```bash
$ cd $S/proj && python3 ci/first-pass/plan_select.py apply \
    --workflows ci/first-pass/workflows.yaml --workflow development --tier 2 \
    --keep "impact,review1,verify_pr" --actor me
wrote 26 skip records to .hitl/current-change.yaml

$ python3 -c "import yaml;d=yaml.safe_load(open('.hitl/current-change.yaml'));\
print('current_step:',d.get('current_step'));\
print('issue status:',[s['status'] for s in d['workflow']['steps'] if s['key']=='issue'])"
current_step: {'number': 1, 'name': 'Issue', 'phase': 'Requirements'}
issue status: ['skipped']

$ CLAUDE_PROJECT_DIR=$PWD bash .hitl/hooks/welcome.sh <<< '{}'
  HITL — Requirements  •  Step 1: Issue
  change: GH-1  •  tier: 2
  (step trail unavailable — run /hitl:dev-update to migrate this change to the
   self-describing workflow format)

$ CLAUDE_PROJECT_DIR=$PWD bash .hitl/hooks/statusline-hitl.sh <<< '{}'
  |  HITL: Requirements · Step 1 [GH-1 · T2]   (run /hitl:dev-update for the step trail)
```

The same file **before** `apply` renders the full ribbon and trail. Cause:
`welcome.sh:53` `cur=$(hitl_current_n "$HITL_FILE")` — nothing has status `current` any more, so
both hooks fall through to the pre-v2 back-compat branch. `apply_to_change` guards
`status not in ("done",)` and does not guard `"current"`. Running `/hitl:dev-update` as instructed
changes nothing, because the file is already current-format.

Note the breadcrumb also still announces "Step 1: Issue" as the thing to do, while the ledger says
Issue was declined by name.

**Smallest fix:** in `apply_to_change`, either exclude `current` from the statuses it will overwrite,
or re-point `current_step` (and set `status: current`) to the first kept step after skipping.

### U2 — five of the eleven coherence dependencies can never fire

```bash
$ python3 - <<'PY'
import sys,yaml; sys.path.insert(0,'ci/first-pass'); import plan_select as P
wf=yaml.safe_load(open('ai/shared/workflows.yaml')); plan=wf['workflows']['development']['steps']
for tier in (1,2,3):
    l,o,t=P.build(plan,wf['step_costs'],wf['step_requires'],tier=tier,paths=[],profile='',
                  tags=[],manifest={},incidents={})
    locked={r['key'] for r in l}
    dead=[(k,n) for k,v in wf['step_requires'].items() for n in v['needs'] if n in locked]
    print("tier %s: dead %d/11 -> %s" % (tier,len(dead),dead))
PY
tier 1: dead 5/11 -> [('verify_red','red'),('green','red'),('verify_green','green'),('design_plus','red'),('promote','deploy')]
tier 2: dead 5/11 -> [same]
tier 3: dead 5/11 -> [same]
```

Confirmed live, not theoretical:

```bash
$ python3 ci/first-pass/plan_select.py apply … --keep "issue,green,verify_pr" --actor me
wrote 27 skip records to .hitl/current-change.yaml        # dropping red while keeping green: silent

$ python3 ci/first-pass/plan_select.py apply … --keep "issue,reconcile" --actor me
incoherent: keeping reconcile while dropping review1 — reconciling findings from a review that did not happen
```

`plan_select.py:188` `kept = asked | {r["key"] for r in locked}` — `red`, `green` and `deploy` are
always in `kept`, so `incoherent()` can never see them missing. The six that work are the three that
need `review1`, plus `figma_compare`/`roi_30`/`roi_90`.

The example the feature is sold on is one of the dead five. CHANGELOG:57-58: *"GREEN is defined
against a RED that was never generated. Eleven such dependencies challenge the selection."*
`selection.md:117`: *"Keeping **GREEN** but dropping **RED**. That is a fix with no failing test
behind it."* That conversation cannot happen.

**Smallest fix:** pass `asked` (not `asked | locked`) to `R.incoherent()`, keeping the union for the
skip-writing loop — or delete the claim and the two worked examples.

### U3 — the tier-0/1 choices path has no writer

```bash
$ grep -rn 'plan_select.py choices\|"\$SEL" choices' ai/ ci/ tools/ --include=*.md --include=*.sh --include=*.py
ai/claude/start-change/first-pass-choices.md:8:**Do not hand-write it.** `ci/first-pass/plan_select.py choices` writes
```

One hit, and it is prose. `first-pass-choices.md:14` says *"The command is in `selection.md`, beside
this file"*; `git diff 07bda66..HEAD -- ai/claude/start-change/selection.md` shows round 2 deleted
that invocation. `grep -n choices ai/claude/start-change/selection.md` returns three prose lines and
no command.

Meanwhile intake still consumes the file — `SKILL.md:223`
`CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b; absent ⇒ full plan, no First Pass` —
and `test_wiring.py:771-786` now asserts that **no** file under `start-change/` may write it.

So at tier 0/1, where `right-sizing.md` promises *"One confirmation clears all eleven"*, the model
is told (a) do not hand-write the file, (b) the command is in a file that does not contain it, and
(c) a guard fails the build if it writes it. The human confirms, nothing is written, Step 6 sees an
absent `CHOICES`, and the full plan is seeded. The confirmed decision is discarded.

Secondary: even if invoked, `choices` mode can only emit `disposition: decline`, while
`first-pass-choices.md`'s own worked JSON shows `"docs": {"disposition": "starter"}` and its rules
section requires `starter`/`defer` with `followup_ref`. The one sanctioned writer cannot produce the
documented output.

**Smallest fix:** either restore a `choices` invocation to `first-pass-choices.md` (and narrow the
wiring guard to `selection.md`), or delete Step 4b's choices path and say plainly that tier-0/1
lightening now happens at apply-change 3a like everything else.

### U4 — a refusal that does not exist, asserted in the file that would implement it

```bash
$ sed -n '101,102p' ai/claude/start-change/SKILL.md
Tiers are defined in [`/hitl:dev-practices`]… Both departures from the tier you proposed are
attributed: the generator refuses a tier 0/1 without `tier_set_by` and `tier_reason`, and refuses a
tier 2+ without them when the shape probe said the change was trivial.

$ grep -rn "TRIVIAL_SHAPE" ai/claude/start-change/ ci/first-pass/plan_select.py
ai/claude/start-change/SKILL.md:102:…when the shape probe said the change was trivial.
```

The only surviving reference is the sentence claiming the behaviour. Extracting the Step 6 generator
from the same file and listing its `sys.exit` calls shows the tier-0/1 refusal and nothing else.
`git diff 07bda66..HEAD -- ai/claude/start-change/SKILL.md | grep "refuses a tier"` returns nothing:
round 2 did not touch it, though round 2's report listed this exact sentence under "What is now
false in the CHANGELOG".

**Smallest fix:** delete "` , and refuses a tier 2+ … trivial`" from line 102.

### U5 — the intake shape probe still ships, and it still returns nothing

`right-sizing.md` is new in this release (`git log v2.8.0..HEAD -- …/right-sizing.md`). Intake
Step 3b points at it: *"**Look at what the change touches before you propose a tier**
([`right-sizing.md`](right-sizing.md))"*. Step 5 creates the branch — after Step 3b.

```bash
$ cd $S/probe && git log --oneline
0e3f0b1 init                       # on main, HEAD == main, as at intake
$ BASE=main; git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD | sed -n '1,200p'
$ echo "lines: $(git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD | wc -l)"
lines: 0
```

The table in `right-sizing.md:22-26` has three rows and none of them is "empty". An empty file list
is vacuously "non-source only", and both rows that match it propose down — tier 0/1 if the ask reads
as a value, tier 2 otherwise. Tier is what decides which steps are `floor`: 3→2 takes `impact`,
`packet`, `arch_review`, `qa_verify` and `rollout` off the floor, and 2→1 takes `integration_verify`.
So the probe biases the proposal toward the tier that unlocks five floor steps for ordinary
unticking at 3a.

CHANGELOG:83-87 says an earlier draft *"tried to compute a change's shape **at intake**, from
`git diff`… It could not work — at intake nothing has been written, so there is no diff… Both the
probe and that refusal are removed rather than patched."* One of the two is not removed; it is one
file over and newly shipped in this release.

**Smallest fix:** either delete the probe block from `right-sizing.md` and let the tier proposal come
from the request text alone, or add the row the table is missing ("no diff yet — the probe says
nothing; propose from the request") and correct CHANGELOG:86.

### U6 — no undo

```bash
$ python3 ci/first-pass/plan_select.py apply … --keep "impact,review1,verify_pr" --actor me
wrote 26 skip records
# now keep every single step in the plan
$ python3 ci/first-pass/plan_select.py apply … --keep "<all 34 keys>" --actor me
wrote 26 skip records
$ python3 -c "…"
statuses after keeping EVERYTHING: {'skipped': 26, 'open': 8}
skip records still present: 26
```

A mistyped `--keep`, or a human who unticks and changes their mind, leaves 26 declines permanently
attributed to that person. The tool has no path back; every doc tells them not to hand-edit the file.
`check_skips` certifies the result clean.

### U7 — the selection works for one workflow out of eight

```bash
$ python3 - <<'PY'   # against the SHIPPED shared/workflows.yaml
…
development        steps=34 costed=34 sizable=True   missing=[]
brownfield         steps=11 costed= 1 sizable=False  missing=['map_code','claude_md','manifest',…]
migration          steps= 9 costed= 0 sizable=False
migration_review   steps= 5 costed= 0 sizable=False
docs               steps= 6 costed= 2 sizable=False  missing=['scope','draft','doc_review','merge']
prd                steps= 5 costed= 0 sizable=False
platform           steps=17 costed= 0 sizable=False
release            steps=12 costed= 0 sizable=False
PY
distinct step keys across all workflows: 87 ; step_costs entries: 38
```

Reproduced against the real `v2.8.0` release change file with the **current** catalog:

```bash
$ python3 …/plan_select.py apply --workflows $S/plug290/shared/workflows.yaml \
    --workflow release --tier 2 --keep "build,publish,tag" --actor pappar
$ …
announce | decline | pappar | not selected at right-sizing (rank medium): no reason record…
retire   | decline | pappar | not selected at right-sizing (rank medium): no reason record…
```

`(rank medium)` is not a computed rank — it is `_idx()`'s fallback for absent data, written into the
durable ledger as though it were a finding. On seven of eight workflows every skip record will say
this. `protects` is empty, so the "what you'd lose" column the feature exists for is blank, on a
fresh install, with a fully current catalog.

### U8 — the upgrade note describes the deleted behaviour

CHANGELOG:69-71 (Fixed): *"the plan is shown whole and nothing is collapsed. An earlier version …
fell back to **catalog order** … Strictly worse than the problem this release exists to fix."*
CHANGELOG:93-94 (Note for existing projects): *"a project that has not refreshed its copy gets the
plan in **catalog order**, which is what it got before."*

Neither half is right. What it actually gets, reproduced:

```bash
$ cd $S/proj && python3 $S/plug290/shared/ci/first-pass/plan_select.py render \
    --workflows ci/first-pass/workflows.yaml --workflow development --tier 2 \
    --paths "src/api/orders.py,docs/runbook.md"
Running (locked)
   red                thinnable, never dropped
   green              thinnable, never dropped
   integration_verify floor at tier 2
   deploy             floor at tier 2
   promote            floor at tier 2

Selected — untick any                      what you'd lose
   [x] issue            medium
   [x] figma            medium
   …29 rows, every rank "medium", every `protects` blank…
```

Five locked steps hoisted out of order, 29 checkboxes with an empty consequence column, and a
`--keep` that mass-declines everything not named. That is neither catalog order nor "what it got
before" — on 2.8.0 there was no selection at all. No message anywhere tells the reader their catalog
is stale or to run `/hitl:dev-update`; the degrade is completely silent, which is safe but leaves
them permanently on the blank-column version with no idea it is fixable.

**Smallest fix:** rewrite CHANGELOG:93-94 to match CHANGELOG:69-71, and have `render()` print one
line when `sizable()` is False: "no `step_costs` in this catalog — showing the whole plan; run
`/hitl:dev-update` to get the ranked view."

### U9 / U10 — two round-2 findings unchanged

U9: `install_verify` is `floor` at tier 2. Unticking it:

```bash
$ python3 …/plan_select.py apply --workflow release --tier 2 \
    --keep "build,publish,tag,announce,retire" --actor pappar     # install_verify NOT kept
wrote 1 skip records
install_verify status: ['open'] ; skip records for install_verify: []
```

`selection.md:101-108` promises the opposite, with a worked "Unticking **pentest** … who is
accepting that, and against which waiver?" prompt.

U10: apply-change Step 3a has no tier condition. At tier 2 the default selection is:

```
offered   : issue, impact, verify_green, review1, arch_review, qa_verify, rollout, verify_pr
COLLAPSED : packet, adv_design, design_plus, verify_red, adv_code, rerun, reconcile, figma, roi,
            docs, iac, test_plan, training, test_review, refactor, conventions, review2,
            impact_brief, figma_compare, roi_30, roi_90        (21 of 34)
```

`selection.md` shows the tail as one line naming six of them, so `conventions`, `review2` and
`test_plan` are inside the "…". That is the release's intended behaviour and the CHANGELOG describes
it — but intake `SKILL.md:160` tells the user the opposite ("above tier 1 it is opt-in and the full
plan is the default"), and the "Note for existing projects" never states the one thing an upgrading
team most needs to know: after `/hitl:dev-update`, an ordinary tier-2 change defaults to declining
21 of 34 steps.

### U11 — the new tool's output trips the migrator on the next update

```bash
$ python3 ci/first-pass/migrate_project.py --root .
! this change was lightened without declaring `first_pass`:
    26 skip record(s)
    lightened step(s): figma, impact, roi, docs, …
  It certified clean before because enforcement never engaged. It will now fail.
  If the change really is running First Pass, add `first_pass: true`.
  If not, restore the steps. Do not delete the records to make the check pass.

$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[warn] FP_ABSENT_ENFORCED: first_pass is absent, but this change carries attributed skips — enforcing the full ruleset on them.
$ echo $?
0
```

`apply_to_change` never sets `first_pass`. The Step 6 generator only emits it when a choices file
exists — which, per U3, it now never does. So on every 2.9.0 change the migrator says "It will now
fail" about something that passes, and offers two remedies, one of which ("restore the steps")
undoes the release's whole feature.

**Smallest fix:** have `apply_to_change` set `first_pass: true` when it writes any record.

### U12 — the retired-test hash is stale again

```bash
$ shasum -a 256 ci/first-pass/test_rank.py
f3afb383b3a0e092c8034b4d848b48d300d8b2c31b9cf2727b1b9f67f00baddd
$ grep test_rank ci/retired-tests.sha256
e7f86c39f148377f207651fc3b3745f95ef06e9ec5850f28b62a536e160cefaf  test_rank.py
$ git show 07bda66 -- ci/retired-tests.sha256 | tail -2
-3b25391d…  test_rank.py
+e7f86c39…  test_rank.py            # round 1's fix, matching 07bda66's file
```

`e7f86c39` matched the file at `07bda66`/`0a0b256`. Round 2's `c6adfc4` rewrote `test_rank.py`
(+99 lines) and left the manifest. `791 passed` — nothing checks the manifest against the files it
names, so the round-1 fix has no guard against exactly this recurrence. Inert in practice
(`build.sh` filters `test_*`, so `test_rank.py` has never reached a product repo, confirmed by a
fresh `init-project.sh` run finding zero `test_*.py` in the target), but CHANGELOG:76 claims it
fixed.

### U17 — the publishing repo will not build

```bash
$ ls /Users/Prasad_1/Projects/hitl-claude-plugin/shared/ci/first-pass/
__pycache__  check_skips.py  dispositions.py  migrate_project.py  permissions.py  rank.py  resurface.py  starters.py
$ HITL_SOURCE_DIR=… bash scripts/build.sh
BUILD FAILED — these would ship to every consumer and cannot run there:
  …/shared/ci/first-pass/__pycache__/rank.cpython-313.pyc
```

Left behind by a review round importing `rank.py` from the packaged copy. `rm -rf` it before the
release build; the assertion itself is working correctly.

---

## The smallest change that clears the verdict

Five edits, four of them one line:

1. `plan_select.py apply_to_change` — do not overwrite `status: current` (U1), and set
   `first_pass: true` when writing records (U11).
2. `plan_select.py:188` — pass `asked`, not `asked | locked`, to `R.incoherent()` (U2).
3. `ai/claude/start-change/SKILL.md:102` — delete the clause about the tier 2+ refusal (U4).
4. `ai/claude/start-change/right-sizing.md` — delete the `git diff` probe, or add the empty-result
   row (U5).
5. Decide U3: restore the `choices` invocation, or delete Step 4b's choices path. Whichever, the
   three files that reference it must agree.

Then CHANGELOG:58, :76, :86 and :93-94, and `selection.md:9-10`, need to match what ships.
