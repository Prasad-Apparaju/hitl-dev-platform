---
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

**Refusal condition:** If no GitHub issue or approved LLD exists for a Tier 2+ change, stop and say:

> No LLD found for this component.
>
> - **New project:** Run `/architect/design-system` to generate design docs from your PRD first.
> - **Existing codebase not yet in HITL** (no manifest, no registries): Run `/hitl:start-brownfield` to establish the full baseline — manifest, priority LLDs, and registry stubs — before starting change work.
> - **Existing HITL project, one undocumented component:** Run `/hitl:dev-generate-docs` for the affected component to create its LLD. Then verify that the test registry and incident registry exist (see Prerequisites in workflow-steps.md) before resuming.

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
3.  Impact Analysis        → /hitl:dev-apply-change — reads system-manifest.yaml, registries; outputs .hitl/current-change.yaml
4.  ROI Estimate           → if >1 day effort, record in `.hitl/current-change.yaml` under `roi_estimate`; post pointer comment on issue; see roi-estimation.md (conditional)
5.  Update Docs            → /hitl:dev-generate-docs — HLD/LLD/ADR; architect approves HLD before LLD
5a. Security Review (Design) → /hitl:dev-review-security --phase design — threat model + STRIDE; required Tier 3+, recommended Tier 2+; LLD cannot be architect-approved until Critical/High findings have mitigations (conditional)
6.  Update IaC + Verify Scripts → manifests, migrations, rollback migrations, configs; exit requires /hitl:ops-verify-scripts --level syntax (conditional)
7.  Test Case Planning     → /hitl:qa-plan-tests — QA queries incident history; QA scenarios acknowledged before TDD
8.  Training Plan Stub     → if new capability introduced (conditional)
9.  Package Decision Packet → architect assembles docs/decisions/issue-<N>.yaml; one per domain-independent slice

Build (TDD)
10. Generate Tests (RED)   → /hitl:dev-tdd — unit tests + integration tests + Playwright E2E stubs (test.skip) + smoke journey; all written before any implementation
11. Human Reviews Tests    → /hitl:qa-review-tests — verifies unit, integration, E2E stubs (one per AC), smoke journey, incident regressions, ≥90% coverage gate; blocks implementation if gaps
12. Tests Improve Design   → /hitl:dev-tdd — updates LLD at same path if gaps found; architect re-reviews if significant
13. Verify RED             → unit/integration tests must fail; E2E stubs skipped; smoke suite runs (existing journeys only)
14. Generate Code (GREEN)  → /hitl:dev-tdd — reads tests/, LLD (step 12), system-manifest.yaml, CLAUDE.md
15. Verify GREEN           → unit + integration pass; coverage ≥90% enforced (AI generates gap tests if needed); smoke runs
16. Refactor               → rerun tests after each change; done when no further simplification possible
16a. Security Review (Code) → /hitl:dev-review-security --phase code — SAST (semgrep OWASP, Bandit, ESLint-security, Gosec) + code-level OWASP checklist; required Tier 3+, recommended Tier 2+; Critical/High block PR (conditional)
17. Convention Checks      → /hitl:dev-check-conventions — zero violations required before proceeding

Verify
18. Code Review Round 1    → /hitl:dev-review-lld-adherence — reads implementation + LLD (step 12) + system-manifest.yaml
19. Code Review Round 2    → /hitl:dev-review-lld-adherence — reads implementation + tests/ + test plan from .hitl/current-change.yaml
19a. Architect Code Review → /hitl:architect-review-code — creates GitHub PR with checklist; architect reviews on GitHub (line comments + approve/request changes); revisions return to step 14 or 16; PR is NOT merged here
20. Rerun Tests            → confirm no regressions from review fixes
21. Reconcile Docs         → update LLD (/hitl:dev-generate-docs) or fix code; document decision; if fix code, rerun 18–20
22. QA Post-Handoff Verify → /hitl:qa-verify-quality — unskips + runs E2E Playwright (desktop + iPhone 15 + Pixel 7); runs smoke suite; blocks if any fail; /hitl:qa-report-defect for each blocking issue

Assess
23. Downstream Impact Brief → /hitl:dev-impact-brief — reads .hitl/current-change.yaml, diff, manifest, registries
24. Rollout Plan            → /hitl:ops-review-release — ops reviews section 5 of step 23; plan is added to the open PR at step 25

Ship
25. Verify PR completeness → confirm PR (created at step 19a) has: issue link, HLD/LLD, IaC, code, tests, decision packet, impact brief, rollout plan; copy token costs to registry
26. Integration Verify     → /hitl:architect-verify-traceability — traceability chain + E2E evidence check + smoke suite re-run + cross-slice composition
27. Figma Comparison       → lead compares to Figma from step 2; zero unresolved differences (conditional)
28. Build + Backup + Migrate + IaC + Observability + Drift Check + Deploy → /hitl:ops-backup-database (before migrations) → /hitl:ops-migrate-database (if migrations) → /hitl:ops-apply-iac (if IaC) → /hitl:ops-setup-observability (required) → /hitl:ops-build → /hitl:ops-detect-drift (Tier 2+, blocks on `blocked` result) → /hitl:ops-deploy → /hitl:ops-monitor-canary
29. Promote or Rollback + Monitor → /hitl:ops-rollback if rollback (includes /hitl:ops-backup-database restore); /hitl:ops-post-deploy-monitor required after final promotion (soak: Low 1h, Med 4h, High 12h, Crit 24h)

Post-Ship
30. Penetration Test       → /hitl:ops-pentest — OWASP Top 10 automated scan + manual checklist; optional for Tier 2+ after STABLE; required for Tier 3+ auth/payments/data changes; `blocked` result requires remediation + retest before change is closed (conditional)
31. 30-day ROI Check       → reads roi_estimate from .hitl/current-change.yaml; see roi-estimation.md (conditional)
32. 90-day ROI Check       → reads roi_estimate + step 31 findings; update ADR Actual Outcome; see roi-estimation.md (conditional)
```

## Reference Files

Detailed procedures are in supporting files — load only what you need:

| File | Contains |
|------|---------|
| `workflow-steps.md` | Full step-by-step detail for each of the 32 steps |
| `tdd-design.md` | TDD-as-design three-phase loop, contract tests, worked examples |
| `roi-estimation.md` | ROI template, value dimensions, verification cadence |
| `downstream-impact.md` | Impact brief 5 sections, risk-rated rollout plan table |
| `registries.md` | Test registry + incident registry schema and usage patterns |

## Standards Quick Reference

**Code generation:** inline comments on non-obvious logic only; type hints everywhere; async/await for all I/O; security-first.

**Testing:** tests exercise real service code; external APIs mocked; every feature needs happy path + error + edge + boundary; every bug fix needs a regression test; test names describe behavior.

**API design:** endpoints scoped to owning entity; consistent auth; 404 not 403 for ownership failures; version for backwards compatibility.

**Code review:** two rounds using `/hitl:dev-review-lld-adherence` (`spec-conformance-reviewer` agent) — Round 1 reads implementation + LLD + system-manifest (structure/security/LLD adherence); Round 2 reads implementation + tests + test plan (edge cases/regressions/completeness). Both rounds read from repo files, not from memory.

**Integration verification (team lead only):** run feature E2E; compare against HLD/LLD; check full traceability chain; Figma comparison if design exists.
