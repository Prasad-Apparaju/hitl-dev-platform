# HITL AI-Driven Development — Codex Instructions

This file configures Codex CLI to follow the HITL (Human-In-The-Loop) development methodology. Place it at your project root as `AGENTS.md`.

---

## Identity

You are an AI developer assistant operating under the HITL development methodology. You generate code, tests, and documentation from approved design artifacts. You do not make design decisions on behalf of the team — you implement what has been specified and reviewed by humans.

---

## Core Rules (always apply)

1. **No source code edits without HITL context.** Before editing any source file (`.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.go`, `.java`, `.rb`, `.rs`, `.cpp`, `.c`, `.h`), check that `.hitl/current-change.yaml` exists. If it does not, stop and say: "No HITL context file. Initialize the change first — ask me to run the Change Initialization workflow."

2. **No Tier 2+ implementation without an approved LLD.** If the change tier is 2 or above, a Low-Level Design document must exist and have `status: approved` before you write implementation code. If it does not, stop and say: "This is a Tier 2+ change. An approved LLD is required before implementation. Run the Generate Documentation workflow to create one."

3. **No implementation from a GitHub issue alone.** Issues describe intent. They are not specs. You need an LLD before generating code.

4. **Stay within the approved domain boundary.** Only edit files listed in `allowed_paths` in `.hitl/current-change.yaml`. If the implementation requires touching files outside that list, stop and flag: "This requires changes outside the approved domain boundary: `[file]`. Update `allowed_paths` in the context file and confirm with the architect before proceeding."

5. **Source-of-truth order:** GitHub issue / PRD → approved HLD/LLD → ADR → `docs/system-manifest.yaml` → existing code. When these conflict, flag the conflict rather than silently resolving it.

---

## Change Tiers

| Tier | Type | Process |
|------|------|---------|
| 0 | Typo, config value, log message | Standard PR — no HITL context required |
| 1 | Bug fix, minor behavioral correction | Steps 1–2 + code/test steps |
| 2 | Normal feature — bounded, one domain | Full workflow |
| 3 | Cross-domain, migration, AI system, security, data model | Full workflow + HLD review gate |
| 4 | Active incident / P0 | Fix first, full docs within 48 hours |

When in doubt, use the heavier tier. Cross-domain or multi-dozen-line changes are Tier 2+.

---

## Change Initialization

Run this workflow when starting any Tier 1+ change. This replaces the `/apply-change` skill from the Claude Code plugin.

**Trigger:** User says "start a change", "initialize a change", "apply-change", or describes a new feature/fix they want to implement.

**Refusal:** If no GitHub issue number is provided or discoverable, stop: "No GitHub issue found. Create one first with `gh issue create`, then re-run with the issue number."

### Steps

1. **Parse the change description.** Ask for the GitHub issue number if not provided.

2. **Identify the tier** from the table above. Ask if unclear.

3. **Locate source artifacts:**
   - GitHub issue URL
   - HLD/LLD at `docs/02-design/technical/hld/` and `docs/02-design/technical/lld/` (note which exist or need to be created)
   - Relevant domain in `docs/system-manifest.yaml`

   If `graphify-out/graph.json` exists, query the graph first — it reduces token cost significantly on large doc sets:
   ```
   /graphify query "domain: <domain-name> — facade APIs, boundary entities, dependencies"
   /graphify query "what components does <component-name> depend on?"
   ```
   Fall back to reading the full file if the graph is missing or the `graphify check-update docs/` command reports it is stale.

   For Tier 2+: if the LLD does not exist, stop — "LLD required before implementation. Run the Generate Documentation workflow first."

4. **Impact analysis** — read the codebase to identify:
   - Affected endpoints/APIs
   - Affected services/modules
   - Affected infrastructure (manifests, migrations, configs)
   - Affected documentation
   - Affected tests

5. **Documentation plan** — list which HLD/LLD docs need updating and what changes.

6. **Test case plan** — list:
   - New tests to add (name + what they verify)
   - Existing tests to update (file + what changes)
   - Regression tests to confirm still pass

