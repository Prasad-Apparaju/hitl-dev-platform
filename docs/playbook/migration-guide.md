# Migration Guide — Adopting This Process to Migrate a Backend

For teams migrating an existing system (e.g., NestJS/Spring Boot) to a new backend architecture (e.g., Python/FastAPI) using the HITL AI-Driven Development process.

> **AI tool note:** This guide uses Claude Code and `CLAUDE.md` as examples. The process works with any AI coding assistant that supports auto-loaded project rules (Cursor, Windsurf, Cline, etc.).

## Which path are you on?

| Path | You have | Start at |
|------|----------|----------|
| **A — Bundled workspace** | A migration workspace repo (like [PSR-Works-Migration](https://github.com/Prasad-Apparaju/PSR-Works-Migration)) with target docs, skills, tools, and V1/V2 structure already set up | [Path A](#path-a--bundled-migration-workspace) |
| **B — Starting from scratch** | Only your existing codebase and access to [hitl-dev-platform](https://github.com/Prasad-Apparaju/hitl-dev-platform) | [Path B](#path-b--starting-from-scratch) |

---

## Path A — Bundled migration workspace

Your workspace already contains the target architecture docs, skills, tools, CI actions, CLAUDE.md, and system manifest. The setup and architecture adoption steps are done.

### A1. Setup

```bash
git clone https://github.com/Prasad-Apparaju/PSR-Works-Migration.git
cd PSR-Works-Migration

# Check out the current system into V1/
cd V1 && git clone https://github.com/dilipkpoluru/PSR-Works.git . && cd ..

# Install the agentic platform (if building agents)
pip install agentic-platform

# Open in Claude Code — CLAUDE.md auto-loads the conventions
claude
```

**Time: 30 minutes.** Every developer who clones the repo gets the process, the target architecture, and the migration docs.

### A2. Understand the current system

```bash
/generate-docs reverse-engineer the existing system
```

AI scans `V1/`, produces a manifest and docs for the CURRENT system. Compare against the TARGET docs already in `docs/` to see exactly what needs to change.

Also populate:
- `docs/test-registry.yaml` — catalog existing tests using the template already in the repo
- `docs/incident-registry.yaml` — ask the team: "what broke in the last 6 months?" Each answer is an entry.

### A3. Assess the gaps

```bash
/check-conventions
```

Bucket findings into tiers (Blocker / Near-term / Medium-term / Long-term) using the [gap assessment](adoption-guide.md) criteria. Fix blockers before migration starts.

### A4. Read the target architecture

These docs are already in your repo — no external access needed:

| What to read | Local path | What it tells you |
|-------------|-----------|------------------|
| Migration plan | `docs/05-migration/migration-plan.md` | The proven sequence for this exact migration |
| Architecture mapping | `docs/05-migration/architecture.md` | How V1 components map to V2 |
| Data model mapping | `docs/05-migration/data-model-mapping.md` | Old schema → new schema, field by field |
| API contract mapping | `docs/05-migration/api-contract-mapping.md` | Old endpoints → new endpoints |
| Target HLDs | `docs/02-design/technical/hld/` | 14 architecture specs (system, agents, data, AI inference, observability, security, infrastructure, etc.) |
| Target LLDs | `docs/02-design/technical/lld/` | 33 component specs — the detail level AI generates code from |
| Design decisions | `docs/02-design/technical/adrs/` | 55+ ADRs with rationale — follow these, don't reinvent them |
| System manifest | `docs/system-manifest.yaml` | Domain boundaries, facade APIs, conventions |
| Frontend reuse | `docs/05-migration/frontend-reuse.md` | What stays, what changes in the UI |

### A5. Sequence into vertical slices

Order by dependency. Each slice is a shippable unit migrated end-to-end. Use the migration plan's sequence as your starting point — adapt to your team's priorities.

### A6. Execute one slice at a time

| Step | What to do | Skill |
|------|-----------|-------|
| 1 | Read the target LLD for this slice | Study `docs/02-design/technical/lld/` |
| 2 | Read the migration mapping for this slice | Study `docs/05-migration/` |
| 3 | Generate tests from the target LLD | `/tdd` |
| 4 | Human + QA review tests, add edge cases | Manual |
| 5 | AI generates Python code in `V2/` that passes tests | `/tdd` continues |
| 6 | Code review against the target LLD | Two rounds |
| 7 | Downstream impact brief | `/impact-brief` |
| 8 | Convention check | `/check-conventions` |
| 9 | Ship the slice | PR, canary, promote |

### A7. Verify behavioral equivalence

**For migrated agents:**
- Run the same inputs through V1 (JS) and V2 (Python)
- Compare outputs — differences are either bugs (fix) or improvements (document as ADRs)

**For migrated APIs:**
- Run the existing frontend E2E tests against V2
- Every test that passes against V1 must also pass against V2

### A8. Cut over and retire

1. Route traffic gradually: V1 → V2 per endpoint (feature flags)
2. Keep V1 as rollback for 30 days
3. After 30 days stable, decommission V1
4. Update the system manifest to reflect the final architecture

**→ Continue to [Language migration considerations](#language--framework-migration) if migrating across languages.**

---

## Path B — Starting from scratch

You have your existing codebase and access to hitl-dev-platform. You need to set up the process, reverse-engineer your system, and adopt or design the target architecture.

### B1. Set up the process on your repo

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

### B2. Reverse-engineer the existing system

| What to do | Skill / tool | Reference to study first |
|-----------|-------------|-------------------------|
| Generate manifest, HLDs, LLDs, ADRs from the current codebase | `/generate-docs reverse-engineer the existing system` ([skills/generate-docs/](../../skills/generate-docs/)) | Study the [styleflow manifest](https://github.com/Prasad-Apparaju/styleflow/blob/main/docs/system-manifest.yaml) to see the target format |
| Generate the system manifest standalone | `python tools/generate-manifest/generator.py --source ./src --output docs/system-manifest.yaml` ([tools/generate-manifest/](../../tools/generate-manifest/)) | Study `facade_apis` (blurb + mutations + preconditions) and `boundary_entities` |
| Populate the test registry | Create `docs/test-registry.yaml` using the template ([templates/test-registry-template.yaml](../../templates/test-registry-template.yaml)) | How tests are tagged by domain, risk, origin |
| Start the incident registry | Create `docs/incident-registry.yaml` using the template ([templates/incident-registry-template.yaml](../../templates/incident-registry-template.yaml)) | Ask the team: "what broke in the last 6 months?" |

### B3. Assess the gaps

| What to do | Skill / tool |
|-----------|-------------|
| Run all convention checks | `/check-conventions` ([skills/check-conventions.md](../../skills/check-conventions.md)) or `python tools/check-conventions/runner.py --config convention-checks.yaml --verbose` |
| Bucket findings into tiers | Follow [adoption-guide.md §After the Sprint](adoption-guide.md) — Blocker / Near-term / Medium-term / Long-term |
| Fix blockers before migration starts | AI generates the fix; architect reviews |

### B4. Adopt the target architecture

Two sub-paths:

**B4a — A reference implementation exists** (e.g., someone already migrated this system or a similar one):

The reference repo is the most valuable asset the team has. Give them READ access and point them to:

| What to study | What it shows |
|--------------|---------------|
| `docs/system-manifest.yaml` | The format, detail level per domain, what a facade API looks like |
| Any HLD in `docs/02-design/technical/hld/` | How architecture is documented — diagrams, component tables, security |
| Any LLD in `docs/02-design/technical/lld/` | The precision needed for AI to generate correct code |
| Any ADR in `docs/02-design/technical/adrs/` | How decisions are documented with rationale and consequences |
| `CLAUDE.md` | How conventions are inlined so every Claude session follows the same rules |
| `docs/test-registry.yaml` | How tests are cataloged by domain, risk, origin |

Use these as FORMAT EXAMPLES — "my LLD should look like this, at this level of detail." The specific content describes a different system; yours will differ.

What transfers directly vs. what doesn't:

| Copy it | Use as reference only |
|---------|----------------------|
| CLAUDE.md template | The specific conventions (yours are different) |
| Skills (dev-practices, apply-change, tdd, etc.) | The specific HLDs/LLDs/ADRs (yours describe a different system) |
| Convention checker + CI actions | The specific convention checks (yours enforce different patterns) |
| Issue template with ROI section | The system manifest content (yours has different domains) |
| Test/incident registry FORMAT | The specific test cases and incidents |
| agentic-platform code (if building agents) | Domain-specific agent implementations |

> **Tip:** If the reference implementation migrated the exact same system, consider building a bundled migration workspace (like [PSR-Works-Migration](https://github.com/Prasad-Apparaju/PSR-Works-Migration)) — copy all target docs into the migration repo so the team doesn't need separate access. This converts your Path B into a Path A for the next team.

**B4b — No reference implementation exists:**

Design the target architecture from scratch using `/generate-docs`:
1. Write HLDs for the target system
2. Get architect approval
3. Write LLDs for each component
4. Document decisions as ADRs

### B5. Sequence into vertical slices

Order by dependency. Each slice is a shippable unit migrated end-to-end. A typical backend migration is 6-12 slices.

### B6. Execute one slice at a time

| Workflow step | Skill / tool | What it produces |
|--------------|-------------|-----------------|
| Create issue | Use [templates/issue-template.md](../../templates/issue-template.md) | Issue with ROI estimate + downstream impact sections |
| Impact analysis | `/apply-change` ([skills/apply-change.md](../../skills/apply-change.md)) | Affected components in BOTH current and target system |
| TDD | `/tdd` ([skills/tdd.md](../../skills/tdd.md)) | Tests from the target LLD + manifest contracts |
| Generate code | AI generates from the target LLD following `CLAUDE.md` conventions | Code using agentic-platform infrastructure (if agentic) |
| Code review | Two rounds — AI reviews against LLD | Structure (R1) then behavior (R2) |
| Downstream impact brief | `/impact-brief` ([skills/impact-brief.md](../../skills/impact-brief.md)) | 5-section brief from PR diff + manifest + incident registry |
| Convention check | `/check-conventions` ([skills/check-conventions.md](../../skills/check-conventions.md)) | Violations caught before CI |

### B7. Run old and new in parallel

- **Route by feature flag** — new endpoints serve from the new backend; old from the old
- **Compare outputs** — for migrated endpoints, run both and compare (shadow mode)
- **Migrate traffic gradually** — 5% → 25% → 50% → 100% per endpoint
- **Keep the old system as rollback** until the new one is stable for 30 days

### B8. Retire the old system

1. All traffic on the new backend
2. Old system available as rollback for 30 days
3. After 30 days with zero rollbacks, decommission
4. Update the system manifest to reflect the final architecture

---

## Language + framework migration

When migrating across languages (not just refactoring within the same language), additional considerations apply regardless of which path you're on.

### API contract preservation

The existing frontend expects specific API shapes. Before writing any backend code:

1. **Extract the API contract** from the current system — every endpoint, request shape, response shape, status codes, error format. AI can generate this from the existing route handlers.
2. **Write contract tests** against the current backend — these become the acceptance criteria for the new backend.
3. **Decide: same contract or new contract?**
   - **Same contract** — frontend doesn't change. New backend implements the existing API exactly. Simplest migration path.
   - **New contract** — frontend adapts. Requires a v1-compat shim during migration OR frontend changes in parallel.

Document this decision as an ADR.

### Data migration

If the database changes (e.g., MongoDB → PostgreSQL):

1. **Map the data model** — current schema → target schema, field by field
2. **Write migration scripts** — AI generates from the mapping. Test against a copy of production data.
3. **Plan the cutover** — can you run dual-write during migration? Or is it a single-cutover with downtime?
4. **Verify data integrity** — row counts, checksums, referential integrity checks after migration

### Agent behavior verification (for agentic systems)

1. **Capture golden outputs** from the current agents — run them against a fixed set of inputs, record the outputs. These become the behavioral baseline.
2. **Build the new agents** using [agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform) infrastructure (BaseAgent, MutatingTool, AgentEvaluator, etc.)
3. **Run the same inputs through the new agents** — compare outputs against the golden baseline. Differences are either bugs (fix) or intentional improvements (document as ADRs).
4. **Migrate prompts to skill files** — if agents have prompts embedded as string literals in code, extract them into versioned `skills/<agent>/system-prompt.md` files.

### Frontend preservation

If keeping the existing UI:

1. **The frontend points to a single API base URL** — during migration, route to either backend per endpoint (feature-flag or path-based routing via reverse proxy)
2. **Auth must be compatible** — if switching JWT implementations, the frontend's token handling must work with both during the transition
3. **Test the frontend against the new backend** — run the existing E2E tests against the new backend. Every test that passes against the old must also pass against the new.

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

## FAQ

| Question | Answer |
|----------|--------|
| "Do we need to document the old system?" | Yes — run `/generate-docs reverse-engineer`. AI does the drafting; architect reviews. ~1 week. |
| "Can we skip the docs and just rewrite?" | AI will generate inconsistent code without a shared spec. The rewrite will need its own rewrite. |
| "What if we don't have an architect?" | The most senior dev who knows the current system plays that role. Their job is reviewing, not writing. |
| "How long does the full migration take?" | Each vertical slice takes days to weeks. A typical backend migration is 6-12 slices. |
| "What tools do we use?" | Claude Code + the skills (`/generate-docs`, `/tdd`, `/apply-change`, `/impact-brief`, `/check-conventions`) + the convention checker in CI + agentic-platform (if building agents). |
| "Where do I look to see what 'done' looks like?" | The reference repo (or bundled workspace) — study its manifest, HLDs, LLDs, ADRs, CLAUDE.md, test registry. |

## Reference

- [Process overview](process-overview.md) — the full workflow
- [Adoption guide](adoption-guide.md) — the brownfield sprint + gap assessment
- [hitl-dev-platform README](https://github.com/Prasad-Apparaju/hitl-dev-platform) — the practitioner's guide
- [agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform) — reusable agent infrastructure (if the target system includes agents)
- [PSR-Works-Migration](https://github.com/Prasad-Apparaju/PSR-Works-Migration) — bundled migration workspace (Path A example)
