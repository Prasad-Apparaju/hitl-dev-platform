# ADR-0001: Adopt HITL AI-Driven Development

| | |
|---|---|
| **Status** | Accepted |
| **Date** | [fill in: project start date] |
| **Deciders** | [fill in: tech lead, architect, stakeholders] |
| **Supersedes** | — |
| **Related** | ADR-0002 (documentation-first), ADR-0004 (change tier policy) |

---

## 1. Context

This project uses AI (Claude Code) heavily for software development. Without a structured process, AI-assisted development leads to:

- Output that drifts from intent as context grows across sessions
- Tests written after code, reducing their value as design feedback
- Undocumented decisions that block future AI sessions from understanding why things are the way they are
- No clear human approval gates — hard to know what the AI changed and why

## 2. Decision

Adopt the **HITL AI-Driven Development** process for all Tier 1+ changes:

- **Document-first**: HLD and LLD are written and architect-approved before any code is generated
- **TDD-as-design**: tests are written from the LLD before implementation, not after
- **32-step workflow**: structured delivery from issue → design → tests → code → review → ship → monitor
- **Human approval gates**: architect, QA, and TA review at defined checkpoints; AI does not self-approve
- **Change tiers**: scope of process scales with risk (see ADR-0004)

Tooling: Claude Code with the HITL plugin. Entry point for every change: `/hitl:dev-practices`.

## 3. Alternatives Considered

### Alt 1: Ad-hoc AI use (no structured process)
Each developer prompts Claude freely without shared conventions. Rejected because: output quality degrades rapidly on non-trivial changes across sessions; no shared process means no shared mental model; hard to audit what the AI changed and why.

### Alt 2: Traditional development (no AI)
No AI involvement. Rejected because: the team's delivery goals require AI assistance; HITL was chosen to capture AI productivity gains while managing the quality risks.

### Alt 3: AI-only with no human gates
Full AI autonomy, AI reviews its own output. Rejected because: current models reliably miss cross-cutting concerns, security implications, and non-obvious regressions; human judgment at key gates is the core risk mitigation.

## 4. Consequences

### Positive
- AI output stays aligned with approved design documents across sessions
- Tests provide real design feedback (written before implementation)
- Every decision is documented — future sessions and team members have context
- Change risk is managed by tier — trivial changes are not over-processed

### Negative
- Initial ramp is slower: requires HLD/LLD before code
- Team must maintain design documents as the system evolves
- Learning curve for the 32-step workflow (~2–4 weeks)

### Neutral
- Velocity shifts from "fast first, fix later" to "slower start, fewer fixes later"

## 5. Implementation Notes

| What | Where |
|---|---|
| Plugin | `claude plugin install hitl@hitl` |
| Project setup | `/hitl:dev-start-from-prd` (or brownfield/migration variant) |
| Hook wiring | `.hitl/hooks/` and `.claude/settings.json` — created by Step 0 |
| Change entry point | GitHub issue + `/hitl:dev-practices` |

## 6. Open Questions

1. [fill in: any team-specific concerns about adopting this process]

## 7. Status

**Accepted.** Adopted at project initialization.

## ROI Estimate

**Value dimension:** Quality / Risk / Velocity
**Expected outcome:** [fill in — e.g., "Reduce production incidents by X% within 6 months; maintain AI-assisted velocity after 4-week ramp"]
**Baseline metric:** [fill in: current incident rate or rework time per change]
**Expected cost:** Ramp: ~2–4 weeks | Ongoing: ~10–15% overhead per change from documentation
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]
**Decision if not realized:** Re-evaluate tier thresholds; consider restricting HITL to Tier 2+ only

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
