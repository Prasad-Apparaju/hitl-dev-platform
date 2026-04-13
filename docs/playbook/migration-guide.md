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

| What to do | Skill / tool to use | Reference to study first |
|-----------|---------------------|-------------------------|
| Generate manifest, HLDs, LLDs, ADRs from the current codebase | Run `/generate-docs reverse-engineer the existing system` ([skills/generate-docs/](../../skills/generate-docs/)) | Study the reference repo's `docs/system-manifest.yaml` to see the target format and level of detail |
| Generate the system manifest standalone | Run `python tools/generate-manifest/generator.py --source ./src --output docs/system-manifest.yaml` ([tools/generate-manifest/](../../tools/generate-manifest/)) | Study the reference repo's manifest — especially `facade_apis` (blurb + mutations + preconditions) and `boundary_entities` |
| Populate the test registry from existing tests | Create `docs/test-registry.yaml` using the template ([templates/test-registry-template.yaml](../../templates/test-registry-template.yaml)) | Study the reference repo's test registry — how tests are tagged by domain, risk, origin |
| Start the incident registry | Create `docs/incident-registry.yaml` using the template ([templates/incident-registry-template.yaml](../../templates/incident-registry-template.yaml)) | Ask the team: "what broke in the last 6 months?" — each answer is an entry |

The output answers: "What does the current system actually do, and why?"

### Step 3: Assess the gaps

| What to do | Skill / tool to use |
|-----------|---------------------|
| Run all convention checks | `/check-conventions` ([skills/check-conventions.md](../../skills/check-conventions.md)) or `python tools/check-conventions/runner.py --config convention-checks.yaml --verbose` |
| Bucket findings into tiers | Follow [adoption-guide.md §After the Sprint](adoption-guide.md) — Blocker / Near-term / Medium-term / Long-term |
| Fix blockers before migration starts | AI generates the fix; architect reviews. See the gap assessment table in the adoption guide. |

### Step 4: Design the target architecture

