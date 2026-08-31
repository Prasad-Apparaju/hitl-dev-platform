# Consequence — design review, `docs/design/right-sizing/01-design.md` (issue #97)

**Under review:** the design document only, at `feb2cc3` on `main`.
**Lens:** consequence — what this destroys, exposes, or makes unrecoverable.
**Stance:** refute. Assume it causes harm and go looking for it.
**Method:** every claim below about how HITL behaves today was run or quoted, not recalled. Fixtures
were built in `mktemp -d` from the working tree's `ci/first-pass/*.py`, `ai/shared/workflows.yaml`
and `docs/examples/greenfield/docs/system-manifest.yaml`. Nothing tracked was modified.

**Verdict: NOT SOUND.**

The design argues about *which facts feed the sizing*. It never touches *how the cut is made*. The
cut is `rest[:8]` — a fixed constant in `plan_select.py`. Every improvement in sections 2, 3 and 4
reorders a list whose length is decided by `OFFERED = 8`, so none of them can change how many steps
are skipped or which criticality classes land in the skipped set. Meanwhile the design removes the
one human gate that existed to catch an under-counted blast radius, and it does its worst work on
exactly the class of change it was written to help.

---

## C1 — CRITICAL. The cut is a constant, so the design's safeguards cannot reach it

`ci/first-pass/plan_select.py:21`:

```python
OFFERED = 8                       # how many decidable steps are shown; the rest collapse
```

`build()` returns `locked, rest[:OFFERED], rest[OFFERED:]`. The tail is skipped by default and
written straight into `skips[]` by `apply`. Nothing in the design changes this. Sections 2, 3 and 4
change what goes into `paths` and `engages`, which affects **ordering inside `rest`** and nothing
else.

Reproduced. Same plan, same tier, five different changes:

```
python3 plan_select.py render --workflow development --tier 2 --paths <varies>
```

