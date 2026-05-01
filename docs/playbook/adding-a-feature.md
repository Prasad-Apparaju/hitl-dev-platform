# Adding a New Feature

This guide walks through adding a new feature, from idea to production. It applies to any functional change — new endpoint, new agent capability, new integration, new UI flow.

For bug fixes and refactors, see [Fixing a Bug or Refactoring](./fixing-and-refactoring.md).

---

## Which Process Do I Need?

Not every change needs the full workflow below. Use this table to pick the right weight:

| Change Type | Process |
|---|---|
| **Trivial** (typo, config value, log message) | GitHub issue or linked task &rarr; code &rarr; tests if applicable &rarr; review &rarr; merge |
| **Bug fix** | Issue &rarr; regression test first &rarr; fix &rarr; risk note &rarr; registry update if incident-related |
| **Normal feature** | Full workflow (all steps below) |
| **Cross-cutting / security / data migration** | Decomposition plan &rarr; domain-scoped PRs &rarr; full workflow per PR |
| **P0 incident** | Fix first &rarr; full docs within 48 hours &rarr; incident registry entry |

When in doubt, use the heavier process. If you are here, you probably need the full workflow.

---

## Before You Start

Read these once. They define the rules of the game:

| Document | What it gives you |
|---|---|
| `CLAUDE.md` | 30-step workflow, preflight check, coding standards, cross-cutting conventions |
| `docs/system-manifest.yaml` | Domain boundaries, facade APIs, 10 conventions that apply to all code |
| `docs/playbook/process-overview.md` | Visual pipeline + detailed step descriptions |
| `docs/02-design/technical/adrs/design-decisions.md` | 55 decisions — understand WHY things are the way they are before proposing changes |

---

## The Process

### Phase 1 — Define (Steps 1-2)

**1. Create a GitHub issue.**

Every feature starts with an issue. No exceptions. The issue describes:
- What the feature does (user-facing behavior)
- Why it's needed (link to PRD requirement if applicable)
- Proposed approach (high-level, not implementation details)

```bash
gh issue create --title "feat: <short description>" --body "..."
```

**2. Figma review (if a design exists).**

If there's a visual design, extract requirements, interactions, and visual specs into the issue before proceeding. The design is both the input and the acceptance criteria — it bookends the workflow.

---

### Phase 2 — Design (Steps 3-8)

**3. Impact analysis.**

Before touching code or docs, identify what's affected:
- Which endpoints / APIs change?
- Which services / modules are involved?
- Which infrastructure (manifests, configs, migrations) needs updating?
- Which existing tests cover this area?
- Has anything gone wrong here before? Check `docs/04-operations/incident-registry.yaml`.

**4. ROI estimate (if change costs > 1 day).**

Add to the issue:
- Value dimension (Quality / Reliability / Velocity / Cost / Risk / UX)
- Expected outcome (specific, falsifiable)
- Baseline metric (measured, not guessed)
- 30/90-day checkpoint dates

For changes under 1 day: state "ROI estimate not required — change is < 1 day."

**5. Update design docs BEFORE code.**

- Does an HLD cover the architecture for this feature? If not, create or update one in `docs/02-design/technical/hld/`.
- Create or update the LLD in `docs/02-design/technical/lld/` with class diagrams, method signatures, sequence diagrams.
- If this introduces a new architectural decision, propose an ADR in `docs/02-design/technical/adrs/`.

The LLD must be precise enough to generate code from. If it isn't, it's not done.

**6. Update IaC (if infrastructure is affected).**

New service? New migration? New secret? New config? Update the relevant manifests, Alembic migrations, and environment configs.

**7. Plan the tests.**

Before writing any code, identify:
- New tests to add (happy path, error cases, edge cases)
- Existing tests to update
- Obsolete tests to remove
- Regression tests that must still pass

Document this in the issue or PR description.

**8. Training plan stub (if introducing a new capability).**

New architectural pattern, external system, framework, or ML technique → create `docs/03-engineering/training/<capability>.md`. Otherwise, state "no new capability — training plan not required."

---

### Phase 3 — Build with TDD (Steps 9-16)

**9. Generate tests first (RED).**

Using Claude, generate maximum test coverage from the LLD + test plan + manifest facade contracts. Tests cover:
- Happy paths for every method in the LLD
- Error paths for every failure mode
- Edge cases and boundary conditions
- Contract tests from the manifest's facade APIs
- Convention tests (idempotency keys, plan mode, brand isolation)

No implementation code exists yet.

**10. Review the tests (HUMAN GATE).**

This is the highest-value human step. The developer:
- Adds edge cases AI missed ("what if the API returns 429 mid-carousel?")
- Adds integration scenarios from domain knowledge
- Removes trivial or wrong tests
- Challenges assumptions

