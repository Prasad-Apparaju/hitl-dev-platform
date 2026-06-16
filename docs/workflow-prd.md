# PRD Workflow — End to End

All steps from project creation to production, following the `/hitl:dev-start-from-prd` path. Each node shows the HITL command that executes that step. Steps marked `(cond)` are conditional based on change tier or project configuration.

---

## 1. Project Setup — `/hitl:dev-start-from-prd`

```mermaid
graph TB
  entry["/hitl:dev-start-from-prd"]
  s0["Step 0 - Wire 7 hooks + settings.json + ADR stubs"]
  s1["Step 1 - Customize CLAUDE.md"]
  s2["Step 2 - Initialize system manifest"]
  s3["Step 3 - Create first GitHub issue"]
  s4["Step 4 - Confirm ready"]
  design["/hitl:architect-design-system"]
  graph_build["graphify . + graphify hook install (if Graphify is installed)"]
  loop["Per-change delivery loop - see Section 2 and 3"]

  entry --> s0 --> s1 --> s2 --> s3 --> s4 --> design --> graph_build --> loop
```

### What each setup step does

| Step | What happens | Output |
|---|---|---|
| 0 | Creates `.hitl/hooks/` with 7 wrappers, `.claude/settings.json` with hooks + statusLine, seeds 4 default ADR stubs | `.hitl/hooks/`, `.claude/settings.json`, `docs/02-design/technical/adrs/adr-000{1-4}.md` |
| 1 | Fills in coding conventions, test framework, naming rules in CLAUDE.md | `CLAUDE.md` customized |
| 2 | Drafts initial domain list from PRD → `docs/system-manifest.yaml` | `docs/system-manifest.yaml` (provisional) |
| 3 | Creates the first tracked work item on GitHub | GitHub issue URL |
| 4 | Confirms setup complete; hands off to architect | — |
| Design | Full system design from PRD — domains, HLDs, LLDs, delivery plan | `docs/01-product/`, `docs/02-design/hld/`, `docs/02-design/lld/`, `docs/decisions/` |
| Graphify | Builds knowledge graph from generated docs (optional — if Graphify is installed) | `graphify-out/graph.json` |

---

## 2. Per-Change Loop — Requirements and Design (Steps 1–9)

One GitHub issue = one delivery slice. These steps run before any code is written.

```mermaid
graph TB
  subgraph REQ["Requirements (Steps 1-2)"]
    r1["1 - GitHub issue - /hitl:pm-add-feature or /hitl:pm-design-feature"]
    r2["2 - Figma review - manual (cond)"]
    r1 --> r2
  end

  subgraph DESIGN["Design (Steps 3-9)"]
    d3["3 - Impact analysis - /hitl:dev-apply-change"]
    d4["4 - ROI estimate (cond)"]
    d5["5 - HLD + LLD - /hitl:dev-generate-docs"]
    d5a["5a - Security review design - /hitl:dev-review-security --phase design (cond)"]
    d6["6 - IaC + migration scripts - /hitl:ops-verify-scripts (cond)"]
    d7["7 - Test case planning - /hitl:qa-plan-tests"]
    d8["8 - Training plan stub (cond)"]
    d9["9 - Decision packet - architect assembles docs/decisions/issue-N.yaml"]
    d3 --> d4 --> d5 --> d5a --> d6 --> d7 --> d8 --> d9
  end

  gate1["TA gate - /hitl:ta-approve - design"]

  REQ --> DESIGN
  DESIGN --> gate1
```

---

## 3. Per-Change Loop — Build, Verify, and Ship (Steps 10–32)

