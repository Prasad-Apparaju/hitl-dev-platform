# Implementation review 2 — right-sizing, run end to end

Ran the whole path in a scratch project (`mktemp -d`), twice: once with the plugin layout
(`$ROOT/shared/{workflows.yaml,ci/first-pass/}`), once with the onboarded-product layout
`init-project.sh` actually creates (`ci/first-pass/` + `ci/first-pass/workflows.yaml`, no `ai/`).
Stub → requirement filled → impact record → size → choices from the exclusions → generate → certify.
The pieces individually do their jobs. The path does not complete: certification blocks on the
pointer the generator itself wrote, and two of the three commands the skills give do not run at all
in the layout they ship into. Repo suite is green (408 passed), which is part of the point.

**1. The change file names an impact record that `check_skips` can never find.**
The stub emits `impact_record: ".hitl/impact/<id>.yaml"` and both skills say to write the record
there — repo-root-relative. `run()` passes `change_dir=os.path.dirname(abspath(change_path))`, i.e.
`<repo>/.hitl`, so the lookup is `<repo>/.hitl/.hitl/impact/<id>.yaml`. Ran from the repo root with
the record exactly where the skill puts it:
`[BLOCK] IMPACT_RECORD: change names impact record '.hitl/impact/GH-97.yaml' but it is not there`,
rc=2, non-waivable. Copied the record to `.hitl/.hitl/impact/` and the same command printed
`First Pass skip ledger: clean.` rc=0. The four unit tests call `C.check(..., change_dir=d)` with
`d` standing in for the repo root, so they encode the right semantics and never exercise `run()`.
Every right-sized change fails Step 6b.

**2. Two of the three commands in `start-change` don't execute in a product repo.**
- Step 4: `"$PY" "$SZ" ".hitl/impact/$CHANGE_ID.yaml" "$WFYAML" "$TIER" fast`. `$WFYAML` is set
  nowhere — one occurrence in the repo, this line. Ran verbatim:
  `FileNotFoundError: [Errno 2] No such file or directory: ''`, rc=1.
- Step 6: `gen_change.py` looks for the catalog at `$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml` then
  `ai/shared/workflows.yaml`. An onboarded repo has it at `ci/first-pass/workflows.yaml`
  (`init-project.sh:222`), and Step 4b's own comment says `CLAUDE_PLUGIN_ROOT` is unset in the Bash
  tool. Ran it there: `workflows.yaml not found`, rc=1, no change file.
- Step 6b's fallback `$ROOT/shared/ci/first-pass/check_skips.py` with no `--workflows`:
  `_default_workflows()` tries `here/workflows.yaml` and `here/../../ai/shared/workflows.yaml`,
  neither of which exists in the plugin layout, so the catalog loads empty and every skip is
  `[BLOCK] UNKNOWN_STEP` — 22 of them on my change. Three tools, three different catalog-resolution
  strategies, one of which matches the shipped layout.

**3. The reason recorded against a dropped step is the reason to keep it.**
`size_plan.why()` returns the `needed_now` sentence only when the step *is* needed; otherwise it
returns the `engages` sentence. So every fast-track exclusion where the step applies but isn't
needed now carries the affirmative finding, and `gen_change` writes it verbatim into `skips[]`.
From my run (tier 1, one-line fix):
`- { step: packet, ..., reason: "applies to every change", disposition: not_applicable }` — same for
`adv_design`, `design_plus`, `refactor`, `adv_code`, `review1`, `qa_verify`; `roi`/`roi_30`/`roi_90`
read `reason: "touches api"`. The design says the fourth disposition carries "the rule that decided
it as its reason", and this is the rule that decided it applies. That string is what the human
confirms, what goes to the roll-up, and what the retrospective reads back as what was left out.

**4. Seven of the eight workflows get no sizing, and say nothing about it.**
`step_costs` covers the development spine only: development 34/34 steps with rules, brownfield 1/11,
docs 2/6, migration 0/9, migration_review 0/5, prd 0/5, platform 0/17, release 0/12. A record naming
`workflow: release` sized at tier 2 printed fast=12 steps, full=12 steps, `excluded: 0`, every
outcome `"no rules declared for this step"`, exit 0. Fail-closed is the right default, but the two
options are then byte-identical and Step 4 still offers them as a choice. `test_the_record_workflow_
is_honoured_not_assumed` asserts brownfield returns brownfield steps and stops there. Related drift:
`tools/workflow-catalog/catalog.yaml` — the named source of truth — has a stray `retro:` entry in
`step_requires` (a copied `step_costs` body, no `needs:`) that is absent from `ai/shared/workflows.yaml`;
`derive.py` mentions neither block, so nothing compares them.

**5. Nothing checks the record against the change file, and "what the rules concluded" is never written.**
I set the record's `change_id` to `GH-999-some-other-change` and its `workflow` to `brownfield` while
the change file said `GH-97` / `development`: `First Pass skip ledger: clean.` rc=0. The schema says
"Must match `.hitl/current-change.yaml` change_id. A mismatch is a blocking error" — unimplemented,
so the sizing evidence may belong to a different change or a different catalog. Separately,
`rule_outcomes` is written by nothing: `size_plan` returns the right shape and its docstring says
`apply-change` runs it to record the outcomes, but `apply-change/SKILL.md` never invokes it and
could not — the tier does not exist until intake Step 4 and `size_plan` now refuses without one. So
the design's third part of the record, "what makes the retrospective's feedback loop possible", is
absent from every record the path produces. (Minor, same family: `size_plan` tracebacks rather than
refusing on a malformed record — `findings: "oops"` → `AttributeError`, empty file → `AttributeError`,
`tier: "high"` → `ValueError`. Boundary tiers are handled: 0 and 4 size correctly, 5/-1/2.5 refuse.)

**Smallest thing that stops it:** the impact-record path. The generator writes a pointer relative to
the repo root and the validator resolves it relative to `.hitl/`, so every right-sized change dies at
`IMPACT_RECORD`, non-waivable — and #2 means the two commands before it don't run in a real product
repo either. Not shippable yet.