| change | steps auto-skipped |
|---|---|
| `app/services/auth.py` | 21 |
| `docs/runbook.md,infra/main.tf` | 21 |
| `web/components/Login.tsx` | 21 |
| *(no paths at all)* | 21 |
| `auth,orders` (domain names, i.e. the design's own output shape) | 21 |

The **set** of skipped steps is identical in four of the five, and in the fifth (`docs+infra`) the
only difference is that `docs` and `iac` moved to the *front of the tail* — engaged, correctly
identified as relevant, and still skipped, because eight higher-cost steps outrank them and the cut
is a count.

This is the finding that decides the verdict. A design about right-sizing that does not mention the
number that determines the size is not a design about right-sizing.

**Why the ranking cannot compensate.** `rank.py:103,106`:

```python
    i -= 1
...
    return RANKS[max(0, min(len(RANKS) - 1, i))]
```

The demotion clamps at zero, so `engages` is a **no-op for every step whose `forgo_cost` is `low`**
— `figma`, `roi`, `training`, `refactor`, `figma_compare`, `roi_30`, `roi_90`. Of the ten
`engages`-gated steps in the catalog, only four can move at all, and one rank of movement is never
enough to cross an eight-item cut line. Section 4 is cosmetic.

---

## C2 — CRITICAL. The design shortens most where the code matters most, and least where the pain was

Section 5 turns shortening **off** when "something touched is undeclared". Section 2 sends anything
no domain claims to `undeclared / confidence: unknown`.

Now read the case this whole feature exists for, `ai/claude/start-change/right-sizing.md:7`:

> A user asked for `FIRECRAWL_API_KEY` to be added to `demo.sh`. It ran to eleven recorded steps
> [...] They reported the tool as broken.

`demo.sh` is not in any manifest domain. `right-sizing.md:22` defines the class explicitly:

> **Non-source** means scripts, config, CI workflows, docs, examples, fixtures, lockfiles — anything
> outside the `paths` of a domain in the system manifest.

So under this design the motivating change resolves to `undeclared`, confidence `unknown`,
shortening **off**, full 31-step plan. The design inverts its own founding example.

The mirror image is worse. A change confined to a well-declared domain — every file listed, `lld`
present, `tests` listed — resolves to `confidence: declared` and gets maximum shortening. Declared
domains are the product. Undeclared paths are the shell scripts. **This design applies its heaviest
process to shell scripts and its lightest to the product.**

### The concrete change that should get 31 steps and gets a short plan

A session-invalidation fix in a declared `auth` domain: shorten the refresh-token TTL and add a
revocation path. Every touched file is in `domains.auth.files`. `lld` exists. `tests` listed.

Why the safeguards miss it:

1. **Confidence is a path-coverage measure, not a completeness measure.** Section 2's flowchart
   computes confidence solely from "which domain claims these files". All files are claimed, so
   confidence is `declared`. Nothing asks whether `depends_on`, `facade_apis`, `events_emitted` or
   `boundary_entities.consumed_by` are *complete*. The change is confidently sized on an entry that
   is confidently wrong.
2. **`dependents` is derived from a field nothing validates and a scanner that under-reads.**
   `tools/generate-manifest/generator.py:199` sets `"depends_on": sorted(domain["imports_from"])`,
   and `imports_from` is populated at line 71 by `if isinstance(node, ast.ImportFrom) and
   node.module:` — **`ast.Import` is not handled**, so `import app.services.auth` is invisible; the
   scan is `rglob("*.py")`, so every non-Python caller is invisible; and HTTP calls, queue
   consumers, cron jobs and shared tables were never in scope. `depends_on: []` on an auth domain
   with three real consumers is the normal case, not the pathological one.
3. **The two ranker signals that would have raised the rank are dead on a real manifest.** The
   manifest schema declares `domains` as `map[string, DomainEntry]`
   (`ai/claude/generate-docs/templates/system-manifest.schema.yaml:23`) with a `files` key. Both
   consumers read it as a **list of dicts with a `paths` key**:

   ```python
   # rank.py:141-143
   for d in ((manifest or {}).get("domains") or []):
       if isinstance(d, dict) and d.get("name"):
           doms[d["name"]] = [p for p in (d.get("paths") or []) if isinstance(p, str)]
   # plan_select.py:24-26
   def source_paths(manifest):
       return [p for d in ((manifest or {}).get("domains") or []) if isinstance(d, dict)
               for p in (d.get("paths") or []) if isinstance(p, str)]
   ```

   Iterating a dict yields keys (strings), so `isinstance(d, dict)` is False for every domain.
   Verified against `docs/examples/greenfield/docs/system-manifest.yaml`:

   ```
   risky_domains -> {}
   source_paths  -> []
   touches_risky(['app/services/auth.py']) -> False
   ```

   `risky_domain` therefore never raises a rank, and `multi_domain` is permanently False.
4. **The paths never arrive anyway.** `ai/claude/start-change/selection.md:41-45` invokes
   `plan_select.py` with `--workflows --workflow --tier --profile --tags --paths` and passes
   **neither `--manifest` nor `--incidents`**, so both defaults apply:
   `--manifest docs/02-design/system-manifest.yaml` and
   `--incidents docs/03-engineering/incident-registry.yaml` (`plan_select.py:155-156`). Neither path
   exists anywhere in this framework. `grep -rn "system-manifest.yaml"` over `ai/ ci/ tools/`
   returns **81** hits for `docs/system-manifest.yaml` and **1** for `docs/02-design/…` — the
   argparse default itself. The incident registry lives at `docs/04-operations/incident-registry.yaml`
   in 18 places. `_load()` catches with a bare `except` and returns `{}`, so both files load empty
   and silently.
5. **`profile` and `tags` do not exist.** `grep -n "profile\|tags"
   ai/shared/templates/change-context.schema.yaml` returns nothing. No skill sets them. So every
   step gated on `engages: {profiles: [...]}` or `{tags: [...]}` — including `test_plan`,
   `forgo_cost: medium`, "QA knows what *working* means" — is unconditionally demoted.

**Result, reproduced end to end.** Tier 2, `--paths app/services/auth.py`, keeping the four steps a
reasonable person would tick:

```
$ python3 plan_select.py apply --tier 2 --paths app/services/auth.py \
      --keep issue,impact,review1,verify_pr --actor alice
wrote 25 skip records to .hitl/current-change.yaml
$ python3 check_skips.py .hitl/current-change.yaml
[warn] FP_ABSENT_ENFORCED: ...
exit=0
```

Twenty-five declines, and **the fail-closed validator certifies it clean**. Among them: `test_plan`,
`docs`, `iac`, `conventions`, `review2`, `rerun`, `reconcile`, `impact_brief`, `verify_red`,
`adv_code`, `test_review`, `packet`.

At **tier 3** — the tier `dev-practices` reserves for cross-domain and non-trivial work — 16 steps
are auto-declined and the validator still exits 0:

```
skipped: figma, roi, docs, iac, test_plan, training, test_review, refactor,
         conventions, review2, rerun, reconcile, impact_brief, figma_compare, roi_30, roi_90
exit=0
```

**What goes wrong afterwards.** The TTL change lands. `orders` held a session assumption that the
static Python scan never saw. `impact_brief` was skipped, so no downstream team was told.
`review2` was skipped, so one reader carried a cross-domain change alone. `rerun` and `reconcile`
were skipped, so review findings were edited in and neither re-tested nor closed out. `test_plan`
was skipped, so QA verified against the code rather than against acceptance criteria. The incident
lands in production, and the artifact HITL leaves behind says a named human declined all of it.

---

## C3 — CRITICAL. Section 5 is the wrong list, and the right one is a different axis

Section 5 gates shortening on **data availability**: unknown confidence, undeclared paths, no
manifest, missing ranking data, non-`development` workflow. Every one of those is a question about
whether the *tool* has enough input. None is a question about whether the *change* is dangerous.

A change can satisfy all four bullets perfectly and still be the one you must not shorten. What is
missing from the list:

- **Auth, session, permission and tenancy boundaries.** `ai/shared/adversarial-review.md:84` already
  names the trigger set — "auth, secrets, permissions, a trust boundary" — and `right-sizing.md:48`
  already carves it out for the tier probe: "It does not survive a real risk signal." Section 5
  inherits neither. A well-declared `auth` domain is the *best* case for shortening under this list.
- **A facade API or boundary entity changing shape.** The design *reads* `facade_apis` and puts them
  in the block (section 3, `facades: [POST /refund]`), then does nothing with the fact. Today
  `apply-change/SKILL.md` Step 3 refuses outright: "If backwards-incompatible changes are
  identified, flag them explicitly in the summary and **do not proceed to planning without a
  compatibility strategy**." Section 6 deletes the step that carries that refusal and does not
  re-home it.
- **Irreversible or externally-visible effects.** The manifest carries `facade_apis.mutations` with
  an explicit instruction to "Mark IRREVERSIBLE effects explicitly"
  (`system-manifest.schema.yaml:71`). The design's section-2 table does not read `mutations`.
- **A domain with incident history.** Section 4 concedes the incident check "cannot [match on domain
  names] today" but attributes it to path-vs-name matching. The actual cause is C2.3, the dict/list
  shape bug in `risky_domains`, which the design does not name — so a faithful implementation of
  section 4 leaves the check just as dead.
