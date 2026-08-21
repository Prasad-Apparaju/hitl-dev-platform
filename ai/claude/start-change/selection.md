# The step selection

- [What it is for](#what-it-is-for)
- [Compute the order](#compute-the-order)
- [Show it](#show-it)
- [Rules](#rules)

Shown at intake once the ask is understood and the impact read is done, before the plan is fixed.
Called from Step 4.

## What it is for

A user asked for one environment variable to be added to a shell script and HITL ran thirty-one
steps over three and a half hours. Every mechanism for right-sizing existed and none of them was
reachable: the plan was shown as seven phase names, the disposition menu had no defined form, and
`keep` was the default for all thirty-one. You cannot pick from a list you were never shown.

So: show the steps, ranked, with what each one protects, and let the person choose.

## Compute the order

`ci/first-pass/plan_select.py` does all of it — ranking, rendering, and writing the choices. Run it;
do not reimplement it in prose.

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
SEL="ci/first-pass/plan_select.py"; [[ -f "$SEL" ]] || SEL="$ROOT/shared/ci/first-pass/plan_select.py"
WF="ci/first-pass/workflows.yaml";  [[ -f "$WF"  ]] || WF="$ROOT/shared/workflows.yaml"

# 1. the shape probe — this is what sets TRIVIAL_SHAPE for Step 6's generator
export TRIVIAL_SHAPE="$(python3 "$SEL" probe --base "${BASE:-main}")"

# 2. the selection a person reads
python3 "$SEL" render --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
        --profile "$PROFILE" --tags "$TAGS" --base "${BASE:-main}"
```

`TRIVIAL_SHAPE` must be exported here. Step 6's generator reads it and refuses a tier 2+ on a
change that touches no source under a manifest domain without a name and a reason. Set nowhere, that
refusal is dead code — which is exactly what shipped in the first draft of this feature.

## Show it

**Locked, not offered.** Floor steps at this tier and `no_omit` (TDD red/green — thinnable to a
starter, never dropped) lead the list as already-on, each with its one-line reason. They are not
choices, so they do not take up choosing.

**Then six to eight, ranked**, each with the `protects` sentence — what the reader gives up, in
their terms. Not the step name restated.

**Then the tail, collapsed.** One line naming the rest and their count. `"show the rest"` expands it.

```
Running (locked)     RED · GREEN — thinned to a starter test
                     no deploy steps in scope

Selected — untick any                              what you'd lose
 ✓ Review              a second pair of eyes on the diff
 ✓ Verify PR           CI is green on the exact commit being merged
 ✓ Impact              the callers and jobs this touches, found before you touch them
 ☐ Docs                the runbook keeps describing a system that no longer exists
 ☐ Test plan           QA won't know what "done" meant
 ☐ Arch review         a boundary crossing goes unnoticed

 + 14 more, skipped: conventions, reconcile, rerun, baseline …      "show the rest"
```

**Collect the decision with `AskUserQuestion`,** multi-select, so it is a real checkbox rather than
a sentence someone has to compose. It caps at four options per question and four questions, so put
the top items there and keep fine control conversational — *"also drop docs"* is a normal reply.

## Rules

**Everything below the cut line is skipped, and recorded.** Not by hand — pass what the person kept
back to the same tool, which writes an entry for every step not kept, offered or collapsed alike:

```bash
python3 "$SEL" choices --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
        --profile "$PROFILE" --base "${BASE:-main}" \
        --keep "issue,review1,verify_pr" --actor "<the person, not you>" \
        > .hitl/first-pass-choices.json
```

That file is what Step 6 turns into the ledger. **If the tail does not reach it, the tail is skipped
and NOT recorded**, and the fail-closed validator certifies the change clean — the first draft of
this feature did precisely that, and a review caught it. The command above is the compensation for
inverting the default; prose describing it is not.

This inverts CR-1, which made `keep` the default so an agent could not quietly lighten a plan. The
human still confirms — they are confirming *these eight* rather than *cut these twenty-five*. A
default nobody was shown was not protecting anyone. Silence is still never allowed to do the
skipping: every step not kept lands in the file above, with the reason it was ranked where it was.

**The floor can be unticked.** It is not locked out of the view, it is locked out of *casual*
choice: name the specific loss, take a name against it, and a linked waiver where the step maps to a
hard gate. That is the skip ledger's existing machinery, reachable from here for the first time.

> Unticking **pentest**. This change touches auth, so nothing else in the plan looks for a
> privilege bug. Who is accepting that, and against which waiver?

**Push back on an incoherent selection, do not block it.** `rank.incoherent(kept, step_requires)`
returns every kept step whose prerequisite was dropped, with the sentence saying what breaks.
`green` without `red` is a fix with no failing test behind it; `promote` without `deploy`;
`reconcile` resolving findings from a review nobody did.

Name it, take the answer, proceed — consistent with everything else here, where even the floor
yields to a signature. Dropping *both* a step and its prerequisite is coherent and says nothing:
skipping the whole TDD pair is an ordinary recorded skip.

> Keeping **GREEN** but dropping **RED**. That is a fix with no failing test behind it — GREEN is
> defined against RED. Keep RED as a starter, or drop both?

**Never quote a duration.** Quote step counts. Elapsed time is dominated by when someone reads their
notifications, which HITL does not control and cannot predict.
