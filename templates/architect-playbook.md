# Architect Playbook — PSR-Works V1 → V2 Migration

**Context:** You built V1. Your mission is to rebuild it as V2 (Python/FastAPI) using the PRD, existing designs, and ADRs in this repo. Prasad is the technical advisor and Dilip is the product owner. You own the day-to-day execution and team delegation.

---

## Step 1 — Sync on V1 changes and PRD scope

```
You built V1. Read the current V1 codebase in V1/ and the PRD at 
docs/01-product/prd.md. Tell me what's changed in V1 since the PRD 
was written, and whether the PRD captures everything V1 does today. 
Flag any V1 functionality missing from the PRD.
```

## Step 2 — Internalize standards and process

```
Read docs/02-design/technical/adrs/design-decisions.md, 
docs/system-manifest.yaml, and docs/playbook/process-overview.md.
Summarize the key ADRs, the 10 cross-cutting conventions, and the 
change management process you must follow for every change.
```

## Step 3 — Review and evolve the architecture

```
Read the HLDs at docs/02-design/technical/hld/ and compare against 
the PRD and current V1 code. Flag gaps, inconsistencies, and anything 
new in V1 not yet reflected. Propose improvements. Update the HLD 
documents. Escalate architectural trade-offs to Prasad and Dilip 
with supporting documentation (see Escalation Path below).
```

## Step 4 — Review and evolve the component designs

```
Read the LLDs at docs/02-design/technical/lld/ and compare against 
the approved HLDs and current V1 code. Flag missing components, 
underspecified areas, and V1 changes not yet reflected. Propose 
improvements. Update the LLD documents.
```

## Step 5 — Plan the build

```
From the approved HLDs and LLDs, create a phased build plan. Each 
phase is a shippable slice. Identify which phases you build yourself 
(HITL) and which you delegate to the team via the LLDs.
```

## Step 6 — Delegate work

```
Implement the LLD at docs/02-design/technical/lld/<component>.md.
Follow the 22-step process in CLAUDE.md. You review at each gate — 
design, tests, code review Round 1, code review Round 2.
Do not proceed past a gate without your approval.
```

## Step 7 — Build (HITL)

```
You're implementing <component> yourself using its LLD. Claude 
proposes code, you approve each piece. Follow the 22-step process, 
starting with the GitHub issue.
```

## Step 8 — Review progress

```
Show me the gap between the PRD and what's built. For each 
requirement: Done / Partial / Not started. What's next?
```

## Repeat steps 6-8 until the PRD is covered.

---

## Ownership Rules

**Whoever builds a slice owns it end-to-end.** Build it, test it, fix it. No handing off broken code for someone else to debug. Each slice must be a working system — deployed, tested, and verified — before moving to the next.

**The architect owns:**
- **QA** — define test strategy, review test coverage, ensure every slice passes before merge
- **IaC / Ops** — infrastructure manifests, deployment configs, migrations, monitoring setup
- **Integration** — slices work together, not just in isolation
- **A working system at all times** — after every slice ships, the system must be deployable and functional. No "it works on my machine" — it works on the target environment.

---

## Escalation Path

Architectural trade-offs, ADR changes, PRD scope changes, and cross-team decisions must be discussed with Prasad (technical advisor) and Dilip (product owner).

All escalations must use the prescribed documentation formats — no Slack messages or verbal escalations without supporting docs. The docs ARE the discussion.

| Type | How to communicate |
|---|---|
| **Architectural decisions** | Propose as a new ADR following `docs/02-design/technical/adrs/README.md` format — options, trade-offs, and a recommendation |
| **PRD scope changes** | Update `docs/01-product/prd.md` with the proposed change, flag which functional requirements are affected |
| **Design changes** | Update the relevant HLD/LLD first, then present the diff |
| **Risk decisions** | Use the downstream impact brief (5-section format from CLAUDE.md step 21) |

---

## How-To Guides

| I want to... | Guide |
|---|---|
| Add a new feature | [Adding a New Feature](./adding-a-feature.md) — full 28-step process from issue to post-ship ROI check |
| Fix a bug | [Fixing a Bug or Refactoring](./fixing-and-refactoring.md) — streamlined process with regression-test-first |
| Refactor code | [Fixing a Bug or Refactoring](./fixing-and-refactoring.md) — tests must pass before AND after |
| Understand the full pipeline | [Process Overview](./process-overview.md) — visual pipeline + 22-step detail |
