# Consequence review — HITL 2.9.0, round 2

**State:** `07bda66` on `main`. Diffs read: `9ba9fd2..HEAD` (the round-1 fixes), `v2.8.0..HEAD` (the release).
**Lens:** consequence — what this destroys, exposes, or makes unrecoverable.
**Verdict: DO NOT SHIP.**

All findings below were reproduced in scratch repos (`mktemp -d`). No tracked file in the platform
repo was modified; `git status --porcelain` is clean apart from pre-existing untracked review files.

Round 1's three unreachable features are now reachable — `plan_select.py` is a real caller with three
working modes, and `rank.py`'s import of `check_skips.resolve_crit` genuinely closes the tier-4
divergence (verified: 0 disagreements across all 8 workflows × tiers 0–4, and the *fallback*
implementation agrees too). The problem is one layer up. The tool is correct and the shell block that
invokes it does not run; the file it writes has a second writer that truncates it; and on every repo
onboarded before 2.9.0 it silently ranks code review, architecture review and QA verification below
the cut line and declines them.

| # | Sev | Finding |
|---|---|---|
| C1 | CRITICAL | The `selection.md` shell block cannot run: four variables it reads are assigned nowhere. Both invocations exit 2, and the second truncates the choices file to 0 bytes. |
| C2 | CRITICAL | Two writers to `.hitl/first-pass-choices.json`. Step 4b's heredoc clobbers Step 4's 25 tail records down to 2. Reproduced end to end. |
| C3 | CRITICAL | Version skew: 2.9.0 tool + pre-2.9.0 local catalog ⇒ every rank "medium", so `review1`/`arch_review`/`qa_verify`/`verify_pr` fall into the auto-declined tail, land in the ledger as "no reason given", and `check_skips` prints "clean". |
| H1 | HIGH | `TRIVIAL_SHAPE` is structurally `0` at intake — the probe sees only committed work, and it runs before the branch and before any edit. The refusal added in this release cannot fire on the change that motivated it. |
| H2 | HIGH | `--keep` is not validated against the plan. One typo silently declines the step the person asked to keep. |
| M1 | MEDIUM | "Recorded" is a receipt. The reason field is the step's own `protects` sentence — an argument *for* the step, filed as the reason to skip it — or literally "no reason given". 14 standard skips per change accumulate: 3 changes ⇒ 42 resurfaced reminders. |
| M2 | MEDIUM | `selection.md` says "the floor can be unticked". Through the tool it cannot be, and no decline is written. |
| L1–L6 | LOW | Four false CHANGELOG claims; a coherence challenge that always fires falsely in the `docs` workflow; a non-tolerant fallback resolver; a dead parameter; a variable name with two opposite meanings; two different numbers for the same incident. |

---

## C1 — CRITICAL — the shipped selection block does not run, and failing truncates the choices file

`ai/claude/start-change/selection.md:34,78` read `$WF_ID`, `$TIER`, `$PROFILE`, `$TAGS`. None of the
four is assigned anywhere in the skill:

```
$ grep -rn 'WF_ID\|^WF=\|WF="' ai/claude/start-change/
selection.md:28:WF="ci/first-pass/workflows.yaml";  [[ -f "$WF"  ]] || WF="$ROOT/shared/workflows.yaml"
selection.md:34:python3 "$SEL" render --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
selection.md:78:python3 "$SEL" choices --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
SKILL.md:205:WF=<development|brownfield|migration|migration_review|prd|release|docs>
```

`WF_ID`, `TIER`, `PROFILE`, `TAGS` are never set. Running the block as shipped, in a repo where a
real choices file already exists:

```
$ echo '{"actor":"a","choices":{"roi":{"disposition":"decline","reason":"real earlier work"}}}' \
    > .hitl/first-pass-choices.json
$ bash verbatim.sh          # lines 27-35 and 78-81 of selection.md, copied verbatim
plan_select.py: error: argument --tier: invalid int value: ''
render rc=2
plan_select.py: error: argument --tier: invalid int value: ''
choices rc=2
$ wc -c .hitl/first-pass-choices.json
       0 .hitl/first-pass-choices.json
```

Two consequences. The selection never renders, so the release's headline feature is once again
invoked by nothing — this time by a shell defect rather than a missing caller. And because line 81 is
a bare `>` redirect, the shell truncates the target *before* python runs, so every failure of this
command destroys whatever was already in the choices file.

