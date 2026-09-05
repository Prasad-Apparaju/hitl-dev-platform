# HITL Command Map (generated)

Generated from `tools/workflow-catalog/catalog.yaml` by `tools/workflow-catalog/derive.py command-map`. **Do not edit by hand.**

Each row is one step of the development delivery spine, with the command that executes it (a skill/command name, or the literal `manual` / `guided`) and the owning role.

## Development — deliver a change (31 steps)

| # | Step | Phase | Command | Role |
|---|---|---|---|---|
| 1 | GitHub Issue | Requirements | manual | PM |
| 2 | Figma Review | Requirements | manual | PM |
| 3 | ROI Estimate | Design | guided | PM |
| 4 | Update Docs | Design | dev-generate-docs | Architect |
| 4a | Baseline Measurement | Design | ops-measure-baseline | Ops |
| 4b | Security Design Review | Design | dev-review-security | Architect |
| 4c | Dependency + CVE Audit | Design | ops-audit-dependencies | Ops |
| 5 | Update IaC | Design | ops-apply-iac | Ops |
| 6 | Test Case Planning | Design | qa-plan-tests | QA |
| 7 | Training Plan Stub | Design | guided | PM |
| 8 | Package Decision Packet | Design | manual | Architect |
| 8a | Verification Review (Design) | Design | dev-verification-review | Architect |
| 9 | AI Generates Tests (RED) | Build | dev-tdd | Dev |
| 10 | Human Reviews Tests | Build | qa-review-tests | QA |
| 11 | Tests Improve the Design | Build | dev-tdd | Dev |
| 12 | Verify RED | Build | manual | Dev |
| 13 | Generate Code (GREEN) | Build | dev-tdd | Dev |
| 14 | Verify GREEN | Build | manual | Dev |
| 15 | Refactor | Build | manual | Dev |
| 16 | Convention Checks | Build | dev-check-conventions | Dev |
| 16a | Verification Review (Code) | Build | dev-verification-review | Architect |
| 17 | Code Review Round 1 | Verify | dev-review-lld-adherence | Dev |
| 18 | Code Review Round 2 | Verify | dev-review-security | Dev |
| 18a | Architect Code Review | Verify | architect-review-code | Architect |
| 19 | Rerun Tests | Verify | manual | Dev |
| 20 | Reconcile Docs | Verify | dev-generate-docs | Dev |
| 21 | QA Post-Handoff Verification | Verify | qa-verify-quality | QA |
| 22 | Downstream Impact Brief | Assess | dev-impact-brief | Dev |
| 23 | Risk-Rated Rollout Plan | Assess | ops-review-release | Ops |
| 24 | Verify PR Completeness | Ship | manual | Dev |
| 25 | Integration Verification | Ship | architect-verify-traceability | Architect |
| 26 | Figma Comparison | Ship | manual | QA |
| 27 | Build, Migrate, Apply, Deploy | Ship | ops-deploy | Ops |
| 27a | Penetration Test | Ship | ops-pentest | Ops |
| 28 | Promote or Rollback | Ship | ops-post-deploy-monitor | Ops |
| 29 | Closing Retrospective | Post-Ship | dev-retro | Dev |
| 30 | 30-Day ROI Check | Post-Ship | guided | PM |
| 31 | 90-Day ROI Check | Post-Ship | guided | PM |

