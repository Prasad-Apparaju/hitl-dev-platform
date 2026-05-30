---
description: Orchestrate the architect's design journey for a change — steps 3 through 9. Covers impact analysis, HLD and LLD generation with approval gates, slice decomposition, test case planning, and decision packet assembly. Produces decision packets ready to hand to developers. Do not invoke spontaneously; requires a GitHub issue.
argument-hint: "[issue number or feature description]"
disable-model-invocation: true
---

# Design Feature — Architect Workflow (Steps 3–9)

**Input:** $ARGUMENTS (GitHub issue number and/or feature description)

**Refusal rule:** If no GitHub issue number is provided or discoverable, stop and say: "No GitHub issue found. Create one first with `gh issue create`, then re-run with the issue number."

---

## Startup — Status Router

Before doing anything else, check `.hitl/current-change.yaml`:

```bash
[ -f .hitl/current-change.yaml ] && grep "^status:" .hitl/current-change.yaml || echo "status: not-found"
```

Route based on the current status:

| Status | Action |
|--------|--------|
| File not found | Proceed normally — run from Phase 1 |
| `planning` | Proceed normally — run from Phase 1 |
| `awaiting-scope-approval` | Output the gate-pending message below and STOP |
| `scope-approved` | Skip to Phase 3 (HLD) |
| `awaiting-hld-approval` | Output the gate-pending message below and STOP |
| `hld-approved` | Skip to Phase 5 (LLD) |
| `awaiting-lld-approval` | Output the gate-pending message below and STOP |
| `lld-approved` | Skip to Phase 10 (Decision Packet) |
| `awaiting-packet-approval` | Output the gate-pending message below and STOP |
| `implementation-approved` | Output: "Design is complete. Decision packets are ready — hand them to developers to begin `/hitl:dev-tdd`." and STOP |
| `blocked` | Output the blocked message below and STOP |

**Gate-pending message** (for any `awaiting-*` status):
```
Gate pending — waiting for TA approval.

Status:   [current status]
Change:   [change_id]

The TA must run /hitl:ta-approve to review the current artifact and advance this gate.
Once approved, re-run this command to continue to the next phase.
```

**Blocked message** (for `blocked` status):
```
This change is blocked — a gate was rejected by the TA.

Gate:     [blocker.gate]
Finding:  [blocker.finding]

Address the finding above, then re-run this command. The skill will resume
at the rejected phase so you can rework the artifact.
```

For `blocked` status: after showing the blocked message, ask the architect: "Are you ready to rework the [blocker.gate] artifact? Say 'yes' to resume." On confirmation, clear the `blocked` status and route to the appropriate phase to re-do that work.

---

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

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
3. **Are NFRs relevant to this change stated?** If the change affects throughput, latency, or availability, are the targets in the issue or findable in the requirements source? If not, ask — see `shared/challenge-stance.md` for the full NFR checklist.
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

Use the tier definitions from `ai/claude/dev-practices/SKILL.md`. State the tier with justification.

**Challenge the tier before accepting it:**
- Cross-domain or multi-service changes are Tier 3 even when described as simple
- If the change touches more than one domain AND those domains have ordering dependencies, confirm whether this should be split into sequential changes
- If the change is too large for one slice, say so and wait for architect confirmation before proceeding

### 1f. Estimate effort and token cost

Estimate implementation effort (in days) based on the number of affected domains, facade API changes, and IaC scope. This determines whether step 4 (ROI) is required.

For token cost estimation, use the phase-level formula from `ai/claude/dev-practices/roi-estimation.md`.

### 1g. Initialize `.hitl/current-change.yaml`

Create or update using the schema at `docs/changes/change-context.schema.yaml`. See `docs/changes/GH-000-example.yaml` for a filled-in example.

Set from this impact analysis:
- `change_id`: `GH-<issue-number>`
- `tier`: from Step 1e
- `status`: `planning`
- `source_artifacts.issue`: GitHub issue URL; set `hld` and `lld` to `pending`
- `manifest.domain`: primary affected domain
- `allowed_paths`: source paths for all affected domains
- `approvals.product` and `approvals.architecture`: both `pending`
- `token_tracking.estimated`: populate with the cost estimate from Step 1f

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

Update `.hitl/current-change.yaml`: set `status: awaiting-scope-approval`.