This is exactly the clobber the Step 6 generator was hardened against — `SKILL.md` writes to
`.hitl/current-change.yaml.tmp` and `mv`s only on success, with a comment explaining why. The new
command in `selection.md` does the thing that guard exists to prevent, one file away.

The failure is not limited to unset variables. Any refusal path truncates:

```
$ python3 ci/first-pass/plan_select.py choices --workflow development --tier 2 --keep issue \
      > .hitl/first-pass-choices.json          # --actor omitted
--actor is required: a skip is accountable to a person, not the agent
rc=2
$ ls -l .hitl/first-pass-choices.json
-rw-r--r--  0 ... .hitl/first-pass-choices.json

$ python3 gen.py development GH-1 feat 2.9.0 2 .hitl/first-pass-choices.json "" ""   # Step 6
.hitl/first-pass-choices.json is not valid JSON: Expecting value: line 1 column 1 (char 0)
gen rc=1
```

Step 6 then prints *"Existing change file and your First Pass choices are untouched."* The choices
were zeroed thirty seconds earlier.

**Smallest fix.** Assign the four variables in the block (`WF_ID`, `TIER`, `PROFILE`, `TAGS` — with
the same `<placeholder>` convention `SKILL.md:205` already uses), and give `plan_select.py` an
`--out` that writes temp-then-rename so no invocation of it can leave a truncated file.

---

## C2 — CRITICAL — two writers to the choices file; the second destroys the first

`selection.md:78-81` (Step 4) writes `.hitl/first-pass-choices.json` with plan_select's output.
`first-pass-choices.md:11-19` (Step 4b, which runs *after*) writes the same path with a heredoc:

```bash
cat > .hitl/first-pass-choices.json <<'JSON'
```

`cat >`, not merge. Neither document mentions the other. Reproduced with the real generator:

```
$ python3 ci/first-pass/plan_select.py choices --workflows ci/first-pass/workflows.yaml \
      --workflow development --tier 2 --keep "issue,impact,review1,verify_pr" --actor "me@team" \
      > .hitl/first-pass-choices.json
$ python3 -c "import json;print(len(json.load(open('.hitl/first-pass-choices.json'))['choices']))"
25
$ python3 gen.py development GH-1 feat 2.9.0 2 .hitl/first-pass-choices.json "" "" > cc-full.yaml
$ grep -c "status: skipped" cc-full.yaml
25

# now run first-pass-choices.md:11-19 exactly as written
$ cat > .hitl/first-pass-choices.json <<'JSON' ... JSON
$ python3 -c "import json;print(len(json.load(open('.hitl/first-pass-choices.json'))['choices']))"
2
$ python3 gen.py development GH-1 feat 2.9.0 2 .hitl/first-pass-choices.json "" "" > cc-clob.yaml
$ grep -c "status: skipped\|status: starter" cc-clob.yaml ; grep -c "status: open" cc-clob.yaml
2
31
```

Twenty-three steps the person unticked, and was told were "skipped and recorded", come back as
`open`. `selection.md:84` states the invariant in bold: *"If the tail does not reach it, the tail is
skipped and NOT recorded."* The step immediately after it is what stops the tail reaching it.

The destruction runs both ways. If Step 4b's file is written first — a floor risk-accept carrying
`ack_by` and `waiver_ref`, a `starter` disposition, a `followup_ref` — `plan_select choices` emits
only bare `decline` entries and re-keys the whole document, so the ack, the waiver reference and the
starter artifact are erased with no copy anywhere. `plan_select` cannot even express those fields.

**Smallest fix.** One writer. Give `plan_select.py` a `--merge <existing.json>` that preserves any
entry already present (and its `ack_by`/`waiver_ref`/`starter_artifact`/`followup_ref`), then rewrite
`first-pass-choices.md` to describe the *entry shape* fed into that merge rather than to `cat >` the
file itself.

---

## C3 — CRITICAL — on any repo onboarded before 2.9.0, the tail is the review steps, and the validator says clean

`selection.md:27-28` resolves the tool and the catalog **independently**:

```bash
SEL="ci/first-pass/plan_select.py"; [[ -f "$SEL" ]] || SEL="$ROOT/shared/ci/first-pass/plan_select.py"
WF="ci/first-pass/workflows.yaml";  [[ -f "$WF"  ]] || WF="$ROOT/shared/workflows.yaml"
```

