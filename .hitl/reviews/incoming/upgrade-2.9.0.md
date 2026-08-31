# Upgrade review — 2.9.0 RC (9ba9fd2)

Lens: what happens to someone already on 2.8.0, and to the next fresh install.
Base: `git diff v2.8.0..HEAD` on `main`, HEAD = `9ba9fd2da89e5dc46c1f7cb40cacc8141d87e034`.
Every finding below was reproduced. Commands and observed output are inline.

**Verdict: DO NOT SHIP.** Three of the four things the release announces are either unreachable,
contradicted by a second implementation, or contradicted by the page the portal publishes.

---

## Summary

| # | Severity | Finding |
|---|---|---|
| F1 | **HIGH** | The new tier 2+ refusal can never fire. Nothing anywhere sets `TRIVIAL_SHAPE`. |
| F2 | **HIGH** | `rank.py` resolves the floor differently from `check_skips.py`. At tier 3 one floor step, at tier 4 six floor steps, are shown as ordinary unticked choices. |
| F3 | **HIGH** | `site/catalog.html` as committed omits `roi`, `roi_30`, `roi_90` and the whole Post-Ship phase. Regenerating from the catalog it claims to be generated from produces a different page. |
| F4 | MEDIUM | Regression against 2.8.0: the `brief.md` / `permissions.md` / `language.md` references lost their relative path and now resolve against the user's project instead of the plugin. |
| F5 | MEDIUM | The shape probe reports "touches nothing" for every change, by construction — it runs at intake, before the branch and before any code exists. |
| F6 | MEDIUM | `step_costs` covers the development spine only. Six of eight workflows get a selection with every `protects` blank and every rank flattened to `medium` (`release`: 12 of 12). |
| F7 | LOW | `selection.md` gives no way to execute `rank.py`. It has no CLI and the shipped bash resolves `$RANK` and never uses it. |
| F8 | LOW | `ci/retired-tests.sha256` records the wrong hash for `test_rank.py` — an intermediate version that never shipped. |
| F9 | LOW | `selection.md`'s worked floor example uses `pentest`, a step in `step_costs` but in no runtime workflow, so it can never appear in a selection. |
| F10 | LOW | `ai/shared/workflows.yaml` claims `derive.py verify` keeps `step_costs` in step with the catalog. It does not. |

Sound, in one line each — priorities 1, 2, 4, 5 all pass except where noted above:

- **Priority 1 — packaging.** `build.sh` ships all four new files; `init-project.sh`, `/hitl:dev-update`, and all three `dev-start-*` skills carry `rank.py` into a product repo via existing `*.py` globs. No "ships to shared/ with nothing copying it in" gap this time. Verified below.
- **Priority 2 — parsers.** `derive.py verify`, `check_skips.load_catalog`, `ci/breadcrumb/run_matrix.sh` (a hand-rolled line parser, the obvious suspect), the Step 6 generator and the Step 4.5 migration all tolerate the two new top-level blocks. Nothing copies them into a change file.
- **Priority 4 — existing change files.** A 2.8.0-seeded change file migrated to 2.9.0 gains version stamps only; zero `protects` / `forgo_cost` / `step_costs` leakage; the original is left untouched pending confirmation.
- **Priority 5 — the split.** All three new intra-skill links resolve in source and in the built plugin; no reference chains more than one level; nothing was lost except F4.
- `claude plugin validate` passes on the freshly built plugin.
- Full suite green: `python3 -m pytest ci/first-pass ci/wiring tools/workflow-catalog -q` → `395 passed`.

---

## F1 — HIGH — the new refusal is unreachable. Nothing sets `TRIVIAL_SHAPE`.

`ai/claude/start-change/SKILL.md:235` reads the flag from the process environment and its own comment
says where it comes from:

```
# for 3h31m. TRIVIAL_SHAPE comes from the probe in right-sizing.md.
trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1", "true", "yes")
```

`right-sizing.md` contains no such assignment. Its probe is a bare `git diff --name-only` whose output
a human reads. The Step 6 bash block that invokes the generator does not export it either.

