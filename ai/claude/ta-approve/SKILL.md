---
description: "TA gate approval — advance a design-phase gate from awaiting-* to *-approved. The only command that can unlock the next phase. Run after reviewing the artifact the architect produced at the current gate."
argument-hint: ""
disable-model-invocation: true
---

# TA Approve — Gate Advancement

**Who runs this:** Technical Advisor only. This command is not in the architect or developer skill inventories. The AI cannot call it on its own behalf.

**Refusal rule:** If `.hitl/current-change.yaml` does not exist AND `.hitl/design-system.yaml` does not exist, stop: "No active HITL context found. This command requires either `.hitl/current-change.yaml` (for a feature change) or `.hitl/design-system.yaml` (for initial system design) to exist."

---

## Step 1 — Detect context and current gate

Read whichever file exists:
- `.hitl/current-change.yaml` — for feature/change design gates
- `.hitl/design-system.yaml` — for initial system design gates (project inception)

If both exist, prefer `.hitl/current-change.yaml` unless `$ARGUMENTS` contains "system" or "design-system".

Extract the `status` field. Determine what gate is pending:

| Status | Gate | Artifact to review |
|--------|------|--------------------|
| `awaiting-scope-approval` | Scope | Impact summary in previous session output; `source_artifacts.hld: pending` in context file |
| `awaiting-hld-approval` | HLD | `source_artifacts.hld` path in context file |
| `awaiting-lld-approval` | LLD | `source_artifacts.lld` path(s) in context file |
| `awaiting-packet-approval` | Decision packet | `source_artifacts.decision_packet` path(s) in context file |
| `awaiting-requirements` | Requirements (design-system) | PRD extraction in previous session output |
| `awaiting-domains` | Domains (design-system) | Domain decomposition in previous session output |
| `awaiting-manifest` | Manifest + ADRs (design-system) | `docs/system-manifest.yaml` and `docs/02-design/technical/adrs/` |
| `awaiting-hld-approval` | HLD (design-system) | `docs/02-design/technical/hld/` |
| `awaiting-lld-approval` | LLD (design-system) | `docs/02-design/technical/lld/` |
| `awaiting-delivery-plan` | Delivery plan (design-system) | `docs/decisions/` |

If status is NOT one of the `awaiting-*` values above, stop:

> "No gate is pending. Current status: `[status]`.
>
> This command advances gates — it only acts when the architect has reached a checkpoint and is waiting for TA review. If you expected a gate to be pending, check `.hitl/current-change.yaml` or `.hitl/design-system.yaml` directly."

If status is `blocked`, stop:

> "This change is currently blocked. Finding: [blocker.finding] (gate: [blocker.gate]).
>
> The architect must rework the [blocker.gate] artifact and re-submit before this command can advance the gate. Ask the architect to re-run `/hitl:architect-design-feature` (or `/hitl:architect-design-system`) to address the finding."

---

## Step 2 — Surface the artifact

Load and display the artifact path(s) from the context file. Output:

```
Gate pending: [gate name]
Artifact:     [path or description]
Change:       [change_id] — [title if available]
```

If the artifact path points to a file that does not exist on disk, stop:

> "Artifact not found at `[path]`. The architect may not have completed this phase yet, or the path in the context file is wrong. Ask the architect to re-run the design skill and confirm the artifact was written."

Remind the TA:
> "If you are on a different machine than the architect, run `git pull` now to ensure you have the latest artifacts before reviewing."

---

## Step 3 — Present the gate checklist

Present the checklist for the current gate. Each item requires a yes/no answer. Ask all items as a numbered list — do not proceed until every item is answered.

### Scope gate checklist (`awaiting-scope-approval`)
1. Are the affected domains correct — neither over-counted (scope creep) nor under-counted (hidden blast radius)?
2. Is the tier assignment correct for this change?
3. Is the ROI trigger noted if effort > 1 day?
4. Are any backwards-incompatible changes flagged with a compatibility strategy?

### HLD gate checklist (`awaiting-hld-approval`)
1. Are the component boundaries correct — does each component have a clear single responsibility?
2. Is the security model correct for this feature (auth, data isolation, secrets handling)?
3. Are design decisions that need ADRs flagged — no undocumented tradeoffs embedded in the diagram?
4. Is there no implementation bias — does the HLD describe *what*, not *how*?

### LLD gate checklist (`awaiting-lld-approval`)
1. Are method signatures precise enough that a developer could generate tests directly from the LLD without reading other docs?
2. Are preconditions and error modes complete for every public method?
3. Does the LLD correctly reflect the decisions in the approved HLD?
4. Is the slice demo answer concrete — does each slice describe what the PM will see and verify in the running app?

### Decision packet gate checklist (`awaiting-packet-approval`)
1. Does each packet cover exactly one manifest domain (no cross-domain scope)?
2. Is the LLD path in the packet correct and the file present on disk?
3. Is the test plan complete enough for a developer to start the TDD cycle without clarification?
4. Is the rollout risk level correct for this change?
5. Has PM confirmed the acceptance criteria and scope (product approval)?

### Requirements gate checklist — design-system (`awaiting-requirements`)
1. Are the core use cases correct and complete (the 3–5 workflows that matter most)?
2. Are NFRs specific enough to drive architecture decisions (performance targets, availability, compliance)?
3. Are all external integrations listed?
4. Are tech stack constraints captured or flagged as open decisions?

