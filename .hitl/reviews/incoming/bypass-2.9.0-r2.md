# Bypass review — 2.9.0 release candidate, round 2

**State:** `07bda6643737ad2a339bfd21213d36d81b12eda1` on `main`
**Diffs read:** `git diff 9ba9fd2..HEAD` (the round-1 fixes), `git diff v2.8.0..HEAD` (the release)
**Lens:** bypass — the round-1 fixes are assumed walkable. Refute, do not confirm.
**Method:** all work in `mktemp -d` scratch dirs and in `git archive HEAD | tar -x -C <scratch>` copies.
No tracked file was modified; nothing was written under `.hitl/` except this report.
**Baseline:** `python3 -m pytest ci/wiring ci/first-pass/test_rank.py -q` → `254 passed` in the working
tree, `250 passed, 4 skipped` in a clean `git archive` copy (4 tests skip when `.hitl/` is absent).

**Not re-reported, per the brief:** `step_costs` covering only `development`; the incident raise never
firing; `engages` gating artifact-creating steps; the three plugin-relative links.

---

## Verdict first

**DO NOT SHIP.**

Round 1 called the ranker unreachable, the tail unrecorded and the tier-2+ refusal dead. Two of those
three are now genuinely fixed: `plan_select.py` is a real caller, and the tail does reach the choices
file. The third is not fixed — the refusal is dead **three independent ways**, and one of them was
introduced by the fix. And the new caller ships with its defaults inverted: the view's default is
*keep*, the writer's default is *decline*, and nothing reconciles them. I drove 29 of 31 steps out of
a tier-2 `development` plan through the shipped tool, the shipped generator and the fail-closed
validator, and got `First Pass skip ledger: clean.`

Both new guards were beaten. One by a single-line shell comment — the third instance of that exact
defect class in this repo, added in the commit whose message says the guards were rewritten to
execute the path rather than grep for names.

| # | Finding | Severity |
|---|---|---|
| CRITICAL-1 | The tier-2+ refusal is still dead code, three separate ways | CRITICAL |
| CRITICAL-2 | The writer declines everything the reader was shown as ticked; 29/31 steps skipped, validator clean | CRITICAL |
| HIGH-1 | The new `TRIVIAL_SHAPE` guard is defeated by a comment; suite unchanged | HIGH |
| HIGH-2 | The documented Step-4 command exits 2 as written; the guard asserts the string, not the run | HIGH |
| MEDIUM-1 | `"no reason given"` is a valid ledger reason end to end | MEDIUM |
| MEDIUM-2 | The ranker/validator agreement guard cannot fail on the branch that can diverge | MEDIUM |
| MEDIUM-3 | `selection.md` documents a floor untick the shipped caller cannot produce | MEDIUM |
| LOW | `--actor claude` accepted; `--incidents` default path also wrong; `--tags` dropped from `choices` | LOW |

---

## Setup used by every reproduction below

```bash
# a repo laid out the way tools/scripts/init-project.sh lays one out
W=$(mktemp -d); cd "$W"
git init -q .; git config user.name t; git config user.email t@t
mkdir -p src scripts docs ci/first-pass .hitl
echo "x=1" > src/app.py; echo "echo hi" > scripts/demo.sh
# init-project.sh:171 writes the manifest HERE
printf 'domains:\n  - name: app\n    paths: ["src/"]\n  - name: api\n    paths: ["svc/"]\n' \
  > docs/system-manifest.yaml
git add -A; git commit -qm base; git checkout -q -b work
echo "# FIRECRAWL_API_KEY=" >> scripts/demo.sh        # the change this whole release exists for
git add -A; git commit -qm change
cp <platform>/ci/first-pass/*.py ci/first-pass/; rm -f ci/first-pass/test_*.py
cp <platform>/ai/shared/workflows.yaml ci/first-pass/workflows.yaml
```

---

## CRITICAL-1 — The tier-2+ refusal is still dead code. Three independent causes ship; any one is sufficient.

