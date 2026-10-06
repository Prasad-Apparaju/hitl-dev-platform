# Intake detail: the workflow, the tier, the two options, and the skip record

Read from Steps 3b, 4, 4b and 6b of `dev-start-change`. SKILL.md has the decision points and the
commands that must run; this file has the detail behind them: what a `docs` change owes, what the
tier changes, what the two options look like when shown, how the checkbox questions are built, and
how a choice becomes an entry in the skip record, and what the skipped-line exit codes mean.

## Contents

- [The docs workflow](#the-docs-workflow)
- [What the tier changes](#what-the-tier-changes)
- [The two options, as shown](#the-two-options-as-shown)
- [The plan question](#the-plan-question)
- [The checkbox questions](#the-checkbox-questions)
- [Pre-selection comes from the rules](#pre-selection-comes-from-the-rules)
- [What a step can become](#what-a-step-can-become)
- [Filling the choices file](#filling-the-choices-file)
- [The skipped line at Step 6b](#the-skipped-line-at-step-6b)
- Resolving an id with another repository's prefix (Step 2)
- Workflow heuristics (Step 3b)
- "Fast Track" said during intake (Step 2)

## The docs workflow

Only for a change that touches nothing but documentation: no source, tests, or IaC. Docs *and*
code is a `development` change (the spine already reconciles docs), so `docs` is never a way
around the gates on real code. Its `doc_review` gate is domain-routed: Architect for design docs,
PM for product, Ops for runbooks. At its final `merge` step set top-level `status: merged` in
`.hitl/current-change.yaml`, so the file does not linger and satisfy the gate for the next change.

## What the tier changes

The evidence is in the impact record by the time the tier is proposed, so the proposal cites the
record rather than the issue's wording: three dependent areas and a data migration is a different
change from one flagged file with no callers. Asking for a tier before the analysis exists means
asking before the evidence exists, which is how a one-line change gets a multi-hour path.

Where protection actually changes, from the catalog: **3 → 2** takes `packet`, `arch_review`,
`qa_verify` and `rollout` off `floor`; **2 → 1** moves only `integration_verify`. `deploy`,
`promote`, the test-first cycle and the retrospective never demote. So **declaring 2 instead of 3 is
the consequential call.**

The sizer requires the tier as an argument and will not read one from the record: the impact
analysis is not allowed to set a tier, and two sources for that field disagree. `size_plan` returns
`outcomes`, what each rule decided and why. Append it to `.hitl/impact/<change_id>.yaml` as
`rule_outcomes`; without it the retrospective cannot ask whether a rule was right. It is written at
Step 4, not by the analysis, because sizing needs the tier and the tier does not exist until then.

## The two options, as shown

Two counts and a comma list read as a summary, not a choice. Show both options and list what Fast
Track leaves out, one step per line, every time, without being asked:

```
This change reaches: 1 area, no dependents, no interface or data change.

  Fast Track   16 steps   what this change needs before it ships
  Full Scale   26 steps   everything that applies to a change of this shape

  Fast Track leaves out (most consequential first):
    Baseline measurement        a before-number, so "faster" is measured
    Decision packet             the decision and alternatives, recorded
    Design verification         someone tries to break the design early
    Design update               the design catches up with what building taught
    Code verification           someone tries to break the implementation
    ROI estimate                a stated reason this is worth building
    Test review                 a person checks the tests assert the right thing
    Refactor                    code left in shape for the next person
    30-day ROI check            whether it was worth building
    90-day ROI check            the longer-term effect, looked at

  Always stays: the failing test and making it pass, the integration check, deploy,
  promote and the retrospective.

Recommended: Fast Track. Nothing it drops is protecting something this change touches.
```

Each line is the step's name as a person would say it, not the catalog label (`VfyDsn`), and a
short form of its `protects` line, ordered by `forgo_cost` then catalog order. "Always stays" is every
`locked` step from the sizer. One line on which is recommended and why. The recommendation is
advice, and taking Full Scale is not recorded. Write the two names exactly as shown, capitalized:
a different spelling each time is how a name stops being findable.

If the two options come out the same, say so and do not offer a choice.

## The plan question

Ask with the `AskUserQuestion` tool. It draws the options as a menu the person moves through with
the arrow keys, and `multiSelect` draws checkboxes. Do not ask "which do you want?" in prose.
One single-select question:

| field | value |
|---|---|
| `header` | `Plan` |
| `question` | `Which plan for <change_id>?` |
| options | `Fast Track (Recommended)`, `Full Scale`, `Pick steps myself`, with the recommended one first and carrying "(Recommended)" |
| `description` | Fast Track: "16 steps: what this change needs before it ships. You can tick any step back in next." Full Scale: "26 steps: everything that applies." Pick steps myself: "Start from Fast Track, then choose what to add back and what to leave out." |
| `preview` | on Fast Track and Full Scale, that option's ordered step list with the left-out steps under it, so moving between the two shows the difference |

## The checkbox questions

**Add back.** For Fast Track and for Pick steps myself, one `multiSelect` call over every step
Full Scale has and Fast Track does not:

- `question`: `Fast Track leaves these out. Tick any you want to keep.` With more than one question,
  number them (`... leaves these out (1 of 3). ...`): the tool rejects a call whose question texts
  repeat, or whose option labels repeat within a question.
- `header`: `Add back`, or `Add back 1` to `Add back 4` when there is more than one question.
- One option per step, in the same order as the list. `label` is the step's name (five words at
  most); `description` is its `protects` line and what leaving it out costs ("Leaving it out costs:
  medium").
- Four options per question, four questions per call: sixteen boxes. A question needs at least two
  options, so split five as three and two, not four and one. Past sixteen, box the sixteen most
  consequential, name the rest in the last question's text, and take names typed into the "Other"
  box the tool adds.
- Nothing ticked is Fast Track as proposed. A ticked step is kept. An unticked one is recorded at
  Step 4b: `not_applicable` with the rule's reason, or `defer` when the sizer lists it under `proposed`.

**Leave out.** For Pick steps myself, a second checkbox screen after the "Add back" one:
`Leave out any of these?` (header `Leave out`), over the steps in the plan a person may lighten.
That is every step that is not `locked`, not `no_omit` and not `issue` (intake has already done
it), lowest `forgo_cost` first, so the cheapest to drop comes first. A ticked step goes through the
disposition menu below, which says what it becomes. Offer the same screen after Fast Track when
someone says they want it lighter still. Full Scale asks nothing more.

**Steps that always stay are never checkboxes.** Dropping one needs a named person to accept the
risk, not a tick. List them, and say how to ask for a risk-accepted skip. Without the
`AskUserQuestion` tool (a host without it, a non-interactive run), print the same lists numbered and
take the numbers typed back; never drop the list.

Print the full ordered plan on request ("show me every step"), and always in full for a workflow
of 10 steps or fewer.

## Pre-selection comes from the rules

`size_plan.py` has already decided what applies and what is needed now, from what this change
reaches, not from the tier. Present the steps outside the chosen option pre-selected, each carrying
the finding that decided it as its reason: "no interface files in this change", "3 dependents".
Let one confirmation record the lot.

Those entries take the `not_applicable` disposition: the rules determined the step does not apply,
which is a different fact from a person choosing to skip it; otherwise Fast Track would record a
named human declining twenty-odd steps they never looked at.

A rule may never retire a load-bearing step. `not_applicable` on a `floor` or `no_omit` step is a
non-waivable block (`RULE_OVER_FLOOR`); those are dropped by a named person accepting the risk, or
not at all. The one exception is a **conditional** step (`cond:`) whose activator did not fire: it
was never in the plan, so the sizer records it `not_applicable`. The gate reads the impact record,
not the ledger: it must name this change and workflow, its `rule_outcomes` must match the rules run
on its own findings and show `applies: false`, and the security steps need `security_sensitive`
answered (silence is not a no); else `COND_UNCONFIRMED`, `RECORD_UNIDENTIFIED` or
`RECORD_CONTRADICTED`, all non-waivable. Active, a conditional step is protected like any other.

One floor pair is pre-filled rather than asked for twice: when the impact record says
`reaches_production: false`, offer `deploy` and `promote` under Leave out as `decline`, reason
"does not reach production (impact record)", `ack_by` the person confirming the plan (the validator
needs a named person; for these two Ops floor steps the confirmer is that person), so the one
confirmation records the accepted risk.

Steps the rules excluded (`excluded`) are pre-selected `not_applicable`; an active conditional
step Fast Track leaves out (`proposed`, e.g. baseline on an API change) is pre-selected `defer` by
the confirming person, never `not_applicable`. Both are "Add back" boxes only. A step ticked under
"Leave out" is a person lightening beyond that.

## What a step can become

A step's `crit` (catalog, resolved against the `tier`) says what it can become:

| step type | options offered |
|---|---|
| `ceremony` | keep · starter\* · skip (defer / decline) |
| `standard` | keep · starter\* · defer · decline |
| `standard` + `no_omit` (TDD RED/GREEN) | keep · starter — *never defer/decline* |
| `floor` | keep · *request risk-accepted skip* |

\*starter offered only for steps in the registry (`ci/first-pass/starters.py`); `keep` is the default.

For a ticked step, use its starter when it has one, otherwise `decline` for a ceremony step and
`defer` for a standard one. Say which in one line per step ("Test plan: a thin version now, marked
to enhance later"), and ask only if the person wants a different one. A ticket is filed only when
the person says "file this one" (one, for that step).

## Filling the choices file

Only non-keep steps go in the choices file; an absent step means keep. `actor` is the accountable
human, not the agent. Three rules when filling an entry:

1. **Floor.** A `floor` skip requires the accountable role's risk-accepted `ack_by` + reason, and
   (for a step mapping to a hard gate) a linked `waiver_ref`. A skip is **not** a waiver. Put both in
   the entry.
2. **Starter.** Write the honest-minimal artifact from `starters.py` (e.g. acceptance criteria = "a
   working version of the system"), mark it `needs-enhancement`, record its path. Listed on the
   issue's skipped line like a defer; no ticket unless asked for.
3. **Defer.** Leave `followup_ref` out; the generator sets `issue:<N>` (the change's own issue,
   where Step 6b writes the notice). A ticket ref goes there only when the person asked for one.

## The skipped line at Step 6b

`skipped_line.py --apply` writes one line between markers at the top of the issue body naming every
step left out, regenerated from the ledger, idempotent. Exit 3: `gh` could not edit the issue; say
so and carry on, the ledger is the record. Exit 2: no issue number (the id is not `GH-N`, so
`followup_ref` is empty and certify warned `DEFER_NO_FOLLOWUP`); say the left-out steps are in the
ledger only, and re-run with `--issue N` if there is an issue.

Entries with no area declared yet record as project-wide and resurface at any later change until
resolved; the impact step reads them and does not append. The append is idempotent on
`(change_id, step)`.

## Resolving an id with another repository's prefix (Step 2)

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"; LINKED="ci/linked/linked.py"; [[ -f "$LINKED" ]] || LINKED="$ROOT/shared/ci/linked/linked.py"; python3 "$LINKED" resolve <id>
```

Say which repository the id belongs to; it is not a change to start here.

## Workflow heuristics (Step 3b)

Labels: `bug` or `enhancement` point to development, `documentation` to docs. Wording: "migrate" or
"port" point to migration; "onboard" or "adopt HITL" to brownfield. Whether `docs/system-manifest.yaml`
exists separates a greenfield `prd` run from everything else.

## "Fast Track" said during intake (Step 2)

Note it and offer it at Step 4. After intake, switching means restarting intake; it never skips the
restatement or the analysis, which tell Fast Track what to leave out.
