# Bypass review — 2.9.0 release candidate

**State:** `9ba9fd2da89e5dc46c1f7cb40cacc8141d87e034` on `main` (`git diff v2.8.0..HEAD`)
**Lens:** bypass — this release adds and inverts controls; how do you get around them.
**Method:** all work in a detached `git worktree` under `mktemp -d`, removed afterwards. No tracked
file modified. Every finding below was reproduced; the command and its output are shown.

**Baseline:** `python3 -m pytest ci/wiring ci/first-pass/test_rank.py -q` → `242 passed, 4 skipped`.

---

## Verdict first

**DO NOT SHIP.**

The two controls this release is *named for* — the ranked selection and the recorded tail — have no
executable path. `rank.py` is never invoked by anything that ships, and the tail the intake view
declares "skipped, and recorded" reaches no writer. Everything downstream of those two facts (the
`locked` pin, the `protects` sentences, `incoherent()`, the incident raise) is machinery attached to
nothing, and both wiring guards for it are green.

This is the exact defect class `ci/wiring/test_wiring.py`'s own docstring enumerates:

> machinery that existed, was correct, was unit-tested, and was connected to nothing.

---

## CRITICAL-1 — The ranker has no caller. The whole selection feature is unreachable.

`selection.md` §"Compute the order" says `ci/first-pass/rank.py` does this, and ships a bash block
that resolves the path into `$RANK`:

```bash
RANK="ci/first-pass/rank.py"; [[ -f "$RANK" ]] || RANK="$ROOT/shared/ci/first-pass/rank.py"
git diff --name-only "$(git merge-base HEAD "${BASE:-main}")"..HEAD 2>/dev/null | head -200
```

`$RANK` is assigned and never used. `rank.py` has no CLI to use it with, and nothing imports it.

```
$ grep -n "__main__\|argparse\|def main" ci/first-pass/rank.py || echo "  NONE"
  NONE — rank.py has no CLI entry point

$ git grep -n "rank\.py\|import rank\|from rank\|shown_rank\|rank_plan" -- ai tools ci .github \
    | grep -v "^ci/first-pass/rank.py\|^ci/first-pass/test_rank.py\|^ci/wiring/test_wiring.py"
ai/claude/start-change/selection.md:17:`ci/first-pass/rank.py` (plugin fallback ...) does this. It reads
ai/claude/start-change/selection.md:22:RANK="ci/first-pass/rank.py"; [[ -f "$RANK" ]] || RANK="$ROOT/shared/ci/first-pass/rank.py"
ai/claude/update/SKILL.md:312:      ... ci/first-pass/test_rank.py \
ci/retired-tests.sha256:30:3b25391d...  test_rank.py
```

Four references. Two are a shell variable and a prose sentence; two are the test file's own name in
a cleanup list. **Zero invocations.** Same for `incoherent()` — `selection.md` writes
`rank.incoherent(kept, step_requires)` as prose with no runnable form.

**What an agent actually does at Step 4:** improvises an order. Nothing constrains it to
`forgo_cost`, nothing pins `locked` to the top, nothing supplies the `protects` sentence, nothing
computes the coherence challenge. The rendered example in `selection.md` is the only specification,
and it is a picture.

The guard that is supposed to catch precisely this — `test_step_costs_reach_the_runtime_and_
something_reads_them`, whose docstring says *"Data nobody reads is this repo's recurring defect"* —
asserts `os.path.isfile(ranker)`, `"def shown_rank(" in src`, and `"selection.md" in SKILL.md`. File
exists, function names exist, doc mentions doc. Presence, not invocation. It cannot fail on this bug.

---

## CRITICAL-2 — The inverted default has no writer. The tail is dropped with no record, and the fail-closed validator certifies it clean.

`selection.md` line 62:

> **Everything below the cut line is skipped, and recorded.** Name, reason, timestamp, in the ledger
> that already exists.

The only thing in this codebase that turns a disposition into a `skips:` entry is the Step 6
generator, and its sole input is `.hitl/first-pass-choices.json`. `selection.md` never mentions that
file. `SKILL.md` Step 6 says it is `# written by Step 4b`. And Step 4b — 40 lines below the
selection — states the opposite default:

> Above tier 1 it is opt-in and the full plan is the default. […] doing nothing still runs the full
> plan — `keep` remains the default disposition (CR-1).

Two adjacent steps of the same skill declare opposite defaults for the same list, and only the
opt-in one has a write path.

