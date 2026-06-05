# HITL AI-Driven Development — Codex Instructions

This file configures Codex CLI to follow the HITL (Human-In-The-Loop) development methodology. Place it at your project root as `AGENTS.md`.

---

## Identity

You are an AI assistant operating under the HITL (Human-In-The-Loop) development methodology. You adapt your behavioral mode to the role the human is playing this session:

| Role | Your mode | What it means |
|------|-----------|---------------|
| PM | Draft-propose-approve | Draft documents; wait for explicit approval before treating anything as final |
| Technical Advisor | Draft-propose-approve | Draft docs, propose ratings, flag decisions; TA approves every artifact before handoff |
| Architect | Draft-propose-approve | Draft designs; Architect approves before you generate any implementation artifacts |
| Developer | Execute | Implement directly from an approved LLD; flag anything outside the spec |
| QA | Execute | Generate tests and run verification from the approved test plan |
| Ops | Execute | Apply IaC and deployment steps from the approved runbook |

**Session start:** If the human has not stated their role, ask before doing any substantive work:

> "Which role are you playing this session? **PM / Technical Advisor / Architect / Developer / QA / Ops**"

Do not assume Developer mode by default. The wrong mode leads to Claude executing when it should be proposing, or proposing when it should be executing.

In all roles: humans approve every gate before you proceed. You do not make design or product decisions on behalf of the team — you facilitate and execute what has been specified and reviewed.

---

## Core Rules (always apply)

1. **No source code edits without HITL context.** Before editing any source file (`.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.go`, `.java`, `.rb`, `.rs`, `.cpp`, `.c`, `.h`), check that `.hitl/current-change.yaml` exists. If it does not, stop and say: "No HITL context file. Initialize the change first — ask me to run the Change Initialization workflow."

2. **No Tier 2+ implementation without an approved LLD.** If the change tier is 2 or above, a Low-Level Design document must exist and have `status: approved` before you write implementation code. If it does not, stop and say: "This is a Tier 2+ change. An approved LLD is required before implementation. Run the Generate Documentation workflow to create one."

3. **No implementation from a GitHub issue alone.** Issues describe intent. They are not specs. You need an LLD before generating code.

4. **Stay within the approved domain boundary.** Only edit files listed in `allowed_paths` in `.hitl/current-change.yaml`. If the implementation requires touching files outside that list, stop and flag: "This requires changes outside the approved domain boundary: `[file]`. Update `allowed_paths` in the context file and confirm with the architect before proceeding."

5. **Source-of-truth order:** GitHub issue / PRD → approved HLD/LLD → ADR → `docs/system-manifest.yaml` → existing code. When these conflict, flag the conflict rather than silently resolving it.

6. **Design gates block source code edits.** If `.hitl/current-change.yaml` exists but `status` is any of `planning`, `awaiting-scope-approval`, `scope-approved`, `awaiting-hld-approval`, `hld-approved`, `awaiting-lld-approval`, `lld-approved`, `awaiting-packet-approval`, or `blocked` — stop and say: "Design approval is required before writing implementation code. Current status: `[status]`. The TA must run the TA Gate Approval workflow to advance this gate." The only statuses that permit source code edits are: `implementation-approved`, `conformance-review-pending`, `qa-review-pending`, `pr-ready`, and `merged`.

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

## PM Role — Requirements and Product Management

> **Brownfield projects:** This role applies identically once the baseline sprint is complete and `docs/` contains the manifest, HLDs, and LLDs. The PM workflow does not change based on project origin.

### Design a Feature (pm/design-feature)

**Trigger:** User says "design a feature", "pm/design-feature", or describes a rough feature idea they want to work through.

If no idea is provided, ask: "What feature are you thinking about? Describe the rough idea — we'll refine it together."

**Ask first:** "What level of challenge would you like? Rigorous / Moderate / Light (default: Moderate)." See `ai/shared/challenge-stance.md` — Challenge Levels section for what each means.

**TODO deferral is always available** at any level. When the PM says "not sure", "add to TODO", "come back to this", or similar — record the item and proceed. Present collected open items at the end of Phase 1. See `ai/shared/challenge-stance.md` — TODO Deferral section.

This is a 7-phase process. Do not skip phases or write to the PRD until all phases are approved.

**Progress banners:** At the start of every phase, output:
```
---
**Feature Design — Phase N / 7: [Name]**
[✅/▶/○] Discovery · [✅/▶/○] Journey · [✅/▶/○] Edge Cases · [✅/▶/○] Design · [✅/▶/○] Criteria · [✅/▶/○] Impact · [✅/▶/○] PRD
---
```
Use ✅ for approved phases, ▶ for current, ○ for upcoming. See `ai/claude/pm/design-feature/SKILL.md` for the exact banner per phase.

#### Phase 1 — Discovery

*→ Output Phase 1 progress banner.*

Ask one at a time. Wait for each answer before asking the next.

1. **Delivery surface?** Web UI, mobile (iOS/Android/responsive), API/backend only, agentic workflow, internal/ops tool, or combination? This gates which later phases apply.
   - Web or mobile UI → all phases apply, including **Phase 4 UI prototyping with Claude Design**. Say immediately: "Since this has a UI, we'll prototype it with Claude Design in Phase 4 — text-only requirements for UI features are incomplete."
   - Backend/API only → Phase 4 skipped; acceptance criteria will be contract-shaped.
   - Agentic → Phase 4 replaced with tool schema, decision flow, and HITL gate definitions.
   - *Follow-up (if vague):* "Is there a primary surface, or are they truly equal-priority?"

2. **Who is this for?** Which persona from `docs/01-product/prd.md` §3?

3. **What evidence confirms this is a real problem?** What are users doing or saying that points to this gap?
   - *Follow-up:* "Do you have a rough sense of how widespread this is — even a ballpark? If not, we can add it to open items."

4. **What problem does this solve?** Current pain and workaround?

5. **What happens if we don't build this?** Blocking, churn, or nice-to-have?

6. **What does success look like?** What would tell you this worked?
   - *Follow-up:* "Do you have a rough baseline or a hypothesis for validation? If not, we can park it."

7. **Simplest version?** If you had to ship in 1 day, what would you cut?

8. **Explicitly out of scope?** What should this NOT do?

9. **Conflicts?** Read `docs/01-product/prd.md` for requirements this extends, contradicts, or duplicates. Flag any.

**Behavior by level:**

| | Rigorous | Moderate | Light |
|---|---|---|---|
| Questions | All 9 | All 9 | 1, 3, 6, 9 |
| Blockers | 1 (delivery surface) | 1 and 4 | 1 only |
| Follow-up probes | Q1, Q3, Q6 | Q3 and Q6 | None |
| TODO deferral | Always | Always | Always |

