# Brownfield Adoption Guide — The One-Week Baseline Sprint

An architect working with AI can produce the full documentation baseline for an existing codebase in one week. This guide covers the day-by-day plan.

## Who

One architect (or senior dev who knows the system), working with Claude full-time for a week.

## Input

Whatever exists — code, old wiki pages, Confluence docs, Swagger specs, README files, Slack threads, Jira tickets, architecture diagrams. Even stale docs are useful — they show intent even if they've drifted.

## Output

A complete documentation baseline ready for the HITL process: system manifest, HLDs, LLDs, ADRs, and the process itself.

## Day-by-Day Plan

### Day 1: System Manifest from Code

| Hour | Architect does | AI does |
|------|---------------|---------|
| 1-2 | Points AI at codebase. Answers "what is this module for?" | Scans directory tree, parses imports, produces draft domain boundary map |
| 3-4 | Reviews boundaries, corrects ("billing and payments are one domain") | Generates full system-manifest.yaml with file lists, dependency graph, placeholder facades |
| 5-6 | Fills in judgment-dependent fields: mutation descriptions, preconditions, risk notes | Produces cross-cutting conventions from code patterns (decorators, base classes) |
| 7-8 | Reviews interaction matrix, corrects wrong edges | Final manifest committed |

**End of Day 1:** working system-manifest.yaml — ~80% accurate, 100% coverage.

### Days 2-3: HLDs from Infrastructure + Architecture

AI reads deployment configs, database schemas, network policies, and the service layer. Produces 5-8 HLDs:

- System architecture (components + deployment)
- Data architecture (entity relationships, tenant isolation)
- Service/agent architecture (component interactions)
- Security posture (auth, secrets, network)
- Observability (logging, tracing, metrics)

Architect reviews each for 30-60 min. Corrects factual errors. Adds the "why" that code can't tell you.

### Days 3-4: LLDs from Source Code

AI generates one LLD per domain from the manifest's file list. Extracts class hierarchies, public methods, state machines, error handling patterns.

Architect reviews in priority order: **hot domains first** (changed weekly), **cold domains last** (marked "DRAFT — not reviewed").

### Days 4-5: ADRs from Tribal Knowledge

Two sources:

**Architect-driven**: architect tells AI about each decision. AI formats as ADR. High confidence.

**AI-forensic**: for decisions nobody remembers, AI infers from code. Lower confidence, marked "NEEDS VERIFICATION."

### Day 5 Afternoon: Process Setup

1. Commit all docs
2. Copy skills to `.claude/commands/`
3. Copy and fill in CLAUDE.md template
4. Set up convention checker + CI
5. Apply the full process to ONE real change as proof-of-concept

## The Quality Curve

| When | Accuracy | What improves it |
|------|----------|------------------|
| Day 1 (manifest) | ~80% | Architect review |
| Day 5 (full baseline) | ~70% overall | Mix of verified (90%) and AI-drafted (60%) |
| Week 2 | ~75% | First re-run + first real changes |
| Month 1 | ~85% | 10-15 changes each corrected their area |
| Month 3 | ~95% | Hot paths battle-tested |

**70% accurate docs on day 5 are infinitely more useful than 100% accurate docs on month 6.**

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
