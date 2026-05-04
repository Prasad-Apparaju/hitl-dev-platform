# Developer Playbook

**Context:** You're a developer on [Project Name]. The architecture is fully designed — HLDs, LLDs, ADRs, and a system manifest are all in the repo. Your job is to implement assigned work by following the LLDs and the dev workflow. Claude Code does most of the heavy lifting; you review, steer, and make judgment calls.

---

## Step 1 — Set up your environment

```bash
git clone <repo-url>
cd <project>
claude   # CLAUDE.md auto-loads on startup — no config needed
```

Verify Claude loaded the project context:

```
What project am I working on, what conventions must I follow,
and what domains does the system manifest define?
```

---

## Step 2 — Understand the domain you're working in

Before writing any code, load the context for your domain:

```
I'm about to work on the [domain name] domain. Read the system
manifest entry for this domain and the relevant LLD at
docs/02-design/technical/lld/.

Tell me:
1. What files this domain owns
2. What conventions specifically apply here
3. What the facade API looks like (what callers expect)
4. What tests currently cover this domain
```

---

## Step 3 — Find your next task

```
Read docs/01-product/prd.md and the current GitHub issues.
What's the next piece of work ready to be picked up?
What does "done" look like for it, and what LLD should
I implement from?
```

---

## Step 4 — Start a change (every time)

For every change — feature, fix, or refactor — start with:

```
/dev-practices
```

Tell Claude what you're doing and it will confirm the tier and walk you through each step:

```
I'm implementing [feature/fix]. What tier is this and what
steps do I need to follow?
```

The workflow is: issue → impact analysis → LLD review → TDD (tests first) → code → two-round review → impact brief → PR.

---

## Step 5 — Write tests before code (TDD)

```
/tdd

I'm implementing [component] from docs/02-design/technical/lld/[path].
Generate the maximum set of tests from the LLD spec — happy paths,
error paths, edge cases, contract compliance, and any regression
tests linked to past incidents. No implementation code yet.
```

Review the generated tests carefully. Add cases Claude missed:

```
I want to add these test cases you missed: [describe them].
Update the test file and flag any gaps they reveal in the LLD.
```

---

## Step 6 — Generate the implementation

Once tests are written, reviewed, and all failing (RED):

```
All tests are written and confirmed failing. Generate the
implementation code from docs/02-design/technical/lld/[path]
that makes all tests pass. Follow every convention in CLAUDE.md
and docs/system-manifest.yaml. Simplest correct code only.
```

---

## Step 7 — Review your own code before the PR

```
/check-conventions

Review the code I just wrote against the LLD and the system
manifest conventions. Flag any violations, missing inline comments,
missing idempotency keys, unguarded external calls, or places where
the implementation diverged from the spec.
```

Fix what's flagged, then run a second pass:

```
Second review pass: focus on edge cases, error paths,
and whether retry/idempotency/tenant-isolation conventions
are correctly applied everywhere they're needed.
```

---

## Step 8 — Write the impact brief before the PR

```
/impact-brief

Generate the downstream impact brief for this change. Include:
1. What flows and components changed
2. Risk assessment
3. Manual verification scenarios for QA
4. What the PM needs to know (mental model update)
5. Rollout strategy and go/no-go criteria
```

---

## Step 9 — Ask about anything you're unsure of

```
Why does [thing] work this way? Where is that decision documented?
```

```
I'm not sure whether to [option A] or [option B] here. What do
the ADRs and LLD say, and what would be consistent with how
the rest of the system handles this?
```

```
This test is failing in an unexpected way. Read the LLD, the
test, and the implementation and help me diagnose whether this
is a test bug, an implementation bug, or an LLD gap.
```

---

## Ownership Rules

**You own your slice end-to-end.** Issue, design check, tests, code, review, impact brief, PR. No handing off half-finished work.

**Never silently normalize drift.** If your implementation diverges from the LLD, explicitly decide: does the implementation reveal a better design (update the LLD), or did the code drift (fix the code)? Document the decision.

**If you're stuck, the docs come first.** Before asking a colleague, ask Claude Code — the answer is usually in the LLD, ADR, or system manifest. If it's not, that gap should be documented.

---

## Key Files

| File | What it is |
|------|-----------|
| `CLAUDE.md` | Conventions and workflow rules — auto-loaded every session |
| `docs/system-manifest.yaml` | Domain map — read your domain's entry before every change |
| `docs/02-design/technical/lld/` | Component specs — what Claude generates code from |
| `docs/02-design/technical/adrs/design-decisions.md` | Why every major decision was made |
| `docs/01-product/prd.md` | Product requirements |
| `docs/04-operations/incident-registry.yaml` | Past failures — shapes your test plan |

---

## How-To Guides

| I want to... | Guide |
|---|---|
| Understand the full workflow | `claude/dev-practices/SKILL.md` |
| Run TDD on a component | `claude/tdd/SKILL.md` |
| Analyse impact of a change | `claude/apply-change/SKILL.md` |
| Write a downstream impact brief | `claude/impact-brief/SKILL.md` |
| Check convention violations | `claude/check-conventions/SKILL.md` |
