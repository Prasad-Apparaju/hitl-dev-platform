# Migration Guide — Adopting This Process to Migrate a Backend

For teams migrating an existing system (e.g., NestJS/Spring Boot) to a new backend architecture (e.g., Python/FastAPI) using the HITL AI-Driven Development process.

## Prerequisites

- Access to the [hitl-dev-platform](https://github.com/Prasad-Apparaju/hitl-dev-platform) repo
- Claude Code (or equivalent AI coding tool) for each developer
- The existing system's source code
- A reference architecture for the target system (if one exists)

## The Steps

### Step 1: Set up the process on your repo

```bash
# Copy the skills so every developer's Claude follows the same workflow
cp -r hitl-dev-platform/skills/ your-repo/.claude/commands/

# Copy and customize CLAUDE.md
cp hitl-dev-platform/templates/CLAUDE.md.template your-repo/CLAUDE.md
# Edit: fill in your project's conventions and coding standards

# Copy convention checker config
cp hitl-dev-platform/examples/greenfield/convention-checks.yaml your-repo/

# Copy CI actions
cp hitl-dev-platform/ci/*.yml your-repo/.github/workflows/

# Copy issue template
cp hitl-dev-platform/templates/issue-template.md your-repo/.github/ISSUE_TEMPLATE/
```

**Time: 1 hour.** After this, every developer who clones the repo gets the process.

### Step 2: Reverse-engineer the existing system

Run the `/generate-docs` skill in reverse-engineer mode against the CURRENT codebase (the system you're migrating FROM):

```
/generate-docs reverse-engineer the existing system
```

This produces:
- System manifest — domain boundaries, file lists, facade APIs, conventions
- HLDs — architecture as it exists today
- LLDs — component-level design as it exists today
- ADRs — decisions inferred from the code (marked "NEEDS VERIFICATION")
- CLAUDE.md populated with detected conventions

**Time: ~1 week** (architect reviews AI output at each phase).

The output answers: "What does the current system actually do, and why?"

### Step 3: Assess the gaps

Run the convention checker against the reverse-engineered baseline:

```
/check-conventions
```

Bucket the findings (see [adoption-guide.md](adoption-guide.md) §After the Sprint):

| Tier | Action |
|------|--------|
| **Blocker** — security, data integrity | Fix before migration starts |
| **Near-term** — missing tests, missing error handling | Fix in the first migration sprint |
| **Medium-term** — convention drift, stale docs | Fix alongside migration work |
| **Long-term** — cosmetic | Fix when touched |

### Step 4: Design the target architecture

If a reference architecture exists (e.g., another team's repo you're migrating toward), use it as the starting point. If not, design from scratch.

For each major area of the target system:

1. **Create an HLD** describing the target architecture for that area
2. **Create an LLD** for each component in the target — precise enough that AI can generate code from it
3. **Create an ADR** for each significant decision that DIFFERS from the current system: "We're switching from X to Y because Z"
4. **Create a migration mapping** — which current component maps to which target component

| Current (source) | Target (destination) | Migration strategy |
|------------------|---------------------|-------------------|
| NestJS UserController | FastAPI auth controller | Rewrite — different framework, same API contract |
| Prisma User model | SQLAlchemy User model | Translate — same schema, different ORM |
| MongoDB campaigns collection | PostgreSQL campaigns table | Migrate data — different DB, schema mapping needed |
| React frontend | Keep as-is (or Next.js) | Reuse or rewrite depending on scope |

This mapping drives the order of migration work.

### Step 5: Sequence the migration into vertical slices

Each slice is a shippable unit that migrates one part of the system end-to-end. Order by dependency — the foundation comes first:

Example sequence:
1. **Foundation** — DB schema, auth, health checks, CI/CD pipeline
2. **Core models** — the data layer (users, brands, products)
3. **Core API** — the most-used endpoints
4. **Business logic** — the services that the API calls
5. **Integrations** — external APIs (payment, email, etc.)
6. **Advanced features** — agents, pipelines, monitoring (if applicable)

Each slice follows the full workflow: issue → design → PoC (if unknowns) → TDD → build → verify → assess → ship.

### Step 6: Execute one slice at a time

For each vertical slice:

1. **Create an issue** referencing the migration mapping from Step 4
2. **Run `/apply-change`** — impact analysis against both the current AND target system docs
3. **Update the target LLD** — make it precise enough for AI to generate from
4. **If unknowns exist** (new framework, new pattern), run a **PoC** first — see the Unknown phase in the workflow
5. **Run `/tdd`** — generate tests from the target LLD, have the team review + add edge cases
6. **Generate code** — AI generates from the target LLD, following CLAUDE.md conventions
7. **Verify** — two-round code review, reconcile docs
8. **Run `/impact-brief`** — downstream impact of this slice
9. **Ship** — canary deploy the new slice alongside the old system

### Step 7: Run old and new in parallel during migration

Do NOT cut over all at once. Run both systems simultaneously:

- **Route by feature flag** — new endpoints serve from the new backend; old endpoints serve from the old
- **Compare outputs** — for migrated endpoints, run both backends and compare results (shadow mode)
- **Migrate traffic gradually** — 5% → 25% → 50% → 100% per endpoint
- **Keep the old system as the rollback path** until the new system has been stable for 30 days

### Step 8: Retire the old system

Once all slices are migrated and stable:

1. All traffic routes to the new backend
2. Old system remains available as rollback for 30 days
3. After 30 days with zero rollbacks, decommission the old system
4. Update the system manifest to remove any references to the old architecture

## What the team needs to know

| Question | Answer |
|----------|--------|
| "Do we need to document the old system?" | Yes — Step 2. AI does the drafting; the architect reviews. This takes ~1 week, not months. |
| "Can we skip the docs and just rewrite?" | You can, but AI will generate inconsistent code without a shared spec. The rewrite will need its own rewrite within a year. |
| "What if we don't have an architect?" | The most senior developer who knows the current system plays that role. Their job is reviewing AI output, not writing docs from scratch. |
| "How long does the full migration take?" | Depends on system size. Each vertical slice takes days to weeks. A typical backend migration is 6-12 slices. |
| "What tools do we use?" | Claude Code for each developer. GitHub for everything. The skills and convention checker from this repo. |

## Reference

- [Process overview](process-overview.md) — the full workflow
- [Adoption guide](adoption-guide.md) — the brownfield sprint + gap assessment
- [hitl-dev-platform README](https://github.com/Prasad-Apparaju/hitl-dev-platform) — the practitioner's guide
- [agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform) — reusable agent infrastructure (if the target system includes agents)
