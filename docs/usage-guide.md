# HITL Plugin — Usage Guide

How to use the HITL Claude Code plugin across every common team scenario: new projects, existing codebases, migrations, enhancements, bug fixes, and incidents.

---

## Installation — once per developer machine

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code. The plugin is now available in every project. Run `/hitl:help` at any time to get a command recommendation for your current situation.

To update later:
```bash
/hitl:dev-update
```

---

## Which path is right for you?

| Situation | Path |
|---|---|
| No code yet — you have a PRD or product spec | [New project from a PRD](#1-new-project-from-a-prd) |
| Code already exists — onboarding it into the process | [Existing codebase (brownfield)](#2-existing-codebase-brownfield) |
| Replacing one system with another | [Migration](#3-migration) |
| Adding a feature or enhancement to an onboarded project | [Enhancement](#4-enhancement) |
| Fixing a bug in an onboarded project | [Bug fix](#5-bug-fix) |
| Active production incident | [Incident response](#6-incident-response) |

**Project setup (scenarios 1–3) runs once per project.** After setup, all ongoing work follows scenario 4, 5, or 6.

---

## 1. New Project from a PRD

**When:** You are starting from scratch. A PRD (or equivalent product spec) exists, but no production code has been written yet.

**Start:**
```
/hitl:dev-start-from-prd
```

**What happens — setup (run once):**

| Step | Who | What |
|---|---|---|
| 0 | Claude | Wires 7 hooks and creates `.claude/settings.json` |
| 1 | Claude + PM | Reads `docs/01-product/prd.md`; customizes `CLAUDE.md` with project conventions |
| 2 | Claude + Architect | Generates `docs/system-manifest.yaml` with domains and facade APIs |
| 3 | Claude | Creates GitHub issue to track project setup |
| 4 | Human ✅ | Confirm ready; optionally run `graphify .` if Graphify is installed |

**What happens — architect design (run once before first feature):**
```
/hitl:architect-design-system docs/01-product/prd.md
```

The architect runs this to decompose the PRD into HLDs, LLDs, ADRs, and a delivery plan. No code is written until this is approved.

**After setup, every feature follows:** [Enhancement](#4-enhancement)

**What you get:**
- `CLAUDE.md` — project conventions, enforced on every session
- `docs/system-manifest.yaml` — domain boundaries
- `docs/02-design/` — HLDs, LLDs, ADRs from architect design
- `.hitl/hooks/` — 7 enforcement hooks wired to every Claude Code session
- Statusline breadcrumbs on every prompt

---

## 2. Existing Codebase (Brownfield)

**When:** You have a working codebase you want to bring into the HITL process. The code is the product — you are not replacing it.

**Start:**
```
/hitl:dev-start-brownfield
```

**What happens — setup (run once):**

| Step | Who | What |
|---|---|---|
| 0 | Claude | Wires 7 hooks, creates `.claude/settings.json`, copies 4 default ADR stubs |
| 1 | Claude | Maps top-level directory structure; confirms source dirs and framework with you |
| 2 | Claude + you | Fills in `CLAUDE.md` from observed code patterns + your conventions input |
| 3 | Claude | Generates `docs/system-manifest.yaml` from the existing codebase |
| 4 | Claude + Architect ✅ | Runs `/hitl:architect-review-existing` — interviews architect to document decisions already in the code as real ADRs (not inferred guesses) |
| 5 | Claude + Architect | Identifies 1–3 priority components; generates HLD + LLD for each via `/hitl:dev-generate-docs` |
| 6 | Claude + you | Seeds `test-registry.yaml` from existing tests; seeds `incident-registry.yaml` from recent production incidents |
| 7 | Claude | Optionally runs `graphify .` if installed |
| 8 | Claude | Creates first GitHub issue for the first change |
| 9 | Human ✅ | Confirm ready |

**What you get:**
- Same artifacts as PRD path, plus real ADRs reconstructed from the existing codebase
- HLD + LLD for priority components; other components get their LLD generated when first touched (`/hitl:dev-generate-docs` on demand)
- Statusline breadcrumbs on every prompt

**Note on undocumented components:** If `/hitl:dev-practices` stops with "no LLD found" on a component not covered in setup, run:
```
/hitl:dev-generate-docs
```
Then resume. Friction decreases naturally as each component gets its first doc pass through real use.

**After setup, every change follows:** [Enhancement](#4-enhancement) or [Bug fix](#5-bug-fix)

---

## 3. Migration

**When:** You are replacing one system (source) with another (target). The source codebase is being retired — it is reference only, not extended.

**Start:**
```
/hitl:dev-start-migration
```

**What happens — setup (run once):**

| Step | Who | What |
|---|---|---|
| 0 | Claude | Wires hooks, creates `.claude/settings.json`, copies 4 default ADR stubs |
| 1 | Claude + you | Collects migration context: source system, target system, trigger, external docs |
| 2 | Claude + Architect | Customizes `CLAUDE.md` for **target** system conventions; appends read-only rule for source code |
| 3 | Claude + Architect | Initialises `docs/system-manifest.yaml` for the **target** architecture |
| 4 | Claude | Creates `docs/00-migration/` directory structure |
| 5 | Claude | Reads source codebase; produces `docs/00-migration/source-behavioral-inventory.md` with every API, behavior, data contract, and integration the target must reproduce (BI-NNN entries) |
| 6 | Claude | Optionally ingests external migration docs into `docs/00-migration/external-reference/` |
| 7 | Claude | Seeds registries from source tests and incidents (incidents flagged `migration_regression: true`) |
| 8 | Claude | Creates migration tracking GitHub issue |
| 9 | Human ✅ | Confirm ready |

**Then — architect deep review (mandatory before any design):**
```
/hitl:dev-review-external-docs
```

Produces two documents requiring architect approval:
- `docs/00-migration/migration-review.md` — critique of external docs: gaps, divergences, risks
- `docs/00-migration/migration-brief.md` — PRD-equivalent requirements for the target, including a **behavior coverage matrix** keyed to BI IDs

**Then — architect design:**

| Choice | Command | When |
|---|---|---|
| Full-system | `/hitl:architect-design-system docs/00-migration/migration-brief.md` | Design all slices upfront |
| Slice-by-slice | `/hitl:architect-design-feature` (per slice) | Design each slice just before its development sprint |

**After design, each slice follows the 31-step workflow:** [Enhancement](#4-enhancement)

**Migration is complete when** every BI entry in the coverage matrix is `Complete` or `Descoped`. `Descoped` requires an explicit architect decision.

**Source code rule:** The source codebase is read-only reference. Never copy, import, or adapt source code into the target. Only behaviors (BI-NNN entries) transfer — the target implements them from scratch.

---

## 4. Enhancement

**When:** Adding a feature, implementing a requirement, or making a meaningful change to an already-onboarded project.

This is the standard day-to-day path. It assumes project setup (scenario 1, 2, or 3) is already complete.

**Typical flow:**

**Step 1 — Shape the requirement (PM or developer)**

```
/hitl:pm-design-feature        ← rough idea → structured requirement with ACs
/hitl:pm-add-feature           ← add a new feature to the PRD
/hitl:pm-enhance-feature       ← understand an existing feature, produce enhancement request
```

These produce a structured GitHub issue with acceptance criteria.

**Step 2 — Start the change**

```
/hitl:dev-practices
```

This is the 31-step workflow entry point. Paste the GitHub issue number when prompted.

**The 31 steps at a glance:**

| Phase | Steps | Key commands |
|---|---|---|
| Requirements | 1–2 | GitHub issue; Figma review (if applicable) |
| Design | 3–9 | `/hitl:dev-apply-change` → impact analysis, branch creation; `/hitl:dev-generate-docs` → HLD/LLD; `/hitl:qa-plan-tests`; architect assembles decision packet |
| TA gate ✅ | — | `/hitl:ta-approve` — architect approves design before any code |
| Build (TDD) | 10–17 | `/hitl:dev-tdd` RED → QA review → GREEN → refactor → `/hitl:dev-check-conventions` |
| Verify | 18–22 | `/hitl:dev-review-lld-adherence` × 2; `/hitl:architect-review-code`; `/hitl:qa-verify-quality` |
| Assess | 23–24 | `/hitl:dev-impact-brief`; rollout plan |
| TA gate ✅ | — | `/hitl:ta-approve` — architect approves code before merge |
| Ship | 25–29 | PR verification; integration verify; ops commands; deploy |
| Post-ship | 30–31 | 30-day ROI; 90-day ROI + ADR update (pentest, if applicable, runs in Ship via `/hitl:ops-pentest`) |

**Human gates (what you approve, in order):**

1. GitHub issue — PM or architect confirms scope
2. Figma review — PM/developer confirms UI requirements (if applicable)
3. Decision packet — architect approves design and test plan (TA gate 1)
4. QA test review — QA approves test coverage before code is written
5. Architect code review — architect reviews PR on GitHub (step 19a)
6. QA verify — QA confirms acceptance criteria met
7. TA code gate — architect approves implementation for merge (TA gate 2)
8. PR merge — tech lead or architect merges

**Statusline shows your position** in the 31 steps on every prompt. If you get lost:
```
/hitl:dev-validate
```
Runs all checks and tells you what's incomplete.

---

## 5. Bug Fix

**When:** A defect has been identified in an onboarded project — regression, behavioral error, or production issue (non-P0).

**Flow:**

**Step 1 — Document the bug**
```
/hitl:pm-report-bug
```
Produces a structured GitHub issue with: reproduction steps, expected vs actual behavior, severity, and a regression test requirement.

**Step 2 — Start the fix**
```
/hitl:dev-practices
```

Bug fixes are typically **Tier 1** (abbreviated workflow):
- Steps 1–2: issue and optional Figma review
- Steps 3, 5, 7, 9: impact analysis, LLD update if behavior changed, test planning, decision packet
- TA gate (if Tier 2+ — cross-domain or security-related)
- Steps 10–13: write regression test first (RED), verify it fails
- Steps 14–15: write fix (GREEN), verify tests pass
- Steps 17–22: convention check, two code reviews, QA verify
- Steps 25–29: PR and deploy

**Key rule:** the regression test is written **before** the fix. Step 13 must fail before step 14.

If the bug is related to a past production incident, `/hitl:pm-report-bug` flags it for the incident registry automatically.

---

## 6. Incident Response

**When:** An active production incident — P0 system down or P1 significant impact.

```
/hitl:ops-incident
```

**P0 flow — fix first, document after:**

1. **Immediate triage** — Claude reads recent logs, deployment history, and changes in the blast radius domain
2. **Hypothesis** — proposes most likely root cause with confidence rating
3. **Fix** — implements the minimal targeted fix; no refactoring during incident
4. **Verify** — confirms the fix resolves the symptom before deploying
5. **Deploy** — uses `/hitl:ops-deploy` with expedited rollout; `/hitl:ops-rollback` if metrics regress
6. **Post-incident (within 48 hours):**
   - Create or update the LLD for the affected component
   - Add incident to `docs/04-operations/incident-registry.yaml` with `regression_test_ref`
   - Write a regression test covering the failure mode
   - File a GitHub issue for any structural fix needed (and run the full 31-step workflow for it)

**What you skip during P0:** TA design gate, full TDD cycle. These are replaced by the post-incident doc requirement.

**P1 flow — abbreviated:**
```
/hitl:pm-report-bug     ← document before fixing
/hitl:dev-practices     ← abbreviated: issue → minimal analysis → code → test → PR
```

---

## Role-specific commands

Each role has dedicated commands. All can be used in the same Claude Code session — state your role at the start.

### PM
| Command | Use |
|---|---|
| `/hitl:pm-design-feature` | Rough idea → requirement with user stories and ACs |
| `/hitl:pm-add-feature` | Add feature to PRD |
| `/hitl:pm-enhance-feature` | Enhancement request for existing feature |
| `/hitl:pm-update-requirement` | Change ACs, scope, or priority on existing requirement |
| `/hitl:pm-report-bug` | Structured bug report → GitHub issue |
| `/hitl:pm-review-progress` | Sprint or milestone progress vs PRD goals |
| `/hitl:pm-review-scope-change` | Impact analysis of a proposed scope change |
| `/hitl:pm-answer-questions` | Answer product questions using PRD and existing docs |
| `/hitl:pm-prioritize` | Prioritize backlog by value, effort, and risk |
| `/hitl:pm-prep-demo` | Demo script or talking points for a feature |

### Architect
| Command | Use |
|---|---|
| `/hitl:architect-design-system` | Design a new system from a PRD or migration brief |
| `/hitl:architect-design-feature` | Design a feature: impact analysis, HLD, LLD, decision packet |
| `/hitl:architect-review-existing` | Reconstruct ADRs from an existing codebase via architect interview |
| `/hitl:architect-review-code` | Code review step 19a — creates GitHub PR with checklist |
| `/hitl:ta-approve` | TA gate: advance design or code phase from awaiting to approved |
| `/hitl:dev-review-external-docs` | Architect deep review of migration docs (migration path only) |

### QA
| Command | Use |
|---|---|
| `/hitl:qa-plan-tests` | Design-time review of LLD — identify edge cases before TDD |
| `/hitl:qa-review-tests` | Formal test coverage review after TDD RED phase |
| `/hitl:qa-verify-quality` | Post-handoff verification against acceptance criteria |
| `/hitl:qa-report-defect` | Structured defect report when verify-quality finds issues |

### Ops
| Command | Use |
|---|---|
| `/hitl:ops-build` | Validate and run the build pipeline |
| `/hitl:ops-deploy` | Structured deployment workflow |
| `/hitl:ops-apply-iac` | Apply infrastructure-as-code changes |
| `/hitl:ops-migrate-database` | Run and verify a database migration |
| `/hitl:ops-backup-database` | Trigger and verify a backup |
| `/hitl:ops-setup-observability` | Set up logging, metrics, and alerting |
| `/hitl:ops-verify-scripts` | Validate scripts before use |
| `/hitl:ops-post-deploy-monitor` | Monitor a deployment after it goes live |
| `/hitl:ops-detect-drift` | Detect configuration or infrastructure drift |
| `/hitl:ops-rollback` | Roll back a deployment |
| `/hitl:ops-pentest` | Penetration test workflow |
| `/hitl:ops-incident` | P0/P1 incident response |

---

## Context switching between issues

If you need to work on a different issue in the same Claude Code session:

```
/hitl:dev-switch-context 42
```

This stashes uncommitted work, checks out the `issue/42-*` branch, reloads all artifacts for issue 42 from disk (GitHub issue, HLD, LLD), and outputs a context-reset block. All prior conversation context is discarded — Claude starts fresh with only the new issue's artifacts.

**Recommended alternative:** open a new Claude Code session for each issue. A new session guarantees zero context bleed.

---

## Quick reference

| I want to... | Command |
|---|---|
| Start a new project | `/hitl:dev-start-from-prd` |
| Onboard an existing codebase | `/hitl:dev-start-brownfield` |
| Set up a migration project | `/hitl:dev-start-migration` |
| Start any feature or change | `/hitl:dev-practices` |
| Design a feature (architect) | `/hitl:architect-design-feature` |
| Write tests then code (TDD) | `/hitl:dev-tdd` |
| Generate HLD or LLD | `/hitl:dev-generate-docs` |
| Report a bug | `/hitl:pm-report-bug` |
| Respond to a P0 incident | `/hitl:ops-incident` |
| Approve a design gate | `/hitl:ta-approve` |
| Validate all session work | `/hitl:dev-validate` |
| Switch to a different issue | `/hitl:dev-switch-context [issue-number]` |
| Update the plugin | `/hitl:dev-update` |
| Find the right command | `/hitl:help [describe your situation]` |
