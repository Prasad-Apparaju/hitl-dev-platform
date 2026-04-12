# Brownfield Adoption Guide — The One-Week Baseline Sprint

An architect working with AI can produce the full documentation baseline for an existing codebase in one week. This guide covers the day-by-day plan.

## Who

One architect (or senior dev who knows the system), working with Claude full-time for a week.

## Input

Whatever exists — code, old wiki pages, Confluence docs, Swagger specs, README files, Slack threads, Jira tickets, architecture diagrams. Even stale docs are useful — they show intent even if they've drifted.

## The Skill

The `/generate-docs` skill (at `skills/generate-docs/`) automates most of this sprint. Run it in **reverse-engineer mode**:

```
/generate-docs reverse-engineer the existing system
```

It scans the codebase, generates the manifest, HLDs, LLDs, and forensic ADRs, and sets up the process — with approval gates at each phase. The architect reviews and corrects at each gate.

The day-by-day plan below describes what happens at each phase. The skill handles the AI side; the architect handles the judgment.

## Output

A complete documentation baseline ready for the HITL process: system manifest, HLDs, LLDs, ADRs, and the process itself.

## The Sprint

| What | AI does | Architect does |
|------|---------|---------------|
| **System manifest** | Scans directory tree + imports → produces domain boundaries, file lists, dependency graph, convention detection, placeholder facades | Reviews boundaries ("these two are one domain"), fills in mutation descriptions + preconditions + risk notes |
| **HLDs** (5-8 docs) | Reads deployment configs, schemas, service layer → generates system/data/service/security/observability architecture docs | Reviews each for 30-60 min. Corrects facts. Adds the "why" that code can't tell you. |
| **LLDs** (one per domain) | Reads source files per domain → extracts class hierarchies, method signatures, state machines, error patterns | Reviews hot domains first, marks cold domains "DRAFT — not reviewed" |
| **ADRs** | Infers decisions from code patterns (framework choices, auth approach, error handling). Marks as "INFERRED — NEEDS VERIFICATION" | Verifies inferred ADRs. Adds decisions that aren't visible in code (tribal knowledge). |
| **Process setup** | Generates CLAUDE.md from template, convention-checks.yaml from detected patterns, copies skills + CI actions | Reviews conventions, applies the process to ONE real change as proof-of-concept |

## The Quality Curve

| When | Accuracy | What improves it |
|------|----------|------------------|
| Day 1 (manifest) | ~80% | Architect review |
| Day 5 (full baseline) | ~70% overall | Mix of verified (90%) and AI-drafted (60%) |
| Week 2 | ~75% | First re-run + first real changes |
| Month 1 | ~85% | 10-15 changes each corrected their area |
| Month 3 | ~95% | Hot paths battle-tested |

**70% accurate docs on day 5 are infinitely more useful than 100% accurate docs on month 6.**

## After the Sprint: Assessing and Closing the Gaps

The sprint reveals every gap between the system's current state and what the process requires. Run the convention checker + manifest completeness check + lethal trifecta audit on day 5. Bucket the findings:

| Tier | Gate | AI does | Architect does |
|------|------|---------|---------------|
| **Blocker** — data loss, security breach, or production incident risk (missing tenant isolation, missing idempotency, unmitigated prompt injection) | Fix before feature work starts in the affected domain | Scans code, generates the fix + tests, produces PR | Reviews: "Is the fix structurally enforced, not just a code comment?" |
| **Near-term** — will cause issues within a month (missing retry logic, missing tests on hot paths, unverified forensic ADRs) | Fix in parallel with feature work | Generates retry wrappers, test stubs, ADR drafts | Reviews: "Is the retry budget reasonable? Do the tests cover real behavior?" |
| **Medium-term** — convention drift, stale LLDs, missing training plans | Fix as a rider on feature PRs (compliance-on-touch) | During each feature PR, also fixes one gap in the touched domain | Reviews: "Does this change behavior, or just style?" |
| **Long-term** — naming, comments, unused code in cold domains | Fix when the domain is next touched | Generates the fix when the developer opens the file for other reasons | No dedicated review — standard PR process |

**Feature work proceeds when blockers are zero.** The convention checker tracks the rest — its violation count on every PR is the compliance dashboard.

## The Weekly Delta Re-run

After the sprint, run the manifest generator weekly. It produces a delta report:

- NEW FILES not in manifest
- DELETED FILES still in manifest
- CHANGED INTERFACES
- CONVENTION DRIFT

Architect reviews (~15 min/week), accepts or rejects. The manifest stays current.

## Handling "Nobody Knows Why" Areas

Don't fake it. Document the uncertainty:

```yaml
legacy_billing:
    purpose: "Legacy billing — poorly understood"
    facade_apis:
      note: "DO NOT modify without full manual regression test."
    conventions:
      - "Changes skip AI code-generation — written by hand"
```

Documenting "we don't understand this" is MORE valuable than a wrong LLD.

## Expedited Path for Incidents

| Urgency | Process | Doc requirement |
|---------|---------|-----------------|
| P0 (system down) | Fix first | Write LLD for affected area within 48 hours |
| P1 (significant) | Abbreviated: issue → minimal analysis → code → test → PR | Write LLD during PR review |
| P2+ (everything else) | Full 22-step process | Standard docs-before-code |

## Common Objections

| Objection | Response |
|-----------|----------|
| "No time for docs" | AI writes them. You review. 15 min per change. |
| "Code changes too fast" | Docs change WITH the code in the same PR (step 14). |
| "AI won't understand legacy code" | It doesn't need to understand all of it. Just the manifest + the area being changed. |
| "Nobody will read the docs" | The AI reads them. Docs are input to code generation, not shelf decoration. |
| "We tried this before" | Did you start with the whole system or one change? Start with one. |