Post a GitHub issue comment:
```bash
gh issue comment <issue-number> \
  --body "## ⏸ Gate: Scope Review

Impact analysis complete. Awaiting TA approval before HLD generation begins.

**Tier:** [N] | **Effort:** [N days] | **Domains:** [list]
**Backwards compat:** [compatible / incompatible — details]

Run \`/hitl:ta-approve\` to review and advance this gate."
```

Output:
```
Gate 1 reached — status set to 'awaiting-scope-approval'.

The TA must run /hitl:ta-approve to confirm scope before HLD generation begins.
Re-run /hitl:architect-design-feature after TA approval to continue.
```

**STOP. Do not generate any further content. This session ends here.**

---

## Phase 2 — ROI Trigger Check (Step 4)

If effort estimate exceeds 1 day:

Record the ROI section in `.hitl/current-change.yaml` under `roi_estimate` using the template in `ai/claude/dev-practices/roi-estimation.md`. Fill in:
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

Update `.hitl/current-change.yaml`: set `status: awaiting-hld-approval`.

Post a GitHub issue comment:
```bash
gh issue comment <issue-number> \
  --body "## ⏸ Gate: HLD Review

High-Level Design is ready for TA review.

**HLD:** \`docs/02-design/technical/hld/<feature-name>.md\`

Run \`/hitl:ta-approve\` to review and advance this gate. The TA checklist covers:
component boundaries, security model, ADR candidates, and implementation bias."
```

Output:
```
Gate 2 reached — status set to 'awaiting-hld-approval'.

The TA must run /hitl:ta-approve to review the HLD before LLD generation begins.
Re-run /hitl:architect-design-feature after TA approval to continue.
```

**STOP. Do not generate ADRs or LLDs. This session ends here.**

For Tier 0–1: skip this phase.

---

## Phase 4 — ADR Capture (Step 5, Part 2)

After HLD approval:

1. From the approved HLD, identify every design decision — framework choice, pattern selection, tradeoff made, constraint accepted.

2. For each decision that is not already documented in an existing ADR, create a stub at `docs/02-design/technical/adrs/<decision-slug>.md` using `shared/templates/adr-template.md`. Mark status as "DRAFT — architect to complete rationale."

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

3. After each LLD is written, update `source_artifacts.lld` in `.hitl/current-change.yaml`.

4. After ALL domain LLDs are written, update `.hitl/current-change.yaml`: set `status: awaiting-lld-approval`.

Post a GitHub issue comment:
```bash
gh issue comment <issue-number> \
  --body "## ⏸ Gate: LLD Review

Low-Level Designs are ready for TA review.

**Domains:** <domain list>
**LLD(s):** \`docs/02-design/technical/lld/...\`

Run \`/hitl:ta-approve\` to review and advance this gate. The TA checklist covers:
method signature precision, error modes completeness, HLD alignment, and slice demo answers."
```

Output:
```
Gate 3 reached — status set to 'awaiting-lld-approval'.

The TA must run /hitl:ta-approve to review the LLD(s) before slice decomposition begins.
Re-run /hitl:architect-design-feature after TA approval to continue.
```

**STOP. Do not begin slice decomposition. This session ends here.**

---

## Phase 6 — IaC Planning (Step 6)

If Phase 1 identified IaC changes:

For each affected infrastructure artifact, specify:
- File path (Terraform module, Kubernetes manifest, migration file, config)
- What changes (resource added/modified/removed, migration direction, config key)
- Whether the change is reversible

**Config and secrets externalization (required):**

For any new config or secret introduced by this change:
- Config values must be externalized as environment variables or a config service reference — not hardcoded in source.
- Secrets must be declared as vault references — never as literal values in IaC, migrations, or deploy scripts.

For each new secret, record the vault path and secret manager. If a secret has no vault path assigned, stop: "Secret `<name>` has no vault path. Assign one before proceeding."