7. **Create `.hitl/current-change.yaml`:**

   ```yaml
   change_id: GH-<issue-number>
   tier: <0|1|2|3|4>
   status: planning
   source_artifacts:
     issue: <url>
     hld: <path or "pending">
     lld: <path or "pending">
   manifest:
     path: docs/system-manifest.yaml
     domain: <domain-name>
   allowed_paths:
     - <source file globs for this domain>
   required_evidence: []
   approvals:
     product: pending
     architecture: pending
   ```

8. **Present the full plan** (impact, doc changes, test plan, execution order) and ask the user to confirm before proceeding. Do not write any code until confirmed.

---

## Developer Role

When implementing a change with an approved context file, follow this process:

### Before Writing Code

1. Read `.hitl/current-change.yaml` — verify `status` is `implementation-approved`.
2. Read the approved LLD at the path in the context file.
3. Get the relevant domain's facade APIs, boundary entities, and cross-cutting conventions. Prefer a graph query if the graph is available — `docs/system-manifest.yaml` is large and the graph surfaces just the relevant slice:
   ```
   /graphify query "domain: <domain-name> facade APIs and boundary entities"
   /graphify query "cross-cutting conventions for <domain-name>"
   ```
   Fall back to reading `docs/system-manifest.yaml` directly if the graph is unavailable.

### During Implementation

- Follow the TDD workflow (below) — tests before implementation code.
- Cite the LLD section each piece of code implements:
  ```python
  # LLD: §3.2 — rate limit handling
  if response.status_code == 429:
      raise RateLimitError(retry_after=response.headers.get("Retry-After"))
  ```
- If implementation reveals an LLD gap, stop: "LLD gap found: [description]. Update the LLD and get re-approval before continuing."
- If implementation requires a design decision not in the LLD, stop: "This requires a design decision not specified in the LLD: [description]. Update the LLD."

### After Implementation

Update `.hitl/current-change.yaml`:
- Add `tests_red: done`
- Add `tests_green: done`
- Update `status: conformance-review-pending`

---

## TDD Workflow

Use after the LLD is approved, before writing any implementation code. This replaces the `/tdd` skill.

**Refusal:** If no LLD exists or is not approved, stop: "No approved LLD found. Write the LLD first — this workflow generates tests FROM the spec, not without one."

### Phase 1 — Generate Tests (RED)

1. Read the LLD for the component.
2. Get the manifest data needed for test generation. Prefer graph queries over reading the full manifest:
   ```
   /graphify query "domain: <domain-name> facade_apis for contract tests"
   /graphify query "domain: <domain-name> boundary_entities and cross_cutting conventions"
   ```
   Fall back to reading `docs/system-manifest.yaml` directly if the graph is unavailable.
   Extract: `facade_apis` → contract tests, `cross_cutting` conventions → convention tests, `boundary_entities` → entity shape tests.
3. Generate maximum coverage:
   - Happy path for every method
   - Error path for every `error_modes` entry
   - Precondition violation tests for every `preconditions` entry
   - Boundary entity shape tests
   - Contract tests from facade APIs
4. Register each test in `docs/03-engineering/testing/test-registry.yaml` with domain, risk level, type (unit/integration/contract), and `origin: tdd`.
5. **Stop.** Present all tests. Ask: "Review the tests above. Add edge cases or domain scenarios I missed. When satisfied, say 'tests approved' to continue."

### Phase 2 — Human Review

Wait for "tests approved" (or equivalent). Do not proceed until the user confirms.

### Phase 3 — Tests Improve Design

For each test that covers behavior the LLD does not describe, flag it and propose an LLD update. Confirm each LLD change with the user before writing it.

### Phase 4 — Verify RED

Run the test suite. All new tests must fail. If any new test passes before implementation, flag it: "This test passed before implementation — it may be testing existing behavior. Investigate before proceeding."

### Phase 5 — Generate Code (GREEN)

Generate the simplest implementation that makes failing tests pass. Do not over-engineer. Present the code for review.

### Phase 6 — Verify GREEN

Run the full suite (new + existing). If existing tests fail, flag as a regression and fix before proceeding.

### Phase 7 — Refactor

Simplify the passing code. After each refactor step, rerun tests. If any test breaks, revert — the refactor changed behavior, not just style.

Mark `tests_red: done` and `tests_green: done` in `.hitl/current-change.yaml`.

---

## Convention Checks

Run before creating a PR. This replaces the `/check-conventions` skill.

**Trigger:** User asks to "check conventions", "run checks", or "verify before PR".

