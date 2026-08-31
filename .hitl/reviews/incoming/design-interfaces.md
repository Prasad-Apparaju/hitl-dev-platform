# Interfaces review — `docs/design/right-sizing/01-design.md` (issue #97)

**Lens:** interfaces. Does this hold at the boundaries it crosses?
**Design state:** `feb2cc3` (`design(right-sizing): cut it down to the plan`), tree otherwise clean.
**Method:** every claim about current behaviour below is checked against the file and quoted or
reproduced. Reproductions ran in `mktemp -d` scratch dirs and in a throwaway `git worktree`, now
removed. No tracked file was modified; nothing was written into `.hitl/` except this report.

**Verdict: NOT SOUND.**

The fourth instance is here, and it is the same shape as the first three. The design has a
producer at step 4 and a consumer at step 6 with **no artifact named between them**, and both of
the only two artifacts that could carry it are already closed: one is refused by the writer
(`plan_select.py apply` exits 2 when the change file does not exist yet — and step 6 is what
creates it), the other fails a shipped fail-closed wiring guard the moment it is written from
intake. That is I1. I2 is worse in kind: the design puts the ledger writer *between* two tier
decisions, and criticality — which decides whether a skip record is legal — is a function of the
tier. A clean ledger at step 6b becomes seven non-waivable blockers at the PR gate.

---

## The handover table

Every handover the design implies, with producer, consumer, artifact and moment. The rows marked
**✗** are the ones that cannot both be true.

| # | Producer (moment) | Artifact | Consumer (moment) | Holds? |
|---|---|---|---|---|
| H1 | intake 3a impact (before branch exists) | domains/paths/deps facts | intake 3b tier | ✓ ordering is right |
| H2 | intake 3b tier | `TIER` shell var | intake 4 shortening (locks floor steps) | ✓ |
| H3 | intake 4 shortening | **unnamed** | intake 6 generator | **✗ I1 — no artifact exists** |
| H4 | intake 6 generator | `.hitl/current-change.yaml` (`skips[]`, `first_pass`) | intake 6b `check_skips.py` | ✓ *if* H3 is solved |
| H5 | intake 3a impact | `impact:` block, location unstated | apply-change step 1 tier check | **✗ I4 — no writer, no schema slot** |
| H6 | intake 3b tier (frozen into `crit` per record) | `skips[].crit` + `tier:` | PR gate `check_skips.py` re-resolves from `tier:` | **✗ I2 — apply-change step 1 revises `tier` after** |
| H7 | ~~apply-change step 3 impact~~ (removed by §6) | `manifest.domain`, `allowed_paths` | apply-change step 7 → 7a `resurface.py`, `check-domain-boundary.sh` | **✗ I3 — producer deleted, consumers left** |
| H8 | design §3 facts (`dependents`, `facades`, `events`) | — | `rank.engaged()` / `plan_select` CLI | **✗ I6 — no parameter, no flag** |
| H9 | product repo `docs/system-manifest.yaml` | `files`, `depends_on`, `tests`, … | §2 lookup | **✗ I5 — keys absent or wrong-shaped in shipped template** |
| H10 | plugin `shared/*` | catalog + validators | product `ci/first-pass/*` | **✗ I9 — opposite precedence in one run** |

---

## I1 — CRITICAL. Step 4 produces a selection; step 6 consumes a file that nothing may write

The design (§1): `4. shorten the plan using those facts` → `5. create the branch` →
`6. write the change file including anything skipped`. It never names what crosses from 4 to 6.

There are exactly two candidates in the shipped system. **Both are closed.**

**Candidate A — `.hitl/first-pass-choices.json`.** This is the *only* input channel the Step 6
generator has for skips. `start-change/SKILL.md:223`:

```
CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b; absent ⇒ full plan, no First Pass
```