Round 1's HIGH-3 was "nothing sets `TRIVIAL_SHAPE`, so the refusal is dead, and every unrecognised
value fails open." The fix added one line to `selection.md`:

```
export TRIVIAL_SHAPE="$(python3 "$SEL" probe --base "${BASE:-main}")"
```

The refusal is still dead. Not marginally — it cannot fire on any HITL project, for three reasons
that are each on their own fatal.

### (a) The probe reads a manifest path HITL never creates, so it always answers `0`

`ci/first-pass/plan_select.py:129`:

```python
ap.add_argument("--manifest", default="docs/02-design/system-manifest.yaml")
```

`selection.md:31` calls `probe` with no `--manifest`, so that default is what runs. HITL's own
onboarding writes the manifest somewhere else:

```
$ grep -rho "docs/[0-9a-z/-]*system-manifest\.yaml" ai/ tools/ ci/ | sort | uniq -c | sort -rn
  91 docs/system-manifest.yaml
   7 docs/examples/compound-agentic/system-manifest.yaml
   2 docs/examples/greenfield/docs/system-manifest.yaml
   1 docs/02-design/system-manifest.yaml      <- plan_select.py's own default, and nothing else
```

`tools/scripts/init-project.sh:171`: `cp "$MANIFEST_TMPL" "$TARGET_DIR/docs/system-manifest.yaml"`.

`trivial_shape()` returns `False` when it cannot find any source paths — deliberately, "no manifest
means no basis to call anything non-source" (`plan_select.py:52`). A manifest it cannot find is a
manifest it does not have. So the probe answers `0` on every real project, for every change.

**Reproduced** (setup above):

```
$ python3 ci/first-pass/plan_select.py probe --base main
0
$ python3 ci/first-pass/plan_select.py probe --base main --manifest docs/system-manifest.yaml
1
```

A one-line change to `scripts/demo.sh` — the `FIRECRAWL_API_KEY` case the release is named after —
probes as **not trivial**.

The same wrong-path bug is in the sibling default: `--incidents docs/03-engineering/incident-registry.yaml`
against 20 references to `docs/04-operations/incident-registry.yaml`. (The incident raise itself is
on the known list; I note the path only because it is the same defect in the adjacent line, and it
also kills `multi_domain`, which is computed from the same unreadable manifest.)

**The new guard cannot see this, because its fixture encodes the wrong path.** `test_rank.py::_repo()`
writes the manifest to `docs/02-design/system-manifest.yaml` — matching the tool's default rather
than the product's convention. Move the fixture to where `init-project.sh` writes it and the new
"the probe runs and answers" test fails:

```
$ python3 -m pytest ci/first-pass/test_rank.py -q      # fixture manifest moved to docs/system-manifest.yaml
>       assert _sel(_repo(), "probe", "--base", "main").stdout.strip() == "1"
E       AssertionError: assert '0' == '1'
1 failed, 19 passed
```

### (b) The `export` is in a different shell from the reader

`selection.md` exports `TRIVIAL_SHAPE` in the Step 4 bash block. `SKILL.md:235` reads
`os.environ.get("TRIVIAL_SHAPE", "")` in the Step 6 bash block. These are two separate Bash tool
invocations, and the harness this plugin runs in states plainly: *"Working directory persists between
calls, but ... Shell state (env vars, functions) does not persist."*

**Reproduced in the actual harness**, two consecutive Bash tool calls:

```
call 1: export TRIVIAL_SHAPE=1; echo "call 1 set TRIVIAL_SHAPE=$TRIVIAL_SHAPE"
        -> call 1 set TRIVIAL_SHAPE=1
call 2: echo "call 2 sees TRIVIAL_SHAPE=[${TRIVIAL_SHAPE-<unset>}]"
        -> call 2 sees TRIVIAL_SHAPE=[<unset>]
```

