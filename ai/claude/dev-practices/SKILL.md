---
description: Full HITL development practices workflow covering change tiers, TDD-as-design, doc-driven development, code review, integration verification, downstream impact, rollout planning, and ROI tracking. Load this skill when starting any Tier 1+ change or when the developer asks how to apply the HITL process to a change.
argument-hint: "[change description or issue number]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---


# Development Practices

## Contents

- [Change tiers](#development-practices) — this section: which process a change gets, and why
- [Core Rules](#core-rules)
- [Workflow Summary (Tier 2)](#workflow-summary-tier-2)
- [Reference Files](#reference-files)
- [Standards Quick Reference](#standards-quick-reference)

This skill defines the HITL change workflow. Apply it based on the change tier:

| Tier | Change type | Process |
|------|-------------|---------|
| 0 — Trivial | Typo, config value, log message | Intake, then the lightest plan: ceremony steps offered pre-declined, one confirmation |
| 1 — Bug fix | Regression fix, minor behavioral correction | Same as tier 0. The TDD steps can never be omitted, though they may be thinned to a starter — a fix without a failing test first is not a fix |
| 2 — Normal feature | Bounded, well-understood change within one domain | Full workflow |
| 3 — Non-trivial / cross-domain | Migrations, cross-domain, AI systems, security, data model | Full workflow + HLD review gate |
| 4 — Incident / P0 | Active production problem | Fix first, full docs within 48 hours |

When in doubt, use the heavier process. If you are touching more than one domain or writing more than a few dozen lines, treat it as Tier 2 or above.

**Every tier goes through `/hitl:dev-start-change`.** There is no tier that skips intake: the session
gate blocks edits made through the Edit and Write tools until a change is active, and it does not read
the tier. (Writes made through the shell are not covered by that gate — a known gap, tracked
separately.) What a low tier buys is a *shorter plan*, not an exemption.

Dropped steps are recorded in the change file for every workflow. They reach the durable roll-up
(`.hitl/skip-ledger.yaml`), which is what lets a later change in the same area pick them back up, at
the impact step of `/hitl:dev-apply-change` — so today that durability applies to the **development**
workflow. On other routes the record lives in the change file only, which the next intake replaces.

Tier 0 and 1 require `tier_set_by` and `tier_reason` in the change file, because those tiers unlock
the batch-decline path at intake.

**The consequential tier call is 3 versus 2, not 1 versus 2.** Dropping from 3 to 2 takes `impact`,
`packet`, `arch_review`, `qa_verify` and `rollout` off the protected floor in one move; dropping from
2 to 1 only affects `integration_verify`. `deploy` and `promote` are floor at every tier. Tier 2 is
also the default and asks for no justification, so the boundary that matters is the one with the
least ceremony around it. Slow down on it deliberately.

## Core Rules

**Do not implement from chat-only requirements.** Source artifacts must exist first.

**Refusal condition:** If no GitHub issue or approved LLD exists for a Tier 2+ change, stop and say:

> No LLD found for this component.
>
> - **New project:** Run `/architect/design-system` to generate design docs from your PRD first.
> - **Existing codebase not yet in HITL** (no manifest, no registries): Run `/hitl:dev-start-brownfield` to establish the full baseline — manifest, priority LLDs, and registry stubs — before starting change work.
> - **Existing HITL project, one undocumented component:** Run `/hitl:dev-generate-docs` for the affected component to create its LLD. Then verify that the test registry and incident registry exist (see Prerequisites in workflow-steps.md) before resuming.

**Source-of-truth order:**
1. GitHub issue or PRD
2. Approved HLD/LLD
3. ADR or decision packet
4. `docs/system-manifest.yaml` domain
5. Existing code

## Workflow Summary (Tier 2)

Impact analysis is not a numbered step: it runs at intake (`/hitl:dev-start-change` → `/hitl:dev-apply-change`), reads system-manifest.yaml and the registries, and produces the plan below plus the impact record. Lettered steps are substeps of the integer above them; the ones marked (conditional) are activated per change by the sizing rules and recorded not_applicable otherwise.

```
Requirements
1.  GitHub Issue           → /pm/add-feature or /pm/report-bug
2.  Figma Review           → manual extraction into issue (conditional)

Design
3.  ROI Estimate           → if >1 day effort, record in `.hitl/current-change.yaml` under `roi_estimate`; post pointer comment on issue; see roi-estimation.md (conditional)
4.  Update Docs            → /hitl:dev-generate-docs — HLD/LLD/ADR; architect approves HLD before LLD
4a. Baseline Measurement   → /hitl:ops-measure-baseline — a before-measurement so "faster" is a number; activated by an API surface or a data migration (conditional)
4b. Security Design Review → /hitl:dev-review-security --phase design — threat model + STRIDE; activated when the change is security-sensitive, changes an interface or migrates data; LLD cannot be architect-approved until Critical/High findings have mitigations (conditional)
4c. Dependency + CVE Audit → /hitl:ops-audit-dependencies — published vulnerabilities of the versions being moved to; activated by a dependency change or a security-sensitive change (conditional)
5.  Update IaC             → manifests, migrations, rollback migrations, configs; exit requires /hitl:ops-verify-scripts --level syntax
6.  Test Case Planning     → /hitl:qa-plan-tests — QA queries incident history; QA scenarios acknowledged before TDD
7.  Training Plan Stub     → if new capability introduced (conditional)
8.  Package Decision Packet → architect assembles docs/decisions/issue-<N>.yaml; one per domain-independent slice
8a. Adversarial Design Review → /hitl:dev-adversarial-review — clean-context reviewers briefed to refute the design; findings put to you before anything is fixed

Build (TDD)
9.  Generate Tests (RED)   → /hitl:dev-tdd — unit tests + integration tests + Playwright E2E stubs (test.skip) + smoke journey; all written before any implementation
10. Human Reviews Tests    → /hitl:qa-review-tests — verifies unit, integration, E2E stubs (one per AC), smoke journey, incident regressions, ≥90% coverage gate; blocks implementation if gaps
11. Tests Improve Design   → /hitl:dev-tdd — updates LLD at same path if gaps found; architect re-reviews if significant
12. Verify RED             → unit/integration tests must fail; E2E stubs skipped; smoke suite runs (existing journeys only)
13. Generate Code (GREEN)  → /hitl:dev-tdd — reads tests/, LLD (Tests Improve the Design), system-manifest.yaml, CLAUDE.md
14. Verify GREEN           → unit + integration pass; coverage ≥90% enforced (AI generates gap tests if needed); smoke runs
15. Refactor               → rerun tests after each change; done when no further simplification possible
16. Convention Checks      → /hitl:dev-check-conventions — zero violations required before proceeding
16a. Adversarial Code Review → /hitl:dev-adversarial-review — the same refuting review against the code, before the review rounds

Verify
17. Code Review Round 1    → /hitl:dev-review-lld-adherence — reads implementation + LLD (Tests Improve the Design) + system-manifest.yaml
18. Code Review Round 2    → /hitl:dev-review-lld-adherence — reads implementation + tests/ + test plan from .hitl/current-change.yaml
18a. Architect Code Review → /hitl:architect-review-code — creates GitHub PR with checklist; architect reviews on GitHub (line comments + approve/request changes); revisions return to Generate Code (GREEN) or Refactor; PR is NOT merged here
19. Rerun Tests            → confirm no regressions from review fixes
20. Reconcile Docs         → update LLD (/hitl:dev-generate-docs) or fix code; document decision; if fix code, rerun 17–19
21. QA Post-Handoff Verify → /hitl:qa-verify-quality — unskips + runs E2E Playwright (desktop + iPhone 15 + Pixel 7); runs smoke suite; blocks if any fail; /hitl:qa-report-defect for each blocking issue

Assess
22. Downstream Impact Brief → /hitl:dev-impact-brief — reads .hitl/current-change.yaml, diff, manifest, registries
23. Rollout Plan            → /hitl:ops-review-release — ops reviews section 5 of the Downstream Impact Brief; plan is added to the open PR at Verify PR Completeness

Ship
24. Verify PR Completeness → confirm PR (created at Architect Code Review) has: issue link, HLD/LLD, IaC, code, tests, decision packet, impact brief, rollout plan; copy token costs to registry
25. Integration Verify     → /hitl:architect-verify-traceability — traceability chain + E2E evidence check + smoke suite re-run + cross-slice composition
26. Figma Comparison       → lead compares to Figma from Figma Review; zero unresolved differences (conditional)
27. Build + Backup + Migrate + IaC + Observability + Drift Check + Deploy → /hitl:ops-backup-database (before migrations) → /hitl:ops-migrate-database (if migrations) → /hitl:ops-apply-iac (if IaC) → /hitl:ops-setup-observability (required) → /hitl:ops-build → /hitl:ops-detect-drift (Tier 2+, blocks on `blocked` result) → /hitl:ops-deploy → /hitl:ops-monitor-canary
27a. Penetration Test      → /hitl:ops-pentest — OWASP Top 10 automated scan + manual checklist; activated with the security steps (4b); floor once active: skipping it is a named person's risk-accepted decision with a waiver; `blocked` result requires remediation + retest before the change is closed (conditional)
28. Promote or Rollback + Monitor → /hitl:ops-rollback if rollback (includes /hitl:ops-backup-database restore); /hitl:ops-post-deploy-monitor required after final promotion (soak: Low 1h, Med 4h, High 12h, Crit 24h)

Post-Ship
29. Closing Retrospective  → /hitl:dev-retro — what happened, what is still open, how the sizing turned out; reads the change file, impact record and review records; lands in .hitl/retro/; floor
30. 30-day ROI Check       → reads roi_estimate from .hitl/current-change.yaml; see roi-estimation.md (conditional)
31. 90-day ROI Check       → reads roi_estimate + 30-Day ROI Check findings; update ADR Actual Outcome; see roi-estimation.md (conditional)
```

Security Review (Code) — `/hitl:dev-review-security --phase code` (SAST: semgrep OWASP, Bandit, ESLint-security, Gosec + code-level OWASP checklist) — is not a numbered step. Run it alongside the code review rounds whenever 4b was active; Critical/High findings block the PR.

## Reference Files

Detailed procedures are in supporting files — load only what you need:

| File | Contains |
|------|---------|
| `workflow-steps.md` | Full step-by-step detail for each of the 31 steps |
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