and the generator emits `first_pass: true` and a `skips:` block only when that file is non-empty
(`SKILL.md:341-342`, `:355-366`). But `ci/wiring/test_wiring.py::test_the_selection_writes_the_change_file_not_a_hand_off`
now **fails the build** if any `.md` under `ai/claude/start-change/` writes it:

```python
    d = os.path.join(AI, "claude", "start-change")
    ...
            if re.search(r"(>|cat >|tee)\s*\.hitl/first-pass-choices\.json", t) and not t.startswith("#"):
                handoff.append(...)
    assert not handoff, (
        "the selection still writes a choices file. Intake's Step 6 consumes that and has already "
        "run by then, so the record reaches nobody:\n  " + ...)
```

Reproduced in a detached worktree at HEAD (baseline `1 passed`), by appending the round-1 command
to `selection.md`:

```
$ printf '\n```bash\npython3 "$SEL" choices --keep "$KEEP" --actor "$WHO" > .hitl/first-pass-choices.json\n```\n' >> ai/claude/start-change/selection.md
$ python3 -m pytest -q ci/wiring/test_wiring.py::test_the_selection_writes_the_change_file_not_a_hand_off
E       AssertionError: the selection still writes a choices file. ...
E           selection.md: python3 "$SEL" choices --keep "$KEEP" --actor "$WHO" > .hitl
1 failed in 0.08s
```

The guard's docstring states the rule it is enforcing: *"Two earlier versions got this wrong in
opposite directions: first two writers of the choices file racing each other, then a single writer
producing a file nobody would read."* The design moves the selection back to the side of the
boundary the guard was written to keep it off.

**Candidate B — write straight into the change file with `plan_select.py apply`.** At step 4 the
change file does not exist; step 6 creates it. `apply_to_change` refuses:

```
$ ls .hitl/          # empty — step 6 has not run
$ python3 ci/first-pass/plan_select.py apply --workflows ci/first-pass/workflows.yaml \
    --workflow development --tier 2 --paths "src/billing/refund.py" \
    --keep "issue,impact,verify_pr" --actor "priya@team"
no change file at .hitl/current-change.yaml — intake creates it; run /hitl:dev-start-change first
EXIT=2
```

Running it *after* step 6 does not rescue the design either: the generator only writes
`first_pass: true` when it had choices (which it would not have), and `apply` never sets the flag
(`plan_select.py:99-132` — no `first_pass` assignment), so every lightened change certifies through
the `FP_ABSENT_ENFORCED` warn path (`check_skips.py:224-227`), which is the anomaly branch, not the
normal one. That is finding B3/C7/U11 in the three round-3 reports, unchanged by this design.

There is also a third, silent cost of Candidate B. If step 6's generator becomes the writer, the
same guard *requires* the now-orphaned `apply` invocation to stay in `selection.md`:

```python
    assert re.search(r'(?m)^[^#\n]*python3 "\$SEL" apply', sel), (
        "selection.md does not run `plan_select.py apply`, so nothing writes the skip records")
```

So the build stays green while `apply` becomes a writer with no caller — literally the first of the
three failures, restored, with a guard holding it in place.

**§1's claim "The skip check stays at 6b and starts working, because the record now exists by the
time it runs" is therefore unproven.** 6b already runs after 6 today (`SKILL.md:413-440`). The
reason it certifies nothing is not its position — it is that the record's only writer was deleted
and its replacement lives on the other side of the command boundary. The design changes the
position and not the writer.

---

## I2 — CRITICAL. The ledger is written between two tier decisions, and the ledger's legality is a function of the tier

§1 puts `3b. confirm the tier now based on evidence` before `6. write the change file`. §6 then says
apply-change's *"first step stops re-guessing the tier from your description and checks it against
the recorded evidence instead."* A check that cannot change the answer is not a check, so the design
has two tier decisions with the ledger writer between them.

