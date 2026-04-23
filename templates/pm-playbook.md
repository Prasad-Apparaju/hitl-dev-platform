# PM Playbook

**Context:** You're the PM on [Project Name]. Your job is to write requirements, review and approve designs, track progress, review impact briefs before deploys, and translate technical changes into product language for stakeholders. Claude Code helps you do all of this — you don't need to read code.

---

## Step 1 — Set up your environment

```bash
git clone <repo-url>
cd <project>
claude   # CLAUDE.md auto-loads on startup — no config needed
```

Verify Claude loaded the project context:

```
What product does this system build, what are the main user-facing
capabilities, and what does the current PRD say about priorities?
```

---

## Step 2 — Understand the system

```
Give me a non-technical summary of what [Product Name] does,
who the users are, and what the key product capabilities are.
Reference docs/01-product/prd.md.
```

To understand current development status:

```
Read docs/01-product/prd.md and give me a plain-English status update:
1. What has been built and is working?
2. What's in progress right now?
3. What's blocked and why?
4. What's the next thing to ship?
```

---

## Step 3 — Write or update a product requirement

When you need to capture a new feature or change a requirement:

```
/generate-docs

I need to document a new product requirement for [feature name].
Here's what I need it to do: [describe in plain English].

Generate an HLD first so I can review the proposed design before
the team starts detailed work.
```

Once the HLD is generated, ask Claude to explain anything unclear:

```
Explain what the [component name] does in plain English.
What does a user experience when this component is working correctly,
and what do they experience when it fails?
```

When you're satisfied, approve the HLD:

```
Approved — proceed to LLD for [feature name].
```

---

## Step 4 — Review a design before the team implements it

When an HLD or LLD is ready for your review:

```
Read the HLD at docs/02-design/technical/hld/[feature].md.
Explain it to me as a product manager — what does this design
do, what are the main user-facing behaviors it enables,
and what are the key trade-offs the team made?
```

To check the design matches what you had in mind:

```
Here's what I expected this feature to do: [describe].
Read the LLD at docs/02-design/technical/lld/[path].md and tell me:
1. Does the design match my expectation?
2. What edge cases does the design handle that I might not have thought of?
3. What is explicitly out of scope in this design?
```

To understand why a technical decision was made:

```
Why did we choose [technology/approach]? Where is that decision
documented? What alternatives did we consider and why did we reject them?
```

---

## Step 5 — Create a well-scoped GitHub issue

Before the team starts any work, there must be a GitHub issue:

```
I want the team to [describe the work]. Help me write a GitHub issue with:
1. A clear one-line title
2. User story: "As a [persona], I want [capability] so that [outcome]"
3. Acceptance criteria — bullet list of what "done" looks like
4. Out of scope — what this issue explicitly does NOT cover
5. Dependencies — what must be done before this can start
```

---

## Step 6 — Track progress and prepare status updates

For a sprint status update:

```
Read docs/01-product/prd.md and the recent git log (last 2 weeks).
Produce a stakeholder update covering:
1. What shipped this sprint (user-visible impact, not code details)
2. What's in flight (ETA if known)
3. Any blockers the product team needs to know about
4. Key decisions made and why (plain English, not technical)
```

---

## Step 7 — Review an impact brief before a deploy

Every non-trivial change produces an impact brief. Your job is to review Section 4 (product mental model) before approving:

```
/impact-brief

What is changing in [PR number / branch / describe change]?
Focus on Section 4 — what assumptions do I currently hold
about this feature that will no longer be true after this ships?
```

Ask follow-up questions before approving:

```
What does a user see if this change fails mid-way through?
Is there a rollback plan and how long does rollback take?
What is the canary strategy — which users will see this first?
```

---

## Step 8 — Validate a feature before sign-off

When testing a feature before approval:

```
I'm about to test [feature]. Read the LLD at
docs/02-design/technical/lld/[path].md and give me a manual
test script for a non-technical tester:
1. What to set up before testing
2. Step-by-step actions to take
3. What the expected outcome is for each step
4. What failure looks like
```

---

## Step 9 — Ask about anything you're unsure of

```
Why does [thing] work this way? What would happen if we did [alternative]?
Where is that decision documented?
```

```
I want to change [requirement]. What parts of the system would be
affected? Read the relevant HLD/LLD and tell me the blast radius
in plain language.
```

```
A user reported [problem]. Is this a known issue? Check
docs/04-operations/incident-registry.yaml and tell me if we've
seen this before and what we did about it.
```

---

## Ownership Rules

**You own product clarity end-to-end.** Requirements, design approvals, impact brief sign-off, staging validation, stakeholder updates.

**Review impact briefs before every significant deploy.** Section 4 of every brief is written for you — if it's wrong, say so before the ship goes out.

**If you can't explain a design decision in plain English, ask.** A design you can't explain is a design you can't own.

---

## Key Files

| File | What it is |
|------|-----------|
| `CLAUDE.md` | Conventions and workflow — auto-loaded every session |
| `docs/01-product/prd.md` | Product requirements — the source of truth for scope |
| `docs/02-design/technical/hld/` | High-level architecture — your design approval gate |
| `docs/02-design/technical/adrs/design-decisions.md` | Why every major decision was made |
| `docs/04-operations/incident-registry.yaml` | Past failures and lessons learned |
| `templates/prd-template.md` | PRD template with AI-friendly writing tips |

---

## PM How-To Summary

| I want to... | Step |
|---|---|
| Understand system status | Step 2 |
| Write a new requirement | Step 3 (`/generate-docs`) |
| Review a design | Step 4 |
| Create a GitHub issue | Step 5 |
| Write a stakeholder update | Step 6 |
| Review a change before deploy | Step 7 (`/impact-brief`) |
| Validate a feature | Step 8 |
| Understand a trade-off | Step 9 |
