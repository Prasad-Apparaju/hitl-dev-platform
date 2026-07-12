# Brownfield Workflow — End to End

All steps from onboarding an existing codebase through production delivery, following the `/hitl:dev-start-brownfield` path.

**Key difference from the PRD path:** you have existing code, so the setup phase reconstructs what is already there rather than designing from scratch. Documentation is built incrementally — only priority components get docs during setup; every other component gets its LLD the first time it is changed.

---

## 1. Project Setup

Setup ends when the system manifest, architecture ADRs, priority component LLDs, registries, and the platform readiness register all exist. No per-change work begins before that point.

```mermaid
graph TB
  subgraph SETUP["Project Setup — run once per project"]
    entry["/hitl:dev-start-brownfield"]
    s0["Step 0 - Wire 7 hooks + settings.json + 4 ADR stubs"]
    s1["Step 1 - Map the codebase"]
    s2["Step 2 - Customize CLAUDE.md"]
    s3["Step 3 - Generate system manifest from existing code"]
    s4["Step 4 - /hitl:architect-review-existing - reconstruct decisions as ADRs"]
    s5["Step 5 - Verify pipeline - verdicts persisted to readiness register"]
    s6["Step 6 - Observability survey - verdicts persisted to readiness register"]
    s7["Step 7 - Priority components - /hitl:dev-generate-docs for each"]
    s8["Step 8 - Seed registries from existing tests and incidents"]
    s9["Step 9 - Graphify (if installed)"]
    s10["Step 10 - Create first change issue"]
    s11["Step 11 - Confirm ready + offer /hitl:ops-plan-platform roadmap"]
    entry --> s0 --> s1 --> s2 --> s3 --> s4 --> s5 --> s6 --> s7 --> s8 --> s9 --> s10 --> s11
  end

  loop["Per-change delivery loop - GitHub issue + /hitl:dev-practices"]
  roadmap["Platform roadmap - gaps become ordinary HITL changes"]

  s11 --> loop
  s11 --> roadmap
```

### What each step produces

| Step | Command | Output | Required before |
|---|---|---|---|
| 0 | _(wires hooks automatically)_ | `.hitl/hooks/`, `.claude/settings.json`, 4 ADR stubs | Everything else |
| 1 | _(reads directory tree)_ | Confirmed source roots and tech stack | Manifest generation |
| 2 | _(fills CLAUDE.md from observed code patterns)_ | Conventions and test framework locked in | Code generation |
| 3 | `python tools/generate-manifest/generator.py` | `docs/system-manifest.yaml` (from real code) | Architecture review |
| 4 | `/hitl:architect-review-existing` | Tech stack summary, ADR-0005+ for existing decisions, concern list | Per-change work |
| 5 | _(verifies CI/CD, offers scaffold)_ | Pipeline verdicts (D1/E1/E3) in `docs/04-operations/platform-readiness.yaml` | Build/deploy steps of the 31-step workflow |
| 6 | _(surveys observability)_ | Observability verdict (F1) in the readiness register; token cost registry | First Tier 2 deploy |
| 7 | `/hitl:dev-generate-docs` (per component) | HLD + LLD for each priority component | First change to those components |
| 8 | _(scans test files + interviews team)_ | `test-registry.yaml`, `incident-registry.yaml` | `/hitl:dev-practices` Test Case Planning |
| 9 | `graphify . && graphify hook install` | `graphify-out/graph.json` (optional) | First `/hitl:dev-practices` run |
| 10 | `gh issue create` | First tracked change issue | Per-change loop |
| 11 | _(confirms baseline)_ | Handoff to `/hitl:ops-plan-platform roadmap` — recorded gaps become phased roadmap issues; Tier 2+ **production** deploys stay blocked until the register says `delivery_ready: true` | — |

### What `/hitl:architect-review-existing` produces (Step 4)

This is the brownfield-specific step that has no equivalent in the PRD path. It reads the existing codebase and interviews the architect before any incremental work begins.

