# Design review — right-sizing, fitness lens

**Target:** `docs/design/right-sizing/01-design.md` (commit `feb2cc3`, "cut it down to the plan")
**Lens:** fitness. Does this design satisfy the requirement it claims to satisfy, and what case does it not handle?
**Verdict: NOT SOUND.**

Method: every statement below about how HITL behaves today is taken from the files at HEAD and quoted,
or reproduced by running the shipped code. Reproductions ran in `mktemp -d` scratch dirs. Nothing in
the tree was modified; the only file written is this report.

The design is a plan, not an implementation, so the bar I applied is: can a competent implementer
build this without inventing a contract the design did not specify, and if they build exactly what is
written, does the motivating change come out shorter and still safe? The answer to both is no.

---

## Summary

| # | Sev | Finding |
|---|---|---|
| F1 | CRITICAL | The central claim is a sequencing claim, and sequencing is not what is wrong at 6b. Reproduced: with the record present and correctly ordered, `check_skips.py` certifies a 21-step auto-decline whose every reason reads "no reason recorded" as **clean, exit 0**. The design adds no rule to 6b. |
| F2 | CRITICAL | The design has no writer for the shortening decision. Shortening happens at intake Step 4; the change file does not exist until Step 6. The only artifact that ever bridged that gap is the choices file, which `ci/wiring/test_wiring.py` now **forbids** any file under `start-change/` from writing. This is failure #1 restored verbatim. |
| F3 | CRITICAL | The motivating change lands in the branch where §5 switches shortening **off**. `demo.sh` is outside every domain's `files`, so §2 yields `undeclared` / `confidence: unknown`, and §5's first bullet shows the full plan. The one-line env var gets 31 steps again. |
| F4 | HIGH | Even with shortening fully on, the motivating change is not materially shorter at tier 2. Reproduced: locked = `red, green, integration_verify, deploy, promote`. A TDD RED/GREEN cycle to add an environment variable is the exact complaint in `right-sizing.md:8-9`, and §8 puts it out of scope. |
| F5 | HIGH | The impact facts do not shorten anything. `build()` cuts at a constant `OFFERED = 8`; the tail is auto-declined regardless. Reproduced: identical locked/offered/tail for `demo.sh` and `src/billing/refund.py` at tiers 1, 2 and 3. Better evidence changes *which eight you are asked about*, not how many steps run. |
| F6 | HIGH | §1 says "Nothing else moves" while omitting Step 4b, which is a second collector of dispositions feeding the same generator input. Two writers to that input is failure #2, reproduced by a previous reviewer as "Step 4b's heredoc clobbers Step 4's 25 tail records down to 2". |
| F7 | HIGH | The lookup answers at most one of the six impact questions outright. On the manifest `init-project.sh` actually installs, 3 of the 8 fields §2 reads exist. `owning_fr` is a compound-agentic field, which §8 says is out of scope. |
| F8 | HIGH | §5's off-switches are all about information quality. None is about risk. The catalog's risk-shaped steps engage on `profiles`/`tags`, and §8 leaves those as advice, so they are demoted on every change forever. `right-sizing.md:45` has a "does not survive a real risk signal" rule; §5 has no counterpart. |
| F9 | MEDIUM | §4 misdiagnoses why the incident-registry check does not work. Reproduced: `risky_domains()` returns `{}` on the shipped worked-example manifest because it reads `domains` as a list with `paths` while manifests are a map with `files`, and `plan_select.py`'s `--manifest` / `--incidents` defaults point at paths no project has. Matching on domain names does not fix a reader that never loads the file. |
| F10 | MEDIUM | The §3 fact block has no home and no writer. `change-context.schema.yaml` has no `impact:` key, the facts are produced before the change file exists, and "which domain" already has a declared home (`manifest.domain`) written by a different step. |
| F11 | MEDIUM | §6 removes apply-change Step 3, which is the declared consumer of the incident registry and the declared precondition of Steps 4, 5, 6, 7 and 7a. §3's handover carries no incidents field and the design does not say what Step 7a resurfacing does now. |
| F12 | MEDIUM | `/hitl:dev-apply-change` is separately invocable and seeds its own change file. On that path there is no impact block, no shortening and no 6b, and §6's "checks it against the recorded evidence" has no evidence to check. Unmentioned. |
| F13 | LOW | §7 restates the premise `sizable()` got wrong. §5's "missing or **incomplete**" is the right fix but does not define incomplete, and an undefined threshold is exactly how `len(keys) // 2` happened. |
| F14 | LOW | The dead `git diff` probe in `right-sizing.md` is unmentioned. §1 makes it redundant by putting 3a before 3b, but nothing says to delete it, and three reviewers flagged it as still shipped. |

