# Release review — HITL 2.9.0

SHA 46271e7818b8dafb423127c7b1601e8e28d32c7d · scope `git diff v2.8.0..HEAD`, 72 files.
Excluded per brief: #101, #102, `total: 31`, two-option choice being `development`-only.

## 1. The shipping path completes

Scratch dir laid out as an onboarded product repo (`ci/first-pass/*.py` + `ci/first-pass/workflows.yaml`,
no `ai/`). Ran, in order:

- `gen_change.py --stub GH-500 issue/500-add-env-var 2.9.0` → stub with `status: intake`, `tier: 3`,
  `tier_provisional: true`, `impact_record: ".hitl/impact/GH-500.yaml"`. `check_skips.py` on it →
  `First Pass skip ledger: clean.` rc=0.
- Hand-wrote `.hitl/impact/GH-500.yaml` to the shipped schema (small config change, no dependents,
  no interfaces, no migration).
- `size_plan.py .hitl/impact/GH-500.yaml 2 fast` → rc=0, `plan 16, excluded 18, outcomes 34, unruled []`.
  `... 2 full` → `plan 22, excluded 12`.
- Built `.hitl/first-pass-choices.json` from the 18 fast exclusions as `not_applicable`.
- `gen_change.py development GH-500 issue/500-add-env-var 2.9.0 2 <choices> "" ""` → rc=0, 7611 bytes,
  valid YAML, 18 `skipped` steps, `command:` on all 34 rows, `current_step.command: "manual"`,
  `requirement` + `impact_record` carried forward from the stub.
- `check_skips.py .hitl/current-change.yaml` → `First Pass skip ledger: clean.` rc=0.
- Step 6b `resurface.py --append` → `Recorded 18 skip(s) as project-wide`, rc=0; re-certifying with
  `--rollup` → clean.
- Same run taking full scale instead (12 exclusions) → gen rc=0, certify clean.
- `python3 -m pytest ci/ -q` → **777 passed**. `derive.py verify` → `VERIFY OK`.

## 2. `retro` ships as a floor step with nothing behind it

`ai/shared/workflows.yaml:68` adds `{ n: 29, key: retro, crit: floor, command: guided }`, and
`step_costs.retro` is `engages: always`, `needed_now: always`, `forgo_cost: high`. It is in the locked
set at every tier (that is what makes the CHANGELOG's 5/6/10 counts correct), so no rule can drop it
and `RULE_OVER_FLOOR` blocks `not_applicable` on it. Getting past it requires a floor risk-accept:
`ack_by` plus, for a gate step, `waiver_ref`.

`find ai/claude -ipath '*retro*'` → nothing. `grep -rn retro ai/` finds only the catalog line and three
sentences of prose in `start-change/SKILL.md`. `grep -rn rule_outcomes ai/ ci/ tools/` finds the schema,
one prose line, one docstring, and a presence test in `check_skips.py` — nothing reads it. The only
design for it, `docs/design/progress-and-retro/01-design.md`, added in this same diff, reads
`**Status:** agreed, ready to build` / `the retrospective is #98`.

So the statusline will say `→ say go, Claude walks it` on a step nothing walks, on every change; and
the CHANGELOG's stated correction mechanism — "The sizing rules will be wrong at first. The closing
retrospective is what corrects them" — is a `guided` step with no content and no consumer of the data
it would correct from.

## 3. CHANGELOG claims

Checked against the shipped catalog, not accepted.

**Verified.** "12 steps of 34, against 23" and "22, against 31" both reproduce exactly, using the
test file's own SMALL/BIG findings against `ai/shared/workflows.yaml` (SMALL at tier 0/1 → 12/23;
BIG → 22/31 at every tier). "Locked floors are 5 at tier 1, 6 at tier 2, 10 at tier 3" → `locked_keys`
returns 5/6/10 (floor-only is 3/4/8; the numbers are the floor ∪ no_omit set). "the plan is 34 steps
either way" → development was 34 in v2.8.0 and is 34 now, `impact` out, `retro` in. "38 catalog steps"
→ `step_costs` has exactly 38 entries. `not_applicable`, `RULE_OVER_FLOOR`, the one resolver, and the
derive-time `command` comparison are all in the code as described.

