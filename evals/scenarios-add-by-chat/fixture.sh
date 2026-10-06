#!/usr/bin/env bash
set -euo pipefail
git init -q .
mkdir -p .hitl docs/01-product docs/03-engineering/testing/scenarios
cat > .hitl/current-change.yaml <<'YAML'
schema_version: "2.0"
hitl_version: "2.17.0"
change_id: GH-123
tier: 2
status: implementation-approved
workflow: { id: development, version: "2.17.0", total: 31, steps: [] }
tests:
  scenarios_file: docs/03-engineering/testing/scenarios/GH-123.md
  scenario_review: { status: pending }
YAML
cat > docs/01-product/prd.md <<'MD'
# PRD

## FR-1 Discount codes at checkout
Shoppers can enter a discount code at checkout and see the new total before paying.
- AC-1: a valid code lowers the total and shows the saving
- AC-2: a blank or unknown code leaves the total unchanged and says why
MD
cat > docs/03-engineering/testing/scenarios/GH-123.md <<'MD'
# Test scenarios: GH-123 Discount codes at checkout

| | |
|---|---|
| Change | GH-123 |
| Serves | FR-1 |
| Owner | QA |
| Review | PM: pending |
| Written | by HITL at the test plan step, 2026-10-04 |

## What this change does

Shoppers can enter a discount code at checkout and see the new total before paying. It matters because support gets a ticket a day about codes that did nothing. Acceptance criteria: FR-1 in the PRD.

## Scenarios

### SC-GH-123-01: A blank discount code leaves the total unchanged
- Kind: acceptance
- Priority: strongly-recommended
- Serves: FR-1 AC-2
- Added by: qa
- Given: a cart with two items totalling 40.00
- When: the shopper submits an empty code
- Then: the total still shows 40.00 and the field says a code is needed
- Test: none yet
MD
git add -A && git -c user.email=e@x -c user.name=eval commit -qm init