Register every test in `docs/03-engineering/testing/test-registry.yaml`.

**11. Tests improve the design.**

AI analyzes the test suite for LLD gaps. If a test covers behavior the LLD doesn't describe → update the LLD first. Examples:
- Test for rate-limit handling but LLD doesn't mention rate limits → add to LLD
- Test for retry path but LLD doesn't specify retry → add to LLD

**12. Verify RED.**

Run the full test suite. All new tests MUST fail (no implementation exists). If any pass → investigate.

**13. Generate code (GREEN).**

Generate the simplest implementation that makes all failing tests pass. Follow the LLD and cross-cutting conventions from `docs/system-manifest.yaml`.

**14. Verify GREEN.**

Run full test suite (new + existing). ALL must pass. If new pass but old fail → regression. Fix before proceeding.

**15. Refactor.**

Simplify passing code. Remove duplication, improve naming. Rerun tests after each change; if any break, revert.

**16. Convention checks.**

Run locally — do not defer to CI:
```bash
semgrep scan --config .semgrep/ --error    # if installed
ruff check <changed-files>
```
Fix any violations before proceeding.

---

### Phase 4 — Verify (Steps 17-20)

**17. Code review Round 1** — structure, security, LLD adherence.

**18. Code review Round 2** — edge cases, regressions, completeness.

**19. Rerun tests** — confirm no regressions from review fixes.

**20. Reconcile docs** — if implementation diverged from the design docs, pause and decide: does the implementation reveal a better design (update the docs), or did the implementation drift from the intended design (fix the code)? The decision is explicit and documented — never silently normalize drift.

---

### Phase 5 — Assess (Steps 21-22)

**21. Downstream impact brief.**

Produce a 5-section brief:

| Section | Question | Audience |
|---|---|---|
| Flows changed | What user-visible behaviors are different? | PM, QA |
| Risk assessment | What can break? Severity × likelihood? | Lead, Ops |
| Manual verification | What to test beyond the automated suite? | QA, Ops |
| PM mental model update | What assumptions does the PM hold that are no longer true? | PM |
| Rollout strategy | How do we derisk deployment? | Ops, Lead |

**22. Risk-rated rollout plan.**

| Risk | When | Rollout |
|---|---|---|
| Low | Cosmetic, internal-only | Direct deploy |
| Medium | New feature, additive | Feature flag → staging → 24h soak → prod |
| High | Changes existing behavior | Canary 5-10% → 4h monitor → expand |
| Critical | Irreversible side effects | Canary 1% → manual gate per step |

---

### Phase 6 — Ship (Steps 23-26)

**23. Create PR.**

Link to the GitHub issue. The PR includes docs + IaC + code + tests — all in one PR. Not separate.

**24. Integration verification (ARCHITECT GATE).**

The architect runs the feature E2E and verifies:
- Implementation matches the HLD/LLD intent
- Impact brief is complete
- Rollout plan is appropriate

**25. Figma comparison (if design exists).**

Compare implementation to design. List differences. Resolve before sign-off.

**26. Merge + deploy.**

Deploy per the risk-rated rollout plan. Monitor go/no-go criteria. The system must remain functional after deployment — no broken deploys.

---

### Phase 7 — Post-Ship (Steps 27-28)

**27. 30-day ROI check** — developer + lead: is the metric moving?

**28. 90-day ROI check** — lead + PM: actual vs estimated ROI. Update the ADR with an "Actual Outcome" section.

---

## Ownership

**Whoever builds the feature owns it end-to-end.** You write the code, you write the tests, you fix the bugs, you deploy it, you verify it works in the target environment. No handing off broken work.

## Escalation

Architectural trade-offs, PRD scope changes, and cross-team decisions → discuss with the technical advisor and product owner using the prescribed documentation formats. See [Architect Playbook — Escalation Path](../05-migration/architect-playbook.md#escalation-path).

## Quick Reference

| I need to... | Go to... |
|---|---|
| Understand the 30-step workflow | `CLAUDE.md` (inlined) or `docs/playbook/process-overview.md` (visual) |
| Check domain boundaries | `docs/system-manifest.yaml` |
| Look up an architectural decision | `docs/02-design/technical/adrs/design-decisions.md` |
| Find the HLD for a component | `docs/02-design/technical/hld/index.md` |
| Find the LLD for a component | `docs/02-design/technical/lld/index.md` |
| Check past incidents in this area | `docs/04-operations/incident-registry.yaml` |
| Check test coverage for this area | `docs/03-engineering/testing/test-registry.yaml` |
| Fix a bug instead | [Fixing a Bug or Refactoring](./fixing-and-refactoring.md) |