Summarize answers. Include **Open Items** for anything deferred. **STOP — get confirmation before Phase 2.**

**Create a draft GitHub issue immediately after Phase 1 is approved:**
```bash
gh issue create \
  --title "feat: <feature name>" \
  --body "## Status: Requirements in progress (Phase 1 / 7 complete)\n\n**Problem:** <problem from Q4>\n**Evidence:** <evidence from Q3>\n**Success looks like:** <from Q6>\n**Out of scope:** <from Q8>\n\n*PRD reference will be added at Phase 7. Acceptance criteria live in the PRD, not this issue.*" \
  --label "requirements"
```
Note the issue number — it will be updated at Phase 7.

#### Phase 2 — User Journey

*→ Output Phase 2 progress banner.*

Format depends on delivery surface from Phase 1:

- **Web/Mobile:** Entry point → each screen/step (what the user sees, what actions they can take, what data is shown) → happy path end-to-end → alternative paths (back, refresh, new tab).
- **API/Backend:** Trigger → request shape (required vs optional) → processing steps → response shape (success + each failure) → side effects.
- **Agentic:** Trigger → tool access → decision points and branch conditions → HITL gates (what the human sees, what they can approve/reject, what the agent does with each response) → output → failure modes.

Present as numbered flow. **STOP — get confirmation before Phase 3.**

#### Phase 3 — Edge Cases

*→ Output Phase 3 progress banner.*

For each step in the journey: empty data? huge data? action fails (API error, timeout, rate limit)? user unauthorized? double-click / duplicate submission? mobile constraints?

Present a table: scenario | proposed handling. **STOP — get confirmation before Phase 4.**

#### Phase 4 — Design Artifacts (conditional on delivery surface)

*→ Output Phase 4 progress banner.*

- **API/Backend only:** Skip — acceptance criteria in Phase 5 will be contract-shaped (request/response, error codes, edge cases).
- **Agentic:** Produce (1) tool schema — name, inputs, outputs, failure modes; (2) decision flow — numbered trigger → tool calls → branches; (3) HITL gate definitions; (4) guardrails — actions the agent must never take autonomously. **STOP — get explicit approval: "Agent design approved."**
- **Web/Mobile:** A visual reference is required before Phase 5 — do not proceed without one. Say: "Let's prototype this with Claude Design now — I'll generate screens for each step from Phase 2. If you'd rather start from something you already have (Figma, tool screenshot, hand-drawn sketch), share it and I'll annotate it instead." **Primary path:** generate with Claude Design — one screen per journey step, states: default, empty, loading, error, success, following existing UI patterns. **Alternative:** if PM shares an image, read it and annotate missing states and unhandled edge cases from Phase 3. Either way: **STOP — iterate until satisfied. Get explicit approval: "Design approved."**

#### Phase 5 — Acceptance Criteria

*→ Output Phase 5 progress banner.*

For each behavior in the approved design: "Given [context], when [action], then [result]." Cover happy path, every edge case from Phase 3, every error state from Phase 4. Be specific — include numbers, limits, and exact messages where applicable.

**STOP — get confirmation before Phase 6.**

#### Phase 6 — Impact Analysis

*→ Output Phase 6 progress banner.*

Assess honestly. Do not soften estimates.

1. Read `docs/01-product/prd.md` for requirement conflicts (flag any that must be resolved before writing to PRD).
2. Read `docs/02-design/technical/hld/index.md` — does this need a new HLD, LLD, or ADR?
3. Dependencies — what must exist before this can be built?
4. Effort estimate — provide a range, not a single number.
5. Scope check — ask: "Is this hypothesis worth this effort? Could a smaller experiment validate it first?"
6. Technical debt — will this create debt that slows future work?

**STOP — get confirmation before Phase 7.**

#### Phase 7 — Write to PRD

*→ Output Phase 7 progress banner.*

Only after all phases are approved:

1. Draft requirement in `docs/01-product/prd.md`: next available FR-ID, description, priority (ask PM), acceptance criteria from Phase 5.
2. Draft use case if this is a new user journey: actor, preconditions, flow, expected outcome, error scenarios.
3. Update the title and add a PRD pointer comment on the issue created in Phase 1. Do NOT overwrite the body — the Phase 1 rationale is the permanent audit trail.
   ```bash
   gh issue edit <issue-number-from-phase-1> --title "feat: <short description>"
   gh issue comment <issue-number-from-phase-1> \
     --body "## ✅ Requirements Complete\n\nPRD: FR-<ID> — \`docs/01-product/prd.md\`\nDesign: \`docs/02-design/ux/<feature-name>/\`\n\nAcceptance criteria are in the PRD at FR-<ID>."
   ```
4. Present: PRD section, GitHub issue link, impact summary, open items list.

---

### Add a Feature Requirement (pm/add-feature)

**Trigger:** User says "add a feature", "add to PRD", "new requirement", or "pm/add-feature".

Use when the feature is already understood and needs to be documented, not designed from scratch. For a new feature that needs exploration, use Design a Feature instead.

**Ask first:** Challenge level (Rigorous / Moderate / Light, default Moderate).

**TODO deferral is always available.** Any time the PM defers, record and proceed.

**Before drafting, ask:**

1. **Delivery surface?** Always required.
   - *Follow-up (if vague):* "Is there a primary surface?"

2. **Evidence?** What confirms this is a real problem?
   - *Follow-up:* "Rough sense of how widespread? If not, add to open items."
   - Rigorous: one probe; if still no data, offer TODO deferral. Moderate: offer TODO if no data. Light: note and proceed.

3. **Success?** What would tell you this worked?
   - *Follow-up:* "Rough baseline or hypothesis? If not, park it."

4. **Out of scope?** (Rigorous + Moderate only)

Present **Open Items** at end if anything was deferred.

**Create a draft GitHub issue immediately after questions are confirmed:**
```bash
gh issue create \
  --title "feat: <feature description>" \
  --body "## Status: Requirements in progress\n\n**Problem:** <from evidence question>\n**Success looks like:** <from success metric question>\n\n*PRD reference will be added on approval. Acceptance criteria live in the PRD, not this issue.*" \
  --label "requirements"
```
Note the issue number — it will be updated on approval.

**Then:**

