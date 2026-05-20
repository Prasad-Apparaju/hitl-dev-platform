---
name: architect:review-code
description: Human architect code review — step 19a. After AI rounds 1 and 2 have resolved mechanical issues (LLD conformance, conventions, test coverage), the architect reviews for judgment calls that AI cannot assess: business logic correctness, architectural consistency, domain boundary integrity, hidden coupling, and naming clarity. Blocks progression to step 20 until the architect explicitly approves.
argument-hint: "[change ID or issue number]"
disable-model-invocation: true
---

# Architect Code Review

Human architect review of the implementation. AI rounds 1 and 2 verified LLD conformance, conventions, security patterns, and test coverage. This step reviews the things that require judgment: is this the right design, not just a correct implementation of the spec?

**Input:** $ARGUMENTS (change ID or issue number)

**Refusal rule:** If `.hitl/current-change.yaml` does not show both `code_review.round_1: complete` and `code_review.round_2: complete`, stop: "AI review rounds 1 and 2 must complete before architect review. Run `/hitl:dev:check-implementation` for Round 1, then Round 2."

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

## Step 1 — Create the PR and prepare the review package

### 1a. Gather change context

Read `.hitl/current-change.yaml`. Extract:
- `change_id`, `manifest.domain`, `allowed_paths`
- `source_artifacts.lld` — path to the approved LLD
- `source_artifacts.decision_packet` — path to the decision packet
- Any AI review findings recorded from rounds 1 and 2

### 1b. Pre-flight checks

Before pushing, run these checks and stop if any fail:

```bash
# Must not be on main/master
branch=$(git branch --show-current)
[[ "$branch" == "main" || "$branch" == "master" ]] && echo "ERROR: on protected branch $branch — create a feature branch first" && exit 1

# Working tree must be clean (all changes committed)
[[ -n "$(git status --short)" ]] && echo "ERROR: uncommitted changes — commit or stash before creating PR" && exit 1

# PR must not already exist for this branch
existing=$(gh pr view --json url --jq '.url' 2>/dev/null)
[[ -n "$existing" ]] && echo "PR already exists: $existing — use that PR, do not create a duplicate" && exit 1
```

If any check fails, stop and report the issue to the developer. Do not proceed.

### 1c. Create the GitHub PR

Push the current branch and open a regular PR. The PR description must include all artifacts assembled so far:

```bash
git push -u origin HEAD

gh pr create \
  --title "<short summary of the change>" \
  --body "$(cat <<'EOF'
## Change
Closes #<issue-number>

## Artifacts
- **LLD:** <source_artifacts.lld>
- **Decision packet:** <source_artifacts.decision_packet>
- **Test plan:** `.hitl/current-change.yaml` — `test_plan` section

## AI Review Summary
**Round 1 findings (acceptable drift carried forward):**
- <finding or "none">

**Round 2 findings (acceptable drift carried forward):**
- <finding or "none">

## Checklist (architect to complete in GitHub review)
- [ ] Business logic — code solves the problem described in the issue, not just the spec
- [ ] Architectural consistency — approach is consistent with similar solutions elsewhere in the system
- [ ] Domain boundary integrity — no code reaches into another domain's internals
- [ ] Hidden coupling — no shared mutable state, implicit ordering, or timing assumptions outside the LLD
- [ ] Complexity — could this be simpler without losing correctness?
- [ ] Naming — names communicate intent to a future reader
- [ ] Error handling — failures are diagnosable from logs; errors are surfaced correctly to callers
EOF
)"
```

Request the architect as a reviewer:

```bash
# Replace <architect-github-username> with the value from system-manifest.yaml or team config
gh pr edit --add-reviewer <architect-github-username>
```

If the architect's GitHub username is not known, ask the developer before proceeding.

Record the PR URL in `.hitl/current-change.yaml`:
```yaml
pr_url: <PR URL from gh pr create output>
```

Report the PR URL to the developer.

### 1d. Summarise AI findings (for PR description)

From rounds 1 and 2, pull findings classified as **acceptable drift** — these are decisions the developer made that AI accepted. They are the first candidates for the architect to scrutinise on the PR.

---

## Step 2 — Architect reviews on GitHub

The architect receives a GitHub review request notification and reviews the PR on GitHub using line comments and the review UI.

**What the architect reviews** (the checklist is in the PR description):

**1. Business logic correctness** — Does this code actually solve the problem the GitHub issue describes, or does it solve the spec of the problem? Walk through the most important acceptance criterion manually.

**2. Architectural consistency** — Is this consistent with how similar problems are solved elsewhere in the same domain? If it diverges, is the divergence justified or does it introduce a second way to do the same thing?

**3. Domain boundary integrity** — Does any code reach into another domain's internals rather than calling its facade API? Check `system-manifest.yaml` `depends_on` — are any new implicit dependencies introduced?

**4. Hidden coupling** — Shared mutable state without coordination; implicit ordering (A must run before B but nothing enforces it); timing assumptions as magic numbers; global side effects not captured in the LLD?

**5. Complexity** — Could any part of this be simpler without losing correctness? Would a developer not in the design session understand each method from its name and signature?

**6. Naming** — Do names communicate intent to a future reader? Are any names misleading in a broader reading?

**7. Error handling** — Will failures be diagnosable from logs alone? Are errors surfaced to callers in a way that lets them make correct decisions?

**GitHub review outcome:**
- **Approve** the PR → proceed to recording approval below
- **Request changes** → developer addresses, pushes commits, re-requests review
- Do not merge the PR here — merging happens at Step 28

---

## Step 3 — Record the decision

### If APPROVED (architect approved the GitHub PR)

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
  --body "## Architect Code Review — Approved

Architect approved PR <PR URL> at <ISO timestamp>.

**Domain:** <domain>
**LLD:** <lld-path>

Proceed to Step 20 (Rerun Tests)."
```

Report: "Architect code review approved. Proceed to Step 20 — Rerun Tests."

---

### If REVISIONS REQUIRED (architect requested changes on the GitHub PR)

Classify each revision request from the GitHub review:

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

Next action: address revisions on the existing PR branch, then re-request architect review.
```

---

## Important Rules

- The PR is created once at this step and is not recreated at Step 25 — Step 25 verifies PR completeness
- Do not answer the checklist on behalf of the architect — the checklist lives in the PR description and the architect fills it in via GitHub review
- A SIGNIFICANT revision means the developer returns to Step 14, re-generates the code, and re-runs AI rounds 1 and 2 before re-requesting architect review on the same PR
- Architect approval recorded here is distinct from `approvals.architecture` (design approval at Step 9) — both must be set before merge
- Do not merge the PR at this step — merging is part of Step 28