### Run these checks

```bash
# Semgrep (install: pip install semgrep)
semgrep scan --config .semgrep/ --error

# Manifest drift
python tools/manifest-drift/check_manifest_drift.py --source-dirs app/ src/

# Mermaid br tags
find docs/ -name "*.md" -exec python scripts/fix_mermaid_br_tags.py --check {} +
```

Or use the bundled script:
```bash
bash codex/scripts/hitl-conventions.sh
```

### Report results

- **Violations** (must fix before PR): file path, rule ID, what's wrong, suggested fix
- **Warnings** (should fix, not blocking)
- **Passing**: count

For each violation, ask the user if they want you to fix it. Generate fixes following project conventions.

Convention violations are blocking in CI. Catching them here saves a failed CI run.

---

## Spec Conformance Review

Run after implementation is complete, ideally in a fresh conversation without the implementation context. This replaces the `spec-conformance-reviewer` agent.

**Trigger:** User asks to "review conformance", "check implementation against spec", or "run conformance review".

### What to check

1. **Traceability:** For each LLD section — is it implemented? Does the implementation match the spec? Is it tested?
2. **Manifest compliance:**
   - Facade API contracts are kept (method signatures match manifest)
   - Boundary entities have the correct shape (no fields added/removed without manifest update)
   - Domain boundaries respected (no imports from domains not in `depends_on`)
   - Cross-cutting conventions applied (idempotency, validation, error handling)
3. **Drift classification:**
   - **Acceptable drift:** code implements the spec more precisely (document, no code change required)
   - **Gap:** required LLD behavior is missing from code (block merge)
   - **Unintended drift:** code differs from LLD without justification (flag for developer to decide: update docs or fix code)

### Output format

```
## Spec Conformance Review: [change ID]

### PASS / FAIL / FINDINGS PRESENT

### Traceability Table
| LLD Section | Code File:Line | Test | Status |
|-------------|----------------|------|--------|

### Manifest Compliance
| Check | Status | Notes |
|-------|--------|-------|

### Drift Findings
| Finding | Classification | Recommendation |
|---------|---------------|----------------|

### Unresolved Findings (block merge)
- [ ] ...

### Acceptable Findings (document, no block)
- ...
```

If unintended drift is pervasive (more than 3 findings): "Recommend a full architecture review before merge rather than point fixes."

---

## Architecture Review

Run when a design needs review before implementation. This replaces the `architect-reviewer` agent.

**Trigger:** User asks to "review the design", "architect review", or "review HLD/LLD".

### What to check

**HLD:**
- Architecture diagram is accurate and complete
- Integration points are explicit (every external dependency named)
- Security architecture is present (auth, data isolation, secrets)
- Scalability considerations are stated
- No implementation details in HLD (describes WHAT, not HOW)

**LLD:**
- Every method has a signature (parameters, return types, error modes)
- Preconditions are explicit
- Error modes are enumerated
- Manifest facade APIs are updated if new ones introduced
- Cross-cutting conventions apply
- LLD is precise enough to generate tests from without asking questions

**Gate — do not approve for implementation without:**
- [ ] LLD status set to `approved`
- [ ] Manifest facade APIs updated if new ones introduced
- [ ] ADRs written for all tradeoffs
- [ ] Domain boundary is clear and matches the manifest

### Output format

```
## Architecture Review: [feature/component name]

### APPROVED / REVISIONS REQUIRED / BLOCKED

### HLD Assessment
- [PASS/FAIL]: [check] — [notes]

### LLD Assessment
- [PASS/FAIL]: [check] — [notes]

### Manifest Impact
- New facade APIs: [list or "none"]
- Domain boundary changes: [list or "none"]
- Manifest update required: [Yes/No]

### Required Changes Before Implementation
1. [change]
```

---

## Greenfield System Design (New System from PRD)

Run once at project inception when designing a new system from scratch.

**Trigger:** User asks to "design the system", "design system from PRD", "architect design-system", or "start greenfield design".

### Phase 1 — PRD Analysis

1. Read the PRD from the path in $ARGUMENTS or `docs/01-product/prd.md`.
2. Extract: system name, user personas, core use cases (3–5), functional requirements (must-have vs nice-to-have), NFRs (performance, scale, security, compliance), external integrations, tech stack constraints, out-of-scope items, open questions.
3. Flag gaps that will make domain decomposition ambiguous: who owns what data, consistency requirements between capabilities, scale profile.
4. **STOP — ask architect to confirm requirements are complete and resolve gaps before proceeding.**

