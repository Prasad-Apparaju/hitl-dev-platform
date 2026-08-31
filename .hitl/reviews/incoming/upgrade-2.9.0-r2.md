# Upgrade review — 2.9.0 RC, round 2 (07bda66)

Lens: what happens to someone already on 2.8.0, and to the next fresh install.
Base: `git diff 9ba9fd2..HEAD` (the round-1 fixes) and `git diff v2.8.0..HEAD` (the whole release),
HEAD = `07bda6643737ad2a339bfd21213d36d81b12eda1` on `main`.
Every finding below was reproduced in a scratch repo. Commands and observed output are inline.
Nothing in the source tree or `.hitl/` was modified; the plugin build ran against a `mktemp -d` copy.

**Verdict: DO NOT SHIP.** Round 1's packaging finding is genuinely fixed and I could not break it
from any install path. But round-1's F1 was fixed one layer up and is still dead: the tier 2+
refusal the CHANGELOG leads with never fires, because the only thing that sets `TRIVIAL_SHAPE`
does it in a shell that no longer exists when the reader runs. And the tail-recording fix that
round 1 forced into `plan_select.py` is destroyed one step later by a sibling doc that truncates
the same file. Both reproduced end to end, both green under the new guards.

---

## Summary

| # | Severity | Finding |
|---|---|---|
| G1 | **CRITICAL** | Round-1 F1 is not fixed. `export TRIVIAL_SHAPE=` runs in Step 4's Bash call; Step 6 reads `os.environ` in a later Bash call, where it is unset. The tier 2+ refusal never fires. The new guard greps for the string in a file — the exact pattern this release condemns. |
| G2 | **CRITICAL** | Two shipped files truncate `.hitl/first-pass-choices.json`. Step 4 writes 27 tail records; Step 4b's `cat > …` overwrites them with a 1–3 entry hand-written file; the validator then reports `clean`. This is the "tail skipped and NOT recorded" failure that `plan_select.py choices` was written to prevent, reachable one step later. |
| G3 | MEDIUM | The shipped selection block references `$WF_ID`, `$TIER`, `$PROFILE`, `$TAGS`, which no step sets. Run as written it exits 2 on `--tier ''` and prints no selection. Its sibling block in Step 6 assigns every variable it uses. |
| G4 | MEDIUM | `selection.md` says "the floor can be unticked"; the tool it tells you to run cannot express that — `kept` is unioned with every locked step, so an unticked floor step yields no skip, no record and no prompt. |
| G5 | MEDIUM | `SKILL.md` Step 4b still says First Pass "above tier 1 is opt-in and the full plan is the default". Step 4 runs the selection unconditionally and declines the tail at every tier — 16 steps at tier 3. Two adjacent paragraphs, opposite defaults. |
| G6 | LOW | Step 6's comment says "`TRIVIAL_SHAPE` comes from the probe in `right-sizing.md`". `right-sizing.md` sets nothing; the setter is `selection.md`. A reader debugging G1 is sent to the wrong file. |
| G7 | LOW | `ci/retired-tests.sha256`'s `test_rank.py` line is inert. `test_rank.py` has never been synced into a product repo and cannot be (`build.sh` filters `test_*`), so the file's own header — "every version of every test file HITL has ever synced" — is false about the one line round 1 added. |

### Areas I could not break — stated plainly

- **Priority 1, packaging and reach: SOUND.** Round 1's stdlib-shadowing bug is really gone.
  `plan_select.py` ships, lands, and runs from a copied location on every path I exercised: a real
  `build.sh` run from source HEAD, `init-project.sh` end to end, `/hitl:dev-update`'s copy, and the
  three `dev-start-*` skills. Both upgrade orders (plugin first / `dev-update` first) degrade
  correctly. Evidence below.
- **Priority 2, stdlib shadowing: SOUND.** No `.py` packaged under `shared/` has a basename in
  `sys.stdlib_module_names` — checked mechanically, not by eye. Two shipped call sites still
  `sys.path.insert(0, …)` (`dispositions.py:22` and the Step 6 generator), so the "append, never
  insert" rule is applied to two of four sites; I could not turn that into a failure and am not
  reporting it as one. It is a landmine for the next module added to `ci/first-pass/`.
