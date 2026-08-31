# Consequence review — 2.9.0 (`9ba9fd2`)

Lens: what does this destroy, expose, or make unrecoverable. Refuting, not confirming.
Every finding below was reproduced. Commands and observed output are inline.

**Verdict: DO NOT SHIP.** Two one-line fixes and one regenerate close the blocking set; see the end.

---

## C1 — CRITICAL. Step 4 skips the tail. Only Step 4b can record it. Step 4b says the opposite.

The release's compensating control for reversing CR-1 is "recorded in the ledger". There is no
writer.

`ai/claude/start-change/SKILL.md`, Step 4 (line ~137):

> **Then show the selection** ([`selection.md`](selection.md)): […] Locked steps lead as already-on;
> six to eight are offered; **the tail is collapsed and skipped, recorded.**

`ai/claude/start-change/SKILL.md`, Step 4b — the very next section (lines ~151, ~157):

> **First Pass** […] **Above tier 1 it is opt-in and the full plan is the default.**
> […] and doing nothing still runs the full plan — **`keep` remains the default disposition (CR-1)**.

Two sections of one file, in one release, state opposite defaults for the same tier-2 change. Check
each file against itself: this file fails.

Now the recording path. `selection.md` line 62:

> **Everything below the cut line is skipped, and recorded.** Name, reason, timestamp, in the ledger
> that already exists.

It names no file, no schema, no command. Grep for one:

```
$ grep -n "first-pass-choices\|ledger\|skips\|record" ai/claude/start-change/selection.md
62:**Everything below the cut line is skipped, and recorded.** Name, reason, timestamp, in the ledger
70:hard gate. That is the skip ledger's existing machinery, reachable from here for the first time.
82:skipping the whole TDD pair is an ordinary recorded skip.
```

The only ledger writer in the skill is `.hitl/first-pass-choices.json`, and SKILL.md's own Step 6
generator says who writes it:

```
$ sed -n '200,300p' ai/claude/start-change/SKILL.md | grep -n "first-pass-choices"
18:CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b; absent ⇒ full plan, no First Pass
```

So the chain is: Step 4 drops 21 steps → the writer is Step 4b → Step 4b is opt-in above tier 1 and
defaults to `keep`. Whichever branch an agent takes, one of the two is inoperative:

- follows Step 4 → 21 steps dropped, `first-pass-choices.json` absent, generator seeds the full plan
  with **no record of the decision at all**, and the person has been shown a screen saying those 21
  were skipped;
- follows Step 4b → nothing is dropped, and the entire feature is inert.

CHANGELOG 2.9.0 asserts both halves as fact: *"Now the tail is skipped by default and recorded"* and
*"**Nothing is ever silent:** every skipped step lands in the ledger."* Neither has a mechanism in
this diff.

**Answer to "is the receipt sufficient compensation":** there is no receipt. And even where one is
written by hand, it is not a compensating control — see C9.

---

## C2 — CRITICAL. `rank.py` and `check_skips.py` disagree about what the floor is. At tier 4 six floor steps are unlocked.

`ci/first-pass/rank.py:86` resolves criticality by **exact tier match**:

```python
crit = (s.get("crit_by_tier") or {}).get(tier, s.get("crit", "standard"))
```

`ci/first-pass/check_skips.py:96` — the fail-closed validator — and `docs/design/first-pass/03-lld.md`
both specify the opposite:

> the effective criticality is the **highest-tier key ≤** the change's tier, else `crit`

Reproduced:

```
$ python3 repro1.py      # rank_plan vs resolve_crit over ai/shared/workflows.yaml
tier 1 rank.py locked: ['red', 'green', 'deploy', 'promote']
      DIVERGENCE: []
tier 2 rank.py locked: ['red', 'green', 'integration_verify', 'deploy', 'promote']
      DIVERGENCE: []
tier 3 rank.py locked: ['impact','packet','red','green','arch_review','qa_verify','rollout','deploy','promote']
      DIVERGENCE: ['integration_verify']
tier 4 rank.py locked: ['red', 'green', 'deploy', 'promote']
      DIVERGENCE: ['arch_review', 'impact', 'integration_verify', 'packet', 'qa_verify', 'rollout']
```

At **tier 4 — the highest tier the generator accepts (`if not 0 <= tier <= 4`)** — the six steps that
`crit_by_tier` makes floor are all treated as ordinary rankable steps by the thing the human reads.
Where they land:

