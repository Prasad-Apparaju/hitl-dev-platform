# Consequence review — HITL 2.9.0, round 3

- **State:** `c6adfc43d90de3d5788c70b3b8e51a5343f6445f` on `main`
- **Lens:** consequence — what this destroys, exposes, or makes unrecoverable
- **Verdict: DO NOT SHIP**
- Every finding below was reproduced. Commands and output are inline. Nothing is inferred from reading alone.
- Reproduction environment: `mktemp -d` product repo with `ci/first-pass/*` and `workflows.yaml` copied
  from the tree, change files produced by the real intake generator extracted verbatim from
  `ai/claude/start-change/SKILL.md`. No tracked file was modified.

The round-2 fix is correct about the cause and wrong about the cure. Moving the selection to
apply-change step 3a moved the writer **past the only reader**, and rebuilt the writer without the
four guards the intake writer had. The result is worse than the sequencing bug it fixes: 2.8.0 ran
too many steps; 2.9.0 as it stands declines architecture review, QA verification, code review and the
rollout plan in a named human's name, records "no reason recorded" as the reason, and exits 0 with
the fail-closed validator reporting the change clean.

---

## C1 — CRITICAL. The fail-closed validator is now downstream of nothing

`check_skips.py` is invoked in exactly one place in the entire workflow surface:

```
$ grep -rn "check_skips" --include=*.md --include=*.sh --include=*.yml ai/ .github/
ai/claude/start-change/SKILL.md:434:CHK="ci/first-pass/check_skips.py"; RS="ci/first-pass/resurface.py"
ai/claude/start-change/SKILL.md:435:[[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/first-pass/check_skips.py"
ai/claude/start-change/first-pass-choices.md:43:CHK="ci/first-pass/check_skips.py"
(remaining hits are imports of resolve_crit, or prose)
$ ls .github/workflows/
pages.yml  tests.yml          # neither runs check_skips
```

`start-change/SKILL.md:434` is intake Step 6.5 — "Run it **before** the Step 7 commit". It runs
**before** step 3a exists. `ai/claude/apply-change/SKILL.md` never invokes the validator: the new
Step 3a writes skip records and hands off to Step 4 (Documentation Plan). Step 7a runs
`resurface.py --append`, which folds skips into the roll-up without validating them.

So: every skip this feature produces is written by `plan_select.py apply` and read by nothing. The
CHANGELOG's load-bearing sentence — *"an attributed entry in `skips[]`, which is what the fail-closed
validator reads"* — describes a reader that is not wired to the writer. Findings C2, C3, C5 and C10
below are all caught by `check_skips.py` when run by hand, and by nothing in the shipped flow.