A repo onboarded at 2.8.0 has `ci/first-pass/workflows.yaml` (copied by `init-project.sh:222`) but no
`plan_select.py` — that file is new in 2.9.0. So `SEL` falls back to the plugin's 2.9.0 tool while
`WF` resolves to the repo's 2.8.0 catalog. `step_costs` is new in this release:

```
$ git show v2.8.0:ai/shared/workflows.yaml > wf280.yaml
$ python3 -c "import yaml;print(sorted(yaml.safe_load(open('wf280.yaml'))))"
['schema_version', 'workflows']
```

With no `step_costs`, `rank.shown_rank` sees `{}` for every step, defaults `forgo_cost` to `medium`,
and the sort collapses to catalog position:

```
$ python3 plugroot/shared/ci/first-pass/plan_select.py render --workflows wf280.yaml \
      --workflow development --tier 2
Running (locked)
   red                thinnable, never dropped
   green              thinnable, never dropped
   integration_verify floor at tier 2
   deploy             floor at tier 2
   promote            floor at tier 2

Selected — untick any                      what you'd lose
   [x] issue            medium
   [x] figma            medium
   [x] impact           medium
   [x] roi              medium
   [x] docs             medium
   [x] iac              medium
   [x] test_plan        medium
   [x] training         medium

   + 21 more, skipped and recorded: packet, adv_design, test_review, design_plus, verify_red, verify_green …
```

The "what you'd lose" column is empty — that column *is* the feature. The eight offered are the first
eight catalog entries. Everything that verifies the change is in the collapsed tail, declined by
default. Carried through the real Step 6 generator and the real validator:

```
$ python3 plugroot/shared/ci/first-pass/plan_select.py choices --workflows wf280.yaml \
      --workflow development --tier 2 --keep issue --actor me@t > .hitl/first-pass-choices.json
$ python3 gen.py development GH-1 feat 2.9.0 2 .hitl/first-pass-choices.json "" "" \
      > .hitl/current-change.yaml
$ grep -n "review1\|arch_review\|qa_verify\|verify_pr" .hitl/current-change.yaml
35:    - { n: "18",  key: "review1",     ... status: skipped }
37:    - { n: "19a", key: "arch_review", ... status: skipped }
40:    - { n: "22",  key: "qa_verify",   ... status: skipped }
43:    - { n: "25",  key: "verify_pr",   ... status: skipped }
68:  - { step: review1, crit: standard, actor: "me@t",
       reason: "below the cut line at intake (rank medium): no reason given", ... disposition: decline }
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
First Pass skip ledger: clean.
$ echo $?
0
```

Code review, architecture review, QA verification and PR verification are all skipped, all recorded
as "no reason given", and the fail-closed validator certifies the change clean. Nothing anywhere
warns that the catalog is missing the block the ranker exists to read. `/hitl:dev-update` does refresh
the catalog (`update/SKILL.md:248`) — but nothing forces a user to run it before `start-change`, and
the failure is silent when they haven't.

The same degradation hits any workflow other than `development` even on a current catalog:

```
$ for W in release platform migration prd brownfield docs migration_review; do ... done
release          7 entries; no-reason-given: 7
platform        17 entries; no-reason-given: 17
migration        9 entries; no-reason-given: 9
prd              5 entries; no-reason-given: 5
brownfield      11 entries; no-reason-given: 10
docs             6 entries; no-reason-given: 4
migration_review 5 entries; no-reason-given: 5
```

(The `step_costs`-covers-only-`development` fact is recorded as known and not re-reported. What is
new here is what the *writer* does with the gap: it emits a ledger of reasonless declines that the
generator and the validator both accept, because the only check on `reason` is that it is non-empty.)

**Smallest fix.** Fail closed. `plan_select.py` should exit 2 when the resolved catalog has no
`step_costs` for the requested workflow — "this catalog predates the ranker; run `/hitl:dev-update`" —
rather than ranking every step `medium` and calling that a selection. Additionally, resolve `WF` from
the same root that `SEL` resolved from.

---

## H1 — HIGH — `TRIVIAL_SHAPE` is structurally `0` at intake

`plan_select.changed_paths` (`plan_select.py:24-33`) runs `git diff --name-only <merge-base>..HEAD`.
That sees **committed** work only, and `selection.md` runs at Step 4 — before Step 5 creates the
branch, and before anything has been written.

