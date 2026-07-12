---
description: Find the right HITL command for any situation. Describe what you are trying to do and get a recommendation, or ask for a full directory of all available commands grouped by role.
argument-hint: "[what you're trying to do — or leave blank for the full command directory]"
disable-model-invocation: true
---

# HITL Help — Find the Right Command

**Input:** $ARGUMENTS

---

## If $ARGUMENTS is empty — show the full command directory

Output this exactly:

---

## HITL Command Directory

### Getting started

| Command | When to use |
|---|---|
| `/hitl:dev-start-change` | **Start work on an issue** — pick the issue, choose the workflow, seed the change. The front door for every change. |
| `/hitl:dev-start-from-prd` | New greenfield project — no code exists yet |
| `/hitl:dev-start-brownfield` | Existing codebase you want to bring into HITL |
| `/hitl:dev-start-migration` | Migrating from one system to another |
| `/hitl:dev-update` | Update the HITL plugin to the latest version |
| `/hitl:help` | This command — find the right command for any situation |

### Developer workflow

| Command | When to use |
|---|---|
| `/hitl:dev-practices` | Reference for the full 31-step delivery workflow (after a change is started) |
| `/hitl:dev-apply-change` | Analyze and plan a specific change before writing code |
| `/hitl:dev-tdd` | Run the TDD Red→Green→Refactor cycle (after LLD is approved) |
| `/hitl:dev-check-conventions` | Run semgrep, secrets scan, manifest drift, Mermaid lint |
| `/hitl:dev-review-lld-adherence` | Verify generated code matches the approved LLD |
| `/hitl:dev-review-security` | Threat model, SAST scan, or security baseline |
| `/hitl:dev-impact-brief` | Generate a risk-rated rollout plan for a change |
| `/hitl:dev-generate-docs` | Generate HLD, LLD, ADR for a feature or component |
| `/hitl:dev-conclude` | Turn a concluded Slack design thread into GitHub artifacts |
| `/hitl:dev-validate` | Check everything from the session — runs until all checks pass |
| `/hitl:ta-approve` | TA gate — advance a design phase from awaiting to approved |

### Architect

| Command | When to use |
|---|---|
| `/hitl:architect-design-system` | Design a new system from scratch (produces HLD, LLD, delivery plan) |
| `/hitl:architect-design-feature` | Design a feature — impact analysis, HLD, LLD, decision packet |
| `/hitl:architect-review-code` | Human architect code review (step 19a in the 31-step workflow) |

### QA

| Command | When to use |
|---|---|
| `/hitl:qa-plan-tests` | Design-time QA review of LLD — identify edge cases before TDD |
| `/hitl:qa-review-tests` | Formal review of test coverage after the TDD RED phase |
| `/hitl:qa-verify-quality` | Post-handoff independent verification against acceptance criteria |
| `/hitl:qa-report-defect` | File a structured defect report when verify-quality finds issues |

### PM

| Command | When to use |
|---|---|
| `/hitl:pm-design-feature` | Rough idea → structured requirement with user stories and ACs |
| `/hitl:pm-add-feature` | Add a new feature requirement to the PRD |
| `/hitl:pm-enhance-feature` | Understand an existing feature and produce an enhancement request |
| `/hitl:pm-update-requirement` | Update an existing PRD requirement (ACs, scope, priority) |
| `/hitl:pm-report-bug` | Document a bug as a structured GitHub issue |
| `/hitl:pm-review-progress` | Review sprint or milestone progress against PRD goals |
| `/hitl:pm-review-scope-change` | Analyze impact of a proposed scope change |
| `/hitl:pm-answer-questions` | Answer product questions using PRD, HLDs, and existing docs |
| `/hitl:pm-prioritize` | Prioritize features or backlog items by value, effort, and risk |
| `/hitl:pm-prep-demo` | Prepare a demo script or talking points for a feature |

### Ops