This is the same defect class 2.9.0 was written to fix ("three features were built, tested, shipped
and invoked by nothing"), reintroduced by the fix.

**Smallest fix:** append `python3 "$CHK" .hitl/current-change.yaml` to Step 3a, and stop on exit 2.

---

## C2 — CRITICAL. `apply` writes an unattributed ledger, then cannot repair it, while reporting success

`--actor` is validated only in `choices` mode. `plan_select.py:191-201` returns from `apply` before
reaching the guard at line 203:

```python
    if a.mode == "apply":
        ...
        return 0
    doc, warn = choices(...)
    if not a.actor.strip():
        print("--actor is required: a skip is accountable to a person, not the agent", ...)
```

`choices` mode is now unreachable from any skill (C7). The guard protects the dead path; the live
path has none.

```
$ python3 ci/first-pass/plan_select.py apply --workflows ci/first-pass/workflows.yaml \
    --workflow development --tier 2 --paths "src/api/orders.py,docs/hld.md" \
    --keep "issue,impact,verify_green,review1,arch_review,qa_verify,rollout,verify_pr"
wrote 21 skip records to .hitl/current-change.yaml
EXIT=0

$ python3 -c "import yaml;d=yaml.safe_load(open('.hitl/current-change.yaml'));print(sorted({repr(e.get('actor')) for e in d['skips']}))"
["''"]

$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[BLOCK] FP_UNDECLARED: ... 21 unattributed entries in skips[] ...
EXIT=2
```

Now the unrecoverable part. `apply_to_change` dedupes on step key (`existing`), so re-running the
sanctioned command with the correct actor is a **no-op that prints success**:

```
$ python3 ci/first-pass/plan_select.py apply ... --actor "priya@team"
wrote 21 skip records to .hitl/current-change.yaml
EXIT=0
$ python3 -c "...print(sorted({repr(e.get('actor')) for e in d['skips']}))"
["''"]                                   # unchanged
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[BLOCK] FP_UNDECLARED: ... 21 unattributed entries in skips[] ...
EXIT=2                                   # still blocked
```

One omitted flag permanently poisons the change file. The only repair is hand-editing
`.hitl/current-change.yaml` — the file the whole model says only the tool may write. The tool tells
you it succeeded while doing nothing, twenty-one times.

**Smallest fix:** move the `--actor` guard above the mode dispatch, and make `apply` update an
existing entry rather than skip it when the field differs.

---

## C3 — CRITICAL. The tier is a CLI flag defaulting to 2, never read from the file being written

`apply` writes into a change file that declares its own `tier`, and never looks at it. The floor —
the one boundary the model says needs a signature — is decided by an argparse default.

```
$ CLAUDE_PLUGIN_ROOT=$PWD python3 gen.py development GH-88 feature/y 2.9.0 3 ... > .hitl/current-change.yaml
$ grep '^tier:' .hitl/current-change.yaml
tier: 3

$ python3 ci/first-pass/plan_select.py apply --workflows ci/first-pass/workflows.yaml \
    --workflow development --paths "src/api/orders.py" \
    --keep "issue,impact,verify_green,review1,verify_pr" --actor "priya@team"
wrote 24 skip records to .hitl/current-change.yaml
EXIT=0

$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[BLOCK] FLOOR_NO_ACK:    floor step 'packet' skipped with no ack_by
[BLOCK] FLOOR_NO_ACK:    floor step 'arch_review' skipped with no ack_by
[BLOCK] FLOOR_NO_WAIVER: floor step 'arch_review' maps to a hard gate but has no waiver_ref
[BLOCK] FLOOR_NO_ACK:    floor step 'qa_verify' skipped with no ack_by
[BLOCK] FLOOR_NO_WAIVER: floor step 'qa_verify' maps to a hard gate but has no waiver_ref
[BLOCK] FLOOR_NO_ACK:    floor step 'rollout' skipped with no ack_by
EXIT=2
```

Four tier-3 floor steps — the design packet, architecture review, QA verification and the rollout
plan — marked `skipped` with no ack and no waiver, exit 0, "wrote 24 skip records". Per C1 nothing
runs that validator, so in the shipped flow this lands silently. Per C2 it cannot then be repaired.

This is *made likely*, not merely possible, by C12: the command block in `selection.md` needs
`$WF_ID $TIER $PROFILE $TAGS $IMPACT_PATHS`, and `apply-change/SKILL.md` defines none of them
(`grep -n "WF_ID\|IMPACT_PATHS\|TIER" ai/claude/apply-change/SKILL.md` → no output). An agent that
cannot find `TIER` reaches for the default.

**Smallest fix:** in `apply` mode, read `tier` and `workflow.id` from the change file; treat a
supplied `--tier`/`--workflow` that disagrees as a refusal, not an override.

---

## C4 — CRITICAL. `sizable()` fires at 50% coverage, and the uncosted half is exactly what gets dropped

The guard checks for *total* absence of `step_costs`. A partial refresh — the far likelier upgrade
state — passes it, and then the missing half sorts into the collapsed tail, because an uncosted step
ranks `medium` while every costed one ranks `high`.

Threshold: one step's worth of coverage flips the whole plan.

```
$ python3 -c "... for n in (16,17): print(' costed',n,'of 34 -> sizable',P.sizable(c,plan))"
 costed 16 of 34 -> sizable False
 costed 17 of 34 -> sizable True
```

At exactly the threshold, with costs for the first 17 development steps:

```
$ python3 -c "...l,o,t=P.build(plan,costs,{},tier=2,paths=['src/a.py'],...)"
locked 5 offered 8 tail 21
uncosted steps in tail: ['adv_code', 'review1', 'review2', 'arch_review', 'rerun',
 'reconcile', 'qa_verify', 'impact_brief', 'rollout', 'verify_pr', 'figma_compare',
 'roi_30', 'roi_90']
```

Code review round 1, code review round 2, adversarial code review, architecture review, the rerun,
finding reconciliation, QA verification, the impact brief, the rollout plan and PR verification — the
entire back half of the workflow — collapsed and skipped by default. Then `apply`:

```
$ python3 ci/first-pass/plan_select.py apply --workflows half.yaml --workflow development --tier 2 \
    --paths "src/a.py" --keep "issue,impact,verify_green,packet,adv_design,design_plus,verify_red,red" --actor "p@t"
$ python3 -c "...print(e['step'],'|',e['crit'],'|',e['reason'])"
  review1     | standard | not selected at right-sizing (rank medium): no reason recorded
  arch_review | standard | not selected at right-sizing (rank medium): no reason recorded
  qa_verify   | standard | not selected at right-sizing (rank medium): no reason recorded
  rollout     | standard | not selected at right-sizing (rank medium): no reason recorded
  verify_pr   | standard | not selected at right-sizing (rank medium): no reason recorded
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[warn] FP_ABSENT_ENFORCED: ...
EXIT=0                                   # clean
```

Two consequences compound here:

1. The docstring's stated scenario — *"a project that upgraded but has not refreshed its
   `ci/first-pass/workflows.yaml` would have had code review and QA silently dropped"* — happens
   anyway at ≥50% coverage, which is the state a project reaches by merging its own catalog edits
   with the shipped `step_costs`.
2. `check_skips`'s only defence against a silent skip is `reason` being non-empty. `apply`
   manufactures a non-empty reason whose content is the literal admission that there is no reason.
   The validator's emptiness test is satisfied by a string that says nothing. **This is a silent skip
   that passes the silent-skip check.**

**Smallest fix:** require full coverage (`all(costs.get(k) for k in keys)`), and refuse to write a
skip record whose `protects` is empty — no reason, no decline.

---

## C5 — HIGH. `--keep ""` annihilates the plan, exits 0, and validates clean

The intake generator refuses this exact state:
`sys.exit("every step in the plan was lightened — there is no change left to run. Keep at least one.")`
The new writer dropped the refusal.

```
$ CLAUDE_PLUGIN_ROOT=$PWD python3 gen.py docs GH-77 docs/x 2.9.0 2 ... > .hitl/current-change.yaml
$ python3 ci/first-pass/plan_select.py apply --workflows ci/first-pass/workflows.yaml \
    --workflow docs --tier 2 --paths "docs/hld.md" --keep "" --actor "priya@team"
wrote 6 skip records to .hitl/current-change.yaml
EXIT=0
$ python3 -c "...print('statuses:',{s['key']:s['status'] for s in d['workflow']['steps']})"
statuses: {'issue':'skipped','scope':'skipped','draft':'skipped','doc_review':'skipped',
           'reconcile':'skipped','merge':'skipped'}
   issue      | ...: There is a written record of what was asked for and why, ...
   scope      | ...: no reason recorded
   draft      | ...: no reason recorded
   doc_review | ...: no reason recorded
   merge      | ...: no reason recorded
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[warn] FP_ABSENT_ENFORCED: ...
EXIT=0
```

Every step of the change, including `merge`, declined in a named person's name. Four of the six
reasons are "no reason recorded". The docs workflow has no floor and no `no_omit` steps, so nothing
is locked and there is no floor to stop at.

Note what `sizable()` contributes here rather than prevents. With no `step_costs`, `build()` returns
`locked, rest, []` — the tail is empty, so **every** step is `offered`. `offered` is the set `apply`
treats as skippable-by-omission. The safety valve makes the whole plan skippable in one command, in
exactly the projects it was written to protect. The docstring — *"No basis to rank means no
collapsing: show the whole plan, exactly as before"* — is true of `render` and false of `apply`.

**Smallest fix:** refuse when `kept` is empty, and refuse when the number of steps about to be marked
`skipped` exceeds what `render` displayed as collapsed.

---

## C6 — HIGH. The selection is one-way. Restoring a step is a silent no-op reported as success

```
$ python3 ci/first-pass/plan_select.py apply ... --keep "issue,impact,verify_green,review1,verify_pr" --actor "p@t"
wrote 24 skip records to .hitl/current-change.yaml
# user: "actually, keep qa_verify, arch_review and docs"
$ python3 ci/first-pass/plan_select.py apply ... --keep "issue,impact,verify_green,review1,verify_pr,qa_verify,arch_review,docs" --actor "p@t"
wrote 24 skip records to .hitl/current-change.yaml
EXIT=0
$ python3 -c "..."
qa_verify   -> skipped
arch_review -> skipped
docs        -> skipped
still in skips[]: ['docs', 'arch_review', 'qa_verify']
```

`apply` only ever adds. A step the human explicitly asks back stays `skipped`, its decline record
stays attributed to that human, and the tool prints a success line. Combined with C3 (a wrong tier on
the first run) and C2 (a missing actor on the first run), the first invocation of step 3a is
irreversible through every sanctioned path. There is no un-skip command in the tool.

**Smallest fix:** in `apply`, restore kept steps — set `skipped` → `open` and drop their `skips[]`
entries when the step is in `kept`.

---

## C7 — HIGH. `first_pass` is now unreachable, so First Pass never engages, and 7 of 8 routes lost their writer

The generator sets `first_pass: true` only when `.hitl/first-pass-choices.json` is non-empty
(`start-change/SKILL.md:342`). Nothing writes that file any more:

```
$ grep -rn "plan_select.py" ai/
ai/claude/apply-change/SKILL.md:140:`plan_select.py apply`, ...
ai/claude/start-change/selection.md:34,41:  (render + apply only)
ai/claude/start-change/first-pass-choices.md:8:**Do not hand-write it.** `ci/first-pass/plan_select.py choices` writes
$ grep -n "choices" ai/claude/start-change/selection.md
34: ... ranks, renders, and writes the choices.     (prose)
92: **Not a choices file.** ...
```

`first-pass-choices.md:14` says *"The command is in `selection.md`, beside this file."* The round-2
diff removed that command from `selection.md`. Intake Step 4b — which is still live, still the
tier-0/1 batch-decline path, still linked from `SKILL.md:185` — now points at a command that exists
in no shipped file. `SKILL.md:223` still carries `CHOICES=".hitl/first-pass-choices.json"  # written
by Step 4b`. Step 4b writes nothing.

Consequences:

- **First Pass mode never activates.** `ai/claude/hooks/first-pass-permissions.sh:66` is
  `if change.get("first_pass") is not True: out()`. The permission relaxation and brief mode
  (`ai/shared/first-pass/brief.md`) — the entire ergonomic payoff of the lighter path, wired in
  2.5.0 — are now dead for every change. Reproduced: every change file this release produces lacks
  the key (verified across all 8 apply runs above).
- **Every right-sized change carries a permanent warning:** `[warn] FP_ABSENT_ENFORCED` on every
  clean run above.
- **The change file contradicts its own schema.** `change-context.schema.yaml:359-362`: "When true,
  this change is running in First Pass — the driver may set a step's status to `skipped` or
  `starter` ... Absent/false ⇒ the full plan runs."
- **Only the development route can size anything.** `grep -rn "Step 3a" ai/` returns exactly one hit,
  `apply-change/SKILL.md:131`. `start-brownfield`, `start-migration`, `start-from-prd` and the
  docs/prd/release/platform/migration_review workflows have no sizing step at all, and their intake
  path is the broken one. For 7 of 8 workflows First Pass now has no writer whatsoever.

**Smallest fix:** have `apply` set `first_pass: true` when it writes any record, and either restore
the `choices` command to `selection.md` or delete Step 4b's dependency on it.

---

## C8 — HIGH. The probe was deleted from the code and left in the prose, where it fails open

The CHANGELOG: *"Both the probe and that refusal are removed rather than patched."* `right-sizing.md`
is not in `git diff 07bda66..HEAD`. It still contains:

```
## The probe
git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null | sed -n '1,200p'
```

and `start-change/SKILL.md:112` still routes to it: *"**Look at what the change touches before you
propose a tier** ([right-sizing.md]): if the diff is non-source only ... propose tier 0/1 with the
reason pre-filled"*. Intake Step 3b runs before Step 5 creates the branch, so `HEAD == main`:

```
$ BASE=main; git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD | sed -n '1,200p'
$ echo "lines: 0"
lines: 0     -> matches "non-source only" -> propose tier 0/1
```

Right-sizing's closing section: *"At tier 0 or 1, **offer First Pass without being asked** and present
the ceremony steps pre-selected as declined ... One confirmation clears all eleven."*

So the round-2 fix removed the probe's **safe** consumer — the refusal that demanded a name and a
reason for running tier 2+ on a trivially-shaped change — and left the **unsafe** one: an
always-empty probe that pushes every change toward tier 1 with a pre-filled batch decline. The
direction of the residue is exactly wrong. `ci/wiring/test_wiring.py:541` guards only the generator
body (`assert "TRIVIAL_SHAPE" not in body`); it does not look at `right-sizing.md`.

**Smallest fix:** delete "## The probe", the proposal table and the "After the tier is set" section
from `right-sizing.md`, and cut the `SKILL.md:112` reference.

---

## C9 — MEDIUM. The pointer lands on a skipped step and the breadcrumb loses its position

`apply_to_change` protects `done` and nothing else, so it will mark the `current` step `skipped` and
leave `current_step:` naming it. The intake generator guards this explicitly ("`current` must never
land on a lightened step (schema: the pointer never points at skipped/starter)"), the schema states
it at `change-context.schema.yaml:263`, and `check_skips` does not test for it.

```
$ source ai/claude/hooks/_steps.sh
BEFORE apply:
  trail: ▶ Issue ·Figma ·Impact ·ROI …
  cur_n: '1'  total: 31
AFTER apply (issue, the current step, not kept):
  trail: ⊘Issue ⊘Figma ·Impact ⊘ROI …
  cur_n: ''  cur_label: ''  total: 31
  cs_name: 'Issue'
```

No `▶` anywhere in the trail. `hitl_current_n` and `hitl_current_label` return empty, so the status
line and the banner lose the pointer, while `current_step.name` keeps asserting a step that has been
declined. `/hitl:dev-switch-context` reads `current_step.number/name`
(`switch-context/SKILL.md:75`) and will resume the user onto a step marked skipped in their own name.

The phase ribbon renders `Requirements ✓ ... Post-Ship ✓` for all-skipped phases — that is deliberate
(CR-16, `_steps.sh:334`), not a new defect, and I am not reporting it.

**Smallest fix:** in `apply`, refuse to skip a step whose status is `current`, or advance
`current_step` to the first kept step and rewrite the block.

---

## C10 — MEDIUM. `--workflow` is a flag too, and a mismatch marks the wrong steps

```
$ CLAUDE_PLUGIN_ROOT=$PWD python3 gen.py docs GH-99 docs/z 2.9.0 2 ... > .hitl/current-change.yaml
$ python3 ci/first-pass/plan_select.py apply --workflows ci/first-pass/workflows.yaml \
    --paths "docs/a.md" --keep "issue,impact,verify_green,review1,verify_pr" --actor "p@t"
wrote 1 skip records to .hitl/current-change.yaml
EXIT=0
wf id: docs
statuses: {'issue':'current','scope':'open','draft':'open','doc_review':'open',
           'reconcile':'skipped','merge':'open'}
$ python3 ci/first-pass/check_skips.py ... ; EXIT=0
```

A `docs` change, sized against the `development` plan because that is the argparse default. One step
(`reconcile`, a key both catalogs happen to share) is declined; `scope`, `draft`, `doc_review` and
`merge` are silently untouched because they are absent from the plan used. The user is told "wrote 1
skip records" and believes the plan was right-sized. Same fix as C3.

---

## C11 — MEDIUM. A damaged change file is reported as absent, with advice that destroys it

`_load()` swallows every exception and returns `{}`, and `apply` reads `{}` as "no file".

```
$ printf '\nnotes: "unclosed\n' >> .hitl/current-change.yaml     # one bad hand-edit
$ python3 ci/first-pass/plan_select.py apply ... --keep "issue" --actor "p@t"
no change file at .hitl/current-change.yaml — intake creates it; run /hitl:dev-start-change first
EXIT=2
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[BLOCK] MALFORMED: cannot parse change file: ScannerError
EXIT=2
```

The validator gets it right; `apply` misdiagnoses and prescribes the one command that overwrites the
file (`start-change` Step 6: `mv .hitl/current-change.yaml.tmp .hitl/current-change.yaml`). Following
the tool's own instruction destroys the change_id, the branch anchor, every step already `done`, the
approvals and the source artifacts. `apply` itself leaves the file untouched (verified with `cmp`) —
the destruction is in the advice.

**Smallest fix:** distinguish "missing" from "unparseable" in `_load`, and say so.

---

## C12 — LOW/MECHANISM. Step 3a ships no runnable command

`selection.md`'s block needs `$WF_ID $TIER $PROFILE $TAGS $IMPACT_PATHS`, all of which were
established at intake. `apply-change/SKILL.md` defines none:

```
$ grep -n "WF_ID\|IMPACT_PATHS\|TIER\|PROFILE\|TAGS" ai/claude/apply-change/SKILL.md
(no output)
$ python3 "$SEL" render --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" --profile "$PROFILE" --tags "$TAGS" --paths "$IMPACT_PATHS"
plan_select.py: error: argument --tier: invalid int value: ''
EXIT=2
```

Fails loud, which is the safe direction — but the recovery an agent reaches for is inventing the
values, which is the delivery mechanism for C3 and C10. Step 3a also says "revisit the tier here" and
`plan_select` never writes `tier` back to the change file, so a revised tier has no writer at all.

---

## C13 — LOW. The write is not atomic, unlike the writer it replaced

`with open(a.change, "w") as f: yaml.safe_dump(doc, f, ...)` truncates the live change file in place.
The intake generator uses `> .tmp` + guarded `mv` for stated reasons: *"a generator that dies partway
through `> file` leaves a truncated change file behind, and a truncated change file reads as 'no
active change' to the gate."* The new writer discards that discipline on the same file.

**Not reproduced as a corruption** — I could not force `safe_dump` to raise on a `safe_load`-produced
document (I tried `!!binary`, complex keys and duplicate keys; `safe_load` rejects the hostile cases
before the dump). Reporting it as an unproven hazard and a regression in discipline, not as a defect.

`apply` also does not check `expected_branch` before rewriting.

---

## C14 — Claims in the CHANGELOG 2.9.0 entry that are now false

| Claim | Status |
|---|---|
| "an attributed entry in `skips[]`, **which is what the fail-closed validator reads**" | **False.** Nothing runs the validator after step 3a (C1). |
| "each unkept step ... given an **attributed** entry" | **False.** Attribution is unenforced in `apply` mode (C2). |
| "On the change that started this: **4 locked, 8 offered, 22 collapsed**" | **False.** The tool produces 5 / 8 / 21 (`render --workflow development --tier 2 --paths demo.sh`). |
| "**Six to eight are offered.** The tail is collapsed" | **False** whenever `sizable()` is false — all non-locked steps are offered and the tail is empty (C5). |
| "the plan is shown whole and **nothing is collapsed**" | **Half true.** True of `render`; `apply` skips everything not named in `--keep` (C5). |
| "A plan is lightened when a project has the data to lighten it, **never as a side effect of missing it**" | **False.** Reproduced twice: the docs workflow (no costs at all, C5) and a 17/34 catalog (C4). |
| "**`protects` and `forgo_cost` for all 38 steps**" | **Misleading.** 87 distinct catalog steps; 38 have costs; 53 do not. 4 of the 38 (`baseline`, `cve_audit`, `pentest`, `sec_design`) name no step in any workflow. |
| "It also **revisits the tier**" | **Unwired.** `plan_select` never writes `tier` back; a revised tier has no writer (C12). |
| "Both the probe and that refusal are **removed** rather than patched" | **False.** The probe survives in `right-sizing.md`, which the round-2 diff did not touch (C8). |
| "**Nothing that validated before this release fails now**" | **Holds.** Verified: no step added/removed and no `crit`/`crit_by_tier`/`no_omit` changed in any workflow between `v2.8.0` and HEAD; the diff to `ai/shared/workflows.yaml` is 209 pure insertions of `step_costs`/`step_requires`. |
| "a project that has not refreshed its copy gets the plan in **catalog order**" | **Minor.** Locked steps are hoisted to the front, so it is catalog order among the non-locked only. |

---

## C15 — LOW. The rewrite destroys comments and inflates the file 6x

No field is lost and no value changes type (verified by key-set and value comparison across a change
file carrying `source_artifacts`, `manifest`, `allowed_paths`, `approvals`). But `safe_dump` reflows
flow style to block style and drops every comment:

```
comments surviving: 0        (1 human comment before)
lines before/after: 61 360
```

The change file is the human-readable trail. It becomes 6x longer and loses every annotation a person
wrote into it.

---

## Areas I checked and found sound — no findings

- **Field, value and type preservation across the rewrite.** No key lost, no scalar retyped; PyYAML
  quotes version-like and bool-like strings correctly.
- **Non-ASCII handling.** No `protects` string in the catalog is non-ASCII, so `allow_unicode`
  being unset causes no escaping. Verified.
- **`_steps.sh` reparsing the block-style file.** The awk parser handles both styles; the breadcrumb
  renders correctly after the rewrite (the pointer loss in C9 is caused by the skipped status, not
  by the reformat).
- **`resurface.py`.** `apply` omits `resolved: false`, which the intake generator wrote; `resurface`
  does `e.setdefault("resolved", False)` on append and `e.get("resolved")` on read, so a missing
  field is correctly unresolved. No finding.
- **The `--keep` unknown-step guard.** Refuses rather than silently declining. Correct, and it caught
  a real mistake during this review.
- **Catalog compatibility with existing change files** (see C14, last two rows).
- **The double-apply idempotence for an *identical* keep list.** No duplicate records.

---

## On the guard that shipped with this fix

`ci/wiring/test_wiring.py::test_the_selection_writes_the_change_file_not_a_hand_off` asserts that
`selection.md` contains the string `python3 "$SEL" apply`, that `plan_select.py` contains
`def apply_to_change(`, and that its body contains two substrings. It never runs `apply`, never feeds
the output to `check_skips.py`, and never checks that an actor is required. `81 passed in 3.19s` over
every finding above.

That is the same guard shape the release notes indict: *"Guards asserted their names appeared in a
file, which is why the suite stayed green over all three."* The fix for the wiring-defect class was
verified by a wiring-defect-class guard.

---

## Verdict

**DO NOT SHIP.**

There is no single smallest change. The writer must gain the four guards the intake writer already
had, and the reader must be reconnected. The minimum set:

1. Move the `--actor` guard above the mode dispatch (C2), and let a re-run update an entry.
2. Read `tier` and `workflow.id` from the change file; refuse a disagreeing flag (C3, C10).
3. Refuse an empty `kept`, refuse to skip the `current` step, and refuse a record with an empty
   `protects` (C4, C5, C9).
4. Run `check_skips.py` at the end of Step 3a and stop on exit 2 (C1).
5. Make `sizable()` require full coverage, not half (C4).
6. Delete the probe and the tier-0/1 proposal from `right-sizing.md` (C8).

C7 (First Pass never engaging, and 7 of 8 routes having no writer) is a scope question, not a patch:
either `apply` declares `first_pass: true` and the other routes get a Step 3a, or the release should
say plainly that right-sizing is development-route-only in 2.9.0.

Round 3 is not a clean round. C1, C2, C3, C4, C6, C7 and C8 are new — they are properties of the
round-2 fix, not survivals from round 2.
