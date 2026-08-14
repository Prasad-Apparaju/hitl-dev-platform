---
description: Run an independent adversarial review of the current work — spawns clean-context reviewers briefed to refute rather than confirm, collects reproduced findings, and writes the review record the release gate reads. Use at the end of design or code, and before publishing anything to users.
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

**If the working tree is dirty, stop and say so.** A review of uncommitted work cannot be recorded:
the gate binds a record to a commit, and there is no commit yet. Offer to commit first.

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

Tell the user, briefly: roughly ten minutes, runs in the background, they keep working. Then start.
Do not wait for permission a second time if they already accepted the offer at a step boundary.

---

## Step 3 — Write the briefs

Spawn **two** reviewers with **different lenses**. Two reviewers with the same lens find the same
things twice.

The default pair, which catch different classes and rarely overlap:

| Lens | Asks |
|---|---|
| **Correctness** | Does it do what it claims? What input breaks it? Is the fix complete, or does the same bug survive somewhere the diff did not touch? |
| **Consequence** | What does this destroy, expose, or make unrecoverable? What happens to someone who already has the old version? |

Swap a lens when the work calls for it — `security` for auth and secrets, `migration` for anything
that rewrites data in place, `compatibility` when the change lands in repos you do not control.

Each brief must contain, in this order:

1. **The state under review** — the sha, and how to see the diff. Not a summary of it: let them read
   the code.
2. **The stance, stated plainly.** *"Assume this is broken and find how. Your job is to refute, not
   to confirm."*
3. **What to attack, in priority order.** Be specific about the mechanisms, not about what you think
   is wrong with them.
4. **The reproduction rule.** *"Report only findings you reproduced, with the exact command and the
   observed output."* A finding nobody reproduced is a guess, and acting on guesses turns review
   into theatre.
5. **Permission to find nothing.** *"If an area is sound, say so in one line. Do not manufacture
   findings."* A reviewer that must produce findings will.
6. **A verdict instruction** — SHIP or DO NOT SHIP, and if the latter, the smallest change that
   would fix it.
7. **Working rules** — scratch directories only, restore anything touched, never modify tracked
   files.

### What must not be in a brief

- **Your conclusions.** "I think the hash check is sound, please confirm" gets you confirmation. State
  the mechanism, not your confidence in it.
- **Your reasoning for why you built it this way.** They will evaluate the reasoning instead of the
  code.
- **Reassurance of any kind** — "this is well tested", "this was already reviewed". Both are
  invitations to look less hard.

Give each reviewer a distinct name so the reports are attributable.

---

## Step 4 — Verify before you believe

Reports come back. **Do not act on them yet.**

For each finding, reproduce it yourself. Reviewers are wrong sometimes — confidently. Relaying an
unverified finding wastes everyone's time and teaches you to distrust the next real one.

- **Reproduces** → it is real. Keep it, at the severity you measure, which may not be the severity
  claimed.
- **Does not reproduce** → say so explicitly in the record, with what you ran. Do not silently drop
  it; a finding you could not reproduce is information too.
- **Reproduces, but is by design** → it is `accepted`, not `open`, and needs a name against it.

Then re-read the suggested fix with the same suspicion. A correct diagnosis often comes with a wrong
remedy — check that the proposed fix actually covers the cases you just measured, not only the one
in the report.

---

## Step 5 — Write the record

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

## Step 6 — Resolve, then re-review if needed

Fix every `CRITICAL` and `HIGH`, or accept it explicitly with `accepted_by`.

**Fixing changes the code, which makes the record stale.** That is intended. Run another round
against the new sha. Keep going until a round comes back with nothing new — convergence is the
signal, not a single clean pass.

Check where you stand:

```bash
GATE="ci/adversarial/check_review.py"
[[ -f "$GATE" ]] || GATE="$CLAUDE_PLUGIN_ROOT/shared/ci/adversarial/check_review.py"
python3 "$GATE"
```

Exit 0 means the gate is satisfied for the current commit. Exit 2 prints what is missing.

---

## Step 7 — Report

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