```
$ python3 repro2.py
=== tier 4 {'paths': ['src/payments/charge.py']}
 LOCKED  : ['red', 'green', 'deploy', 'promote']
 OFFERED8: [('issue','high'),('impact','high'),('verify_green','high'),('review1','high'),
            ('arch_review','high'),('qa_verify','high'),('rollout','high'),('verify_pr','high')]
 TAIL(22): [('packet','medium'), … ('integration_verify','medium'), …]
```

`packet` and `integration_verify` are floor steps sitting in the **auto-skipped collapsed tail** with
no ack, no waiver, no ceremony. `arch_review`, `qa_verify` and `rollout` are offered as ordinary
checkboxes that can be unticked without the "name the loss, take a name, link a waiver" flow that
`selection.md` reserves for the floor.

The validator does eventually catch it — after the plan is set:

```
$ python3 t7.py
tier 4: 22 steps skipped in the collapsed tail
  check_skips -> [('FLOOR_NO_ACK', "floor step 'packet' skipped with no ack_by (accountable role)"),
                  ('FLOOR_NO_ACK', "floor step 'integration_verify' skipped with no ack_by …"),
                  ('FLOOR_NO_WAIVER', "floor step 'integration_verify' maps to a hard gate but has
                   no waiver_ref (skip != waiver)")]
```

This is priority 2's "a floor step argued down the list", and it is not modulation doing it — it is
the lock resolution. `ci/wiring/test_wiring.py::test_a_floor_step_is_never_ranked_below_high`
reasons explicitly about these steps and **excludes them from the guard** on the belief that "a step
that is floor at tier 3 alone … is LOCKED at that tier". It is not, at tier 4.

Same defect, milder, at tier 3: `integration_verify` unlocks and demotes to `medium` (see C6), so
the step named "The pieces work together, not just individually" sits in the auto-skipped tail on
the tier reserved for the riskiest changes.

---

## C3 — HIGH. Both new inputs are empty at the exact moment they are read.

`start-change` is the enforced front door **before any edit**. SKILL.md, line 24:

> The HITL hooks […] inject a directive that no real work may happen until a change is active for the
> current branch, and `check-hitl-context.sh` **hard-blocks edits until then**.

Step 3b (tier) and Step 4 (selection) both run before Step 5 creates the branch and before any code
exists. Both new mechanisms read `git diff`. Run the probe from `right-sizing.md` as written, at the
moment it is called:

```
$ git init r && … && git checkout -b issue/42-fix-charge
$ BASE=main; git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null | sed -n '1,200p'
--- (no output) ---
line count: 0
```

Three consequences, all reproduced:

**(a) The incident-registry raise can never fire.** It is the only mechanism in the release that can
*raise* a rank — "this area has burned us before".

```
$ python3 repro3.py
risky domains: {'payments': ['src/payments']}
touches_risky([]) -> False
touches_risky(['src/payments/charge.py']) -> True
```

`paths` is `[]` at intake, so the raise is dead. CHANGELOG lists it as shipped: *"up one when a
changed path falls in a manifest domain named in the incident registry."*

**(b) Every path-keyed `engages` fails**, demoting `docs`, `iac`, `figma`, `figma_compare` on every
change. Demotion is the only direction this failure goes (see C6).

**(c) The shape probe classifies every change as trivial.** `right-sizing.md` defines "**Non-source**
means […] anything outside the `paths` of a domain in the system manifest." An empty diff is
vacuously non-source-only, so the table's row 1 ("a value: env var, flag, version pin, doc line →
tier 0 or 1, reason pre-filled") matches every change. `right-sizing.md` has a "What this never
does" section; it does not cover an empty diff, which is the universal case at intake.

---

## C4 — HIGH. The tier-2+ attribution refusal has no writer, so it never fires.

Priority 4 asked me to find someone this blocks mid-work with no way forward. Nobody, because it is
unreachable. That is worse than blocking someone.

```
$ grep -rn "TRIVIAL_SHAPE" . | grep -v "^./.git/"
ci/wiring/test_wiring.py:539:    assert "TRIVIAL_SHAPE" in body, (
ai/claude/start-change/SKILL.md:234:# […] TRIVIAL_SHAPE comes from the probe in right-sizing.md.
ai/claude/start-change/SKILL.md:235:trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1","true","yes")
ai/claude/start-change/SKILL.md:242:             "default. See right-sizing.md; TRIVIAL_SHAPE=0 if the probe is wrong." % tier)
```

