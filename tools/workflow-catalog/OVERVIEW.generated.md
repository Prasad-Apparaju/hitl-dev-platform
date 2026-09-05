# Workflow Overview (generated)

Derived from `tools/workflow-catalog/catalog.yaml`. Do not edit by hand.

## spine (31 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Requirements.1 | Issue | issue |
| 2 | Requirements.2 | Figma | figma |
| 3 | Design.1 | ROI | roi |
| 4 | Design.2 | Docs | docs |
| 4a | Design.2a | Basln | baseline |
| 4b | Design.2b | SecDsn | sec_design |
| 4c | Design.2c | CVE | cve_audit |
| 5 | Design.3 | IaC | iac |
| 6 | Design.4 | Tests | test_plan |
| 7 | Design.5 | Train | training |
| 8 | Design.6 | Packet | packet |
| 8a | Design.6a | VfyDsn | adv_design |
| 9 | Build.1 | RED | red |
| 10 | Build.2 | TstRvw | test_review |
| 11 | Build.3 | Dsn+ | design_plus |
| 12 | Build.4 | VfyRED | verify_red |
| 13 | Build.5 | GREEN | green |
| 14 | Build.6 | VfyGRN | verify_green |
| 15 | Build.7 | Refact | refactor |
| 16 | Build.8 | Conv | conventions |
| 16a | Build.8a | VfyCode | adv_code |
| 17 | Verify.1 | Rvw1 | review1 |
| 18 | Verify.2 | Rvw2 | review2 |
| 18a | Verify.2a | ArchRvw | arch_review |
| 19 | Verify.3 | Rerun | rerun |
| 20 | Verify.4 | Recncl | reconcile |
| 21 | Verify.5 | QAVfy | qa_verify |
| 22 | Assess.1 | ImpBrf | impact_brief |
| 23 | Assess.2 | Rollout | rollout |
| 24 | Ship.1 | VfyPR | verify_pr |
| 25 | Ship.2 | IntVfy | integration_verify |
| 26 | Ship.3 | Figma2 | figma_compare |
| 27 | Ship.4 | Deploy | deploy |
| 27a | Ship.4a | Pentest | pentest |
| 28 | Ship.5 | Promote | promote |
| 29 | Post-Ship.1 | Retro | retro |
| 30 | Post-Ship.2 | 30dROI | roi_30 |
| 31 | Post-Ship.3 | 90dROI | roi_90 |

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

## docs (6 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Docs Change.1 | Issue | issue |
| 2 | Docs Change.2 | Scope | scope |
| 3 | Docs Change.3 | Draft | draft |
| 4 | Docs Change.4 | Review | doc_review |
| 5 | Docs Change.5 | Reconcile | reconcile |
| 6 | Docs Change.6 | Merge | merge |

## greenfield (5 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | PRD Setup.1 | CLAUDE.md | claude_md |
| 2 | PRD Setup.2 | Manifest | manifest |
| 3 | PRD Setup.3 | Issue | create_issue |
| 4 | PRD Setup.4 | Ready | confirm_ready |
| 5 | PRD Setup.5 | Platform | platform_roadmap |

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

## platform (17 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Survey.1 | Register | derive_register |
| 2 | Survey.2 | Roadmap | roadmap |
| 3 | Verify.1 | Suites | test_suites |
| 4 | Verify.2 | E2E | e2e_env |
| 5 | Verify.3 | Trace | traceability |
| 6 | Deliver.1 | Build | build_repro |
| 7 | Deliver.2 | Playbook | deploy_playbook |
| 8 | Deliver.3 | CD | cd_from_ci |
| 9 | Operate.1 | Observ | obs_established |
| 10 | Operate.2 | Canary | canary_exercised |
| 11 | Operate.3 | SecPos | sec_posture |
| 12 | Parity.1 | Golden | golden_dataset |
| 13 | Parity.2 | Shadow | shadow_run |
| 14 | Cutover.1 | CutPlan | cutover_plan |
| 15 | Cutover.2 | DualRun | dual_run |
| 16 | Cutover.3 | Sunset | decommission |
| 17 | Ready.1 | Ready | delivery_ready |

## release (12 steps)

| # | phase.step | label | key |
|---|---|---|---|
| 1 | Prepare.1 | Scope | rc_scope |
| 2 | Prepare.2 | Notes | changelog |
| 3 | Prepare.3 | Bump | version_bump |
| 4 | Verify.1 | Gates | gates |
| 5 | Gate.1 | Review | adversarial_review |
| 6 | Gate.2 | Resolve | resolve_findings |
| 7 | Publish.1 | Build | build |
| 8 | Publish.2 | Publish | publish |
| 9 | Publish.3 | Tag | tag |
| 10 | Confirm.1 | Verify | install_verify |
| 11 | Confirm.2 | Announce | announce |
| 12 | Confirm.3 | Retire | retire |