### Phase 2 — Domain Decomposition

This is the most consequential decision. Do not rush it.

1. Propose candidate domains using these heuristics:
   - Group by **business capability**, not technical layer
   - Separate by rate of change and data ownership
   - Keep transactional boundaries inside a single domain — avoid distributed transactions
   - Each domain should be implementable without knowing the internals of other domains

2. For each domain: name, purpose, what it owns, key responsibilities, explicit exclusions.

3. Build the interaction matrix: for each cross-domain data exchange, specify direction, what data crosses (boundary entity), and sync vs async.

4. Self-challenge before presenting: circular dependencies? Domain doing too many unrelated things? Two domains always changed together?

5. **STOP — ask architect to confirm domain breakdown. This is the only gate where the skill must not proceed without explicit confirmation. Domain boundary errors cascade through every subsequent artifact.**

### Phase 3 — System Manifest

Generate `docs/system-manifest.yaml` from confirmed domains. Follow the schema in `skills/generate-docs/templates/system-manifest.schema.yaml`.

- `files`: empty (no code yet)
- `facade_apis`: propose from PRD, mark ALL as `DRAFT — architect to verify`
- `boundary_entities`: propose from interaction matrix, mark DRAFT
- `lld`: `"pending"` (updated in Phase 6)

**STOP — ask architect to review manifest, especially facade_apis and boundary_entities.**

### Phase 4 — Foundational ADRs

Identify and resolve every decision that blocks HLD generation:

| Decision | Must resolve before |
|---|---|
| Language and framework | LLDs |
| Data storage | Domain schemas |
| Auth/authz approach | Security HLD, all domain LLDs |
| API style (REST/GraphQL/gRPC/events) | API HLD, facade API shapes |
| Deployment model | System architecture HLD |
| Observability stack | Observability HLD, conventions |

For each: create `docs/02-design/technical/adrs/<decision>.md` using `templates/adr-template.md`. For decided: fill decision, ask architect for rationale. For open: list options and tradeoffs, **STOP and ask architect to decide before continuing**.

Update `docs/02-design/technical/adrs/README.md`.

### Phase 5 — System-Level HLDs

Generate from confirmed manifest and ADRs — not from general knowledge:

**Always:**
1. `hld/system-architecture.md` — component topology, deployment model, domain map (Mermaid), external integrations, sequence diagrams for 2–3 critical use cases
2. `hld/data-architecture.md` — storage choices, data ownership per domain, cross-domain access patterns, compliance
3. `hld/security-architecture.md` — auth/authz, data isolation, secrets management, compliance NFRs

**If applicable:**
4. `hld/api-architecture.md` — if external-facing API exists
5. `hld/observability-architecture.md` — if SLA or availability NFRs exist

Update `hld/index.md`. **STOP after each HLD for architect approval. Do not generate LLDs until all HLDs are approved.**

### Phase 6 — Domain-Level LLDs

For each domain in the manifest, generate `docs/02-design/technical/lld/<domain>/<domain>.md`:
- Propose internal structure (services, classes, models) that implements the domain's facade_apis
- Mermaid class diagram, method signatures, sequence diagrams for main flows, error modes, preconditions
- Mark everything DRAFT — design intent, not final

Update `lld/index.md`, `lld/packages.md` (domain dependency diagram), and manifest `lld` paths.

**STOP after each LLD for architect approval.**

### Phase 7 — HITL Process Bootstrap

Follow Phase R5 of the `Generate Documentation` section:
1. Generate `CLAUDE.md` — inline conventions from ADRs
2. Generate `convention-checks.yaml` — checks from Phase 4 conventions
3. Install plugin or copy skills
4. Copy CI actions to `.github/workflows/`
5. Generate `.github/ISSUE_TEMPLATE/technical-change.md`
6. For systems with 4+ domains: install Graphify (`pip install graphifyy && graphify install`)
7. Generate `docs/README.md`

### Output format

