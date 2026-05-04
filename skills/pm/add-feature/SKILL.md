---
name: pm-add-feature
description: Add a new feature requirement to the PRD with acceptance criteria, requirement ID, and use case. Use when a PM wants to document a new feature request into the product requirements.
argument-hint: "[feature description]"
disable-model-invocation: true
---
# Add a New Feature Requirement

**Input:** $ARGUMENTS (description of the feature)

If `$ARGUMENTS` is empty, ask: "What feature do you want to add? Describe what the user should be able to do."

---

## Challenge Level — Ask First

Before step 1, ask:

> "What level of challenge would you like?
> - **Rigorous** — I'll push back until I have specific answers. Nothing gets drafted without justification.
> - **Moderate** — I'll ask all questions and flag gaps, but won't block on every one.
> - **Light** — I'll ask the essentials only and move fast.
>
> Default is **Moderate** if you don't specify."

---

## Steps

1. **Challenge before drafting** — before touching the PRD, ask the following. Apply the chosen challenge level.

   **TODO deferral is always available.** Any time the PM says "not sure", "add to TODO", "come back to this", or similar — record the item and proceed. Do not block on it.

   - **[All levels]** "What is the delivery surface?" Web UI, mobile, API/backend only, agentic workflow, internal/ops tool, or a combination? Always required — blocks at every level.

     *Follow-up probe (if vague or combo):* "Is there a primary surface, or are they equal-priority?"

   - **[All levels]** "What evidence confirms this is a real problem?" What are users doing or saying that points to this gap?

     *Follow-up probe (after any answer):* "Do you have a rough sense of how widespread this is — even a ballpark? If not, we can add it to open items."
     - *Rigorous*: one follow-up probe; if still no data, offer TODO deferral and note the gap
     - *Moderate*: offer TODO deferral if no data; note the gap and proceed
     - *Light*: ask once; if no answer, note and proceed

   - **[All levels]** "What does success look like?" What would tell you this feature worked?

     *Follow-up probe (after any answer):* "Do you have a rough current baseline or a hypothesis for how you'd validate this? If not, we can park it."
     - *Rigorous*: one follow-up probe; accept rough metric, hypothesis + validation plan, or TODO deferral
     - *Moderate*: accept any answer or TODO deferral; note the gap
     - *Light*: ask once; note if vague

   - **[Rigorous + Moderate]** "What's explicitly out of scope?" Unstated non-goals become scope creep.
     - *Rigorous*: one follow-up if skipped; offer TODO if still no answer
     - *Moderate*: ask; if skipped, note in summary

   At the end of this step, if any items were deferred, present the open items list:

   > **Open items to revisit before this feature ships:**
   > - [ ] [Question label]: [what's missing]

   At **Light**, summarize any unanswered questions as "Gaps to revisit" in the draft rather than blocking on them.

2. **Get the existing requirements structure** — prefer a graph query if available:
   ```
   /graphify query "all requirement IDs and use case numbers from PRD"
   /graphify query "PRD format and requirement areas FR-<AREA>"
   ```
   Fall back to reading `docs/01-product/prd.md` directly if the graph is unavailable or stale. You need the full document to pick the correct next ID and follow the exact format.

3. **Draft the requirement** following the existing format:
   - Requirement ID: next available `FR-<AREA>-N` (look at the existing IDs to pick the right area and number)
   - Description: what the user can do
   - Priority: Must Have / Should Have / Could Have
   - Acceptance criteria: specific, testable conditions
   - Implementation file: leave blank (the team fills this in)

4. **If the feature implies a new use case**, also draft a UC entry:
   - Actor
   - Preconditions
   - Flow (numbered steps)
   - Expected outcome
   - Error scenarios

5. **Check for conflicts** — does this feature contradict or duplicate any existing requirement? Flag it.

6. **Present the draft** to the user for review. Do NOT update the PRD until they approve.

7. **On approval**, update `docs/01-product/prd.md` with the new requirement (and use case if applicable).

8. **Create a GitHub issue** linking to the new PRD requirement:
   ```
   gh issue create --title "feat: <short description>" --body "PRD reference: FR-<ID>\n\n<acceptance criteria>"
   ```

## Important Rules

- Follow the EXACT format used in the existing PRD — don't invent a new structure
