# Bypass lens — HITL 2.9.0, round 3

**State reviewed:** `c6adfc43d90de3d5788c70b3b8e51a5343f6445f` on `main`.
**Method:** onboarded product repo reconstructed in a scratch dir (`ci/first-pass/*` + `ai/shared/workflows.yaml`
copied to `ci/first-pass/workflows.yaml`), change file produced by running the Step 6 generator extracted
verbatim from `ai/claude/start-change/SKILL.md`. Guard mutations run against a clone at `c6adfc4`.
Every finding below was reproduced; commands and output are inline.

## VERDICT: DO NOT SHIP

The round-2 sequencing fix moved the selection to a moment where it can genuinely see the change. It also
moved it past every writer, guard and certifier that used to stand around it. `plan_select.py apply` is now
the only thing in the release that writes a skip record, and it is a partial replacement for the Step 6
generator: it writes the ledger and none of the state the ledger's consumers read. Separately, the intake
diff probe that this release deleted from two files is still shipped in a third — and the wiring suite
asserts it is present.

---

## Summary

| # | Sev | Finding |
|---|---|---|
| B1 | HIGH | `apply` leaves `current_step` pointing at a step it marked `skipped`, and no step `current`. Step 6 refuses to emit this file; the validator certifies it clean. |
| B2 | HIGH | The selection is write-once. Re-running with a wider `--keep` does not restore a step — it stays `skipped`, carrying a record that is now false. Tool reports success. |
| B3 | HIGH | `first_pass: true` is unreachable in 2.9.0. Nothing writes `.hitl/first-pass-choices.json` any more, so the only emitter never fires, and `apply` never sets the flag. The permission hook and brief mode are dead for every change. |
| B4 | HIGH | `right-sizing.md` still ships the intake `git diff` probe deleted elsewhere this release, and `test_intake_proposes_a_tier_from_the_shape` asserts it is present. It returns zero lines at intake, and the only reachable row of its table proposes tier 0/1 + a pre-selected batch decline. |
| B5 | MED | `choices` refuses an empty `--actor`; `apply` — the only writer left — accepts none and exits 0. The verbatim command in `selection.md` passes the literal placeholder `<the person, not you>`, which certifies clean. |
| B6 | MED | `apply` writes into any change file: no `expected_branch` check, no `status` check. 28 records written into a `status: merged` change on a foreign branch. |
| B7 | MED | `apply` only ever writes `decline`. No `starter`, no `defer`, so no honest-minimal artifact and no fast-follow is seeded for 21–29 steps. `DEFER_NO_FOLLOWUP` can never fire. |
| B8 | MED | Local certification (Step 6b) now runs strictly *before* the only writer of skips. Its stated purpose — "so nothing uncertified is ever pushed" — is false. |
| G1 | HIGH | `test_the_selection_writes_the_change_file_not_a_hand_off` passes with **both** halves of the pairing commented out. |
| G2 | HIGH | A mutation that breaks the pairing on the shape intake actually produces keeps **all 81** tests green. `test_rank`'s fixture hand-writes a change file the generator never emits. |
| G3 | MED | The same guard scans only `start-change/*.md`. The selection now lives in `apply-change/SKILL.md`, unscanned. |
| G4 | MED | Same guard: a redirect through a shell variable dodges its literal-path regex. |
| G5 | MED | `test_the_tier_0_1_attribution_rule_survives` matches the `if` line and nothing about its body. `sys.exit(...)` → `pass` keeps it green. |
| G6 | MED | `^[^#\n]*python3 "\$SEL" apply` is fence-blind. ` ```bash ` → ` ```text ` keeps all 56 wiring tests green with no runnable invocation shipped. |
| S1–S4 | LOW | Four files now contradict themselves or state something false about this release. |

Sound, and I could not break them: `sizable()`, and the `--keep` unknown-name refusal. Details at the end.

---

## Priority 1 — a step out of the plan with no usable record

