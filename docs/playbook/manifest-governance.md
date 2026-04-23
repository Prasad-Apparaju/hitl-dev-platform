# Manifest Governance

The system manifest is only useful if it stays accurate. This document defines who owns it, when it must be updated, what CI can enforce, and what remains judgment-based.

## Ownership model

| Responsibility | Owner | Fallback |
|---------------|-------|---------|
| Domain boundaries (which files belong to which domain) | Architect | Senior dev with cross-domain knowledge |
| Facade API blurbs (mutation descriptions, preconditions, error modes) | Domain lead (the developer most familiar with the domain) | Architect |
| Cross-cutting conventions | Architect | Team consensus via ADR |
| Weekly delta re-run review | Architect | Any senior engineer |
| Manifest schema and generator tooling | Platform team | Whoever maintains the hitl-dev-platform |

### In teams without a dedicated architect

The most senior developer who understands cross-domain concerns takes the manifest owner role. If multiple people share that knowledge, designate one person per sprint rotation. The key property: one person must be accountable for the manifest being correct at any given time.

---

## When updates are required

### Mandatory — CI should block if not done

| Trigger | What to update |
|---------|---------------|
| New source file added to a domain | Add to `domains.<domain>.files` |
| New public API added to a domain | Add to `domains.<domain>.facade_apis` |
| Existing API's signature, contract, or side effects change | Update the mutation description and preconditions |
| Domain boundary changes (files moved between domains) | Update both affected domains' file lists |
| New cross-cutting convention introduced | Add to `cross_cutting.conventions` |

### Recommended — update within 1 sprint

| Trigger | What to update |
|---------|---------------|
| New dependency between domains discovered | Document in facade interactions |
| Known failure mode discovered in production | Add to `domains.<domain>.facade_apis.<api>.error_modes` |
| Precondition assumption violated by a bug | Strengthen the precondition language |

### Not required

| Trigger | Why not |
|---------|--------|
| Internal refactor within a domain (no interface change) | Internals are not in the manifest |
| Test file changes (unless they test the facade contract) | Tests are not domain internals |
| Docs-only changes | The manifest describes the code structure, not the docs |

---

## What CI can enforce

| Check | Enforcement mechanism |
|-------|----------------------|
| Files exist in manifest | Manifest drift checker (`tools/manifest-drift/`) compares file lists against actual directory |
| Newly added source files are in a domain | CI fails if unregistered source files detected |
| Convention checks pass | Semgrep rules in `.semgrep/` run on every PR |
| Decision packet includes affected domains | Preflight check (`tools/preflight/`) validates packet against manifest domains |

**CI cannot automatically verify:**
- Whether the facade API blurbs accurately describe the code
- Whether preconditions are complete
- Whether error modes are exhaustive
- Whether domain boundaries make architectural sense

These require human review.

---

## What remains judgment-based

### Domain boundaries

The manifest generator can suggest domain boundaries from import graphs and directory structure. It cannot determine whether two modules that are tightly coupled *should* be one domain or whether the coupling should be broken.

Rule of thumb: if a change to module A almost always requires a change to module B, they belong in the same domain. If they can change independently, they are candidates for separate domains.

### Facade precision

A facade blurb that says "processes payments" is technically accurate but useless to a specialist agent that needs to know whether the call is synchronous, what happens on timeout, and whether a charge is reversed on downstream failure.

Useful facade blurbs include: synchrony, idempotency, side effects, failure modes, what the caller must ensure before calling, and what state is left on failure.

Review facade blurbs whenever a domain is involved in a production incident — incidents almost always reveal that the facade description was incomplete.

### Cross-cutting convention freshness

Conventions become stale when the team evolves its standards. A convention that was added for a framework that has since been replaced still appears in CLAUDE.md and the manifest. Someone must periodically review and retire stale conventions.

Schedule: review cross-cutting conventions quarterly, or whenever a major framework or tooling change is made.

---

## Review cadence

| Review | Frequency | Who | Time required |
|--------|-----------|-----|---------------|
| Weekly delta re-run | Weekly | Architect | 15 min |
| Facade API review (hot domains) | Per feature PR that touches the domain | Domain lead | 10 min per PR |
| Full manifest audit | Quarterly | Architect + domain leads | 1-2 hours |
| Convention retirement | Quarterly or after major framework change | Architect | 30 min |

---

## Common drift patterns and remedies

| Pattern | How it happens | Remedy |
|---------|---------------|--------|
| Files not in manifest | Developer adds a module without running the generator | Add manifest update to PR checklist |
| Stale facade blurbs | Interface changes without updating the blurb | Domain lead reviews facade on every PR that changes the API |
| Overly broad domain | Everything ends up in "core" | Split when a domain has more than 20 files or when two responsibilities have different change rates |
| Convention rot | Old conventions stay in CLAUDE.md after the practice is retired | Quarterly convention review |
| Phantom domains | Domain exists in manifest but all files have been deleted | Weekly delta re-run catches these |

---

## Escalation

If two teams disagree about where a file or API belongs, the architect decides and documents the decision as an ADR with a short rationale. The ADR prevents the same argument from recurring when the next person encounters the boundary.