```
$ grep -rn "TRIVIAL_SHAPE" . | grep -v '^./.git/' | grep -v session-logs
ci/wiring/test_wiring.py:539:    assert "TRIVIAL_SHAPE" in body, (
ai/claude/start-change/SKILL.md:234:# for 3h31m. TRIVIAL_SHAPE comes from the probe in right-sizing.md.
ai/claude/start-change/SKILL.md:235:trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1", "true", "yes")
ai/claude/start-change/SKILL.md:242:             "default. See right-sizing.md; TRIVIAL_SHAPE=0 if the probe is wrong." % tier)
```

Three hits: the read, its own error string, and a wiring test. **Zero writes.**

Reproduced by extracting the generator verbatim (the way `test_driver_e2e.py` does) and running it
both ways:

```
$ python3 gen.py development GH-1 issue/1-x 9.9.9 2 absent.json "" ""
EXIT=0            # tier 2, no attribution, no refusal — the shipped path
$ TRIVIAL_SHAPE=1 python3 gen.py development GH-1 issue/1-x 9.9.9 2 absent.json "" ""
no source under a manifest domain is touched, so tier 2 needs TIER_SET_BY and TIER_REASON. ...
```

The refusal is correct code. It is reached only by someone who already knows the variable exists and
types it by hand. Bash-tool shell state does not persist between calls, so an export in an earlier
probe call cannot reach the generator either.

**The wiring test is complicit.** `test_both_departures_from_the_proposed_tier_are_attributed`
(`ci/wiring/test_wiring.py:530`) asserts `"TRIVIAL_SHAPE" in body` and that the `if trivial and tier
>= 2` line is present. Both are true. Neither asserts anything *sets* the variable — the exact
end-to-end gap `ci/wiring` was created to close, reproduced inside `ci/wiring` itself.

**Therefore the CHANGELOG's "Note for existing projects" is false.** "One thing newly refuses: a tier
2 or higher declared on a change whose diff touches no source under a manifest domain, with no
`tier_set_by`/`tier_reason`" — nothing newly refuses. An upgrader is being warned about a behaviour
change that will not occur.

---

## F2 — HIGH — `rank.py` and `check_skips.py` disagree about the floor at tier 3 and 4.

The Step 6 generator refuses to duplicate this rule, and says why:

> Criticality must be resolved the SAME way the validator resolves it, so import it rather than
> reimplement it here — two copies of this rule is how a floor step quietly becomes skippable.

`rank.py:rank_plan` is that second copy:

```python
crit = (s.get("crit_by_tier") or {}).get(tier, s.get("crit", "standard"))
locked = crit == "floor" or bool(s.get("no_omit"))
```

An **exact** key lookup. `check_skips.resolve_crit` takes the **max over every `crit_by_tier` key
`<= tier`**, deliberately, so criticality can only rise with tier. The catalog encodes
`integration_verify` as `crit_by_tier: { 2: floor }` and five steps as `{ 3: floor }`, so an exact
lookup misses at every tier above the one named.

```
$ python3 - <<'EOF'
import sys, yaml; sys.path.insert(0,"ci/first-pass")
import rank, check_skips as C
d=yaml.safe_load(open("ai/shared/workflows.yaml"))
steps=d["workflows"]["development"]["steps"]; costs=d["step_costs"]
meta={s["key"]:s for s in steps}
for tier in (2,3,4):
    r={x["key"]:x for x in rank.rank_plan(steps,costs,tier=tier)}
    bad=[k for k,m in meta.items() if C.resolve_crit(m,tier)=="floor" and not r[k]["locked"]]
    print("tier %d: validator says floor but the selection shows it UNLOCKED -> %s" % (tier,bad))
EOF
tier 2: validator says floor but the selection shows it UNLOCKED -> []
tier 3: validator says floor but the selection shows it UNLOCKED -> ['integration_verify']
tier 4: validator says floor but the selection shows it UNLOCKED -> ['impact', 'packet', 'arch_review', 'qa_verify', 'rollout', 'integration_verify']
```

