# [Project Name] — Test Strategy

**Parent:** [link to engineering docs]
**Derived from:** [HLD documents, requirements]

---

## Test Case ID Convention

Format: `TC-{AREA}-{NN}` where AREA is a 2-3 letter code for the system area.

| Area code | System area |
|:---------:|-------------|
| SA | System architecture |
| AU | Authentication |
| DT | Data layer |
| AI | AI / inference |
| AG | Agents |
| SE | Security |
| OB | Observability |
| IN | Infrastructure |

---

## Test Case Template

For each test case, use this structure:

| Field | Value |
|-------|-------|
| **ID** | TC-XX-NN |
| **Objective** | What this test verifies (one sentence) |
| **Preconditions** | What must be true before the test runs |
| **Steps** | Numbered steps to execute |
| **Expected** | What a passing result looks like |
| **Priority** | Must Have / Should Have / Nice to Have |
| **Linked requirements** | Requirement IDs this test covers |
| **Linked incidents** | Incident IDs this test prevents (from incident registry) |

---

## Test Layers

| Layer | What it tests | Tool | Runs when |
|-------|--------------|------|-----------|
| Unit | Individual functions, pure logic | pytest | Every commit (CI) |
| Integration | Service + database, service + external API | pytest + testcontainers | Every PR (CI) |
| Contract | API request/response shapes match spec | pytest + schema validation | Every PR (CI) |
| E2E | Full user flows through the deployed system | Playwright / Cypress | Pre-deploy (staging) |
| Load | Performance under expected and peak load | k6 / Locust | Before launch, quarterly |

---

## Test Coverage by Vertical Slice

Organize test cases by the vertical slice (feature/showcase) they belong to. Each slice should have coverage across all relevant layers.

### Slice 1: [Name]

| ID | Objective | Layer | Priority |
|----|-----------|:-----:|:--------:|
| TC-XX-01 | [what it verifies] | Unit | Must Have |
| TC-XX-02 | [what it verifies] | Integration | Must Have |
| TC-XX-03 | [what it verifies] | E2E | Should Have |

### Slice 2: [Name]

[Same table structure]

---

## Agent-Specific Testing (for agentic systems)

| Test type | What it verifies | How |
|-----------|-----------------|-----|
| Behavioral baseline | Agent produces expected output for known inputs | Golden output comparison (capture V1 outputs, compare V2) |
| Tool call correctness | Agent calls the right tools with right arguments | Mock tools, assert call sequence |
| Self-eval calibration | LLM Judge scores correlate with human scores | Run eval dataset, compare against human labels |
| Guardrail coverage | Agent rejects adversarial inputs, respects limits | Adversarial test cases (prompt injection, rate limit abuse) |
| Idempotency | Retried agent runs don't produce duplicate side effects | Run same input twice, verify single external call |

---

## Test Registry Integration

Every test case in this strategy should have a corresponding entry in `docs/03-engineering/testing/test-registry.yaml`. The registry tracks:
- Which domain each test covers
- Risk level (what breaks if this test is absent)
- Origin (from requirements, from incidents, from code review)
- Linked incidents (what past failure this test prevents)

See [test-registry-template.yaml](../shared/templates/test-registry-template.yaml) for the format.

---

## Quality Gates

| Gate | When | Must pass |
|------|------|-----------|
| PR merge | Before merge to main | All unit + integration tests, convention checker, no CRITICAL security findings |
| Staging deploy | Before deploying to staging | All of above + E2E tests |
| Production deploy | Before deploying to production | All of above + manual verification scenarios from impact brief |

---

## Maintenance

- **Add tests before code** — TDD-as-design via `/tdd` skill
- **Link every new test to the registry** — unregistered tests are invisible to impact analysis
- **Review test coverage quarterly** — are there areas with no tests? Areas with brittle tests?
- **When an incident occurs** — add a regression test BEFORE closing the incident (required by incident registry)
