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
Requirements
1.  GitHub Issue           → /pm/add-feature or /pm/report-bug
2.  Figma Review           → manual extraction into issue (conditional)

Design
3.  Impact Analysis        → /apply-change — reads system-manifest.yaml, registries; outputs .hitl/current-change.yaml
4.  ROI Estimate           → if >1 day effort, add to issue; see roi-estimation.md (conditional)
5.  Update Docs            → /generate-docs — HLD/LLD/ADR; architect approves HLD before LLD
6.  Update IaC             → manifests, migrations, configs (conditional)
7.  Test Case Planning     → reads LLD + registries; records in issue and .hitl/current-change.yaml
8.  Training Plan Stub     → if new capability introduced (conditional)
9.  Package Decision Packet → architect assembles docs/decisions/issue-<N>.yaml; one per domain-independent slice

Build (TDD)
10. Generate Tests (RED)   → /tdd — reads LLD path from packet + system-manifest.yaml; writes to tests/
11. Human Reviews Tests    → /qa/review-tests — reads same LLD + incident registry; updates test registry
12. Tests Improve Design   → /tdd — updates LLD at same path if gaps found; architect re-reviews if significant
13. Verify RED             → all new tests must fail; resolve any that pass before proceeding
14. Generate Code (GREEN)  → /tdd — reads tests/, LLD (step 12), system-manifest.yaml, CLAUDE.md
15. Verify GREEN           → all tests pass; regression fix loops back to step 14
16. Refactor               → rerun tests after each change; done when no further simplification possible
17. Convention Checks      → /check-conventions — zero violations required before proceeding

Verify
18. Code Review Round 1    → /check-implementation — reads implementation + LLD (step 12) + system-manifest.yaml
19. Code Review Round 2    → /check-implementation — reads implementation + tests/ + test plan from .hitl/current-change.yaml
20. Rerun Tests            → confirm no regressions from review fixes
21. Reconcile Docs         → update LLD (/generate-docs) or fix code; document decision; if fix code, rerun 18–20

Assess
22. Downstream Impact Brief → /impact-brief — reads .hitl/current-change.yaml, diff, manifest, registries
23. Rollout Plan            → /ops/review-release — ops reviews section 5 of step 22; approves before PR

Ship
24. Create PR              → issue + HLD/LLD + IaC + code + tests + packet + brief + plan
25. Integration Verify     → /architect/verify-traceability — each slice E2E + cross-slice composition
26. Figma Comparison       → lead compares to Figma from step 2; zero unresolved differences (conditional)
27. Merge + Canary Deploy  → /ops/monitor-canary — lead merges; remaining slices rebase + rerun 17–19
28. Promote or Rollback    → verify go/no-go criteria from step 23; pause on failure, lead decides

Post-Ship
29. 30-day ROI Check       → reads baseline from step 4 issue; see roi-estimation.md (conditional)
30. 90-day ROI Check       → reads step 4 + step 29; update ADR Actual Outcome; see roi-estimation.md (conditional)
```

## Reference Files

Detailed procedures are in supporting files — load only what you need:

| File | Contains |
|------|---------|
| `workflow-steps.md` | Full step-by-step detail for each of the 30 steps |
| `tdd-design.md` | TDD-as-design three-phase loop, contract tests, worked examples |
| `roi-estimation.md` | ROI template, value dimensions, verification cadence |
| `downstream-impact.md` | Impact brief 5 sections, risk-rated rollout plan table |
| `registries.md` | Test registry + incident registry schema and usage patterns |

## Standards Quick Reference

**Code generation:** inline comments on non-obvious logic only; type hints everywhere; async/await for all I/O; security-first.

**Testing:** tests exercise real service code; external APIs mocked; every feature needs happy path + error + edge + boundary; every bug fix needs a regression test; test names describe behavior.

**API design:** endpoints scoped to owning entity; consistent auth; 404 not 403 for ownership failures; version for backwards compatibility.

**Code review:** two rounds using `/check-implementation` (`spec-conformance-reviewer` agent) — Round 1 reads implementation + LLD + system-manifest (structure/security/LLD adherence); Round 2 reads implementation + tests + test plan (edge cases/regressions/completeness). Both rounds read from repo files, not from memory.

**Integration verification (team lead only):** run feature E2E; compare against HLD/LLD; check full traceability chain; Figma comparison if design exists.