Tier 3 is the tier the skill tells people to default to. `selection.md` promises "Floor steps at this
tier and `no_omit` … lead the list as already-on, each with its one-line reason", and separately that
unticking a floor requires naming the loss and taking a waiver. At tier 3, `integration_verify` gets
neither: it appears in the offered block as a plain checkbox with no lock reason and no waiver
prompt. The person is walked into a skip the fail-closed validator will later reject — the ledger
still catches it, but the view has already told them it was a free choice.

This also falsifies the CHANGELOG's "**never past the floor**" and `rank.py`'s own docstring
("never past the floor — modulation reorders the list, it does not unlock a floor step").

Smallest fix: `rank_plan` should call `check_skips.resolve_crit(s, tier)` rather than index
`crit_by_tier` itself, with the same tolerant fallback `rank.py` already uses for missing data.

---

## F3 — HIGH — the published catalog page omits three shipped steps and a whole phase.

`site/catalog.html` at HEAD advertises itself as "generated from the same catalog file the running
system executes, so this page cannot drift from reality." It has drifted.

```
$ git worktree add -q --detach $W/wt HEAD && cd $W/wt
$ python3 tools/scripts/generate-catalog-page.py
wrote site/catalog.html (99 step rows)
$ diff /Users/Prasad_1/Projects/hitl-dev-platform/site/catalog.html site/catalog.html
118c118
<     ... <b>8 workflows</b> · 93 steps + 3 substeps ...
---
>     ... <b>8 workflows</b> · 96 steps + 3 substeps ...
126,127c126,127
< <!-- generated from tools/workflow-catalog/catalog.yaml · 8 workflows · 96 step rows -->
< ... <span class="wfmeta">28 steps + 3 substeps · 6 phases</span>
---
> <!-- generated from tools/workflow-catalog/catalog.yaml · 8 workflows · 99 step rows -->
> ... <span class="wfmeta">31 steps + 3 substeps · 7 phases</span>
```

Which steps are missing from the committed page:

```
$ python3 -c "... compare <code>key</code> cells against ai/shared/workflows.yaml ..."
runtime keys missing from the published page: ['roi', 'roi_30', 'roi_90']
```

`roi`, `roi_30` and `roi_90` are present in `tools/workflow-catalog/catalog.yaml` (lines 35, 73, 74),
present in `ai/shared/workflows.yaml` (lines 40, 69, 70), and `derive.py verify` passes. Only the HTML
lost them, along with the entire Post-Ship phase.

Traced to `2bf80e5`, whose own commit message opens *"Chasing 'drop ROI in priority' found why the
customer's one-line change ran the full 31 steps"* — the page was regenerated while ROI was
experimentally removed from the catalog, the catalog was restored, the page never was.

No gate catches this. `ci/workflows/workflow-model.yml` runs `derive.py verify` and the deriver tests;
neither touches the HTML. `test_the_portal_agrees_with_itself_about_the_current_version` checks
version strings only. A fresh install reads the public catalog and is told three steps that will
appear in their plan do not exist.

Fix: re-run `python3 tools/scripts/generate-catalog-page.py` and commit; ideally add the regeneration
diff to the workflow-model CI job.

---

## F4 — MEDIUM — regression: three plugin-relative links became project-relative.

2.8.0's SKILL.md carried working relative links. Built from the v2.8.0 tag:

```
$ CLAUDE_BIN=/bin/true $W/plug280/scripts/build.sh $W/src   # $W/src = worktree at v2.8.0
$ grep -n "first-pass/brief" $W/plug280/skills/dev-start-change/SKILL.md
203:Run the change under **brief mode** ([`shared/first-pass/brief.md`](../../shared/first-pass/brief.md) —
```

From `skills/dev-start-change/`, `../../shared/first-pass/brief.md` resolves to
`<plugin>/shared/first-pass/brief.md`, which `build.sh` does ship (`ls shared/first-pass/` →
`brief.md language.md permissions.md`). Correct.

