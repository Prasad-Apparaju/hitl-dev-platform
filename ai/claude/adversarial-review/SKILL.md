---
description: Run an independent adversarial review of the current work — spawns clean-context reviewers briefed to refute rather than confirm, collects reproduced findings, puts them to you before anything is fixed, and writes the review record the release gate reads. Use at the end of design or code, and before publishing anything to users.
argument-hint: "[what to review — a phase name, paths, or a diff range. Defaults to the whole change.]"
disable-model-invocation: true
---

# Adversarial Review

**Input:** $ARGUMENTS

You are about to have your own work attacked. That is the point. Do not defend it, do not brief the
reviewers toward your conclusions, and do not soften what comes back.

Read `shared/adversarial-review.md` for when to offer this and how to talk about it.

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

Tell the user, briefly: **a round** takes roughly ten minutes, runs in the background, they keep
working. Say that if it finds things there may be more than one round, and that they will see what
came back before anything is changed. Ten minutes is the cost of a round, not of the review — a
change that needs three rounds costs a working day, and quoting the round as the whole makes the
next estimate worthless.

**Say which lenses you would point it at, and why.** They know things about this change you do
not: that the migration is already covered elsewhere, that nobody has looked at cost yet. Pick the
plan from the catalog in `shared/adversarial-review.md` — the base pair for the phase you just
finished, plus whatever the change earns — and name it in one line:

> Design's done. Want an adversarial review before we build? I'd point it at **fitness** (does this
> actually satisfy FR-12) and **consequence** (it rewrites records in place), plus **security**
> since it touches the token store. Three lenses, about half an hour, runs in the background. Swap
> or drop any of them.

This is the same single question, carrying more information. **Do not add a second prompt for plan
approval** — the offer is the plan. They can answer yes, or yes-with-changes, or no.

They pick **where to look, never what will be found.** Take "drop security, it's covered by the
pentest" as a deselection and record it; do not pass their reasoning to the reviewers, because a
brief carrying someone's conclusion gets that conclusion back.

**Write a dropped lens into the record you do write.** Name it in `scope` — *"security lens
offered and declined"* — so if something later goes wrong there, it is visible that a lens for it
was on the table. It is not a workflow skip: `skips[]` records lightened workflow *steps*, keyed by
step, and a lens is not one. Filing it there produces a change file the First Pass check rejects.

Then start. Do not wait for permission a second time if they already accepted the offer at a step
boundary.

---

## Step 3 — Write the briefs

Spawn one reviewer per lens the user agreed to, **never two on the same lens** — they find the
same things twice.

The lens catalog, what each one asks, and when to add it are in `shared/adversarial-review.md`.
The short version: the base pair is `consequence` plus the one for the phase you just finished
(`fitness` after design, `correctness` after code, `upgrade` at release), and conditional lenses
are added for what the change actually touches.

**Use the catalog's ids verbatim in the record.** The gate groups records by lens to catch two
reviewers filed under one; a hand-invented name defeats it silently.

**Do not give the reviewers names.** A named agent becomes an addressable peer rather than a task
that returns: it does the work, and its report does not come back. Attribution comes from the file
it writes, which is a stronger claim than the agent's identity anyway.

**Every reviewer writes its report to a file as its final action.** That is the only channel that
survives whichever way the harness chooses to hand work back, and it removes the temptation to read
a transcript, which is a race you lose:

```
.hitl/reviews/incoming/<lens>-round<N>.md
```

Each brief must contain, in this order:

1. **The state under review** — the sha, and how to see the diff. Not a summary of it: let them read
   the code.
2. **The stance, stated plainly.** *"Assume this is broken and find how. Your job is to refute, not
   to confirm."*
3. **What to attack, in priority order.** Be specific about the mechanisms, not about what you think
   is wrong with them.
   **Include: check each file against itself before checking files against each other.** Two
   contradictory claims twenty lines apart survive every cross-file comparison, because every other
   document agrees with the stale half.
