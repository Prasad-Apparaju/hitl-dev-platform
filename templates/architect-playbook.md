# Architect Playbook

**Context:** You are the architect on [Project Name]. The target architecture is fully designed — HLDs, LLDs, ADRs, and a system manifest are all in the repo. Your job is to govern and evolve the architecture as the system grows, delegate work to the team via LLDs, and own quality end-to-end.

---

## Step 1 — Orient to the system

At the start of any new piece of work, reload your context:

```
Read docs/02-design/technical/adrs/design-decisions.md,
docs/system-manifest.yaml, and docs/02-design/technical/hld/system.md.
Summarize the key architectural decisions, the 10 cross-cutting
conventions, and the domain boundaries I must respect.
```

---

## Step 2 — Review and evolve the architecture

When requirements change or new capabilities are needed:

```
Read the HLDs at docs/02-design/technical/hld/ relevant to
[feature/capability]. Compare against the updated PRD at
docs/01-product/prd.md. Flag gaps, inconsistencies, or areas
where the design needs to evolve. Propose improvements and update
the HLD documents.
```

For any proposed architectural change:

```
I want to [describe change]. What ADRs are relevant? What
are the trade-offs? Draft a new ADR following
docs/02-design/technical/adrs/README.md format — options,
trade-offs, and a recommendation.
```

---

## Step 3 — Review and evolve component designs

Before delegating any work to the team:

```
Read the LLD at docs/02-design/technical/lld/[path].md.
Does it fully specify the component for implementation?
Flag underspecified areas, missing error paths, missing
conventions from the system manifest, or edge cases not covered.
```

When a new component is needed:

```
/generate-docs

I need a new component: [describe]. Generate the HLD section
first, then the LLD when I approve. Follow the existing
conventions from docs/system-manifest.yaml.
```

---

## Step 4 — Plan and delegate work

Once designs are approved:

```
From the approved HLDs and LLDs, propose a phased build plan.
Each phase is a shippable, independently testable slice.
Sequence them to minimize integration risk.
```

To delegate a slice to a team member, point them at the LLD and the workflow:

```
Implement the component at docs/02-design/technical/lld/[path].md.
Follow the developer playbook at docs/06-team/developer-playbook.md.
The gates are: design check-in, tests reviewed, code review Round 1,
code review Round 2. Do not proceed past a gate without my approval.
```

---

## Step 5 — Build directly (HITL)

For work you're implementing yourself:

```
I'm implementing [component] from
docs/02-design/technical/lld/[path].md. Claude proposes
code, I approve each piece. Start with the GitHub issue and
follow the dev-practices workflow.
```

---

## Step 6 — Review progress

```
Based on docs/01-product/prd.md and the current state of the codebase,
show me the gap between requirements and what's built.
For each requirement: Done / Partial / Not started. What's next?
```

---

## Ownership Rules

**Whoever builds a slice owns it end-to-end.** Build it, test it, fix it. No handing off broken code for someone else to debug.

**The architect owns:**
- **QA** — define test strategy, review test coverage, ensure every slice passes before merge
- **IaC / Ops** — infrastructure manifests, deployment configs, migrations, monitoring setup
- **Integration** — slices work together, not just in isolation
- **A deployable system at all times** — after every slice ships, the system must work on the target environment

---

## Escalation Path

Architectural trade-offs, ADR changes, PRD scope changes, and cross-team decisions must be discussed with the technical advisor and product owner.

All escalations use documentation — no undocumented verbal decisions.

| Type | How to communicate |
|---|---|
| **Architectural decisions** | Propose as a new ADR following `docs/02-design/technical/adrs/README.md` format |
| **PRD scope changes** | Update `docs/01-product/prd.md` with the proposed change, flag affected requirements |
| **Design changes** | Update the relevant HLD/LLD first, then present the diff |
| **Risk decisions** | Use the downstream impact brief (`/impact-brief`) |

---

## How-To Guides

| I want to... | Guide |
|---|---|
| Make any code change | `docs/06-team/developer-playbook.md` |
| Write a new design | `/generate-docs` skill |
| Analyse impact of a change | `/apply-change` skill |
| Check convention violations | `/check-conventions` skill |
| Write a downstream impact brief | `/impact-brief` skill |
| Understand the full dev workflow | `ai/dev-practices/SKILL.md` |