**Reproduced** — the real generator extracted verbatim from `SKILL.md`, tier 2, no choices file:

```
$ python3 gen.py development GH-999 issue/999-x 2.9.0 2 .hitl/first-pass-choices.json "" ""
exit=0
$ grep -c "status: open" change-no-choices.yaml
33
$ grep -c "skips:" change-no-choices.yaml
0
$ python3 ci/first-pass/check_skips.py change-no-choices.yaml --workflows ai/shared/workflows.yaml
First Pass skip ledger: clean.
check_skips exit=0
```

A human was told 14 steps are skipped. The change file records 33 steps as `open`, no
`first_pass:`, no `skips:`. `check_skips.py` — the fail-closed validator — returns **clean, exit 0**.

This defeats the validator by construction, not by a hole in it. `check_skips` reasons about
`skipped`/`starter` (needs a record), deletion (`PLAN_PRUNED`/`INCOMPLETE_PLAN`), and an absent
`first_pass` flag with lightened steps (`FP_UNDECLARED`). It has **no concept of a step left `open`
that will never run** — and `open` is exactly what the new default produces. The honest path (record
the skip) is once again strictly more expensive than the silent one, which is the incentive
inversion `PLAN_PRUNED` was added to close.

The guard, `test_the_selection_keeps_its_load_bearing_rules`, asserts:

```python
assert re.search(r"(?i)below the cut line is skipped, and recorded", sel)
```

It checks that the sentence is in the document. It does not check that anything records.

---

## HIGH-1 — A floor step sorts into the collapsed tail at tier 3. Both guards stay green.

`rank_plan` derives `locked` with a **direct dict lookup**:

```python
crit = (s.get("crit_by_tier") or {}).get(tier, s.get("crit", "standard"))
locked = crit == "floor" or bool(s.get("no_omit"))
```

`check_skips.resolve_crit` — which the generator deliberately imports rather than reimplement,
commenting *"two copies of this rule is how a floor step quietly becomes skippable"* — takes the MAX
over every `crit_by_tier` key **≤ tier**, because "criticality may only RISE with tier". `rank.py` is
the second copy, and it disagrees:

```
$ # for every workflow x tier, compare rank_plan's `locked` to resolve_crit's floor
  development tier=3 integration_verify: rank_plan locked=False resolve_crit=floor
  development tier=4 impact:             rank_plan locked=False resolve_crit=floor
  development tier=4 packet:             rank_plan locked=False resolve_crit=floor
  development tier=4 arch_review:        rank_plan locked=False resolve_crit=floor
  development tier=4 qa_verify:          rank_plan locked=False resolve_crit=floor
  development tier=4 rollout:            rank_plan locked=False resolve_crit=floor
  development tier=4 integration_verify: rank_plan locked=False resolve_crit=floor
```

Then the second half lands. `integration_verify` carries
`engages: {multi_domain: true}`, which never matches a single-domain change, so the unlock is
immediately followed by a demotion from `high` to `medium`:

```
$ rank_plan(development, costs, tier=3, paths=["scripts/demo.sh"], profile="fix", tags=["chore"])
--- tier 3: 9 locked, 25 offered/tail ---
   pos 11 integration_verify   rank=medium  TAIL(skipped by default)

--- tier 4: 4 locked, 30 offered/tail ---
   pos  9 packet               rank=medium  TAIL(skipped by default)
   pos 16 integration_verify   rank=medium  TAIL(skipped by default)
```

Position 11 of 25 unlocked, past a cut line `selection.md` sets at six to eight. A **floor** step, at
the tier the skill tells you to default up to, inside the collapsed tail that is skipped by default.
Tier 4 is worse than tier 3: the highest tier unlocks the most floor steps.

**Neither guard covers this.** `test_rank.py::test_modulation_never_moves_a_locked_step` passes
`locked=True` to `shown_rank` by hand — it tests the pin, never `rank_plan`'s derivation of it.
`test_wiring.py::test_a_floor_step_is_never_ranked_below_high` reads the catalog YAML and explicitly
excuses `crit_by_tier` steps, with this rationale:

> A step that is floor at tier 3 alone (packet, impact, qa_verify...) is LOCKED at that tier — it
> never appears in the rankable list there

That sentence is the invariant the code violates. The guard states the rule, then declines to check
it, on the strength of an assumption about `rank_plan` that `rank_plan` does not honour.

