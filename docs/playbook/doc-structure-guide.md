# Documentation Structure Guide

How to organize your project's `docs/` folder. This structure scales from a solo developer to a full product team.

---

## The Structure

```
docs/
├── 01-product/          WHAT and WHY
│   ├── prd.md           Product requirements (use ai/templates/prd-template.md)
│   ├── roadmap.md       Phases, milestones, priorities
│   └── competitive-analysis.md
│
├── 02-design/           HOW
│   ├── technical/
│   │   ├── overview.md  Architecture overview (start-here doc)
│   │   ├── solution-strategy.md
│   │   ├── hld/         High-level designs (one per system area)
│   │   │   ├── index.md
│   │   │   ├── system.md
│   │   │   ├── data.md
│   │   │   ├── security.md
│   │   │   └── ...
│   │   ├── lld/         Low-level designs (one per component)
│   │   │   ├── index.md
│   │   │   ├── controllers/
│   │   │   ├── services/
│   │   │   ├── models/
│   │   │   └── ...
│   │   └── adrs/        Architectural decision records
│   │       ├── README.md
│   │       └── design-decisions.md
│   └── ux/              Figma references, user flows
│
├── 03-engineering/      The PRACTICE of building
│   ├── best-practices.md
│   ├── testing/
│   │   ├── strategy.md
│   │   ├── test-plan.md
│   │   └── test-registry.yaml  ← index of all tests by domain + risk
│   └── training/
│       └── <capability>.md     ← one per new pattern/framework
│
├── 04-operations/       RUNNING the system
│   ├── deployment/
│   ├── admin-guide.md
│   ├── security-audit.md
│   ├── cost-analysis.md
│   └── incident-registry.yaml  ← past failures + lessons learned
│
├── 05-<project-specific>/  Time-bounded docs — archive after completion
│   ├── migration-plan.md       (e.g., for a V1→V2 migration)
│   ├── team-responsibilities.md
│   └── gap-analysis.md
│
├── 06-team/             WHO does what + how each role works
│   ├── README.md        Team roster, roles, escalation path
│   ├── pm-playbook.md           ← PM: requirements, design reviews, deploy approvals
│   ├── developer-playbook.md    ← Developer: issue to PR workflow
│   └── architect-playbook.md   ← Architect: architecture governance, ADR process
│
├── playbook/            HOW-TO guides for system-wide processes
│   ├── process-overview.md
│   ├── adding-a-feature.md
│   └── fixing-and-refactoring.md
│
├── patterns/            Reusable architecture patterns
│   ├── idempotency-keys.md
│   └── failure-mode-taxonomy.md
│
├── releases/            Release notes
│   └── v1.0-alpha.md
│
├── system-manifest.yaml Cross-cutting conventions + domain map
└── README.md            Navigation index for the whole tree
```

---

## What Goes Where

| Content | Location | Who owns it |
|---|---|---|
| Product vision, requirements, personas | `01-product/` | PM |
| Architecture diagrams, component design | `02-design/technical/hld/` | Architect |
| Method signatures, class diagrams, sequence diagrams | `02-design/technical/lld/` | Architect |
| Why we chose X over Y | `02-design/technical/adrs/` | Architect (technical advisor approves) |
| Coding standards, testing strategy | `03-engineering/` | Architect |
| Training plans for new patterns | `03-engineering/training/` | Developer who built it |
| Deployment, runbooks, monitoring | `04-operations/` | Architect (owns IaC/Ops) |
| Past incidents + lessons | `04-operations/incident-registry.yaml` | Whoever fixed it |
| Test coverage index | `03-engineering/testing/test-registry.yaml` | Developers |
| Time-bounded project docs (migrations, launches) | `05-<project-specific>/` | Architect — archive after completion |
| Team structure, roles, and role playbooks | `06-team/` | Architect + PM |
| System-wide process guides (feature workflow, fix workflow) | `playbook/` | Shared |

---

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Numbered folders | `NN-name/` for the core hierarchy | `01-product/`, `02-design/` |
| Unnumbered folders | For cross-cutting concerns | `playbook/`, `patterns/`, `releases/` |
| HLD files | One per system area | `system.md`, `data.md`, `security.md` |
| LLD files | Organized by layer | `controllers/auth.md`, `services/model-router.md` |
| ADRs | Descriptive names | `idempotency-keys.md`, `retry-policy.md` |
| Templates | Always in `/ai/templates/` at repo root | Not in `docs/` |

---

## Getting Started

1. Copy this structure into your project's `docs/` folder
2. Start with `01-product/prd.md` (use `ai/templates/prd-template.md`)
3. Create `docs/system-manifest.yaml` (use `ai/templates/system-manifest-template.yaml`)
4. Add `docs/README.md` as the navigation index
5. Fill in docs as you design and build — the 31-step process drives doc creation

The numbered folders represent a logical progression: understand the product (01) → design the solution (02) → build it (03) → run it (04). Not every project needs all folders on day one.
