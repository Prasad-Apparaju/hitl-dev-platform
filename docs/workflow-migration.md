# Migration Workflow — End to End

All steps from initialising a migration project through production delivery, following the `/hitl:dev-start-migration` path.

**Key difference from PRD and brownfield paths:** migration is not brownfield. In brownfield you work *inside* the existing codebase — it is the live product. In migration the source codebase is being *replaced*: it is read-only reference. Only behaviors transfer to the target, never code. The behavioral inventory (`docs/00-migration/source-behavioral-inventory.md`) is the only bridge: each BI-NNN entry describes what the target must do; how it does it is a fresh design decision. Migration is complete when every BI entry is marked `Complete` or `Descoped` in the coverage matrix.

---

## 1. Project Setup

Setup ends when the migration brief is approved and architect design begins. No per-slice development starts before that point.

```mermaid
graph TB
  subgraph SETUP["Project Setup — run once per migration project"]
    entry["/hitl:dev-start-migration"]
    s0["Step 0 - Wire 7 hooks + settings.json + 4 ADR stubs"]
    s1["Step 1 - Collect migration context - source, target, trigger, external docs"]
    s2["Step 2 - Customize CLAUDE.md for TARGET system conventions"]
    s3["Step 3 - Initialize TARGET system manifest (provisional)"]
    s4["Step 4 - Create docs/00-migration/ directory structure"]
    s5["Step 5 - Analyze source codebase - source-behavioral-inventory.md"]
    s6["Step 6 - Ingest external docs into docs/00-migration/external-reference/ (optional)"]
    s7["Step 7 - Seed registries from source tests and incidents"]
    s8["Step 8 - Create migration tracking issue"]
    s9["Step 9 - Confirm ready"]
    review["/hitl:dev-review-external-docs - review + migration brief"]
    design_choice{"Full-system or\nslice-by-slice?"}
    design_full["/hitl:architect-design-system migration-brief.md"]
    design_slice["/hitl:architect-design-feature (per slice)"]
    graphify["graphify . + graphify hook install (if installed)"]
    entry --> s0 --> s1 --> s2 --> s3 --> s4 --> s5 --> s6 --> s7 --> s8 --> s9
    s9 --> review --> design_choice
    design_choice --> design_full --> graphify
    design_choice --> design_slice --> graphify
  end

  loop["Per-slice delivery loop - GitHub issue + /hitl:dev-practices + update coverage matrix"]

  graphify --> loop
```

### What each setup step produces

| Step | Command | Output | Required before |
|---|---|---|---|
| 0 | _(wires hooks automatically)_ | `.hitl/hooks/`, `.claude/settings.json`, 4 ADR stubs | Everything else |
| 1 | _(collects context)_ | `docs/00-migration/migration-context.yaml` | All subsequent steps |
| 2 | _(fills CLAUDE.md for target)_ | Target-system conventions locked in | Code generation |
| 3 | _(drafts target manifest)_ | `docs/system-manifest.yaml` (provisional, for target) | Architect design |
| 4 | _(creates directory structure)_ | `docs/00-migration/` with stubs for all migration docs | Steps 5–6 |
| 5 | _(reads source code)_ | `docs/00-migration/source-behavioral-inventory.md` (BI-NNN entries) | Migration brief |
| 6 | _(copies or links external docs)_ | `docs/00-migration/external-reference/` | Review phase |
| 7 | _(scans source tests + interviews team)_ | `test-registry.yaml`, `incident-registry.yaml` (incidents flagged `migration_regression: true`) | `/hitl:dev-practices` step 7 |
| 8 | `gh issue create` | Migration tracking issue | Per-slice loop |
| 9 | _(confirms ready)_ | — | — |
| Review | `/hitl:dev-review-external-docs` | `migration-review.md` + `migration-brief.md` with coverage matrix | Architect design |
| Design | `/hitl:architect-design-system` or `/hitl:architect-design-feature` | HLDs, LLDs, `docs/decisions/` per slice | Per-slice loop |
| Graphify | `graphify . && graphify hook install` | `graphify-out/graph.json` (optional) | First `/hitl:dev-practices` run |

---

## 2. External Docs Review Phase — `/hitl:dev-review-external-docs`

This phase has no equivalent in the PRD or brownfield paths. It produces two documents that gate all design work.

```mermaid
graph TB
  subgraph REVIEW["External Docs Review"]
    p1a["1a - Read migration-context.yaml"]
    p1b["1b - Read source-behavioral-inventory.md"]
    p1c["1c - Inventory external reference docs"]
    p1d["1d - Read all external docs in full"]
    p2["2 - Critical evaluation - reliability, gaps, divergence, risks"]
    p3["3 - Write migration-review.md - critique of external docs"]
    p4["4 - Write migration-brief.md - PRD-equivalent + coverage matrix"]
    p5["5 - Hand off to architect design"]
    p1a --> p1b --> p1c --> p1d --> p2 --> p3 --> p4 --> p5
  end
```

| Output | Purpose | Approval required |
|---|---|---|
| `docs/00-migration/migration-review.md` | Critiques external docs: reliable inputs, gaps, divergences, risk flags | Architect must approve before brief is written |
| `docs/00-migration/migration-brief.md` | PRD-equivalent requirements for target, including behavior coverage matrix keyed to BI IDs | Architect must approve before design begins |

The **behavior coverage matrix** in the migration brief is the live definition of migration progress:

| BI ID | Behavior | Domain | Target slice | Status |
|---|---|---|---|---|
| BI-001 | _(from inventory)_ | _(domain)_ | TBD | Not started |

Status values: `Not started` / `In progress` / `Complete` / `Descoped`

`Descoped` requires an explicit architect decision. No BI entry may be silently dropped.

---

## 3. Slice Design Paths

After the migration brief is approved, the architect chooses one of two design paths. Both produce the same inputs for the per-slice delivery loop.

| Path | Command | When to use |
|---|---|---|
| Full-system | `/hitl:architect-design-system docs/00-migration/migration-brief.md` | Migrating the entire target system before any slice ships; all HLDs and LLDs designed upfront |
| Slice-by-slice | `/hitl:architect-design-feature` (per slice) | Migrating one domain at a time into an existing or partially-built target; each slice is designed just before its development begins |

**Slice criterion for both paths:** every slice must be **observable** — either user-visible (PM can demo it) or verifiable by ops/QA (record counts, data consistency checks, performance comparison). "Data migrated but not yet accessible" does not pass.

---

## 4. Per-Slice Delivery Loop — Requirements and Design (Steps 1–9)

Each slice is one GitHub issue. The migration brief replaces the PRD — reference it as `docs/00-migration/migration-brief.md` wherever a skill asks for the PRD path.

```mermaid
graph TB
  subgraph REQ["Requirements (Steps 1-2)"]
    r1["1 - GitHub issue - declare which BI IDs this slice covers"]
    r2["2 - Figma review - manual (cond)"]
    r1 --> r2
  end

  subgraph DESIGN["Design (Steps 3-9)"]
    d3a["3 - Create feature branch issue/N-slug + commit initial current-change.yaml"]
    d3["3 - Impact analysis - /hitl:dev-apply-change"]
    d3a --> d3
    d4["4 - ROI estimate (cond)"]
    d5["5 - HLD + LLD - /hitl:dev-generate-docs or /hitl:architect-design-feature"]
    d5a["5a - Security review design - /hitl:dev-review-security --phase design (cond)"]
    d6["6 - IaC + migration scripts - /hitl:ops-verify-scripts (cond)"]
    d7["7 - Test case planning - /hitl:qa-plan-tests"]
    d8["8 - Training plan stub (cond)"]
    d9["9 - Decision packet - architect assembles docs/decisions/issue-N.yaml"]
    d3 --> d4 --> d5 --> d5a --> d6 --> d7 --> d8 --> d9
  end

  gate1["TA gate - /hitl:ta-approve - design"]
  coverage["Update coverage matrix - mark BI IDs as In progress"]

  REQ --> DESIGN
  DESIGN --> gate1
  gate1 --> coverage
```

**Migration-specific rule for Step 1:** the GitHub issue body must list which BI IDs from the behavioral inventory this slice covers. This is how the coverage matrix is kept up to date.

---

## 5. Per-Slice Delivery Loop — Build, Verify, and Ship (Steps 10–32)

Identical to the PRD and brownfield paths. After the slice ships, update the coverage matrix.

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

  coverage_update["Update coverage matrix in migration-brief.md - mark BI IDs Complete"]
  done_check{"All BI entries\nComplete or Descoped?"}
  next_slice["Design and deliver next slice"]
  migration_done["Migration complete"]

  TDD --> VERIFY --> ASSESS --> gate2 --> SHIP --> POSTSHIP --> coverage_update
  coverage_update --> done_check
  done_check -->|"no"| next_slice
  done_check -->|"yes"| migration_done
```

---

## 6. Human Approval Gates

| Gate | Position | Command | Who approves |
|---|---|---|---|
| Migration review | After Phase 3 of `dev-review-external-docs` | _(architect reviews draft in session)_ | Architect |
| Migration brief | After Phase 4 of `dev-review-external-docs` | _(architect approves in session)_ | Architect |
| Design gate | After Step 9 of each slice | `/hitl:ta-approve` | Tech Architect |
| QA test review | Step 11 | `/hitl:qa-review-tests` | QA |
| Architect code review | Step 19a | `/hitl:architect-review-code` | Architect reviews PR on GitHub |
| QA verify | Step 22 | `/hitl:qa-verify-quality` | QA |
| Code gate | After Step 24 | `/hitl:ta-approve` | Tech Architect |

---

## 7. All Three Paths — Comparison

| Aspect | PRD | Brownfield | Migration |
|---|---|---|---|
| What exists at start | Nothing | Working source code | Working source code + target to build |
| Manifest represents | Target system (designed from PRD) | Existing system (generated from code) | Target system (designed from brief) |
| Source of requirements | `docs/01-product/prd.md` | Existing code + team knowledge | `docs/00-migration/migration-brief.md` |
| Architecture decisions | New — architect designs them | Existing — architect reconstructs as ADRs | New (target) + existing (source) reconstructed in behavioral inventory |
| LLDs at setup end | All components designed upfront | Only priority components | All (full-system) or per-slice (slice-by-slice) |
| Definition of done | Product backlog cleared | Backlog cleared | All BI entries in coverage matrix are Complete or Descoped |
| Source incidents in registry | N/A | Past production incidents | Source incidents flagged `migration_regression: true` |
| Per-change unit | Feature or bug fix | Feature or bug fix | Observable migration slice |
| Slice must be | — | — | User-visible or verifiable by ops/QA |
| Coverage tracking | None | None | BI coverage matrix in migration-brief.md, updated per slice |