**I could not do it with `apply` alone.** `apply` never deletes a step, and `check_skips` covers the
delete case (`INCOMPLETE_PLAN` / `PLAN_PRUNED`), the unattributed case (`FP_UNDECLARED`), and the
marked-but-unrecorded case (`SILENT_SKIP`). Three attempts — plan/change workflow mismatch, `--tier` lower
than the change file's tier, duplicate-key laundering through `safe_load`/`safe_dump` — all failed closed.
That part of the design holds.

What I got instead is a step that is *still on the plan and still recorded* while the file around it is
incoherent, which the validator has no rule for.

### B1 (HIGH) — `current_step` points at a step `apply` marked `skipped`

The Step 6 generator treats this as a schema invariant and refuses rather than emit it
(`ai/claude/start-change/SKILL.md:325-330`):

```
# `current` must never land on a lightened step (schema: the pointer never points at skipped/starter).
first = next((s for s in steps if s["key"] not in choices), None)
if first is None:
    sys.exit("every step in the plan was lightened — there is no change left to run. Keep at least one.")
```

`apply_to_change` has neither guard. `plan_select.py:123` skips only steps whose status is `done`;
`current` is fair game.

```
$ python3 ci/first-pass/plan_select.py apply --workflows ci/first-pass/workflows.yaml \
    --workflow development --tier 2 --paths src/app.py --keep "" --actor "alice@team"
wrote 29 skip records to .hitl/current-change.yaml
tool exit=0

$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[warn] FP_ABSENT_ENFORCED: first_pass is absent, but this change carries attributed skips — enforcing the full ruleset on them.
validator exit=0

current_step -> {'number': 1, 'name': 'Issue', 'phase': 'Requirements'}
status of issue: ['skipped']
any status==current? []
open steps: ['red', 'green', 'integration_verify', 'deploy', 'promote']
```

`current_step` is what `switch-context/SKILL.md:75,126` reads to resume a change and what the status-line
trail renders. It now names a step nobody will run, and no step carries `current`. `check_skips` has no rule
relating `current_step` to `workflow.steps`, so exit 0.

### B2 (HIGH) — the selection is write-once; a re-tick does not restore the step

`selection.md` collects the decision with `AskUserQuestion` and explicitly invites conversational
correction (*"also drop docs" is a normal reply*). The correction only works in one direction.

```
$ ... apply --keep "issue" --actor alice
wrote 28 skip records to .hitl/current-change.yaml
$ ... apply --keep "issue,review1,qa_verify,conventions" --actor alice     # the person re-ticks three
wrote 28 skip records to .hitl/current-change.yaml
review1 -> skipped
qa_verify -> skipped
conventions -> skipped
skips count 28
['conventions', 'review1', 'qa_verify']
[warn] FP_ABSENT_ENFORCED: ...
validator exit=0
```

Nothing in `apply_to_change` clears a `skipped` status or removes a record. The three steps stay off the
plan, each carrying a record that reads *"not selected at right-sizing (rank high): A second person has
actually read the diff."* — which is now untrue: the person selected it. The tool prints a success line both
times, and the fail-closed validator certifies the result clean. This is the worst shape a record can take:
present, attributed, and wrong.

---

## Priority 2 — breaking the pairing

### B3 (HIGH) — `first_pass: true` is unreachable in 2.9.0

`apply` writes the ledger. It does not write the flag that turns the ledger on.

Only one line in the whole tree emits it — `ai/claude/start-change/SKILL.md:342` — and only when `choices`
is non-empty, which requires `.hitl/first-pass-choices.json`. The round-2 fix deleted the redirect that
wrote that file from `selection.md`. Nothing replaced it:

```
$ grep -rn "first-pass-choices.json" ai/ ci/ tools/ | grep -Ev "reviews|CHOICES=|rm -f"
ai/claude/start-from-prd/SKILL.md:117:   ... .gitignore ...
ai/claude/start-brownfield/SKILL.md:101:  ... .gitignore ...
ai/claude/start-migration/SKILL.md:72:   ... .gitignore ...
ai/claude/start-change/first-pass-choices.md:9:  (prose)
ai/claude/start-change/selection.md:92:        (prose)
ci/wiring/test_wiring.py:771 / ci/first-pass/test_rank.py:270 / plan_select.py:11  (docstrings)
```

