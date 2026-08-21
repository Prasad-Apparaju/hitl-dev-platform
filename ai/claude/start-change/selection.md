# The step selection

- [What it is for](#what-it-is-for)
- [When it runs](#when-it-runs--and-why-not-at-intake)
- [Compute the order](#compute-the-order)
- [Show it](#show-it)
- [Rules](#rules)

Shown at intake once the ask is understood and the impact read is done, before the plan is fixed.
Called from Step 4.

## What it is for

A user asked for one environment variable to be added to a shell script and HITL ran thirty-one
steps over three and a half hours. Every mechanism for right-sizing existed and none was reachable:
the plan was shown as seven phase names and `keep` was the default for all thirty-one. You cannot
pick from a list you were never shown.

## When it runs — and why not at intake

**After impact analysis, not before.** Intake happens before a line is written, so nothing there
knows what the change touches. A first attempt probed `git diff` at intake and always got an empty
answer, because at intake there is nothing to diff.

Impact analysis (`/hitl:dev-apply-change` step 3) is the step that reads the codebase and answers
what this change affects — endpoints, modules, infrastructure, docs, tests, compatibility. That is
the first moment HITL knows the shape of the work, so that is when the plan gets sized.

Until then the plan is **provisional**: the full spine, shown so the shape of the work is visible,
sized by nobody.

## Compute the order

`ci/first-pass/plan_select.py` ranks, renders, and writes the choices. Run it; do not reimplement it.

**`--paths` comes from the impact analysis you just did** — the affected modules, infra and docs —
not from a git diff. There is no diff yet; that is the whole point of running here.

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
SEL="ci/first-pass/plan_select.py"; [[ -f "$SEL" ]] || SEL="$ROOT/shared/ci/first-pass/plan_select.py"
WF="ci/first-pass/workflows.yaml";  [[ -f "$WF"  ]] || WF="$ROOT/shared/workflows.yaml"

python3 "$SEL" render --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
        --profile "$PROFILE" --tags "$TAGS" --paths "$IMPACT_PATHS"
```

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

**Everything below the cut line is skipped, and recorded.** Not by hand, and not into a hand-off
file — the change file already exists by now, so write straight into it:

```bash
python3 "$SEL" apply --workflows "$WF" --workflow "$WF_ID" --tier "$TIER" \
        --profile "$PROFILE" --paths "$IMPACT_PATHS" \
        --keep "issue,review1,verify_pr" --actor "<the person, not you>"
```

That marks each unkept step `skipped` and appends an attributed entry to `skips[]`, which is what
the fail-closed validator reads.

**Not a choices file.** `.hitl/first-pass-choices.json` is consumed by intake's Step 6, which has
already run by the time the selection happens — writing one here records for a consumer that never
comes. An earlier version of this feature did exactly that.

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
