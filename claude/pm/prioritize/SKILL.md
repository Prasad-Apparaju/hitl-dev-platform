---
name: pm-prioritize
description: Help PM prioritize features or backlog items using value, effort, risk, and strategic alignment. Use when the team needs to make prioritization decisions.
argument-hint: "[list of features or 'current backlog']"
disable-model-invocation: true
---
# Prioritize the Backlog

Review all requirements and help the PM prioritize.

---

## Steps

1. **Get all functional requirements** — prefer a graph query if available:
   ```
   /graphify query "all requirements from PRD grouped by priority"
   /graphify query "Must Have Should Have Could Have requirements"
   ```
   Fall back to reading `docs/01-product/prd.md` directly if the graph is unavailable or stale.

2. **Present the current priority breakdown:**
   ```
   Must Have: N requirements (list IDs)
   Should Have: N requirements (list IDs)
   Could Have: N requirements (list IDs)
   ```

3. **For each Should/Could item**, analyze:
   - **Dependencies:** Is anything else blocked on this?
   - **User impact:** Does this affect a core use case (UC-0 through UC-4)?
   - **Effort estimate:** Is it quick (< 1 day) or substantial (> 1 day)?
   - **Risk if deferred:** What happens if we don't build this for alpha/GA?

4. **Suggest priority changes** with reasoning:
   ```
   PROMOTE to Must: FR-xxx-N — reason
   DEMOTE to Could: FR-xxx-N — reason
   KEEP: FR-xxx-N — reason
   ```

5. **Wait for the PM's decisions.** Update the PRD priority column on approval.

## Important Rules

- Don't change priorities without PM approval
- "Must Have" means the product doesn't ship without it — use sparingly
- Consider what's needed for alpha (immediate) vs GA (later) vs V3 (future)