Three `.gitignore` lines, two prose mentions, three docstrings. No writer. And `choices` mode does not write
it either — it prints to stdout:

```
$ python3 ci/first-pass/plan_select.py choices ... --keep issue --actor alice >/dev/null
choices-file created? ls: .hitl/first-pass-choices.json: No such file or directory
```

Consequences, all reproduced above: every change file in 2.9.0 has `first_pass` absent.

- `ai/claude/hooks/first-pass-permissions.sh:66` — `if change.get("first_pass") is not True: exit 0`. The
  reduced-friction permission policy never engages, on any change.
- `ai/shared/first-pass/brief.md:3` — brief mode is gated on `first_pass: true`. Never engages.
- `check_skips.py:224-227` — every lightened change now certifies through the `FP_ABSENT_ENFORCED`
  fall-through, whose own comment says it is "reached only via the attributed-skip fall-through … the flag
  is legitimately absent". The anomaly branch is now the normal one, and its warning fires on every change,
  which is how a warning stops being read.
- Intake Step 4b (`start-change/SKILL.md:157-186`) is dead: it collects dispositions into a file nothing
  writes, following a doc that points at a command that no longer exists.

This is not a bypass of the ledger; it is the release shipping with its own runtime switched off.

### B5 (MED) — `--actor` is enforced on the mode nobody runs and unenforced on the only one that writes

`plan_select.py:189-204`: the `apply` branch returns at line 200; the actor check is at line 202.

```
$ ... apply --keep "issue"                       # no --actor at all
wrote 28 skip records to .hitl/current-change.yaml
exit=0
[BLOCK] FP_UNDECLARED: ... 28 unattributed entries in skips[] ...

$ ... choices --keep "issue"                     # same, on the other mode
--actor is required: a skip is accountable to a person, not the agent
exit=2
```

The validator catches it, so the ledger holds — but the writer reports success on a file it just made
un-mergeable, and the check lives on the mode that no longer has a caller.

The softer version certifies clean. `selection.md:83-86` ships this command verbatim:

```
--keep "issue,review1,verify_pr" --actor "<the person, not you>"
```

Run as written, `_actor_of()` accepts the placeholder and the change certifies clean with 26 skips
attributed to `<the person, not you>`. Reproduced.

### B6 (MED) — `apply` writes into any change file

No `expected_branch` check (every other surface matches it exactly —
`ai/claude/hooks/check-hitl-context.sh:141`), no `status` check (`apply-change/SKILL.md:170` calls `merged`
"an enum whose value deactivates the change").

```
current branch: totally/other
$ ... apply --keep "issue" --actor alice
wrote 28 skip records to .hitl/current-change.yaml
tool exit=0
status: merged expected_branch: issue/9-something-else skips: 28
```

### B7 (MED) — one disposition out of three

`apply_to_change` hardcodes `"disposition": "decline"`. `starter` and `defer` are unreachable through it.
For a tier-2 `development` change that is 21 steps at the default selection and up to 29 with nothing
ticked, none of which gets an honest-minimal artifact (CR-2) or a linked fast-follow (CR-7). `starters.py`
has registered starters for several of them; `DEFER_NO_FOLLOWUP` can never fire, because nothing is ever
deferred. The Step 6 generator supported the full vocabulary — and per B3 it can no longer be reached.

### B8 (MED) — the certifier now runs before the writer

Step 6b's stated contract: *"Run it **before** the Step 7 commit, so nothing uncertified is ever pushed."*
It runs at intake, on a change file with zero skips. Step 3a then writes 26–29. `apply-change/SKILL.md`
contains no `check_skips` invocation at all (`grep -n "check_skips" ai/claude/apply-change/SKILL.md` → no
match); Step 7a re-runs `resurface --append` only. The first thing that certifies a lightened 2.9.0 change
is the PR gate, and only in a repo that onboarded `ci/workflows/first-pass-check.yml`.

---

## Priority 3 — `sizable()`

**Sound. I could not break it.** On the shipped catalog every non-`development` workflow returns `False`,
so none of them collapses, and `development` returns `True`:

```
development        steps=34 costed=34 thresh=17 sizable=True
brownfield         steps=11 costed= 1 thresh= 5 sizable=False
migration          steps= 9 costed= 0 thresh= 4 sizable=False
migration_review   steps= 5 costed= 0 thresh= 2 sizable=False
docs               steps= 6 costed= 2 thresh= 3 sizable=False
prd                steps= 5 costed= 0 thresh= 2 sizable=False
platform           steps=17 costed= 0 thresh= 8 sizable=False
release            steps=12 costed= 0 thresh= 6 sizable=False
```

I tried to force a collapse via cross-workflow key overlap (`step_costs` is a single global block, not
per-workflow, so a workflow sharing half of `development`'s keys would collapse on data that was never
about it). No shipped workflow gets close. The CHANGELOG's arithmetic also checks out: at tier 1 the
development spine is 4 locked / 8 offered / 22 collapsed, as claimed.

---

## Priority 4 — the guards

All mutations run against a clone at `c6adfc4`. Baseline: `81 passed`.

### G1 (HIGH) — the new pairing guard passes with the pairing deleted

`test_the_selection_writes_the_change_file_not_a_hand_off` asserts the pairing with two bare substring
checks (`test_wiring.py:791-794`):

```python
assert 'st["status"] = "skipped"' in body and 'doc.setdefault("skips"' in body
```

Mutation — delete both, leave the literals as comments:

```python
            # st["status"] = "skipped"   <- the guard greps for this literal
            st["status"] = "open"        # the step stays on the plan, unmarked
            ...
    # doc.setdefault("skips", []).extend(added)   <- and this one
    pass
```

```
$ python3 -m pytest -q ci/wiring/test_wiring.py::test_the_selection_writes_the_change_file_not_a_hand_off
1 passed
$ python3 -m pytest -q ci/wiring/test_wiring.py
56 passed
```

`apply` now writes nothing at all — no status, no record — and the guard whose docstring is *"apply must
BOTH mark the step skipped and append the ledger entry"* is green. Twenty lines above, in the same test
function, the author anchors with `^[^#\n]*` and explains why: *"Commenting out the call leaves the string
in the file."* The lesson was applied to the doc assertion and not to the code assertion beside it.

`test_rank` catches this particular mutation (`assert doc["skips"], "nothing was recorded"`). So it is a
guard-quality finding, not a shippable bypass — until G2.

### G2 (HIGH) — a mutation that keeps all 81 green while breaking the pairing on the real artifact

`test_rank`'s fixture hand-writes its change file with **every step `status: "open"` and `skips: []`**
(`test_rank.py:275-284`). The Step 6 generator never emits that: it always marks one step `current`, and
the `existing` de-dupe path is never exercised. So make the record conditional on the prior status:

```python
        if k in unkept and str(st.get("status")) not in ("done",):
            was = str(st.get("status"))
            st["status"] = "skipped"
            if k not in existing and was == "open":
```

```
$ python3 -m pytest -q ci/wiring/test_wiring.py ci/first-pass/test_rank.py
81 passed in 3.42s
```

Both suites green. On a real generated change file the mutant produces a silent skip of exactly the step
intake was pointing at:

```
$ ... apply --keep "review1" --actor alice
marked skipped but unrecorded: ['issue']
[BLOCK] FP_UNDECLARED: ... step(s) 'issue' lightened ...
[BLOCK] SILENT_SKIP: step 'issue' is skipped but has no skip record
validator exit=2
```

The runtime validator holds. The unit guards do not see it, because the fixture is not the artifact. Note
that this is the same blind spot B1 exploits from the other side: the `current` status is the one shape
`apply` meets on every real change and the one shape its test never constructs.

### G3 (MED) — the hand-off guard scans the wrong directory

`for f in sorted(x for x in os.listdir(d) ...)` where `d = ai/claude/start-change`. The selection moved to
`apply-change/SKILL.md`. Appending the full redirect there:

```bash
python3 "$SEL" choices ... > .hitl/first-pass-choices.json
```

```
$ python3 -m pytest -q ci/wiring/test_wiring.py::test_the_selection_writes_the_change_file_not_a_hand_off
1 passed
$ python3 -m pytest -q ci/wiring/test_wiring.py
56 passed
```

