---
name: pm-update-requirement
description: Update an existing PRD requirement with new acceptance criteria, scope changes, or priority adjustments while maintaining traceability.
argument-hint: "[requirement ID and change description]"
disable-model-invocation: true
---
# Update an Existing Requirement

**Input:** $ARGUMENTS (requirement ID and what to change, e.g., "FR-CAMP-3 add support for TikTok publishing")

If `$ARGUMENTS` is empty, ask: "Which requirement do you want to update? Provide the ID (e.g., FR-AUTH-1) and describe the change."

---

## Steps

1. **Read the PRD** at `docs/01-product/prd.md`. Find the requirement by ID.

2. **Show the current requirement** to the user — full row including acceptance criteria.

3. **Draft the updated requirement.** Highlight what changed (old vs new).

4. **Check for ripple effects:**
   - Do other requirements reference or depend on this one?
   - Does this change affect any use case flows?
   - Does this change any NFR (performance, security, etc.)?
   - Does this affect the Out of Scope list?

5. **Present the draft and ripple effects** to the user. Do NOT update until approved.

6. **On approval**, update `docs/01-product/prd.md`.

7. **If the change is significant** (new behavior, removed behavior, changed acceptance criteria):
   - Comment on the relevant GitHub issue (if one exists)
   - Or create a new issue if none exists

## Important Rules

- Never silently change requirements — always show old vs new
- Flag ripple effects even if the user didn't ask about them
- If the change contradicts an ADR, flag it: "This conflicts with ADR D-X.Y — the architect and technical advisor need to weigh in"