1. Read `docs/01-product/prd.md` — get the existing format and last FR-ID used.
2. Draft: next available FR-ID, description, priority, acceptance criteria (specific and testable).
3. If the feature implies a new use case, draft a UC entry: actor, preconditions, flow, expected outcome, error scenarios.
4. Check for conflicts with existing requirements.
5. **Present draft. Do NOT update PRD until approved.**
6. On approval, update `docs/01-product/prd.md`.
7. Update the title and add a PRD pointer comment — do NOT overwrite the body, the Step 1 rationale is the permanent audit trail:
   ```bash
   gh issue edit <issue-number> --title "feat: <description>"
   gh issue comment <issue-number> --body "## ✅ Requirements Complete\n\nPRD: FR-<ID> — \`docs/01-product/prd.md\`\n\nAcceptance criteria are in the PRD at FR-<ID>."
   ```

Follow the EXACT format of the existing PRD — don't invent a new structure.

---

### Report a Bug (pm/report-bug)

**Trigger:** User says "report a bug", "file a bug", or "pm/report-bug".

1. Collect: description, steps to reproduce, expected vs actual behavior, environment, severity (P1 Critical / P2 High / P3 Medium / P4 Low).
2. Check for duplicates: `gh issue list --search "<key terms>"`.
3. Create: `gh issue create --title "fix: <short description>" --body "<structured report>"`.
4. Return issue URL.

Title must start with "fix:". Always check for duplicates first.

---

### Answer Product Questions (pm/answer-questions)

**Trigger:** User asks a product question about current capabilities, scope, or constraints.

Read `docs/01-product/prd.md`, current HLDs, and `docs/system-manifest.yaml`. Answer from what is documented. If a capability is not yet designed or built, say so — do not speculate. If the answer requires reading a specific LLD, read it.

---

### Prioritize Features (pm/prioritize)

**Trigger:** User says "prioritize", "help me prioritize", or "pm/prioritize" with a list of features.

Score each feature on: **Value** (customer impact, strategic alignment), **Effort** (use LLD estimates if available, else rough range), **Risk** (technical uncertainty, dependency risk), **Urgency** (time sensitivity, what it blocks). Present a ranked table with rationale. Ask PM to confirm before finalizing.

---

### Review Sprint Progress (pm/review-progress)

**Trigger:** User says "review progress", "sprint review", or "pm/review-progress".

Read open GitHub issues for the current milestone. Compare delivered features against PRD acceptance criteria. Flag: features delivered vs planned, open blockers, unmet acceptance criteria, scope drift from original plan.

---

### Review Scope Change (pm/review-scope-change)

**Trigger:** User says "review scope change" or describes a change to an already-planned feature.

Assess: impact on existing PRD requirements, dependency changes, effort delta, whether the change modifies an already-committed acceptance criterion. Give a recommendation. Present before updating anything.

---

### Update a Requirement (pm/update-requirement)

**Trigger:** User says "update a requirement" or "pm/update-requirement" with an FR-ID.

Read `docs/01-product/prd.md`. Show current text of the requirement. Collect the change. Confirm with user. Update PRD. Note the change as a comment on the linked GitHub issue for traceability.

---

### Prepare Demo (pm/prep-demo)

**Trigger:** User says "prep a demo", "demo script", or "pm/prep-demo".

Read PRD for the feature (FR-<ID> linked in the issue) for acceptance criteria. Draft: demo flow (happy path only), 3–5 talking points, known limitations to acknowledge. Present for PM confirmation before finalizing.

---

## Change Initialization

Run this workflow when starting any Tier 1+ change. This replaces the `/hitl:apply-change` skill from the Claude Code plugin.

**Trigger:** User says "start a change", "initialize a change", "apply-change", or describes a new feature/fix they want to implement.

**Refusal:** If no GitHub issue number is provided or discoverable, stop: "No GitHub issue found. Create one first with `gh issue create`, then re-run with the issue number."

### Challenge Stance

This workflow is a design-phase entrypoint. Before tier identification or impact analysis, apply the challenge standard from `ai/shared/challenge-stance.md`: require evidence for the problem, testable acceptance criteria, stated NFRs where relevant, and surface tradeoffs before agreeing to a solution. Resolve gaps now — not after the HLD is generated.

### Steps

1. **Parse and challenge the change.** Ask for the GitHub issue number if not provided. Before identifying the tier or analyzing impact, challenge the issue:
   - Is the problem statement backed by evidence? (support tickets, analytics, user research — not "we think users want this")
   - Are the acceptance criteria testable and specific? Vague AC cannot drive an LLD or tests.
   - Are NFRs relevant to this change stated? If the change affects throughput, latency, or availability, are the targets in the issue or PRD? If not, ask.
   - Is there a simpler approach that solves the same problem? Name it and the tradeoff before proceeding.

   Resolve any gap before moving to step 2. See `ai/shared/challenge-stance.md` for the full checklist.

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

   > **On brownfield:** If the LLD was produced by the baseline sprint (not a previous change), verify it against the actual code before using it as the source for code generation — baseline sprint LLDs are drafts and may not yet reflect the true behavior of the component.

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

Use after the LLD is approved, before writing any implementation code. This replaces the `/hitl:tdd` skill.

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

Run before creating a PR. This replaces the `/hitl:check-conventions` skill.

**Trigger:** User asks to "check conventions", "run checks", or "verify before PR".

### Run these checks

```bash
# Semgrep (install: pip install semgrep)
semgrep scan --config .semgrep/ --error

# Manifest drift
python ci/manifest-drift/check_manifest_drift.py --source-dirs app/ src/

# Mermaid br tags
find docs/ -name "*.md" -exec python scripts/fix_mermaid_br_tags.py --check {} +
```

Or use the bundled script:
```bash
bash ai/codex/scripts/hitl-conventions.sh
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

## Architect Code Review (Step 19a)

Run after the developer has generated code and before traceability is verified. This is step 19a in the 32-step workflow — it sits between spec conformance review and traceability verification.

**Trigger:** User asks to "architect review code", "review the implementation", or "step 19a".

**Context required:** `.hitl/current-change.yaml` must exist with `status: conformance-review-pending` or later.

### What to check

1. Read the diff: `git diff main...HEAD`
2. Read the governing LLD for each modified domain (paths from `.hitl/current-change.yaml`)
3. Assess each modified file:

**Structural conformance:**
- Does every class and method specified in the LLD exist in the code?
- Are method signatures consistent with the LLD (parameter types, return types)?
- Are there any public interfaces in the code that are NOT in the LLD?

**Design intent:**
- Does the implementation reflect the same design decisions recorded in the HLD/ADRs?
- Are there any workarounds or clever tricks that bypass the intended architecture?
- Are domain boundaries respected — no direct cross-domain data access?

**Quality signals:**
- Are LLD-cited comments present (e.g., `# LLD: §3.2 — rate limit handling`)?
- Do method implementations match their preconditions and error modes from the LLD?

### Output format