```
SYSTEM DESIGN COMPLETE — [System Name]
Domains: N  |  HLDs: N  |  LLDs: N  |  ADRs: N

Artifacts:
  System manifest:   docs/system-manifest.yaml
  HLDs:              docs/02-design/technical/hld/
  LLDs:              docs/02-design/technical/lld/
  ADRs:              docs/02-design/technical/adrs/
  CLAUDE.md:         repo root
  Convention checks: convention-checks.yaml
  Graphify:          [installed / not required]

Needs architect attention before first feature:
  • Facade API blurbs (DRAFT): N fields
  • Boundary entity shapes (DRAFT): N fields
  • ADR rationale sections: N docs

Next: /architect/design-feature for first change
      First implementations will correct DRAFT fields
```

---

## Architect Design Journey (Steps 3–9)

Run when the architect is starting a new change and needs to drive the full design phase — from impact analysis through to decision packets ready for developer handoff.

**Trigger:** User asks to "design feature", "run the design phase", "architect design-feature", or "steps 3 through 9".

This section covers everything from impact analysis through decision packet assembly. Use the `Architecture Review` section (above) for the narrower case of reviewing existing design docs.

### Phase 1 — Impact Analysis and Scope

1. Fetch the GitHub issue. If no issue exists, stop: "Create a GitHub issue first with `gh issue create`."
2. Read the system manifest — prefer a graph query:
   ```
   /graphify query "all domains and facade APIs"
   /graphify query "domain: <candidate> facade APIs boundary entities"
   ```
   Fall back to `docs/system-manifest.yaml` directly.
3. Check incident history for candidate domains — prefer a graph query:
   ```
   /graphify query "past incidents affecting domain: <domain-name>"
   ```
   Fall back to `docs/04-operations/incident-registry.yaml`.
4. Identify affected domains, facade API changes, boundary entity changes, IaC scope, and backwards compatibility.
5. Determine tier (from `skills/dev-practices/SKILL.md`). Challenge scope: cross-domain or multi-service changes are Tier 3 even when described as simple.
6. Estimate effort and token cost (phase-level formula from `skills/dev-practices/roi-estimation.md`).
7. Initialize or update `.hitl/current-change.yaml` with `status: planning`.
8. **STOP — present impact summary and ask architect to confirm scope and tier.**

### Phase 2 — ROI Trigger (Step 4)

If effort > 1 day: draft ROI section for the GitHub issue from `skills/dev-practices/roi-estimation.md`. Ask architect to fill in the baseline metric now — it cannot be estimated after the fact.

### Phase 3 — HLD (Step 5, Part 1)

For Tier 2+:
- Generate HLD at `docs/02-design/technical/hld/<feature>.md` following the `Generate Documentation` section below.
- Update `docs/02-design/technical/hld/index.md` and `source_artifacts.hld` in `.hitl/current-change.yaml`.
- **STOP — ask architect to approve HLD.** Do not generate LLDs until approval.

### Phase 4 — ADR Capture (Step 5, Part 2)

After HLD approval:
- Identify every design decision in the HLD.
- Create ADR stubs at `docs/02-design/technical/adrs/<decision>.md` using `templates/adr-template.md`. Mark as "DRAFT — architect to complete rationale."
- Ask architect: "Are there decisions being made here that aren't visible in the design?"

### Phase 5 — LLD per Domain (Step 5, Part 3)

For each affected domain:
- Generate LLD following the `Generate Documentation` section below.
- **STOP after each LLD — ask architect:** "Is this precise enough to generate tests from?"
- Update `source_artifacts.lld` in `.hitl/current-change.yaml` after each approval.

### Phase 6 — IaC Planning (Step 6)

If IaC changes were identified: list specific files, what changes, and reversibility. Record in `.hitl/current-change.yaml` under `iac_plan`. If none: state so explicitly.

### Phase 7 — Slice Decomposition

This is the architect's core parallelization decision — no default behavior, requires explicit reasoning.

For each affected domain, propose a slice. For each pair of slices:
- Do they share mutable state, database tables, or external API contracts?
- Can both be deployed to production independently?

Mark slices with ordering dependencies as **SEQUENTIAL**. Mark fully independent slices as **PARALLEL OK**.

**STOP — present slice plan and ask architect to confirm.** Do not assemble packets until the slice plan is confirmed.

### Phase 8 — Test Case Planning (Step 7)

For each confirmed slice, using the approved LLD, produce:

| Action | Test name | What it covers |
|--------|-----------|----------------|
| ADD | `test_<scenario>` | [behavior from LLD] |
| UPDATE | `test_<existing>` | [what changes] |
| REMOVE | `test_<obsolete>` | [why] |
| VERIFY | `test_<existing>` | [regression check] |

Check incident registry for the domain (graph-first). Add regression tests for any relevant incidents.

Record the test plan in `.hitl/current-change.yaml` under `tests.plan`.

### Phase 9 — Training Plan Stub (Step 8, conditional)

Training required for: new architectural pattern, new external system, new framework, new ML/AI technique, significant mental-model-changing refactor.

Not required for: new endpoints on existing patterns, bug fixes, model-preserving refactors.

If required: create stub at `docs/03-engineering/training/<capability>.md` using `templates/training-plan-template.md`.

### Phase 10 — Decision Packet Assembly (Step 9)

For each confirmed slice, generate `docs/decisions/issue-<N>-slice-<M>.yaml` (or `docs/decisions/issue-<N>.yaml` for single-slice) using `templates/decision-packet-template.yaml`. Fill all fields: issue, domain (one only), LLD path, HLD path, ADR paths, IaC plan, test plan, rollout risk, ROI flag, impact brief placeholders.

**STOP after each packet — ask architect to approve.** After all packets approved:
- Set `approvals.architecture: approved` in `.hitl/current-change.yaml`
- Set `status: implementation-approved`

### Output format

```
DESIGN COMPLETE — GH-<N>: [title]
Tier: N  |  Slices: M  |  Est. effort: N days

Artifacts:
  HLD: docs/02-design/technical/hld/...
  LLDs: N files
  ADRs: N stubs (architect to fill rationale)
  Decision packets: N files
  Training stub: [path or "not required"]
  .hitl context: implementation-approved

Slice handoff:
  Slice 1: domain [A] [PARALLEL OK]
    LLD: docs/.../lld/[A]/...
    Packet: docs/decisions/issue-<N>-s1.yaml
  Slice 2: domain [B] [SEQUENTIAL — after slice 1]
    LLD: docs/.../lld/[B]/...
    Packet: docs/decisions/issue-<N>-s2.yaml

Next: assign packets to developers; each runs /tdd with their LLD path
```

---

## QA Review

Run after the TDD cycle is complete, before creating a PR.

**Trigger:** User asks to "QA review", "review test coverage", or "verify tests".

### What to check

1. Every acceptance criterion from the GitHub issue has at least one test
2. Every LLD error mode has a test
3. Every LLD precondition has a violation test
4. Incident regressions are present — prefer a graph query:
   ```
   /graphify query "past incidents affecting domain: <domain-name>"
   ```
   Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. Do not assume the registry is empty — actively query it.
5. Tests assert on behavior, not implementation (test names describe scenarios)
6. Tests are independent (no shared mutable state)
7. External APIs mocked; internal logic not mocked
8. All new tests registered in the test registry with domain, risk, type, and origin
9. Incident regression tests have `incident_ref` set

### Output format

```
## QA Review: [feature/component name]

### APPROVED / REVISIONS REQUIRED

### Acceptance Criteria Coverage
| AC | Test(s) | Status |
|----|---------|--------|

### LLD Edge Case Coverage
| Edge case | Test | Status |
|-----------|------|--------|

### Incident Regression Check
| Incident | Test | Status |
|----------|------|--------|

### Test Quality Issues
- ...

### Tests to Add
- [test name]: [what it covers]

### Test Registry Status
- [ ] All new tests registered
- [ ] Incident refs set on regression tests
```

---

## Generate Documentation

Run before implementation on any Tier 2+ change. This replaces the `/generate-docs` skill.

**Trigger:** User asks to "generate docs", "write HLD/LLD", or "create design documents".

### New Feature Mode

1. Determine the feature name (kebab-case).
2. Create `docs/02-design/technical/hld/<feature-name>.md` using `templates/hld-template.md` (installed by `codex/install.sh`). Must include: executive summary, Mermaid architecture diagram (`graph TB`), component overview, data flow sequence diagrams, integration points, security architecture, scalability considerations.
3. Update `docs/02-design/technical/hld/index.md`.
4. **Stop — ask the user to review and approve the HLD** before creating the LLD.
5. After HLD approval, create LLD files under `docs/02-design/technical/lld/` using `templates/lld-component-template.md` (installed by `codex/install.sh`). Include Mermaid class and sequence diagrams, method signatures, error modes, preconditions, and usage examples.
6. Update `docs/02-design/technical/lld/index.md` and `packages.md`.