- **Data migration or schema change.** Absent from the manifest, absent from `engages`, absent from
  section 5.
- **Multi-domain scope.** `multi_domain` is `len(source_paths(manifest)) > 1` — a property of the
  *project*, not the *change*. Broken today it is always False; naively repaired it becomes always
  True on any project with two domains. It never means "this change spans domains" in either state.
  `review2`, `impact_brief` and `integration_verify` are gated on it.
- **Nothing about the change file's own `manifest.domain` being singular.** The schema has
  `manifest.domain` as one string (`change-context.schema.yaml:131-139`). The design's section-3
  block emits `domains: [billing]` and `dependents: [checkout, reporting]`. There is no `impact:`
  key in the change-context schema at all — verified by listing its top-level keys. The design's
  central artifact has nowhere to live and the design does not say so.

Section 5's list also fails *open* in a way the design does not notice. When `sizable()` is False,
`build()` returns `locked, rest, []` — the tail is empty and **all** of `rest` becomes offered. On a
34-step development plan at tier 2 that is 24 checkboxes. `selection.md:74-76` states the UI ceiling
itself: "`AskUserQuestion` [...] caps at four options per question and four questions" — sixteen. So
"shortening is off" does not produce the full plan; it produces a selection the tool cannot render,
after which the operator improvises a `--keep` list and everything omitted from it is declined.
The safeguard's failure mode is an unbounded manual cut.