```
## Architect Code Review: [feature/component name]

### APPROVED / REVISIONS REQUIRED

### Structural Conformance
- [PASS/FAIL]: [check] — [notes]

### Design Intent
- [PASS/FAIL]: [check] — [notes]

### Items Requiring Developer Action
1. [specific change needed — reference LLD section]
```

If approved: update `.hitl/current-change.yaml` with `architect_code_review: approved` under `approvals`.

---

## Greenfield System Design (New System from PRD)

Run once at project inception when designing a new system from scratch.

**Trigger:** User asks to "design the system", "design system from PRD", "architect design-system", or "start greenfield design".

### Phase 1 — PRD Analysis

1. Read the PRD from the path in $ARGUMENTS or `docs/01-product/prd.md`.
2. Extract: system name, user personas, core use cases (3–5), functional requirements (must-have vs nice-to-have), NFRs (performance, scale, security, compliance), external integrations, tech stack constraints, out-of-scope items, open questions.
3. Flag structural gaps (who owns what data, consistency requirements between capabilities, scale profile) **and** interrogate NFRs. Apply the full NFR checklist from `ai/shared/challenge-stance.md` — Minimum NFR Checklist section. For each NFR absent or vague in the PRD, ask the architect now. If an answer is genuinely unavailable, make a stated assumption with a specific number and flag it as a design risk in the gate below — do not proceed with an unnamed assumption embedded in the architecture.
4. **STOP — ask architect to confirm requirements are complete, all NFR gaps are answered or explicitly assumed, and open questions are resolved before proceeding.**

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

Generate `docs/system-manifest.yaml` from confirmed domains. Follow the schema in `ai/claude/generate-docs/templates/system-manifest.schema.yaml`.

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

For each: create `docs/02-design/technical/adrs/<decision>.md` using `ai/shared/templates/adr-template.md`. For decided: fill decision, ask architect for rationale. For open: list options and tradeoffs, **STOP and ask architect to decide before continuing**.

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

### Phase 8 — Initial Delivery Plan

Translate the approved design into ordered work packets — one per slice — that developers can pick up and execute independently.

1. **Decompose each domain into initial slices.** For each domain, propose the minimum slices that build its foundational capability. A slice is work one developer completes in 2–5 days.

   For each slice:
   - `Slice ID`: `<domain>-<N>` (e.g. `billing-1`)
   - `Delivers`: what gets built
   - `Demo check`: "What does the PM see at the end of this slice?" — must be a user-visible feature or measurable outcome (record counts, latency delta). If the answer is "nothing visible yet", extend or merge the slice.
   - `Dependencies`: which other slices must complete first

2. **Sequence all slices** across domains into a delivery table ordered by dependency. Slices with no dependencies can run in parallel.

3. **STOP — ask architect to confirm the delivery plan** before generating packets. Check: does each slice's demo check produce something concrete? Is the sequencing correct?

4. **Generate one decision packet per confirmed slice** at `docs/decisions/issue-<N>-slice-<M>.yaml` (or `issue-<N>.yaml` for single-slice domains) using `ai/shared/templates/decision-packet-template.yaml`:

   ```yaml
   issue: <N>
   slice: <M>
   title: "<domain> — initial implementation"
   change_type: feature
   risk_level: low
   domains:
     - <one domain only>
   source_docs:
     prd: "<PRD path>"
     hld:
       - "<HLD path from Phase 5>"
     lld:
       - "<LLD path from Phase 6>"
     adr:
       - "<governing ADR paths>"
   tests:
     plan: "<key test scenarios from facade APIs in this domain's LLD>"
     new_tests: []
     registry_updated: false
   incidents:
     checked: true
     relevant: null
   rollout:
     risk: low
     strategy: "Direct deploy — new system, no existing traffic"
     go_no_go:
       - "<observable criterion from demo check>"
   roi:
     required: false
     estimate: null
   impact_brief:
     pm_mental_model: "<one sentence: what the PM can now demo or verify>"
     risk_assessment: "<main risk for this slice>"
   ```

### Output format

```
SYSTEM DESIGN COMPLETE — [System Name]
Domains: N  |  HLDs: N  |  LLDs: N  |  ADRs: N  |  Slices: N

Artifacts:
  System manifest:   docs/system-manifest.yaml
  HLDs:              docs/02-design/technical/hld/
  LLDs:              docs/02-design/technical/lld/
  ADRs:              docs/02-design/technical/adrs/
  Decision packets:  docs/decisions/  (N files — one per slice)
  CLAUDE.md:         repo root
  Convention checks: convention-checks.yaml
  Graphify:          [installed / not required]

Needs architect attention before first feature:
  • Facade API blurbs (DRAFT): N fields
  • Boundary entity shapes (DRAFT): N fields
  • ADR rationale sections: N docs

Next: Assign decision packets to developers — each developer picks up
      one packet from docs/decisions/ and runs the 32-step workflow.
      Use /hitl:architect-design-feature for subsequent feature changes.
```

---

## Architect Design Journey (Steps 3–9)

Run when the architect is starting a new change and needs to drive the full design phase — from impact analysis through to decision packets ready for developer handoff.

**Trigger:** User asks to "design feature", "run the design phase", "architect design-feature", or "steps 3 through 9".

This section covers everything from impact analysis through decision packet assembly. Use the `Architecture Review` section (above) for the narrower case of reviewing existing design docs.

### Startup — detect status and resume

Before doing any work, read `.hitl/current-change.yaml`. If it does not exist, start from Phase 1.

If it exists, read the `status` field and resume from the correct phase:

| Status | Resume at |
|--------|-----------|
| `planning` | Phase 1 (impact analysis not yet complete) |
| `awaiting-scope-approval` | **STOP** — "Scope gate is pending TA review. Ask the TA to run the TA Gate Approval workflow." |
| `scope-approved` | Phase 3 (HLD generation) |
| `awaiting-hld-approval` | **STOP** — "HLD gate is pending TA review. Ask the TA to run the TA Gate Approval workflow." |
| `hld-approved` | Phase 4 (ADRs) |
| `awaiting-lld-approval` | **STOP** — "LLD gate is pending TA review. Ask the TA to run the TA Gate Approval workflow." |
| `lld-approved` | Phase 6 (IaC planning) |
| `awaiting-packet-approval` | **STOP** — "Decision packet gate is pending TA review. Ask the TA to run the TA Gate Approval workflow." |
| `blocked` | Report the blocker: "This change is blocked. Finding: `[blocker.finding]` (gate: `[blocker.gate]`). Rework the artifact and re-submit." |
| `implementation-approved` | Design is complete — nothing left to do in this workflow. |

If status is `awaiting-*` or `blocked`, output the message and stop. Do not re-run completed phases.