Criticality is resolved from the tier at write time and frozen per record
(`start-change/SKILL.md:361`: `crit = resolve_crit(by_key[key], tier)`), but `check_skips.py`
**re-resolves it from the change file's current `tier:`** at every later validation
(`check_skips.py:339`: `crit = resolve_crit(meta, tier)`; `:230`: `tier = change.get("tier") if tier is None else tier`).
Five development steps move onto the floor at 3 (`ai/shared/workflows.yaml`:
`impact`, `packet`, `arch_review`, `qa_verify`, `rollout` all carry `crit_by_tier: { 3: floor }`).

Reproduced. A change file seeded at tier 2 with those five declined, then the tier revised up:

```
recorded crits at intake tier 2: {'arch_review':'standard','impact':'standard','packet':'standard',
                                  'qa_verify':'standard','rollout':'standard'}

--- validate at tier 2 (as intake recorded it) ---
First Pass skip ledger: clean.
EXIT=0

--- apply-change step 1 revises the tier UP to 3 (design section 6) ---
tier: 3
[BLOCK] FLOOR_NO_ACK: floor step 'arch_review' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_WAIVER: floor step 'arch_review' maps to a hard gate but has no waiver_ref (skip != waiver)
[BLOCK] FLOOR_NO_ACK: floor step 'impact' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_ACK: floor step 'packet' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_ACK: floor step 'qa_verify' skipped with no ack_by (accountable role)
[BLOCK] FLOOR_NO_WAIVER: floor step 'qa_verify' maps to a hard gate but has no waiver_ref (skip != waiver)
[BLOCK] FLOOR_NO_ACK: floor step 'rollout' skipped with no ack_by (accountable role)
EXIT=2
```

`ci/workflows/first-pass-check.yml` runs `check_skips.py` on **every** PR, so this is where it lands:
a merge-blocking failure on records written correctly, by the right person, at the tier that was
true when they were written. And nothing can repair them — `plan_select.py` never writes `tier`
(no assignment anywhere in the file) and has no `--ack-by`/`--waiver-ref`; the Step 6 generator has
already run; every doc tells the user not to hand-edit the change file.

Note the direction. This is not "the tier might be wrong". It is that the design *asks* for the tier
to be revised after the ledger exists, and the two components disagree about whether `crit` is a
recorded fact or a derived one. Today the writer treats it as recorded, the reader as derived; today
that is harmless because both run at intake, seconds apart. The design pulls them into two commands
and two sessions.

