---
name: qa-review-tests
description: Formal QA review of test coverage after the TDD RED phase. Verifies every acceptance criterion has a test, every LLD error mode is exercised, and all relevant incident regressions are present. Gates implementation start.
argument-hint: "[feature name, PR link, or LLD path]"
disable-model-invocation: true
---

# Review Test Coverage

Verify that the test suite produced by the TDD cycle is complete before implementation begins. This is a blocking gate — do not approve if coverage gaps exist.

**Input:** $ARGUMENTS (feature name, PR link, or LLD path)

---

## Step 1 — Read the spec

1. Read the GitHub issue to extract all acceptance criteria
2. Read the LLD at the path in `.hitl/current-change.yaml` (`source_artifacts.lld`) — note every method signature, error mode, precondition, and boundary entity
3. Read the test plan from `.hitl/current-change.yaml` under `tests.plan` — this is what the developer committed to covering
4. List the test files in `tests/` — read them

---

## Step 2 — Check incident regressions

Query the incident registry for the affected domain — prefer a graph query:
```
/graphify query "past incidents affecting domain: <domain-name>"
/graphify query "incident failure modes in <domain-name> that need regression coverage"
```
Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. For each incident relevant to this domain: verify a regression test exists that would have caught it. If no incidents exist for this domain, say so explicitly — do not skip the check.

---

## Step 3 — Coverage matrix

For each item in the spec, confirm test coverage:

| Spec item | Source | Test(s) | Status |
|-----------|--------|---------|--------|
| `<AC from issue>` | GitHub issue | `<test name>` | ✅ / ❌ |
| `<method + error mode from LLD>` | LLD | `<test name>` | ✅ / ❌ |
| `<incident regression>` | Incident registry | `<test name>` | ✅ / ❌ |

Flag every ❌ as a gap that must be resolved before implementation starts.

---

## Step 4 — Approve or block

**If no gaps:** Update the test registry at `docs/03-engineering/testing/test-registry.yaml` to record the reviewed tests. Report: "Test coverage approved. `<N>` tests cover `<M>` acceptance criteria, `<K>` LLD error modes, and `<J>` incident regressions. Implementation may proceed."

**If gaps exist:** List every gap with the specific spec item it fails to cover. Do not approve. Report: "Test coverage blocked. `<N>` gap(s) found — implementation must not start until these are resolved."

---

## Important Rules

- Every acceptance criterion must have at least one test — no exceptions
- Every LLD error mode must be exercised — if a method can throw, there must be a test for the throw
- Do not approve if any incident regression from this domain is uncovered
- Update the test registry when approving — a review with no registry update is incomplete
