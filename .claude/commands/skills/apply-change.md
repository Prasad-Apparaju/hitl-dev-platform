# Apply Change Workflow

Apply the dev-practices workflow to analyze and plan a change before writing code.

**Input:** $ARGUMENTS (description of the change — feature, bug fix, refactor, etc.)

---

## Steps

### Step 1: Understand the Change
- Parse the change description from $ARGUMENTS
- If unclear, ask clarifying questions before proceeding

### Step 2: Impact Analysis
Identify and list:
- **Affected endpoints/APIs** — what callers will see different behavior?
- **Affected services/modules** — what internal code paths change?
- **Affected infrastructure** — do manifests, configs, secrets, or migrations need updating?
- **Affected documentation** — which HLD/LLD docs describe the changed behavior?
- **Affected tests** — which existing tests cover the changed code?

Search the codebase to verify each item. Don't guess — read the files.

### Step 3: LLD Read and Confirmation Gate

**This step is a hard stop. Do not proceed to code until the developer confirms.**

1. Read `docs/system-manifest.yaml` — identify which domain(s) this change belongs to and which LLD file(s) govern those domains
2. Read each governing LLD file in full
3. If an LLD does not exist for the affected component → **STOP**. State: "No LLD exists for [component]. The architect must create the LLD before any code is written." Do not proceed.
4. Present the following to the developer:

```
## LLD Confirmation

**LLD read:** [path to LLD file]
**Component:** [component name]

**What I will implement (from the LLD):**
- [Class/function/interface name]: [what it does, per LLD]
- [Class/function/interface name]: [what it does, per LLD]
- ...

**What I will NOT implement (out of scope per LLD):**
- [anything adjacent but not specified]

**LLD gaps or ambiguities I found:**
- [any section that is unclear or missing — the architect must resolve these]

Do you confirm this scope? If the LLD is wrong or incomplete, stop here and update the LLD first.
```

5. **Wait for explicit developer confirmation before continuing.** A response of "yes", "confirmed", "go ahead", or equivalent is required. Silence is not confirmation.

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

### Step 7: Summary
Present the full plan in this format:

```
## Change: [one-line description]

### LLD Governing This Change
- [path to LLD]: [what it specifies for this change]

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
3. Code changes: [list] — strictly per LLD confirmed in Step 3
4. Test changes: [list]
5. Run test suite
6. Run /review-lld-adherence before opening PR
7. Reconcile docs if needed
```

Wait for user approval before proceeding to implementation.