Sound, stated plainly, at the end.

---

## 1. The central claim: does moving impact analysis into intake make 6b correct?

**Where 6b is, and what it is.** The design's step numbering is accurate.
`ai/claude/start-change/SKILL.md:413` is `## Step 6b — Certify the ledger`, it runs
`python3 "$CHK" .hitl/current-change.yaml` (`SKILL.md:434-441`) and its stated contract is *"Run it
**before** the Step 7 commit, so nothing uncertified is ever pushed"* (`SKILL.md:415-416`). So yes,
6b is where the local check runs, and yes, at HEAD it runs before the only writer of skip records
(`apply-change/SKILL.md:131` Step 3a) and therefore sees an empty ledger. The design's diagnosis of
the *ordering* is correct.

**But the ordering was never what made 6b wrong.** 6b runs `check_skips.py`, and `check_skips.py`
validates the *accountability* of a ledger, not the *correctness* of a shortening. Its per-record
test for a reason is one line, `check_skips.py:331`:

```python
if not _str(s.get("reason")).strip():
    findings.append(_f("SILENT_SKIP", f"skip '{key}': reason is empty"))
```

Non-empty is the whole test. And the string the shortener manufactures is non-empty by construction,
`plan_select.py:129-130`:

```python
"reason": "not selected at right-sizing (rank %s): %s"
          % (r["rank"], r["protects"] or "no reason recorded")
```

Reproduced. A tier-2 `development` change with the full 34-step plan present, the 21-step tail marked
`skipped`, each carrying an attributed record whose reason is
`not selected at right-sizing (rank medium): no reason recorded`, and `first_pass: true`:

```
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ai/shared/workflows.yaml
First Pass skip ledger: clean.
EXIT=0
```

Declined and certified clean in that run: `review2`, `adv_code`, `conventions`, `reconcile`,
`impact_brief`, `packet`, `adv_design`, `test_review`, `docs`, `iac`, `test_plan`, `refactor`,
`verify_red`, `design_plus`, `rerun`, `figma`, `figma_compare`, `roi`, `roi_30`, `roi_90`,
`training`. Twenty-one steps, one command, exit 0, in a named person's name, with the literal
admission that no reason was recorded.

That is the state the design's §1 promises to fix by fixing the ordering. Fixing the ordering
produces exactly this state, on time. **The check does not read the impact facts, does not compare
the shortening to them, and the design adds no rule that it should.** §1's sentence "The skip check
stays at 6b and starts working" is true only in the sense that it stops reading an empty list. What
it then reads, it accepts.

Two further points on the same claim:

- 6b is not the last line of defence and never was. `ci/workflows/first-pass-check.yml:31` runs the
  same validator on the PR. Any failure that 6b's ordering hid, the PR gate catches. The failures
  that actually mattered in round 3 (a whole plan declined; reasons that say nothing) exit 0 in
  **both**, because they are not ledger-integrity failures. Repairing the local ordering therefore
  buys less than the design implies, and buys nothing at all for the two worst outcomes of the
  implementation it replaces.
