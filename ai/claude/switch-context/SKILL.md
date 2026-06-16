---
description: Switch HITL context to a different issue within the current session. Switches git branch, stashes in-progress work, reloads all artifacts for the target issue, and outputs a context-reset block. Use when context-switching between GitHub issues without starting a new Claude Code session.
argument-hint: "[issue number, e.g. 42 or GH-42]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and say: "This project hasn't been set up for HITL."

---

# Switch HITL Context

**Recommended approach:** start a new Claude Code session for each issue. A new session guarantees zero context bleed from the previous issue. Use this command only when a new session is not practical.

**What this command does:** switches to the target issue's branch, stashes any uncommitted work from the current branch, reloads all artifacts for the target issue, and outputs a context-reset block. After this command, treat all prior conversation context as stale — rely only on what is output below.

---

## Step 1 — Identify the target issue

If $ARGUMENTS contains an issue number (`42`, `GH-42`, or `issue/42-slug`): extract the number.

Otherwise read the current branch:
```bash
git branch --show-current
```
Extract the number from `issue/N-slug` format. If neither provides a number, ask: "Which issue are you switching to?"

Call the target issue number `N`.

---

## Step 2 — Stash uncommitted work on the current branch

```bash
git status --porcelain
```

If there are uncommitted changes:
```bash
git stash push -m "hitl: stash before switching to issue #N"
```
Report: "Stashed uncommitted changes on [current-branch]."

If the working tree is clean, say: "Working tree clean — no stash needed."

---

## Step 3 — Switch to the target branch

```bash
git branch --list "issue/${N}-*"
```

- **Branch exists and is already checked out:** say "Already on issue #N branch." and proceed to Step 4.
- **Branch exists, not checked out:**
  ```bash
  git checkout "issue/${N}-$(git branch --list "issue/${N}-*" | head -1 | xargs | sed 's|issue/[0-9]*-||')"
  ```
  Say: "Switched to issue #N branch."
- **No branch found:** stop and say:
  > No branch found for issue #N. The per-issue branch is created by `/hitl:dev-apply-change`.
  > Run `/hitl:dev-apply-change GH-N` first to initialise the branch and context for this issue.

---

## Step 4 — Load the HITL context file

Read `.hitl/current-change.yaml`. If it does not exist:
- Say: "No current-change.yaml on this branch. Run `/hitl:dev-apply-change GH-N` to initialise."
- Stop.

Extract:
- `change_id`, `tier`, `status`
- `current_step.number`, `current_step.name`, `current_step.phase`
- `manifest.domain`, `allowed_paths`
- `source_artifacts.issue`, `source_artifacts.hld`, `source_artifacts.lld`

---

## Step 5 — Reload source artifacts

Read these now. Do not rely on anything previously in the conversation context.

**1. GitHub issue:**
```bash
gh issue view N --json number,title,body,labels,assignees,milestone
```
Read the full body. Note the acceptance criteria.

**2. HLD** (path from `source_artifacts.hld`, or search `docs/02-design/hld/`):
Read in full. Note the architecture boundaries and interface definitions.

**3. LLD** (path from `source_artifacts.lld`, or search `docs/02-design/lld/`):
Read in full. Note the component contract, data model, and sequence diagrams.

**4. Current step context:**
Note what the current step number requires — refer to `ai/claude/dev-practices/SKILL.md` workflow summary if needed.

---

## Step 6 — Output context-reset block

Output this exactly, filled in from the data above:

---
**⚡ HITL context switched. All prior conversation context is now stale — discard it.**

**Active issue:** GH-[N] — [issue title]
**Branch:** [branch name]
**Tier:** [tier] | **Status:** [status]
**Phase:** [phase] | **Step:** [number] — [step name]
**Domain:** [domain]
**Allowed paths:** [allowed_paths list]

**Acceptance criteria (from GitHub issue):**
[AC list from the issue body]

**Architecture in scope (from HLD):**
[1-3 sentence summary of the relevant HLD section]

**Component contract (from LLD):**
[1-3 sentence summary of the relevant LLD section — interfaces, inputs, outputs]

**Where this was left off:**
[One paragraph: what the last completed step produced, what the current step requires. Based on current_step and the YAML status field.]

**Do not reference or use any context, decisions, or code from before this switch.**
To return to the previous issue, run `/hitl:dev-switch-context [previous-issue-number]`.

---

## Never

- Do not reference the previous issue's work after this command completes
- Do not carry forward assumptions from the prior conversation
- Do not proceed with implementation — wait for the user's next instruction
- Do not skip Step 5 — loading artifacts from disk, not from conversation memory, is the whole point
