# PM Playbook

**Context:** You're the PM on [Project Name]. You work entirely through Claude Code — type a command, Claude does the work. You don't run terminal commands, you don't edit files manually, and you don't need to read code. Everything below is something you type into Claude Code.

---

## Step 1 — Set up (one time)

```bash
git clone <repo-url>
cd <project>
claude
```

Once Claude Code is open, verify it loaded correctly:

```
What product does this system build, what are the main user-facing
capabilities, and what does the current PRD say about priorities?
```

Claude should describe the product, main features, and product goals. If it doesn't, check you're in the repo root.

---

## Step 2 — Check progress at any time

```
/pm:review-progress
```

Claude reads the PRD and scans the codebase. Gives you a table of every requirement: Done / Partial / Not started, with notes on what's missing.

---

## Step 3 — Design a new feature from scratch

When you have a rough idea and want to think it through properly:

```
/pm:design-feature [describe your idea]
```

Claude walks you through 7 phases — discovery, user journey, edge cases, UX mockup, acceptance criteria, impact analysis, and writing to the PRD. You approve each phase before it moves to the next. A GitHub issue is created immediately after Phase 1 discovery so the work is tracked from the start; the PRD reference is added to it at the end.

---

## Step 4 — Add a quick requirement

When you already know what you want and just need it in the PRD:

```
/pm:add-feature [describe the requirement]
```

Claude creates a draft GitHub issue first to track the work, then drafts the requirement in the right format, checks for conflicts with existing requirements, gets your approval, updates the PRD, and adds the PRD reference to the issue.

---

## Step 5 — Update an existing requirement

```
/pm:update-requirement FR-[ID] [describe what to change]
```

Claude shows you the current requirement, drafts the change, flags any ripple effects on other requirements, and updates the PRD on your approval.

---

## Step 6 — Review a scope change from the team

When a developer opens a PR that changes the PRD:

```
/pm:review-scope-change [PR number]
```

Claude summarises what changed, assesses the impact, generates review questions for you to ask the team, and lets you approve or request changes — all within Claude Code.

---

## Step 7 — Work through open questions

When the PRD has unresolved questions blocking the team:

```
/pm:answer-questions
```

Claude walks through each open question one at a time, takes your answer, and updates the PRD.

---

## Step 8 — Report a bug

```
/pm:report-bug [describe what went wrong]
```

Claude gathers the details, checks for duplicates, and creates a well-structured GitHub issue.

---

## Step 9 — Review an impact brief before a deploy

Every non-trivial change produces an impact brief before it ships. Section 4 is the product mental model update — written for you. Ask Claude to surface it:

```
/impact-brief [PR number or describe the change]
```

Then ask follow-up questions before you approve:

```
What does a user see if this fails mid-way?
What is the rollback plan?
Which users see this first in the canary?
```

---

## Step 10 — Prepare a demo

```
/pm:prep-demo [feature or sprint you're demoing]
```

Claude produces a structured demo script: what to show, in what order, what to say at each step, and what edge cases to avoid.

---

## Step 11 — Prioritize the backlog

```
/pm:prioritize
```

Claude reads the PRD and open issues, summarises the options, and helps you work through trade-offs. You decide — Claude documents.

---

## Step 12 — Ask anything about the system

```
Why did we choose [technology]? What alternatives did we consider?
```

```
I want to change [requirement]. What parts of the system would be affected?
```

```
A user reported [problem]. Have we seen this before?
Check docs/04-operations/incident-registry.yaml.
```

---

## Ownership Rules

**You own product clarity end-to-end.** Requirements, design approvals, impact brief sign-off, staging validation, stakeholder updates. Claude does the drafting; you decide.

**Review impact briefs before every significant deploy.** Section 4 is written for you — if it's wrong, say so before the ship goes out.

**If you can't explain a design decision in plain English, ask.** A design you can't explain is a design you can't own.

---

## Command Reference

| I want to... | Command |
|---|---|
| Check what's been built | `/pm:review-progress` |
| Design a feature from scratch | `/pm:design-feature [idea]` |
| Add a quick requirement | `/pm:add-feature [description]` |
| Update a requirement | `/pm:update-requirement [FR-ID] [change]` |
| Review a scope change PR | `/pm:review-scope-change [PR number]` |
| Work through open questions | `/pm:answer-questions` |
| Report a bug | `/pm:report-bug [description]` |
| Review an impact brief | `/impact-brief [PR or change]` |
| Prepare a demo | `/pm:prep-demo [feature]` |
| Prioritize the backlog | `/pm:prioritize` |