One reader, one string-presence assertion, zero writers. `right-sizing.md` — which the code comment
names as the source — never mentions the variable. So:

- CHANGELOG **Changed**: *"A tier 2+ declared on a trivially-shaped change now needs a name and a
  reason too. This **adds** a rule rather than trading one away."* It adds an unreachable rule.
- CHANGELOG **Note for existing projects**: *"One thing newly refuses: a tier 2 or higher declared on
  a change whose diff touches no source under a manifest domain, with no `tier_set_by`/`tier_reason`."*
  Nothing newly refuses.

This is the release's own named wiring-defect class, and the wiring test written to prevent it
asserts the reader exists rather than the writer — the same shape as `excludes`/`activates`, which
is what the release exists to atone for.

Two secondary consequences worth naming:

1. **If someone does wire it** from the empty-diff probe (C3c), every tier-2 change refuses until an
   accountable human name is supplied — friction on every change in every project.
2. **The gate reads an env var set by the party it constrains**, and its own error message documents
   the bypass: `"TRIVIAL_SHAPE=0 if the probe is wrong"`. An agent that hits the refusal can re-run
   with `TRIVIAL_SHAPE=0` and never mention it. A gate whose failure message is its own workaround is
   not attribution.

---

## C5 — HIGH. The default selection keeps the review and drops the reconcile. `incoherent()` is silent.

Priority 3: the incoherent selection that should have been refused.

Default tier-2 selection on a real source change, top 8 kept plus locked:

```
$ python3 t8.py
--- coherence of the DEFAULT tier-2 selection (top 8 kept + locked) ---
kept: ['arch_review','deploy','green','impact','integration_verify','issue','promote',
       'qa_verify','red','review1','rollout','verify_green','verify_pr']
incoherent(kept) -> []
```

`review1` is kept. In the auto-skipped tail:

- `rerun` — *"Tests re-run after review edits, so the thing reviewed is the thing that ships."*
- `reconcile` — *"Every review finding is resolved or explicitly accepted; none are quietly dropped."*
- `conventions`, `review2`, `adv_code`, `verify_red`, `packet`, `test_plan`, `docs`.

So the shipped default runs a code review, produces findings, never re-tests after the edits those
findings cause, and never confirms a single finding was resolved — and the coherence check certifies
it as coherent. `step_requires` encodes `reconcile → needs: [review1]` but not the converse, and the
block's own comment defends that choice: *"Deliberately not a phase-order graph. Later-than is not
depends-on."* Correct in general, wrong here: `reconcile` is not later-than `review1`, it is the
half of `review1` that makes `review1` mean anything. A review whose findings go nowhere is exactly
the "claim the plan cannot support" that `incoherent()` was written to name.

Second silent case, from `selection.md`'s own rule *"The floor can be unticked"*:

```
--- keeping RED, unticking GREEN ---
incoherent({'red','review1','verify_pr'}, req) -> []
```

Generate a failing test and never fix it. `no_omit` catches this downstream at certification, but it
is not challenged at the point of choice, which is where the challenge is supposed to happen.

---

## C6 — HIGH. `engages` matches the diff, but the steps it gates are the ones that create the missing artifact.

```
$ python3 t9.py
A. `engages` is evaluated against the CHANGED paths, not the artifact the step produces:
   docs          paths=['src/app.py']               -> low
   docs          paths=['docs/runbook.md']          -> medium
   iac           paths=['src/app.py']               -> low
   iac           paths=['infra/main.tf']            -> medium
   iac           paths=['ai/shared/workflows.yaml'] -> medium
   test_plan     paths=['src/app.py']               -> low
   impact_brief  paths=['src/app.py']               -> low
```

`docs` protects *"The runbook and reference stop describing a system that no longer exists."* It is
ranked **low and auto-skipped** precisely when the code changed and the docs did not — the only case
where the step matters. It is ranked **medium** when the docs were already written, where the step is
nearly redundant. The signal is inverted for every produce-an-artifact step: `docs`, `iac`,
`test_plan`, `impact_brief`, `figma_compare`.

`iac`'s glob `**/*.yaml` also engages on any YAML file in the repo — a change to
`ai/shared/workflows.yaml` ranks "Update IaC" as medium.

