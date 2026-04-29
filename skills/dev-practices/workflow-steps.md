# Workflow Steps — Full Detail

Step-by-step reference for the 22-step HITL change workflow. The SKILL.md entrypoint has the summary; this file has the detail.

## Steps 1–5: Requirements and Design

**1. GitHub Issue**
Describe the change, root cause, and proposed solution. If no issue exists, create one with `gh issue create` before proceeding.

**1a. Figma Review (conditional)**
If a Figma design exists, extract requirements, interactions, and visual specs into the issue before proceeding to design.

**2. Impact Analysis** — use `/apply-change`
Identify affected components, APIs, configs, dependencies. Query the test registry and incident registry for the affected domain:
- Test registry: "which tests cover this area? are there coverage gaps?"
- Incident registry: "what has gone wrong here before? are the regression tests still in place?"

**2a. ROI Estimate (conditional)**
If >1 day of effort, add ROI Estimate section to the issue. See `roi-estimation.md`.

**3. Update Docs**
HLD/LLD/ADR before any code. Reference Figma specs if available. Use `/generate-docs` for new features.

**4. Update IaC**
Infrastructure manifests, migrations, configs if affected.

**5. Test Case Planning**
Before writing code, identify tests to add, update, or remove. Document in the issue or PR description.

**5a. Training Plan Stub (conditional)**
If the change introduces a new technical capability, draft a stub at `docs/03-engineering/training/<capability>.md`. See `roi-estimation.md §Training Plan`.

---

## Steps 6–12: TDD Build Cycle

> Use the `/tdd` skill for steps 6–8. See `tdd-design.md` for the conceptual background.

**6. AI Generates Tests (RED)**
AI generates maximum test coverage from the LLD + manifest facade contracts. No implementation code exists. Goal: MAXIMUM coverage of the SPEC.

**7. Human Reviews Tests**
Developer + QA review all generated tests. Add edge cases AI missed, add integration scenarios, remove trivial tests, challenge assumptions. Every test added gets registered in the test registry.

**8. Tests Improve the Design**
AI analyzes the test suite for LLD gaps. If tests reveal behavior the LLD doesn't describe, UPDATE THE LLD FIRST. The LLD and manifest are updated before any code is generated.

**9. Verify RED**
Run the full test suite. All NEW tests must fail (no implementation exists). If any pass, investigate — the test is wrong or the LLD describes existing behavior.

**10. Generate Code (GREEN)**
AI generates the simplest implementation to make all failing tests pass. Tests are the spec.

**11. Verify GREEN**
Run the full test suite (new + existing). All must pass. If new pass but existing fail → regression. Fix before proceeding.

**12. Refactor**
Simplify passing code. Remove duplication, improve naming. Rerun tests after each change. If any test breaks → revert.

---

## Steps 13–15: Review and PR Prep

**13. Code Review Round 1**
AI reviews: structure, security, LLD adherence, naming conventions. Fix all CRITICAL and HIGH findings before proceeding.

**14. Code Review Round 2**
AI reviews: edge cases, regressions, completeness, test quality. Fix findings, rerun test suite.

**15. Rerun Tests**
Confirm no regressions from Round 2 fixes.

---

## Steps 16–20: Ship

**16. Reconcile Docs**
If implementation diverged from the LLD, make the decision explicit: does the implementation reveal a better design (update docs) or did it drift from the intended design (fix code)? Never silently normalize drift.

**17. Create PR**
Link to GitHub issue. Include docs + IaC + training plan stub + code + tests in the same PR.

**18. Downstream Impact Brief + Rollout Plan** — use `/impact-brief`
See `downstream-impact.md` for the 5-section brief and risk-rated rollout table.

**19. Integration Verification (team lead only)**
Team lead runs the feature E2E, verifies intent matches HLD/LLD, reviews impact brief and rollout plan. Signs off or sends back.

**20. Figma Comparison (conditional)**
If Figma design exists, team lead compares implementation screen-by-screen. Lists and resolves all differences. No merge until resolved.

**21. Canary Deploy**
Deploy per the risk-rated rollout plan. Monitor go/no-go criteria.

**22. Promote or Rollback**
Lead promotes to full production or reverts the canary.

---

## Post-Ship: Steps 23–24

**23. Merge + Demo**
After lead sign-off, merge and demo to PM.

**24. 30-day ROI Check**
Developer + lead review: is the metric moving in the right direction?

**25. 90-day ROI Check**
Lead + PM review: actual vs estimated ROI. Update the ADR with an "Actual Outcome" section.