---

## C4 — HIGH. A confidently-wrong manifest is invisible to `ci/manifest-drift`, by construction

The design's section 2 replaces "read the source" with "read the manifest, and read source only
where the change goes beyond it". The only thing standing behind that trade is
`ci/manifest-drift/check_manifest_drift.py`. Here is exactly what it does and does not do.

**What it checks** (docstring, lines 4-14): unlisted files, deleted files, cross-domain imports,
missing facade coverage.

**Severities**: only DELETED FILES is an error by default. UNLISTED FILES, CROSS-DOMAIN IMPORT and
MISSING FACADE are warnings and exit 0 unless `--strict`, `--fail-cross-domain-imports` or
`--fail-missing-facade` is passed. The design never says intake runs this checker at all.

**What it cannot catch, every one of which the design now depends on:**

| design reads | validated by manifest-drift? |
|---|---|
| `depends_on` ("who breaks if this changes, read backwards") | **no** — the string `depends_on` does not appear in the file |
| `events_emitted` / `events_consumed` | **no** |
| `boundary_entities` / `consumed_by` | **no** |
| `tests` | **no** — no check that the listed test files exist or cover anything |
| `lld` | **no** — no check the path resolves |
| `owning_fr` | **no** |
| `last_changed` | **no** |
| `facade_apis` | name-existence only, and only as a warning |

Scope limits on the checks that *do* exist: `_collect_source_files` is `base.rglob("*.py")` and
`check_unlisted_files` skips `__init__.py`. A TypeScript, Go, Java or Ruby project gets no unlisted
detection, no cross-domain-import detection and no facade coverage at all. `check_cross_domain_imports`
only fires when both files are already listed and the import is an exact dotted match of a listed
path — dynamic imports, DI, HTTP and message-bus coupling are all outside it.

**And `last_changed` is not the staleness hint section 2 claims it is.**
`tools/generate-manifest/generator.py:201-204` stamps it at generation time:

```python
"last_changed": {
    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    "summary": "Auto-generated — needs review",
},
```

That is when the *generator ran*, not when the *domain changed*, and a re-run marks every domain
fresh whether or not anything moved. Section 2's row "`last_changed` | whether that description is
likely still true" is false, and open question 2 is therefore asking about a signal that does not
exist. Answer to question 2: `last_changed` cannot be used, and `partial` must not shorten, because
`partial` and `declared` are both computed from path coverage and neither says anything about the
fields the shortening actually consumes.

There is one further trap. The design's premise — "read source only where the change goes past what
is written down" — is circular at intake. To know whether the change goes past the manifest you must
read either the change (which does not exist yet) or the source (which the design is avoiding). The
only remaining input is the developer's description, so the entire safeguard chain
(paths → domain → confidence → shortening) is downstream of an unverified forecast. Compare what
`apply-change/SKILL.md` Step 3 says today: "**Search the codebase to verify each item. Don't guess —
read the files.**"

---

## C5 — HIGH. Removing the impact step from `dev-apply-change` orphans four things anchored to it

Section 1 says "Nothing else moves." Section 6 says "Its impact analysis step is removed." Both
cannot be true. Four mechanisms are anchored to that step *by name*:

**1. The TA scope gate — the only human check on an under-counted blast radius.**
`ai/claude/architect/design-feature/SKILL.md:174` sets `status: awaiting-scope-approval` after the
impact summary. `ai/claude/ta-approve/SKILL.md:89-93` gives the checklist:

> 1. Are the affected domains correct — neither over-counted (scope creep) nor under-counted
>    (**hidden blast radius**)?
> ...
> 4. Are any backwards-incompatible changes flagged with a compatibility strategy?

`ai/codex/AGENTS.md:42` confirms `awaiting-scope-approval` blocks source edits until a human
advances it. This gate exists **precisely** to catch the failure mode C2 describes. Under the
design, the plan is cut at intake step 4 from facts nobody has reviewed, and the gate that reviews
those facts — if it survives at all — now runs downstream of the decision that consumed them. That
is the single most consequential structural change in the document, and section 6 describes it in
one sentence without naming the gate.