The Step 4b extraction into `first-pass-choices.md` dropped the link targets. Built from HEAD:

```
$ grep -n "first-pass/brief\|first-pass/permissions\|first-pass/language" \
    $W/plug/skills/dev-start-change/first-pass-choices.md
43:Run the change under **brief mode** (`shared/first-pass/brief.md` —
45:(`shared/first-pass/permissions.md`); use the neutral /
46:respectful language in `shared/first-pass/language.md`.
```

Bare, unprefixed, un-anchored. `build.sh`'s pass-2 prefixes only `shared/templates/`,
`skills/dev-practices/`, `skills/dev-apply-change/` and the four names in `SHARED_PROSE`
(`challenge-stance`, `adversarial-review`, `skip-record`, `personas`). `shared/first-pass/*` is in
none of them, so the path ships verbatim and resolves against the user's project, where nothing
exists. This is precisely the failure `build.sh`'s own comment records: *"A hardcoded per-file list is
how adversarial-review.md shipped with a bare path that resolved against the user's project."*

Fix: restore `](../../shared/first-pass/brief.md)` etc. in `first-pass-choices.md`, or add
`brief.md permissions.md language.md` to `SHARED_PROSE`.

---

## F5 — MEDIUM — the shape probe can never see the change.

`right-sizing.md`'s probe:

```bash
BASE="${BASE:-main}"
git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null | sed -n '1,200p'
```

It is invoked at Step 3b/Step 4. `## Step 5 — Create the branch` is where the branch is cut, and no
code has been written at any point before Step 6. On a checkout sitting on or freshly branched from
`main`, `merge-base(HEAD, main) == HEAD`, so the diff is empty by construction:

```
$ git init -b main r; ... commit; git checkout -qb issue/1-x
$ BASE=main; git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null
                                            # (no output)
```

Read against the guidance table — "the diff touches: non-source only → propose tier 0 or 1, reason
pre-filled" — the honest answer for **every** change at intake is "non-source only". Combined with
Step 4b's new "at tier 0 or 1, offer it without being asked, ceremony steps pre-selected as declined,
one confirmation for the lot", the shipped default reading is: propose tier 1 and pre-decline the
ceremony for everything. That is a downgrade default wearing a right-sizing label — the inverse of
the guard the release says it added.

Two secondary defects in the same three lines:

```
$ # repo whose default branch is master, BASE unset so it defaults to main
$ BASE=main; git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null
fatal: Not a valid object name main
                                            # (git diff prints nothing)
```

`2>/dev/null` is a redirection on `git diff`; the command substitution's stderr is not covered, so the
`fatal:` leaks. The substitution collapses to empty, the argument becomes `..HEAD`, which git resolves
as `HEAD..HEAD` and exits 0 with no output. Failure is indistinguishable from "touches nothing", and
"touches nothing" is the answer that proposes the lightest tier. Same for a first commit with no
merge-base.

Fix: run the probe against the *request*, not the diff, or hard-fail when `git merge-base` fails
rather than falling through to an empty list.

---

## F6 — MEDIUM — `step_costs` covers one workflow of eight.

```
$ python3 -c "... yaml.safe_load('ai/shared/workflows.yaml') ..."
step_costs entries: 38
distinct step keys across all workflows: 87
development steps with NO step_costs entry: []
step_costs keys not in any workflow: ['baseline', 'sec_design', 'cve_audit', 'pentest']
ALL steps missing step_costs (53): ['adversarial_review', 'announce', 'build', ... 'write_review']
```

Run through the ranker:

```
$ python3 -c "import rank; rank.rank_plan(steps, costs, tier=2, ...)"
development  steps=34  blank protects= 0
release      steps=12  blank protects=12
brownfield   steps=11  blank protects=10
```

`rank.py` degrades correctly — `entry = costs.get(key) or {}`, so `protects` is `""` and `forgo_cost`
defaults to `medium`, no exception. But the feature is gone: for `release`, `brownfield`, `migration`,
`migration_review`, `docs`, `prd` the selection shows a list where the "what you'd lose" column is
empty on every row and the ranking is flat. `selection.md` describes a view that only exists for the
development spine, and says nothing about the other six.