The asymmetry is documented and applied in only one direction. `engaged()`'s docstring:

> Absent means the step's author did not narrow it, so it applies. **Guessing "not engaged" would
> silently demote every step nobody has annotated.**

That defensiveness protects missing *catalog* data. It is not applied to missing *runtime* data.
`profile=""`, `tags=()`, `multi_domain=False` — all defaults, all universal at intake, all resolve to
"not engaged", which demotes. Reproduced above and in C2's tier-3 case: `review2`, `impact_brief` and
`integration_verify` are permanently one rank below their declared cost because their signal is
`multi_domain`, which has no computed source at Step 4 (the impact step that determines domains is
step 3 *of the plan*, i.e. after intake). And `catalog.yaml`'s own new note says of profiles and tags:
*"Nothing at runtime applies them."* The ranker consumes exactly the signal the release documents as
absent, and the failure is one-directional: less protection, never more.

---

## C7 — MEDIUM-HIGH. `selection.md`'s only worked render is not producible by the ranker, and contradicts the CHANGELOG.

Priority 1 said to read this file as an agent would. An agent would imitate the mock, because it is
the only concrete rendering in the file. Here is the ranker's actual output for the change the mock
depicts (the `demo.sh` env var, tier 1):

```
$ python3 t8.py
--- the demo.sh change at tier 1, as selection.md's mock depicts it ---
locked  (4): ['red', 'green', 'deploy', 'promote']
offered (6): ['issue', 'impact', 'verify_green', 'review1', 'arch_review', 'qa_verify']
tail    (24): ['rollout','verify_pr','packet','adv_design','design_plus','verify_red','adv_code',
               'rerun','reconcile','integration_verify','figma','roi','docs','iac','test_plan',
               'training','test_review','refactor','conventions','review2','impact_brief',
               'figma_compare','roi_30','roi_90']
total   : 34
```

Against the mock, line by line:

| The mock shows | The code produces |
|---|---|
| 2 locked (`RED · GREEN`) | 4 locked (`red, green, deploy, promote`) |
| `no deploy steps in scope` as a locked-line entry | `deploy`/`promote` are `crit: floor`, `engages: always`; `rank_plan` has **no scope filter** and returns every step |
| offers `Docs`, `Test plan` | both rank `low` and sit in the tail |
| omits `issue` | `issue` is `high` and sorts **first** among unlocked |
| offers `Verify PR` | at a 6-wide cut it is in the tail (C8) |
| `+ 14 more` | 24 more at a 6-wide cut, 22 at 8 |
| names `baseline` in the tail | `baseline` is `cond: perf`; per this release's own catalog note it has **never** entered a runtime plan |
| 2 + 6 + 14 = 22 steps | the workflow has 34 |
| `protects` strings ("QA won't know what \"done\" meant") | `workflows.yaml` holds different sentences ("QA knows what \"working\" means for this change before anyone builds it") |

CHANGELOG for the same change says *"4 locked, 8 offered, 22 recorded […] A person decides on 8 items
instead of 34."* That arithmetic is correct and matches `rank_plan`. It also flatly contradicts the
mock in `selection.md`. Two files in one release describe the same screen with different numbers.

Two further self-inconsistencies inside `selection.md`:

- The offered band is headed **"Selected — untick any"** and then shows three of six boxes already
  **unticked** (`☐ Docs`, `☐ Test plan`, `☐ Arch review`). The default tick state of the offered band
  is never stated, and the only affordance named is "untick". Whether a shown-but-unticked step runs
  is undefined — for `arch_review`, whose `protects` is *"a boundary crossing goes unnoticed"*.
- **"Everything below the cut line is skipped"** — the cut line is never located. Is it below the
  six-to-eight, or below the ticked ones?

And the file's **only** demonstration of the floor-unticking ceremony — the machinery that makes the
CR-1 reversal survivable — uses `pentest`:

> Unticking **pentest**. This change touches auth, so nothing else in the plan looks for a privilege
> bug. Who is accepting that, and against which waiver?

`pentest` is `cond: security` and is not in the development workflow. `ai/shared/workflows.yaml`
line 30 says so in terms: *"There is NO standalone 'Pentest' step."* An agent will never encounter
this case, so it never learns the ceremony from the one place it is shown.