**2. The skip roll-up narrowing.** `start-change/SKILL.md` Step 6b, verbatim:

> **No `--rollup` here, deliberately.** The roll-up is written at the impact step, once the change
> knows its own area — so at intake every skip would warn as missing from a ledger it cannot be in
> yet.

and `apply-change/SKILL.md` Step 7a, verbatim:

> Run this **immediately after Step 7**, and only here. [...] Called at intake, before
> `manifest.domain` and `allowed_paths` exist, it matches nothing and silently says nothing.

The design moves impact analysis to intake but leaves `manifest.domain` and `allowed_paths` written
at apply-change Step 7. So resurfacing still cannot run at intake, and the step it was anchored to
is gone. Unresolved skips from earlier changes stop being surfaced. Nothing in the design notices.

**3. `allowed_paths`, which gates every file edit.** `ai/claude/hooks/check-domain-boundary.sh:57-65`
reads `allowed_paths` from the change file and blocks edits outside it. Today that list is written
from a source read. Under the design its only available source is the declared `files` of the looked-up
domain, so a file that exists but is not declared — the UNLISTED FILES warning class — now trips the
hook, whose own remedy text is "Add the path to `allowed_paths`" (line 129). The recovery path for
manifest staleness becomes "widen the declaration", which is the drift, written down.

**4. Effort, ROI and token estimation.** `ai/claude/dev-practices/workflow-steps.md:51`:

> **3. Impact Analysis** [...] Produces an effort estimate. Outputs `.hitl/current-change.yaml` with
> change ID, tier, affected domains, source artifact paths, and `token_tracking.estimated`

and step 4 immediately after: "If the Impact Analysis effort estimate exceeds 1 day, record the ROI
section". Also `ai/claude/ops/audit-dependencies/SKILL.md:195` schedules the CVE gate "Design phase,
after Impact Analysis, before implementation". All three lose their anchor.

---

## C6 — HIGH. Section 7's upgrade claim is false for the half that matters

Section 7: "A project that updates the plugin but not its own copy of the workflow file has no
ranking data, so shortening is off and **nothing changes for them**."

The shortening half is correct, and I verified it: `git show v2.8.0:ai/shared/workflows.yaml | grep
-c step_costs` returns `0`, and `ci/first-pass/plan_select.py` and `rank.py` did not exist in v2.8.0.
`init-project.sh:222` unconditionally copies the catalog into the project
(`cp ai/shared/workflows.yaml "$TARGET_DIR/ci/first-pass/workflows.yaml"`), and `selection.md:42`
resolves **project first** (`WF="ci/first-pass/workflows.yaml"; [[ -f "$WF" ]] || WF="$ROOT/shared/workflows.yaml"`).
So a stale project catalog wins, `sizable()` is False, nothing collapses. That much holds.

"Nothing changes for them" does not. The **procedure** is not a project file.
`tools/scripts/init-project.sh:325-338`:

```bash
  # Skills — symlinks from .claude/commands/ to the platform SKILL.md files.
  # Claude Code discovers commands from this directory; symlinks mean platform
  # updates propagate without re-running this script.
```

and every `/hitl:dev-*` command resolves through `$CLAUDE_PLUGIN_ROOT`. So the moment the plugin
updates — with no `dev-update`, no consent, no notice — that project gets:

- impact analysis moved into intake (new `start-change/SKILL.md`), and
- impact analysis **removed** from `dev-apply-change` (new `apply-change/SKILL.md`),

while shortening stays off because the data half is gated on `dev-update`. That is the worst of both
states: they lose the step from where it was, they lose the four mechanisms in C5 that were anchored
to it, and they gain nothing in exchange. Section 7 describes this population as unaffected.

There is a second, sharper split in the same run. The Step 6 generator resolves the catalog and the
criticality resolver **plugin first**:

```python
for p in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/workflows.yaml"),
          "ai/shared/workflows.yaml"):
```
```python
for d in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/ci/first-pass"), "ci/first-pass"):
```

