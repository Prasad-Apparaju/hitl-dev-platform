# Right-sizing a change: impact-led plan sizing

**Status:** draft, for review · **Issue:** #97 · **Supersedes:** three implementation attempts in 2.9.0

## Why this document exists

Three implementations of this feature were built and all three failed adversarial review — nine
lenses, three rounds, every one DO NOT SHIP. Not one was reviewed as a *design* first, and every
failure was a **contract between components** rather than a defect inside one:

| attempt | what broke |
|---|---|
| 1 | the ranker had no caller; the record was never produced |
| 2 | the probe read `git diff` at intake, where nothing has been written |
| 3 | the record was written correctly, to a validator that had already run |

Each fix moved the break to the next link. Code review cannot catch that class — each component was
correct on its own. This document exists so the fourth attempt starts from an agreed contract.

## The problem

A user asked for `FIRECRAWL_API_KEY` to be added to `demo.sh`. It ran 31 steps over 3h31m.

Two causes, and the second is the real one:

1. Nothing sizes a plan. Profiles and tags never reach the runtime catalog, so every change in every
   project gets the same 31 steps.
2. **HITL decides how much process a change needs before it has looked at the change.** Intake picks
   a tier from your description and fixes the plan. The codebase is first read two skills later.

## The constraint that killed three attempts

Three things must hold at once, and today they cannot:

- sizing must happen **after** something has read the code — that is the only moment the shape of the
  work is known
- the ledger validator (`check_skips.py`) runs at intake Step 6b
- the validator must read what sizing produced

The validator runs near the end of intake. Impact analysis lives in `apply-change`, a **separate
command run later**. So the check completes before the record exists, and no amount of fixing the
writing end changes that.

## The decision

**Move impact analysis into intake, immediately after the requirements conversation.** Everything
then happens in one command, in an order where each step has what it needs.

```
/hitl:dev-start-change
  1   don't clobber an active change
  2   choose the issue
  3   determine the workflow            ← classification, from the issue
  3a  IMPACT ANALYSIS                   ← MOVED HERE. produces the facts
  3b  confirm the tier                  ← now from evidence, not description
  4   size the plan                     ← the selection, using those facts
  5   create the branch
  6   write the change file             ← including the skips
  6b  certify the ledger                ← validator, now downstream of the record
  7   commit
  8   route onward
```

Nothing else moves. The validator stays exactly where it is and becomes correct, because the record
now exists before it runs. No cross-command state, no hand-off file, no second writer.

## Impact analysis is a graph query, not a codebase scan

The current instruction is *"search the codebase to verify each item. Don't guess — read the files."*
It queries neither the manifest nor Graphify, and re-derives every time what the project already
declares. That is why moving it earlier looked expensive. It is not.

HITL builds a top-down chain on purpose — manifest → HLD → LLD → ADRs — and Graphify indexes code
**and** docs, rebuilds on write, and is committed. Each domain in the manifest already declares:

| field | answers |
|---|---|
| `files` | which domain owns the touched paths |
| `lld` | the design doc for this domain |
| `facade_apis`, `boundary_entities` | what callers see |
| `depends_on` (reversed) | who breaks if this changes |
| `events_emitted` / `events_consumed` | what fires and what listens |
| `tests` | what covers it |
| `owning_fr` | which requirement is in play, and so which acceptance criteria |
| `last_changed` | whether the declaration is plausibly current |

So impact analysis becomes: **resolve the domain, walk the declared model down and sideways, then
read source only where the change goes beyond what is declared.**

That last clause is where the quality is. A change the declared model cannot account for is itself a
finding — either the manifest is stale (`ci/manifest-drift` exists for this) or the change crosses a
boundary nobody wrote down. Both are worth saying out loud, and neither is visible to a grep.

## What impact analysis must produce

Sizing consumes a defined artifact, not prose. This is the contract:

```yaml
impact:
  domains:      [billing]              # from `files`
  dependents:   [checkout, reporting]  # depends_on, reversed
  facades:      [POST /refund]         # facade_apis touched
  events:       [refund.issued]
  docs:         [docs/.../billing.md]  # the domain's lld/HLD
  tests:        [tests/billing/]
  owning_fr:    FR-12
  paths:        [src/billing/refund.py]
  undeclared:   []                     # touched, and no domain claims it
  confidence:   declared | partial | unknown
```

`undeclared` and `confidence` are load-bearing. A change with `confidence: unknown` must not be
sized down — see the floor below.

## What sizing consumes

`rank.py` already ranks by `forgo_cost` modulated by engagement. Today `engages` matches path globs
invented by hand. It should match **structure**:

- `engages.domains` — this step matters when the change touches these domains
- `engages.dependents` — matters when anything depends on the touched domain
- `engages.facades` — matters when a public interface moves
- the incident-registry raise keys off `domains`, which it can now actually resolve

That replaces guessed directory names with the model the project maintains.

## The floor: when sizing must not happen

Sizing is a privilege earned by information. It is **off** when:

- `confidence: unknown`, or `undeclared` is non-empty — the model cannot explain the change
- the project has no manifest
- `step_costs` is absent or covers less than the whole plan
- the workflow is not `development`

In every one of those cases the full plan is shown and nothing is collapsed — 2.8.0 behaviour. A
plan is lightened when there is a basis to lighten it, never as a side effect of missing data.

## Consequences for `apply-change`

- Its **Step 3 (Impact Analysis)** is removed; the analysis now arrives in the change file.
- Its **Step 1** currently re-derives the tier from the description. That becomes a check against the
  recorded evidence, not a fresh guess.
- It becomes what it mostly already is: the implementation planner.

Both skills need reconciling in one change. That is the part most likely to break and the part that
most needs review before code.

## Upgrade

- A project that upgrades the plugin but not its `ci/first-pass/workflows.yaml` has no `step_costs`,
  so sizing is off and it sees exactly 2.8.0 behaviour.
- An existing `.hitl/current-change.yaml` is never re-read or re-seeded.
- `dev-update` refreshes the catalog copy; until it runs, nothing changes for that project.

## Out of scope

- Wiring profiles and tags into the runtime. They stay advisory.
- Any change to what the floor protects, or to `no_omit`.
- The compound-agentic manifest fields; this reads `domains` only.

## Open questions for review

1. **Does impact analysis at intake change what intake is for?** It becomes a heavier front door.
   Is that right, or should sizing be a distinct command run between the two?
2. **What does a stale manifest do to sizing?** `last_changed` is a hint, not proof. Is
   `confidence: partial` enough to size on, or should any staleness signal disable it?
3. **Who is the actor on a skip recorded at intake** — the person driving intake, always? There is no
   second human present at that moment.
4. **Should the workflow classification (Step 3) also be revisited** once impact analysis has run? It
   is decided from the issue text and never rechecked, the same weakness the tier had.
