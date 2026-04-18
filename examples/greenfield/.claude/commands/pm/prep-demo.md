# Prepare for Demo Review

Generate a demo checklist from the PRD so the PM knows exactly what to test and verify.

---

## Steps

1. **Read the PRD** at `docs/01-product/prd.md`. Extract all use cases (UC-0 through UC-N).

2. **Read the latest release notes** at `docs/releases/` to understand what's currently deployed.

3. **For each use case**, generate a checklist:
   ```
   ## UC-N: <name>

   ### Happy path
   - [ ] <step 1 — what to do>
   - [ ] <step 2 — what to expect>
   - [ ] <verify — acceptance criteria from PRD>

   ### Error scenarios
   - [ ] <error case from PRD — what to try, what should happen>

   ### Not testable yet
   - <what's blocked and why (missing API key, stub, etc.)>
   ```

4. **Add a section for admin features** if the PM has admin access:
   - Model profile switching
   - User management
   - Feature flags
   - Backend health

5. **Present the full checklist.** The PM uses this during the demo session.

## Important Rules

- Base the checklist on PRD acceptance criteria — not on what you think was built
- Flag items that are known limitations (see PRD §9 Out of Scope and release notes)
- Include the deployment URL from the release notes
