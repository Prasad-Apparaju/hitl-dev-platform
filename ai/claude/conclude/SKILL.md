---
name: conclude
description: Turn a concluded Slack design-room thread into GitHub artifacts — ADR, issue, and HLD/LLD updates. Reads the thread, extracts the decision, confirms the summary, then generates and commits the artifacts. Use after a team has reached a decision in a Slack thread.
argument-hint: "[Slack thread URL or topic description]"
disable-model-invocation: true
---

# Conclude — Turn a Slack Discussion into GitHub Artifacts

Reads a Slack design-room thread, extracts the concluded decision, and generates the appropriate GitHub artifacts (ADR, issue, HLD/LLD updates). The human decides; this skill does the paperwork.

**Input:** $ARGUMENTS (Slack thread URL, or a topic description like "auth migration approach")

If `$ARGUMENTS` is empty, ask: "Which design-room thread should I conclude? Paste the Slack thread URL or describe the topic."

---

## Step 1 — Read the thread

1. **Find the thread** — use `slack_read_thread` if a URL or timestamp is provided, or `slack_search_public_and_private` to find the thread by topic
2. **Extract from the conversation:**
   - **Decision:** What was decided? (Look for explicit markers: "Decision:", "Let's go with", "Agreed:", or the last substantive message before consensus)
   - **Rationale:** Why this option? What constraints drove it?
   - **Alternatives considered:** What other options were discussed and why were they rejected?
   - **Participants:** Who contributed to the discussion?
   - **Open questions:** Anything left unresolved or flagged for later?
   - **Affected components:** Which domains/services does this touch? Prefer a graph query:
     ```
     /graphify query "domain: <topic-keyword> components and dependencies"
     /graphify query "facade APIs affected by <decision-topic>"
     ```
     Fall back to reading `docs/system-manifest.yaml` directly if the graph is unavailable or stale.

3. **Present the summary** to the user:

```
## Thread Summary

**Topic:** [topic]
**Decision:** [one-sentence decision]
**Rationale:** [why]
**Alternatives rejected:** [list with reasons]
**Participants:** [names]
**Affected domains:** [from manifest]
**Open questions:** [if any]
```

Ask: "Is this an accurate summary of the decision? Anything to add or correct?"

Do NOT proceed until the user confirms.

---

## Step 2 — Determine which artifacts to generate

Based on the decision type, determine which artifacts are needed:

| Decision type | Artifacts to generate |
|--------------|----------------------|
| Architectural choice (technology, pattern, approach) | ADR + GitHub issue |
| Design change (new component, changed API, new data model) | ADR + HLD/LLD update + GitHub issue |
| Process change (workflow, convention, deployment strategy) | ADR + CLAUDE.md or manifest update |
| Bug fix or operational decision | GitHub issue only |
| Scope/priority change | GitHub issue only (label: `product-decision`) |

Present the plan: "Based on this decision, I'll generate: [list]. Does that look right?"

Do NOT proceed until the user confirms.

---

## Step 3 — Generate the ADR

If an ADR is needed:

1. **Read existing ADRs** in `docs/02-design/technical/adrs/` to determine the next available number and check for related ADRs
2. **Generate the ADR** following the template at `ai/shared/templates/adr-template.md`:
   - **Context** — from the thread discussion (the problem, constraints, what triggered it)
   - **Decision** — the concluded choice, with enough detail to implement
   - **Alternatives** — each rejected option with the reason from the thread
   - **Consequences** — positive, negative, neutral
   - **ROI Estimate** — ask the user for value dimension and expected outcome if not obvious from the thread
   - **Deciders** — the thread participants
   - **Status** — Accepted (it was decided in the thread)
   - **Related** — link to affected HLDs/LLDs and any related ADRs

3. **Present the draft ADR** for review. Ask: "Review the ADR. Is the decision captured accurately? Any consequences I missed?"

---

## Step 4 — Update HLD/LLD if needed

If the decision changes the design:

1. **Read the affected HLD/LLD** from the paths identified via the system manifest
2. **Draft the update** — add/modify the relevant section. Mark new content clearly.
3. **Present the diff** for review

If the decision introduces a new component not in the current design, note: "This decision introduces [component] which doesn't have an LLD yet. Create one now or defer to implementation?"

---

## Step 5 — Create the GitHub issue

Generate a GitHub issue using the issue template (`ai/shared/templates/issue-template.md`):

- **Title:** Action item from the decision (imperative mood)
- **Body:**
  - Link to the ADR (once merged)
  - Summary of what needs to be implemented
  - Acceptance criteria derived from the decision
  - Affected domains from the manifest
  - ROI estimate section (from the ADR)
  - Downstream impact section (which stakeholders are affected)

Present the draft issue for review.

---

## Step 6 — Commit and post back

Once all artifacts are approved:

1. **Create a branch** — `decision/<short-topic-name>`
2. **Commit all artifacts** — ADR, HLD/LLD updates
3. **Open a PR** — title: "Decision: [topic]", body links to the Slack thread and lists all artifacts
4. **Create the GitHub issue** via `gh issue create`
5. **Post to the Slack thread** — reply with links:

```
✅ Decision documented:
• ADR: [link to PR]
• Issue: [link to issue]
• HLD/LLD updates: [link to PR if applicable]
```

---

## Important Rules

- **Never infer a decision that wasn't explicitly stated.** If the thread doesn't have a clear conclusion, say: "I can't find a clear decision in this thread. Can you point me to the message where the team agreed?"
- **The ADR captures what was decided, not what should be decided.** This skill documents concluded discussions, not open ones.
- **Thread participants are listed as Deciders** in the ADR. If someone who should have been involved wasn't in the thread, flag it: "Note: [role] wasn't in this discussion. Should they review the ADR before it's accepted?"
- **Don't skip the ROI estimate.** If the thread doesn't mention expected value, ask the user. Every decision has a cost; documenting expected return makes 30/90-day verification possible.
- **Preserve the thread's language.** Use the team's actual words for rationale and alternatives — don't rephrase into generic architecture-speak. The ADR should sound like the team, not a textbook.
