---
description: Apply the HITL dev-practices workflow to analyze and plan a change before writing any code. Use when a developer is about to start implementing a feature, bug fix, or refactor and needs to produce an impact analysis, documentation plan, test plan, and execution order. Refuses to proceed if no GitHub issue exists.
argument-hint: "[change description or issue number]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---


# Apply Change Workflow

**Input:** $ARGUMENTS (description of the change — feature, bug fix, refactor, etc.)

**Refusal rule:** If no GitHub issue number is provided or discoverable in $ARGUMENTS, stop and say: "No GitHub issue found. Create one first with `gh issue create`, then re-run this skill with the issue number."

---

## Challenge Stance

This skill is a design-phase skill. The challenge stance from `ai/shared/challenge-stance.md` applies throughout — challenge vague requirements, surface tradeoffs, require evidence. In particular: if the issue has vague acceptance criteria, no supporting data, or unstated NFRs relevant to the affected domain, raise them at Step 1 before doing any analysis.

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

If the LLD does not exist for a Tier 2+ change, stop: "LLD is required before implementation. Run `/hitl:dev-generate-docs` first."

### Step 2a: Create feature branch

All work for this change must happen on a dedicated branch so that `.hitl/current-change.yaml` and every commit are isolated to this issue.

```bash
# Derive branch name from issue number and title
N=<issue-number>
TITLE=$(gh issue view $N --json title -q .title \
  | tr '[:upper:]' '[:lower:]' \
  | tr -cs 'a-z0-9' '-' \
  | sed 's/^-//;s/-$//' \
  | cut -c1-50)
BRANCH="issue/${N}-${TITLE}"
CURRENT=$(git branch --show-current)
```

- If already on `$BRANCH`: say "Already on branch `$BRANCH` — continuing." and proceed.
- If branch exists but not checked out: `git checkout "$BRANCH"` and say "Switched to existing branch `$BRANCH`."
- If branch does not exist: `git checkout -b "$BRANCH"` and say "Created branch `$BRANCH`."

After switching, write `.hitl/current-change.yaml` and commit it immediately so the file is
branch-tracked from the start. If `/hitl:dev-start-change` already seeded a `development`
workflow block, just advance it (steps 1–2 `done`, step 3 `current`). Otherwise write the full
v2 block, seeded from the catalog at `ai/shared/workflows.yaml` (workflow `development`):

```yaml
schema_version: "2.0"
change_id: GH-<N>
tier: <from Step 1>
status: planning
expected_branch: "<this branch>"
workflow:
  id: development
  total: 31
  steps:
    - { n: 1,   key: issue,  label: "Issue",  phase: "Requirements", status: done }
    - { n: 2,   key: figma,  label: "Figma",  phase: "Requirements", status: done }
    - { n: 3,   key: impact, label: "Impact", phase: "Design",       status: current }
    - { n: 4,   key: roi,    label: "ROI",    phase: "Design",       status: open }
    # … remaining steps from ai/shared/workflows.yaml (carry each step's `phase` verbatim), all status: open
current_step:
  number: 3
  name: "Impact analysis"
  phase: "Design"
```

Seed the full `steps` list from the catalog rather than hand-typing it — copy each step's `phase`
verbatim from `ai/shared/workflows.yaml` so the phase-ribbon breadcrumb has data. As each step
below completes, set its `status: done` and the next step's `status: current`, and update
`current_step` to match, so the breadcrumb advances.

```bash
git add .hitl/current-change.yaml
git commit -m "chore(hitl): initialize change context for GH-<N>"
```

This commit anchors the file to this branch. Every subsequent step that updates the file will produce a new commit (or the file will be amended into the next logical commit) — whichever keeps the branch diff clean.

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
Create or update `.hitl/current-change.yaml` using the schema at `docs/changes/change-context.schema.yaml`. See `docs/changes/GH-000-example.yaml` for a filled-in example.

Set from the impact analysis above:
- `change_id`: `GH-<issue-number>`
- `tier`: from Step 3
- `status`: `planning`
- `source_artifacts.issue`: GitHub issue URL; set `hld` and `lld` to paths if known, or `"pending"`
- `manifest.domain`: affected domain name
- `allowed_paths`: source paths for this domain
- `approvals.product` and `approvals.architecture`: both `pending`
- `current_step`: `{number: 3, name: "Impact analysis", phase: "Design"}`

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
