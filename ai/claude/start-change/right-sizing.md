# Right-sizing the tier from the shape of the change

Nothing here decides a tier. It decides which one you **propose first**, so that the cheap answer is
the one on offer rather than the one someone has to argue for.

## Why this exists

A user asked for `FIRECRAWL_API_KEY` to be added to `demo.sh`. It ran three hours thirty-one
minutes across eleven recorded steps, including an adversarial design review, a full TDD RED/GREEN
cycle, a refactor step, an adversarial code review, and a fifty-seven minute review round. They
reported the tool as broken. That is a fair description of how it felt, and nothing malfunctioned:
intake tiered up, and at tier 2 every ceremony step runs.

## The probe

```bash
# What does this change actually touch? Source under a manifest domain, or everything else?
BASE="${BASE:-main}"
git diff --name-only "$(git merge-base HEAD "$BASE")"..HEAD 2>/dev/null | sed -n '1,200p'
```

**Non-source** means scripts, config, CI workflows, docs, examples, fixtures, lockfiles — anything
outside the `paths` of a domain in the system manifest.

## What to propose

| The diff touches | The request is | Propose |
|---|---|---|
| non-source only | a value: env var, flag, version pin, doc line | tier 0 or 1, reason pre-filled |
| non-source only | behaviour: new logic in a script, a changed deploy step | tier 2, say why |
| source under a manifest domain | anything | the tier you would have anyway — this probe does not apply |

Say it in one line, and be plain that tiering up is one word away:

> This touches `demo.sh` only, so I'd run it as tier 1 — the ceremony steps come off and it's about
> twenty minutes. Say the word if you want it heavier.

A proposal someone can reject in four characters is not pressure. Making them argue a tier down is.

## What this never does

- **It does not lower a floor step.** Criticality is resolved from the catalog against the tier, and
  the floor at whatever tier is chosen still holds.
- **It does not apply to source.** However small a diff under a manifest domain looks, this probe
  says nothing about it.
- **It does not survive a real risk signal.** Secrets moving between files, auth, permissions,
  anything a `security` profile activates on: propose the tier you would have proposed anyway.

**Naming a key is not moving one.** Adding `FIRECRAWL_API_KEY=` to a script that already reads
environment variables is a chore. Changing where a secret is stored, or who can read it, is not.
That distinction is the whole judgement here, and when you cannot tell which one you are looking at,
that ambiguity is what "default up" was written for. Use it.

## After the tier is set

At tier 0 or 1, **offer First Pass without being asked** (Step 4b) and present the ceremony steps
pre-selected as declined with the reason filled in. One confirmation clears all eleven. Nothing is
written until the human confirms, and the actor on every resulting record is that person.