| What to do | Skill / tool to use | Reference to study |
|-----------|---------------------|-------------------|
| Create HLDs for the target system | `/generate-docs` in new-feature mode for each area ([skills/generate-docs/](../../skills/generate-docs/)) — uses [templates/hld-template.md](../../skills/generate-docs/templates/hld-template.md) | Reference repo's `docs/02-design/technical/hld/` — especially `system.md`, `agents.md`, `data.md` |
| Create LLDs for each target component | `/generate-docs` phase 2 — uses [templates/lld-component-template.md](../../skills/generate-docs/templates/lld-component-template.md) | Reference repo's `docs/02-design/technical/lld/` — especially `agents/framework.md` for the level of precision needed |
| Document each decision that differs from current | Use [templates/adr-template.md](../../templates/adr-template.md) | Reference repo's `docs/02-design/technical/adrs/` — 55 decisions show the format and depth |
| Create migration mapping table | Manual — AI can draft from the two manifests (current vs target) | Reference repo's `docs/05-migration/` — data-model-mapping, api-contract-mapping, architecture |
| Set up the target agent infrastructure (if agentic) | Install [agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform) (`pip install agentic-platform`) | Reference repo's agent implementations + the [minimal agent example](https://github.com/Prasad-Apparaju/agentic-platform/tree/main/examples/minimal_agent) |
| Extract JS agent prompts into skill files | Create `skills/<agent>/system-prompt.md` for each agent — see [Skill System pattern](https://github.com/Prasad-Apparaju/agentic-platform/blob/main/docs/patterns/skill-system.md) | Reference repo's `skills/` directory structure |

### Step 5: Sequence the migration into vertical slices

Order by dependency. Each slice is a shippable unit migrated end-to-end.

Use the reference repo's showcase sequence as a model — it went: Foundation → Auth + Infra → AI Core → Content → Automation → Observability. Adapt the order to your system's dependency graph.

Each slice follows the full workflow. The skills that drive each slice:

### Step 6: Execute one slice at a time

| Workflow step | Skill / tool | What it produces |
|--------------|-------------|-----------------|
| Create issue | Use [templates/issue-template.md](../../templates/issue-template.md) | Issue with ROI estimate + downstream impact sections |
| Impact analysis | `/apply-change` ([skills/apply-change.md](../../skills/apply-change.md)) | Affected components in BOTH current and target system |
| TDD — generate tests, human review, improve LLD | `/tdd` ([skills/tdd.md](../../skills/tdd.md)) | Tests from the target LLD + manifest contracts. Tests registered in test registry. |
| Generate code | AI generates from the target LLD following `CLAUDE.md` conventions | Python code using agentic-platform infrastructure (if agentic) |
| Code review | Two rounds — AI reviews against LLD | Structure (R1) then behavior (R2) |
| Downstream impact brief | `/impact-brief` ([skills/impact-brief.md](../../skills/impact-brief.md)) | 5-section brief from PR diff + manifest + incident registry |
| Convention check before PR | `/check-conventions` ([skills/check-conventions.md](../../skills/check-conventions.md)) | Violations caught before CI |

### Step 7: Run old and new in parallel

- **Route by feature flag** — new endpoints serve from the new backend; old from the old
- **Compare outputs** — for migrated endpoints, run both and compare (shadow mode)
- **Migrate traffic gradually** — 5% → 25% → 50% → 100% per endpoint
- **Keep the old system as rollback** until the new one is stable for 30 days

### Step 8: Retire the old system

1. All traffic on the new backend
2. Old system available as rollback for 30 days
3. After 30 days with zero rollbacks, decommission
4. Update the system manifest to reflect the final architecture

## What the team needs to know

| Question | Answer |
|----------|--------|
| "Do we need to document the old system?" | Yes — Step 2. Run `/generate-docs reverse-engineer`. AI does the drafting; architect reviews. ~1 week. |
| "Can we skip the docs and just rewrite?" | AI will generate inconsistent code without a shared spec. The rewrite will need its own rewrite. |
| "What if we don't have an architect?" | The most senior dev who knows the current system plays that role. Their job is reviewing, not writing. |
| "How long does the full migration take?" | Each vertical slice takes days to weeks. A typical backend migration is 6-12 slices. |
| "What tools do we use?" | Claude Code + the skills from this repo (`/generate-docs`, `/tdd`, `/apply-change`, `/impact-brief`, `/check-conventions`) + the convention checker in CI + the agentic-platform (if building agents). |
| "Where do I look to see what 'done' looks like?" | The reference repo — study its manifest, HLDs, LLDs, ADRs, CLAUDE.md, test registry. |

## Language + framework migration (e.g., JavaScript → Python)

When migrating across languages (not just refactoring within the same language), additional steps are needed:

### API contract preservation

The existing frontend expects specific API shapes. Before writing any backend code:

1. **Extract the API contract** from the current system — every endpoint, request shape, response shape, status codes, error format. AI can generate this from the existing route handlers.
2. **Write contract tests** against the current backend — these become the acceptance criteria for the new backend. The new Python API must pass the same contract tests.
3. **Decide: same contract or new contract?**
   - **Same contract** — frontend doesn't change. New backend implements the existing API exactly. Simplest migration path.
   - **New contract** — frontend adapts. Requires a v1-compat shim in the new backend during migration (serves old shape, delegates to new internals) OR frontend changes in parallel.

Document this decision as an ADR.

### Data migration

If the database changes (e.g., MongoDB → PostgreSQL):

1. **Map the data model** — current schema → target schema, field by field
2. **Write migration scripts** — AI generates from the mapping. Test against a copy of production data.
3. **Plan the cutover** — can you run dual-write during migration? Or is it a single-cutover with downtime?
4. **Verify data integrity** — row counts, checksums, referential integrity checks after migration

### Agent behavior verification (for agentic systems)

When migrating agents from one language/framework to another, the hardest part is verifying that the new agents behave the same as the old ones:

1. **Capture golden outputs** from the current JS agents — run them against a fixed set of inputs, record the outputs. These become the behavioral baseline.
2. **Build the new Python agents** using the [agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform) infrastructure (BaseAgent, MutatingTool, AgentEvaluator, etc.)
3. **Run the same inputs through the new agents** — compare outputs against the golden baseline. Differences are either bugs (fix) or intentional improvements (document as ADRs).
4. **Migrate prompts to skill files** — if the JS agents have prompts embedded as string literals in code, extract them into versioned `skills/<agent>/system-prompt.md` files. This is the right time to do it — the prompts are being touched anyway.

### Frontend preservation

If keeping the existing UI:

1. **The frontend points to a single API base URL** — during migration, this URL routes to either the old or new backend per endpoint (feature-flag routing or path-based routing via a reverse proxy)
2. **Auth must be compatible** — if switching from one JWT implementation to another, the frontend's token handling must work with both during the transition
3. **Test the frontend against the new backend** — run the existing E2E tests (Playwright, Cypress) against the new backend. Every test that passes against the old backend must also pass against the new one.

### Dependency mapping

| JavaScript | Python equivalent | Notes |
|-----------|------------------|-------|
| Express / NestJS | FastAPI | Route structure, middleware, DI patterns differ |
| Prisma / Mongoose | SQLAlchemy | ORM patterns differ; model definitions need rewriting |
| Jest | pytest + pytest-asyncio | Test structure is similar; async patterns differ |
| LangChain.js | LangGraph (Python) | Agent framework; use agentic-platform's BaseAgent |
| npm packages | pip packages | Map each dependency; some have no Python equivalent |

AI generates the bulk of this mapping. The architect verifies the equivalences are correct.

---

## Using a reference implementation

If someone has already done this migration (or a similar one), their repo is the most valuable asset the team has. It shows what "done" looks like at every step — not in theory, but with real code and real docs.

Give the team READ access to the reference repo and point them to these specific files:

| What to look at | What it shows | File to study |
|----------------|---------------|---------------|
| **System manifest** | The format, the level of detail per domain, what a facade API looks like, how conventions are listed | `docs/system-manifest.yaml` |
| **An HLD** | How architecture is documented — diagrams, component tables, integration points, security considerations | Any file in `docs/02-design/technical/hld/` |
| **An LLD** | The level of precision needed for AI to generate correct code — method signatures, class diagrams, sequence diagrams, error handling | Any file in `docs/02-design/technical/lld/` |
| **An ADR** | How a design decision is documented — context, decision, alternatives, consequences, ROI estimate | Any file in `docs/02-design/technical/adrs/` |
| **CLAUDE.md** | How conventions are inlined so every Claude session follows the same rules | `CLAUDE.md` at the repo root |
| **Convention checker results** | What compliance looks like — which checks pass, which fail, how violations are reported | Run `python scripts/check_conventions.py --verbose` |
| **The test registry** | How tests are cataloged by domain, risk, origin, and incident link | `docs/test-registry.yaml` |
| **The migration docs** | How the current-to-target mapping was structured (if the reference repo IS a migration) | `docs/05-migration/` |

The team should NOT copy the reference docs into their repo — the content is specific to that system. They should use them as FORMAT EXAMPLES: "my LLD should look like this, at this level of detail, with this kind of diagram." Then they run `/generate-docs reverse-engineer` on their own codebase and produce their own version.

**What transfers directly vs what doesn't:**

| Transfers (copy it) | Doesn't transfer (use as reference only) |
|---------------------|------------------------------------------|
| CLAUDE.md template | The specific conventions (yours are different) |
| Skills (dev-practices, apply-change, tdd, etc.) | The specific HLDs/LLDs/ADRs (yours describe a different system) |
| Convention checker + CI actions | The specific convention checks (yours enforce different patterns) |
| Issue template with ROI section | The system manifest content (yours has different domains) |
| Test registry + incident registry FORMAT | The specific test cases and incidents |
| The agentic-platform code (if building agents) | The domain-specific agent implementations |

## Reference

- [Process overview](process-overview.md) — the full workflow
- [Adoption guide](adoption-guide.md) — the brownfield sprint + gap assessment
- [hitl-dev-platform README](https://github.com/Prasad-Apparaju/hitl-dev-platform) — the practitioner's guide
- [agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform) — reusable agent infrastructure (if the target system includes agents)