Record the IaC plan in `.hitl/current-change.yaml`:
```yaml
iac_plan:
  - path: <file>
    change: <description>
    reversible: true|false
secrets:
  - name: <SECRET_NAME>
    vault_path: <path>
    manager: <aws-secrets-manager|hashicorp-vault|gcp-secret-manager|azure-key-vault|ssm>
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

If yes: create a stub at `docs/03-engineering/training/<capability>.md` using `shared/templates/training-plan-template.md`. Link to the relevant LLDs and ADRs. Mark sections as "DRAFT — architect to complete."

If no: state the reason explicitly (e.g., "No training plan required — this extends an existing pattern.").

---

## Phase 10 — Decision Packet Assembly (Step 9)

For each confirmed slice, create `docs/decisions/issue-<N>-slice-<M>.yaml` (or `docs/decisions/issue-<N>.yaml` for a single-slice change). Create the `docs/decisions/` directory first if it does not exist.

Use **exactly** the schema below — do not add, remove, or rename fields. Populate every field from the work completed in prior phases:

```yaml
# docs/decisions/issue-<N>.yaml  (or issue-<N>-slice-<M>.yaml for multi-slice)
issue: <N>                        # GitHub issue number (Phase 1)
slice: null                       # slice number M, or null for single-slice (Phase 7)
title: "<slice description>"      # from Phase 7
change_type: feature              # feature | bugfix | refactor | infrastructure
risk_level: medium                # low | medium | high | critical — derived from tier

domains:
  - <domain-name>                 # exactly one domain per packet (Phase 7)

source_docs:
  prd: "<path>#<requirement-ref>" # PRD path from Phase 1
  hld:
    - "<path>"                    # HLD path from Phase 3
  lld:
    - "<path>"                    # LLD path for this domain from Phase 5
  adr:
    - "<path>"                    # ADR paths from Phase 4 (empty list if none)

tests:
  plan: "<summary>"               # test plan summary from Phase 8
  new_tests:
    - "<tests/file.py::test_name>"  # full list from Phase 8
  registry_updated: false         # developer sets true during /hitl:dev-tdd

incidents:
  checked: true
  relevant: null                  # incident ID from Phase 8, or null

rollout:
  risk: medium                    # same as risk_level
  strategy: "canary 5% → 25% → 100%, 1h soak each"  # placeholder; ops refines
  go_no_go: "<measurable criteria from LLD or incident history>"

roi:
  required: false                 # true if effort > 1 day (Phase 1)
  estimate: null                  # roi_estimate from .hitl/current-change.yaml, or null

impact_brief:
  pm_mental_model: "<one sentence: what changes for the PM>"
  risk_assessment: "<one sentence: main risk>"

approvals:
  architecture: pending           # architect sets to approved after review
```

Field mapping from prior phases:

| Field | Source |
|---|---|
| `issue` | GitHub issue number from Phase 1 |
| `slice` | Slice number M; `null` if single-slice |
| `title` | Slice description from Phase 7 |
| `risk_level` | tier 0–1 → low, 2 → medium, 3–4 → high/critical |
| `domains` | Exactly one domain — the domain for this slice from Phase 7 |
| `source_docs.lld` | LLD path for this domain from Phase 5 |
| `source_docs.adr` | ADR paths from Phase 4 that apply to this slice |
| `tests.plan` | Test plan summary for this slice from Phase 8 |
| `tests.new_tests` | Test list from Phase 8 |
| `incidents.relevant` | Incident ID found in Phase 8, or `null` |
| `rollout.go_no_go` | Criteria from LLD or incident history (Phase 8) |
| `roi.required` | `true` if effort > 1 day (Phase 1) |
| `roi.estimate` | `roi_estimate` from `.hitl/current-change.yaml`, or `null` |

Update `.hitl/current-change.yaml`:
- Add `source_artifacts.decision_packet` paths for all packets
- Set `status: design-review`
- Set `approvals.architecture: pending`

After all packets are assembled, update `.hitl/current-change.yaml`: set `status: awaiting-packet-approval`.

Post a GitHub issue comment:
```bash
gh issue comment <issue-number> \
  --body "## ⏸ Gate: Decision Packet Review

Decision packet(s) assembled and awaiting TA + PM approval.

**Slices:** <slice plan from Phase 7>
**Decision packet(s):** \`docs/decisions/issue-<N>...\`
**Estimated effort:** <N days>
**Rollout risk:** <level>

Run \`/hitl:ta-approve\` to review and advance this gate. The TA checklist covers:
domain scope, LLD path, test plan completeness, rollout risk, and PM sign-off."
```

Output:
```
Gate 4 reached — status set to 'awaiting-packet-approval'.

The TA (and PM) must run /hitl:ta-approve to approve the decision packet(s).
Once approved, status will advance to 'implementation-approved' and developers
can begin /hitl:dev-tdd.

This session ends here.
```

**STOP. Do not set implementation-approved. This session ends here.**

---

## Output Summary

Read `output-summary.md` in this skill's directory and present the completion summary populated with the actual values from this session.