**Reproduced end to end** with the Step 6 generator extracted verbatim from `SKILL.md`
(`WF=development`, `CHANGE_ID=GH-42`, a fake `CLAUDE_PLUGIN_ROOT` holding `shared/workflows.yaml`),
run in a shell that did not export the variable — i.e. the real case:

```
shell A: export TRIVIAL_SHAPE="$(python3 ci/first-pass/plan_select.py probe --base main)"
         -> shell A sees TRIVIAL_SHAPE=1
shell B: TRIVIAL_SHAPE=[<unset>]
         bash /tmp/step6.sh ; generator rc=0
         .hitl/current-change.yaml written: tier: 2, workflow development, total: 31
```

Control — the identical generator, same repo, with the variable present in its own shell:

```
no source under a manifest domain is touched, so tier 2 needs TIER_SET_BY and TIER_REASON. ...
Change file NOT written (generator exit 1).
```

The refusal works. The delivery channel does not. A one-line `demo.sh` change gets a 31-step tier-2
plan with nobody's name on the decision, which is the exact 3h31m outcome this release was written
to prevent.

### (c) An absent or unrecognised value still fails open

`SKILL.md:235`: `trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1","true","yes")`.
Unset → `""` → not trivial → no refusal. Round 1 flagged this; the fix did not touch it. It is the
reason (a) and (b) are silent rather than loud: every failure mode of the probe and every failure of
the channel resolves to "not trivial, carry on".

**Smallest fix:** delete the env-var channel. Have the Step 6 generator run the probe itself
(`plan_select.py probe`, resolved the same way it already resolves `check_skips`), fix the two
default paths, and treat a probe that fails to run as *trivial* — the direction that asks for a name
rather than the direction that skips the question.

---

## CRITICAL-2 — The view's default is keep, the writer's default is decline. 29 of 31 steps skipped, and the fail-closed validator certifies clean.

`render` prints the offered eight pre-ticked:

```
Selected — untick any                      what you'd lose
   [x] issue            high   There is a written record of what was asked for and why,
   [x] impact           high   You find the callers, data and scheduled jobs this touch
   [x] verify_green     high   The suite is green for real, not green because it never
   [x] review1          high   A second person has actually read the diff.
   [x] arch_review      high   The change still fits the architecture it landed in, and
   [x] qa_verify        high   Someone checks the change against the acceptance criteri
   [x] rollout          high   There is a plan for how this reaches production and how
   [x] verify_pr        high   CI is green on the exact commit being merged, not an ear
```

`choices` keeps **only** what `--keep` names (`plan_select.py:157`). There is no notion that the
offered set was shown as ticked. A step the person saw as `[x]` and did not untick is declined
unless the agent re-types its key.

**Reproduced — the person unticks nothing, the agent passes no keeps:**

```
$ python3 ci/first-pass/plan_select.py choices --workflows ci/first-pass/workflows.yaml \
    --workflow development --tier 2 --base main --keep "" --actor "priya"
rc=0 ; declined steps: 29
['adv_code','adv_design','arch_review','conventions','design_plus','docs','figma','figma_compare',
 'iac','impact','impact_brief','issue','packet','qa_verify','reconcile','refactor','rerun','review1',
 'review2','roi','roi_30','roi_90','rollout','test_plan','test_review','training','verify_green',
 'verify_pr','verify_red']

  issue -> {'disposition': 'decline', 'reason': 'unticked at intake: There is a written record of ...'}
  review1 -> {'disposition': 'decline', 'reason': 'unticked at intake: A second person has actually read the diff.'}
```

The recorded reason says **"unticked at intake"** for eight steps nobody unticked. The ledger does
not merely fail to record a decision, it records a decision that did not happen.

**Through the shipped generator and the fail-closed validator:**

```
$ cp choices.json .hitl/first-pass-choices.json
$ bash step6.sh          # extracted verbatim from SKILL.md, WF=development
generator rc=0
$ grep -c '^  - { step:' .hitl/current-change.yaml
29
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
First Pass skip ledger: clean.
validator rc=0
```

