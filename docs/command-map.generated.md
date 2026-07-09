# HITL Command Map (generated)

Generated from `tools/workflow-catalog/catalog.yaml` by `tools/workflow-catalog/derive.py command-map`. **Do not edit by hand.**

Each row is one step of the development delivery spine, with the command that executes it (a skill/command name, or the literal `manual` / `guided`) and the owning role.

## Development — deliver a change (31 steps)

| # | Step | Phase | Command | Role |
|---|---|---|---|---|
| 1 | GitHub Issue | Requirements | manual | PM |
| 2 | Figma Review | Requirements | manual | PM |
| 3 | Impact Analysis | Design | dev-apply-change | Dev |
| 4 | ROI Estimate | Design | guided | PM |
| 5 | Update Docs | Design | dev-generate-docs | Architect |
| 6 | Update IaC | Design | ops-apply-iac | Ops |
| 7 | Test Case Planning | Design | qa-plan-tests | QA |
| 8 | Training Plan Stub | Design | guided | PM |
| 9 | Package Decision Packet | Design | manual | Architect |
| 10 | AI Generates Tests (RED) | Build | dev-tdd | Dev |
| 11 | Human Reviews Tests | Build | qa-review-tests | QA |
| 12 | Tests Improve the Design | Build | dev-tdd | Dev |
| 13 | Verify RED | Build | manual | Dev |
| 14 | Generate Code (GREEN) | Build | dev-tdd | Dev |
| 15 | Verify GREEN | Build | manual | Dev |
| 16 | Refactor | Build | manual | Dev |
| 17 | Convention Checks | Build | dev-check-conventions | Dev |
| 18 | Code Review Round 1 | Verify | dev-review-lld-adherence | Dev |
| 19 | Code Review Round 2 | Verify | dev-review-security | Dev |
| 19a | Architect Code Review | Verify | architect-review-code | Architect |
| 20 | Rerun Tests | Verify | manual | Dev |
| 21 | Reconcile Docs | Verify | dev-generate-docs | Dev |
| 22 | QA Post-Handoff Verification | Verify | qa-verify-quality | QA |
| 23 | Downstream Impact Brief | Assess | dev-impact-brief | Dev |
| 24 | Risk-Rated Rollout Plan | Assess | ops-review-release | Ops |
| 25 | Verify PR Completeness | Ship | manual | Dev |
| 26 | Integration Verification | Ship | architect-verify-traceability | Architect |
| 27 | Figma Comparison | Ship | manual | QA |
| 28 | Build, Migrate, Apply, Deploy | Ship | ops-deploy | Ops |
| 29 | Promote or Rollback | Ship | ops-post-deploy-monitor | Ops |
| 30 | 30-Day ROI Check | Post-Ship | guided | PM |
| 31 | 90-Day ROI Check | Post-Ship | guided | PM |