The dead hand-off is restored in the file the guard exists to protect, and the guard never looks there.

### G4 (MED) — same guard, redirect through a variable

`(>|cat >|tee)\s*\.hitl/first-pass-choices\.json` requires the literal path. In `first-pass-choices.md`:

```bash
CHOICES=".hitl/first-pass-choices.json"
python3 "$SEL" choices --keep "$KEEP" --actor "$WHO" > "$CHOICES"
```

Green (56 passed, run together with G3).

### G5 (MED) — the tier rule guard matches the `if`, not the rule

`test_the_tier_0_1_attribution_rule_survives` asserts `re.search(r"if\s+tier\s*<=\s*1\s+and\s+not", body)`.

```python
if tier <= 1 and not (tier_set_by.strip() and tier_reason.strip()):
    pass   # rule removed; the `if` line is all the guard looks for
```

```
$ python3 -m pytest -q ci/wiring/test_wiring.py::test_the_tier_0_1_attribution_rule_survives
1 passed
```

The tier 0/1 attribution rule is dead and the guard that exists to notice is green. This test was
**rewritten in the round-2 fix**, and its own docstring names the anti-pattern it kept: *"it was dead code
… this guard stayed green — because it asserted a name appeared in a file."*

### G6 (MED) — the anchored invocation check is fence-blind

`^[^#\n]*python3 "\$SEL" apply` rejects a leading `#`. It does not know what fence it is inside. Change
` ```bash ` to ` ```text ` above the `apply` block in `selection.md`:

```
$ python3 -m pytest -q ci/wiring/test_wiring.py
56 passed
```

The skill now ships no runnable invocation of the only writer in the release, and the guard built after
three features shipped unreachable does not notice. A blockquote (`> python3 "$SEL" apply`) also matches.

---

## Priority 4b — B4: the probe this release deleted is still shipped, and a guard requires it

This is the one I would fix first, because it is reachable by a user doing nothing unusual.

The round-2 fix removed the shape probe from `plan_select.py` and `selection.md` and wrote the reason into
both: *"The probe read `git diff` at intake, where there is nothing to diff — intake runs before a line is
written."* `ai/claude/start-change/right-sizing.md` still ships it, in shell, under the heading **"The
probe"**:

```bash
BASE="${BASE:-main}"
git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null | sed -n '1,200p'
```

Step 3b routes to it (`start-change/SKILL.md:118-121`), and Step 3b runs **before Step 5 creates the
branch**. Reproduced on the repo state intake actually runs in:

```
$ git checkout -q main
$ git diff --name-only "$(git merge-base HEAD main)"..HEAD | sed -n '1,200p' | wc -l
       0
```

Zero lines, on every change, always. The table below it has no row for an empty answer. Its first row —
"the diff touches **non-source only**" — is vacuously the match a reader lands on, and it says: **propose
tier 0 or 1, reason pre-filled**. `right-sizing.md`'s closing section then says: *"At tier 0 or 1, offer
First Pass without being asked (Step 4b) and present the ceremony steps pre-selected as declined … One
confirmation clears all eleven."* Tier 0/1 is also where the floor set is smallest — `integration_verify`
comes off `floor` at 2→1.

And the wiring suite **requires** it:

```python
def test_intake_proposes_a_tier_from_the_shape():
    txt = _flat(ref)                                   # right-sizing.md
    assert re.search(r"(?i)git diff --name-only", txt), "the probe command is gone"
```

Two tests in the same file now enforce opposite conclusions: `test_the_tier_0_1_attribution_rule_survives`
asserts `"TRIVIAL_SHAPE" not in` the intake skill *"if sizing is being attempted there again, read
selection.md on why that moment knows nothing"* — while `test_intake_proposes_a_tier_from_the_shape` fails
the build if the intake diff probe is removed. The first guard checks one variable name in one file; the
probe survived under a different name in the file next door.

---

## Priority 5 — shared state across the skill boundary

Covered above and all reproduced: run twice → B2 (irreversible, false record, success message); stale
change file → B6 (`status: merged`, foreign branch, 28 records, exit 0); after the branch changed → B6.
One more: the certifier and the writer are now on opposite sides of the boundary (B8), and the flag that
declares the change to be running First Pass is written on the side that no longer has the data (B3).