A tier-2 `development` change now runs `red`, `green`, `integration_verify`, `deploy`, `promote` and
nothing else. No issue record, no impact read, no review, no QA, no CI check on the merged commit —
and the certification is clean.

### The same hole, reached by a typo

`--keep` is never validated against the plan. Mistyped and invented keys are dropped in silence:

```
$ python3 ci/first-pass/plan_select.py choices ... \
    --keep "issue,review_1,qa-verify,architecture_review,totally_made_up" --actor "priya"
rc=0 ; stderr: (empty) ; declined: 28
  review1    -> decline | unticked at intake: A second person has actually read the di
  qa_verify  -> decline | unticked at intake: Someone checks the change against the ac
  arch_review-> decline | unticked at intake: The change still fits the architecture i
```

Three steps the operator meant to keep, plus one step that does not exist, and not one word on
stderr. The asymmetry is exactly backwards: the generator **does** refuse an unknown key in
`choices` (`SKILL.md:303`, "first-pass choices name steps not in the workflow"), so the pipeline
validates the names of steps being *dropped* and not the names of steps being *saved*.

**Smallest fix:** in `plan_select.main()`, exit 2 on any `--keep` token that is not a key in the
ranked plan; and make the offered set default to *kept* — take an explicit `--drop` for the offered
eight and let only the tail default to decline. That preserves the inversion the release wanted (the
tail is skipped-and-recorded) without silently discarding what the person was shown as on.

---

## HIGH-1 — The new `TRIVIAL_SHAPE` guard is defeated by one shell comment. The suite does not move.

Added in `07bda66`, `ci/wiring/test_wiring.py:542`:

```python
assert re.search(r"export TRIVIAL_SHAPE=", sel), (
    "nothing exports TRIVIAL_SHAPE, so the refusal that reads it can never fire")
```

Unanchored, and it does not reject a leading `#` — in the same commit, and eleven lines apart in the
same file, the sibling guard for the `plan_select` calls does both:
`r'(?m)^[^#\n]*python3 "\$SEL" %s'`, with a comment explaining that a commented-out call still
matches an unanchored regex.

**Mutation** (clean `git archive HEAD` copy), one line of `selection.md`:

```diff
-export TRIVIAL_SHAPE="$(python3 "$SEL" probe --base "${BASE:-main}")"
+python3 "$SEL" probe --base "${BASE:-main}"   # export TRIVIAL_SHAPE=<the probe answer>
```

```
$ python3 -m pytest ci/wiring ci/first-pass/test_rank.py -q
250 passed, 4 skipped in 21.28s          # identical to baseline
```

`TRIVIAL_SHAPE` is now set nowhere, the refusal is dead again, both guards are green, and the
`probe` guard still passes because the probe *is* still called — it just goes to stdout. This is the
third time in this repo a guard has been satisfied by a string inside a comment.

**Smallest fix:** `r'(?m)^[^#\n]*export TRIVIAL_SHAPE='`. (It is not a real fix for CRITICAL-1(b) —
that needs the channel removed — but it stops this guard lying.)

---

## HIGH-2 — The documented Step-4 command exits 2 as written. The new guard asserts the string, not the run.

`selection.md:34`:

```bash
python3 "$SEL" render --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
        --profile "$PROFILE" --tags "$TAGS" --base "${BASE:-main}"
```

`WF_ID`, `PROFILE` and `TAGS` are assigned **nowhere in the plugin**. `TIER` is assigned once, at
`SKILL.md:214` — in Step 6, two steps later, in a different shell.

```
$ grep -rn 'TIER=\|WF_ID=\|PROFILE=\|TAGS=' ai/claude/start-change/*.md
ai/claude/start-change/SKILL.md:214:TIER=2                       # from Step 3b — never assume it
```

**Reproduced**, the block run verbatim in a fresh shell (setup above):

