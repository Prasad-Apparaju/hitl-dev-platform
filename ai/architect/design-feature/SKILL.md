---
name: architect/design-feature
description: Orchestrate the architect's design journey for a change — steps 3 through 9. Covers impact analysis, HLD and LLD generation with approval gates, slice decomposition, test case planning, and decision packet assembly. Produces decision packets ready to hand to developers. Do not invoke spontaneously; requires a GitHub issue.
argument-hint: "[issue number or feature description]"
disable-model-invocation: true
---

# Design Feature — Architect Workflow (Steps 3–9)

**Input:** $ARGUMENTS (GitHub issue number and/or feature description)

**Refusal rule:** If no GitHub issue number is provided or discoverable, stop and say: "No GitHub issue found. Create one first with `gh issue create`, then re-run with the issue number."

---

## Progress Banners

Output the banner for the current phase at the start of every phase — before any questions, analysis, or content.

Format: `---` line, `**Design Feature — Phase N / 10: [Name]**`, trail, `---`.

| Phase | Name | Banner trail |
|---|---|---|
| 1 | Impact Analysis | `▶ Impact · ○ ROI · ○ HLD · ○ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 2 | ROI Check | `✅ Impact · ▶ ROI · ○ HLD · ○ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 3 | HLD | `✅ Impact · ✅ ROI · ▶ HLD · ○ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 4 | ADR Capture | `✅ Impact · ✅ ROI · ✅ HLD · ▶ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 5 | LLD | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ▶ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 6 | IaC Planning | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ▶ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 7 | Slice Decomposition | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ▶ Slices · ○ Tests · ○ Training · ○ Packet` |
| 8 | Test Case Planning | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ✅ Slices · ▶ Tests · ○ Training · ○ Packet` |
| 9 | Training Stub | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ✅ Slices · ✅ Tests · ▶ Training · ○ Packet` |
| 10 | Decision Packet | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ✅ Slices · ✅ Tests · ✅ Training · ▶ Packet` |

---

## Phase 1 — Impact Analysis and Scope (Step 3)

### 1a. Read and challenge the issue

Fetch the GitHub issue from $ARGUMENTS. Extract: title, description, any linked Figma references.

**Detect project type and locate the requirements source:**

- **Migration project** — if `docs/00-migration/migration-brief.md` exists, that file is the requirements source. It replaces `docs/01-product/prd.md`. Read it in full. The issue title should reference the migration slice being designed; the migration brief is the source of truth for acceptance criteria and NFRs. Do not look for an `FR-<ID>` pointer — migration slices reference `MR-<ID>` from the brief instead.
- **Standard project** — extract the PRD reference (`FR-<ID>`) from the issue and read `docs/01-product/prd.md` at that requirement. The issue is a pointer; the PRD is the source of truth.

Before reading the manifest or doing any analysis, challenge the issue against its requirements source:

1. **Is the problem statement specific?** If the issue says "users want X" or "improve Y" without data, ask: "What evidence supports this — support tickets, analytics, churn feedback, user research?" For migration: "What in the migration brief or external reference docs supports this slice being needed now?"
2. **Are the acceptance criteria testable?** Vague AC ("should feel fast", "user-friendly") cannot drive an LLD or tests. Ask for specific, measurable criteria before proceeding.
3. **Are NFRs relevant to this change stated?** If the change affects throughput, latency, or availability, are the targets in the issue or findable in the requirements source? If not, ask — see `ai/shared/challenge-stance.md` for the full NFR checklist.
4. **Is the proposed solution the right solution?** State the problem, then ask: "Is there a simpler approach that would solve the same problem?" If yes, name it and the tradeoff before designing the proposed solution.

If any answer is unsatisfactory, resolve it now — not after the HLD is generated.

### 1b. Read the system manifest

Prefer a graph query:
```
/graphify query "all domains and facade APIs"
/graphify query "domain: <candidate-domain> facade APIs boundary entities"
```
Fall back to reading `docs/system-manifest.yaml` directly if Graphify is unavailable.