---

## Priority 6 — files against themselves

- **S1** `selection.md:9-10` — *"Shown at intake once the ask is understood and the impact read is done,
  before the plan is fixed. Called from Step 4."* Three lines below, its own new section: *"After impact
  analysis, not before."* The call site is `apply-change` step 3a. The header block survived the rewrite.
- **S2** `start-change/SKILL.md:100-102` — *"Both departures from the tier you proposed are attributed: the
  generator refuses a tier 0/1 without `tier_set_by` and `tier_reason`, and refuses a tier 2+ without them
  when the shape probe said the change was trivial."* The second refusal was deleted in this release
  (`git diff 07bda66..HEAD`). The skill documents a rule its own embedded generator no longer has, and
  `test_the_tier_0_1_attribution_rule_survives` passes because the prose does not contain the literal
  `TRIVIAL_SHAPE`.
- **S3** `first-pass-choices.md:4,8-15` — three false statements in one paragraph: *"Called from
  start-change Step 4b"* (Step 4b now leads nowhere), *"`plan_select.py choices` writes
  `.hitl/first-pass-choices.json`, and it is the only thing that should"* (it prints to stdout and writes
  nothing — verified), *"The command is in `selection.md`, beside this file"* (`selection.md` no longer
  contains a `choices` invocation — verified).
- **S4** `plan_select.py:11` — the module docstring still describes `choices` as *"turn what they kept into
  `.hitl/first-pass-choices.json`"*, in the same docstring that opens by explaining that features shipped
  which nothing invoked.

---

## What I could not break

- `sizable()` — see Priority 3. No collapse forced where there is no basis; no collapse prevented where
  there is.
- `--keep` unknown-name refusal — `asked - known` is computed against locked+offered+tail, exits 2. Correct.
- `--tier` lower than the change file's tier — fails closed: `check_skips` re-resolves criticality from the
  change file's own tier and blocks with `FLOOR_NO_ACK`, so a step argued off the floor at selection time
  cannot certify.
- Duplicate-key laundering — `apply`'s `safe_load`/`safe_dump` round-trip does normalize a file that
  `_strict_load` would reject, but PyYAML's last-wins discards the forged block rather than promoting it,
  and the surviving block is then validated normally.
- Plan/change workflow mismatch (`--workflow development` against a `release` change file) — records land
  as `UNKNOWN_STEP` or resolve against the change's own catalog. Fails closed.

---

## Smallest change that fixes it

Two, because B4 is independent of the rest.

**1. Make `apply` the complete writer, and re-certify after it.** In `apply_to_change`:
set `doc["first_pass"] = True`; refuse an empty `--actor` (move the check above the `apply` branch, and
reject the `<...>` placeholder shape); refuse when `doc["expected_branch"]` does not match the current
branch or `doc["status"]` is `merged`; on a re-run, restore steps that are now kept (clear `skipped`, drop
their record) instead of accumulating; repoint `current_step` at the first non-lightened step, or refuse
as Step 6 does. Then add the `check_skips` invocation to `apply-change` step 3a, immediately after the
`apply` call. That closes B1, B2, B3, B5, B6, B8, and makes G2's mutation visible.

**2. Delete "The probe" from `right-sizing.md`** — keep the table, source it from the impact analysis or
from the issue text — and flip `test_intake_proposes_a_tier_from_the_shape` to assert the diff probe is
*absent*, matching the sibling guard. Closes B4.

Then, separately, the guards: replace the two substring asserts in
`test_the_selection_writes_the_change_file_not_a_hand_off` with a behavioural check (call
`apply_to_change` on a fixture whose steps include a `current` one and a pre-existing `skips[]` entry, and
assert `skipped == recorded`); widen its directory scan to `apply-change/` and its regex past a variable
redirect; and give `test_the_tier_0_1_attribution_rule_survives` something to assert about the body of the
rule rather than its `if`. B7 (`starter`/`defer` unreachable) and S1–S4 are follow-ups, not blockers.