4. **The reproduction rule.** *"Report only findings you reproduced, with the exact command and the
   observed output."* A finding nobody reproduced is a guess, and acting on guesses turns review
   into theatre.
5. **Permission to find nothing.** *"If an area is sound, say so in one line. Do not manufacture
   findings."* A reviewer that must produce findings will.
6. **A verdict instruction** — SHIP or DO NOT SHIP, and if the latter, the smallest change that
   would fix it.
7. **Where the report goes.** *"Write your full report to `.hitl/reviews/incoming/<lens>-round<N>.md`
   as your final action, then reply with that path and nothing else."* Say it last so it is the
   instruction nearest the end of the brief.
8. **Working rules** — scratch directories only, restore anything touched, never modify tracked
   files. Writing its own report file is the one exception, and `.hitl/` is exempt from the gate's
   uncommitted-changes check for exactly this reason.

### What must not be in a brief

- **Your conclusions.** "I think the hash check is sound, please confirm" gets you confirmation. State
  the mechanism, not your confidence in it.
- **Your reasoning for why you built it this way.** They will evaluate the reasoning instead of the
  code.
- **Reassurance of any kind** — "this is well tested", "this was already reviewed". Both are
  invitations to look less hard.

Attribution comes from the report file each reviewer writes, not from the agent.

---

## Step 4 — Verify before you believe

**Read `.hitl/reviews/incoming/`.** Do not wait for reports to arrive on their own and do not read
a reviewer's transcript — the last message is not flushed when the agent goes idle, so a transcript
read returns a half-written report and looks like a reviewer that produced nothing.

**A missing file means unknown, never failed.** If a lens has no report, say the lens did not
complete and offer to re-run it. Never record a reviewer as having failed to synthesize anything:
that is asserting a state you did not verify, the same move as marking a finding fixed without
checking.

Then, for each finding, **do not act on it yet** — reproduce it yourself. Reviewers are wrong
sometimes, confidently. Relaying an unverified finding wastes everyone's time and teaches you to
distrust the next real one.

- **Reproduces** → it is real. Keep it, at the severity you measure, which may not be the severity
  claimed.
- **Does not reproduce** → say so explicitly in the record, with what you ran. Do not silently drop
  it; a finding you could not reproduce is information too.
- **Reproduces, but is by design** → it is `accepted`, not `open`, and needs a name against it.

Then re-read the suggested fix with the same suspicion. A correct diagnosis often comes with a wrong
remedy — check that the proposed fix actually covers the cases you just measured, not only the one
in the report.

---

## Step 5 — Put it to the user before you fix anything

You have verified findings. **You do not yet know which of them this change should carry.** That is
not your call: a finding can be real, reproducible, and still out of scope for the change in front
of you. Scope belongs to the person who owns the change.

Skipping this step is what makes a review feel like it happens in the dark — the user offered ten
minutes of background work and got back a rewritten change hours later, having never seen what was
found.

**Put CRITICAL and HIGH to them individually. Summarise MEDIUM and LOW** — disposition those
yourself and list them in the report. A twenty-five item ballot is not a decision, it is a signature
mill, and a rubber-stamped `accepted_by` is worse than none because it looks like someone decided.

Write each one in plain English:

- **What breaks**, in a sentence, in their terms. Not the record's `claim` field, not YAML, no
  unglossed jargon. If a reviewer wrote "the effect-tier guard misclassifies a tunnelled host",
  you write "anyone with a port-forward open makes the deployed stack look local, so the check
  that is supposed to stop destructive tests against production doesn't fire".
- **What it costs if it ships**, concretely.
- **Your recommendation**, and why. They are checking a judgement, not forming five from scratch.

Then take one of three answers per finding:

| Answer | What it means | What you write |
|---|---|---|
| **fix** | it belongs to this change | `status: fixed`, once the fix exists |
| **accept** | real, and this change is not the place | `status: accepted` + `accepted_by:` their name |
| **defer** | later, on the record | `status: accepted` + `accepted_by:`, and seed a fast-follow |