**Mutation confirming the hole is general** — delete the floor half of the lock entirely:

```
$ sed: locked = crit == "floor" or bool(s.get("no_omit"))  ->  locked = bool(s.get("no_omit"))
$ python3 -m pytest ci/first-pass/test_rank.py ci/wiring -q
242 passed, 4 skipped
```

`deploy` and `promote` — floor at every tier, "never demote" per `SKILL.md` — become ordinary
unticked checkboxes and the full suite stays green. `test_locked_steps_sort_first_...` survives
because `red`/`green` (`no_omit`) keep the `locked` list non-empty; it asserts locked steps lead, not
*which* steps are locked.

---

## HIGH-2 — The incident-registry raise never fires on any HITL project.

`risky_domains()` reads:

```python
for d in ((manifest or {}).get("domains") or []):
    if isinstance(d, dict) and d.get("name"):
        doms[d["name"]] = [p for p in (d.get("paths") or []) ...]
```

That is a **list of `{name, paths}`**. Every manifest HITL ships is a **mapping of name → {…,
`files`: […]}**. Iterating a dict yields strings, so `isinstance(d, dict)` is False for every entry
and `doms` is always empty.

**Reproduced against the repo's own shipped example manifest and incident-registry template:**

```
$ python3 -c "... rank.risky_domains(greenfield/system-manifest.yaml, incident-registry-template.yaml)"
manifest domains type: dict -> ['auth', 'catalog', 'orders']
incident domains named: ['publishing']
risky_domains(real manifest, real registry) = {}
touches_risky(['app/controllers/auth.py'], risky) = False
with an incident in 'auth': {} -> False
shape risky_domains expects works: True     # only for domains: [{name, paths}], which HITL has nowhere
```

`ai/shared/templates/change-context.schema.yaml` confirms the other candidate input is wrong too:
`manifest.domain` is a **string**, and `manifest.path` points at `docs/system-manifest.yaml` — the
mapping shape. The only place in the repo carrying `domains: [{name, paths}]` is this repo's own
hand-written `.hitl/current-change.yaml`, and the domain it names is `release-2.9.0`, which no
incident registry will ever reference.

So the "up one when the change touches a burned domain" modulation — the *only* signal that pushes a
step **up** into the offered band — is dead for every project. The demotion path works; the
promotion path does not. The asymmetry is entirely in the direction of dropping more steps.

`test_rank.py`'s only coverage is `assert R.risky_domains(None, None) == {}` — the degraded case,
whose output is identical to the bug. `test_an_incident_in_the_area_raises_one_rank` passes
`risky_domain=True` straight into `shown_rank`, jumping over both functions. The plumbing is
untested end to end.

*Related, smaller:* `touches_risky` is prefix-only (`dp.rstrip("*").rstrip("/")`), so even with a
correct manifest, any domain path with a non-trailing glob silently never matches:

```
  domain path 'src/**'                 vs 'src/api/x.py'           -> raise=True
  domain path 'src/api/*.py'           vs 'src/api/x.py'           -> raise=False
  domain path '**/handlers/**'         vs 'src/handlers/x.py'      -> raise=False
  domain path 'services/*/src/**'      vs 'services/auth/src/x.py' -> raise=False
  domain path '*.tf'                   vs 'main.tf'                -> raise=False
```

---

## HIGH-3 — The new tier-2+ refusal is dead code, and every unrecognised value fails open.

```python
trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1", "true", "yes")
if trivial and tier >= 2 and not (tier_set_by.strip() and tier_reason.strip()):
    sys.exit("no source under a manifest domain is touched, so tier %d needs TIER_SET_BY ...")
```

**Nothing sets `TRIVIAL_SHAPE`.**

```
$ git grep -n "TRIVIAL_SHAPE"
ai/claude/start-change/SKILL.md:234:# ... TRIVIAL_SHAPE comes from the probe in right-sizing.md.
ai/claude/start-change/SKILL.md:235:trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1", "true", "yes")
ai/claude/start-change/SKILL.md:242:             "default. See right-sizing.md; TRIVIAL_SHAPE=0 if the probe is wrong." % tier)
ci/wiring/test_wiring.py:539:    assert "TRIVIAL_SHAPE" in body, (
```

Three hits: the reader, a comment, and its own error message. Plus the guard. `right-sizing.md` —
which the comment says the value "comes from" — never mentions it. The Step 6 bash block never
exports it. In every documented path the variable is unset and the refusal cannot fire.

