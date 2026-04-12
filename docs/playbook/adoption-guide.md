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

## After the Sprint: Assessing and Closing the Gaps

The one-week sprint produces the documentation baseline. It also reveals every gap between the system's current state and what the process requires. These gaps are tech debt — but not all tech debt is equal. Some will cause production incidents next week. Others are cosmetic. Treating them all the same wastes time; ignoring them all guarantees the process fails.

### Step 1: Run the assessment

On day 5, after the baseline is committed, run three checks:

1. **Convention checker** against the full codebase — produces a concrete violation list
2. **Manifest completeness check** — which facade APIs are still DRAFT? Which domains have zero test entries in the test registry?
3. **Lethal trifecta audit** — which agents have unmitigated prompt injection risk?

The output is a numbered list of specific gaps, not a vague "we have tech debt" feeling. Each gap has a location (file, domain), a category (missing test, missing idempotency, convention violation), and a severity.

### Step 2: Bucket into four tiers

| Tier | Criteria | Examples | Action |
|------|----------|---------|--------|
| **Blocker — fix before feature work starts** | Will cause data loss, security breach, or production incident if any new feature touches this area. The risk is too high to proceed. | Missing tenant isolation (queries return other tenants' data). Missing idempotency on external side effects (can double-publish, double-charge). Lethal trifecta fully present with no HITL gate. | Dedicated issues, assigned immediately. No feature work in the affected domain until these are resolved. AI generates the fix; architect reviews. Target: closed within 1-2 weeks. |
| **Near-term — fix within the first month** | Won't cause an incident today, but will cause one soon. Blocks the team from trusting the process. | Missing retry/error handling on external API calls. Missing test coverage on hot-path domains (changed weekly, zero tests). Forensic ADRs for decisions that affect current work (team is making new decisions without knowing the old ones). | Dedicated sprint (1-2 weeks) run in parallel with feature work. AI generates the fixes (retry wrappers, test stubs, ADR drafts); developer reviews and corrects. Target: closed within month 1. |
| **Medium-term — fix through compliance-on-touch** | Technical cleanliness that improves the codebase gradually. Not urgent, but the convention checker keeps reminding you. | Convention drift (3 error handling patterns when there should be 1). Stale LLDs (reverse-engineered docs that are 70% accurate). Missing training plans for existing capabilities. Background workers without leader election. | **No dedicated sprint.** Every time a developer opens a file for feature work, they also fix one medium-term gap in that file. The feature is the reason the PR exists; the compliance fix is a rider. Target: trending to zero over 3-6 months. |
| **Long-term — fix when the domain is next touched** | Cosmetic, low-risk, or in cold areas of the codebase. | Naming inconsistencies. Comment density below threshold. Unused code. Stale docs for domains that haven't changed in 6+ months. | Don't schedule. Fix when the domain is touched for other reasons. If a domain is never touched, these gaps never matter. Target: best-effort, no deadline. |

### Step 3: Maximize AI for gap closure

AI can do most of the mechanical work of closing these gaps. The architect's job is to review, not to write. Here's what AI handles at each tier:

**Blockers (AI generates, architect reviews same-day):**

| Gap | What AI does | What the architect verifies |
|-----|-------------|---------------------------|
| Missing tenant isolation | Scans every DB query in the domain. Generates the `brand_id` filter for each one. Produces a PR with the changes + tests. | "Are these the right queries? Did it miss any? Is the filter in the right position (WHERE clause, not application-level)?" |
| Missing idempotency | Identifies every external API call. Wraps each in a `MutatingTool` subclass with idempotency key derivation. Generates the migration for the dedup table. | "Is the idempotency key derived from stable identity (campaign_id:index:channel), not from runtime state (trace_id)?" |
| Lethal trifecta | Proposes which leg to break for each agent. Generates the HITL gate, input sanitization, or data-access restriction. | "Is the mitigation structurally enforced (LangGraph state machine), not just a code comment?" |

**Near-term (AI generates, developer reviews within the week):**

| Gap | What AI does | What the developer verifies |
|-----|-------------|---------------------------|
| Missing retry logic | Reads the manifest's `cross_cutting` convention for retry. Wraps each external call in `retry_external_call()` with appropriate budget. | "Is the retry budget reasonable for this call? Should this call even retry, or should it fail fast?" |
| Missing test coverage | Reads the LLD for the domain. Generates tests from the spec — same TDD flow as feature work. Registers them in the test registry. | "Do these tests cover the actual behavior, or just the happy path? What edge cases are missing?" |
| Forensic ADR verification | Presents each forensic ADR to the architect: "I inferred X from the code. Is this correct?" Architect confirms or corrects. AI updates the ADR status from INFERRED to VERIFIED. | "Is the inferred rationale correct? Were there alternatives I should document?" |

**Medium-term (AI generates as part of feature PRs):**

| Gap | What AI does | What the developer verifies |
|-----|-------------|---------------------------|
| Convention drift | During the feature PR, AI also refactors the inconsistent pattern in the touched file to match the convention. | "Does this refactor change behavior, or just style? Run the tests." |
| Stale LLD | During the feature PR, AI updates the LLD for the domain being changed — correcting the 30% that was wrong in the reverse-engineered version. | "Does this LLD now match what the code actually does?" |
| Missing training plan | When a developer encounters a domain they don't understand, AI generates a training plan stub from the LLD. | "Would this plan have helped me understand the domain faster?" |

### Step 4: Track with the convention checker

The convention checker runs on every PR. The violation count is the compliance dashboard:

```
Week 1 (post-sprint):   Blockers: 5   Near-term: 12   Medium: 31   Long-term: 47
Week 2:                 Blockers: 0   Near-term: 8    Medium: 29   Long-term: 47
Week 4:                 Blockers: 0   Near-term: 0    Medium: 22   Long-term: 45
Week 8:                 Blockers: 0   Near-term: 0    Medium: 14   Long-term: 42
Week 12:                Blockers: 0   Near-term: 0    Medium: 6    Long-term: 38
```

**What the trend tells you:**
- Blockers hit zero in week 2 → the system is safe for feature work
- Near-term hit zero in week 4 → the process is trustworthy
- Medium trends down steadily → compliance-on-touch is working
- Medium plateaus → developers are skipping the compliance rider; enforce in PR review
- Long-term barely moves → expected; these are in cold code that nobody touches

### When is the system "compliant enough" to proceed with feature work?

**When blockers are zero.** That's the gate. Near-term, medium-term, and long-term gaps don't block feature work — they're addressed alongside it or on their own timeline.

The architect makes the blocker/non-blocker call on day 5 of the sprint. If the architect says "this gap is a blocker," it gets a dedicated issue and blocks feature work in that domain. If the architect says "this is near-term," feature work proceeds and the gap is fixed in parallel.

The convention checker enforces the trajectory. The test registry and incident registry capture the institutional knowledge. The process itself — feature work that follows the 26-step workflow — closes the remaining gaps organically because every PR that touches a domain also fixes one medium-term gap in that domain.

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
