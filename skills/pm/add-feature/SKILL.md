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

## Steps

1. **Challenge before drafting** — before touching the PRD, ask:
   - "What evidence confirms this is a real problem?" Require a specific data point: support tickets, analytics, user research, churn feedback. "We think users want this" is not evidence — ask until a concrete data point is provided.
   - "What does success look like?" Require a specific metric with its current measured value and a target. "Improve engagement" is not an answer. "Increase X from N to M, measured by event Y" is.
   - "What's explicitly out of scope?" Unstated non-goals become scope creep.

   If any answer is vague, ask for the specific data point before proceeding. Do not draft a requirement for a problem that hasn't been justified.

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

- **Challenge stance applies at step 1.** See `skills/shared/challenge-stance.md` for the full standard. Do not add a requirement to the PRD for a problem that hasn't been justified with evidence.
- Follow the EXACT format used in the existing PRD — don't invent a new structure
- Requirements must be specific and testable — reject vague descriptions ("make it better")
- Don't specify technical implementation — that's the architect's job
- Always include error scenarios in use cases
