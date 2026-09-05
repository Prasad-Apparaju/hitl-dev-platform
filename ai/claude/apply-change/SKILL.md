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

**Refusal rule:** If no GitHub issue number is provided or discoverable in $ARGUMENTS, stop and say: "No GitHub issue found. Create one first with `gh issue create`, then re-run this skill with the issue number." (when creating one, follow `shared/issue-hygiene.md`)

---

## Challenge Stance

This skill is a design-phase skill. The challenge stance from `ai/shared/challenge-stance.md` applies throughout — challenge vague requirements, surface tradeoffs, require evidence. In particular: if the issue has vague acceptance criteria, no supporting data, or unstated NFRs relevant to the affected domain, raise them at Step 1 before doing any analysis.

---

## Steps

### Step 1: (moved — the challenge belongs to intake)

Challenging a vague ask happens at intake's restate-and-confirm, before anything is read. That is
the cheapest moment to catch a misread: a wrong sentence is easier to argue with than a wrong plan,
because a plan looks considered.

### Step 2: Identify Source Artifacts
Before any analysis, locate and confirm these exist:
- **GitHub issue** — URL or issue number
- **HLD/LLD** — path(s) that describe this area (or note they need to be created)
- **System manifest domain** — which domain in `docs/system-manifest.yaml` is affected

If the LLD does not exist for a Tier 2+ change, stop: "LLD is required before implementation. Run `/hitl:dev-generate-docs` first."

### Step 2a: (removed — the branch belongs to intake)

`start-change` creates the branch after the plan is agreed. Creating one here, before the change has
been sized, leaves a stray branch behind whenever intake is abandoned.

### Step 3: Impact analysis — what this change reaches

**This is what produces the plan.** It is not a step inside one: it always runs, it cannot be ticked
off, and when it runs there is no plan yet to put it in. Intake calls it between agreeing the
requirement and proposing the tier, and continues when the record comes back.

Read the stub at `.hitl/current-change.yaml` for the agreed requirement and definition of done.

**Which area owns this.** The workflow was already chosen at intake as a routing decision; do not
revisit it. Answer which area of the manifest owns the work. If none does, say so and ask **one**
question: is this genuinely outside the system, like a demo script or a CI config, or is the
manifest missing an area? Outside means the fast track is the locked floor and nothing else. Missing
means do not pretend it sized correctly — offer full scale or ask for the area.

**What this change reaches.** Read top-down, cheapest source first: the manifest entry, then the
design docs it points at, then source, and only where the declared picture is thin or the change
clearly goes beyond it.

The distinction that decides everything downstream is between what the *area* has and what this
*change* touches. An area having tests is not a fact about your change; your change altering
behaviour those tests cover is. Record only the second kind. Rules keyed to the first give the same
answer for every change to an area, so a one-line fix in the best-documented code would draw the
longest plan and documenting an area would tax every future change to it.

**Two findings are declared, not derived.** `dependencies_changed`: read the lockfiles and package
manifests the change touches. `security_sensitive`: ask the human **one** question — does this change
touch authentication, authorization, secrets, personal or payment data? Record the answer with
provenance `human`. A yes activates the security design review, the dependency + CVE audit and the
penetration test whatever else was found (#102); they are conditional steps and appear in no plan
otherwise. Do not infer a no from silence, and do not answer it yourself.

**Write the record** to `.hitl/impact/<change_id>.yaml`, against
`ai/shared/templates/impact-record.schema.yaml`: the findings, the provenance of each one, and what
the rules concluded. Provenance matters because a finding resting on a hand-written manifest field
must never be presented as if it came from the code — one is a claim, the other is evidence.

**Write the acceptance criteria** into the same record. This is the first moment the work is
understood well enough to say how each definition-of-done line gets proved, and it has to happen
here rather than in a plan step because any step could be dropped, and the coverage check must never
fire without its producer having run. Every criterion must be something QA can test: "returns 400
with a message naming the missing field", not "works properly". Every definition-of-done line needs
at least one criterion, or an explicit note that it is not verifiable in this change, with a reason
and a name.

**Then resurface what overlaps.** Now the change knows its area, raise unresolved skips from earlier
changes that touch it. Doing this here rather than later means past decisions inform the plan instead
of arriving after it.

Do **not** fold this change's skips into the roll-up here. They do not exist yet — they are decided
at intake's Step 4b, after this returns. Appending now would write an empty set and every skip would
raise `ROLLUP` at certification.

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

### Step 7: (removed — the change file belongs to intake)

Intake writes the stub before calling this skill, and fills in the tier and the plan after it
returns. Two writers for one file is how a tier set here and a tier set there disagree.

### Step 7a: (split — see Step 3)

Its two halves had different preconditions that used to be satisfied at the same moment. Resurfacing
needs the area, so it runs in Step 3 and informs the plan. Folding this change's skips into the
durable roll-up needs the skips, which are decided at intake's Step 4b, so it runs there.

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

## Closing this step

When this step is done, close it the way `ai/shared/next-step.md` describes: what finished, what is
next in words that say what it achieves, and how to start it. Read the next step and its `command`
from `.hitl/current-change.yaml`; `manual` and `guided` are not commands and must not be rendered as
one. Do not list the remaining steps, restate what just happened, or ask permission to continue.