**Reproduced against the real generator** (extracted verbatim from `SKILL.md`), tier 2, no
attribution:

```
--- TRIVIAL_SHAPE=<unset> tier=2 ---   exit=0   wrote 52 lines
--- TRIVIAL_SHAPE=1        tier=2 ---   exit=1   (refusal)
--- TRIVIAL_SHAPE=trivial  tier=2 ---   exit=0   wrote 52 lines
--- TRIVIAL_SHAPE=y        tier=2 ---   exit=0   wrote 52 lines
--- TRIVIAL_SHAPE=yes      tier=2 ---   exit=1   (refusal)
--- TRIVIAL_SHAPE=non-source tier=2 ---  exit=0  wrote 52 lines
--- TRIVIAL_SHAPE=TRUE     tier=2 ---   exit=1   (refusal)
```

`trivial`, `y`, `non-source` — every plausible near-miss fails **open**. Compare the tier parse eight
lines above, which fails **closed** on anything unparseable. The documented escape hatch is
`TRIVIAL_SHAPE=0`; every typo of every other value is a silent equivalent.

**Guard defeated by mutation:**

```
$ sed: os.environ.get("TRIVIAL_SHAPE", "")  ->  os.environ.get("TRIVIAL_SHAPE_ENABLE", "")
$ python3 -m pytest ci/wiring -q
229 passed, 4 skipped
```

`test_both_departures_from_the_proposed_tier_are_attributed` asserts the substring `"TRIVIAL_SHAPE"`
(a prefix of the new name) and regexes the `if trivial and tier >= 2 and not` line, which is
untouched. The guard is structurally unable to check that anything sets the variable it protects.

*Credit where due:* the guard uses `_read`, not `_flat`, so a hard-wrap inside the condition makes it
**fail**, which is the safe direction. The line-break attack does not work here.

---

## MEDIUM-1 — `step_costs` covers one workflow of eight. The other seven collapse a tail ranked by nothing.

`selection.md` and `SKILL.md` Step 4 are workflow-agnostic. `step_costs`/`step_requires` are not:

```
development:       34 steps,  0 with no step_costs entry
brownfield:        11 steps, 10 with no entry
migration:          9 steps,  9
migration_review:   5 steps,  5
docs:               6 steps,  4
prd:                5 steps,  5
platform:          17 steps, 17
release:           12 steps, 12
```

A missing entry means `forgo_cost` defaults to `medium` and `protects` is `""`. With every rank
equal, ties keep catalog order, so **the collapsed tail is simply the last steps of the workflow**,
each offered with a blank "what you'd lose" column:

```
== release ==                                == platform ==
   5 rc_scope      medium  protects=''         13 cutover_plan   medium  protects=''
   9 tag           medium  protects=''         14 dual_run       medium  protects=''
  10 announce      medium  protects=''         15 decommission   medium  protects=''
  11 retire        medium  protects=''         16 delivery_ready medium  protects=''
```

`platform`'s `delivery_ready` gate and `brownfield`'s `create_issue`/`confirm_ready` land in a tail
that is skipped by default with no sentence beside them. The `release` workflow — the one that ships
this release — has zero coverage.

`test_every_step_declares_what_it_protects_and_what_skipping_costs` compares `step_costs` against
`catalog["spine"]["steps"]` only. Spine ≈ development. Coverage is asserted for one eighth of the
surface the feature applies to.

*Also:* four `step_costs` keys (`pentest`, `baseline`, `sec_design`, `cve_audit`) appear in **no**
runtime workflow. `test_rank.py::test_modulation_never_moves_a_locked_step` explicitly picks
`pentest` as *"the case the pin exists for"* — proving the pin on a step that can never appear in a
plan.

---

## MEDIUM-2 — The floor holds against the bare attempt and yields to two strings.

Priority 3 asked for both halves. Honest result:

**Without a name or a waiver — blocked.** Correct.

```
=== A-floor-bare.yaml ===   (integration_verify declined, actor only)
[BLOCK] FLOOR_NO_ACK: floor step 'integration_verify' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_WAIVER: floor step 'integration_verify' maps to a hard gate but has no waiver_ref
exit=2
```

**With a waiver that does not exist — clean.** `check_skips` tests `_str(...).strip()` truthiness and
nothing else. No registry, no resolution, no existence check anywhere in the repo.

