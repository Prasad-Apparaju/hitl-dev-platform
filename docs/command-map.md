# HITL Command Map

All commands across every workflow, showing where each one appears in the delivery lifecycle.

---

## 1. Project Lifecycle — High Level

The three setup paths converge into a single repeating change loop.

```mermaid
graph LR
  prd["/hitl:dev-start-from-prd"]
  brown["/hitl:dev-start-brownfield"]
  mig["/hitl:dev-start-migration"]

  pm["PM phase"]
  arch["Architect phase"]
  dev["Dev phase — 31 steps"]
  qa["QA phase"]
  ops["Ops phase"]

  prd --> pm
  brown --> pm
  mig --> pm
  pm --> arch --> dev --> qa --> ops
  ops -->|"next change"| pm
```

---

## 2. Setup Flows

Each path produces a different starting artifact before the change loop begins.

```mermaid
graph TB
  subgraph PRD["Start from PRD"]
    s1["/hitl:dev-start-from-prd"]
    s2["/hitl:architect-design-system"]
    s3["Manifest + HLDs + LLDs + delivery plan"]
    s1 --> s2 --> s3
  end

  subgraph BROWN["Start brownfield"]
    b1["/hitl:dev-start-brownfield"]
    b2["/hitl:dev-generate-docs"]
    b3["/hitl:architect-review-existing"]
    b4["Manifest + baseline docs + ADRs"]
    b1 --> b3
    b1 --> b2
    b2 --> b4
    b3 --> b4
  end

  subgraph MIG["Start migration"]
    m1["/hitl:dev-start-migration"]
    m2["/hitl:dev-review-external-docs"]
    m3["/hitl:architect-design-system"]
    m4["Migration brief + target HLDs + LLDs"]
    m1 --> m2 --> m3 --> m4
  end
```

---

## 3. Per-Change Delivery Flow

The full command sequence for a Tier 2+ change, by role.

```mermaid
graph TB
  subgraph PM_PHASE["PM — Shape the change"]
    pm1["/hitl:pm-prioritize"]
    pm2["/hitl:pm-design-feature"]
    pm3["/hitl:pm-add-feature"]
    pm4["/hitl:pm-enhance-feature"]
    pm5["/hitl:pm-update-requirement"]
    issue["GitHub Issue"]
    pm1 --> pm2 --> issue
    pm3 --> issue
    pm4 --> issue
    pm5 --> issue
  end

  subgraph ARCH_PHASE["Architect — Design"]
    a1["/hitl:architect-design-feature"]
    a2["HLD + LLD approved"]
    ta1["/hitl:ta-approve — design gate"]
    a1 --> a2 --> ta1
  end

  subgraph QA_PLAN["QA — Plan tests (step 7)"]
    q1["/hitl:qa-plan-tests"]
  end

  subgraph DEV_PHASE["Developer — Build (steps 1-25)"]
    d1["/hitl:dev-apply-change"]
    d2["/hitl:dev-generate-docs"]
    d3["/hitl:dev-tdd"]
    d4["/hitl:dev-check-conventions"]
    d5["/hitl:dev-review-lld-adherence"]
    d6["/hitl:dev-review-security"]
    d7["/hitl:architect-review-code"]
    d8["/hitl:dev-impact-brief"]
    d9["/hitl:dev-validate"]
    d1 --> d2 --> d3 --> d4 --> d5 --> d6 --> d7 --> d8 --> d9
  end

  subgraph QA_REVIEW["QA — Review and verify"]
    q2["/hitl:qa-review-tests — step 11"]
    q3["/hitl:qa-verify-quality — step 22"]
    q4["/hitl:qa-report-defect"]
    q2 --> q3
    q3 -->|"fail"| q4
  end

  subgraph GATE["TA gate — code approval"]
    ta2["/hitl:ta-approve — code gate"]
  end

  subgraph OPS_PHASE["Ops — Ship"]
    o1["/hitl:ops-build"]
    o2["/hitl:ops-deploy"]
    o3["/hitl:ops-post-deploy-monitor"]
    o4["/hitl:ops-rollback"]
    o1 --> o2 --> o3
    o3 -->|"issue"| o4
  end

  PM_PHASE --> ARCH_PHASE
  ARCH_PHASE --> QA_PLAN
  QA_PLAN --> DEV_PHASE
  DEV_PHASE --> QA_REVIEW
  QA_REVIEW --> GATE
  GATE --> OPS_PHASE
```

---

## 4. Ops Command Landscape

