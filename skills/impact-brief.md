# Downstream Impact Brief

Generate a structured impact brief for a change that is ready for PR. The brief tells downstream stakeholders (PM, QA, Ops) what changed, what can break, and how to deploy safely.

**Input:** $ARGUMENTS (PR number, branch name, or description of the change)

If `$ARGUMENTS` is empty, check for unstaged changes via `git diff` and use those. If no changes found, ask: "What change should I assess? Provide a PR number or describe the change."

---

## Step 1 — Gather context

1. **Read the diff** — `git diff main...HEAD` or the PR diff
2. **Read the system manifest** (`docs/system-manifest.yaml`) — identify which domains are affected
3. **Read the incident registry** (`docs/incident-registry.yaml`) — find past incidents in the affected domains
4. **Read the test registry** (`docs/03-engineering/testing/test-registry.yaml`) — check coverage for the affected areas

---

## Step 2 — Draft the 5-section brief

Generate each section. Mark anything you're uncertain about with "⚠️ VERIFY".

### Section 1: Flows and components changed

List user-visible behaviors that differ after this change. Not code paths — user journeys.

- Good: "Campaign creation now shows a TikTok option in the channel selector"
- Bad: "`campaigns.py` line 47 changed"

### Section 2: Risk assessment

What can break? For each risk:
- What could go wrong
- Severity (data loss / user-facing error / internal error / cosmetic)
- Likelihood (high / medium / low)
- Which existing tests cover it (reference test registry)
- Which past incidents are relevant (reference incident registry)

### Section 3: Manual verification scenarios

What should be tested beyond the automated suite? These are deployment-time checks that unit tests cannot cover.

- Example: "Publish a real post to Instagram and verify it appears within 60 seconds"
- Example: "Verify the canary cohort sees the new UI while the baseline cohort sees the old"

### Section 4: Product mental model update

What assumptions does the PM currently hold that are no longer true? Write for a non-engineer.

- Example: "Publishing now supports 3 channels instead of 2. The new channel has a daily post limit of 100."
- Example: "Approve no longer triggers immediate publish — it queues for scheduled delivery."

This is the section most often skipped and most often regretted. If nothing changed from the PM's perspective, say so explicitly.

### Section 5: Rollout strategy

Based on the risk assessment, recommend a risk level and rollout plan:

| Risk level | When to use | Rollout |
|-----------|------------|---------|
| Low | Cosmetic, internal-only, no external side effects | Direct deploy |
| Medium | New feature, additive, no existing behavior changed | Feature flag → staging → 24h soak → production |
| High | Changes existing behavior, new external integration | Canary 5-10% → 4h monitor → 25% → 4h → 100% |
| Critical | Irreversible side effects, billing, data migration | Canary 1% → manual gate per step → 24h soak per tier |

For High and Critical, propose specific go/no-go criteria calibrated to this change (not generic thresholds).

---

## Step 3 — Present for review

Present the complete brief and ask:

- "Review the brief above. Is anything missing or wrong?"
- "Section 4 (PM mental model) — does this accurately describe what the PM needs to know?"
- "Section 5 (rollout) — is the risk level correct? Should the canary criteria be tighter or looser?"

Do NOT proceed until the user confirms the brief is complete.

---

## Step 4 — Add to the PR

Once approved, add the brief to the PR description or as a comment on the GitHub issue.

---

## Important Rules

- The brief protects against ORGANIZATIONAL risk, not technical risk. Tests and code review handle technical risk.
- Section 4 (mental model update) must be written for a non-engineer audience
- Reference the incident registry for the affected domains — past failures shape the risk assessment
- If no incidents exist for a domain, say "No prior incidents in this domain" — don't skip the check
- Mark uncertain items with ⚠️ VERIFY so the reviewer knows where human judgment is needed
