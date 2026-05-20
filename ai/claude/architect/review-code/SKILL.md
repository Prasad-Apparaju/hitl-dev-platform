---
name: architect-review-code
description: Human architect code review — step 19a. After AI rounds 1 and 2 have resolved mechanical issues (LLD conformance, conventions, test coverage), the architect reviews for judgment calls that AI cannot assess: business logic correctness, architectural consistency, domain boundary integrity, hidden coupling, and naming clarity. Blocks progression to step 20 until the architect explicitly approves.
argument-hint: "[change ID or issue number]"
disable-model-invocation: true
---

# Architect Code Review

Human architect review of the implementation. AI rounds 1 and 2 verified LLD conformance, conventions, security patterns, and test coverage. This step reviews the things that require judgment: is this the right design, not just a correct implementation of the spec?

**Input:** $ARGUMENTS (change ID or issue number)

**Refusal rule:** If `.hitl/current-change.yaml` does not show both `code_review.round_1: complete` and `code_review.round_2: complete`, stop: "AI review rounds 1 and 2 must complete before architect review. Run `/check-implementation` for Round 1, then Round 2."

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Progress Banners

Format: `---` line, `**Architect Code Review — Step N / 3: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Prepare Package | `▶ Prepare · ○ Review · ○ Decision` |
| 2 | Architect Review | `✅ Prepare · ▶ Review · ○ Decision` |
| 3 | Record Decision | `✅ Prepare · ✅ Review · ▶ Decision` |

---

## Step 1 — Prepare the review package

### 1a. Gather change context

Read `.hitl/current-change.yaml`. Extract:
- `change_id`, `manifest.domain`, `allowed_paths`
- `source_artifacts.lld` — path to the approved LLD
- `source_artifacts.decision_packet` — path to the decision packet
- Any AI review findings recorded from rounds 1 and 2

### 1b. Build the diff

```bash
git diff main...HEAD -- $(cat .hitl/current-change.yaml | python3 -c "
import sys, yaml
cy = yaml.safe_load(sys.stdin)
paths = cy.get('allowed_paths', [])
print(' '.join(paths))
")
```

If `allowed_paths` is empty, fall back to `git diff main...HEAD`.

### 1c. Summarise AI findings

From rounds 1 and 2, pull the findings that were classified as **acceptable drift** (documented, no code change required). These are the decisions the developer made that the AI accepted — they are the first candidates for the architect to scrutinise.

### 1d. Present the package

```
Architect Code Review Package — <change-ID>
────────────────────────────────────────────
Domain:       <manifest.domain>
LLD:          <source_artifacts.lld>
Changed files:
  <list each file and a one-line description of what changed>

AI Round 1 findings carried forward (acceptable drift):
  - <finding 1>
  - <finding 2>
  (or "none")

AI Round 2 findings carried forward:
  - <finding>
  (or "none")
```

---

## Step 2 — Architect review

Present the checklist below to the architect. The architect reads the diff and the LLD, then answers each item. Do not answer on the architect's behalf — these are judgment calls that require a human decision.

---

**Architect checklist — what AI rounds did not assess:**

**1. Business logic correctness**
The spec may be met but the logic may still be wrong. Ask:
- Does this code actually solve the problem the GitHub issue describes, or does it solve the spec of the problem?
- Walk through the most important acceptance criterion manually. Does the code do what you expect, step by step?

**2. Architectural consistency**
Check whether the approach is consistent with existing patterns in the same domain or adjacent domains. Prefer a graph query:
```
/graphify query "similar patterns in domain: <domain-name>"
/graphify query "how is <pattern-type> implemented elsewhere in the system"
```
Fall back to reading LLDs in `docs/02-design/technical/lld/` directly.
- Is this consistent with how similar problems are solved elsewhere?
- If it diverges, is the divergence justified or does it introduce a second way to do the same thing?

**3. Domain boundary integrity**
- Does any code reach into another domain's internals rather than calling its facade API?
- Does this code expose any internal implementation details that callers should not depend on?
- Check `system-manifest.yaml` `depends_on` for the domain — are any new implicit dependencies introduced?

**4. Hidden coupling**
Things the spec rarely captures:
- Shared mutable state accessed without coordination
- Implicit ordering dependency (A must run before B, but nothing enforces it)
- Timing assumptions baked into the implementation (retry intervals, cache TTLs as magic numbers)
- Global side effects (writes to a shared log, modifies a registry, touches the filesystem) not mentioned in the LLD

**5. Complexity**
- Could any part of this be simpler without losing correctness?
- Would a developer who was not part of the design session understand the intent of each method from its name and signature alone?
- Are there abstractions that are not yet earning their complexity (only one callsite, only one implementation)?

**6. Naming**
- Do names communicate intent to a future reader, not just to the person who wrote them?
- Are any names misleading — correct in the narrow context but wrong in a broader reading?

**7. Error handling and observability**
- When this code fails, will the failure be diagnosable from logs alone?
- Are errors surfaced to callers in a way that lets them make correct decisions, or are they swallowed or over-generalised?

---

After the architect has worked through the checklist, ask:

> "Based on this review, what is your decision? Reply **APPROVED** to proceed, or list your revision requests."

---

## Step 3 — Record the decision

### If APPROVED

Update `.hitl/current-change.yaml`:
```yaml
approvals:
  architect_code_review: approved
  architect_code_review_at: <ISO timestamp>
  architect_code_review_notes: "<optional notes>"
```

Post a comment on the GitHub issue:
```bash
gh issue comment <issue-number> \
  --body "## ✅ Architect Code Review — Approved

Reviewed by architect at <ISO timestamp>.

**Domain:** <domain>
**LLD:** <lld-path>

Proceed to Step 20 (Rerun Tests)."
```

Report: "Architect code review approved. Proceed to Step 20 — Rerun Tests."

---

### If REVISIONS REQUIRED

Classify each revision:

| Severity | Criteria | Return to |
|---|---|---|
| **Minor** | Naming, simplification, comment clarity, small refactor | Step 16 — Refactor |
| **Significant** | Logic error, wrong abstraction, domain boundary violation, hidden coupling | Step 14 — Generate Code (GREEN) |
| **Design change** | Fundamental approach is wrong; LLD must be revised | Step 12 — Tests Improve Design (LLD update + architect re-review) |

Update `.hitl/current-change.yaml`:
```yaml
approvals:
  architect_code_review: revisions_requested
  architect_code_review_at: <ISO timestamp>
  architect_code_review_revisions:
    - severity: <minor|significant|design_change>
      description: "<what needs to change>"
      return_to_step: <16|14|12>
```

Present the revision list with step targets:

```
Architect revision requests — <change-ID>
──────────────────────────────────────────
  [Minor → Step 16]     <description>
  [Significant → Step 14] <description>

Next action: address revisions, then re-run /architect:review-code.
```

Post a comment on the GitHub issue:
```bash
gh issue comment <issue-number> \
  --body "## 🔄 Architect Code Review — Revisions Required

**Revisions requested:**
<numbered list>

Developer to address and re-run architect review before proceeding."
```

---

## Important Rules

- Do not answer the checklist on behalf of the architect — present it and wait
- The architect is reviewing for design judgment, not re-running what the AI already checked — do not re-present AI findings as if they need re-resolution
- A SIGNIFICANT revision means the developer returns to Step 14, re-generates the code, and re-runs AI rounds 1 and 2 before this review is repeated
- Architect approval recorded here is distinct from `approvals.architecture` (design approval at Step 9) — both must be set before merge