- **Priority 3, existing change files: SOUND.** A 2.8.0-era change file is byte-identical after
  `migrate_project.py --root . --apply`, and the validator returns the same verdict under the 2.8.0
  and 2.9.0 catalogs. The catalog's `workflows` block is *structurally identical* across the
  release — same 8 workflows, same 99 step rows, same keys, same order, same per-step fields; only
  `step_costs` and `step_requires` are new. The CHANGELOG's "existing change files are unaffected"
  is true.
- **Priority 4, retired tests: SOUND** (bar G7). All 17 `test_*.py` blobs ever committed under
  `shared/` in the plugin's whole history are present in the manifest, and the dev-update removal
  list covers all 14 paths with no extras and no gaps. No consumer keeps a file forever; no
  consumer loses one it wrote.
- **`site/catalog.html`: SOUND.** Regenerate-and-compare passes; the committed page is generator
  output. Header count (96 steps + 3 substeps) matches the generated comment (99 rows).
- **`rank.py`'s fallback: SOUND.** With `check_skips` unimportable, `effective_crit`'s local
  fallback agrees with `resolve_crit` on all 99 steps at tiers 0–4. A repo where the import fails
  still locks the right set.
- **Suites: 211 passed** (`ci/wiring` + `ci/first-pass`) — including every new guard, while G1 and
  G2 are both live.

---

## G1 — CRITICAL. Round-1 F1 is not fixed: the refusal still cannot fire

Round 1 found that nothing set `TRIVIAL_SHAPE`. The fix added a setter — in the wrong process.

`selection.md` (Step 4) does the export:

```bash
export TRIVIAL_SHAPE="$(python3 "$SEL" probe --base "${BASE:-main}")"
```

`SKILL.md` (Step 6) does the read, in a different Bash tool call:

```python
trivial = os.environ.get("TRIVIAL_SHAPE", "").strip().lower() in ("1", "true", "yes")
```

Shell state does not survive between Bash tool calls, and these two blocks **cannot** share one:
Step 4 renders a selection, Step 4b collects a human decision through `AskUserQuestion`, and Step 5
runs before Step 6. A human confirmation sits between the setter and the reader by design.

Demonstrated in this environment, two consecutive Bash calls:

```
call A:  export HITL_PROBE_PERSIST=yes; echo "set in call A: $HITL_PROBE_PERSIST"
         set in call A: yes
call B:  echo "call B sees: [${HITL_PROBE_PERSIST:-<unset>}]"
         call B sees: [<unset>]
```

Then the generator itself, extracted verbatim from `SKILL.md` and run in an onboarded repo whose
diff touches only `deploy.sh` (non-source, manifest domain = `src/`), at tier 2, with no
attribution:

```
### A. Step 4 exported TRIVIAL_SHAPE=1 in an EARLIER bash call; Step 6 runs in a NEW one:
$ env -u TRIVIAL_SHAPE python3 step6.py development GH-1 work 2.9.0 2 .hitl/first-pass-choices.json "" ""
rc=0
schema_version: "2.0"
hitl_version: "2.9.0"
change_id: "GH-1"
tier: 2
status: planning

### B. same command with TRIVIAL_SHAPE=1 present (what the author assumed):
$ TRIVIAL_SHAPE=1 python3 step6.py development GH-1 work 2.9.0 2 .hitl/first-pass-choices.json "" ""
no source under a manifest domain is touched, so tier 2 needs TIER_SET_BY and TIER_REASON. …
rc=1
```

A is what every user gets. The `FIRECRAWL_API_KEY` change — the one the release opens with — seeds a
tier 2 with no name against it, exactly as it did in 2.8.0.

**What is now false in the CHANGELOG:**

- *"A tier 2+ declared on a trivially-shaped change now needs a name and a reason too. This **adds**
  a rule rather than trading one away."* — it adds nothing that executes.
- *"### Note for existing projects … One thing newly refuses: a tier 2 or higher declared on a change
  whose diff touches no source under a manifest domain, with no `tier_set_by`/`tier_reason`."* — the
  single behavioural change the upgrade note promises existing projects is the one that does not
  happen. As shipped, the upgrade is behaviourally a no-op on this axis.
