# Fixing a Bug or Refactoring

This guide covers bug fixes and refactors. The same 22-step workflow applies, but several steps are shortened or skipped because the scope is smaller.

For new features, see [Adding a New Feature](./adding-a-feature.md).

---

## Bug Fix

### What's different from a feature

- No HLD/LLD creation — unless the fix reveals a design gap
- No ROI estimate — unless the fix costs > 1 day
- No training plan — unless the fix introduces a new pattern
- Impact brief is still required — bugs that reach production already broke trust; the fix needs a risk assessment

### The steps

**1. GitHub issue — describe the bug.**
- What's the expected behavior?
- What's the actual behavior?
- Steps to reproduce
- Root cause (if known)
- Link to incident registry entry if this was a production incident

```bash
gh issue create --title "fix: <short description>" --body "..."
```

**2. Impact analysis.**
- Which components are affected?
- What's the blast radius if the fix is wrong?
- Check `docs/04-operations/incident-registry.yaml` — has this happened before?
- Check `docs/03-engineering/testing/test-registry.yaml` — is there a test that should have caught this?

**3. Update docs (if the bug reveals a design gap).**

If the root cause is a missing spec (the LLD didn't describe this behavior), update the LLD before writing the fix. Otherwise, skip.

**4. Write the regression test FIRST.**

Write a test that reproduces the bug. Run it. It must fail (proving the bug exists). This is your RED step.

**5. Fix the bug (GREEN).**

Write the minimal fix that makes the regression test pass without breaking existing tests. Run the full suite.

**6. Convention checks.**

```bash
semgrep scan --config .semgrep/ --error
ruff check <changed-files>
```

**7. Code review.**

One round is sufficient for most bug fixes. Focus on: does the fix address the root cause, not just the symptom?

**8. Downstream impact brief.**

Even for bug fixes:
- What changed? (user-visible behavior difference)
- Risk assessment (could the fix break something else?)
- Manual verification scenarios

**9. Create PR, merge, deploy.**

Link to issue. Include the regression test. Deploy per risk level.

**10. Post-fix.**

- Add the regression test to `docs/03-engineering/testing/test-registry.yaml` with `origin: incident-regression` and `incident_ref: INC-NNN` if applicable.
- If this was a production incident, add an entry to `docs/04-operations/incident-registry.yaml` within 48 hours.
- If the fix revealed a missing canary criterion, update the rollout plan for this domain.

---

## Refactor

### What's different from a feature

- No PRD change — refactors don't change user-visible behavior
- No ROI estimate — unless the refactor costs > 1 day
- No impact brief — unless the refactor changes API contracts or deployment
- Tests must pass before AND after — if behavior changes, it's not a refactor

### The steps

**1. GitHub issue — state the goal.**
- What are you improving? (readability, performance, testability, removing tech debt)
- What is NOT changing? (user-visible behavior, API contracts)

```bash
gh issue create --title "refactor: <short description>" --body "..."
```

**2. Impact analysis.**
- Which modules are affected?
- Are any API contracts (facade APIs from the manifest) changing? If yes → this is a feature, not a refactor. Follow the feature process.
- Which tests cover the code being refactored?

**3. Run the full test suite BEFORE starting.**

Capture the baseline. Every test that passes now must pass after.

**4. Refactor.**

Make the changes. Follow coding standards from `CLAUDE.md`. Add inline comments on non-obvious logic.

**5. Run the full test suite AFTER.**

Same tests, same results. Any failure means the refactor changed behavior — investigate and fix or revert.

**6. Convention checks.**

```bash
semgrep scan --config .semgrep/ --error
ruff check <changed-files>
```

**7. Code review.**

One round. Focus on: is the refactored code clearer? Does it follow the conventions in `docs/system-manifest.yaml`?

**8. Reconcile docs (if the refactor moves or renames components).**

Update LLDs if class/method signatures changed. Update the system manifest if domain files moved.

**9. Create PR, merge, deploy.**

Link to issue. No impact brief needed unless API contracts changed.

---

## When a Bug Fix Becomes a Feature

If during investigation you discover that the "fix" requires:
- A new endpoint
- A new model or schema change
- A change to an API contract
- A change to the PRD

Stop. Create a separate feature issue and follow [Adding a New Feature](./adding-a-feature.md). The original bug issue stays open and links to the feature issue.

---

## Quick Decision Table

| Situation | Process to follow |
|---|---|
| User reports broken behavior | Bug fix (this doc) |
| Test fails on existing behavior | Bug fix (this doc) |
| Code works but is hard to read/maintain | Refactor (this doc) |
| Performance improvement with no behavior change | Refactor (this doc) |
| New user-visible capability | [Feature](./adding-a-feature.md) |
| "Bug fix" that requires a new endpoint | [Feature](./adding-a-feature.md) |
| Schema migration needed | [Feature](./adding-a-feature.md) |
| Changing an API contract | [Feature](./adding-a-feature.md) |

## Ownership

Same as features: **whoever fixes it owns it end-to-end.** Write the fix, write the regression test, deploy it, verify it works.
