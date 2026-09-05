---
description: Run an independent verification review of the current work — spawns a clean-context reviewer with a checklist, has it run the artifact rather than read about it, collects a one-page pass/fail report, puts what failed to you before anything is fixed, and writes the review record the release gate reads. Use at the end of design or code, and before publishing anything to users.
argument-hint: "[what to review — a phase name, paths, or a diff range. Defaults to the whole change.]"
disable-model-invocation: true
---

# Verification Review

**Input:** $ARGUMENTS

Someone with no stake in this work is about to check whether it does what it claims. Do not brief
them toward your conclusions, do not pre-answer the checks, and do not soften what comes back.

Read `shared/verification-review.md` for when to offer this and how to talk about it.

---

## Step 1 — Fix what is being reviewed

A review is only worth anything against a specific state of the code.

```bash
git rev-parse HEAD
git status --porcelain | head -20
git diff --stat HEAD~1 2>/dev/null | tail -3
```

**If source files are uncommitted, stop and say so.** A review of uncommitted work cannot be
recorded: the gate binds a record to a commit, and there is no commit yet. Offer to commit first.

Changes under `.hitl/` do not count — advancing the workflow edits the change file, so the tree is
almost always "dirty" in that sense, and the gate exempts it for the same reason. Untracked build
output (`dist/`, `build/`) does not count either.

Establish the scope from `$ARGUMENTS`, or infer it:

| Argument | Scope |
|---|---|
| empty | the whole change — `git diff <base>..HEAD`, where base is the branch point |
| a phase name (`design`, `code`) | the artifacts that phase produced |
| paths | those paths |
| a range (`v1.2.0..HEAD`) | that range |

Record the sha. Everything below hangs off it.

---

## Step 2 — Say what it costs, then start it in the background

Tell the user, briefly: **a round takes roughly ten minutes**, runs in the background, they keep
working. Say that if something fails there may be a second round, and that they will see what came
back before anything is changed. Ten minutes is the cost of a round, not of the review — a change
that needs three rounds costs a working day, and quoting the round as the whole makes the next
estimate worthless.

**Say what you would have it check, and why.** The checklist comes from three places: the
change's own acceptance criteria and definition of done (in `.hitl/impact/<change_id>.yaml` when
the change was sized, otherwise the issue), the claims the change makes about itself (a commit
message, a changelog line, a docstring), and the lens questions from the catalog in
`shared/verification-review.md` that this change earns. Name the lenses in one line:

> Design's done. Want a verification review before we build? I'd have it check **fitness** (does
> this satisfy FR-12, case by case) and **consequence** (it rewrites records in place), plus
> **security** since it touches the token store. Three lenses, in parallel, still about ten
> minutes, runs in the background. Swap or drop any of them.

This is the same single question, carrying more information. **Do not add a second prompt for plan
approval** — the offer is the plan. They can answer yes, or yes-with-changes, or no.

They pick **where to look, never what will be found.** Take "drop security, it's covered by the
pentest" as a deselection and record it; do not pass their reasoning to the reviewer, because a
brief carrying someone's conclusion gets that conclusion back.

**Write a dropped lens into the record you do write.** Name it in `scope` — *"security lens
offered and declined"* — so if something later goes wrong there, it is visible that a lens for it
was on the table. It is not a workflow skip: `skips[]` records lightened workflow *steps*, keyed by
step, and a lens is not one.

Then start. Do not wait for permission a second time if they already accepted the offer at a step
boundary.

---

## Step 3 — Write the briefs

Spawn one reviewer per lens the user agreed to, **never two on the same lens** — they check the
same things twice. **Do not give the reviewers names.** A named agent becomes an addressable peer
rather than a task that returns: it does the work, and its report does not come back. Attribution
comes from the file it writes.

**Use the catalog's ids verbatim in the record.** The gate groups records by lens to catch two
reviewers filed under one; a hand-invented name defeats it silently.

**Every reviewer writes its report to a file as its final action:**

```
.hitl/reviews/incoming/<lens>-round<N>.md
```

Each brief must contain, in this order:

1. **The state under review** — the sha, and how to see the diff. Not a summary of it: let them read
   the code.
