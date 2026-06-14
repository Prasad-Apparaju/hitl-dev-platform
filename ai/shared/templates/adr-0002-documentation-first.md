# ADR-0002: Documentation-First Development

| | |
|---|---|
| **Status** | Accepted |
| **Date** | [fill in: project start date] |
| **Deciders** | [fill in: tech lead, architect] |
| **Supersedes** | — |
| **Related** | ADR-0001 (HITL adoption), ADR-0003 (test strategy), ADR-0004 (change tier policy) |

---

## 1. Context

AI coding assistants generate output from context: what is in the prompt and the files they can see. Without explicit design documents, AI generates code that matches local patterns but may not respect system-wide constraints, domain boundaries, or architectural intent. The result is code that works locally but causes drift at the system level — especially across multiple sessions where the original intent is no longer in context.

## 2. Decision

For all Tier 2+ changes, design documents must exist and be approved **before** any code is generated.

**Document hierarchy (required order):**

| Step | Document | Location | Approved by |
|------|----------|----------|-------------|
| 1 | GitHub issue (requirements + ACs) | GitHub | PM / stakeholder |
| 2 | HLD (component interactions, domain boundaries, data flows) | `docs/02-design/technical/hld/` | Architect |
| 3 | LLD (method signatures, data models, error modes, sequences) | `docs/02-design/technical/lld/` | Architect |
| 4 | ADR (decisions that deviate from defaults or set project patterns) | `docs/02-design/technical/adrs/` | Architect |
| 5 | Code | codebase | QA + Architect code review |

AI is not permitted to generate code for a Tier 2+ change until the LLD is architect-approved.

**Living documents:** Design docs are updated when implementation reveals a better design. Divergence is always a deliberate choice: either the code is wrong (fix it) or the doc is wrong (update it). Undocumented divergence is not acceptable.

**Exceptions:**
- Tier 0–1 changes (typos, bug fixes): standard PR only, no HLD/LLD required
- Brownfield components not yet documented: run `/hitl:dev-generate-docs` for the component before working on it; this is a one-time cost

## 3. Alternatives Considered

### Alt 1: Code-first, document later
Write code, then extract docs from it. Rejected because: "later" rarely happens under deadline pressure; AI generates more consistent output when reading an approved spec than when inferring from existing code patterns; retrofitted docs describe what was built, not why decisions were made.

### Alt 2: No formal documentation
Rely on code comments and PR descriptions. Rejected because: insufficient context for multi-session AI work; new team members and future AI sessions cannot reconstruct intent; no basis for impact analysis or regression targeting.

## 4. Consequences

### Positive
- AI stays on track across sessions — LLD is the shared, approved context
- Architectural intent is reviewable before implementation begins
- HLD/LLD provide the basis for impact analysis (`/hitl:dev-apply-change`) and test planning
- Drift is caught at doc review (cheap) rather than at code review (expensive)

### Negative
- Changes take longer to start — HLD and LLD must be written before code
- Documentation maintenance is an ongoing cost
- Team must resist the instinct to "just write the code quickly"

### Neutral
- The LLD doubles as the spec for test case planning (`/hitl:qa-plan-tests`) — no separate test spec document needed

## 5. Implementation Notes

| Tool | Purpose |
|---|---|
| `/hitl:dev-generate-docs` | Generates HLD/LLD from issue + system manifest |
| `/hitl:architect-design-system` | System-level design for new projects |
| `/hitl:architect-design-feature` | Feature-level HLD/LLD for incremental work |
| `docs/system-manifest.yaml` | Domain registry that all docs reference |

## 6. Open Questions

1. [fill in: any project-specific documentation scope or format questions]

## 7. Status

**Accepted.** Applied from project initialization.

## ROI Estimate

**Value dimension:** Quality / Velocity
**Expected outcome:** Reduced rework from AI-generated code that misses architectural intent; faster review cycles because intent is documented before implementation
**Baseline metric:** [fill in: current rework rate or re-work time per PR]
**Expected cost:** ~15–45 minutes per LLD for a bounded Tier 2 change
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]
**Decision if not realized:** Consider a lighter LLD format for Tier 2 changes; reserve full LLD for Tier 3+

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