- 6b invokes the validator with no `--tier` and no `--workflows`, resolving the catalog through
  `_default_workflows()` (`check_skips.py:441-451`), which prefers the project's own
  `ci/first-pass/workflows.yaml`. §5 makes the *shortener* stand down when that catalog is stale.
  The *certifier* does not stand down; it resolves criticality from whichever catalog it finds. The
  design does not say the two must be the same file. On a half-refreshed project they need not be.

**Finding F1 (CRITICAL).** The design fixes the sequencing and calls that correctness. 6b checks who
signed, not whether the plan that was cut matches the evidence that was gathered. Without a new rule
at 6b tying `skips[]` to the `impact:` block, the design's central claim does not follow.

---

## 2. Would this design have prevented each of the three earlier failures?

Taken one at a time.

### Failure 1 (2.9.0 round 1): the shortening had no writer

`consequence-2.9.0.md` C1, quoting `SKILL.md` Step 4 against Step 4b, and the generator's own comment:

> So the chain is: Step 4 drops 21 steps → the writer is Step 4b → Step 4b is opt-in above tier 1 and
> defaults to `keep`. Whichever branch an agent takes, one of the two is inoperative.

**The design restores this topology exactly, and does not name a writer.** Its diagram puts
"4. shorten the plan using those facts" before "6. write the change file including anything skipped".
At Step 4 the change file does not exist: `SKILL.md:204` is `## Step 6 — Seed and write
.hitl/current-change.yaml`, and the tool that writes records refuses when it is absent
(`plan_select.py:110-111`):

```python
doc = _load(change_path)
if not doc:
    return None, "no change file at %s — intake creates it; run /hitl:dev-start-change first" % change_path
```

So something must carry the decision from Step 4 to Step 6. The only artifact that has ever done this
is `.hitl/first-pass-choices.json`, still read by the Step 6 generator at `SKILL.md:223`
(`CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b; absent ⇒ full plan, no First Pass`)
and still consumed at `SKILL.md:394` (`rm -f .hitl/first-pass-choices.json     # consumed`). Writing
it is now forbidden by a shipped guard, `ci/wiring/test_wiring.py:769-786`:

```python
    d = os.path.join(AI, "claude", "start-change")
    ...
    assert not handoff, (
        "the selection still writes a choices file. Intake's Step 6 consumes that and has already "
        "run by then, so the record reaches nobody:\n  " + ...)
```

and the same test, three lines later, *requires* `selection.md` to run `plan_select.py apply`
instead, which is the mode that cannot run at Step 4.

The design therefore cannot be implemented as written without either restoring the artifact its own
test suite forbids, or inventing a new one it does not name. **Failure 1 can happen again, and the
design contains the same gap that produced it: a step that decides, and no stated writer.**
(F2, CRITICAL.)

### Failure 2 (2.9.0 round 2): two writers to that artifact, and an unrunnable block

`consequence-2.9.0-r2.md` C2: *"Two writers to `.hitl/first-pass-choices.json`. Step 4b's heredoc
clobbers Step 4's 25 tail records down to 2. Reproduced end to end."* And C1: the shell block read
`$WF_ID`, `$TIER`, `$PROFILE`, `$TAGS`, none of which was assigned anywhere.

The design's step list is 1, 2, 3, 3a, 3b, 4, 5, 6, 6b, 7, 8. **Step 4b is not in it, and §1 says
"Nothing else moves."** Step 4b is live at `SKILL.md:157-188`, is linked from `right-sizing.md:55`,
and is the tier-0/1 batch-decline path (*"One confirmation clears all eleven"*). So after this design
lands, intake has two mechanisms that collect dispositions at intake and feed the same generator: the
new shortening at Step 4, and Step 4b. The design does not delete 4b, does not subordinate it, and
does not say which one owns the record. That is the precondition for failure 2. (F6, HIGH.)

