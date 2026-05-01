# Workflow Steps — Full Detail

Step-by-step reference for the 30-step HITL change workflow. The SKILL.md entrypoint has the summary; this file has the detail.

---

## Steps 1–2: Requirements

**1. GitHub Issue**
Describe the change, root cause, and proposed solution. If no issue exists, create one with `gh issue create` before proceeding. Use `/pm/add-feature` for features or `/pm/report-bug` for bugs.

**2. Figma Review (conditional)**
If a Figma design exists, the PM or developer reads the Figma file directly and adds requirements, interactions, and visual specs into the GitHub issue. No command — this is a manual extraction step.

---

## Steps 3–9: Design

**3. Impact Analysis** — use `/apply-change`
Reads `system-manifest.yaml`, test registry (`docs/03-engineering/testing/test-registry.yaml`), and incident registry (`docs/incident-registry.yaml`) to identify affected components, APIs, configs, and dependencies. Produces an effort estimate. Outputs `.hitl/current-change.yaml` with change ID, tier, affected domains, source artifact paths, and `token_tracking.estimated` — a phase-level token cost estimate based on artifact file sizes. See `roi-estimation.md` for the estimation method.

**4. ROI Estimate (conditional)**
If the step 3 effort estimate exceeds 1 day, add an ROI section to the GitHub issue: expected outcome (specific and falsifiable), baseline metric (measured now, not estimated), measurement plan, 30/90-day checkpoints. Include `token_tracking.estimated.total_cost_usd` from `.hitl/current-change.yaml` as the "AI dev tokens" cost line item. See `roi-estimation.md` for the template. No command.

**5. Update Docs** — use `/generate-docs`
Using the affected component list from `.hitl/current-change.yaml` (step 3) and Figma specs from step 2 (if available): create or update HLD at `docs/02-design/technical/hld/<feature>.md` and LLD at `docs/02-design/technical/lld/<component>.md`. Update ADRs for any new design decisions. Architect must approve the HLD before LLD generation begins. LLD must be approved before implementation starts.

**6. Update IaC**
Using the IaC section of `.hitl/current-change.yaml` (step 3) and the LLD at `docs/02-design/technical/lld/<component>.md` (step 5): update Terraform/Kubernetes manifests, migrations, and configs. Only if step 3 identified IaC changes.

**7. Test Case Planning**
Using the LLD at `docs/02-design/technical/lld/<component>.md` (step 5), incident registry, and test registry: produce a concrete list of new tests, updated tests, removed tests, and regression tests. Record the test plan in the GitHub issue and in `.hitl/current-change.yaml` under `tests.plan`.

**8. Training Plan Stub (conditional)**
If the change introduces a new architectural pattern, external system, framework, ML/AI technique, or significant mental-model-changing refactor: draft a stub at `docs/03-engineering/training/<capability>.md`. Triggers: new architectural pattern, new external system, new framework, new ML/AI technique, or a significant mental-model-changing refactor. New endpoints, bug fixes, and preserving-the-model refactors do not require a training plan.

**9. Package Decision Packet**
Architect manually assembles `docs/decisions/issue-<N>.yaml` using `templates/decision-packet-template.yaml`. Fields: issue number, affected domains from `system-manifest.yaml`, LLD path from step 5, IaC plan from step 6, test plan from step 7, training stub path from step 8 if applicable. Constraint: each packet must touch exactly one manifest domain — if two slices would modify the same domain, they are sequential, not parallel. Architect hands one packet per slice to each assigned developer.

---

## Recording Token Costs (recurring — after every Claude Code session)

At the end of each Claude Code session, Claude Code displays the session cost. Record it in `.hitl/current-change.yaml` under `token_tracking.actual.sessions`:

```yaml
token_tracking:
  actual:
    sessions:
      - date: "YYYY-MM-DD"
        steps_covered: [10, 11, 12]   # which workflow steps ran this session
        cost_usd: 0.52                # from Claude Code session summary
```

Do this before closing the session — the summary is not persisted anywhere else. Sum all session costs to get `token_tracking.actual.total_cost_usd`.

---

## Steps 10–17: Build (TDD Cycle)

> Use the `/tdd` skill for steps 10, 12, and 14. See `tdd-design.md` for the conceptual background.

**10. AI Generates Tests (RED)** — use `/tdd`
Developer passes the LLD path from the decision packet to `/tdd`. The skill reads `docs/02-design/technical/lld/<component>.md` (step 5) and `system-manifest.yaml` directly — it does not read the decision packet file itself. Generates maximum test coverage: happy paths, error paths, edge cases, preconditions, boundary entities, contract compliance from manifest facade APIs. Writes test files to `tests/`. Registers each test in `docs/03-engineering/testing/test-registry.yaml`. No implementation code exists at this point.

**11. Human Reviews Tests** — use `/qa/review-tests`
Developer reads the same LLD (`docs/02-design/technical/lld/<component>.md`, step 5) and incident registry to identify gaps in the generated tests. Adds edge cases AI missed, adds integration scenarios from domain knowledge, removes trivial or wrong tests, challenges assumptions. Updates `docs/03-engineering/testing/test-registry.yaml` for every test added or removed.

**12. Tests Improve the Design** — use `/tdd`
`/tdd` analyzes the test files in `tests/` against the LLD at `docs/02-design/technical/lld/<component>.md`. For each test that covers behavior the LLD does not describe, proposes a specific LLD update. LLD is updated at the same path before any code is written. If LLD changes are significant, architect re-reviews and confirms before proceeding.