| Command | When to use |
|---|---|
| `/hitl:ops-build` | Validate and run the build pipeline |
| `/hitl:ops-deploy` | Structured deployment workflow |
| `/hitl:ops-plan-platform` | Platform readiness register + roadmap: onboarded → delivery-ready |
| `/hitl:ops-apply-iac` | Apply infrastructure-as-code changes |
| `/hitl:ops-migrate-database` | Run and verify a database migration |
| `/hitl:ops-backup-database` | Trigger and verify a database backup |
| `/hitl:ops-setup-observability` | Set up logging, metrics, and alerting |
| `/hitl:ops-verify-scripts` | Validate scripts and tooling before use |
| `/hitl:ops-post-deploy-monitor` | Monitor a deployment after it goes live |
| `/hitl:ops-detect-drift` | Detect configuration or infrastructure drift |
| `/hitl:ops-incident` | Incident response — structured P0 workflow |
| `/hitl:ops-rollback` | Roll back a deployment |
| `/hitl:ops-pentest` | Run a penetration test workflow |

### Migration

| Command | When to use |
|---|---|
| `/hitl:dev-review-external-docs` | Architect review of external migration documentation |

---

**Tip:** Run `/hitl:help <describe your situation>` to get a recommendation for what to use.

---

## If $ARGUMENTS is not empty — find the right command

Read `$ARGUMENTS` as a description of a situation, goal, or question. Match it against the skills above and recommend the best fit.

**Output format:**

---

**Recommended:** `/hitl:<command>`

[One sentence on why this is the right command for this situation]

**How to use it:**
```
/hitl:<command> <hint>
```

[1–2 sentences on what to pass as input and what it will do]

---

**Also consider:**
- `/hitl:<alternative>` — [one-line reason it might apply instead]

---

**Never say "I'm not sure" without giving a best guess.** If the situation is ambiguous between two commands, recommend both clearly and explain the distinction.

**Matching guidance — use this to pick the right command:**

| If they say... | Recommend |
|---|---|
| starting a new project | `dev-start-from-prd` |
| onboarding existing code | `dev-start-brownfield` |
| migrating a system | `dev-start-migration` |
| implementing a feature / starting a change | `dev-practices` or `dev-apply-change` |
| writing tests first / TDD | `dev-tdd` |
| checking code quality / lint | `dev-check-conventions` |
| code doesn't match the design doc | `dev-review-lld-adherence` |
| security review / threat model | `dev-review-security` |
| rollout plan / risk analysis | `dev-impact-brief` |
| generating design docs / HLD / LLD | `dev-generate-docs` |
| Slack design discussion → GitHub | `dev-conclude` |
| validate my work / check everything | `dev-validate` |
| approve a gate / TA sign-off | `ta-approve` |
| designing a new system architecture | `architect-design-system` |
| designing a feature (architect role) | `architect-design-feature` |
| architect reviewing code | `architect-review-code` |
| planning test cases / QA input to design | `qa-plan-tests` |
| reviewing test coverage | `qa-review-tests` |
| verifying a feature works / QA sign-off | `qa-verify-quality` |
| filing a defect / bug from QA | `qa-report-defect` |
| turning a rough idea into a requirement | `pm-design-feature` |
| adding a new feature to the PRD | `pm-add-feature` |
| enhancing something that already exists | `pm-enhance-feature` |
| changing an existing PRD requirement | `pm-update-requirement` |
| reporting a bug (PM) | `pm-report-bug` |
| checking sprint progress | `pm-review-progress` |
| scope change impact | `pm-review-scope-change` |
| answering product questions | `pm-answer-questions` |
| prioritizing features / backlog | `pm-prioritize` |
| preparing a demo | `pm-prep-demo` |
| deploying / deployment workflow | `ops-deploy` |
| database migration | `ops-migrate-database` |
| infrastructure / IaC | `ops-apply-iac` |
| incident / production issue | `ops-incident` |
| rollback | `ops-rollback` |
| drift detection | `ops-detect-drift` |
| observability / monitoring setup | `ops-setup-observability` |
| platform roadmap / delivery-ready / first pipeline or environment | `ops-plan-platform` |
| production deploy blocked by platform gate | `ops-plan-platform` (status + waivers) |
| penetration test | `ops-pentest` |