Design question 4 ("Should the workflow choice in step 3 also be rechecked once the analysis has
run?") is the same defect one level up and worse: `check_skips.run()` loads the catalog from
`workflow.id` (`check_skips.py:420-424`), so a workflow revised after step 6 turns every recorded
skip into `UNKNOWN_STEP` (non-waivable) or `INCOMPLETE_PLAN`. The answer to question 4 is "not
unless you also say who rewrites the ledger".

---

## I3 — HIGH. §6 deletes the producer for three consumers it does not mention

§6: *"Its impact analysis step is removed. The facts arrive in the change file."*

`apply-change/SKILL.md` Step 3 is the producer for Step 7, quoted verbatim (`:171-181`):

```
Set from the impact analysis above:
- `tier`: from Step 3
- `manifest.domain`: affected domain name
- `allowed_paths`: source paths for this domain
- `current_step`: {number: 3, name: "Impact analysis", phase: "Design"}
```

Three consumers depend on Step 7's output, and none is named in the design:

1. **Step 7a, the roll-up narrowing.** `apply-change/SKILL.md:186-189`: *"This is the first moment
   the change knows its own area… Called at intake, before `manifest.domain` and `allowed_paths`
   exist, it matches nothing and silently says nothing."* Intake Step 6b already warns about the
   same thing: *"With no area declared yet, entries record as **project-wide** and resurface at any
   later change until resolved. The `development` route re-runs this at its impact step, narrowing
   them to the real scope."* Remove the impact step and the narrowing re-run has no host: every skip
   recorded at intake stays project-wide and resurfaces on every future change, forever.
2. **`check-domain-boundary.sh`**, which reads `allowed_paths` from the change file
   (`:57-66`) to scope edits.
3. **`current_step`**, which Step 7 hard-codes to a step the design deletes.

And the design's own `impact:` block does not satisfy any of them, because they read different keys.
`resurface.scope()` (`resurface.py:167-181`) reads `manifest.domain`, `manifest.domains[].paths` and
`allowed_paths` — never `impact.*`. Reproduced against a change file carrying the design's §3 block
verbatim:

```
impact block present: True ['billing']
resurface.scope(change) -> ([], [])
```

The facts arrive in the change file under a name nothing reads.

---

## I4 — HIGH. The `impact:` block has no home, no writer, and no schema entry

The design does not say where it lives. Working through the candidates:

**In `.hitl/current-change.yaml` as a top-level key.** Not in the schema. The complete top-level key
list in `ai/shared/templates/change-context.schema.yaml` is: `schema_version`, `hitl_version`,
`expected_branch`, `change_id`, `tier`, `tier_set_by`, `tier_reason`, `status`, `source_artifacts`,
`manifest`, `allowed_paths`, `required_evidence`, `approvals`, `blocker`, `workflow`, `current_step`,
`token_tracking`, `first_pass`, `skips`. No `impact`.

*Would it even be valid there?* Mechanically, yes — and I want to be precise, because this is the
one part of the answer that is good news. Nothing enforces the key set: `check_skips.py` reads only
the keys it knows, and the dependency-free awk parsers in `ai/claude/hooks/_steps.sh` are anchored
(`hitl_scalar` matches `^k:`; `hitl_steps` only reads inside `workflow: → steps:`). Reproduced with
the §3 block inserted immediately above `workflow:` in a real change file:

```
hitl_scalar tier        -> 3
hitl_scalar status      -> planning
hitl_scalar change_id   -> GH-1
hitl_change_active      -> yes
hitl_current_n          -> 1
steps parsed            -> 34
```

Nothing broke. So the *location* is viable. What is missing is the writer and the contract:

- The Step 6 generator takes **8 positional arguments** (`wf_id, change_id, branch, ver, tier_s,
  choices_path, tier_set_by, tier_reason`) and emits a **fixed `lines` list**. There is no slot for
  an impact block and no mechanism to pass one. `manifest:` and `allowed_paths:` are not emitted by
  it either — which is why they are Step 7's job today.
- `apply-change/SKILL.md:170` tells the model to *"Create or update `.hitl/current-change.yaml`
  using the schema at `ai/shared/templates/change-context.schema.yaml`"*. An agent following that
  instruction against a schema with no `impact` key has no reason to preserve the block, and §6 has
  that same agent rewriting the file.

**In a side file (`.hitl/impact.yaml`).** Workable — `.hitl/` is committed
(`start-from-prd/SKILL.md:114-117`: *"`.hitl/` itself is COMMITTED … Only transient working files
are ignored"*) — but it is a new durable artifact with no schema, no validator, no `.gitignore`
decision, and no retirement: the `promote` retirement step names `skip-ledger.yaml` explicitly as
protected and would not know about this one.

**In the conversation only.** Dies at the command boundary — that is failure #3 from the round-3
reports.

The design must pick one and say who writes it. Right now §3 is a schema for a message with no
sender and no addressee.

---

## I5 — HIGH. §2's lookup keys are absent or wrong-shaped in the manifests HITL actually ships

§2 turns impact analysis into *"a lookup"* against the system manifest, and tabulates eight fields.
Checked against the three manifests in the tree:

```
docs/examples/greenfield/docs/system-manifest.yaml
    files list · facade_apis dict · depends_on list · tests list · lld str ·
    events_emitted list · owning_fr ABSENT · last_changed dict
ai/shared/templates/system-manifest-template.yaml         <- the one copied into new projects
    files list · facade_apis LIST · depends_on ABSENT · tests ABSENT · lld str ·
    events_emitted ABSENT · owning_fr ABSENT · last_changed ABSENT
docs/examples/compound-agentic/system-manifest.yaml
    files list · facade_apis ABSENT · depends_on ABSENT · tests ABSENT · lld ABSENT ·
    events_emitted ABSENT · owning_fr str · last_changed ABSENT
```

Three consequences at the boundary:

1. **`facade_apis` has two shapes in the wild.** The schema
   (`generate-docs/templates/system-manifest.schema.yaml:60`) says `map[string, FacadeAPI]`, the
   generator emits a dict (`tools/generate-manifest/generator.py:209-225`), the **shipped template**
   emits a list of `{name, description}`. A reader that assumes either one is wrong half the time.
2. **Five of the eight fields are absent from the template HITL gives new projects.** By §5, missing
   data means `confidence` below `declared`, which means shortening is off. The feature is off by
   default for exactly the projects that followed HITL's own onboarding.
3. **`files` is an enumerated list of files that already exist**, not a glob. That is the premise of
   `ci/manifest-drift/check_manifest_drift.py`'s whole first check (*"UNLISTED FILES — source files
   on disk not tracked by any domain"*). But §1 runs impact analysis at intake step 3a — before the
   branch is even cut at step 5, before a line is written. Every path a feature *will create* is
   `undeclared` by construction, so §2's own flow lands on `undeclared → confidence: unknown` and §5
   switches shortening off. **The design moved the analysis earlier to get facts, and the fact source
   can only describe the past.** That is failure #2 from the round-3 reports — a writer whose input
   does not exist yet — in a new costume.

Also: the only automated populator is Python-only (`generator.py:34 scan_python_files`,
`check_manifest_drift.py:82 base.rglob("*.py")`), and only the brownfield route runs it
(`start-brownfield/SKILL.md:187`). For a TypeScript or Go project, `files` and `depends_on` are
hand-maintained prose, and §2's "this is a lookup" is a lookup into whatever someone last typed.

§2's supporting claim is also not quite true as written: *"Graphify already indexes the code and the
docs and rebuilds on write."* `ai/claude/hooks/rebuild-graph.sh` filters to docs and exits otherwise:

```bash
# Only trigger on design doc writes
[[ -n "$FILE_PATH" ]] || exit 0
[[ "$FILE_PATH" == docs/* ]] || exit 0
command -v graphify &>/dev/null || exit 0
[[ -d "graphify-out" ]] || exit 0
```

Header: *"Skips silently if graphify is not installed or no graph has been built yet."* And
`shared/graphify-setup.md:126`: *"Graphify is optional."* §5's off-switch list has no row for
"no graph" or "stale graph".

---

## I6 — HIGH. §4 changes who decides applicability, and the data owner cannot hold the new data

§4: *"A step currently decides whether it applies to your change by matching folder-name patterns."*
That is not what the code does. `rank.py:96-104`:

```python
    i = _idx((entry or {}).get("forgo_cost", "medium"))
    if not engaged(...):
        i -= 1
```

`engaged()` modulates the shown rank **down by one notch**; it never removes a step, and its own
docstring says *"Unknown/absent `engages` counts as engaged… Guessing 'not engaged' would silently
demote every step nobody has annotated."* The module docstring is explicit that this is a display
ordering, not a gate: *"never past the floor — modulation reorders the list, it does not unlock a
floor step or soften `no_omit`."* So §4 is not "change the matcher", it is "promote a sort key into a
predicate", and the design does not say what the new one is allowed to do.

Then the ownership question. Three of §4's bullets need three different owners:

- *"this step matters when the change touches these domains"* — needs **project-specific domain
  names** (`billing`, `auth`) in the file the matcher reads. That file is
  `ci/first-pass/workflows.yaml` in the product repo, and `/hitl:dev-update` overwrites it
  unconditionally (`ai/claude/update/SKILL.md:248`):

  ```bash
  [[ -f "$ROOT/shared/workflows.yaml" ]] && cp "$ROOT/shared/workflows.yaml" ci/first-pass/workflows.yaml   # plugin-canonical crit; safe to refresh
  ```

  Anything a team writes there is destroyed on the next update. The project's real domain
  declarations live in `docs/system-manifest.yaml`, which the ranker never reads for this purpose
  (see I7).
- *"when something depends on the domain you touched"* and *"when a public interface moves"* —
  structural predicates that need `dependents` and `facades`. `rank.engaged()` accepts only
  `paths, profile, tags, multi_domain`; `rank_plan()` accepts only those plus `risky_domain`; and
  `plan_select.py`'s CLI has `--paths --profile --tags --manifest --incidents` and nothing else.
  §3 produces `dependents`, `facades`, `events`, `owning_fr` and hands them to a consumer with no
  parameter for them.

The data itself is duplicated with no verifier. `step_costs` (which holds `engages`) exists in both
`tools/workflow-catalog/catalog.yaml` and `ai/shared/workflows.yaml` — 38 entries each, currently
identical (checked) — and `tools/workflow-catalog/derive.py` verifies **only** `n/key/label/phase/total`
(its own docstring: *"checks the result matches the current runtime `ai/shared/workflows.yaml`
(on n/key/label/phase/total)"*; `grep -n step_costs derive.py test_derive.py` → no output). Editing
`engages` in one and not the other is silent today.

---

## I7 — HIGH. §4's incident-registry claim is wrong about today, and the design does not fix it

§4: *"The incident-registry check can then match on domain names, which it cannot do today."*

It does match on domain names today — `rank.risky_domains()` intersects the registry's
`domain/domains/area` fields with manifest domain names. The reason it produces nothing is a
different bug, in a different reader, that §4 does not touch (`rank.py:138-142`):

```python
    for d in ((manifest or {}).get("domains") or []):
        if isinstance(d, dict) and d.get("name"):
            doms[d["name"]] = [p for p in (d.get("paths") or []) if isinstance(p, str)]
```

`domains` is a **map keyed by domain name** with paths under **`files`** — the schema says
`type: "map[string, DomainEntry]"` and `files: list[string]`, and all three shipped manifests
confirm it. Iterating a dict yields its string keys, so `isinstance(d, dict)` is never true.
Reproduced against the shipped greenfield example with an incident naming `auth`:

```
domains type: <class 'dict'>
domain keys: ['auth', 'catalog', 'orders']
risky_domains -> {}
touches_risky(['app/services/auth.py']) -> False
```

`plan_select.source_paths()` has the identical bug (`plan_select.py:24-26`), so `multi_domain` is
always False:

```
source_paths(manifest) -> []
multi_domain would be  -> False  (manifest declares 3 domains)
```

That kills the `engages: { multi_domain: true }` steps as well. Note what this means for the design:
after §4 ships as written, the incident raise is **still** dead, because it lives in
`risky_domains`, not in `engages`. The design fixes the thing that was not broken.

There is a third break on the same boundary. `plan_select.py`'s manifest and incident defaults point
at paths that exist nowhere else in HITL:

```
$ grep -rno "[a-z0-9./_-]*system-manifest.yaml" --include=*.md --include=*.sh --include=*.py ai/ tools/ ci/ | ... | sort | uniq -c
  82 docs/system-manifest.yaml
   1 docs/02-design/system-manifest.yaml       <- plan_select.py:155, the only occurrence
$ ... incident-registry.yaml
  19 docs/04-operations/incident-registry.yaml
   1 docs/03-engineering/incident-registry.yaml <- plan_select.py:156, the only occurrence
```

and `selection.md`'s two shipped command blocks (`:44-45`, `:84-86`) pass **neither** `--manifest`
nor `--incidents`. So both manifest-derived signals resolve to `{}` at the only call site that
exists. §2 and §4 build the whole feature on a channel that has never carried a byte.

---

## I8 — MEDIUM. The `impact` catalog step has no honest status once the work moves

`impact` is step 3 of the `development` workflow (`ai/shared/workflows.yaml:39`,
`crit: standard, crit_by_tier: { 3: floor }`). §1 moves the work to intake 3a; §6 removes it from
apply-change. What status does the step carry in the file the generator writes at step 6?

The generator can emit exactly four (`start-change/SKILL.md:270, :352-353`):

```python
STATUS_FOR = {"defer": "skipped", "decline": "skipped", "starter": "starter"}
...
    st = STATUS_FOR[ch["disposition"]] if ch else ("current" if s is first else "open")
```

There is no `done`. So:

- `open` — the breadcrumb and the plan say impact is still to do, after it has been done. The user
  is routed back into it at apply-change, which §6 just deleted.
- `skipped` — needs a record. At tier 3 `impact` resolves to `floor`, so `check_skips.py` demands
  `ack_by` (`FLOOR_NO_ACK`, non-waivable) for a step that was actually **performed**. Recording
  "declined" for completed work is exactly the false-but-attributed record B2 flagged as the worst
  shape a record can take.
- deleted from the plan — `INCOMPLETE_PLAN`, non-waivable, at tier 3
  (`check_skips.py:296-301`), and `PLAN_PRUNED` below it.

None of the three is honest. The design needs a fourth: a step that intake completed.

---

## I9 — MEDIUM. The plugin/product boundary is crossed with opposite precedence inside one intake run

What crosses: the skill prose (plugin only), `workflows.yaml` (plugin `shared/`, copied to product
`ci/first-pass/`), the validators/rankers (plugin `shared/ci/first-pass/*.py`, copied to product
`ci/first-pass/`), and the change file (product only).

The precedences disagree:

| Reader | Prefers |
|---|---|
| Step 6 generator, catalog (`SKILL.md:243`) | **plugin** `$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml`, then `ai/shared/workflows.yaml` — never the product copy |
| Step 6 generator, `resolve_crit` (`SKILL.md:257`) | **plugin** `shared/ci/first-pass`, then `ci/first-pass` |
| `selection.md:41-42` | **product** `ci/first-pass/plan_select.py` + `ci/first-pass/workflows.yaml`, then plugin |
| Step 6b `check_skips` (`SKILL.md:434-436`) | **product**, then plugin |
| `check_skips._default_workflows()` | **product** `ci/first-pass/workflows.yaml`, then `ai/shared/workflows.yaml` |

So in a single intake run on a project that has upgraded the plugin but not run `/hitl:dev-update`,
the plan and its criticality come from the **new** catalog while the ranking, the selection and the
certification come from the **old** one. §7's *"has no ranking data, so shortening is off and nothing
changes for them"* describes one knob; there are two, read by different halves of the same step.

It also fails loudly in the ordinary direction. New skill prose driving the old product-copy script:

```
$ python3 ci/first-pass/plan_select.py render ... --domains billing --dependents checkout
plan_select.py: error: unrecognized arguments: --domains billing --dependents checkout
EXIT=2
```

Any flag §4 needs is an intake-blocking crash until `/hitl:dev-update` runs. §7 should say so; today
it says "nothing changes for them".

---

## I10 — MEDIUM. §5's four off-switches have no owner named, and two do not exist

- *"confidence is `unknown`, or something touched is undeclared"* — no component computes
  `confidence`; §3 declares the field and §5 branches on it. New owner required, unnamed.
- *"the project has no manifest"* — today indistinguishable from "manifest at a path
  `plan_select.py` does not look in" (I7). `_load()` swallows every exception and returns `{}`
  (`plan_select.py:135-140`), which is also how it reports a *corrupt* manifest.
- *"the ranking data is missing or incomplete"* — `sizable()` fires at **half** coverage:
  `len([k for k in keys if costs.get(k)]) >= max(1, len(keys) // 2)`. "Incomplete" and "sizable" are
  both true between 50% and 99%. This is finding C4, unaddressed by the design.
- *"the workflow is anything other than `development`"* — no such check exists anywhere.
  `--workflow` is an argparse default of `"development"` (`plan_select.py:147`), so today a `docs`
  change with the flag omitted is sized against the development plan (finding C10). If §5 means this
  to be a gate, it needs a reader of `workflow.id`, not a flag.

---

## I11 — LOW. §3 hands over strictly less than apply-change steps 4–6 consume

§6 says apply-change *"becomes the thing that plans the implementation"*, and its Steps 4, 5 and 6
each open with "Based on the impact analysis" / "If infrastructure is affected". Against §3's block:

- Step 4 (Documentation Plan) wants *"the specific files **and what needs to change in each**"*;
  §3 gives `docs: [path]`.
- Step 5 (Test Case Plan) wants *"which specific test **files/functions** assert on changed
  behavior"*; §3 gives `tests: [tests/billing/]` — a domain-level directory from the manifest.
- Step 6 (IaC Review) wants Terraform/manifest/config files, new secrets, jobs, migrations. §3 has
  **no field for infrastructure at all**, and `iac` is a `standard` step in the plan.

Narrowing a channel is a legitimate design choice; doing it silently while telling the downstream
step it still has what it had is not.

---

## Boundaries I attacked and could not break

Stated plainly, per the brief:

- **H1/H2, the intake ordering 3 → 3a → 3b → 4.** Impact before tier before selection is the right
  order: the tier decides which steps are `floor` and therefore locked, so the selection genuinely
  needs 3b to have run. This part of §1 is sound.
- **A top-level `impact:` block does not break any existing parser.** Reproduced above:
  `hitl_scalar`, `hitl_change_active`, `hitl_current_n` and `hitl_steps` all read correctly with the
  §3 block inserted, and `check_skips.py` ignores it. The awk anchors (`^k:`, and steps read only
  inside `workflow: → steps:`) hold.
- **6b's position is right.** `check_skips.py` after the generator, before the Step 7 commit, with
  `--rollup` deliberately omitted, is the correct place for a certifier. The problem is upstream of
  it, not in it.
- **§7's "an existing change file is never re-read or rewritten"** is consistent with intake-only
  writing, and a project mid-change across an upgrade keeps its file intact — confirmed by the
  round-3 upgrade review's Priority-3 result, which I did not re-run.
- **§8's scope exclusions** cross no boundary I could find. The compound-agentic manifest fields are
  additive and per-check activated; reading `domains` only does not touch them.

---

## Verdict

**NOT SOUND.**

**The smallest change to the design that fixes the load-bearing pair (I1 + I2):**

Add one sentence to §1 naming the artifact and one to §6 removing the second decision:

1. **§1, between steps 4 and 6:** *"Step 4 writes the selection to `.hitl/first-pass-choices.json`;
   step 6's generator consumes it and deletes it, as it does today. `plan_select.py apply` and the
   wiring guard that forbids a choices file under `start-change/` are both removed with it."*
   That names the artifact, restores the generator's only input channel, and — critically — the
   design must say the guard is **inverted**, not merely tolerated, or the build fails on the first
   commit.
2. **§6, first bullet:** *"Its first step may **challenge** the tier and stop, but may not change it.
   A tier that needs revising is a new intake."* The tier must be final before the ledger is written,
   because `crit` is resolved from it at write time and re-resolved from it at every PR.

Those two sentences close H3 and H6. They do not close H5, H7, H8, H9 or H10 — I3 through I10 each
need the design to name a producer, a consumer and a moment the way the table at the top does. The
recurring root cause across all four attempts is that this design describes **where steps sit**, and
every failure has been about **what passes between them**.