**13. Verify RED**
Run the full test suite. All new tests must fail (no implementation exists). If any new test passes: either fix the test (it is wrong) or remove it (LLD already describes existing behavior). Resolve all ambiguities before proceeding — a passing test before implementation means the spec is unclear or redundant.

**14. Generate Code (GREEN)** — use `/tdd`
`/tdd` reads the failing test files in `tests/`, the updated LLD at `docs/02-design/technical/lld/<component>.md` (step 12), `system-manifest.yaml`, and `CLAUDE.md`. Generates the simplest implementation that makes all failing tests pass. Does not anticipate future requirements.

**15. Verify GREEN**
Run the full test suite (new + existing). All must pass. If existing tests fail: regression — fix the regression and re-run step 14 before proceeding. Do not proceed with a broken existing test suite.

**16. Refactor**
Simplify passing code. Remove duplication, improve naming. Rerun tests after each change. Done when no further simplification is possible without breaking a test. Do not introduce new behavior during refactor.

**17. Convention Checks** — use `/check-conventions`
Run `semgrep scan --config .semgrep/ --error` and manifest drift check against `convention-checks.yaml`. Exit criterion: zero violations. Fix all violations before proceeding. Do not defer to CI — catching here avoids a failed CI run.

---

## Steps 18–21: Verify

**18. Code Review Round 1** — use `/check-implementation`
Uses the `spec-conformance-reviewer` agent. Reads implementation files plus the LLD at `docs/02-design/technical/lld/<component>.md` (step 12) and `system-manifest.yaml`. Reviews: structure, security, LLD adherence, naming conventions. Fix all CRITICAL and HIGH findings before proceeding. MEDIUM findings are documented for Round 2.

**19. Code Review Round 2** — use `/check-implementation`
Uses the `spec-conformance-reviewer` agent. Reads implementation files, test files in `tests/`, and the test plan from `.hitl/current-change.yaml` (step 7). Reviews: edge cases, regressions, test quality, and completeness against the test plan. Fix all findings. Rerun full test suite after fixes.

**20. Rerun Tests**
Confirm no regressions from Round 2 fixes. All tests must pass.

**21. Reconcile Docs**
Compare implementation against the LLD at `docs/02-design/technical/lld/<component>.md`. If they diverge, make the decision explicit:
- **Implementation reveals a better design** → update the LLD using `/generate-docs`, have architect confirm, document decision in PR description or ADR
- **Implementation drifted from the intended design** → fix the code, rerun steps 18–20
Never silently normalize drift.

---

## Steps 22–23: Assess

**22. Downstream Impact Brief** — use `/impact-brief`
`/impact-brief` reads `.hitl/current-change.yaml`, `git diff main...HEAD`, `system-manifest.yaml`, incident registry, and test registry. Produces a 5-section brief. Section 5 contains the rollout strategy draft including risk tier and go/no-go criteria.

**23. Risk-Rated Rollout Plan** — use `/ops/review-release`
Ops reads the rollout strategy from step 22's section 5 and the incident registry for the affected domains. Reviews and approves canary tier and go/no-go criteria, or adjusts them. The approved plan must exist before the PR is created.

---

## Steps 24–28: Ship

**24. Create PR**
Includes: issue link, HLD/LLD from step 5 (`docs/02-design/technical/`), IaC from step 6, implementation code, test files from `tests/`, decision packet (`docs/decisions/issue-<N>.yaml`, step 9), impact brief (step 22), approved rollout plan (step 23). Also: copy `token_tracking.actual` from `.hitl/current-change.yaml` into `docs/03-engineering/costs/token-cost-registry.yaml` and recompute the aggregate block.

**25. Integration Verification** — use `/architect/verify-traceability`
Lead runs each slice E2E and verifies cross-slice composition: do the slices integrate correctly when all are deployed together? Also verifies the traceability chain for each slice: GitHub issue → design PR merged → implementation matches LLD → test files cover the spec → impact brief complete → rollout plan approved. Signs off or sends back with findings.

**26. Figma Comparison (conditional)**
If Figma design exists, lead compares running implementation to the Figma spec from step 2 screen by screen. Lists and resolves all differences. Exit criterion: zero unresolved differences before merge.

**27. Merge + Canary Deploy** — use `/ops/monitor-canary`
Lead coordinates merge order if multiple slices are landing. Lead triggers merge and deploys per the approved rollout plan from step 23. Remaining slices that have not yet merged must rebase against main and rerun steps 17–19 before their own merge. Monitor go/no-go criteria.

**28. Promote or Rollback**
At each canary step, verify all go/no-go criteria from the approved plan (step 23). If all met: promote to next tier. If any fail: pause and investigate before deciding — do not roll back automatically on noise. Lead makes the final call.

---

## Steps 29–30: Post-Ship

**29. 30-Day ROI Check (conditional)**
Only if step 4 was done. Reads expected outcome and baseline metric from step 4 in the GitHub issue. Developer + lead assess whether the metric is moving in the right direction. Also check whether `token_tracking.actual.total_cost_usd` was within 50% of estimated — if not, add a note to the cost registry entry explaining the variance. See `roi-estimation.md` for the review template.

**30. 90-Day ROI Check (conditional)**
Only if step 4 was done. Reads expected outcome and baseline metric from step 4 and 30-day findings from step 29. Lead + PM compare actual vs estimated ROI. Update ADR at `docs/02-design/technical/adrs/` with an Actual Outcome section. Review `docs/03-engineering/costs/token-cost-registry.yaml` aggregate block — if 5+ entries exist, apply the optimization signals from the registry template. See `roi-estimation.md`.