```
=== B-floor-fake.yaml ===   actor: claude, ack_by: "the team", reason: "n/a", waiver_ref: "TBD"
First Pass skip ledger: clean.
exit=0

=== C-agent-actor.yaml ===  docs declined, actor: "claude-opus-5", reason: "."
First Pass skip ledger: clean.

=== D-tier3.yaml ===        impact + packet + rollout (all floor at tier 3) declined,
                            actor: agent, ack_by: agent, reason: "x"
First Pass skip ledger: clean.
```

Through the real pipeline, the generator does not enforce the floor at all — it writes
`crit: floor` and moves on. Only Step 6b catches it, and Step 6b is a skill instruction with no hook
behind it:

```
$ choices: {"integration_verify": {"disposition":"decline","reason":"n/a"}}
generator exit=0
  - { step: integration_verify, crit: floor, actor: "ci-bot", reason: "n/a", ... }
$ python3 ci/first-pass/check_skips.py ...
[BLOCK] FLOOR_NO_ACK / FLOOR_NO_WAIVER    exit=2

$ choices: {... "ack_by":"ci-bot", "waiver_ref":"none"}
First Pass skip ledger: clean.   exit=0
```

`ack_by: ci-bot`, `waiver_ref: "none"`. A CI account acknowledging a risk, against a waiver named
"none". The mechanism is unchanged in this release — but 2.9.0 is what makes it *reachable from the
selection view for the first time* ("That is the skip ledger's existing machinery, reachable from
here for the first time"), converting a hand-authored-ledger weakness into a click-through path.

**Guard defeated:** rewrite `selection.md` to abolish the waiver requirement outright —

```
-**The floor can be unticked.** ... take a name against it, and a linked waiver where the step maps
-to a hard gate.
+**The floor can be unticked** like anything else. No waiver is needed; just tick the box and move on.

$ python3 -m pytest ci/wiring -q
229 passed, 4 skipped
```

`assert re.search(r"(?i)floor can be unticked", sel) and re.search(r"(?i)waiver", sel)` — the
replacement keeps the phrase and contains the word "waiver" (in "No waiver is needed"). The guard
protecting the waiver requirement passes on a document that abolishes it.

---

## MEDIUM-3 — `retired-tests.sha256` records a hash of a `test_rank.py` that was never shipped.

```
$ shasum -a 256 ci/first-pass/test_rank.py
c5addc273a4bbf283bcb4187bdafba66b5dfb1b87e9438ed5dcb964644a3f3c4  ci/first-pass/test_rank.py
$ grep test_rank ci/retired-tests.sha256
3b25391d38cd09344a6a53b998c0a92e0e922c63f4361f0ac06dd752868414f9  test_rank.py
```

The recorded hash is a draft's. `/hitl:dev-update` matches on `hash AND basename`, so the cleanup can
never fire for the file that actually ships; the fallback path instead prints *"kept
ci/first-pass/test_rank.py — same name as a HITL test but different content, so it is yours or you
edited it"*, telling the consumer the shipped file is theirs.

`dev-update` copies `ci/first-pass/*.py` with no test exclusion (lines 143, 247), unlike
`init-project.sh` which filters `! -name "test_*"`. In a product repo the result errors on
collection:

```
$ mkdir -p /tmp/fake/ci/first-pass && cp ci/first-pass/*.py /tmp/fake/ci/first-pass/
$ cd /tmp/fake && git init -q . && python3 -m pytest ci/first-pass/test_rank.py -q
E   FileNotFoundError: .../tools/workflow-catalog/catalog.yaml
!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!
```

That is plugin issue #29 reintroduced — the exact failure the hash manifest exists to prevent.
Whether the built plugin's `shared/ci/first-pass/` actually carries test files I could not verify;
the build script is not in this repo, so treat the blast radius as conditional. The **guard** hole is
not conditional: `test_manifest_ships_and_covers_every_listed_filename` asserts the *filename* has at
least one hash. Never that a hash matches a file HITL currently ships. Presence, not correctness.

---

## LOW — incoherence is challenged and then forgotten

`incoherent()` produces a conversational challenge at intake. Nothing re-runs it against the final
ledger at Step 6b, and the change file records the two skips independently — nothing anywhere says
"green ran with no red behind it". In a framework whose premise is *recorded* exceptions, this
particular exception is the one that leaves no record. Not a refusal argument; a record argument.

Related ambiguity: `selection.md` never says whether a step thinned to a `starter` counts as `kept`.
`red` is `no_omit`, so a `starter` red is the *recommended* answer to the green-without-red
challenge — and depending on how the caller builds the `kept` set, that answer either resolves the
challenge or re-raises it forever.

---

## Priority 4 — Should any of the eleven dependencies have been a refusal?

**No.** Stated plainly, and I looked for a reason to say otherwise.

```
verify_red←red   green←red   verify_green←green   design_plus←red
rerun←review1    reconcile←review1  review2←review1
promote←deploy   figma_compare←figma  roi_30←roi   roi_90←roi
```

`promote` without `deploy` is the only one worth arguing, and it argues itself out: both are `floor`
at every tier and neither is in `HARD_GATE_STEPS`, so reaching that combination already costs two
accountable names. Making coherence the single hard refusal in a framework where the floor itself
yields to a signature would be the inconsistency, not the protection — and a refusal people route
around by dropping the prerequisite *and* the dependent (which `incoherent` correctly treats as
silent, per `test_dropping_both_a_step_and_its_prerequisite_is_fine`) buys nothing.

The design call is right. The gap is that the challenge is never recorded (LOW above), and that
`step_requires` — like `step_costs` — covers only the development spine, so `release`'s
`resolve_findings ← adversarial_review` and every other workflow's real dependency is uncovered.

---

## Areas that are sound

- **`shown_rank`'s `locked` pin.** Removing `if locked: return "high"` fails
  `test_modulation_never_moves_a_locked_step` immediately (`1 failed, 12 passed`). The pentest case
  earns its keep — as a mutation guard, if not as a realistic step.
- **`incoherent()` cannot be turned into a blocker unnoticed.** Replacing its body with `sys.exit`
  on the `promote`-without-`deploy` case evades the `"raise" not in src` check but fails
  `test_it_challenges_rather_than_blocks` (`1 failed, 241 passed`). The two guards cover each other.
- **`engaged()`'s absent/empty handling.** `None`, `""`, `"always"`, `{}`, and a dict whose criteria
  lists are all empty all return engaged. No silent demotion via a vacuous `engages` block.
- **`engages` globs.** All fourteen shipped path globs match a realistic file, via `fnmatch` or the
  `**/` → `*` fallback. No dead glob in the catalog.
- **`check_skips` against forged ledgers.** Bare floor skip, unknown status, unknown step, wrong
  workflow id, duplicate keys, deleted steps — all fail closed as documented. The validator is not
  where this release breaks; it is bypassed by never being handed anything to validate.
- **`_flat`.** The hard-wrap defeat is genuinely closed for the doc guards that use it, and the code
  guards correctly use `_read` so a wrap fails safe.

---

## Smallest change that would fix it

Two lines of wiring and one import. In priority order:

1. **Give `rank.py` a `__main__`** (workflow id, tier, paths, profile, tags → printed ranked list)
   and make `selection.md` actually run the `$RANK` it already resolves. Without this, nothing else
   in the release executes.

2. **Make the selection write `.hitl/first-pass-choices.json`.** The writer, the schema, the
   generator and the validator all exist and all work — the selection just has to emit into them.
   Every unticked step, tail included, becomes a `decline` entry with the confirming human as
   `actor`. Then delete the Step 4b sentence "Above tier 1 it is opt-in and the full plan is the
   default", which the new Step 4 contradicts.

3. **In `rank_plan`, replace the direct lookup with the shared resolver:**
   ```python
   from check_skips import resolve_crit
   locked = resolve_crit(s, tier) == "floor" or bool(s.get("no_omit"))
   ```
   Two copies of this rule is, in the generator's own words, how a floor step quietly becomes
   skippable. This is the second copy.

Then, before the next candidate: point `risky_domains()` at the manifest shape HITL ships
(`domains: {name: {files: [...]}}`) and give it a positive test; set `TRIVIAL_SHAPE` in the
`right-sizing.md` probe and make an unrecognised value fail closed like the tier parse beside it;
extend `step_costs`/`step_requires` past the development spine or scope the selection view to
`development` explicitly; and re-hash `test_rank.py` in `retired-tests.sha256`.

And three guards need a direction change, from "the sentence is present" to "the behaviour happens":
`test_the_selection_keeps_its_load_bearing_rules`, `test_both_departures_from_the_proposed_tier_are_
attributed`, and `test_manifest_ships_and_covers_every_listed_filename`. Each was defeated above by a
mutation that left the whole suite green.

**DO NOT SHIP.**