**Not accurate.**

- *"full scale is the answer set where nothing is dropped."* Full scale dropped 12 of 34 steps in my
  run, all written to the ledger as `not_applicable`. The CHANGELOG's own measured numbers two
  paragraphs earlier (23 of 34, 31 of 34) say the same thing.
- *"The ledger, the validator and the actor rule are unchanged."* `check_skips.py` changed by ~140
  lines in this release: a fourth disposition plus four new non-waivable codes (`RULE_OVER_FLOOR`,
  `INTAKE_NOT_EMPTY`, `TIER_PROVISIONAL`, `IMPACT_RECORD`).
- *"The catalog has declared a command for every step all along."* Only `development` (34/34),
  `platform` (17/17) and `release` (12/12) declare one. `brownfield`, `migration`, `migration_review`,
  `docs` and `greenfield`/`prd` declare zero across 36 steps — and `ai/shared/next-step.md`, shipped in
  this same release, says so: "Five workflows declare no commands at all, so this is normal."
  `git show v2.8.0:tools/workflow-catalog/catalog.yaml | grep -c 'command:'` → 67, not one per step.
- *"the other six workflows have no sizing rules and say so rather than offering two identical lists."*
  `brownfield` has one rule and `docs` two, so neither trips the "Do not offer a choice here" guard.
  `size_plan.py <brownfield record> 2 fast` and `... full` return byte-identical 10-step plans, with only
  the partial warning "10 of 11 steps in 'brownfield' have no sizing rules and are kept".

## 4. Upgrading mid-change leaves two `current` steps and no command hints

Extracted the migration from `ai/claude/update/change-file-migration.md` and ran it on a
v2.8.0-format `development` change sitting on `impact`:

```
  ~ repair   3 roi                current
--- your own steps, carried through (not in the HITL catalog) ---
    impact
```

`impact` is no longer a catalog key, so it is preserved verbatim — still carrying `status: current` —
while the repair marks `roi` current. The migrated file has two `status: current` lines;
`check_skips.py` on it says `First Pass skip ledger: clean.` rc=0, and `hitl_render_trail` renders
`✓Issue ✓Figma ▶ Impact ▶ ROI ·Docs ·IaC ·Tests …`.

Separately, `step_line()` in that migration emits `n, key, label, status, phase, substep` and user
extras only — no `command`. `grep -c 'command:'` on the migrated file → 0, `hitl_current_command` → empty,
`current_step` fallback → empty. The #100 hint is silent for the change a user is actually on after
upgrading; it only appears on changes started fresh under 2.9.0. `retro` is also appended after
`roi_90` (n:29 following n:31), so it renders last in the trail.

## 5. Step 8 still routes back into the skill that already ran

`start-change/SKILL.md:414` still says `development` → `/hitl:dev-apply-change <N>` "(impact analysis →
plan; steps 1–9)". But apply-change *is* the impact analysis now, called at Step 3c. Re-entering it
re-runs its Step 3 and rewrites `.hitl/impact/<change_id>.yaml`. Its Steps 4, 5 and 6 (Documentation
Plan, Test Case Plan, IaC Review) then run with no reference to the plan just agreed — so the fast
track I ran, which recorded `docs`, `iac` and `reconcile` as `not_applicable`, is immediately asked for
a documentation plan and an IaC review.

## 6. The generated command map was not regenerated

`docs/command-map.generated.md` carries "Generated from ... **Do not edit by hand**" and was not touched
in this diff. It still lists `| 3 | Impact Analysis | Design | dev-apply-change |`, has no Retrospective
and no 8a/16a substeps, and every number from 4 on is off by one against what ships. Re-running
`python3 tools/workflow-catalog/derive.py command-map` produces a table differing from the committed
file on 30 of its 41 lines. `derive.py verify` passes — it compares catalog to runtime, not the
generated docs, so nothing gates this.

---

**The smallest thing that stops it: `retro` is a floor step on every change with no skill, no
instruction and no consumer for `rule_outcomes` — every 2.9.0 change ends at a mandatory step that
cannot be performed and can only be exited with a risk-accept waiver.**