`accepted_by` is the whole point of this step. The gate requires it and the template calls
accepting risk "someone's decision" — so if nobody is asked, *fix everything* is the only answer
you can reach, and that is what turns a review into a loop.

**Do not block on it.** They accepted a review that runs in the background; do not convert it into
a stop-the-world prompt. Put the list where they will see it, keep working on what is unambiguous
(anything they already said to fix, anything MEDIUM or below), and pick the rest up when they
answer.

**A finding they have not answered is `open`.** Never accept on someone's behalf, and never write a
name into `accepted_by` that did not say the words.

---

## Step 6 — Write the record

Copy `shared/templates/adversarial-review-record.yaml` to
`.hitl/reviews/<change-id>-round<N>.yaml` and fill it in.

```bash
mkdir -p .hitl/reviews
CHANGE=$(grep '^change_id:' .hitl/current-change.yaml | awk '{print $2}' | tr -d '"')
SHA=$(git rev-parse HEAD)
echo ".hitl/reviews/${CHANGE}-round1.yaml   reviewed_sha: ${SHA}"
```

Rules that matter:

- **`reviewed_sha` is the commit you actually reviewed.** Never today's HEAD if the code has moved —
  that is the one lie the gate exists to catch.
- **`reviewer.context: clean`.** If you reviewed your own work in your own context, the honest value
  is `inherited`, and the gate will refuse it. That refusal is correct.
- **`stance: refute`.**
- **Every finding carries its reproduction**, verbatim.
- **`verdict`** is the reviewer's call, not yours. If they said DO NOT SHIP and you fixed everything,
  that is a **new round**, not an edit to theirs.

Round numbers only go up. Earlier rounds stay — the trajectory across rounds is evidence in itself,
and a round-1-clean review reads differently from a round-3-clean one.

---

## Step 7 — Resolve, then re-review if needed

Apply the dispositions from Step 5. Every `CRITICAL` and `HIGH` ends as `fixed` or as `accepted`
with a name against it — an unanswered one stays `open` and the gate blocks, which is correct.

**Fixing changes the code, which makes the record stale.** That is intended: run another round
against the new sha.

**Two rounds, then ask.** Round 3 and beyond are a decision for the person who owns the change, not
an automatic continuation. Say what round 2 found, what is still open, and what you would do next —
then let them choose. Fifteen rounds of hardening is a fine thing to decide to do; it is not a fine
thing to drift into.

**A round against your own repairs is not a round against the design.** The first round reads work
that someone reasoned their way into, and finds the assumption behind it. Later rounds mostly read
fixes written minutes earlier, and find the ones that were correct about the defect they were shown
and wrong about its class. Yield falls, cost does not. Say which kind of round you are proposing.

**Two rounds in a row blocked by the same underlying decision is a scope question, not a fix
question.** When the same acceptance criterion or design choice keeps producing findings, stop and
put *that* to the user. Narrowing the change often dissolves the whole cluster, and it is cheapest
before three rounds of repairs have been built on top of it.

Convergence is a signal worth having, but it is not a plan. A loop with no stop condition but
cleanliness will keep finding the last fix's mistakes.

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
- what came back, by severity — including anything you could not reproduce
- what you fixed, what you accepted and who accepted it
- whether the gate now passes

Lead with what was found. If two rounds found nothing, say that plainly — it is a real outcome, and
inflating it makes the next report harder to trust.

---

## If the user declines

Declining is a normal answer and `adv_design` / `adv_code` are `ceremony` steps, so treat it as an
ordinary skip: record it with the reason they gave, in their words, and move on. Do not ask again
in the same step.

Write the skip the way any other skip is written — see `shared/skip-record.md`. The record is what
lets HITL mention it later if a change touches the same area, and lets the release gate show that no
review happened at any point in this change.