```
$ python3 -c "…"
costs not in dev plan: ['baseline', 'cve_audit', 'pentest', 'sec_design']
```

Four of the "all 38 steps" the CHANGELOG advertises are read by nothing at runtime.

---

## C8 — MEDIUM. The six-to-eight cut is unspecified and can auto-skip a `high` step.

```
$ python3 t9.py
C. the 6-vs-8 cut, tier 1, scripts/demo.sh — where a `high` step lands:
   cut=6 -> auto-skipped HIGH steps: ['rollout', 'verify_pr']
   cut=7 -> auto-skipped HIGH steps: ['verify_pr']
   cut=8 -> auto-skipped HIGH steps: none
```

`selection.md` says *"**Then six to eight, ranked**"* and gives no rule for choosing, and no rule that
the cut may not fall inside a rank band. Whether *"CI is green on the exact commit being merged"*
(`verify_pr`, `forgo_cost: high`) is offered or silently dropped depends on an unconstrained agent
choice between two numbers.

Made worse by `issue`: `forgo_cost: high`, `engages: always`, so it sorts **first** in every
selection at every tier — and Step 2 already completed it ("A change must trace to an issue…
Require an explicit choice."). One of only six-to-eight slots is permanently burned on a decision
already made, pushing a real `high` step over the cut.

---

## C9 — MEDIUM. The ledger is not a compensating control for the tail.

Assume C1 is fixed and the tail *is* written correctly. The validator still has nothing to say:

```
$ python3 t7.py
tier 2: 21 steps skipped in the collapsed tail
  tail: ['packet','adv_design','design_plus','verify_red','adv_code','rerun','reconcile','figma',
         'roi','docs','iac','test_plan','training','test_review','refactor','conventions','review2',
         'impact_brief','figma_compare','roi_30','roi_90']
  check_skips -> CLEAN — nothing to report
```

Twenty-one steps dropped, ledger written, validator silent. That is correct behaviour —
`check_skips` guards the floor, and none of these are floor at tier 2 — but it means the CHANGELOG's
pairing of *"every skipped step lands in the ledger"* with *"the fail-closed validator still blocks
an unauthorised floor skip"* invites the reader to hear a guarantee that does not extend to the
21 steps the release actually changed the default on.

And on screen, the ledger's twin is one collapsed line. `selection.md`:

> **Then the tail, collapsed.** One line naming the rest and their count.

The mock's format names four before an ellipsis (`conventions, reconcile, rerun, baseline …`). At
tier 2, 17 of 21 skipped steps are never named on screen. Set against the same file's rule two
sections later — **"Say what is being skipped; never let silence do it"** — the render does not meet
the rule the file wrote for itself.

So: the receipt is real but narrow, and the screen it is supposed to back up names a fifth of what
was dropped.

---

## C10 — MEDIUM. `site/catalog.html` at HEAD is not generator output, and deletes the three ROI steps.

Regenerated the page in a scratch copy of the repo at HEAD:

```
$ tar cf - tools ai/claude/plugin ai/shared site/catalog.html | (cd $S && tar xf -)
$ cd $S && python3 tools/scripts/generate-catalog-page.py
wrote site/catalog.html (99 step rows)
freshly generated dev steps: 34
roi steps present: ['roi', 'roi_30', 'roi_90']
summary: 31 steps + 3 substeps · 7 phases
$ cmp -s $S/site/catalog.html site/catalog.html && echo IDENTICAL || echo DIFFERENT
DIFFERENT
```

What the checked-in page at HEAD says instead:

```
$ python3 -c "…"   # first workflow block of each file
old dev steps (v2.8.0): 34
new dev steps (HEAD):   31
REMOVED from the portal: ['roi', 'roi_30', 'roi_90']
$ grep -o 'class="phname">[^<]*<' site/catalog.html | head -7
… Requirements Design Build Verify Assess Ship  (Post-Ship absent)
```

- `28 steps + 3 substeps · 6 phases` where the runtime has 31 + 3 across 7
- `Post-Ship` phase deleted entirely
- every step from 4 onward renumbered: RED `10 → 9`, review1 `18 → 17`, arch_review `19a → 18a`
- legend `96 → 93 steps`; HTML comment `99 → 96 step rows`

`derive.py verify` passes, so `catalog.yaml` and `workflows.yaml` agree — the page alone is wrong.
The page's own footer claims *"generated from tools/workflow-catalog/catalog.yaml — the file the
derive gate verifies against the shipped runtime."* False at HEAD. Nothing in the CHANGELOG mentions
removing the ROI steps.

**Consequence.** A user's breadcrumb reads `Step 19a / 31`; the published catalog says `18a` of `28`.
That is a user concluding their install is broken — the exact failure this release was written to
fix. Someone evaluating HITL from the repo reads a delivery spine with no ROI accountability at all.

**Mitigation that limits it:** `.github/workflows/pages.yml` regenerates the page on every deploy and
this release touches both trigger paths, so the live URL self-heals. The harm is confined to the
repo artifact and to anyone reading `site/` from a clone. But the release was cut from a tree whose
`site/` was generated from something other than the committed catalog, and the only content guard on
this file (`test_the_portal_agrees_with_itself_about_the_current_version`) checks version strings,
not steps.

---

## C11 — LOW. `right-sizing.md` quotes a duration, which `selection.md` forbids in the same release.

`selection.md`:

> **Never quote a duration.** Quote step counts. Elapsed time is dominated by when someone reads
> their notifications, which HITL does not control and cannot predict.

`ai/claude/start-change/right-sizing.md:36`, the suggested script for the same conversation:

> This touches `demo.sh` only, so I'd run it as tier 1 — the ceremony steps come off and **it's about
> twenty minutes.** Say the word if you want it heavier.

`ci/wiring/test_wiring.py::test_the_selection_keeps_its_load_bearing_rules` guards the rule, and reads
only `selection.md`. Its own docstring gives the reason the rule exists: *"Two shipped estimates in
this repo were wrong."* This release ships a third, in a file the guard does not read.

---

## CHANGELOG 2.9.0, claim by claim

| Claim | Verdict |
|---|---|
| "`ai/shared/workflows.yaml` […] carries `workflows` and nothing else. No profiles. No tags." | Was true; present tense is now wrong — this release adds `step_costs` and `step_requires` to that file. Reads as a description of the pre-release state, so: imprecise, not false. |
| "`fix` excludes roi/training → none, ever" etc. | **True.** `derive.py` is source-tree only; runtime has no `profiles`/`tags`. Verified. |
| "**`protects` and `forgo_cost` for all 38 steps**" | **True but misleading.** 38 spine entries, 38 costs. Four (`baseline`, `cve_audit`, `pentest`, `sec_design`) are `cond:` steps that never enter a runtime plan — data nobody reads, the defect this release exists to fix. |
| "up one when a changed path falls in a manifest domain named in the incident registry" | **True in code, unreachable in practice.** `paths` is empty at intake (C3a). |
| "never past the floor" | **False at tier 4, and at tier 3 for `integration_verify`** — not via modulation, via lock resolution (C2). |
| "Eleven such dependencies now challenge" | **True.** 11 entries in `step_requires`, all naming real steps. |
| "They never block" | **True.** `incoherent()` returns a list, never raises. |
| "A tier proposed from the shape of the change. If the diff touches only non-source paths…" | **Vacuous at intake** — the diff is empty, so every change matches (C3c). |
| "A tier 2+ declared on a trivially-shaped change now needs a name and a reason too." | **False.** `TRIVIAL_SHAPE` has no writer (C4). |
| "First Pass is offered at tier 0/1 without being asked" | **True** in SKILL.md Step 4b. |
| "Now the tail is skipped by default and recorded." | **Contradicted by SKILL.md Step 4b in the same release**, and "recorded" has no writer (C1). |
| "**Nothing is ever silent:** every skipped step lands in the ledger" | **False.** No mechanism (C1). The screen names ~4 of 21 (C9). |
| "the fail-closed validator still blocks an unauthorised floor skip" | **True where a ledger exists** (FLOOR_NO_ACK/FLOOR_NO_WAIVER reproduced), but it says nothing about the 21 non-floor steps this release changed the default on (C9). |
| "4 locked, 8 offered, 22 recorded […] 8 items instead of 34" | **Arithmetic true** and matches `rank_plan` at tier 1. Contradicts `selection.md`'s mock (2/6/14) (C7). |
| "Note for existing projects — One thing newly refuses…" | **False.** Nothing newly refuses (C4). |
| "`step_costs` and `step_requires` are new blocks read at intake; nothing re-reads a seeded plan" | **True.** |
| "Existing change files are unaffected." | **True.** |
| **Unmentioned in the CHANGELOG** | `site/catalog.html` drops the three ROI steps and the Post-Ship phase and renumbers the spine (C10). |

---

## Sound — one line each, no findings

- **Determinism.** `rank_plan` returned an identical order across 200 runs on identical input; ties break on catalog position. No ordering instability found.
- **Missing-data degradation in `rank.py`.** `shown_rank(None)`, `shown_rank({"forgo_cost":"banana"})`, `risky_domains(None,None)`, `touches_risky(["a/b"],None)`, `incoherent(None,None)` all return sensibly and none raise. Verified.
- **`incoherent()` contract.** Returns tuples, never raises, and all 11 dependencies name real steps with a `without_it` sentence that says what breaks.
- **`ci/retired-tests.sha256`.** Adding `test_rank.py` is correct: removal requires tracked **and** hash **and** basename match, and the branch no-ops inside the platform repo.
- **`derive.py verify`** passes, and `catalog.yaml`'s `step_costs`/`step_requires` are byte-equal to `ai/shared/workflows.yaml`'s.
- **`check_skips.py` floor enforcement** still fires correctly when given a ledger containing a floor skip.
- **The `catalog.yaml` advisory note** on profiles/tags is accurate, and `test_the_catalog_does_not_claim_profiles_filter_the_plain` is well-aimed: it fails if someone wires profiles into the runtime without revisiting the note.
- **`.hitl/current-change.yaml`'s new YAML anchor** (`allowed_paths: &id001` / `paths: *id001`) is handled by both the `yaml.safe_load` path and the no-yaml fallback in `check-domain-boundary.sh`. Not a finding.
- **The 67 new/existing tests in `test_rank.py` + `test_wiring.py` all pass.** They are the reason C2, C4 and C10 got through: they assert text presence and single-tier behaviour, not the cross-file agreement each one is standing in for.

---

## Verdict

**DO NOT SHIP.**

The release reverses CR-1 and the thing it traded CR-1 for — the record — does not exist. That is the
blocking finding, and it is not a judgement call: Step 4 and Step 4b of one file state opposite
defaults, and the only ledger writer is behind the branch that says the tail is not skipped.

### Smallest change that fixes it

Two lines and one command:

1. **`ci/first-pass/rank.py:86`** — resolve criticality the way `check_skips.resolve_crit` and the LLD
   already specify, so the floor cannot be unlocked at tier 4 (closes C2):

   ```python
   # was: crit = (s.get("crit_by_tier") or {}).get(tier, s.get("crit", "standard"))
   from check_skips import resolve_crit
   crit = resolve_crit(s, tier)
   ```
   (or inline the max-over-keys-≤-tier; either way one expression.)

2. **`ai/claude/start-change/SKILL.md`** — delete the two sentences in Step 4b that now assert the
   opposite of Step 4 (*"Above tier 1 it is opt-in and the full plan is the default"*, *"doing nothing
   still runs the full plan — `keep` remains the default disposition (CR-1)"*), and add one sentence
   to Step 4 naming the writer: *the tail is written to `.hitl/first-pass-choices.json` as `decline`
   entries with the reason "below the cut line at intake" and the confirming human as `actor`; Step 4b
   is the same collection pass.* This makes "recorded" true and gives `check_skips` something to
   check (closes C1, makes C9 an accurate statement of a narrow guarantee rather than a false one).

3. **`python3 tools/scripts/generate-catalog-page.py && git add site/catalog.html`** — restores the
   three ROI steps, the Post-Ship phase, and the spine numbering to the portal (closes C10).

Not blocking but should not ship unexplained: **C4** (either wire `TRIVIAL_SHAPE` in `right-sizing.md`
or cut the two CHANGELOG claims and the migration note that describe a refusal that cannot fire) and
**C7** (the mock in `selection.md` is the thing an agent will imitate; it should be the ranker's
actual output for the `demo.sh` change, which the CHANGELOG already states correctly as 4/8/22).

C3, C5, C6 and C8 are design gaps rather than defects introduced by a bad line, and each is a real
loss of protection. They do not need to block this release, but they should be written down before
the next one claims right-sizing is solved: an incident raise that cannot fire, a ranker whose only
input is empty when it runs, a coherence check silent on the default selection, a signal inverted for
every artifact-producing step, and a cut line chosen by nothing.
