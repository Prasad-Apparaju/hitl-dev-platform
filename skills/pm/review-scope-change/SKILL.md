---
name: pm-review-scope-change
description: Analyze a requested scope change: impact on existing requirements, dependencies, effort delta, and recommendation.
argument-hint: "[description of scope change request]"
disable-model-invocation: true
---
# Review a Scope Change from the Team

**Input:** $ARGUMENTS (PR number or branch name)

If `$ARGUMENTS` is empty, check for open PRs that modify `docs/01-product/prd.md`:
```bash
gh pr list --search "prd" --state open
```

---

## Steps

1. **Read the PR diff** for `docs/01-product/prd.md`:
   ```bash
   gh pr diff <PR-number> -- docs/01-product/prd.md
   ```

2. **Summarize the proposed changes:**
   - Requirements added (new FR-* IDs)
   - Requirements modified (what changed, old vs new)
   - Requirements removed
   - Use cases affected
   - Out-of-scope items affected

3. **Assess impact:**
   - Does this change what users see or do?
   - Does this change priorities?
   - Does this add scope (more work) or reduce scope?
   - Is the justification documented in the PR?

4. **Generate review questions** for the PM to ask the team:
   - "Why is this change needed?"
   - "What happens if we don't make this change?"
   - "Does this affect the timeline?"
   - "Are there acceptance criteria for the new/changed requirements?"

5. **Present the summary and questions.** The PM decides: approve, request changes, or reject.

6. **If approved:**
   ```bash
   gh pr review <PR-number> --approve --body "PRD scope change approved by PM"
   ```

7. **If changes requested:**
   ```bash
   gh pr review <PR-number> --request-changes --body "<PM feedback>"
   ```

## Important Rules

- The PM owns PRD scope — their decision is final
- Every scope change should have a justification
- If the change removes a "Must Have" requirement, flag it prominently
