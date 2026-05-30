# Architect Playbook

**Context:** You are the architect on [Project Name]. The target architecture is fully designed — HLDs, LLDs, ADRs, and a system manifest are all in the repo. Your job is to govern and evolve the architecture as the system grows, delegate work to the team via LLDs, and own quality end-to-end.

---

## Step 1 — Orient to the system

At the start of any new piece of work, reload your context:

```
Read docs/02-design/technical/adrs/design-decisions.md,
docs/system-manifest.yaml, and docs/02-design/technical/hld/system.md.
Summarise the key architectural decisions, the cross-cutting conventions,
and the domain boundaries I must respect before I start designing
the payments refund flow.
```

---

## Step 2 — Review and evolve the architecture

When requirements change or new capabilities are needed:

```
Read the HLDs at docs/02-design/technical/hld/ relevant to
the payments domain. Compare against the updated PRD at
docs/01-product/prd.md. Flag gaps, inconsistencies, or areas
where the design needs to evolve to support the refund flow.
Propose improvements and update the HLD documents.
```

For any proposed architectural change:

```
I want to add idempotency key enforcement to all refund API calls.
What ADRs are relevant? What are the trade-offs? Draft a new ADR
following docs/02-design/technical/adrs/README.md format — options,
trade-offs, and a recommendation.
```

---

## Step 3 — Review and evolve component designs

Before delegating any work to the team:

```
Read the LLD at docs/02-design/technical/lld/payments/refund-flow.md.
Does it fully specify the component for implementation?
Flag underspecified areas, missing error paths, missing
conventions from the system manifest, or edge cases not covered.
```

When a new component is needed:

```
/hitl:dev-generate-docs

I need an LLD for the payments refund flow — a new component that
handles refund requests idempotently and posts a reversal event.
Generate the HLD section first, then the LLD once I approve.
Follow the existing conventions from docs/system-manifest.yaml.
```

---

## Step 4 — Plan and delegate work

Once designs are approved:

```
From the approved HLDs and LLDs for the payments domain, propose
a phased build plan. Each phase is a shippable, independently testable
slice. Sequence them to minimise integration risk.
```

To delegate a slice to a team member, point them at the LLD and the workflow:

```
Implement the payments refund flow from
docs/02-design/technical/lld/payments/refund-flow.md.
Follow the developer playbook. The gates are: tests reviewed, code
review Rounds 1 and 2, architect code review (step 19a).
Do not proceed past a gate without my approval.
```

---

## Step 5 — Build directly (HITL)

For work you're implementing yourself:

```
/hitl:dev-tdd

I have been assigned GitHub issue #42. Read the decision packet at
docs/decisions/issue-42.yaml and tell me what I am building,
what domain I am in, and what the test plan requires me to cover.
```

---

## Step 6 — Review progress

```
Based on docs/01-product/prd.md and the current state of the codebase,
show me the gap between requirements and what's built. For each
requirement: Done / Partial / Not started. Focus on the payments domain.
```

---

## Ownership Rules

**Whoever builds a slice owns it end-to-end.** Build it, test it, fix it. No handing off broken code for someone else to debug.

**The architect owns:**
- **QA** — define test strategy, review test coverage, ensure every slice passes before merge
- **IaC / Ops** — infrastructure manifests, deployment configs, migrations, monitoring setup
- **Integration** — slices work together, not just in isolation
- **A deployable system at all times** — after every slice ships, the system must work on the target environment
- **Architect code review (step 19a)** — after AI rounds complete, review the implementation on GitHub using the approve/request-changes UI; the developer runs `/hitl:architect-review-code` to create the GitHub PR with the AI review summary and a 7-item judgment checklist; assess business logic correctness, architectural consistency, domain boundary integrity, hidden coupling, complexity, naming, and error handling; approve or request changes; the PR is not merged at this step — merging happens at step 28

---

## Escalation Path

Architectural trade-offs, ADR changes, PRD scope changes, and cross-team decisions must be discussed with the technical advisor and product owner.

All escalations use documentation — no undocumented verbal decisions.

| Type | How to communicate |
|---|---|
| **Architectural decisions** | Propose as a new ADR following `docs/02-design/technical/adrs/README.md` format |
| **PRD scope changes** | Update `docs/01-product/prd.md` with the proposed change, flag affected requirements |
| **Design changes** | Update the relevant HLD/LLD first, then present the diff |
| **Risk decisions** | Use the downstream impact brief (`/hitl:dev-impact-brief`) |

---

## How-To Guides

| I want to... | Guide |
|---|---|
| Make any code change | `docs/06-team/developer-playbook.md` |
| Write a new design | `/hitl:dev-generate-docs` skill |
| Analyse impact of a change | `/hitl:dev-apply-change` skill |
| Check convention violations | `/hitl:dev-check-conventions` skill |
| Write a downstream impact brief | `/hitl:dev-impact-brief` skill |
| Understand the full dev workflow | `ai/claude/dev-practices/SKILL.md` |