```mermaid
graph TB
  deploy["/hitl:ops-deploy"]

  subgraph INFRA["Infrastructure"]
    iac["/hitl:ops-apply-iac"]
    obs["/hitl:ops-setup-observability"]
    drift["/hitl:ops-detect-drift"]
    vs["/hitl:ops-verify-scripts"]
    pt["/hitl:ops-pentest"]
  end

  subgraph DATA["Data"]
    mdb["/hitl:ops-migrate-database"]
    bdb["/hitl:ops-backup-database"]
  end

  subgraph INCIDENT["Incident response"]
    inc["/hitl:ops-incident"]
    roll["/hitl:ops-rollback"]
    inc --> roll
  end

  deploy --> iac
  deploy --> obs
  deploy --> mdb
  mdb --> bdb
```

---

## 5. Commands at a Glance

### Setup — run once

| Command | When |
|---|---|
| `/hitl:dev-start-from-prd` | New greenfield project |
| `/hitl:dev-start-brownfield` | Existing codebase |
| `/hitl:dev-start-migration` | System-to-system migration |
| `/hitl:architect-design-system` | After PRD or migration setup |
| `/hitl:architect-review-existing` | After brownfield manifest generation |
| `/hitl:dev-review-external-docs` | After migration setup, before design |

### PM — any time before a change starts

| Command | When |
|---|---|
| `/hitl:pm-design-feature` | Rough idea → structured requirement |
| `/hitl:pm-add-feature` | Add new requirement to PRD |
| `/hitl:pm-enhance-feature` | Enhance existing feature |
| `/hitl:pm-update-requirement` | Change AC, scope, or priority on existing requirement |
| `/hitl:pm-report-bug` | File a structured defect |
| `/hitl:pm-prioritize` | Backlog prioritization |
| `/hitl:pm-review-scope-change` | Impact of a proposed scope change |
| `/hitl:pm-review-progress` | Sprint or milestone progress check |
| `/hitl:pm-answer-questions` | Product questions from PRD and docs |
| `/hitl:pm-prep-demo` | Demo script and talking points |

### Architect — design phase (steps 3–9)

| Command | When |
|---|---|
| `/hitl:architect-design-feature` | Feature-level HLD + LLD with approval gates |
| `/hitl:architect-review-code` | Human code review at step 19a |

### QA — across design and implementation

| Command | Step | When |
|---|---|---|
| `/hitl:qa-plan-tests` | 7 | After LLD approval, before TDD |
| `/hitl:qa-review-tests` | 11 | After RED phase; gates implementation start |
| `/hitl:qa-verify-quality` | 22 | Post-handoff independent verification |
| `/hitl:qa-report-defect` | 22+ | When verify-quality fails |

### Developer — implementation (steps 1–25)

| Command | Step(s) | When |
|---|---|---|
| `/hitl:dev-practices` | 1 | Entry point for the 31-step workflow |
| `/hitl:dev-apply-change` | 3 | Change planning and impact analysis |
| `/hitl:dev-generate-docs` | 5–6 | HLD/LLD for a component |
| `/hitl:dev-tdd` | 10–16 | Red→Green→Refactor cycle |
| `/hitl:dev-check-conventions` | 17 | Semgrep, secrets, manifest drift, Mermaid lint |
| `/hitl:dev-review-lld-adherence` | 18 | Code vs LLD conformance check |
| `/hitl:dev-review-security` | 19 | Threat model, SAST, or security baseline |
| `/hitl:dev-impact-brief` | 23 | Downstream impact and rollout plan |
| `/hitl:dev-validate` | Any | Iterative check→fix→re-check before done |
| `/hitl:dev-conclude` | Any | Slack design thread → GitHub ADR + issue |

### Gates

| Command | When |
|---|---|
| `/hitl:ta-approve` | Advance design gate (after LLD approval) or code gate (before Ops) |

### Ops — after code gate

| Command | When |
|---|---|
| `/hitl:ops-build` | Validate and run build pipeline |
| `/hitl:ops-deploy` | Full deployment workflow |
| `/hitl:ops-plan-platform` | Platform readiness register + roadmap (onboarded → delivery-ready) |
| `/hitl:ops-apply-iac` | Infrastructure-as-code changes |
| `/hitl:ops-migrate-database` | Database migration before deploy |
| `/hitl:ops-backup-database` | Pre-deploy or scheduled backup |
| `/hitl:ops-setup-observability` | Logging, metrics, alerting |
| `/hitl:ops-verify-scripts` | Script/tooling validation |
| `/hitl:ops-post-deploy-monitor` | Post-deploy monitoring |
| `/hitl:ops-detect-drift` | Config or infrastructure drift |
| `/hitl:ops-pentest` | Penetration test workflow |
| `/hitl:ops-rollback` | Roll back a deployment |
| `/hitl:ops-incident` | P0 incident response |

### Utility — available at any time

| Command | Purpose |
|---|---|
| `/hitl:help` | Find the right command for any situation |
| `/hitl:dev-update` | Update the plugin to the latest version |