```
$ git checkout -q main                       # where start-change actually runs
$ python3 ci/first-pass/plan_select.py probe
0
$ python3 -c "...; print(P.changed_paths('main'))"
[]

$ git checkout -q feat && echo "SECRET=1" >> demo.sh     # uncommitted work
$ python3 -c "...; print(P.changed_paths('main'))"
['README.md', 'src/core/a.py']               # demo.sh absent — ..HEAD cannot see it
```

`trivial_shape` returns `False` for empty paths by design ("nothing to judge is not evidence of
triviality"), so the probe prints `0`. The Step 6 refusal added by this release —

```python
if trivial and tier >= 2 and not (tier_set_by.strip() and tier_reason.strip()):
```

— therefore cannot fire on the FIRECRAWL scenario the release was written for: at intake there is no
diff, so `trivial` is never true. Round 1 found the probe set no variable; it now sets a variable
whose value is `0` in the flow that matters.

Three further states produce a silent `[]` with no message to the user (stderr is captured and
discarded at `plan_select.py:29`):

```
repo whose default branch is `master`     changed_paths('main') -> []
unborn branch (no commits)                probe -> 0
not a git repo at all                     probe -> 0
```

Beyond the dead refusal, empty paths mean `touches_risky` can never fire and every `engages: {paths:}`
step is demoted one rank. On the shipped catalog all 38 `step_costs` entries carry `engages`, so this
is not a corner.

**Smallest fix.** Include the working tree and the index (`git diff --name-only` + `--cached`, union
with the committed range), and return a distinguishable "no signal" instead of `[]` so the caller can
say so rather than silently ranking on nothing.

---

## H2 — HIGH — one typo in `--keep` declines the step the person asked to keep

`plan_select.py:157` builds the kept set from a raw string split and validates nothing against the
plan's own key set:

```python
kept = {k for k in a.keep.split(",") if k} | {r["key"] for r in locked}
```

```
$ python3 ci/first-pass/plan_select.py choices --workflows ci/first-pass/workflows.yaml \
      --workflow development --tier 2 --keep "review1,verifypr,arch-review" --actor me@t
(no warning on stderr)
verify_pr declined despite the user typing it: True
arch_review declined: True
```

`verifypr` and `arch-review` are near-misses for real keys (`verify_pr`, `arch_review`). Both real
steps are declined and recorded as *"unticked at intake"* — a record that attributes to the human the
exact opposite of what they said. The agent composes this argument from free-text conversation
(`selection.md` explicitly invites *"also drop docs"* as a normal reply), so key-shaped typos are the
expected input, not the exotic one. The tool has the key set in hand.

**Smallest fix.** Exit 2 on any `--keep` token that is not a step key in the resolved plan, naming it.

---

## M2 — MEDIUM — the floor cannot be unticked, and no record is written when someone tries

`selection.md` states: *"**The floor can be unticked.** It is not locked out of the view, it is
locked out of casual choice."* Line 157 unions `locked` into `kept` unconditionally, so:

```
$ python3 ci/first-pass/plan_select.py choices ... --keep "issue,impact,red,green,integration_verify,promote" --actor me@t
deploy in choices? False
any floor/no_omit recorded? []
```

A person who unticks `deploy` gets no decline, no ack prompt, no waiver prompt, and no error. The
step silently reverts to running. That is fail-safe on the step, but it converts a documented,
signature-bearing decision path into a no-op the person is never told about.

---

## M1 — MEDIUM — priority 2, answered: "recorded" is a receipt

Judged honestly against the artifact the writer now produces:

**The reason field argues the opposite of the decision.** `plan_select.py:99-107` composes the reason
from the step's own `protects` sentence:

```
"verify_green": { "disposition": "decline",
  "reason": "unticked at intake: The suite is green for real, not green because it never ran." }
```

That is the case *for* running verify_green, filed as the reason it was skipped. `check_skips`
requires only that the string be non-empty, so it passes. And it is echoed verbatim into the
user-facing reminder:

```
$ python3 -c "...; print(RS.message(s[0]))"
A quick heads-up: last time work touched this area, 'verify_green' was lightened
(decline by me@team — reason: unticked at intake: The suite is green for real...
```

**Or there is no reason at all.** For 7 of 8 workflows, and for every workflow on a pre-2.9.0
catalog, the string is literally `"...: no reason given"` (C3). A ledger entry reading *"below the
cut line at intake (rank medium): no reason given"* is a timestamp with a name on it.

**And the volume destroys the resurfacing mechanism that was supposed to make it a control.** One
development change at tier 2 deposits 25 declines, 14 of them `standard` (ceremony is not
resurfaced). Entries recorded at intake carry no area, so `SKILL.md:444` records them project-wide
and they *"resurface at any later change until resolved"*:

```
$ # three changes, --append each time
$ python3 -c "...; print('rollup entries:',len(r['entries'])); print('resurfaced at change 4:',len(RS.surface(r,['core'],['src/core/**'])))"
rollup entries after 3 changes: 75
resurfaced at change 4: 42
```

Forty-two paragraph-long reminders at the fourth change, each carrying an inverted reason. `surface()`
has no cap. A reminder list nobody can read is not a control, and the release's own reasoning —
*"A check that always warns teaches people to ignore it"* (`SKILL.md:418`) — condemns it.

So: **a receipt.** The record proves a decision was taken and by whom. It carries no reason, is not
gated on, and the mechanism meant to convert it into future pressure is drowned by the volume the new
default produces. That does not by itself make the CR-1 reversal wrong — showing eight items beats
hiding thirty-one — but "recorded" is not currently doing the compensating work the CHANGELOG assigns
to it.

---

## L1 — CHANGELOG 2.9.0 claims that are now false

| Claim | Status |
|---|---|
| *"**Nothing is ever silent:** every skipped step lands in the ledger"* | **False.** C2: 23 of 25 do not, following the shipped step order. |
| *"A project with no manifest or no registry gets the same order, quietly"* | **False.** Reproduced: order differs at index 18 (`review2` vs `rerun`) because `engages: {multi_domain}` steps demote without a manifest. Consequence is nil — the offered/tail cut is unchanged — but the sentence is not true. |
| *"Eleven such dependencies now **challenge** the selection and take an answer"* | **Misleading.** 11 pairs exist; only **6** can fire at tier 2. Five have a prerequisite the tool always keeps (`red`, `green`, `deploy` are locked), and one (`docs`/`reconcile`→`review1`) names a step absent from its workflow. Both illustrations the CHANGELOG uses — *"GREEN is defined against a RED that was never generated"* and *"`promote` without `deploy`"* — are in the dead set. `test_rank.py` says so in its own docstring: *"green/red cannot demonstrate this: red is no_omit, so it is locked and always kept — the incoherence is unreachable by construction."* The release ships tests that know the prose is wrong. |
| *"`protects` and `forgo_cost` for **all 38 steps**"* | **False as written.** The shipped catalog has 87 distinct step keys across 8 workflows; 53 have neither field. (Adjacent to the known `step_costs`-coverage item — flagged here only because the CHANGELOG states 38 as the total.) |
| *"On the change that started this: 4 locked, 8 offered, 22 recorded"* | **True** — verified at tier 0 and tier 1, which is the FIRECRAWL case. At tier 2 it is 5/8/21. |

---

## L2 — a coherence challenge that always fires falsely in the `docs` workflow

`step_requires` is global across workflows; `reconcile` requires `review1`. The `docs` workflow has
`reconcile` and has no `review1`:

```
$ python3 -c "...; print([s['key'] for s in d['workflows']['docs']['steps']])"
['issue', 'scope', 'draft', 'doc_review', 'reconcile', 'merge']
$ python3 ci/first-pass/plan_select.py choices --workflow docs --tier 2 \
      --keep "scope,draft,reconcile,merge" --actor me@t
incoherent: keeping reconcile while dropping review1 — reconciling findings from a review that did not happen
```

Every docs change that keeps `reconcile` is challenged about dropping a step that is not in its plan.
`rank.incoherent` should skip a `need` that is absent from the plan being ranked.

## L3 — the fallback resolver is not exception-tolerant where the imported one is

Priority 3 checked. The import is sound: `check_skips.py` has no heavy module-level code, ships
alongside `rank.py` in every install path (`init-project.sh:222`, `update/SKILL.md:143,247`), and
there is no cycle. The fallback also **agrees** with `resolve_crit` on the shipped catalog:

```
$ # force R._resolve_crit = None, compare across 8 workflows × tiers 0-4
disagreements on the real catalog: 0
```

Round 1's tier-4 defect is genuinely closed in both paths. The residual is narrow: the fallback is
not malformed-input-tolerant.

```
{'key':'x','crit':'floor','crit_by_tier':{'2':['floor']}}
  fallback: RAISE TypeError: unhashable type: 'list'   |  real: floor
'notadict'
  fallback: RAISE AttributeError                       |  real: standard
```

With a malformed catalog *and* a missing `check_skips.py`, `plan_select` crashes instead of degrading,
and under the documented `>` redirect that truncates the choices file (C1). `rank.py`'s own docstring
promises *"Missing data means 'no signal', never an error"*. LOW: requires both conditions.

## L4 — `build()` takes a parameter it never uses

`plan_select.py:61` — `def build(plan, costs, requires, *, ...)`. `requires` is never referenced in
the body; the caller passes `step_requires` twice (lines 149 and 158), once into a dead slot.

## L5 — `WF` means two incompatible things in one skill

`selection.md:28` `WF` = path to the catalog file. `SKILL.md:205` `WF` = the workflow *id*. Same
variable name, same skill, opposite meanings, and the workflow id `selection.md` actually needs
(`WF_ID`) is assigned nowhere (C1). Cross-contamination between the two blocks produces
`unknown workflow 'ci/first-pass/workflows.yaml'` at Step 6, after every choice has been made.

## L6 — two different numbers for the motivating incident

`selection.md:14` — *"HITL ran thirty-one steps over three and a half hours."*
`CHANGELOG.md:9` and `right-sizing.md:9` — *"3 hours 31 minutes across **eleven** recorded steps."*
Same incident, in the release that is named after it.

---

## Areas checked and found sound

Stated plainly, as permitted:

- **The tail partition is exhaustive.** `build()` returns `locked + rest[:8] + rest[8:]` over
  `rank_plan(plan)`, which iterates every step. No step in the shipped catalog lacks a `key` or
  shares one with another (scanned all 8 workflows). Every non-kept step reaches `choices`. Priority 1
  found no gap *in the tool* — every gap found is in what surrounds it (C1, C2, C3, H2).
- **The ranker/validator floor agreement holds** at every tier 0–4, on the real catalog, in both the
  imported and fallback paths.
- **The Step 6 generator's temp-then-`mv` guard is correct** and refuses on every documented path
  without writing.
- **`ci/retired-tests.sha256` is correct.** `e7f86c39…` matches HEAD's `test_rank.py` byte for byte.
- **The new tests are behavioural, not name-greps.** `test_rank.py` shells out to `plan_select.py` in
  a real git repo; the new wiring guard anchors on `^[^#]*python3 "$SEL" <mode>` specifically to
  survive the comment-out mutation. This is a real fix to the round-1 class of defect.
- **`test_wiring.py` and `test_rank.py` pass** (55 + 20) and leave the working tree clean.
- Known-and-recorded items (`step_costs` coverage, the incident-registry raise, `engages` gating its
  own artifact, the three link rewrites) were not re-reported.

---

## Verdict

**DO NOT SHIP.**

C1, C2 and C3 are each independently sufficient. C3 is the one that does damage without anyone
noticing: on every repo onboarded before 2.9.0 — which is every existing HITL project — the feature
that exists to show a person what they would lose shows them a blank column, ranks the review steps
below the cut line, declines them with "no reason given", and the fail-closed validator certifies the
result clean.

**Smallest change that clears the blockers:**

1. `plan_select.py`: exit 2 when the resolved catalog has no `step_costs` for the workflow, pointing
   at `/hitl:dev-update`. (Closes C3 by failing closed instead of ranking on nothing.)
2. `plan_select.py`: add `--out PATH` writing temp-then-rename, and `--merge PATH` preserving existing
   entries and their `ack_by`/`waiver_ref`/`starter_artifact`/`followup_ref`; use `--out` in
   `selection.md:78` instead of `>`; rewrite `first-pass-choices.md:11-19` to feed the merge rather
   than `cat >` the file. (Closes C2 and the truncation half of C1.)
3. `selection.md`: assign `WF_ID`, `TIER`, `PROFILE`, `TAGS` in the block, and resolve `WF` from the
   root `SEL` resolved from. (Closes the rest of C1 and L5.)
4. `plan_select.py`: exit 2 on an unknown `--keep` key. (Closes H2 — three lines.)

H1 needs the probe to see uncommitted work before the refusal it feeds is worth anything, but it is
a dead check rather than a destructive one; it can follow.
