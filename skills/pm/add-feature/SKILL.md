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

1. **Get the existing requirements structure** — prefer a graph query if available:
   ```
   /graphify query "all requirement IDs and use case numbers from PRD"
   /graphify query "PRD format and requirement areas FR-<AREA>"
   ```
   Fall back to reading `docs/01-product/prd.md` directly if the graph is unavailable or stale. You need the full document to pick the correct next ID and follow the exact format.

2. **Draft the requirement** following the existing format:
   - Requirement ID: next available `FR-<AREA>-N` (look at the existing IDs to pick the right area and number)
   - Description: what the user can do
   - Priority: Must Have / Should Have / Could Have
   - Acceptance criteria: specific, testable conditions
   - Implementation file: leave blank (the team fills this in)

3. **If the feature implies a new use case**, also draft a UC entry:
   - Actor
   - Preconditions
   - Flow (numbered steps)
   - Expected outcome
   - Error scenarios

4. **Check for conflicts** — does this feature contradict or duplicate any existing requirement? Flag it.

5. **Present the draft** to the user for review. Do NOT update the PRD until they approve.

6. **On approval**, update `docs/01-product/prd.md` with the new requirement (and use case if applicable).

7. **Create a GitHub issue** linking to the new PRD requirement:
   ```
   gh issue create --title "feat: <short description>" --body "PRD reference: FR-<ID>\n\n<acceptance criteria>"
   ```

## Important Rules

- Follow the EXACT format used in the existing PRD — don't invent a new structure
- Requirements must be specific and testable — reject vague descriptions ("make it better")
- Don't specify technical implementation — that's the architect's job
- Always include error scenarios in use cases
