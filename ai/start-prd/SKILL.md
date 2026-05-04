---
name: start-prd
description: Start a new greenfield project from a PRD. Sets up CLAUDE.md conventions, initializes the system manifest, and prepares for /architect:design-system. Run this first on a new project before any code is written.
argument-hint: "[optional: project name or PRD path]"
---

# Start a New Project (PRD)

Setting up a new greenfield project for HITL AI-Driven Development. Work through these steps in order — pause after each and wait for confirmation before proceeding.

**Quick sanity check:** If this codebase already has substantial source code, you likely want `/start-brownfield` instead. If you are migrating from one system to another, use `/start-migration`. Say so if either applies.

---

## Step 1 — Customize CLAUDE.md

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What language and framework is this project? What test framework do you use? Any specific naming or formatting conventions?"
- Fill in the placeholders based on their answers.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 2 — Initialize the system manifest

If `docs/system-manifest.yaml` is missing or has template content:
- Ask: "What are the main domains or services in this project? For each, give a one-line description."
- Create `docs/system-manifest.yaml` with their answer. Map each domain to a plausible source path and mark as provisional.
- Say: "Manifest initialized. You'll refine domain boundaries as the system grows."

If a real manifest already exists, say: "Manifest found — skipping." and move on.

---

## Step 3 — Create your first GitHub issue

- Ask: "What's the first feature you want to build?"
- Run: `gh issue create --title "[feature name]" --body "Initial feature for [project name]. Created via HITL onboarding."`
- Show the issue URL.

---

## Step 4 — Confirm ready

Output this exactly:

---
**You're ready.**

Generate the design docs for your system before writing any code:

```
/architect:design-system
```

This produces the system manifest, HLDs, and LLDs from your PRD. The 31-step workflow reads these docs at nearly every step — they must exist before feature work starts.

For every change after that:
1. Create a GitHub issue — or use `/pm:add-feature` / `/pm:design-feature` to shape requirements first
2. Run `/dev-practices` — the 31-step workflow starts here
3. Design (HLD → LLD) before writing code
4. Code → tests → PR

---
