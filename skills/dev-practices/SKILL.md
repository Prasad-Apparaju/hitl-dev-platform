---
name: dev-practices
description: Full HITL development practices workflow covering change tiers, TDD-as-design, doc-driven development, code review, integration verification, downstream impact, rollout planning, and ROI tracking. Load this skill when starting any Tier 1+ change or when the developer asks how to apply the HITL process to a change.
argument-hint: "[change description or issue number]"
disable-model-invocation: true
---

# Development Practices

This skill defines the HITL change workflow. Apply it based on the change tier:

| Tier | Change type | Process |
|------|-------------|---------|
| 0 — Trivial | Typo, config value, log message | Standard PR only |
| 1 — Bug fix | Regression fix, minor behavioral correction | Steps 1–2 + code/test steps; skip training plan |
| 2 — Normal feature | Bounded, well-understood change within one domain | Full workflow |
| 3 — Non-trivial / cross-domain | Migrations, cross-domain, AI systems, security, data model | Full workflow + HLD review gate |
| 4 — Incident / P0 | Active production problem | Fix first, full docs within 48 hours |

When in doubt, use the heavier process. If you are touching more than one domain or writing more than a few dozen lines, treat it as Tier 2 or above.

## Core Rules

**Do not implement from chat-only requirements.** Source artifacts must exist first.

**Refusal condition:** If no GitHub issue or approved LLD exists for a Tier 2+ change, stop and say so.

**Source-of-truth order:**
1. GitHub issue or PRD
2. Approved HLD/LLD
3. ADR or decision packet
4. `docs/system-manifest.yaml` domain
5. Existing code

## Workflow Summary (Tier 2)

```
1.  GitHub Issue         → describe the change, root cause, proposed solution
2.  Impact Analysis      → /apply-change skill — also queries test + incident registry
2a. ROI Estimate         → if >1 day effort, add to issue (see workflow-steps.md §ROI)
3.  Update Docs          → HLD/LLD/ADR before code
4.  Update IaC           → manifests, migrations, configs
5.  Test Case Planning   → identify tests to add, update, remove
5a. Training Plan Stub   → if new capability introduced (see workflow-steps.md §Training)
6–8. TDD Cycle           → /tdd skill: RED → GREEN → Refactor
9.  Code Review Round 1  → structure, security, LLD adherence
10. Code Review Round 2  → edge cases, regressions, completeness
11. Rerun Tests          → confirm no regressions from review fixes
12. Reconcile Docs       → drift is a decision, not silence
13. PR                   → links issue + docs + IaC + code + tests
14. Downstream Impact    → /impact-brief skill
15. Rollout Plan         → risk-rated canary with go/no-go criteria
16. Integration Verify   → team lead runs E2E, checks traceability
17. Figma Comparison     → if design exists, compare and resolve differences
18. Canary Deploy        → per the rollout plan
19. Promote or Rollback  → lead decision
20. Merge + Demo         → after lead sign-off; demo to PM
21. 30-day ROI Check     → metric direction, cost vs estimate
22. 90-day ROI Check     → actual vs estimated ROI; update ADR
```

## Reference Files

Detailed procedures are in supporting files — load only what you need:

| File | Contains |
|------|---------|
| `workflow-steps.md` | Full step-by-step detail for each of the 22 steps |
| `tdd-design.md` | TDD-as-design three-phase loop, contract tests, worked examples |
| `roi-estimation.md` | ROI template, value dimensions, verification cadence |
| `downstream-impact.md` | Impact brief 5 sections, risk-rated rollout plan table |
| `registries.md` | Test registry + incident registry schema and usage patterns |

## Standards Quick Reference

**Code generation:** inline comments on non-obvious logic only; type hints everywhere; async/await for all I/O; security-first.

**Testing:** tests exercise real service code; external APIs mocked; every feature needs happy path + error + edge + boundary; every bug fix needs a regression test; test names describe behavior.

**API design:** endpoints scoped to owning entity; consistent auth; 404 not 403 for ownership failures; version for backwards compatibility.

**Code review:** two rounds — Round 1 before tests (structure/security/LLD adherence), Round 2 after all tests pass (edge cases/regressions/completeness).

**Integration verification (team lead only):** run feature E2E; compare against HLD/LLD; check full traceability chain; Figma comparison if design exists.