```
$ SEL=ci/first-pass/plan_select.py; WF=ci/first-pass/workflows.yaml
$ python3 "$SEL" render --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
          --profile "$PROFILE" --tags "$TAGS" --base "${BASE:-main}"
plan_select.py: error: argument --tier: invalid int value: ''
rc=2
```

The selection never renders. The new guard —
`assert re.search(r'(?m)^[^#\n]*python3 "\$SEL" render', seltext)` — passes on this, because the
call is present on a non-comment line. It checks that a command was written down, not that the
command runs. That is a narrower version of the same defect class the guard was added to close: the
round-1 report's own summary of the fix was "guards were rewritten to EXECUTE the path rather than
grep for names", and this one still greps.

`test_rank.py` does execute `plan_select.py`, but with hand-supplied arguments
(`"--tier","1","--profile","fix"`), so it exercises the tool and never the documented invocation.

**Smallest fix:** give the block defaults — `WF_ID="${WF_ID:-development}"`, `TIER="${TIER:-2}"`,
`PROFILE="${PROFILE:-}"`, `TAGS="${TAGS:-}"` — and have the wiring guard extract the bash block from
`selection.md` and run it against a fixture repo, asserting exit 0. Anything less keeps a
copy-pasteable command in a shipped skill that cannot execute.

---

## MEDIUM-1 — `"no reason given"` is a valid ledger reason, end to end

`plan_select.choices()` composes the reason from the step's `protects` sentence, falling back to the
string `"no reason given"` (lines 101 and 106). For any workflow whose steps have no `step_costs`
entry, that fallback is what gets written.

**Reproduced**, `brownfield`, one step kept:

```
$ python3 ci/first-pass/plan_select.py choices --workflows ci/first-pass/workflows.yaml \
    --workflow brownfield --tier 2 --base main --keep "map_code" --actor "priya" \
    > .hitl/first-pass-choices.json
$ bash step6.sh          # WF=brownfield
generator rc=0
$ grep -c 'no reason given' .hitl/current-change.yaml
9
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
First Pass skip ledger: clean.
validator rc=0
```

Nine of eleven brownfield steps — including `manifest`, `seed_registries`, `verify_pipeline` — are
skipped with the recorded justification `unticked at intake: no reason given`. Three checks look at
that string and all three pass it:

- the generator's `if not str(ch.get("reason") or "").strip()` (`SKILL.md:301`),
- `check_skips`' `SILENT_SKIP: reason is empty` (`check_skips.py:331`),
- the new guard's `assert len(e["reason"]) > 20` (`test_rank.py:200`) — the fallback is 35 chars.

CR-3's "a skip cannot be silent" is now satisfied by the words "no reason given". I am reporting the
*consequence*, not the `step_costs` coverage gap on the known list: the round-1 fix converted an
absent rank into a valid, certified ledger entry that asserts nothing.

**Smallest fix:** when `protects` is empty, `plan_select` should refuse to compose a reason — exit 2
naming the steps that need one — rather than write a placeholder. And change the guard's assertion
from a length to `"no reason given" not in e["reason"]`.

---

## MEDIUM-2 — The guard that closed round-1's ranker/validator divergence cannot fail on the branch that can diverge

`test_the_ranker_and_the_validator_agree_on_the_floor_at_every_tier` compares
`R.rank_plan(...)` against `CS.resolve_crit(...)`. When the import at `rank.py:34` succeeds — which
it does everywhere the files are installed together — `effective_crit` *is* `CS.resolve_crit`, so
the assertion compares a function with itself on the primary path and never touches the fallback.

**Mutation** — make the fallback unlock the entire floor:

```diff
     if _resolve_crit is not None:
         return _resolve_crit(step, tier)
+    return "ceremony"   # MUTATION: the fallback now unlocks every floor step
     base = (step or {}).get("crit", "standard")
```

```
$ python3 -m pytest ci/wiring ci/first-pass/test_rank.py -q
250 passed, 4 skipped in 22.48s          # identical to baseline
```