### Phase 1 — Impact Analysis and Scope

1. Fetch and challenge the GitHub issue. If no issue exists, stop: "Create a GitHub issue first with `gh issue create`." Detect the requirements source: if `docs/00-migration/migration-brief.md` exists this is a migration project — read the brief as the requirements source (it replaces `docs/01-product/prd.md`; slices reference `MR-<ID>` not `FR-<ID>`). Otherwise extract the PRD reference (`FR-<ID>`) from the issue and read `docs/01-product/prd.md` at that requirement — the issue is a pointer, the PRD is the source of truth. Before reading the manifest, challenge: Is the problem backed by evidence? Are the AC testable and specific? Are NFRs for the affected domain stated? Is there a simpler approach? Resolve gaps now. See `ai/shared/challenge-stance.md` for the full standard.
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
5. Determine tier (from `ai/claude/dev-practices/SKILL.md`). Challenge scope: cross-domain or multi-service changes are Tier 3 even when described as simple.
6. Estimate effort and token cost (phase-level formula from `ai/claude/dev-practices/roi-estimation.md`).
7. Initialize or update `.hitl/current-change.yaml` with `status: awaiting-scope-approval`. Post a scope summary comment on the GitHub issue:
   ```bash
   gh issue comment <issue-number> --body "## ⏳ Scope Gate — Awaiting TA Review\n\nImpact analysis complete. Awaiting TA approval before HLD generation.\n\n**Affected domains:** <list>\n**Tier:** <N>\n**Estimated effort:** <N days>"
   ```
8. **STOP — present impact summary. The TA must run the TA Gate Approval workflow to advance to `scope-approved` before this workflow continues.**

### Phase 2 — ROI Trigger (Step 4)

If effort > 1 day: record the ROI section in `.hitl/current-change.yaml` under `roi_estimate` using the template from `ai/claude/dev-practices/roi-estimation.md`. Ask architect to fill in the baseline metric now — it cannot be estimated after the fact. Post a pointer comment on the issue (not the content): `gh issue comment <issue-number> --body "ROI estimate required — filed in decision packet (effort > 1 day)."`

### Phase 3 — HLD (Step 5, Part 1)

For Tier 2+:
- Generate HLD at `docs/02-design/technical/hld/<feature>.md` following the `Generate Documentation` section below.
- Update `docs/02-design/technical/hld/index.md` and `source_artifacts.hld` in `.hitl/current-change.yaml`.
- Set `status: awaiting-hld-approval` in `.hitl/current-change.yaml`.
- Post a gate comment on the GitHub issue:
  ```bash
  gh issue comment <issue-number> \
    --body "## ⏳ HLD Gate — Awaiting TA Review\n\nHLD is ready for review.\n\n**HLD:** \`docs/02-design/technical/hld/<feature-name>.md\`\n\nTA: run the TA Gate Approval workflow to approve or reject."
  ```
- **STOP — the TA must run the TA Gate Approval workflow to advance to `hld-approved`. Do not generate LLDs until the status is `hld-approved`.**

### Phase 4 — ADR Capture (Step 5, Part 2)

After HLD approval:
- Identify every design decision in the HLD.
- Create ADR stubs at `docs/02-design/technical/adrs/<decision>.md` using `ai/shared/templates/adr-template.md`. Mark as "DRAFT — architect to complete rationale."
- Ask architect: "Are there decisions being made here that aren't visible in the design?"

### Phase 5 — LLD per Domain (Step 5, Part 3)

For each affected domain:
- Generate LLD following the `Generate Documentation` section below.
- Update `source_artifacts.lld` in `.hitl/current-change.yaml` after each LLD is written.

After all domain LLDs are generated:
- Set `status: awaiting-lld-approval` in `.hitl/current-change.yaml`.
- Post a gate comment on the GitHub issue:
  ```bash
  gh issue comment <issue-number> \
    --body "## ⏳ LLD Gate — Awaiting TA Review\n\nLLDs are ready for review.\n\n**LLD(s):** \`docs/02-design/technical/lld/...\`\n**Domains covered:** <list>\n\nTA: run the TA Gate Approval workflow to approve or reject."
  ```
- **STOP — the TA must run the TA Gate Approval workflow to advance to `lld-approved`. Do not proceed to slice decomposition until the status is `lld-approved`.**

### Phase 6 — IaC Planning (Step 6)

If IaC changes were identified: list specific files, what changes, and reversibility. Record in `.hitl/current-change.yaml` under `iac_plan`. If none: state so explicitly.

### Phase 7 — Slice Decomposition

This is the architect's core parallelization decision — no default behavior, requires explicit reasoning.

For each affected domain, propose a slice. For each slice, answer: **"What does the PM see at the end of this slice?"** A valid answer is a user-visible feature the PM can exercise, or a measurable outcome with a defined pass/fail (record counts, latency delta, error-rate comparison). If the answer is "nothing visible yet," the slice is too narrow — extend or merge it. Add a `demo:` line to each slice.

For each pair of slices:
- Do they share mutable state, database tables, or external API contracts?
- Can both be deployed to production independently?

Mark slices with ordering dependencies as **SEQUENTIAL**. Mark fully independent slices as **PARALLEL OK**.

**STOP — present slice plan (with `demo:` lines) and ask architect to confirm.** Do not assemble packets until the slice plan is confirmed.

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

If required: create stub at `docs/03-engineering/training/<capability>.md` using `ai/shared/templates/training-plan-template.md`.

### Phase 10 — Decision Packet Assembly (Step 9)

For each confirmed slice, generate `docs/decisions/issue-<N>-slice-<M>.yaml` (or `docs/decisions/issue-<N>.yaml` for single-slice) using `ai/shared/templates/decision-packet-template.yaml`. Fill all fields: issue, domain (one only), LLD path, HLD path, ADR paths, IaC plan, test plan, rollout risk, ROI flag, impact brief placeholders.

After all packets are assembled:
- Set `status: awaiting-packet-approval` in `.hitl/current-change.yaml`.
- Post a gate comment on the GitHub issue:
  ```bash
  gh issue comment <issue-number> \
    --body "## ⏳ Decision Packet Gate — Awaiting TA Review\n\nDecision packet(s) assembled and ready for final TA review.\n\n**Packet(s):** \`docs/decisions/issue-<N>...\`\n**Slices:** <slice plan>\n**Estimated effort:** <N days>\n**Rollout risk:** <level>\n\nTA: run the TA Gate Approval workflow to approve and hand off to developers."
  ```
- **STOP — the TA must run the TA Gate Approval workflow to advance to `implementation-approved`. Developers cannot begin until that gate is approved.**