- `SKILL.md` Step 3b: *"the generator … refuses a tier 2+ without them when the shape probe said the
  change was trivial."*

**Why the guard missed it.** `ci/wiring/test_wiring.py:542` asserts
`re.search(r"export TRIVIAL_SHAPE=", sel)` — that the string appears in a file. The comment three
lines above it says: *"Reading it is not enough. Something must SET it … a guard stayed green because
it asserted a name appeared in a file."* The fix for that lesson is the same shape as the bug.

**Smallest fix.** Resolve it in the block that reads it, and delete the cross-call dependency. In
`SKILL.md` Step 6, before the heredoc:

```bash
SEL="ci/first-pass/plan_select.py"; [[ -f "$SEL" ]] || SEL="$ROOT/shared/ci/first-pass/plan_select.py"
export TRIVIAL_SHAPE="${TRIVIAL_SHAPE:-$(python3 "$SEL" probe --base "${BASE:-main}")}"
```

(`$ROOT` must move above Step 6; it is currently first assigned at `SKILL.md:435`, after the
generator that uses it.) Then change the guard to assert **Step 6's own block** sets it, and add a
run-the-generator case with the variable absent that expects a refusal.

---

## G2 — CRITICAL. A sibling doc truncates the choices file, and the tail vanishes again

`selection.md` writes the choices file with `>`:

```bash
python3 "$SEL" choices … --keep "issue,review1,verify_pr" --actor "…" > .hitl/first-pass-choices.json
```

`first-pass-choices.md`, reached from Step 4b — the *next* step — writes the same path with `>`:

```bash
cat > .hitl/first-pass-choices.json <<'JSON'
{ "actor": "name@team", "choices": { "roi": {…}, "docs": {…} } }
JSON
```

Neither file mentions the other. `SKILL.md:217` cements the wrong model:
`CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b`.

Reproduced in the onboarded repo, tier 1, profile `fix` — the release's own worked example:

```
### Step 4 (selection.md) writes the choices file:
   entries: 27
### Step 4b (first-pass-choices.md) writes the SAME path, verbatim from the doc:
   entries: 2
### Step 6 generator consumes it:
skips:
  - { step: roi,  crit: ceremony, actor: "name@team", … }
  - { step: docs, crit: standard, actor: "name@team", … }
```

With the doc's `starter` entry dropped so nothing unrelated blocks:

```
$ python3 ci/first-pass/check_skips.py .hitl/current-change.yaml --workflows ci/first-pass/workflows.yaml
First Pass skip ledger: clean.
validator rc=0 (0 = certified clean)
```

Twenty-six recorded skips became one, the actor became `name@team` instead of the person who
answered, and the fail-closed validator certified the change clean. `selection.md` states the
consequence in bold in its own Rules section:

> **If the tail does not reach it, the tail is skipped and NOT recorded**, and the fail-closed
> validator certifies the change clean — the first draft of this feature did precisely that, and a
> review caught it.

The tool was fixed; the path around the tool ships beside it. This is guaranteed, not incidental, on
the tier 0/1 path — that is where Step 4b is offered "without being asked", and it is the path the
whole release exists to serve.

**Smallest fix.** Make Step 4b amend rather than replace. In `first-pass-choices.md`, replace the
`cat >` heredoc with a merge onto whatever Step 4 already wrote:

```bash
python3 - <<'PY'
import json, os
p = ".hitl/first-pass-choices.json"
doc = json.load(open(p)) if os.path.isfile(p) else {"actor": "", "choices": {}}
doc["actor"] = doc.get("actor") or "name@team"
doc["choices"].update({ "docs": {"disposition": "starter", "reason": "thin first pass"} })
json.dump(doc, open(p, "w"), indent=2)
PY
```

and add one wiring guard: no shipped file other than `selection.md` may contain
`> .hitl/first-pass-choices.json`.

---

## G3 — MEDIUM. The shipped selection command cannot run as written