I could not turn this into an exploit and I looked. The fallback is close to unreachable:
`init-project.sh:107` copies every non-test `.py` from `ci/first-pass/` in one `find`, so
`check_skips.py` is always beside `rank.py`. And on the shipped catalog the two resolvers agree
everywhere:

```
divergences between validator resolve_crit and rank.py fallback: 0
   (all 8 workflows x every step x tiers 0..4)
```

The one asymmetry I found is a crash, not a bypass — `crit: [floor]` with a `crit_by_tier` dict:
validator returns `floor`, the fallback raises `TypeError: unhashable type: 'list'` out of
`rank_plan`. Fails closed.

So: MEDIUM for guard quality, not for exploitability. The guard's docstring claims it closes the
round-1 divergence; it closes a reimplementation of the primary path and is blind to the branch the
comment says exists for repos without the validator.

**Smallest fix:** parametrise the test over `_resolve_crit = None` as well, or delete the fallback
and let the import failure be loud — a ranker that silently ranks with a second opinion of
criticality is the thing the fix was supposed to remove.

---

## MEDIUM-3 — `selection.md` documents a floor untick the shipped caller cannot produce

`selection.md:94`: *"**The floor can be unticked.** ... name the specific loss, take a name against
it, and a linked waiver where the step maps to a hard gate. That is the skip ledger's existing
machinery, reachable from here for the first time."*

It is not reachable from here. `plan_select.main():157` force-adds every locked step to `kept`, and
`choices()` only emits entries for steps **not** kept. A floor step can therefore never receive a
ledger entry from this tool, with or without a name and a waiver — confirmed in the CRITICAL-2 run,
where `deploy`, `promote` and `integration_verify` are absent from a 29-entry decline list produced
by `--keep ""`.

That is safe in itself. The problem is the workaround it forces: the documented way to untick the
floor is now to hand-author `.hitl/first-pass-choices.json` (which `first-pass-choices.md` shows how
to do), which bypasses the ranker's lock entirely and puts the whole floor decision back in prose —
the failure mode this release is named for.

**The floor does hold at the validator.** I tested the loosest route I could construct: run
`choices` at `--tier 2` (where `impact`, `packet`, `arch_review`, `qa_verify`, `rollout` are not
floor and are therefore offered) and the generator at `TIER=3` (where they are). Nothing binds the
two tiers — they are separate arguments in separate shells.

```
generator rc=0     # writes the change file with five floor declines, no ack, exit 0
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
[BLOCK] FLOOR_NO_ACK: floor step 'impact' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_ACK: floor step 'arch_review' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_WAIVER: floor step 'arch_review' maps to a hard gate but has no waiver_ref
[BLOCK] FLOOR_NO_ACK: floor step 'qa_verify' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_WAIVER: floor step 'qa_verify' maps to a hard gate but has no waiver_ref
[BLOCK] FLOOR_NO_ACK: floor step 'rollout' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_ACK: floor step 'packet' skipped with no ack_by (accountable role)
validator rc=2
```

**Answering priority 5 directly: I could not untick a floor step with neither a name nor a waiver.**
Every route I tried was blocked, non-waivably, by `check_skips`. Round 1's MEDIUM-2 (a `waiver_ref`
that does not point at anything) still stands and is unchanged.

**Smallest fix:** either implement the floor path in `plan_select` (`--risk-accept key=ack_by:waiver_ref`,
refusing without both) or delete the paragraph. A documented capability with no implementation is
what produced this release's other findings.

---

## LOW

**`--actor` accepts the agent.** `plan_select.py:160` prints *"a skip is accountable to a person, not
the agent"* and then accepts any non-blank string; `check_skips._actor_of` only tests truthiness.
`--actor claude` writes 29 skips attributed to the agent and certifies clean. Nothing in the release
makes this worse; it is now reachable in one command.

**`--incidents` default is wrong too.** `docs/03-engineering/incident-registry.yaml` (1 reference,
its own) vs `docs/04-operations/incident-registry.yaml` (20). Fix it in the same line as the
manifest default. The incident raise itself is on the known list.