| Phase | What happens |
|---|---|
| 1 — Landscape | Reads manifest + technology indicator files; outputs Tech Stack Summary |
| 2 — Extract decisions | Identifies concrete decisions across 8 categories: service architecture, data, auth, API style, cross-domain communication, deployment, test strategy as-built, non-obvious patterns |
| 3 — Interview | Asks architect: deliberate vs inherited, rationale, constraints and regrets, unknown decisions |
| 4 — Document ADRs | Creates ADR-0005+ for significant decisions — status Accepted or Under review; never fabricates rationale |
| 5 — Surface concerns | Categorises concerns: blocks HITL compliance (🔴), address in first changes (🟡), worth noting (🟢) |
| 6 — Handoff | Lists ADRs created, key constraints, and pre-conditions for first Tier 2 change |

Architect must confirm ADRs are accurate before Step 5 begins.

---

## 2. First-Change Consideration — Docs on First Touch

This is the brownfield-specific friction that does not exist in the PRD path. Not every component has an LLD after setup — only the priority components from Step 5 do. The first time any other component is changed, its LLD must be created before the 31-step loop can proceed.

```mermaid
graph TB
  issue["GitHub issue created"]
  check{"Does component\nhave an LLD?"}
  gendocs["/hitl:dev-generate-docs for this component"]
  practices["/hitl:dev-practices - 31-step workflow"]

  issue --> check
  check -->|"yes"| practices
  check -->|"no - first touch"| gendocs
  gendocs --> practices
```

This friction decreases naturally over time as each component gets its first doc pass through real use. Once all actively-changed components have LLDs, the brownfield path behaves identically to the PRD path.

---

## 3. Per-Change Loop — Requirements and Design (Steps 1–9)

Identical to the PRD path. One GitHub issue = one delivery slice.

```mermaid
graph TB
  subgraph REQ["Requirements (Steps 1-2)"]
    r1["1 - GitHub issue - /hitl:pm-add-feature or /hitl:pm-design-feature"]
    r2["2 - Figma review - manual (cond)"]
    r1 --> r2
  end

  subgraph DESIGN["Design (Steps 3-9)"]
    d3a["3 - Create feature branch issue/N-slug + commit initial current-change.yaml"]
    d3["3 - Impact analysis - /hitl:dev-apply-change"]
    d3a --> d3
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

## 4. Per-Change Loop — Build, Verify, and Ship (Steps 10–32)

Identical to the PRD path.

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

## 5. Human Approval Gates

| Gate | Position | Command | Who approves |
|---|---|---|---|
| Architecture review | Step 4 of setup | _(architect reviews ADR drafts in session)_ | Architect |
| Design gate | After Package Decision Packet | `/hitl:ta-approve` | Tech Architect |
| QA test review | Human Reviews Tests | `/hitl:qa-review-tests` | QA |
| Architect code review | Architect Code Review | `/hitl:architect-review-code` | Architect reviews PR on GitHub |
| QA verify | QA Post-Handoff Verification | `/hitl:qa-verify-quality` | QA |
| Code gate | After Risk-Rated Rollout Plan | `/hitl:ta-approve` | Tech Architect |

---

## 6. PRD vs Brownfield — Key Differences

| Aspect | PRD path | Brownfield path |
|---|---|---|
| Manifest origin | Designed from PRD (provisional) | Generated from existing code |
| Architecture decisions | New — architect designs them | Existing — architect reconstructs and documents them |
| LLDs at setup end | All components designed upfront | Only priority components; others generated on first touch |
| First-change friction | None — LLDs exist | May need `dev-generate-docs` before `dev-practices` |
| Registries at setup end | Empty stubs | Seeded from real test files and past incidents |
| ADRs at setup end | 4 default stubs (ADR-0001 to 0004) | 4 default stubs + ADR-0005+ for real existing decisions |
| Per-change loop | Identical | Identical (once LLD exists) |