`selection.md` lines 34–35 and 78–79 reference `$WF_ID`, `$TIER`, `$PROFILE`, `$TAGS`. Nothing before
Step 4 assigns any of them; the only `TIER=` in the skill is at `SKILL.md:214`, inside Step 6's
block, two steps later and in a different shell. Run in a fresh shell, exactly as shipped:

```
$ env -u WF_ID -u TIER -u PROFILE -u TAGS bash -c '<the block from selection.md>'
TRIVIAL_SHAPE=1
plan_select.py: error: argument --tier: invalid int value: ''
render rc=2
```

The probe succeeds and the selection does not print, so the failure lands precisely where the model
is likeliest to fall back to describing the plan in prose — the behaviour this release was written
to end. Step 6's block assigns every variable it uses (`WF=<development|…>`, `TIER=2`,
`TIER_SET_BY=""`); Step 4's does not. Smallest fix: add the three assignment lines with the same
placeholder convention Step 6 already uses.

---

## G4 — MEDIUM. "The floor can be unticked" — the tool says otherwise

`selection.md` promises, with a worked example:

> **The floor can be unticked.** It is not locked out of the view, it is locked out of *casual*
> choice: name the specific loss, take a name against it, and a linked waiver …

`plan_select.py:154` overrides the person:

```python
kept = {k for k in a.keep.split(",") if k} | {r["key"] for r in locked}
```

Reproduced — keep nothing at all, at tier 2:

```
$ python3 ci/first-pass/plan_select.py choices … --keep "" --actor "priya"
   recorded: 29
   floor/no_omit present: NONE — unticking the floor records nothing
```

The direction is safe (the step stays kept), but the promised interaction is unreachable through the
only tool the doc allows you to use, and the untick produces no prompt, no record, and no sign that
it was ignored. Either the tool needs a `--drop-floor <step>=<ack_by>,<waiver_ref>` path or the
prose needs to say the floor is decided outside this file.

---

## G5 — MEDIUM. Two adjacent paragraphs, opposite defaults

`SKILL.md` Step 4b: *"Above tier 1 it is opt-in and the full plan is the default."*
`SKILL.md` Step 4, unconditional: *"Then show the selection … the tail is collapsed and skipped,
recorded."*

Measured at each tier in the onboarded repo:

```
tier 0  locked=4  offered=8  tail=22
tier 1  locked=4  offered=8  tail=22
tier 2  locked=5  offered=8  tail=21
tier 3  locked=10 offered=8  tail=16
```

At tier 3 — the tier the skill tells you to default up to — the selection declines sixteen steps
unless the person re-ticks them, on a path the same skill calls opt-in with the full plan as the
default. `first_pass: true` is then stamped on a change nobody opted in to. The CHANGELOG's "What
silence means" does disclose the inversion; `SKILL.md` Step 4b now contradicts it. One of the two
has to move.

---

## G6 / G7 — LOW

**G6.** Step 6's comment reads *"`TRIVIAL_SHAPE` comes from the probe in `right-sizing.md`."*
`right-sizing.md`'s probe is a bare `git diff --name-only` for a human to read and assigns nothing;
`grep -n 'TRIVIAL_SHAPE' ai/claude/start-change/right-sizing.md` returns nothing. Anyone debugging
G1 from the comment goes to a file that never mentions the variable.

**G7.** `ci/retired-tests.sha256` gained `e7f86c39…  test_rank.py`. Enumerating every `test_*.py`
blob ever committed under `shared/` across the plugin repo's whole history yields 17 hashes, all 17
already in the manifest; `test_rank.py` is not among them and cannot be, since `build.sh` filters
`! -name "test_*"` and every consumer copy path reads from `shared/`. The entry is inert, and the
file's header claim is false about it. Harmless; delete the line or note why it is there.

---

## Evidence for the sound areas

**Build and reach.** Full `build.sh` run from source HEAD into a `mktemp -d` copy of the plugin
reset to its 2.8.0 commit:

```
$ HITL_SOURCE_DIR=…/hitl-dev-platform ./scripts/build.sh
✔ Validation passed  /  Packaging check: no test/conftest/bytecode under shared/  /  Build complete.
$ ls shared/ci/first-pass/
check_skips.py dispositions.py migrate_project.py permissions.py plan_select.py rank.py resurface.py starters.py
```