2. **The checklist.** Numbered. Each item is one claim the work makes and the way to check it: what
   to run, and what output would mean pass. Write the checks, not the answers. Where a check is
   "read and compare" rather than "run", say so; where it can be run, it must be run.
   **Include: check each file against itself before checking files against each other.** Two
   contradictory claims twenty lines apart survive every cross-file comparison, because every other
   document agrees with the stale half.
3. **The evidence rule.** *"Report only what you verified, with the exact command and the observed
   output. A check you could not run is `unknown`, not a pass and not a fail."*
4. **The shape of the report, and its size.** One page. A table of the checks with the command and
   the result for each. Then at most **five** points, ranked, each in one of three classes:
   **stops it working**, **worth deciding**, or **minor**. No severity labels beyond those three.
   Point at the gap; do not design the fix. *"If it is right, say so and stop. That is a real
   answer."*
5. **The budget.** About fifteen tool calls, or the checklist, whichever ends first. A reviewer that
   is still exploring after the checklist is done is producing volume, not verification.
6. **A verdict instruction** — VERIFIED or NOT VERIFIED, and if the latter, the one check that
   decides it.
7. **Working rules** — scratch directories only, restore anything touched, never modify tracked
   files. Writing its own report file is the one exception, and `.hitl/` is exempt from the gate's
   uncommitted-changes check for exactly this reason.
8. **Where the report goes.** *"Write your full report to `.hitl/reviews/incoming/<lens>-round<N>.md`
   as your final action, then reply with that path and nothing else."* Say it last so it is the
   instruction nearest the end of the brief.

### What must not be in a brief

- **Your conclusions.** "I think the hash check is sound, please confirm" gets you confirmation. State
  the check, not your confidence in it.
- **Your reasoning for why you built it this way.** They will evaluate the reasoning instead of the
  code.
- **Reassurance of any kind** — "this is well tested", "this was already reviewed". Both are
  invitations to look less hard.
- **An instruction to find something.** A reviewer that must produce findings will. The checklist
  is the job; an empty findings list against a full table of passes is the job done.

---

## Step 4 — Verify before you believe

**Read `.hitl/reviews/incoming/`.** Do not wait for reports to arrive on their own and do not read
a reviewer's transcript — the last message is not flushed when the agent goes idle, so a transcript
read returns a half-written report and looks like a reviewer that produced nothing.

**A missing file means unknown, never failed.** If a lens has no report, say the lens did not
complete and offer to re-run it. Never record a reviewer as having failed to synthesize anything:
that is asserting a state you did not verify.

Then, for each failed check and each point, **do not act on it yet** — reproduce it yourself.
Reviewers are wrong sometimes, confidently. Relaying an unverified finding wastes everyone's time
and teaches you to distrust the next real one.

- **Reproduces** → it is real. Keep it, in the class you measure, which may not be the class claimed.
- **Does not reproduce** → say so explicitly in the record, with what you ran. Do not silently drop
  it; a finding you could not reproduce is information too.
- **Reproduces, but is by design** → it is `accepted`, not `open`, and needs a name against it.
- **A check marked `unknown`** → either run it yourself now and record the result, or carry it into
  the record as unknown. An unknown is not a pass.

---

## Step 5 — Put it to the user before you fix anything

You have verified findings. **You do not yet know which of them this change should carry.** A
finding can be real, reproducible, and still out of scope for the change in front of you. Scope
belongs to the person who owns the change.

**Put every "stops it working" and every "worth deciding" to them individually. Summarise the
minor ones** — disposition those yourself and list them in the report. Five points is the cap for
a reason: a twenty-five item ballot is not a decision, it is a signature mill.

Write each one in plain English:

- **What fails**, in a sentence, in their terms. Not the record's `claim` field, not YAML, no
  unglossed jargon.
- **What it costs if it ships**, concretely.
- **Your recommendation**, and why. They are checking a judgement, not forming five from scratch.

Then take one of three answers per finding:

| Answer | What it means | What you write |
|---|---|---|
| **fix** | it belongs to this change | `status: fixed`, once the fix exists |
| **accept** | real, and this change is not the place | `status: accepted` + `accepted_by:` their name |
| **defer** | later, on the record | `status: accepted` + `accepted_by:`, and seed a fast-follow |

`accepted_by` is the whole point of this step. The gate requires it, and a "worth deciding" point
is exactly a decision — so if nobody is asked, *fix everything* is the only answer you can reach.