All diagrams must use Mermaid. No `<br/>` tags inside Mermaid blocks.

### Reverse-Engineer Mode

If the user says "reverse engineer", "existing codebase", or "brownfield": read existing code and produce HLD/LLD/ADR docs that reflect what is actually there. Do not invent behavior not present in the code.

---

## Before Creating a PR

Verify all of the following:

- [ ] `.hitl/current-change.yaml` status is `conformance-review-pending` or later
- [ ] Convention checks pass (zero semgrep violations)
- [ ] All new tests pass
- [ ] No regressions in existing tests
- [ ] LLD is up to date (no unresolved drift from conformance review)
- [ ] Downstream impact brief exists (run `/impact-brief` or ask Codex to generate one)
- [ ] PR description includes: GitHub issue link, HLD/LLD links, test plan summary, rollout notes

---

## Session End

When you finish a session (user says "done", "that's all for now", or similar), summarize:

- Files changed this session
- Current HITL context status (change_id, tier, status from `.hitl/current-change.yaml` if it exists)
- Evidence checklist status (from `required_evidence` in the context file)
- Next steps to complete before the PR

A git post-commit hook also writes `docs/session-logs/hitl-session-<change-id>-<timestamp>.md` automatically on each commit.

---

## Knowledge Graph (Graphify)

The HITL platform integrates Graphify to reduce token cost when querying design docs. On large projects, the full doc set (HLDs + LLDs + system-manifest + ADRs) can exceed the context window. The graph gives you relevant nodes without reading whole files.

### Setup (one-time per project)

```bash
# Install
pip install graphifyy && graphify install

# Build the initial graph (run from project root)
graphify . --directed --no-viz

# Start the MCP server (keep running in a separate terminal)
python3 -m graphify.serve graphify-out/graph.json
```

`.mcp.json` is created by `codex/install.sh` — it wires the MCP server so Codex can call `query_graph`, `get_node`, and `get_neighbors` as tools.

### Keeping the graph current

The PostToolUse hook (`rebuild-graph.sh`) triggers an incremental rebuild automatically after every design doc write. Code file writes do not trigger a rebuild.

To verify the graph is fresh before querying:
```bash
graphify check-update docs/
```

To rebuild manually:
```bash
graphify . --update --no-viz --directed
```

### When to use the graph vs read files directly

| Situation | Use graph | Read file directly |
|---|---|---|
| Finding which domain a component belongs to | ✓ | |
| Getting facade APIs for a domain | ✓ | |
| Tracing cross-component dependencies | ✓ | |
| Checking existing test coverage for a domain | ✓ | |
| Finding past incidents for a domain | ✓ | |
| Getting test strategy constraints for a domain | ✓ | |
| Reading full method signatures from an LLD | | ✓ |
| Verifying a specific precondition or error mode | | ✓ |
| Reading the full test registry to register a new test | | ✓ |
| Graph is missing or stale | | ✓ |

---

## Important Notes for Codex Users

Enforcement runs at two levels. Use both for the strongest guarantees:

### Codex lifecycle hooks (preferred — same timing as Claude Code)

When `codex_hooks = true` is set in `.codex/config.toml`, Codex loads `.codex/hooks.json` and runs HITL context checks before each Write/Edit and boundary checks after — the same real-time enforcement as Claude Code's PreToolUse/PostToolUse hooks.

Both files are installed by `codex/install.sh`. The hook scripts live in `codex/hook-scripts/`.

### Git hooks (portable fallback)

The `pre-commit` hook blocks commits on source files when no `.hitl/current-change.yaml` exists, and warns (or blocks in strict mode) on domain boundary violations.

Enable strict mode to match the full HITL enforcement rules:
```bash
git config hitl.strict true   # project-level
# or
HITL_STRICT=1 git commit ...  # one-off
```

Strict mode additionally blocks Tier 2+ commits without `implementation-approved` status and blocks boundary violations.

### Install everything

```bash
bash /path/to/hitl-dev-platform/codex/install.sh
```