On the variable-plumbing half of failure 2: the design says nothing about where `WF_ID`, `TIER`,
`PROFILE`, `TAGS` or `IMPACT_PATHS` come from either. §3 defines a facts block that carries `paths`
and `domains` but not `profile`, `tags`, `multi_domain` or `tier`. Three of those are live inputs to
`rank.shown_rank()` (`rank.py:95-106`). A design whose stated purpose is to fix contracts between
components leaves three of the ranker's five inputs unassigned.

### Failure 3 (2.9.0 round 3): the writer moved past every guard

Round 3's writer defects were: no `--actor` guard on the live path (C2/B5), tier and workflow taken
from argparse defaults instead of the change file (C3/C10), `--keep ""` annihilating the plan (C5),
a one-way ratchet with no un-skip (C6/B2/U6), `current_step` left pointing at a skipped step
(C9/B1/U1), writing into any change file regardless of branch or `merged` status (B6), and only one
of three dispositions (B7).

Here the design does better, though only by implication. If the writer becomes the Step 6 generator
again, most of those defects disappear, because the generator has the guards `plan_select apply`
lacks: it refuses a lightening with no actor (`SKILL.md:315-316`), it refuses a disposition the tier
does not allow (`SKILL.md:311-313`), it refuses an unregistered starter (`SKILL.md:309`), it refuses
when everything was lightened (`SKILL.md:319-322`, *"every step in the plan was lightened — there is
no change left to run"*), it never lands `current` on a lightened step (same block), and it takes the
tier from the variable the human confirmed rather than an argparse default.

**But the design never says the writer is the generator.** It never says Step 3a in
`apply-change/SKILL.md` is deleted, only that "Its impact analysis step is removed" (§6). Step 3a is
a *different* step from Step 3, sitting at `apply-change/SKILL.md:131-147`, and it is where the
writer currently lives. Read literally, §6 removes Step 3 and leaves Step 3a in place, which puts the
writer back downstream of 6b and reproduces round 3 in full while §1 claims the opposite. Read
generously, §6 means both go, and round 3's writer defects are cured as a side effect nobody wrote
down. A design that exists because three implementations had contract holes cannot leave which
component writes the record to the reader's generosity. (F2 again.)

**Score: failure 1 recurs, failure 2 recurs, failure 3 is cured only under a generous reading the
text does not license.**

---

## 3. Is the lookup possible, and how much of the six questions does it answer?

The six questions are `apply-change/SKILL.md:118-129`: affected endpoints/APIs, affected
services/modules, affected infrastructure, affected documentation, affected tests, backwards
compatibility. That step also carries a hard rule the design's §2 replaces: *"Search the codebase to
verify each item. Don't guess — read the files."*

What the manifest declares, from `ai/claude/generate-docs/templates/system-manifest.schema.yaml:22-135`:

| §2 field | exists? | authored | answers which question |
|---|---|---|---|
| `files` | yes (line 32) | auto | modules, fully |
| `lld` | yes (line 37) | auto | which doc *governs the domain*, not which doc describes the changed behaviour |
| `tests` | yes (line 42) | auto | tests, if declared |
| `boundary_entities` | yes (line 47) | **human** | partial |
| `facade_apis` | yes (line 62) | **human** | the domain's facades, not which one your edit changes |
| `events_emitted` / `events_consumed` | yes (85, 94) | **human** | partial |
| `depends_on` | yes (line 102) | auto | in-repo, domain-level dependents only |
| `last_changed` | yes (line 112) | **human** | a hint, as §9.2 already concedes |
| `owning_fr` | yes (line 135) | **human**, and it sits under the block headed *"Compound-agentic extensions (EPIC #10) — ALL optional and additive"* | contradicts §8 |

Scoring the six questions honestly: **one is answered outright** (services/modules, via `files`).
Three are answered with *candidates* that still need a read (endpoints, docs, compatibility). One
depends on a field absent from the shipped template (tests). One, **affected infrastructure, has no
manifest field at all** and does not appear in §2's table or §3's handover; "do manifests, configs,
secrets, or migrations need updating" is not derivable from a domain entry.

Backwards compatibility is worth its own line, because the design's own example breaks it. §3's
worked output is `facades: [POST /refund]` with `dependents: [checkout, reporting]`. `depends_on` is
*"Other domain names this domain depends on"* (schema line 102): in-repo, domain-granular. For a
`POST /refund` HTTP facade the callers who break are typically outside the repo, and no manifest
field lists them. The lookup returns the domains that declared a dependency, not the callers that
have one. §2's flow has no branch for that; its only escape hatch is "does the change go past what is
written down", which a reader cannot evaluate without reading the callers, which is the search the
design says is no longer needed.

**What a real project actually has.** `tools/scripts/init-project.sh:171` copies
`ai/shared/templates/system-manifest-template.yaml` to `docs/system-manifest.yaml`. Checked
mechanically, that template's domains carry exactly `files`, `lld`, `facade_apis`. Three of the eight
fields §2 reads. The worked example at `docs/examples/greenfield/docs/system-manifest.yaml` carries
nine of ten (all but `owning_fr`), so the design is describing the best case as if it were the
default. Nothing in §5 distinguishes "this manifest is rich" from "this manifest is the template with
two domains filled in": `confidence` is defined nowhere, and the only stated inputs to it are whether
a domain claims the path.

**Graphify.** The design's cost claim rests on it: *"Graphify already indexes the code and the docs
and rebuilds on write, so this is a lookup."* In this repository the only trace of Graphify is a
`.graphifyignore` file and prose mentions in the CHANGELOG/README. No shipped code reads a Graphify
index; `plan_select.py` reads YAML files off disk. And the fields the design most depends on for the
questions the manifest could uniquely answer (`facade_apis`, `boundary_entities`, `events_*`,
`last_changed`) are `authored: human`, so no indexer rebuilds them on write, whatever Graphify does.
The claim that keeps the analysis cheap is unverifiable from the repo and, for half the table,
contradicted by the schema's own `authored:` annotations. (F7, F8.)

---

## 4. The change where the information looks good and the shortening is still wrong

Three, in increasing order of how normal they are.

**(a) The paths are a prediction, not an observation, and confidence does not measure that.**
This is the important one. `selection.md:21-23` states the constraint the design is fighting:

> **After impact analysis, not before.** Intake happens before a line is written, so nothing there
> knows what the change touches.

The design moves impact analysis to intake. It does not move the code. §2's flow begins at "paths you
touched", but at intake nothing has been touched; the paths are inferred from the issue text. So
`confidence: declared` means *"the paths I guessed are claimed by a domain"*, not *"these are the
paths"*. A confident wrong guess produces the design's strongest possible evidence signal.

Concretely: "add a retry to the refund endpoint". Predicted `src/billing/refund.py`, claimed by
`billing`, `confidence: declared`, dependents `[checkout]`, shortening on, tail declined, ledger
written, certified at 6b, committed at Step 7. Implementation then discovers the retry needs a change
in `src/checkout/client.py` too. The change is now cross-domain, which `apply-change/SKILL.md:44`
calls Tier 3 on its own. Every field in §3's block still looks good, because nothing re-derives it.
§5 has no off-switch for this, §6 re-checks only the *tier*, and §7's second bullet ("An existing
change file is never re-read or rewritten") points the other way. There is no stated path back.

**(b) A behaviour change that moves no interface.** §4's three matching rules are "touches these
domains", "something depends on the domain you touched", "a public interface moves". Change the
rounding rule in `refund()`, or the default currency, or a retry count. The signature does not move,
so rule three does not fire; rule one fires and rule two fires, which are exactly the rules that keep
`impact` and `arch_review` (already high-ranked and offered at every tier). Everything that would
have caught a semantic break in a dependent (`review2`, `adv_code`, `impact_brief`, `conventions`,
`reconcile`) is in the tail and auto-declined. Information: perfect. Shortening: wrong.

Note also that §4's third rule has no producer. §3's handover carries `facades: [POST /refund]`,
which is *the domain's facades*, not *the facades this change moves*. §4 consumes a fact §3 does not
emit. That is a contract hole of exactly the class that killed the three implementations, in the two
sections that are supposed to define the contract.

**(c) Risk is not in the model at all.** §5's four off-switches are all about information quality.
None is about what the change is. The catalog's risk-shaped steps engage on profiles and tags
(`ai/shared/workflows.yaml`: `sec_design` → `engages: { profiles: ["security"] }`, `cve_audit` →
`profiles: ["upgrade"]`, `test_plan` → `profiles: ["feature","enhancement","fix"]`, `baseline` →
`tags: ["perf"]`), and §8 says: *"Making profiles and tags filter the plan. They stay as advice."*
With no profile ever supplied, `rank.engaged()` (`rank.py:81-92`) falls through to the glob branch,
finds no globs, returns False, and `shown_rank()` demotes the step one rank on every change forever.
Swapping folder globs for domain names (§4) does nothing for a `profiles:`-keyed step.

Meanwhile `right-sizing.md:45-46` carries the rule the design drops:

> **It does not survive a real risk signal.** Secrets moving between files, auth, permissions,
> anything a `security` profile activates on: propose the tier you would have proposed anyway.

An auth change inside a well-declared domain scores `confidence: declared` and shortens exactly like
a logging change. (F8, HIGH.)

---

## 5. Walking the actual change through this design

The change, from `right-sizing.md:8`: add `FIRECRAWL_API_KEY` to `demo.sh`.

**Step 3 — workflow.** Not docs-only (`SKILL.md:78`: the `docs` workflow is only for changes touching
nothing but docs), so `development`. §5's fourth bullet is satisfied.

**Step 3a — impact analysis.** `demo.sh` is a shell script at the repo root. `right-sizing.md:21`
defines the category precisely: *"**Non-source** means scripts, config, CI workflows, docs, examples,
fixtures, lockfiles — anything outside the `paths` of a domain in the system manifest."* No domain's
`files` claims it. §2's flow takes the left branch: **"no domain does → undeclared → confidence:
unknown"**.

**Step 3b — tier.** With unknown confidence, the design says nothing about what 3b should propose.
The existing proposal table lives in `right-sizing.md:26-30` and is driven by a `git diff` probe that
three reviewers reproduced as returning zero lines at intake. §1 puts 3a before 3b, which is the right
move and would let real path evidence replace the dead probe, but the design never says so and never
says the probe is deleted.

**Step 4 — shorten.** §5, first bullet: *"confidence is `unknown`, or something touched is
undeclared"*. **Shortening is off. The full plan is shown.** The user gets the 31-step plan that
produced the complaint.

That is the headline. **The design's fail-safe fires on the exact change the design exists to fix**,
because "undeclared" is doing two opposite jobs: for a script nobody owns it means *trivial*, and for
source no domain claims it means *unknown risk*. §2 collapses both into one node and §5 treats the
merged node as dangerous. (F3, CRITICAL.)

**And if it were on?** Suppose the manifest were extended to claim `demo.sh`, or §5 were relaxed.
Reproduced against the shipped catalog and ranker:

```
$ python3 - <<'PY'   # plan_select.build on ai/shared/workflows.yaml, development
tier 1 ['demo.sh']                 locked 4 offered 8 tail 22
tier 2 ['demo.sh']                 locked 5 offered 8 tail 21
  locked: ['red', 'green', 'integration_verify', 'deploy', 'promote']
  offered: issue, impact, verify_green, review1, arch_review, qa_verify, rollout, verify_pr
tier 3 ['demo.sh']                 locked 10 offered 8 tail 16
```

At tier 2 the surviving floor is `red`, `green`, `integration_verify`, `deploy`, `promote`: a full
TDD RED/GREEN cycle to add an environment variable to a shell script. `right-sizing.md:8-10` names
that cycle as one of the things the user reported as broken. §8 forecloses fixing it: *"Any change to
which steps are protected, or to the test-first rule"* is out of scope. So the only lever that
actually helps this change is the **tier**, and the tier machinery (Step 3b's proposal, the dead
probe, Step 4b's batch decline) is the part of the system the design leaves alone. At tier 1 there
are still 4 locked plus 8 offered, i.e. 12 steps to work through, against `right-sizing.md:34`'s own
promise of *"8 steps to decide on instead of 31"*. (F4, HIGH.)

**Is it safe?** In the shortening-off case, yes and irrelevant: it is today's behaviour. In the
shortening-on case, the 21 declined steps arrive with the reasons reproduced in §1 above and certify
clean. Safe in the ledger-integrity sense, not in the sense that anyone can later tell why code
review was skipped.

**And the facts do not change the length anyway.** `plan_select.py:21` is `OFFERED = 8`, and
`build()` returns `rest[:OFFERED], rest[OFFERED:]`. Reproduced: the locked/offered/tail split is
**identical** for `demo.sh` and `src/billing/refund.py` at tiers 1, 2 and 3. The rank modulation the
impact facts feed is at most ±1 (`rank.py:100-106`) and moves a step across the cut only at the
boundary. So the design's promise that facts shorten the plan is not a property of the mechanism the
facts feed: the facts reorder, a constant cuts, and the human's ticks decide the length. The design
never states how the evidence is supposed to change how many steps run. (F5, HIGH.)

---

## 6. What the design does not mention and must

- **Which component writes the shortening decision, in what file, in what schema.** F2. This is the
  contract all three implementations got wrong, and it is the one thing a design written to stop that
  must nail down.
- **Step 4b.** Deleted, subordinated, or left as a second writer. §1's "Nothing else moves" currently
  asserts the third. F6.
- **Where the §3 fact block lives.** `ai/shared/templates/change-context.schema.yaml` has no
  `impact:` key (top-level keys are `schema_version, hitl_version, expected_branch, change_id, tier,
  tier_set_by, tier_reason, status, source_artifacts, manifest, allowed_paths, required_evidence,
  approvals, blocker, workflow, current_step, token_tracking, first_pass, skips`). The same fact
  already has a home: `manifest.domain`, *"Manifest domain name this change belongs to"*,
  `required_for_tier: [2, 3]`, written at `apply-change/SKILL.md:172-180`. Two representations of one
  fact, produced by two steps, reconciled by nobody. F10.
- **Where the manifest and the incident registry are read from.** `plan_select.py:155-156` defaults to
  `docs/02-design/system-manifest.yaml` and `docs/03-engineering/incident-registry.yaml`. The
  canonical locations are `docs/system-manifest.yaml` (`init-project.sh:168-171`, 82 references in
  the tree) and `docs/04-operations/incident-registry.yaml` (32 references). `_load()` swallows the
  miss and returns `{}`. Taken with §5's third bullet ("the project has no manifest"), the design as
  specified would ship with shortening off on every project, and the fail-safe would hide it. F9.
- **That the manifest reader is shape-wrong.** Reproduced against the shipped worked example:

  ```
  domains type: dict keys: ['auth', 'catalog', 'orders']
  risky_domains(real manifest, incident in auth) -> {}
  source_paths(real manifest) -> []
  touches_risky(['app/services/auth.py'], risky) -> False
  ```

  `rank.risky_domains()` iterates `manifest["domains"]` expecting a list of dicts with `name` and
  `paths`; real manifests are a map keyed by domain name with `files`. §4 says the incident check
  "can then match on domain names, which it cannot do today", which is true, but the reason is the
  reader and the path, not the folder-name matching §4 proposes to replace. `multi_domain` is dead
  for the same reason and is a live input to the ranker. F9.
- **What happens to the incident registry in the analysis.** `incident-registry-template.yaml:15`
  declares its consumer: *"Step 3 (impact analysis): 'what has gone wrong in this domain before?'"*
  §6 removes Step 3; §2's table and §3's block have no incidents field. The question disappears. F11.
- **What happens to apply-change Steps 4, 5, 6, 7 and 7a**, all of which are written as consumers of
  Step 3. Step 7a is explicit (`apply-change/SKILL.md:186-189`): *"This is the first moment the change
  knows its own area... Called at intake, before `manifest.domain` and `allowed_paths` exist, it
  matches nothing and silently says nothing."* If the area is now known at intake, the design should
  say whether resurfacing moves too, and if not, why the skips written at intake are not resurfaced
  against the ledger until much later. F11.
- **The apply-change-without-intake path.** `apply-change/SKILL.md:81-83`: *"If
  `/hitl:dev-start-change` already seeded a `development` workflow block, just advance it... Otherwise
  write the full v2 block"*. On that branch there is no impact block, no shortening, no 6b, and §6's
  "checks it against the recorded evidence" has nothing to check. F12.
- **Who the actor is.** §9.3 asks this and leaves it open. It is not a detail: `_actor_of()` only
  requires a non-empty string, so at intake, where by the design's own admission only one person is
  present, the record will name the requester for declines they were shown once in a list. The whole
  skip-with-record model rests on that name meaning something. An open question here is a design gap,
  not a review question.
- **`ci/wiring/test_wiring.py:769-794`**, which asserts the current topology and will fail on the
  design's. A design that reverses a wiring decision must say which guard changes and what replaces it.

---

## Sound, stated plainly

- **§5's fourth bullet** (shortening off for any workflow other than `development`) is correct and
  closes a real, reproduced defect: the shipped catalog gives `step_costs` to development only, and
  the other seven workflows produced empty `protects` and "no reason recorded" records.
- **Putting 3a before 3b** is the right order. A tier proposal made from path evidence is better than
  one made from a `git diff` that is structurally empty at intake, and this is the design's best idea.
- **The direction of §5** (degrade to the full plan, never to the light one) is the right failure
  direction. Its defect is what it puts in the conservative branch, not the branch itself.
- **§5's "or incomplete"** is the correct fix to `sizable()`'s `>= max(1, len(keys) // 2)` threshold,
  provided "incomplete" is defined as full coverage rather than left to the implementer, which is how
  the half-coverage threshold arose in the first place.
- If §6 is read as removing apply-change Step 3a as well, returning the writer to the Step 6
  generator recovers six guards the round-3 writer lacks. I did not find that reading stated, but I
  found no evidence it is wrong either.

---

## Verdict

**NOT SOUND.**

**Smallest change that would fix it**, in two parts, both additive to the existing text:

1. **Name the hops.** Add a section that states, for each of the three handovers, the artifact, its
   single writer, its single reader and its schema: (a) impact facts from 3a to 4 and 3a to 6, (b)
   the shortening decision from 4 to the Step 6 generator, (c) whether Step 4b survives and, if so,
   which of the two owns the record. Say explicitly that `apply-change` Step 3a is deleted, not just
   Step 3. This is the whole reason the design exists and it is the one thing the current text leaves
   to the implementer.

2. **Split `undeclared`.** §2 must distinguish "outside every domain and non-source" (the
   `demo.sh` case: propose tier 0/1, shortening **on**, per `right-sizing.md`'s existing rule) from
   "source that no domain claims" (shortening off, manifest is stale). Without this, §5 turns the
   feature off for the change that motivated it.

Everything else in the summary table is a finding I would expect a fixed design to answer, but those
two are what make it unbuildable and unfit as written.