### 1c. Check past incidents in candidate domains

```
/graphify query "past incidents affecting domain: <domain-name>"
```
Fall back to reading `docs/04-operations/incident-registry.yaml` directly.

### 1d. Identify the affected scope

From the issue and manifest, determine:
- **Affected domains** — which manifest domains must change?
- **Affected facade APIs** — which public contracts change or get added?
- **Affected boundary entities** — which shared data types change shape?
- **IaC changes** — are infrastructure, migrations, configs, or secrets required?
- **Backwards compatibility** — does any facade API or boundary entity change break existing callers?

If backwards-incompatible changes are identified, flag them explicitly. Do not proceed without a compatibility strategy.

### 1e. Determine the tier

Use the tier definitions from `ai/dev-practices/SKILL.md`. State the tier with justification.

**Challenge the tier before accepting it:**
- Cross-domain or multi-service changes are Tier 3 even when described as simple
- If the change touches more than one domain AND those domains have ordering dependencies, confirm whether this should be split into sequential changes
- If the change is too large for one slice, say so and wait for architect confirmation before proceeding

### 1f. Estimate effort and token cost

Estimate implementation effort (in days) based on the number of affected domains, facade API changes, and IaC scope. This determines whether step 4 (ROI) is required.

For token cost estimation, use the phase-level formula from `ai/dev-practices/roi-estimation.md`.

### 1g. Initialize `.hitl/current-change.yaml`

Create or update:

```yaml
change_id: GH-<issue-number>
tier: <0–4>
status: planning
source_artifacts:
  issue: <url>
  hld: pending
  lld: pending
manifest:
  path: docs/system-manifest.yaml
  domain: <primary-domain>
allowed_paths:
  - <source paths for all affected domains>
required_evidence: []
approvals:
  product: pending
  architecture: pending
token_tracking:
  estimated:
    total_cost_usd: <estimate>
    by_phase:
      design: <estimate>
      build: <estimate>
      verify: <estimate>
      assess: <estimate>
```

### 1h. Gate — architect confirms scope

Present the impact summary:

```
## Impact Summary — GH-<N>: [title]
Tier: N | Effort estimate: N days

Affected domains:     [list]
Facade API changes:   [list or "none"]
Boundary entity changes: [list or "none"]
IaC changes:          [list or "none"]
Backwards compat:     [compatible / incompatible — details]
Incident history:     [relevant incidents or "none found"]
ROI required:         [yes — effort > 1 day / no]
```

**STOP. Ask the architect:**
- "Are the domain boundaries correct?"
- "Any scope I missed or over-counted?"
- "Confirm tier [N]?"

Do not proceed until the architect confirms.

---

## Phase 2 — ROI Trigger Check (Step 4)

If effort estimate exceeds 1 day:

Record the ROI section in `.hitl/current-change.yaml` under `roi_estimate` using the template in `ai/dev-practices/roi-estimation.md`. Fill in:
- Value dimension
- Expected outcome (specific, falsifiable, with timeframe)
- Baseline metric placeholder (note: architect must measure this now, not estimate it)
- Measurement plan
- 30/90-day checkpoint dates

Present the draft to the architect. Ask them to fill in the baseline metric before proceeding — it cannot be estimated after the fact.

Post a pointer comment on the GitHub issue (not the content — the content lives in the context file and will be included in the decision packet at Phase 10):
```bash
gh issue comment <issue-number> --body "ROI estimate required — filed in decision packet (effort > 1 day)."
```

If effort estimate is ≤ 1 day, state: "ROI estimate not required — change is <1 day."

---

## Phase 3 — HLD (Step 5, Part 1)

For Tier 2 and above:

1. Generate the HLD at `docs/02-design/technical/hld/<feature-name>.md` following the instructions in Phase 1 of the `generate-docs` skill. The HLD must include:
   - Executive summary
   - System architecture diagram (Mermaid `graph TB` or `graph LR`)
   - Component overview table
   - Data flow diagrams (Mermaid `sequenceDiagram`)
   - Integration points with affected facade APIs
   - Security considerations
   - Any design decisions being made (flag each as a candidate ADR)

2. Update `docs/02-design/technical/hld/index.md`.

3. Update `source_artifacts.hld` in `.hitl/current-change.yaml`.

**STOP. Ask the architect:**
> "HLD is ready for your review. Specifically check:
> 1. Are the component boundaries right?
> 2. Are there design decisions in here that need an ADR?
> 3. Is the security model correct?
>
> Say **"HLD approved"** to proceed to ADRs and LLD."

Do not generate LLDs until the architect explicitly approves the HLD.

After the architect says "HLD approved", post a comment on the GitHub issue from Step 1:
```bash
gh issue comment <issue-number> \
  --body "## ✅ HLD Approved

High-Level Design reviewed and approved by architect.

**HLD:** \`docs/02-design/technical/hld/<feature-name>.md\`

Proceeding to ADRs and LLD generation."
```

For Tier 0–1: skip this phase.

---

## Phase 4 — ADR Capture (Step 5, Part 2)

After HLD approval:

1. From the approved HLD, identify every design decision — framework choice, pattern selection, tradeoff made, constraint accepted.

2. For each decision that is not already documented in an existing ADR, create a stub at `docs/02-design/technical/adrs/<decision-slug>.md` using `ai/templates/adr-template.md`. Mark status as "DRAFT — architect to complete rationale."

3. Ask the architect:
   > "I've created stubs for [N] decisions I found in the HLD. Are there decisions being made here that aren't visible in the design — things the team discussed, constraints from legal or ops, or choices you ruled out?"

4. Add any architect-supplied decisions as additional ADR stubs.

5. Update `source_artifacts.adr` in `.hitl/current-change.yaml` with the ADR paths.

---

## Phase 5 — LLD per Domain (Step 5, Part 3)

For each affected domain identified in Phase 1:

1. Generate the LLD at `docs/02-design/technical/lld/<domain>/<component>.md` following the instructions in Phase 2 of the `generate-docs` skill. Each LLD must include:
   - Component purpose
   - Mermaid class diagram
   - Method signatures with parameters, return types, and preconditions
   - Sequence diagrams for non-trivial flows
   - Facade API surface that other domains call
   - Error modes and their handling

2. Update `docs/02-design/technical/lld/index.md`.

3. For each LLD, ask the architect:
   > "LLD for [domain] is ready. Before approving, check:
   > 1. Are the method signatures precise enough that a developer could generate tests directly from this?
   > 2. Are the preconditions and error modes complete?
   > 3. Does this correctly reflect the decisions in the HLD?
   >
   > Say **"[domain] LLD approved"** to continue."

4. After each LLD is approved, update `source_artifacts.lld` in `.hitl/current-change.yaml`.

Do not proceed to slice decomposition until all LLDs are approved.

After all domain LLDs are approved, post a comment on the GitHub issue:
```bash
gh issue comment <issue-number> \
  --body "## ✅ LLDs Approved

Low-Level Designs reviewed and approved for all affected domains: <domain list>.

**LLD(s):** \`docs/02-design/technical/lld/...\`

Proceeding to slice decomposition and test planning."
```

---

## Phase 6 — IaC Planning (Step 6)

If Phase 1 identified IaC changes:

For each affected infrastructure artifact, specify:
- File path (Terraform module, Kubernetes manifest, migration file, config)
- What changes (resource added/modified/removed, migration direction, config key)
- Whether the change is reversible

Record the IaC plan in `.hitl/current-change.yaml` under a new `iac_plan` key:
```yaml
iac_plan:
  - path: <file>
    change: <description>
    reversible: true|false
```