**Do not block on it.** They accepted a review that runs in the background; do not convert it into
a stop-the-world prompt. Put the list where they will see it, keep working on what is unambiguous
(anything they already said to fix, anything minor), and pick the rest up when they answer.

**A finding they have not answered is `open`.** Never accept on someone's behalf, and never write a
name into `accepted_by` that did not say the words.

---

## Step 6 — Write the record

Copy `shared/templates/verification-review-record.yaml` to
`.hitl/reviews/<change-id>-round<N>-<lens>.yaml` and fill it in — one record per reviewer, so two
lenses in a round do not overwrite each other.

```bash
mkdir -p .hitl/reviews
CHANGE=$(grep '^change_id:' .hitl/current-change.yaml | awk '{print $2}' | tr -d '"')
SHA=$(git rev-parse HEAD)
echo ".hitl/reviews/${CHANGE}-round1-<lens>.yaml   reviewed_sha: ${SHA}"
```

Rules that matter:

- **`reviewed_sha` is the commit you actually reviewed.** Never today's HEAD if the code has moved —
  that is the one lie the gate exists to catch.
- **`reviewer.context: clean`.** If you reviewed your own work in your own context, the honest value
  is `inherited`, and the gate will refuse it. That refusal is correct.
- **`checks` is the table from the report**, one entry per check: what was checked, the command,
  the result (`pass`, `fail`, `unknown`), and the output that decided it. A record with no checks
  is a review that did not run anything.
- **Every finding carries its evidence**, verbatim, and its class. A finding that answers for a
  failed check names it in `check:` (the check's own text); a failed check with no resolved finding
  naming it contradicts a verified verdict, and the gate says so.
- **`verdict`** is the reviewer's call, not yours. If they said NOT VERIFIED and you fixed
  everything, that is a **new round**, not an edit to theirs.

Round numbers only go up. Earlier rounds stay — the trajectory across rounds is evidence in itself.

---

## Step 7 — Resolve, then re-review if needed

Apply the dispositions from Step 5. Every "stops it working" ends as `fixed` or as `accepted`
with a name against it; every "worth deciding" ends decided, the same way. An unanswered one stays
`open` and the gate blocks, which is correct. Minor points are yours to fix or leave.

**Fixing changes the code, which makes the record stale.** That is intended: run another round
against the new sha. A second round re-runs the checks that failed and the checks the fix could
have disturbed — not the whole list again, unless the fix was wide.

**Two rounds, then ask.** Round 3 and beyond are a decision for the person who owns the change, not
an automatic continuation. Say what round 2 found, what is still open, and what you would do next —
then let them choose.

**Two rounds in a row failed by the same underlying decision is a scope question, not a fix
question.** When the same acceptance criterion or design choice keeps failing, stop and put *that*
to the user. Narrowing the change often dissolves the whole cluster.

Check where you stand:

```bash
# CLAUDE_PLUGIN_ROOT is unset in the Bash tool; a bare "$CLAUDE_PLUGIN_ROOT/..." becomes "/...".
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
GATE="ci/adversarial/check_review.py"
[[ -f "$GATE" ]] || GATE="$ROOT/shared/ci/adversarial/check_review.py"
python3 "$GATE"
```

Exit 0 means the gate is satisfied for the current commit. Exit 2 prints what is missing.

---

## Step 8 — Report

Tell the user, in a few lines:

- what was reviewed, and at which commit
- the table: how many checks passed, failed, and were unknown
- what came back, by class — including anything you could not reproduce
- what you fixed, what you accepted and who accepted it
- whether the gate now passes

Lead with what failed. If everything passed, say that plainly — it is a real outcome, and
inflating it makes the next report harder to trust.

---

## If the user declines

Declining is a normal answer and `adv_design` / `adv_code` are `ceremony` steps, so treat it as an
ordinary skip: record it with the reason they gave, in their words, and move on. Do not ask again
in the same step.

Write the skip the way any other skip is written — see `shared/skip-record.md`. The record is what
lets HITL mention it later if a change touches the same area, and lets the release gate show that no
review happened at any point in this change.

## Closing this step

When this step is done, close it the way `ai/shared/next-step.md` describes: what finished, what is
next in words that say what it achieves, and how to start it. Read the next step and its `command`
from `.hitl/current-change.yaml`; `manual` and `guided` are not commands and must not be rendered as
one. Do not list the remaining steps, restate what just happened, or ask permission to continue.
