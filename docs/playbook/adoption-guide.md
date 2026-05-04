# Adoption Guide — Baseline Sprint

> **Greenfield (new system from PRD)?** Use `/architect:design-system` — it guides the architect through domain decomposition, manifest creation, HLDs, ADRs, LLDs, and HITL process bootstrap in one session. After it completes, use `/architect:design-feature` for every subsequent change.
>
> **Brownfield (existing codebase)?** Continue reading — this guide covers the reverse-engineer sprint.

An architect working with AI can produce the documentation baseline for an existing codebase in a sprint — typically one to two weeks for a medium-sized system. Larger platforms, systems with significant tribal knowledge gaps, or codebases with heavy integration surface area take longer. The goal is an honest starting point, not a finished product.

## Realistic scope expectations by system size

| System | Characteristics | Sprint estimate |
|--------|----------------|-----------------|
| Small service | <20 source modules, 1-2 integrations, well-documented | 3-5 days |
| Medium service ecosystem | 20-80 modules, 4-8 integrations, partial docs | 1-2 weeks |
| Large legacy platform | 80+ modules, many integrations, heavy tribal knowledge | 2-4 weeks |

The estimate assumes an architect who knows the system. A developer who does not know the system adds 30-50% to each range.

## Who

One architect (or senior dev who knows the system), working with Claude full-time for the sprint.

## Input

Whatever exists — code, old wiki pages, Confluence docs, Swagger specs, README files, Slack threads, Jira tickets, architecture diagrams. Even stale docs are useful — they show intent even if they've drifted.

## The Skill

The `/generate-docs` skill (at `skills/generate-docs/`) automates most of this sprint. Run it in **reverse-engineer mode**:

```
/generate-docs reverse-engineer the existing system
```

It scans the codebase, generates the manifest, HLDs, LLDs, and forensic ADRs, and sets up the process — with approval gates at each phase. The architect reviews and corrects at each gate.

The skill handles the AI side; the architect handles the judgment.

**For medium and large systems, install Graphify before starting the sprint.** The design doc set produced by this sprint (HLDs + LLDs + manifest + ADRs) can reach hundreds of kilobytes — exceeding the context window on large platforms. Graphify indexes those docs as a knowledge graph so subsequent queries retrieve only the relevant slice.

```bash
pip install graphifyy && graphify install
graphify . --directed --no-viz          # run from repo root after the sprint completes
python3 -m graphify.serve graphify-out/graph.json
```

The PostToolUse hook rebuilds the graph incrementally after each doc edit, so it stays current as the sprint produces output. See `CLAUDE.md` in your project for query syntax.

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

These are rough directional estimates from initial projects, not precise benchmarks. Accuracy depends heavily on how well-documented the existing system is, how much tribal knowledge the architect can supply, and how many hot paths the team touches in the first weeks.

| When | Accuracy (rough range) | What improves it |
|------|------------------------|------------------|
| After manifest | 60-80% | Architect review |
| After full sprint | 55-75% overall | Mix of verified (80-90%) and AI-drafted (50-65%) |
| Week 2 | 65-80% | First re-run + first real changes |
| Month 1 | 75-90% | 10-15 changes each corrected their area |
| Month 3 | 85-95% | Hot paths battle-tested |

**Treat the sprint output as a starting point, not a finished product.** Incomplete-but-existing docs are more useful than no docs, because the process corrects them through normal use. Mark unverified sections explicitly (see [Handling "Nobody Knows Why" Areas](#handling-nobody-knows-why-areas)) so the team knows what to trust.

## After the Sprint: Assessing and Closing the Gaps

The sprint reveals every gap between the system's current state and what the process requires. Run the convention checker + manifest completeness check + lethal trifecta audit at the end of the sprint. Bucket the findings:

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
| P0 (system down) | Fix first | Use `/generate-docs` to produce LLD for affected area within 48 hours |
| P1 (significant) | Abbreviated: issue → minimal analysis → code → test → PR | Use `/generate-docs` to produce LLD during PR review |
| P2+ (everything else) | Full 31-step process | Standard docs-before-code |

## Staying Operational — Week 2 and Beyond

The baseline sprint produces the starting state. Keeping the process working over weeks and months requires knowing what must stay in sync, who owns it, and which parts are hard requirements versus optional.

### Ownership

| Artifact | Owner | Update trigger |
|---|---|---|
| `docs/system-manifest.yaml` | Architect | Any PR that adds files, changes domain boundaries, or modifies a facade API |
| `docs/02-design/technical/lld/` | Domain lead (developer) | Same PR as the code change — docs and code move together |
| `docs/03-engineering/testing/test-registry.yaml` | Developer + QA | Every test added, removed, or renamed |
| `docs/04-operations/incident-registry.yaml` | Ops + Lead | After every production incident |
| `docs/decisions/issue-<N>.yaml` | Architect | Created at step 9; updated only if scope changes before merge |
| `.hitl/current-change.yaml` | Developer | Created by `/apply-change`; updated at each phase gate; deleted after merge |

### Hard requirements vs. optional

**Hard requirements — the process breaks without these:**
- `.hitl/current-change.yaml` present and current before any code edit
- LLDs updated in the same PR as the code change (reconcile-docs step)
- Manifest updated when domain boundaries or facade APIs change
- Test registry updated when tests change

**Optional — adds value but the process works without them:**
- Graphify (skills fall back to direct reads)
- Token-cost tracking (valuable for ROI calibration; skip until the workflow is running smoothly)
- 30/90-day ROI checks (only triggered when step 4 ROI estimate was done)
- Training plan stubs (only triggered by new architectural patterns)

### Signals that the process is drifting

- LLDs that describe the old behavior — code and docs have separated
- Convention checker violations accumulating across PRs instead of being fixed in-session
- `.hitl/current-change.yaml` missing or showing a stale `status`
- Test registry entries without `domain` or `risk` fields — registration discipline has slipped
- Incident registry entries without a `regression_test_ref` — past failures are not being encoded

The manifest delta re-run (weekly, ~15 min) and convention checker (every PR) are the two routine signals that catch drift before it compounds.

## Common Objections

| Objection | Response |
|-----------|----------|
| "No time for docs" | AI drafts them; you review and correct. For Tier 2 changes the overhead is real but front-loaded — it prevents larger rework later. For Tier 0-1, the process is lightweight by design. |
| "Code changes too fast" | Docs change WITH the code in the same PR (step 14). |
| "AI won't understand legacy code" | It doesn't need to understand all of it. Just the manifest + the area being changed. |
| "Nobody will read the docs" | The AI reads them. Docs are input to code generation, not shelf decoration. |
| "We tried this before" | Did you start with the whole system or one change? Start with one. |