If no IaC changes: state "No IaC changes identified" and continue.

---

## Phase 7 — Slice Decomposition

This is the architect's core parallelization decision.

### 7a. List the slices

Each slice must touch **exactly one manifest domain**. Present the candidate slices:

```
Proposed slice plan:
  Slice 1: domain [A] — [one-line description of what changes]
  Slice 2: domain [B] — [one-line description of what changes]
  ...
```

### 7b. Check for demoability

For each slice, answer: **"What does the PM see at the end of this slice?"**

A valid answer is one of:
- A user-visible feature or workflow step the PM can exercise in the running app
- A measurable outcome with a defined pass/fail (for infrastructure-only slices: record counts, latency comparison, error-rate delta)

If the answer is "nothing visible yet" — the slice is too narrow. Either extend it to include the user-visible layer, or merge it into an adjacent slice that completes the user-facing story.

Add a `demo:` line to each slice:
```
Slice 1: domain [A] — [description]
  Demo: PM can [specific action] and see [specific result]
```

### 7c. Check for domain independence

For each pair of slices, determine:
- Do they share any mutable state, database tables, or external API contracts?
- Does slice N depend on a schema or interface change introduced by slice M?
- Could both slices be deployed to production independently without breaking anything?

If two slices are NOT independent:
- State which ordering constraint exists
- Mark them as **sequential** (complete and merge slice M before starting slice N)
- Do not allow them to be handed to different developers concurrently

### 7d. Present the final slice plan

```
Slice plan — GH-<N>:
  Slice 1: domain [A] [PARALLEL OK]
    Developer: [to be assigned]
    LLD: docs/02-design/technical/lld/[A]/...
    Demo: PM can [specific action] and see [specific result]
  Slice 2: domain [B] [SEQUENTIAL — after Slice 1]
    Developer: [to be assigned]
    LLD: docs/02-design/technical/lld/[B]/...
    Demo: PM can [specific action] and see [specific result]
```

**STOP. Ask the architect:**
- "Does each slice's Demo answer clearly describe what the PM will see?"
- "Are these slices correctly domain-isolated?"
- "Any hidden dependencies between slices I missed?"
- "Confirm parallelism?"

Do not proceed until the architect confirms the slice plan.

---

## Phase 8 — Test Case Planning (Step 7)

For each confirmed slice:

Using the approved LLD for that domain, produce a concrete test plan:

| Action | Test name | What it covers |
|--------|-----------|----------------|
| ADD | `test_<scenario>` | [behavior from LLD] |
| UPDATE | `test_<existing>` | [what changes] |
| REMOVE | `test_<obsolete>` | [why no longer needed] |
| VERIFY (regression) | `test_<existing>` | [what must still pass] |

Also check:
```
/graphify query "past incidents affecting domain: <domain-name>"
```
Fall back to `docs/04-operations/incident-registry.yaml`. For each relevant incident, add a regression test to the plan.

Record the test plan in `.hitl/current-change.yaml` under `tests.plan` (one entry per slice).

Ask the architect: "Is the test plan complete? Anything from domain knowledge or past incidents that should be covered but isn't here?"

---

## Phase 9 — Training Plan Stub (Step 8, conditional)

Check if the change introduces any of:
- A new architectural pattern not already present in the codebase
- A new external system integration
- A new framework or primitive
- A new ML/AI technique
- A refactor that significantly changes how engineers reason about a subsystem

If yes: create a stub at `docs/03-engineering/training/<capability>.md` using `ai/templates/training-plan-template.md`. Link to the relevant LLDs and ADRs. Mark sections as "DRAFT — architect to complete."

If no: state the reason explicitly (e.g., "No training plan required — this extends an existing pattern.").

---

## Phase 10 — Decision Packet Assembly (Step 9)

For each confirmed slice, generate `docs/decisions/issue-<N>-slice-<M>.yaml` (or `docs/decisions/issue-<N>.yaml` for a single-slice change) using `ai/templates/decision-packet-template.yaml`.