### Domain decomposition gate checklist — design-system (`awaiting-domains`)
1. Is data ownership unambiguous — each domain owns its data with no overlap?
2. Are there any circular dependencies that indicate a boundary is in the wrong place?
3. Are domains right-sized — none doing too many unrelated things, none always changed together?
4. Would a single developer be able to implement one domain without understanding the internals of the others?

### Manifest + ADRs gate checklist — design-system (`awaiting-manifest`)
1. Are facade APIs and boundary entities approximately correct (DRAFT is acceptable — marking matters)?
2. Do domain dependencies match the interaction matrix from domain decomposition?
3. Are all foundational ADRs resolved — no open decisions remaining on: language/framework, data storage, auth, API style, deployment model?

### Delivery plan gate checklist — design-system (`awaiting-delivery-plan`)
1. Does every slice have a concrete PM demo check — something visible or measurable at the end of that slice?
2. Does the sequencing match the dependencies from the interaction matrix?
3. Is every slice 2–5 days in scope (none too large for one developer)?

---

## Step 4 — Collect TA answers

For each checklist item, record the TA's answer (yes / no / with-caveat).

If any item is answered **no** or flagged as a problem, go to **Step 5 — Rejection**.

If all items are answered **yes** (or yes-with-caveat where the caveat is noted), go to **Step 6 — Approval**.

---

## Step 5 — Rejection

Ask the TA: "What specifically needs to change? Be concrete enough for the architect to act on it."

Record the finding. Then update the context file:

```yaml
status: blocked
blocker:
  gate: [scope|hld|lld|packet|requirements|domains|manifest|delivery-plan]
  finding: "[TA's specific finding]"
  rejected_at: "[ISO 8601 timestamp]"
```

Post a GitHub issue comment (if change_id is present and in GH-N format):
```bash
ISSUE_NUM="${CHANGE_ID#GH-}"
gh issue comment "$ISSUE_NUM" --body "## ❌ Gate Rejected — [gate name]

**Finding:** [TA's finding]

The architect must rework the [gate name] artifact and re-submit.
Re-run \`/hitl:architect-design-feature\` to address the finding and reach this gate again."
```

Output:
```
Gate REJECTED — status set to 'blocked'.
Finding recorded in .hitl/current-change.yaml under 'blocker'.

The architect will see the rejection and finding when they next run the design skill.
```

If on a different machine than the architect: "Push this change so the architect can pull and see the rejection: `git add .hitl/ && git commit -m 'hitl: gate rejected — [gate name]' && git push`"

Stop here.

---

## Step 6 — Approval

Determine the next status from the transition table:

| Current status | Next status |
|----------------|-------------|
| `awaiting-scope-approval` | `scope-approved` |
| `awaiting-hld-approval` | `hld-approved` |
| `awaiting-lld-approval` | `lld-approved` |
| `awaiting-packet-approval` | `implementation-approved` |
| `awaiting-requirements` | `requirements-confirmed` |
| `awaiting-domains` | `domains-confirmed` |
| `awaiting-manifest` | `manifest-confirmed` |
| `awaiting-delivery-plan` | `complete` |

Update the context file:
1. Set `status` to the next value from the table above
2. For design-feature gates, also update `approvals`:
   - `awaiting-scope-approval` → set `approvals.architecture: pending` (still pending — full architecture review at packet gate)
   - `awaiting-packet-approval` → set `approvals.architecture: approved` and `approvals.product: approved`
3. Clear any previous `blocker` field (set to null or remove)

Post a GitHub issue comment (if change_id is present and in GH-N format).

**If the approved gate is `awaiting-packet-approval`** (the final design gate — developers start now):
```bash
ISSUE_NUM="${CHANGE_ID#GH-}"
gh issue comment "$ISSUE_NUM" \
  --body "## ✅ Ready for Development

Architecture approved. If this issue is assigned to you, you can begin now.

**Decision packet:** \`docs/decisions/issue-${ISSUE_NUM}.yaml\` (or slice variant)
**Your domain:** [domain from packet]
**LLD:** [lld path from packet]

Open Claude Code in the repo and run:
\`\`\`
/hitl:tdd

I have been assigned GitHub issue #${ISSUE_NUM}. Read the decision packet at
docs/decisions/issue-${ISSUE_NUM}.yaml and tell me what I am building,
what domain I am in, and what the test plan requires me to cover.
\`\`\`"
```

**For all other gates** (scope, HLD, LLD — architect continues):
```bash
ISSUE_NUM="${CHANGE_ID#GH-}"
gh issue comment "$ISSUE_NUM" \
  --body "## ✅ Gate Approved — [gate name]

TA has reviewed and approved the [gate name] artifact.

**Status:** \`[next-status]\`
**Next step:** Architect re-runs \`/hitl:architect-design-feature\` to continue to the next phase."
```

Output:
```
Gate APPROVED — status advanced to '[next-status]'.
```

If the approved gate was `awaiting-packet-approval`:
```
Developer can now begin. The GitHub issue has their starting instructions.
```

Otherwise:
```
Next step: Architect re-runs /hitl:architect-design-feature (or /hitl:architect-design-system)
to continue to the next phase.
```

If on a different machine: "Push this change so the next person can pull and continue: `git add .hitl/ && git commit -m 'hitl: [gate name] approved' && git push`"