The `release` workflow is the one HITL's own maintainers run. Nothing in Step 4 or `selection.md`
tells them why their selection is blank.

CHANGELOG claim "**`protects` and `forgo_cost` for all 38 steps**" is literally true about the count
and misleading about coverage: 38 entries exist, of which 4 name steps in no runtime workflow, and 53
of the 87 real step keys have neither field.

---

## F7 — LOW — nothing can actually run `rank.py`.

`selection.md` says "`ci/first-pass/rank.py` (plugin fallback `$ROOT/shared/ci/first-pass/rank.py`)
does this", then ships:

```bash
RANK="ci/first-pass/rank.py"; [[ -f "$RANK" ]] || RANK="$ROOT/shared/ci/first-pass/rank.py"
git diff --name-only "$(git merge-base HEAD "${BASE:-main}")"..HEAD 2>/dev/null | head -200
```

`$RANK` is resolved and never used. The block runs the probe and stops.

```
$ grep -n "__main__\|argparse\|def main" ci/first-pass/rank.py
  (no matches)
```

`rank.py` is import-only with no CLI, and `selection.md` shows no import either — the next paragraph
is prose ("Pass it the changed paths, the profile and tags…"). The `$ROOT` resolution survives the
build correctly (`@@KEEP_` protection works, verified in the built plugin at `selection.md:22`), so
the packaging is right and the invocation is missing. Related to F1: a second module wired to a
resolved path that nothing calls.

---

## F8 — LOW — the retired-test hash is for a version that never shipped.

```
$ shasum -a 256 ci/first-pass/test_rank.py
c5addc273a4bbf283bcb4187bdafba66b5dfb1b87e9438ed5dcb964644a3f3c4
$ grep test_rank ci/retired-tests.sha256
3b25391d38cd09344a6a53b998c0a92e0e922c63f4361f0ac06dd752868414f9  test_rank.py
$ for c in $(git log --format=%H v2.8.0..HEAD -- ci/first-pass/test_rank.py); do \
    echo "$c $(git show $c:ci/first-pass/test_rank.py | shasum -a 256 | cut -d' ' -f1)"; done
b3c3924... c5addc27...    # HEAD version
f33b3f05... 3b25391d...   # intermediate, superseded by b3c3924
```

The ledger records the `f33b3f0` intermediate. Low impact — `build.sh`, `hitl_copy_tools` and
`dev-update` all exclude `test_*`, so `test_rank.py` never reaches a product repo and the delete list
entry added at `ai/claude/update/SKILL.md:312` never has a file to act on. But the file's own header
says it holds "sha256 of every version of every test file HITL has ever synced", and it now holds a
hash of something that was never synced and lacks the one it would need.

---

## F9 — LOW — the worked floor example uses a step that cannot appear.

`selection.md` illustrates the "floor can be unticked" rule with:

> Unticking **pentest**. This change touches auth, so nothing else in the plan looks for a privilege
> bug. Who is accepting that, and against which waiver?

`pentest` is in `step_costs` and in no workflow (see F6 output). Since the generator copies the
`development` block verbatim and profiles are — per this very release — advice rather than a filter,
`pentest` can never be in a plan, so this exchange can never happen. Same for `baseline`,
`sec_design`, `cve_audit`. The one worked example of the release's most safety-critical rule is
unreachable.

---

## F10 — LOW — `workflows.yaml` names a gate that does not check it.