Fill all fields:
```yaml
issue: <N>
title: "<slice description>"
change_type: <feature|bugfix|refactor|infrastructure>
risk_level: <low|medium|high|critical>  # derived from tier

domains:
  - <domain for this slice only>

source_docs:
  prd: "<PRD path if exists>"
  hld:
    - "<HLD path from Phase 3>"
  lld:
    - "<LLD path for this domain from Phase 5>"
  adr:
    - "<ADR paths from Phase 4 that apply to this slice>"

tests:
  plan: "<summary from Phase 8 for this slice>"
  new_tests: [<list from Phase 8>]
  registry_updated: false  # developer updates this when /tdd runs

incidents:
  checked: true
  relevant: "<incident ID or null>"

rollout:
  risk: <low|medium|high|critical>
  strategy: "<canary percentage + soak time — placeholder for ops to refine>"
  go_no_go:
    - "<criterion from LLD or incident history>"

roi:
  required: <true|false>
  estimate: "<roi_estimate from .hitl/current-change.yaml, or null>"

impact_brief:
  pm_mental_model: "<one sentence: what changes for the PM's mental model of the system>"
  risk_assessment: "<one sentence: main risk>"
```

Update `.hitl/current-change.yaml`:
- Add `source_artifacts.decision_packet` paths for all packets
- Set `status: design-review`
- Set `approvals.architecture: pending`

**STOP. For each packet, ask the architect:**
> "Decision packet for slice [M] (domain: [domain]) is ready. Check:
> 1. Is the domain scope correctly limited to one domain?
> 2. Is the LLD path correct?
> 3. Is the test plan complete enough to hand to a developer?
> 4. Is the rollout strategy risk level right?
>
> Say **"packet [M] approved"** to continue."

After all packets are approved:
- Set `approvals.architecture: approved` in `.hitl/current-change.yaml`
- Update `status: implementation-approved`

Post a comment on the GitHub issue signalling the feature is ready for development:
```bash
gh issue comment <issue-number> \
  --body "## ✅ Architecture Approved — Ready for Development

Design complete. Decision packet(s) assembled and approved by architect.

**Slices:** <slice plan from Phase 7>
**Decision packet(s):** \`docs/decisions/issue-<N>...\`
**Estimated effort:** <N days>
**Rollout risk:** <level>

Developers can begin implementation. Run \`/tdd\` with the assigned LLD."
```

---

## Output Summary

Present a completion summary:

```
┌─────────────────────────────────────────────────┐
│ DESIGN COMPLETE — GH-<N>: [title]               │
├─────────────────────────────────────────────────┤
│ Tier: N  |  Slices: M  |  Est. effort: N days   │
├─────────────────────────────────────────────────┤
│ ARTIFACTS                                       │
│  HLD:              docs/02-design/.../hld/...   │
│  LLDs:             N files                      │
│  ADRs:             N stubs (architect to fill)  │
│  Decision packets: N files                      │
│  Training stub:    [path or "not required"]     │
│  .hitl context:    implementation-approved      │
├─────────────────────────────────────────────────┤
│ SLICE HANDOFF                                   │
│  Slice 1: domain [A] → assign to developer      │
│           LLD: docs/.../lld/[A]/...             │
│           Packet: docs/decisions/issue-<N>-s1   │
│  Slice 2: domain [B] → [SEQUENTIAL after s1]    │
│           LLD: docs/.../lld/[B]/...             │
│           Packet: docs/decisions/issue-<N>-s2   │
├─────────────────────────────────────────────────┤
│ NEXT STEPS                                      │
│  1. Assign packet(s) to developer(s)            │
│  2. Each developer runs /tdd with their LLD     │
│  3. Sequential slices: merge slice 1 before     │
│     handing off slice 2                         │
└─────────────────────────────────────────────────┘
```

