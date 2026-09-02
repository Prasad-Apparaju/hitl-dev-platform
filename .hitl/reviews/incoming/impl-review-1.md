# Right-sizing (#97) — implementation review

Ran the real path in a scratch dir: wrote two impact records, sized both, generated a stub, generated
a change file, certified with `check_skips`. All 167 existing tests pass (`test_check_skips` 67,
`test_size_plan` 17, `test_first_pass_lib` 51, `test_driver_e2e` 32, `ci/wiring` 51).
`derive.py verify` is OK, catalog and `workflows.yaml` `step_costs` agree on all 38 steps, `impact`
is out of the development plan, `retro` is in, count 34. The floor sizes match the design exactly:
5 locked at tier 1, 6 at tier 2, 10 at tier 3. `RULE_OVER_FLOOR` fires as designed — marking `deploy`
`not_applicable` printed `[BLOCK] RULE_OVER_FLOOR ... a rule may not retire it`, exit 2.

Five things, ranked.

## 1. The generator refuses the disposition the whole feature adds. This stops it working.

`size_plan.excluded()` says its output "become[s] `not_applicable` ledger entries". Step 4b of
`start-change` says the same. `check_skips.DISPOSITIONS` accepts it. `gen_change.py` does not:
`STATUS_FOR = {"defer", "decline", "starter"}`.

Fed the 20 exclusions from a sized fast track into `.hitl/first-pass-choices.json` and ran Step 6's
generator:

```
choice for 'figma' has disposition 'not_applicable'; expected one of ['decline', 'defer', 'starter']
(or 'keep' to leave the step alone).
gen exit=1
```

Step 6's wrapper treats a non-zero exit as "write nothing and exit 1", so every right-sized change
dies at Step 6 with no change file. The certification side is fine — I hand-wrote the identical
ledger (20 `not_applicable` entries, steps marked `skipped`) and `check_skips` printed
`First Pass skip ledger: clean.` exit 0. Only the generator is missing it, and no test covers the
generator with a rules-excluded choice.

## 2. The sizer never receives the confirmed tier, so every change sizes at tier 3. This stops it working, silently.

`size_plan.main` does `tier = rec.get("tier", 3)`. `impact-record.schema.yaml` defines no `tier`
field, and `apply-change` is explicitly told not to write one ("Intake writes the stub before calling
this skill, and fills in the tier and the plan after it returns. Two writers for one file is how a
tier set here and a tier set there disagree"). Step 4's invocation passes no tier and the CLI has no
flag for one. So a schema-conformant record always falls back to 3.

Same findings, same file, with and without a hand-added `tier: 1`:

```
rec.yaml (tier: 1)   fast=14  locked=5   excluded=20
rec_notier.yaml      fast=17  locked=10  excluded=17
```

The schema-conformant record locks `packet`, `arch_review`, `qa_verify`, `rollout` and
`integration_verify` on a one-line fix with no dependents and no interfaces — the tier-3 floor
applied to a tier-1 change. That is the over-ceremony on the light path the feature exists to remove,
and it arrives without a message. `size()` takes `tier` as a parameter and the unit tests pass it, so
the gap lives only in the CLI and the skill's call.

## 3. Step 6 destroys the stub, and nothing enforces the impact record. This stops it working.

The stub's stated purpose is to persist the agreed requirement and definition of done and to name the
impact record. Step 6 `mv`s the generator's planning output over `.hitl/current-change.yaml`. Dumped
its top-level keys:

```
['schema_version','hitl_version','change_id','tier','tier_set_by','tier_reason','status',
 'expected_branch','first_pass','workflow','skips','current_step']
has requirement: False   has impact_record: False
```

So the requirement and DoD agreed at Step 3b are gone by Step 6, and the record pointer with them.
Separately, `grep -rn impact_record` over `*.py`/`*.sh`/`*.yaml` returns exactly two non-test hits:
the stub emit and a schema comment. There is no finding code for it. The design says "if the named
record is missing or empty, that blocks"; the schema header says the same; `gen_change.py`'s own
comment says the stub "names the impact record so the blocking reference check has a subject". That
check does not exist. Neither does the DoD-line-to-criterion coverage check the design blocks Build
on — and after Step 6 it would have no DoD to read.

## 4. The sizer ignores the record's workflow and always sizes against `development`. Worth deciding.

`size_plan.main` calls `load_catalog(argv[2])`, whose signature is
`load_catalog(workflows_path, workflow_id="development")`. Handed it a record with
`workflow: brownfield` and got back a development plan — `issue, test_plan, red, verify_red, green,
verify_green, review1, rerun, qa_verify, rollout, verify_pr, deploy, promote, retro` — none of which
are brownfield steps (`map_code, claude_md, manifest, arch_review, ...`). No warning, exit 0. The
design limits the two-option offer to `development`; the CLI does not, and Step 4's call has no
workflow guard around it.

## 5. `needed_now: never` is tier-independent, so a tier-3 fast track still drops two hard gates. Worth deciding.

Walked a tier-3 change through: multi-domain, 3 dependents, one published interface, an event, a data
migration, reaching production, ui+api+data+infra. Fast track 24 steps, full scale 34. The 10 dropped:
`roi, training, adv_design, test_review, design_plus, refactor, conventions, adv_code, roi_30, roi_90`.
`conventions` and `adv_code` are both in `check_skips.HARD_GATE_STEPS`. That ledger certifies clean
(exit 0) because those steps are not floor at tier 3, so no ack and no waiver is asked for. The design
says "risk is handled by the tier and by nothing else ... a high tier locks more, and the gap between
the two options closes on its own." At the highest normal tier the gap is still ten steps, because the
ten are all `needed_now: never`, which no tier can change.

Two minor doc mismatches while here: §4 says `engages` "does not yet do its job. Twenty-one
development steps say `always` ... Every one gets rewritten" — 19 development steps still say
`always`. Harmless, since most are locked or genuinely universal and `needed_now` does the
discriminating, but the doc claims a rewrite that did not happen. And Step 6's
`TIER=2  # from Step 3b — never assume it` points at a step that is now "Restate what you understood,
and write the stub"; the tier is decided at Step 4.

## Ready to ship?

No. The smallest thing that stops it: `gen_change.py` cannot write a `not_applicable` entry, so no
change can get past Step 6. Fixing that alone still leaves every plan sized at tier 3 (#2), which is
the failure mode the feature was built to fix.
