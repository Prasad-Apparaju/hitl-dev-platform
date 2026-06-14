# ADR-0003: Test Strategy

| | |
|---|---|
| **Status** | Draft — complete before the first Tier 2 change |
| **Date** | [fill in] |
| **Deciders** | [fill in: dev lead, QA lead] |
| **Supersedes** | — |
| **Related** | ADR-0001 (HITL adoption), ADR-0002 (documentation-first) |

---

## 1. Context

The HITL workflow requires a defined test strategy before TDD begins (step 7: test case planning, `/hitl:qa-plan-tests`). Without it, "write tests first" is interpreted inconsistently and coverage gates cannot be enforced. This ADR records the team's decisions about test frameworks, coverage thresholds, mocking policy, and CI gates.

## 2. Decision

### Test framework

| Layer | Framework | Notes |
|-------|-----------|-------|
| Unit | [fill in] | |
| Integration | [fill in] | |
| E2E | [fill in] | |
| Contract | [fill in — or "N/A"] | |

### Coverage gate

[fill in — HITL default is ≥90% per changed component. Record your threshold here and whether it is enforced in CI or advisory only.]

### Mocking policy

[fill in — what gets mocked vs what must hit real infrastructure. Example: "External third-party APIs are mocked in unit and integration tests. Database uses a real testcontainer. File system operations use real temp directories."]

### CI gate

| Gate | When it runs | Must pass to proceed |
|------|-------------|---------------------|
| Unit + integration | Every PR | Yes — blocks merge |
| E2E | [fill in] | [fill in] |
| Coverage check | Every PR | [fill in — pass/advisory] |

### Test naming convention

[fill in — Example: "Test names describe behavior, not implementation. Format: `test_<verb>_<condition>_<expected_result>`."]

## 3. Alternatives Considered

[fill in after team discussion]

## 4. Consequences

### Positive
- [fill in]

### Negative
- [fill in]

## 5. Implementation Notes

Every test must be registered in `docs/03-engineering/testing/test-registry.yaml` (template: `test-registry-template.yaml`). Unregistered tests are invisible to impact analysis and `/hitl:dev-apply-change`.

Tests are written before implementation in the HITL workflow — step 10 (`/hitl:dev-tdd`). QA reviews tests at step 11 (`/hitl:qa-review-tests`) before implementation begins.

## 6. Open Questions

1. [fill in: any team-specific testing constraints, e.g., slow external services, flaky third-party sandboxes, licensing constraints on test data]

## 7. Status

**Draft.** Must be accepted before the first Tier 2 change. Assign to: [fill in: QA lead or dev lead].

## ROI Estimate

**Value dimension:** Quality / Risk
**Expected outcome:** [fill in after strategy is decided]
**Baseline metric:** [fill in: current test coverage, current defect escape rate]
**Expected cost:** [fill in after strategy is decided]
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