When the TA approves the packet gate, the TA Gate Approval workflow will post the developer handoff comment on the issue automatically.

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
  .hitl context: awaiting-packet-approval (TA approval pending)

Slice handoff (pending TA approval):
  Slice 1: domain [A] [PARALLEL OK]
    LLD: docs/.../lld/[A]/...
    Packet: docs/decisions/issue-<N>-s1.yaml
  Slice 2: domain [B] [SEQUENTIAL — after slice 1]
    LLD: docs/.../lld/[B]/...
    Packet: docs/decisions/issue-<N>-s2.yaml

Next: TA runs the TA Gate Approval workflow; developers assigned after approval
```

---

## TA Gate Approval

Run when the architect has set a gate to `awaiting-*` status and the Technical Advisor needs to review and advance (or reject) it. This replaces the `/hitl:ta-approve` skill from the Claude Code plugin.

**Who runs this:** Technical Advisor only. This workflow cannot be run by the architect on their own behalf.

**Trigger:** TA says "ta-approve", "approve the gate", "review the design gate", or the GitHub issue has a `⏳ Gate — Awaiting TA Review` comment.

**Refusal:** If `.hitl/current-change.yaml` does not exist AND `.hitl/design-system.yaml` does not exist, stop: "No active HITL context found. This workflow requires either `.hitl/current-change.yaml` or `.hitl/design-system.yaml`."

### Step 1 — Detect context and current gate

Read whichever context file exists. Extract the `status` field. Determine what gate is pending:

| Status | Gate | Artifact to review |
|--------|------|--------------------|
| `awaiting-scope-approval` | Scope | Impact summary in session output; `source_artifacts.hld: pending` |
| `awaiting-hld-approval` | HLD | `source_artifacts.hld` path |
| `awaiting-lld-approval` | LLD | `source_artifacts.lld` path(s) |
| `awaiting-packet-approval` | Decision packet | `source_artifacts.decision_packet` path(s) |
| `awaiting-requirements` | Requirements (design-system) | PRD extraction in session output |
| `awaiting-domains` | Domains (design-system) | Domain decomposition in session output |
| `awaiting-manifest` | Manifest + ADRs (design-system) | `docs/system-manifest.yaml` and `docs/02-design/technical/adrs/` |
| `awaiting-delivery-plan` | Delivery plan (design-system) | `docs/decisions/` |

If status is NOT one of the `awaiting-*` values above, stop:

> "No gate is pending. Current status: `[status]`. This workflow only acts when the architect has reached a checkpoint and is waiting for TA review."

If status is `blocked`, stop:

> "This change is currently blocked. Finding: `[blocker.finding]` (gate: `[blocker.gate]`). The architect must rework the `[blocker.gate]` artifact and re-submit before the gate can advance."

### Step 2 — Surface the artifact

Load and display the artifact path(s) from the context file:

```
Gate pending: [gate name]
Artifact:     [path or description]
Change:       [change_id] — [title if available]
```

If the artifact path points to a file that does not exist, stop:

> "Artifact not found at `[path]`. The architect may not have completed this phase yet. Ask the architect to re-run the design workflow and confirm the artifact was written."

Remind the TA: "If you are on a different machine than the architect, run `git pull` now to ensure you have the latest artifacts before reviewing."

### Step 3 — Present the gate checklist

Present the checklist for the current gate. Ask all items as a numbered list — do not proceed until every item is answered.

**Scope gate (`awaiting-scope-approval`)**
1. Are the affected domains correct — neither over-counted (scope creep) nor under-counted (hidden blast radius)?
2. Is the tier assignment correct for this change?
3. Is the ROI trigger noted if effort > 1 day?
4. Are any backwards-incompatible changes flagged with a compatibility strategy?

**HLD gate (`awaiting-hld-approval`)**
1. Are the component boundaries correct — does each component have a clear single responsibility?
2. Is the security model correct for this feature (auth, data isolation, secrets handling)?
3. Are design decisions that need ADRs flagged — no undocumented tradeoffs embedded in the diagram?
4. Is there no implementation bias — does the HLD describe *what*, not *how*?

**LLD gate (`awaiting-lld-approval`)**
1. Are method signatures precise enough that a developer could generate tests directly from the LLD without reading other docs?
2. Are preconditions and error modes complete for every public method?
3. Does the LLD correctly reflect the decisions in the approved HLD?
4. Is the slice demo answer concrete — does each slice describe what the PM will see and verify in the running app?

**Decision packet gate (`awaiting-packet-approval`)**
1. Does each packet cover exactly one manifest domain (no cross-domain scope)?
2. Is the LLD path in the packet correct and the file present on disk?
3. Is the test plan complete enough for a developer to start the TDD cycle without clarification?
4. Is the rollout risk level correct for this change?
5. Has PM confirmed the acceptance criteria and scope (product approval)?

**Requirements gate — design-system (`awaiting-requirements`)**
1. Are the core use cases correct and complete (the 3–5 workflows that matter most)?
2. Are NFRs specific enough to drive architecture decisions?
3. Are all external integrations listed?
4. Are tech stack constraints captured or flagged as open decisions?

**Domain decomposition gate — design-system (`awaiting-domains`)**
1. Is data ownership unambiguous — each domain owns its data with no overlap?
2. Are there any circular dependencies that indicate a boundary is in the wrong place?
3. Are domains right-sized — none doing too many unrelated things, none always changed together?

**Manifest + ADRs gate — design-system (`awaiting-manifest`)**
1. Are facade APIs and boundary entities approximately correct (DRAFT is acceptable)?
2. Do domain dependencies match the interaction matrix from domain decomposition?
3. Are all foundational ADRs resolved — no open decisions on: language/framework, data storage, auth, API style, deployment model?

**Delivery plan gate — design-system (`awaiting-delivery-plan`)**
1. Does every slice have a concrete PM demo check — something visible or measurable?
2. Does the sequencing match the dependencies from the interaction matrix?
3. Is every slice 2–5 days in scope?

### Step 4 — Collect TA answers

For each checklist item, record the TA's answer (yes / no / with-caveat).

If any item is **no** or flagged as a problem, go to **Step 5 — Rejection**.
If all items are **yes**, go to **Step 6 — Approval**.

### Step 5 — Rejection

Ask the TA: "What specifically needs to change? Be concrete enough for the architect to act on it."

Update the context file:

```yaml
status: blocked
blocker:
  gate: [scope|hld|lld|packet|requirements|domains|manifest|delivery-plan]
  finding: "[TA's specific finding]"
  rejected_at: "[ISO 8601 timestamp]"
