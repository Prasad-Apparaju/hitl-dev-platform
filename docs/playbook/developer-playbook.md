# Developer Playbook

**Context:** You're a developer on [Project Name]. The architecture is fully designed — HLDs, LLDs, ADRs, and a system manifest are all in the repo. Your job is to implement assigned work by following the LLDs and the dev workflow. Claude Code does most of the heavy lifting; you review, steer, and make judgment calls.

---

## What you receive before you start

The architect hands you a **decision packet** — a YAML file at `docs/decisions/issue-<N>.yaml` (or `issue-<N>-slice-<M>.yaml` for multi-slice work). It contains everything you need to begin:

| Field | What it tells you |
|-------|------------------|
| `issue` | The GitHub issue number for your slice |
| `domains` | The one manifest domain you're working in |
| `source_docs.lld` | The LLD path — your implementation spec |
| `source_docs.hld` | The HLD — context for how your domain fits the system |
| `tests.plan` | The test scenarios to cover |
| `rollout.risk` | How carefully to stage the deployment |

Before writing any code, read your packet:

```bash
cat docs/decisions/issue-<N>.yaml
```

Then open the LLD it references — that document drives everything that follows: tests, implementation, and code review.

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
I'm about to work on the payments domain. Read the system manifest
entry for this domain and the LLD at
docs/02-design/technical/lld/payments/refund-flow.md.

Tell me:
1. What files this domain owns
2. What conventions specifically apply here
3. What the facade API looks like (what callers expect)
4. What tests currently cover this domain
```

---

## Step 3 — Start from your assigned GitHub issue

When the architect finishes the design and the TA approves the decision packet, GitHub posts a **"Ready for Development"** comment on the issue assigned to you. That comment contains your packet path, your domain, and your starting command.

Open Claude Code and point it at the issue:

```
/hitl:tdd

I have been assigned GitHub issue #[N]. Read the decision packet at
docs/decisions/issue-[N].yaml and tell me what I am building,
what domain I am in, and what the test plan requires me to cover.
```

Claude reads the packet, loads the LLD, and confirms what you're building before generating any tests. If it can't find the packet, check that the architect has completed `/hitl:architect-design-feature` and the TA has run `/hitl:ta-approve`.

---

## Step 4 — Start a change (every time)

For every change — feature, fix, refactor, or docs-only — start with:

```
/hitl:dev-practices

I'm implementing the refund flow for issue #42. What tier is this
and what steps do I need to follow?
```

The workflow is: issue → impact analysis → LLD review → TDD (tests first) → code → two-round review → impact brief → PR.

---

## Step 5 — Write tests and build the implementation

`/hitl:tdd` is the command for writing code. It runs the full cycle in one session: generates tests from the LLD, pauses for your review, then generates the implementation that makes all tests pass.

```
/hitl:tdd

I have been assigned GitHub issue #[N]. Read the decision packet at
docs/decisions/issue-[N].yaml and tell me what I am building,
what domain I am in, and what the test plan requires me to cover.
```

The skill walks you through seven phases automatically:

1. **RED** — generates tests from the LLD (happy paths, error paths, edge cases, regression tests from past incidents)
2. **Review** — pauses and shows you the tests; you add anything Claude missed
3. **Improve design** — flags any test that reveals a gap in the LLD and proposes an LLD update
4. **Verify RED** — confirms all new tests fail before any implementation exists
5. **GREEN** — generates the implementation code that makes all tests pass
6. **Verify GREEN** — confirms all tests pass with no regressions
7. **Refactor** — simplifies the passing code without breaking tests

You do not need to type separate prompts for tests and code — the skill handles both. Your only judgment call is the review step: add test cases Claude missed, remove tests that check implementation details rather than behaviour.

---

## Step 7 — Review your own code before the PR

```
/hitl:check-conventions

Review the code I just wrote in src/payments/ against the LLD at
docs/02-design/technical/lld/payments/refund-flow.md and the system
manifest conventions. Flag any violations, missing idempotency keys,
unguarded external calls, or places where the implementation diverged
from the spec.
```

Fix what's flagged, then run a second pass:

```
/hitl:dev-check-implementation

Second review pass on the payments refund flow: focus on edge cases,
error paths, and whether retry and idempotency conventions are correctly
applied everywhere they're needed.
```

---

## Step 8 — Write the impact brief before the PR

```
/hitl:impact-brief

Generate the downstream impact brief for issue #42 — payments refund flow.
Include what flows and components changed, risk assessment, manual
verification scenarios for QA, what the PM needs to know about the
mental model update, and the rollout strategy with go/no-go criteria.
```

---

## Step 9 — Ask about anything you're unsure of

```
Why does the payments domain use idempotency keys for refunds?
Where is that decision documented?
```

```
I'm not sure whether to process the refund synchronously or queue it.
What do the ADRs and LLD say, and what would be consistent with how
the rest of the payments domain handles external calls?
```

```
The test_refund_exceeds_original_amount test is failing in an unexpected
way. Read the LLD, the test, and the implementation and help me diagnose
whether this is a test bug, an implementation bug, or an LLD gap.
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
| Understand the full workflow | `ai/claude/dev-practices/SKILL.md` |
| Run TDD on a component | `ai/claude/tdd/SKILL.md` |
| Analyse impact of a change | `ai/claude/apply-change/SKILL.md` |
| Write a downstream impact brief | `ai/claude/impact-brief/SKILL.md` |
| Check convention violations | `ai/claude/check-conventions/SKILL.md` |