`init-project.sh` into a fresh git repo (`printf '1\n' |`, it prompts):

```
✓ ci/first-pass/ (First Pass validator + catalog) + .github/workflows/first-pass-check.yml
$ ls ci/first-pass/ → …plan_select.py rank.py…
$ python3 ci/first-pass/plan_select.py render … | head -3
Running (locked)
   red                thinnable, never dropped
$ python3 ci/first-pass/plan_select.py probe --base main → 0
```

`/hitl:dev-update`'s copy (`cp "$ROOT/shared/ci/first-pass/"*.py ci/first-pass/`) into a repo with a
manifest and a non-source diff — `probe` → `1`, `render` → 5 locked / 8 offered / 21 tail, `choices`
→ 26 entries, exit 0. Executed from the copied location, which is the condition round 1's bug
needed. Plugin-updated-but-`dev-update`-not-run also works: the `$ROOT/shared/…` fallback in
`selection.md` resolves and runs.

**Stdlib shadowing.** Every `.py` under the built `shared/` checked against
`sys.stdlib_module_names`: `packaged .py whose basename shadows a stdlib module: NONE` (18 modules).

**Change files.** `git show v2.8.0:.hitl/current-change.yaml` dropped into the onboarded repo:

```
before=5f5082963cbd64e43aa2679308cab1e749803bea2024904ab9699971f1349df1
$ python3 ci/first-pass/migrate_project.py --root . --apply   → rc=0
after =5f5082963cbd64e43aa2679308cab1e749803bea2024904ab9699971f1349df1   UNTOUCHED
$ check_skips … --workflows <2.9.0 catalog> → [warn] LEDGER_STEPS … rc=0
$ check_skips … --workflows <2.8.0 catalog> → [warn] LEDGER_STEPS … rc=0   (identical)
```

**Catalog structure across the release.** `workflows same: True`; no changed step list, order, total
or per-step field in any of the 8 workflows; new top-level keys `step_costs`, `step_requires` only.
`step_costs` has 38 entries, all with `protects` and `forgo_cost` — the CHANGELOG's "all 38 steps" is
literally accurate about the block that exists (its coverage gap is the already-known item, not
re-reported). `step_requires` has exactly 11 pairs, matching "eleven such dependencies". The
"4 locked, 8 offered, 22 recorded … 8 items instead of 34" headline reproduces exactly at tier 0/1
with `--profile fix`. `derive.py` is confirmed source-only: not present anywhere in the built plugin.

**Checked, no consequence found (not reported as findings):** `render` passes `--tags` and `choices`
does not, so the two calls could in principle split offered/tail differently and mislabel a reason —
I could not make any tag value move a step across the cut at tier 2, so it stays a note.
`__pycache__/rank.cpython-313.pyc` currently sits in the real `hitl-claude-plugin/shared/ci/first-pass/`;
it is gitignored so it cannot ship, but `build.sh`'s stray check will fail the release build until
someone runs `git clean -fdx`. Fail-closed and correct behaviour, mentioned only so it is not a
surprise at release time.

---

## Verdict

**DO NOT SHIP.**

Two blockers, both reproduced, both green under the suite:

1. **G1** — the release's headline behavioural change does not execute. Fix: set `TRIVIAL_SHAPE`
   inside Step 6's own block (`${TRIVIAL_SHAPE:-$(python3 "$SEL" probe …)}`), move `$ROOT` above
   Step 6, and replace the string-grep guard with one that runs the generator with the variable
   absent and expects a refusal.
2. **G2** — Step 4b truncates the file Step 4 wrote, and the tail is skipped and not recorded again.
   Fix: make `first-pass-choices.md` merge into the existing file instead of `cat >`, and guard that
   only `selection.md` may redirect into `.hitl/first-pass-choices.json`.

G3 (three assignment lines) is cheap enough to take in the same pass. G4 and G5 are prose decisions
that should not hold the release but should not be lost either.

Round 1's packaging finding is properly fixed and I could not reopen it from any install or upgrade
path. That area is closed.