and never looks at `ci/first-pass/workflows.yaml` at all. `selection.md` resolves the same two things
**project first**. Under this design both run inside one intake command, so the change file's
`workflow.steps` comes from one catalog while the selection that dispositions those steps comes from
another. `rank.py:36` warns about exactly this class of split — "Import it rather than agreeing with
it by coincidence" — while the two skills disagree about which copy is authoritative.

Third: the design's own step order cannot use the mechanism it inherits. Section 1's flowchart puts
"4. shorten the plan" **before** "6. write the change file". `plan_select.py apply` refuses without
one: `"no change file at %s — intake creates it; run /hitl:dev-start-change first"`. So the design as
drawn must go back to `.hitl/first-pass-choices.json`, which `selection.md:81-83` calls out as the
defect just removed:

> **Not a choices file.** [...] writing one here records for a consumer that never comes. An earlier
> version of this feature did exactly that.

That is the wiring-defect class this project already named. The design reintroduces it in a diagram.

---

## C7 — HIGH. Question 3 answered: every available answer for accountability is worse than the last

The design asks who is named for a skip recorded at intake, and observes "Only one person is there."
The problem is not that there is one person. It is that the record will name them for decisions they
were never shown, with a reason field that argues against the skip.

Verified. From the 25 records `plan_select apply` wrote:

```yaml
- step: test_plan
  crit: standard
  disposition: decline
  actor: alice
  reason: 'not selected at right-sizing (rank low): QA knows what "working" means for
    this change before anyone builds it.'
```

Three separate defects in one record:

1. **The reason is the `protects` sentence.** The ledger's reason column — the field a later
   reviewer, `resurface.py`, or a PR auditor reads to judge whether a skip was justified — contains
   a statement of the value that was given up. Every entry reads as "alice declined this because it
   was important." The audit trail is not merely thin; it is inverted, and at scale it is unreadable
   as evidence.
2. **The disposition is `decline`, the one with no obligations.** `check_skips.py:389` warns when a
   `defer` has no `followup_ref`; `decline` carries no such requirement. The mechanical tail
   therefore records the strongest form of "never doing this" with nothing to bring it back.
3. **`actor` is an unverified free string the agent types.** `selection.md:86` passes
   `--actor "<the person, not you>"`. Nothing checks it against anything.

Now the adversarial pass on each candidate answer:

- **The developer at intake.** They confirmed eight checkboxes. Twenty-one further declines were
  attributed to them from a collapsed line reading `+ 21 more, skipped and recorded: packet,
  adv_design, design_plus, verify_red, adv_code, rerun …`. `selection.md:12` states the governing
  principle itself: "**You cannot pick from a list you were never shown.**" Attribution without
  visibility is manufactured accountability, and it is worse than an unattributed record, because a
  named record stops anyone asking who decided.
- **The TA or tier-setter.** Not present. `tier_set_by` is only required at tier ≤ 1
  (`start-change/SKILL.md` Step 6 generator: `if tier <= 1 and not (tier_set_by.strip() and
  tier_reason.strip())`). At tier 2 and 3 — where C2 showed 25 and 16 auto-declines — nobody is
  named for the tier either.
- **The agent.** Explicitly forbidden, twice, in the same generator: "a skip is accountable to a
  person, not the agent."
- **Defer it to a later reviewer.** The later reviewer was the TA scope gate and the resurfacing
  pass, and C5 shows the design orphans both.
- **Nobody / omit the field.** `check_skips.py` blocks a skip with no actor. Fail-closed, correct,
  and it means the shortening path cannot run without producing a name.

The honest answer to question 3 is that under this design **no answer is defensible**, because the
tail is not a decision anyone made. The accountability question is unanswerable while `OFFERED = 8`
decides the cut.

---

## C8 — MEDIUM. Moving impact analysis into intake taxes the changes the feature exists to make cheap

Question 1 asks whether intake becomes too heavy. It does, and the cost falls asymmetrically.

Intake is not optional. `start-change/SKILL.md` calls itself "the **enforced front door**", and
`check-hitl-context.sh` blocks all guarded edits until it completes. Everything added to intake is
paid by 100% of changes before any of them can begin.