**`--tags` is passed to `render` and not to `choices`** (`selection.md:34` vs `:78`), so the two
halves can rank the same plan differently and a step shown in the offered eight can be written out
as "below the cut line". Inert today — only `baseline` and `refactor` engage on tags and both are
already `low`, and `risky_domain` is always False because the manifest is unreadable (CRITICAL-1a).
It becomes live the moment a tag is attached to a non-`low` step.

**Three catalog resolvers, two orders.** `plan_select` defaults to `ci/first-pass/workflows.yaml`;
the Step 6 generator tries `$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml` **first**;
`check_skips._default_workflows()` tries `ci/first-pass/workflows.yaml` first. On a repo whose
`ci/first-pass/` copy is stale relative to the installed plugin, the selection ranks against one
catalog and the plan is generated from another. `dev-update` converges them, so this needs a user
who has not run it. Noted, not counted.

---

## Areas that are sound

Said plainly, and I tried to break each one.

- **No step escapes both lists.** `build()` returns `locked + rest[:8] + rest[8:]` over the full
  ranked plan; every non-kept step in either list gets an entry. I could not construct a step that
  appears in neither.
- **The tail genuinely reaches the choices file.** Round 1's CRITICAL-2 is fixed. `roi`, `training`,
  `figma` — collapsed and invisible in the render — all appear in the JSON with dispositions.
- **`--keep ""` on a workflow with no locked steps is refused**, not certified: *"every step in the
  plan was lightened — there is no change left to run"*, generator exit 1, no file written.
  Verified on `brownfield`.
- **The generator refuses unknown step keys** in the choices file, and refuses `starter` for steps
  with no registered starter.
- **`ci/retired-tests.sha256` now matches the shipped `test_rank.py`** (`e7f86c39…`). Round 1's
  MEDIUM-3 is fixed; I re-hashed it.
- **The floor holds at the validator** under every route I tried, including a deliberate
  tier mismatch between the selection and the generator.
- **`check_skips.py` itself** remains the strongest thing in this repo. I spent time on
  `resolve_crit`, `_tier_key`, the duplicate-key loader and the `first_pass` fall-through and found
  nothing new; the fallback in `rank.py` is stricter than or equal to it on every shape I could
  construct except the crash noted above.

---

## Smallest change that fixes it

1. `plan_select.py:129-130` — `--manifest docs/system-manifest.yaml`,
   `--incidents docs/04-operations/incident-registry.yaml`. Two strings. (CRITICAL-1a)
2. `SKILL.md` Step 6 — delete the `TRIVIAL_SHAPE` env read; run
   `plan_select.py probe` from inside the generator, resolving the tool the same way it already
   resolves `check_skips`, and treat any failure to run it as trivial. (CRITICAL-1b, 1c)
3. `plan_select.main()` — exit 2 on a `--keep` token that names no step in the plan; take `--drop`
   for the offered set so only the tail defaults to decline. (CRITICAL-2)
4. `plan_select.choices()` — refuse to compose a reason from an absent `protects`. (MEDIUM-1)
5. `selection.md:34` — default `WF_ID`/`TIER`/`PROFILE`/`TAGS` in the block, and pass `--tags` to
   `choices` as well. (HIGH-2, LOW)
6. Guards: anchor the `export TRIVIAL_SHAPE=` regex as its sibling is anchored; assert the reason is
   not `"no reason given"`; run `selection.md`'s bash block against a fixture and assert exit 0; move
   the test fixture's manifest to `docs/system-manifest.yaml`. (HIGH-1, HIGH-2, MEDIUM-1, CRITICAL-1a)

Items 1 and 2 are the ones without which the headline feature of this release does not exist on any
project. Item 3 is the one that makes the release actively worse than 2.8.0: before it, a plan could
not be lightened without someone naming each step; after it, one command with an empty `--keep`
declines twenty-nine of them and the fail-closed validator says clean.

**DO NOT SHIP.**