```

Post a GitHub issue comment (if `change_id` is in GH-N format):
```bash
ISSUE_NUM="${CHANGE_ID#GH-}"
gh issue comment "$ISSUE_NUM" --body "## ❌ Gate Rejected — [gate name]

**Finding:** [TA's finding]

The architect must rework the [gate name] artifact and re-submit.
Re-run the Architect Design Journey to address the finding and reach this gate again."
```

If on a different machine: "Push this change so the architect can pull and see the rejection: `git add .hitl/ && git commit -m 'hitl: gate rejected — [gate name]' && git push`"

Stop here.

### Step 6 — Approval

Determine the next status from the transition table:

| Current status | Next status |
|----------------|-------------|
| `awaiting-scope-approval` | `scope-approved` |
| `awaiting-hld-approval` | `hld-approved` |
| `awaiting-lld-approval` | `lld-approved` |
| `awaiting-packet-approval` | `implementation-approved` |
| `awaiting-requirements` | `requirements-confirmed` |
| `awaiting-domains` | `domains-confirmed` |
| `awaiting-manifest` | `manifest-confirmed` |
| `awaiting-delivery-plan` | `complete` |

Update the context file:
1. Set `status` to the next value from the table.
2. For `awaiting-packet-approval` → also set `approvals.architecture: approved` and `approvals.product: approved`.
3. Clear any previous `blocker` field.

Post a GitHub issue comment:

**If approving `awaiting-packet-approval`** (final design gate — developers start now):
```bash
ISSUE_NUM="${CHANGE_ID#GH-}"
gh issue comment "$ISSUE_NUM" \
  --body "## ✅ Ready for Development

Architecture approved. If this issue is assigned to you, you can begin now.

**Decision packet:** \`docs/decisions/issue-${ISSUE_NUM}.yaml\` (or slice variant)
**Your domain:** [domain from packet]
**LLD:** [lld path from packet]

Open Codex in the repo and run the TDD workflow with:
\`I have been assigned GitHub issue #${ISSUE_NUM}. Read the decision packet at docs/decisions/issue-${ISSUE_NUM}.yaml and tell me what I am building, what domain I am in, and what the test plan requires me to cover.\`"
```

**For all other gates** (scope, HLD, LLD — architect continues):
```bash
ISSUE_NUM="${CHANGE_ID#GH-}"
gh issue comment "$ISSUE_NUM" \
  --body "## ✅ Gate Approved — [gate name]

TA has reviewed and approved the [gate name] artifact.

**Status:** \`[next-status]\`
**Next step:** Architect re-runs the Architect Design Journey to continue to the next phase."
```

If on a different machine: "Push this change so the next person can pull and continue: `git add .hitl/ && git commit -m 'hitl: [gate name] approved' && git push`"

---

## QA Review

Run after the TDD cycle is complete, before creating a PR.

**Trigger:** User asks to "QA review", "review test coverage", or "verify tests".

### What to check

1. Every acceptance criterion from the PRD (FR-<ID> linked in the issue) has at least one test
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

After producing the review, post a comment on the GitHub issue:
- If **APPROVED**: `gh issue comment <issue-number> --body "## ✅ QA Review Approved\n\nTest coverage verified. All ACs covered, LLD edge cases present, incident regressions tested. Implementation can proceed to verify-quality handoff."`
- If **REVISIONS REQUIRED**: `gh issue comment <issue-number> --body "## 🔁 QA Review: Revisions Required\n\n<summary of gaps to fix>"`

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

Run before implementation on any Tier 2+ change. This replaces the `/hitl:generate-docs` skill.

**Trigger:** User asks to "generate docs", "write HLD/LLD", or "create design documents".

### New Feature Mode

1. Determine the feature name (kebab-case).
2. Create `docs/02-design/technical/hld/<feature-name>.md` using `ai/shared/templates/hld-template.md` (installed by `ai/codex/install.sh`). Must include: executive summary, Mermaid architecture diagram (`graph TB`), component overview, data flow sequence diagrams, integration points, security architecture, scalability considerations.
3. Update `docs/02-design/technical/hld/index.md`.
4. **Stop — ask the user to review and approve the HLD** before creating the LLD.
5. After HLD approval, create LLD files under `docs/02-design/technical/lld/` using `ai/shared/templates/lld-component-template.md` (installed by `ai/codex/install.sh`). Include Mermaid class and sequence diagrams, method signatures, error modes, preconditions, and usage examples.
6. Update `docs/02-design/technical/lld/index.md` and `packages.md`.

All diagrams must use Mermaid. No `<br/>` tags inside Mermaid blocks.

### Reverse-Engineer Mode

If the user says "reverse engineer", "existing codebase", or "brownfield": read existing code and produce HLD/LLD/ADR docs that reflect what is actually there. Do not invent behavior not present in the code.

---

## Before Creating a PR

Verify all of the following:

- [ ] `.hitl/current-change.yaml` status is `conformance-review-pending` or later
- [ ] LLD adherence review passes (run the `Review LLD Adherence` workflow below — all ❌ items resolved)
- [ ] Convention checks pass (zero semgrep violations)
- [ ] All new tests pass
- [ ] No regressions in existing tests
- [ ] LLD is up to date (no unresolved drift from conformance review)
- [ ] Downstream impact brief exists (ask Codex to generate one using the `Impact Brief` workflow)
- [ ] PR description includes: GitHub issue link, HLD/LLD links, test plan summary, rollout notes

---

## Review LLD Adherence

Run before opening any PR to verify that generated code strictly matches what the LLD specifies. This is a required step — ❌ items are merge blockers.

**Trigger:** User asks to "review LLD adherence", "check code against LLD", or "verify implementation matches spec". Also run as part of the `Before Creating a PR` checklist.

**Input:** Optional — component name, file path, or PR description. If empty, uses current git diff.

### Step 1 — Identify what was built

1. Read the diff: `git diff main...HEAD` or staged changes
2. List every source file that was added or modified
3. For each file, look up its governing LLD via `docs/system-manifest.yaml`
4. If a modified file has no LLD entry → flag immediately: "⚠️ `[file]` has no LLD. Either add it to the manifest and create an LLD, or confirm with the architect that this file is exempt."

### Step 2 — Read the governing LLDs

For each domain touched by the diff:
1. Read the full LLD document
2. Extract every class, method, interface, and data structure the LLD specifies
3. Note any sections marked DRAFT, TODO, or TBD — these are ambiguous and need architect sign-off

### Step 3 — Check LLD → Code (nothing missing)

For each element specified in the LLD, verify it exists in the generated code:

| LLD Element | Expected | Found in Code | Status |
|---|---|---|---|
| `ClassName` | class with fields X, Y, Z | `src/foo.py:12` | ✅ |
| `method_name(args) -> ReturnType` | method signature | — | ❌ MISSING |

Mark each as:
- ✅ **Present and matches** — implementation matches LLD spec
- ⚠️ **Present but diverged** — exists but signature, behavior, or naming differs
- ❌ **Missing** — LLD specifies it, code does not have it

### Step 4 — Check Code → LLD (nothing extra)

For each class, method, and public interface in the generated code, verify it appears in the LLD:

| Code Element | File | In LLD? | Status |
|---|---|---|---|
| `ExtraHelper` class | `src/foo.py:78` | No | ❌ NOT SPECIFIED |
| `_private_method` | `src/foo.py:90` | N/A (private) | ✅ EXEMPT |

Private methods and internal helpers are exempt. Public classes, public methods, and any code that crosses a domain boundary must be in the LLD.

### Step 5 — Check cross-cutting conventions

Read the `cross_cutting` section of `docs/system-manifest.yaml`. Verify each convention is followed. Flag any violation.

### Step 6 — Report

```
## LLD Adherence Report

**LLD reviewed:** [path]
**Files checked:** [list]

### ✅ Matching ([N] elements)
All LLD-specified elements found and matching.

### ⚠️ Diverged ([N] elements — architect decision required)
- [element]: LLD specifies [X], code implements [Y].
  Options: (a) update LLD to reflect better design, (b) fix code to match LLD.

### ❌ Missing ([N] elements — must fix before merge)
- [element]: specified in LLD at [section], not found in code.

### ❌ Not Specified ([N] elements — must fix before merge)
- [element] in [file:line]: public interface not in LLD.

### Convention Violations ([N] — must fix before merge)
- [file:line]: [convention name] violated.

### Verdict
[ ] PASS — all elements match, no violations.
[ ] PASS WITH NOTES — diverged items logged; architect must acknowledge before merge.
[ ] BLOCK — missing elements or unspecified public interfaces. Fix before PR.
```

### Step 7 — Handle divergence

For each ⚠️ diverged item, present the choice explicitly — do NOT silently normalize divergence:

> "The LLD specifies `method_name(user_id: str) -> User`. The implementation uses `method_name(user: UserDTO) -> UserResponse`. Options:
> (a) **Update the LLD** — if the implementation reflects a better design. Requires architect approval before merge.
> (b) **Fix the code** — if the implementation drifted unintentionally."

---

## Ops Role — Build, Deploy, Infrastructure

### Build (ops/build)

**Trigger:** User says "build", "ops/build", or "build from branch".

1. Confirm branch name and PR number.
2. Verify CI pipeline: `gh run list --branch <branch> --limit 5`. If any failing run: stop — "CI is not green on this branch. Fix failures before building."
3. Check artifact integrity: confirm the build artifact SHA matches the expected commit.
4. Update `.hitl/current-change.yaml` to record build readiness.
5. Report: "Build verified. Branch: `<branch>`. CI: passed. Artifact: `<sha>`. Ready for IaC and deploy."

---

### Apply IaC (ops/apply-iac)

**Trigger:** User says "apply IaC", "apply infrastructure", or "ops/apply-iac".

1. Read IaC plan from `.hitl/current-change.yaml` under `iac_plan`.
2. Run dry-run and present all changes before doing anything:
   ```bash
   terraform plan  # or pulumi preview, cdk diff, etc.
   ```
3. List every resource change: created, modified, destroyed. Flag any destructive operations explicitly.
4. **STOP — ask operator:** "Apply these changes?" Do not apply without explicit confirmation.
5. On confirmation, apply. Verify state matches plan. Report any post-apply drift.

Never apply IaC changes without showing the full plan first. Never skip the confirmation step.

---

### Deploy (ops/deploy)

**Trigger:** User says "deploy", "ops/deploy", or names a target environment.

1. Read rollout plan from `.hitl/current-change.yaml`.
2. Verify prerequisites: IaC changes applied (check `iac_plan.status`), build artifact verified.
3. For **High or Critical risk** changes: canary deployment only — never skip canary for these tiers.
4. **Present the exact deployment command before running it. STOP — ask operator to confirm.**
5. On confirmation, deploy. Monitor health checks.
6. Post a comment on the GitHub issue, then report to the team:
   ```bash
   gh issue comment <issue-number> \
     --body "## 🚀 Deployed to <environment>\n\n**Artifact:** <artifact-reference>\n**Deployed at:** <ISO timestamp>\n**Rollout:** <canary N% / 100% direct>"
   ```
   For the final production promotion (100% traffic, all go/no-go criteria met), also close the issue:
   ```bash
   gh issue close <issue-number> --comment "Deployed to production at <timestamp>. All go/no-go criteria met. Closing."
   ```

A deployment that fails health checks mid-rollout must be paused and investigated — do not auto-rollback without first diagnosing the cause.

---

## Team Decision Documentation (conclude)

**Trigger:** User says "conclude thread", "record decision", or "conclude" with a Slack thread URL or pasted thread content.

1. Read the thread content.
2. Extract: what was decided, by whom, which alternatives were considered, rationale.
3. If no clear decision is present: "I can't find a clear decision in this thread. Can you point me to the message where the team agreed?"
4. Draft ADR at `docs/02-design/technical/adrs/<decision-name>.md` using `ai/shared/templates/adr-template.md`. Use the team's actual words for rationale — do not rephrase into generic architecture-speak. The ADR should sound like the team, not a textbook.
5. **STOP — present draft and ask:** "Is this an accurate record of the decision?"
6. On approval:
   - Save the ADR.
   - Update `docs/02-design/technical/adrs/README.md`.
   - Create GitHub issue: `gh issue create --title "impl: <decision>" --body "ADR: <path>\n\n<summary>"`
   - Update `hld/index.md` if HLD changes are implied.
   - If the decision crosses domain boundaries, note which facade APIs are affected.
7. Ask: "Was everyone who should have been involved in this thread? If not, should they review the ADR before it's accepted?"

Never infer a decision that wasn't explicitly stated. The ADR captures what was decided, not what should be decided.

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

`.mcp.json` is created by `ai/codex/install.sh` — it wires the MCP server so Codex can call `query_graph`, `get_node`, and `get_neighbors` as tools.

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

When `codex_hooks = true` is set in `.ai/codex/config.toml`, Codex loads `.ai/codex/hooks.json` and runs HITL context checks before each Write/Edit and boundary checks after — the same real-time enforcement as Claude Code's PreToolUse/PostToolUse hooks.

Both files are installed by `ai/codex/install.sh`. The hook scripts live in `ai/codex/hook-scripts/`.

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
bash /path/to/hitl-dev-platform/ai/codex/install.sh
```