Today intake already runs: active-change check, `gh issue list`, `gh issue view`, workflow
classification with confirmation, tier proposal with confirmation, full phase plan, First Pass
disposition menu, branch creation, a ~140-line Python generator, `check_skips.py`, `resurface.py`,
commit, push. The design adds impact analysis, a tier re-confirmation on evidence, and the
eight-item selection — three more interactive stops — and removes nothing.

Who leaves: the developer with the one-line fix. C2 shows why the tax lands hardest on them. Their
`demo.sh` change is `undeclared`, so shortening is off and they pay the *full* new intake and then
get the *full* 31-step plan. `right-sizing.md:9` records that this exact person "reported the tool
as broken." This design makes their path longer.

The design's own alternative in question 1 — shortening as its own command between the two — is the
better shape and the document does not argue for it. It keeps the front door thin, and it puts the
sizing decision after `manifest.domain` and `allowed_paths` exist, which is what `apply-change` Step
7a and `check-domain-boundary.sh` both need.

---

## C9 — LOW. Two smaller claims that do not survive checking

- **Section 1: "The skip check stays at 6b and starts working, because the record now exists by the
  time it runs."** Step 6b works today: Step 4b's choices are written by the Step 6 generator, and
  6b certifies them. What changes is coverage, not function. Separately, `start-change/SKILL.md`
  Step 6b claims "a lightened step with no `first_pass` flag exits 2 and is non-waivable." It does
  not — `apply` never sets `first_pass`, and the validator emits
  `[warn] FP_ABSENT_ENFORCED` and **exits 0**. Verified on both fixtures above.
- **Section 5, "the workflow is anything other than `development`."** Nothing enforces this; it
  happens to hold because `step_costs` keys only overlap the `development` catalog. Measured
  coverage: `development` 34/34 sizable, `brownfield` 1/11, `migration` 0/9, `docs` 2/6, `release`
  0/12, `platform` 0/17, `prd` 0/5. Anyone adding a cost entry for a shared key silently turns
  shortening on for a workflow the design says it is off for.

---

## Sound sections

Section 8 (not in scope) is sound: leaving profiles/tags as advice, not touching protected steps or
the test-first rule, and reading domains only rather than the compound-agentic fields are all
correct scoping calls, and the last one is what keeps this out of `ci/manifest-agentic`'s
`depends_on_double_authored` check.

---

## Verdict

**NOT SOUND.**

**The smallest change that would fix it:** replace the fixed cut with a criticality floor on the
*automatic* tail. Only steps whose tier-resolved criticality is `ceremony` may collapse below the cut
line; anything resolving to `standard` or above must be shown individually and ticked or unticked by
a person, however long that list gets. One rule, expressible in one sentence in section 5, and it
removes the entire class in C1, C2 and C7 at once: `docs`, `iac`, `test_plan`, `packet`,
`design_plus`, `verify_red`, `conventions`, `review1`, `review2`, `rerun`, `reconcile`, `qa_verify`
and `impact_brief` can no longer be declined by a constant, and no human is ever named for a
decision they were not shown. It also makes question 3 answerable, because every remaining
attributed skip is one someone actually saw.

That is the smallest change. It is not the only one required before implementation. In priority
order, the design must additionally:

1. Name the C5 orphans and say where each goes — the TA scope gate above all. A design that removes
   the impact step without naming `awaiting-scope-approval` should not be implemented.
2. Add the risk axis to section 5 (auth/secrets/permissions/tenancy, facade or boundary-entity shape
   change, irreversible `mutations`, data migration, incident-history domain) and stop treating
   `declared` confidence as a licence.
3. Correct section 7 to say what actually propagates on a plugin update, and fix the opposite
   resolution precedence between `selection.md` and the Step 6 generator.
4. Fix or explicitly scope the four dead wires C2 documents — the `domains` dict/list shape bug, the
   two wrong argparse defaults, the absent `profile`/`tags` fields, and the `multi_domain` definition
   — since section 4 is built on top of all of them.
5. State where the section-3 impact block is persisted. There is no `impact:` key in
   `change-context.schema.yaml`, and `manifest.domain` is a single string.
6. Resolve the step-4-before-step-6 ordering, without reintroducing the choices file.
