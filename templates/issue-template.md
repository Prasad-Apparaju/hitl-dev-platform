---
name: Technical Change
about: Template for any technical change that follows the HITL process
labels: []
---

## Description

[What is being changed and why]

## ROI Estimate

**Value dimension:** [Quality / Reliability / Velocity / Cost / Risk / UX]

**Expected outcome:**
[Specific, falsifiable prediction with timeframe]
e.g., "Error rate drops by 50% within 30 days"

**Baseline metric (before):**
[Current measured value — not estimated]
e.g., "Current error rate = 2.3% (last 30 days from dashboard)"

**Expected cost:**
- Build: [engineering days]
- Ongoing: [per-call or per-month cost delta]
- Maintenance: [new operational burden]

**Measurement plan:**
[Which metric, which dashboard, when to check]

**Verification checkpoints:**
- [ ] 30-day check: YYYY-MM-DD — is the metric moving in the right direction?
- [ ] 90-day check: YYYY-MM-DD — has the expected magnitude been achieved?

**Decision if ROI not realized:**
[Revert / rearchitect / accept partial return]

## Impact Analysis

**Affected endpoints/APIs:** [list]
**Affected services/modules:** [list]
**Affected infrastructure:** [list or "none"]
**Affected documentation:** [list of HLD/LLD/ADR files]
**Affected tests:** [list]

## Downstream Impact Brief

- **Flows changed:** [user-visible behaviors that are different]
- **Risk assessment:** [what can break, severity x likelihood]
- **Manual verification:** [what automated tests can't cover]
- **PM mental model update:** [what assumptions changed]
- **Rollout strategy:** [Low/Medium/High/Critical → canary plan]

## Training Plan

[Link to training plan if new capability, or "Not required — no new capability"]

## Test Plan

- **New tests:** [list with what they verify]
- **Updated tests:** [list with what changed]
- **Obsolete tests:** [list with why removed]
- **Regression:** [existing tests that must still pass]