`ai/shared/workflows.yaml` header: *"Generated from tools/workflow-catalog/catalog.yaml — `derive.py
verify` and ci/wiring keep the two in step."*

```
$ cp tools/workflow-catalog/catalog.yaml $W/cat.yaml   # then rewrite one `protects` string
$ python3 tools/workflow-catalog/derive.py verify --catalog $W/cat.yaml
VERIFY OK: numberless catalog reproduces runtime for spine->development, ...
EXIT=0
```

`derive.py` contains no reference to `step_costs` or `step_requires` at all. Only
`ci/wiring/test_wiring.py` performs the equality check. Half the stated guarantee is fiction. (No
data-loss risk: `derive.py` has no write mode — `{verify,overview,command-map,numbered,profile}` — so
regenerating cannot wipe the new blocks.)

---

## Priority 1 in detail — packaging and reach (PASS)

Built the plugin into a scratch copy and checked:

```
$ cp -R ../hitl-claude-plugin $W/plug && rm -rf $W/plug/.git
$ $W/plug/scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform
  OK  skills/dev-start-change/selection.md
  OK  skills/dev-start-change/right-sizing.md
  OK  skills/dev-start-change/first-pass-choices.md
  OK  shared/ci/first-pass/rank.py
  OK  shared/workflows.yaml            (step_costs present)
