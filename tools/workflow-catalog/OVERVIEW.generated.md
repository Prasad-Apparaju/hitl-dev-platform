# Workflow Overview (generated)

Derived from `tools/workflow-catalog/catalog.yaml`. Do not edit by hand.

## spine (31 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Requirements.1 | Issue | issue |
| 2 | Requirements.2 | Figma | figma |
| 3 | Design.1 | Impact | impact |
| 4 | Design.2 | ROI | roi |
| 5 | Design.3 | Docs | docs |
| 6 | Design.4 | IaC | iac |
| 7 | Design.5 | Tests | test_plan |
| 8 | Design.6 | Train | training |
| 9 | Design.7 | Packet | packet |
| 10 | Build.1 | RED | red |
| 11 | Build.2 | TstRvw | test_review |
| 12 | Build.3 | Dsn+ | design_plus |
| 13 | Build.4 | VfyRED | verify_red |
| 14 | Build.5 | GREEN | green |
| 15 | Build.6 | VfyGRN | verify_green |
| 16 | Build.7 | Refact | refactor |
| 17 | Build.8 | Conv | conventions |
| 18 | Verify.1 | Rvw1 | review1 |
| 19 | Verify.2 | Rvw2 | review2 |
| 19a | Verify.2a | ArchRvw | arch_review |
| 20 | Verify.3 | Rerun | rerun |
| 21 | Verify.4 | Recncl | reconcile |
| 22 | Verify.5 | QAVfy | qa_verify |
| 23 | Assess.1 | ImpBrf | impact_brief |
| 24 | Assess.2 | Rollout | rollout |
| 25 | Ship.1 | VfyPR | verify_pr |
| 26 | Ship.2 | IntVfy | integration_verify |
| 27 | Ship.3 | Figma2 | figma_compare |
| 28 | Ship.4 | Deploy | deploy |
| 29 | Ship.5 | Promote | promote |
| 30 | Post-Ship.1 | 30dROI | roi_30 |
| 31 | Post-Ship.2 | 90dROI | roi_90 |

## brownfield (11 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Brownfield Setup.1 | MapCode | map_code |
| 2 | Brownfield Setup.2 | CLAUDE.md | claude_md |
| 3 | Brownfield Setup.3 | Manifest | manifest |
| 4 | Brownfield Setup.4 | ArchRvw | arch_review |
| 5 | Brownfield Setup.5 | Pipeline | verify_pipeline |
| 6 | Brownfield Setup.6 | Observ | observability |
| 7 | Brownfield Setup.7 | Docs | priority_docs |
| 8 | Brownfield Setup.8 | Registries | seed_registries |
| 9 | Brownfield Setup.9 | Graphify | graphify |
| 10 | Brownfield Setup.10 | Issue | create_issue |
| 11 | Brownfield Setup.11 | Ready | confirm_ready |

## greenfield (4 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | PRD Setup.1 | CLAUDE.md | claude_md |
| 2 | PRD Setup.2 | Manifest | manifest |
| 3 | PRD Setup.3 | Issue | create_issue |
| 4 | PRD Setup.4 | Ready | confirm_ready |

## migration (9 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Migration Setup.1 | Context | collect_context |
| 2 | Migration Setup.2 | CLAUDE.md | claude_md |
| 3 | Migration Setup.3 | Manifest | manifest |
| 4 | Migration Setup.4 | DirSetup | dir_setup |
| 5 | Migration Setup.5 | SrcAnal | source_analysis |
| 6 | Migration Setup.6 | ExtDocs | ext_docs |
| 7 | Migration Setup.7 | Registries | seed_registries |
| 8 | Migration Setup.8 | Issue | create_issue |
| 9 | Migration Setup.9 | Ready | confirm_ready |

## migration_review (5 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Migration Review.1 | Context | read_context |
| 2 | Migration Review.2 | Evaluate | evaluate |
| 3 | Migration Review.3 | MigRvw | write_review |
| 4 | Migration Review.4 | Brief | write_brief |
| 5 | Migration Review.5 | Handoff | handoff |

