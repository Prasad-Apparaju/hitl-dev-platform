---
name: pm-review-progress
description: Review current sprint or milestone progress against PRD goals and acceptance criteria. Surfaces gaps and blockers.
argument-hint: "[sprint number or milestone name]"
disable-model-invocation: true
---
# Review Progress Against PRD

Compare what's been built against what was requested.

---

## Steps

1. **Get all functional requirements** — prefer a graph query if available:
   ```
   /graphify query "all functional requirements FR-* with implementation status"
   ```
   Fall back to reading `docs/01-product/prd.md` directly if the graph is unavailable or stale.

2. **Scan the V2 codebase** at `V2/app/`. For each requirement, check whether implementation exists:
   - Look at the "Implementation" column in the PRD if populated
   - Otherwise search for relevant controllers, services, models, and agents

3. **Classify each requirement:**

   | Status | Meaning |
   |---|---|
   | **Done** | Code exists, matches acceptance criteria |
   | **Partial** | Code exists but doesn't fully cover the acceptance criteria — explain what's missing |
   | **Not started** | No corresponding implementation found |

4. **Present a summary table:**
   ```
   | ID | Requirement | Status | Notes |
   |---|---|---|---|
   | FR-AUTH-1 | Email + password registration | Done | V2/app/controllers/auth.py |
   | FR-IMG-3 | Classify garment | Partial | Tool exists but no vision model key |
   ```

5. **Highlight:**
   - Requirements that diverged from the PRD (built differently than specified)
   - Open questions from §10 that block progress
   - Use cases that can't be tested yet (missing API keys, stubs)

## Important Rules

- Be honest about status — don't mark something Done if it's stubbed or mocked
- Reference specific files so the team can verify
- If the PRD acceptance criteria is vague, flag it as "criteria needs refinement"
