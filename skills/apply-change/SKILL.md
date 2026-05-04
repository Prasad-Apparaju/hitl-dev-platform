---
name: apply-change
description: Apply the HITL dev-practices workflow to analyze and plan a change before writing any code. Use when a developer is about to start implementing a feature, bug fix, or refactor and needs to produce an impact analysis, documentation plan, test plan, and execution order. Refuses to proceed if no GitHub issue exists.
argument-hint: "[change description or issue number]"
disable-model-invocation: true
---

# Apply Change Workflow

**Input:** $ARGUMENTS (description of the change — feature, bug fix, refactor, etc.)

**Refusal rule:** If no GitHub issue number is provided or discoverable in $ARGUMENTS, stop and say: "No GitHub issue found. Create one first with `gh issue create`, then re-run this skill with the issue number."

---

## Challenge Stance

This skill is a design-phase skill. The challenge stance from `skills/shared/challenge-stance.md` applies throughout — challenge vague requirements, surface tradeoffs, require evidence. In particular: if the issue has vague acceptance criteria, no supporting data, or unstated NFRs relevant to the affected domain, raise them at Step 1 before doing any analysis.

---

## Steps

### Step 1: Understand and Challenge the Change

- Parse the change description from $ARGUMENTS
- If unclear, ask clarifying questions before proceeding
- Identify the change tier (0–4) from the dev-practices skill tier table

**Before accepting the tier at face value, challenge it:**
- Does the scope described match the tier? Cross-domain, multi-service, or migration changes are Tier 3 even when described as simple.
- Is this change too large to implement safely in one slice? If it touches more than one domain or requires more than one LLD update, ask: "Should this be split into smaller, independently-deployable changes?" A change that can be split should be split.
- Is this a pattern we've implemented before? Search the codebase before planning — reusing an existing pattern is better than designing a new one.

State the tier with justification. If the change should be split, say so and stop until the PM or developer confirms the scope.

### Step 2: Identify Source Artifacts
Before any analysis, locate and confirm these exist:
- **GitHub issue** — URL or issue number
- **HLD/LLD** — path(s) that describe this area (or note they need to be created)
- **System manifest domain** — which domain in `docs/system-manifest.yaml` is affected

If the LLD does not exist for a Tier 2+ change, stop: "LLD is required before implementation. Run `/generate-docs` first."

### Step 3: Impact Analysis
Identify and list:
- **Affected endpoints/APIs** — what callers will see different behavior?
- **Affected services/modules** — what internal code paths change?
- **Affected infrastructure** — do manifests, configs, secrets, or migrations need updating?
- **Affected documentation** — which HLD/LLD docs describe the changed behavior?
- **Affected tests** — which existing tests cover the changed code?
- **Backwards compatibility** — if any facade API signature, boundary entity shape, or public interface is changing, which callers break? Is there a migration or versioning plan?

Search the codebase to verify each item. Don't guess — read the files.

If backwards-incompatible changes are identified, flag them explicitly in the summary and do not proceed to planning without a compatibility strategy.

### Step 4: Documentation Plan
Based on the impact analysis, identify which docs need updating:
- HLD documents that describe the affected architecture
- LLD documents that describe the affected components
- Design decision records if the change introduces a new decision
- List the specific files and what needs to change in each

### Step 5: Test Case Plan
Produce a concrete test plan:
- **New tests to add** — what new behavior or edge cases need coverage? List test names and what they verify.
- **Existing tests to update** — which specific test files/functions assert on changed behavior? What changes?
- **Obsolete tests to remove** — which tests cover deleted/replaced functionality?
- **Regression tests to run** — which existing tests must still pass to confirm no breakage?

### Step 6: IaC Review
If infrastructure is affected:
- Which Terraform/manifest/config files need changes?
- Are there new secrets, services, jobs, or migrations?
- Does the local dev config need updating?

### Step 7: Initialize HITL Context File
Create or update `.hitl/current-change.yaml` with the discovered information:

```yaml
change_id: GH-<issue-number>
tier: <0|1|2|3|4>
status: planning
source_artifacts:
  issue: <url>
  hld: <path or "pending">
  lld: <path or "pending">
manifest:
  path: docs/system-manifest.yaml
  domain: <domain-name>
allowed_paths:
  - <source paths for this domain>
required_evidence: []
approvals:
  product: pending
  architecture: pending
```

Ask the user to confirm the HITL context file before proceeding.

### Step 8: Summary
Present the full plan in this format:

```
## Change: [one-line description]
## Source: [issue URL] | Tier: [N]

### Impact
- Endpoints: [list]
- Services: [list]
- Infrastructure: [list or "none"]
- Documentation: [list of files]

### Documentation Changes
- [file]: [what to change]

### Test Plan
| Action | Test File | Test Name | What it Covers |
|--------|-----------|-----------|----------------|
| ADD    | ...       | ...       | ...            |
| UPDATE | ...       | ...       | ...            |
| REMOVE | ...       | ...       | ...            |
| VERIFY | ...       | ...       | ...            |

### IaC Changes
- [file]: [what to change] (or "No IaC changes needed")

### Execution Order
1. Update docs: [list]
2. Update IaC: [list]
3. Code changes: [list]
4. Test changes: [list]
5. Run test suite
6. Reconcile docs if needed
```

Wait for user approval before proceeding to implementation.
