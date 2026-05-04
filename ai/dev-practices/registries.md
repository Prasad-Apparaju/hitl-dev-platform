# Test Registry + Incident Registry — Reference

Two knowledge bases that grow with every change and every incident. They prevent the team from making the same mistake twice and make impact analysis concrete instead of guesswork.

## Test Case Registry

**Location:** `docs/03-engineering/testing/test-registry.yaml`

A catalog of test cases with metadata — not the test code itself (that stays in `tests/`), but an index queryable by domain, risk level, origin, and linked incident.

| Field | Purpose |
|-------|---------|
| `id` | Unique identifier (TC-NNN) |
| `name` | Human-readable test name |
| `domain` | Manifest domain this test covers |
| `risk` | low / medium / high / critical |
| `type` | unit / integration / contract / e2e / exploratory |
| `origin` | tdd / qa-review / incident-regression / design-pr |
| `incident_ref` | INC-NNN if added after an incident |
| `file` | Path to the actual test file + function |

### When it grows
- Step 6–8 (TDD cycle): every test added by developer or QA gets registered
- Post-incident: regression test registered with `origin: incident-regression` and `incident_ref: INC-NNN`

### How it's consumed
- Step 2 (Impact analysis): "which tests cover the affected domain? are there coverage gaps?"
- Step 6 (AI generates tests): AI reads relevant entries — especially incident-regression tests that must not be accidentally removed
- QA review: "is the regression test for INC-X in the plan?"

See `ai/templates/test-registry-template.yaml` for the full format with examples.

## Incident Registry

**Location:** `docs/04-operations/incident-registry.yaml`

A catalog of production incidents with root cause, affected domain, fix, regression test, and canary criteria.

| Field | Purpose |
|-------|---------|
| `id` | Unique identifier (INC-NNN) |
| `date`, `severity` | When and how bad |
| `domain` | Manifest domain affected |
| `summary` | One-line description |
| `root_cause` | What actually went wrong (not symptoms) |
| `fix` | What was done — PR link, ADR link |
| `regression_test` | TC-NNN linking to the test registry |
| `canary_criteria_added` | What monitoring was added to prevent recurrence |
| `lessons` | What the team learned — institutional memory |

### When it grows
- Within 48 hours of incident resolution, Ops + the developer who fixed it write the entry
- When the regression test merges, `regression_test` field is linked
- When canary criteria are updated, `canary_criteria_added` field is linked

### How it's consumed
- Step 2 (Impact analysis): "what has gone wrong in this domain before?"
- Step 15 (Rollout plan): past incidents shape the canary go/no-go criteria
- Onboarding: new team members learn what broke and why, grounded in real incidents

See `ai/templates/incident-registry-template.yaml` for the full format with examples.

## QA and Ops Integration

| Role | Contributes | When | Blocking? |
|------|------------|------|-----------|
| **QA** | Test cases, acceptance criteria, edge cases | Design PR review + TDD review | No — developer proceeds if unavailable |
| **Ops** | Incident entries, canary criteria, go/no-go thresholds | Post-incident + rollout plan review | No — developer self-serves from registry |

The registries make QA and Ops expertise available even when the individuals are not — because their past inputs are captured in queryable form.