```mermaid
graph TB
  subgraph TDD["Build TDD (Steps 10-17)"]
    t10["10 - Write tests RED - /hitl:dev-tdd"]
    t11["11 - QA reviews tests - /hitl:qa-review-tests"]
    t12["12 - Tests improve design - /hitl:dev-tdd updates LLD"]
    t13["13 - Verify RED - run tests, all must fail"]
    t14["14 - Write code GREEN - /hitl:dev-tdd"]
    t15["15 - Verify GREEN - run tests, coverage 90pct"]
    t16["16 - Refactor"]
    t16a["16a - Security review code - /hitl:dev-review-security --phase code (cond)"]
    t17["17 - Convention checks - /hitl:dev-check-conventions"]
    t10 --> t11 --> t12 --> t13 --> t14 --> t15 --> t16 --> t16a --> t17
  end

  subgraph VERIFY["Verify (Steps 18-22)"]
    v18["18 - Code review round 1 - /hitl:dev-review-lld-adherence"]
    v19["19 - Code review round 2 - /hitl:dev-review-lld-adherence"]
    v19a["19a - Architect code review - /hitl:architect-review-code"]
    v20["20 - Rerun tests"]
    v21["21 - Reconcile docs - /hitl:dev-generate-docs if changed"]
    v22["22 - QA post-handoff verify - /hitl:qa-verify-quality"]
    v18 --> v19 --> v19a --> v20 --> v21 --> v22
  end

  subgraph ASSESS["Assess (Steps 23-24)"]
    a23["23 - Downstream impact brief - /hitl:dev-impact-brief"]
    a24["24 - Rollout plan"]
    a23 --> a24
  end

  gate2["TA gate - /hitl:ta-approve - code"]

  subgraph SHIP["Ship (Steps 25-29)"]
    s25["25 - Verify PR completeness"]
    s26["26 - Integration verify"]
    s27["27 - Figma comparison - manual (cond)"]
    s28a["28a - /hitl:ops-backup-database (cond)"]
    s28b["28b - /hitl:ops-migrate-database (cond)"]
    s28c["28c - /hitl:ops-apply-iac (cond)"]
    s28d["28d - /hitl:ops-setup-observability"]
    s28e["28e - /hitl:ops-build"]
    s28f["28f - /hitl:ops-detect-drift"]
    s28g["28g - /hitl:ops-deploy"]
    s29["29 - /hitl:ops-post-deploy-monitor or /hitl:ops-rollback"]
    s25 --> s26 --> s27 --> s28a --> s28b --> s28c --> s28d --> s28e --> s28f --> s28g --> s29
  end

  subgraph POSTSHIP["Post-ship (Steps 30-32)"]
    p30["30 - /hitl:ops-pentest (cond)"]
    p31["31 - 30-day ROI check (cond)"]
    p32["32 - 90-day ROI check + ADR update (cond)"]
    p30 --> p31 --> p32
  end

  TDD --> VERIFY --> ASSESS --> gate2 --> SHIP --> POSTSHIP
```

---

## 4. Human Approval Gates

These are points where work stops until a human explicitly approves before proceeding.

| Gate | Position | Command | Who approves |
|---|---|---|---|
| Design gate | After Step 9 (decision packet) | `/hitl:ta-approve` | Tech Architect |
| QA test review | Step 11 | `/hitl:qa-review-tests` | QA |
| Architect code review | Step 19a | `/hitl:architect-review-code` | Architect reviews PR on GitHub |
| QA verify | Step 22 | `/hitl:qa-verify-quality` | QA |
| Code gate | After Step 24 (rollout plan) | `/hitl:ta-approve` | Tech Architect |

---

## 5. Full Command Reference

| Step | Command | Phase |
|---|---|---|
| 1 | `/hitl:pm-add-feature` or `/hitl:pm-design-feature` or `/hitl:pm-report-bug` | Requirements |
| 3 | `/hitl:dev-apply-change` | Design |
| 5 | `/hitl:dev-generate-docs` | Design |
| 5a | `/hitl:dev-review-security --phase design` (cond) | Design |
| 6 | `/hitl:ops-verify-scripts` (cond) | Design |
| 7 | `/hitl:qa-plan-tests` | Design |
| — | `/hitl:ta-approve` — design gate | Gate |
| 10 | `/hitl:dev-tdd` — write RED tests | Build |
| 11 | `/hitl:qa-review-tests` | Build |
| 12 | `/hitl:dev-tdd` — update LLD | Build |
| 14 | `/hitl:dev-tdd` — write GREEN code | Build |
| 16 | `/hitl:dev-tdd` — refactor | Build |
| 16a | `/hitl:dev-review-security --phase code` (cond) | Build |
| 17 | `/hitl:dev-check-conventions` | Build |
| 18 | `/hitl:dev-review-lld-adherence` — impl vs LLD | Verify |
| 19 | `/hitl:dev-review-lld-adherence` — impl vs tests | Verify |
| 19a | `/hitl:architect-review-code` | Verify |
| 21 | `/hitl:dev-generate-docs` (if design changed) | Verify |
| 22 | `/hitl:qa-verify-quality` | Verify |
| 23 | `/hitl:dev-impact-brief` | Assess |
| — | `/hitl:ta-approve` — code gate | Gate |
| 28a | `/hitl:ops-backup-database` (cond) | Ship |
| 28b | `/hitl:ops-migrate-database` (cond) | Ship |
| 28c | `/hitl:ops-apply-iac` (cond) | Ship |
| 28d | `/hitl:ops-setup-observability` | Ship |
| 28e | `/hitl:ops-build` | Ship |
| 28f | `/hitl:ops-detect-drift` | Ship |
| 28g | `/hitl:ops-deploy` | Ship |
| 29 | `/hitl:ops-post-deploy-monitor` or `/hitl:ops-rollback` | Ship |
| 30 | `/hitl:ops-pentest` (cond) | Post-ship |