$ claude plugin validate $W/plug
✔ Validation passed
```

`remap_skill_path` sends `start-change/*.md` to `skills/dev-start-change/*` via the `*)` default arm —
no per-file list to forget. `rank.py` reaches a product repo by four independent routes, all
pre-existing `*.py` globs that need no edit:

- `tools/scripts/init-project.sh:221` → `hitl_copy_tools` (`find -name "*.py" ! -name "test_*"`)
- `ai/claude/update/SKILL.md:143` and `:247` → `cp "$ROOT/shared/ci/first-pass/"*.py ci/first-pass/`
- `ai/claude/start-from-prd/SKILL.md:214`, `start-brownfield/SKILL.md:205`,
  `start-migration/SKILL.md:89` → same glob

The three reference `.md` files are read from the installed plugin and are not copied into product
repos, which is correct.

## Priority 2 in detail — consumers of the grown `workflows.yaml` (PASS)

The hand-rolled parser in `ci/breadcrumb/run_matrix.sh` was the suspect: it sets `in_workflows=True`
at `workflows:` and never resets, and its `^  (\w+):\s*$` workflow-header regex does match the
two-space-indented `step_costs` entry keys — including `docs:`, which collides with the real `docs`
workflow id. It survives only because those entries carry neither a `total:` line nor a `- {…}` flow
map, so nothing is appended:

```
$ bash ci/breadcrumb/run_matrix.sh
 RESULT: 271 passed, 0 failed (of 271 assertions)
EXIT=0
```

It is fragile rather than broken — a future `step_costs` entry keyed to a workflow name and carrying a
`total:` would corrupt that workflow's step list — but it is not a 2.9.0 defect.

`check_skips.load_catalog`, the Step 6 generator, and the Step 4.5 migration all index `["workflows"]`
and ignore siblings. `derive.py verify` passes. `docs/validation-guide.md`'s `grep` checks are
unaffected.

## Priority 4 in detail — existing change files (PASS)

Seeded a change file with the **v2.8.0** generator, then ran the 2.9.0 Step 4.5 migration against the
2.9.0 catalog:

```
$ python3 gen280.py development GH-42 issue/42-x 2.8.0 2 none.json "" ""   # 34 step lines
$ python3 mig.py ci/first-pass/workflows.yaml 2.9.0
MIG_EXIT=0
$ grep -c "step_costs\|protects:\|forgo_cost" .hitl/current-change.yaml.migrated
0
$ diff before.yaml .hitl/current-change.yaml.migrated
2c2
< hitl_version: "2.8.0"
---
> hitl_version: "2.9.0"
...  version stamps and step-line quoting only
$ diff -q before.yaml .hitl/current-change.yaml && echo yes
yes            # original untouched, migration is confirm-gated
```

A freshly seeded 2.9.0 change file is also clean and validates:

```
$ python3 -c "print(list(yaml.safe_load(open('a.yaml'))))"
['schema_version','hitl_version','change_id','tier','status','expected_branch','workflow','current_step']
$ python3 ci/first-pass/check_skips.py a.yaml --workflows ai/shared/workflows.yaml
First Pass skip ledger: clean.   EXIT=0
```

The CHANGELOG's "Existing change files are unaffected … nothing re-reads a plan that has already been
seeded" is **true**.

## Priority 5 in detail — the split (PASS except F4)

Every link out of the four files:

```
SKILL.md:100  ../dev-practices/SKILL.md      → skills/dev-practices/SKILL.md      ✓
SKILL.md:112,157  right-sizing.md            → same dir                            ✓
SKILL.md:138  selection.md                   → same dir                            ✓
SKILL.md:179  first-pass-choices.md          → same dir                            ✓
selection.md   (no markdown links)
right-sizing.md (no markdown links)
first-pass-choices.md:52  absolute GitHub URL                                       ✓
```

No reference chains onward more than one level. `build.sh`'s mangled-path guard passes. Content
comparison against the removed SKILL.md block shows everything preserved except the three link
targets in F4.

---

## Priority 6 — CHANGELOG 2.9.0 claims that are not true

| Claim | Status |
|---|---|
| "One thing newly refuses: a tier 2 or higher declared on a change whose diff touches no source under a manifest domain, with no `tier_set_by`/`tier_reason`." | **False.** F1 — nothing sets `TRIVIAL_SHAPE`, so nothing newly refuses. |
| "a ranker that modulates them … **never past the floor**" | **False at tier 3 and 4.** F2 — six floor steps show as unlocked at tier 4, one at tier 3. |
| "**`protects` and `forgo_cost` for all 38 steps**" | **Misleading.** F6 — 38 entries, 4 of which name no runtime step; 53 of 87 runtime step keys have neither field. |
| "Every change in every project has been getting the same **31 steps**" / "`keep` was the default for all **31** (CR-1)" | **Wrong count.** The runtime `development` block has 34 rows; the same entry says "instead of 34" two paragraphs earlier. |
| "A tier proposed from the shape of the change. If the diff touches only non-source paths…" | **Unsound in practice.** F5 — at intake the diff is empty for every change, so "non-source only" is always the answer. |
| "the shape probe never lowers a floor step" | True as written in `right-sizing.md`; F2 shows the *selection view* does, independently of the probe. |
| "Existing change files are unaffected… nothing re-reads a plan that has already been seeded" | **True.** Verified. |
| "Run `/hitl:dev-update`." (implying the new tooling arrives) | **True.** `rank.py` and the grown `workflows.yaml` both sync. |
| "8 workflows · 93 steps" (portal, not CHANGELOG) | **False.** F3 — 96 steps + 3 substeps is what the catalog produces. |

---

## Verdict

**DO NOT SHIP.**

Two of the release's four headline items do not do what the notes say, and the third contradicts the
published catalog. In upgrade terms: an upgrader is told about a refusal that will never fire, is
shown a selection that mislabels floor steps at the tier they are told to default to, and is pointed
at a portal page missing three shipped steps.

Smallest change that would fix it, in order:

1. **F1** — in the Step 6 bash block, set `TRIVIAL_SHAPE` from the probe before invoking the
   generator (one exported line), and make the wiring test assert an *assignment* exists, not a
   substring. If that cannot be made honest in this cycle, delete the `if trivial and tier >= 2`
   block and the "Note for existing projects" paragraph rather than shipping a refusal nobody can
   reach.
2. **F2** — one line in `rank.py:rank_plan`: call `check_skips.resolve_crit(s, tier)` instead of
   `(s.get("crit_by_tier") or {}).get(tier, …)`, with the existing tolerant fallback when the import
   is unavailable.
3. **F3** — `python3 tools/scripts/generate-catalog-page.py` and commit the result.
4. **F4** — restore the three relative link targets in `first-pass-choices.md` (or add the three
   filenames to `SHARED_PROSE` in `build.sh`).

F5–F10 are safe to fast-follow, with the exception that F5's guidance table should not ship as
written while the probe returns empty for every change at intake — one sentence saying "if the probe
returns nothing, it has told you nothing; propose the tier you would have anyway" closes it.
