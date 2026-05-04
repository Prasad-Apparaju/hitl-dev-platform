---
name: migrate/review-external-docs
description: Architect deep review of external migration documentation. Reads staged reference docs, critically evaluates their reliability and gaps, and produces two outputs — a migration review (critique) and a migration brief (PRD-equivalent). The migration brief is the required input for /architect:design-system or /architect:design-feature. No HITL design work begins until both documents are approved.
argument-hint: "[optional: specific doc or section to focus on]"
disable-model-invocation: true
---

# Migration — External Docs Deep Review

**Input:** External docs staged in `docs/00-migration/external-reference/` and context from `docs/00-migration/migration-context.yaml`.

**Output:**
- `docs/00-migration/migration-review.md` — critical evaluation of the external docs
- `docs/00-migration/migration-brief.md` — PRD-equivalent requirements for the target system

**Refusal rule:** If `docs/00-migration/external-reference/` is empty and no migration context exists, stop and say: "Run `/start-migration` first — the external docs must be staged and migration context recorded before the review can begin."

Work through phases in order. Pause after each output and wait for architect approval before proceeding.

---

## Phase 1 — Read Context

### 1a. Read migration context

Read `docs/00-migration/migration-context.yaml`. Extract:

| Field | Value |
|---|---|
| Source system | |
| Target system | |
| Migration trigger | |
| External docs available | |

If the file does not exist, stop: "Migration context not found. Run `/start-migration` first."

### 1b. Inventory external reference docs

List all files under `docs/00-migration/external-reference/`. For each:
- File name and type
- Approximate size (lines or pages)
- A one-sentence description of its apparent purpose

Show the inventory to the architect. Ask: "Is anything missing from this list? Are there docs that didn't make it into the reference directory?"

### 1c. Read all external docs

Read each file in full. Do not summarize yet — full comprehension before evaluation.

---

## Phase 2 — Critical Evaluation

Evaluate each external document against four dimensions. Be specific — cite page numbers, section headings, or direct quotes where relevant.

### 2a. Reliability assessment

For each external doc, identify which claims can be trusted as design input:

- **Strong signal:** vendor-produced migration guides for the target platform, field-mapping specs produced by domain experts, runbooks proven in production migrations
- **Weak signal:** consultant deliverables without validation evidence, "best practice" guides without context for this specific source/target pair, docs older than 18 months on rapidly-evolving platforms
- **Flag explicitly:** anything that conflicts with what `/start-migration` recorded as the migration trigger or target architecture

### 2b. Gap analysis

What is missing from the external docs that the architect must supply?

Common gaps in migration documentation:
- Data volume and growth rate (needed for infrastructure sizing)
- Latency and throughput requirements for the target system
- Security and compliance constraints that differ between source and target
- Rollback plan and rollback criteria
- Definition of "migration complete" (what does success look like, measurably?)
- Integration contracts with systems not being migrated
- Operational runbook for the cutover window

List each gap as: **[Gap]** — *what is missing* — *why it matters for the HITL design*.

### 2c. Divergence recommendations

Where should HITL design diverge from the external docs?

Look for:
- Recommendations that assume a different scale, team size, or risk tolerance than this project
- Patterns that contradict the target system's conventions (as recorded in CLAUDE.md and the target manifest)
- Vendor recommendations that benefit the vendor rather than the migration team
- Suggestions that conflict with HITL's slice-by-slice, observable-increment model

List each divergence as: **[Diverge]** — *what the external doc recommends* — *what HITL should do instead and why*.

### 2d. Risk flags

Identify the top 3–5 risks visible in the external docs or their gaps:

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| | | | | |

---

## Phase 3 — Write the Migration Review

Write `docs/00-migration/migration-review.md` with the following structure:

```markdown
# Migration Review — [Source] → [Target]

**Reviewed by:** [Architect name]
**Review date:** [Date]
**Status:** DRAFT — awaiting architect approval

## Source material reviewed

[List of docs with reliability rating: Reliable / Weak / Flagged]

## Reliable inputs

[What can be used directly as HITL design input, with citations]

## Gaps requiring architect decision

[Numbered list of gaps from Phase 2b]

## Divergence recommendations

[Numbered list from Phase 2c]

## Risk flags

[Table from Phase 2d]

## Review verdict

[One paragraph: is there enough reliable input to begin design? What must be resolved before HLD work starts?]
```

Show the draft. Ask: "Does this review accurately reflect the external docs? Anything to add or correct?"

Incorporate feedback. Set `status: approved` only after the architect explicitly approves.

---

## Phase 4 — Write the Migration Brief

The migration brief is the PRD-equivalent for the migration. It is the required input for `/architect:design-system` (full-system migration) or `/architect:design-feature` (slice-by-slice). The architect skills read this file in place of `docs/01-product/prd.md`.

Write `docs/00-migration/migration-brief.md` with the following structure:

```markdown
# Migration Brief — [Source] → [Target]

**Status:** DRAFT — awaiting architect approval

## Purpose and scope

[One paragraph: what is being migrated, why, and what "done" means]

## Functional requirements

| ID | Requirement | Source | Priority |
|---|---|---|---|
| MR-001 | [Specific, testable requirement] | [External doc / migration context] | Must-have |

[List every must-have and should-have requirement. Each must be testable — "the target system must process X records per second" not "the system must be fast".]

## Non-functional requirements

| Dimension | Current (source) | Required (target) | Source |
|---|---|---|---|
| Throughput | | | |
| Latency (p99) | | | |
| Data volume | | | |
| Availability | | | |
| Recovery time | | | |

[Fill in from external docs + migration context. Mark as TBD if not in external docs — these become architect-owned gaps.]

## Known constraints

[Tech stack decisions already made, compliance requirements, infrastructure limits, timeline constraints]

## Out of scope

[Explicit exclusions — what is NOT being migrated]

## Open questions

[Questions the architect must resolve before HLD work can begin. Source them from the gap list in the review.]

## Slice criterion reminder

Every implementation slice must be **observable**: either user-visible (PM can demo it) or verifiable (ops/QA can confirm via record counts, data consistency checks, or performance comparison). "Data migrated but not yet accessible" does not pass the observable check.
```

Show the draft. Ask: "Does this brief capture the real requirements for the target system? Anything missing or wrong?"

Incorporate feedback. Set `status: approved` only after the architect explicitly approves.

---

## Phase 5 — Hand Off to Architect Design

Once both documents are approved, output this exactly:

---
**Migration review complete.**

Two documents produced:

| Document | Purpose | Status |
|---|---|---|
| `docs/00-migration/migration-review.md` | Critique of external docs | Approved |
| `docs/00-migration/migration-brief.md` | PRD-equivalent requirements | Approved |

**Next step — Architect design:**

For a **full-system migration** (designing the entire target system from scratch):
```
/architect:design-system docs/00-migration/migration-brief.md
```

For a **slice-by-slice migration** (migrating one domain at a time into an existing or partially-built target):
```
/architect:design-feature
```
(The migration brief replaces the PRD — reference it as `docs/00-migration/migration-brief.md` when the architect asks for the PRD path.)

**Before starting design:** resolve all open questions from the migration brief. The architect should not begin HLD work while open questions remain — unanswered NFRs at design time become architecture mistakes at build time.

**Slice criterion:** every slice must be observable — either user-visible or verifiable by ops/QA. The architect enforces this during Phase 7 of `/architect:design-feature`.

---
