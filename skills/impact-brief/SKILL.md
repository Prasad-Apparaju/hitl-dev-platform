---
name: impact-brief
description: Generate a structured downstream impact brief and risk-rated rollout plan for a change that is ready for PR. Use after code and tests are complete, before creating the PR. Requires the HITL context file (.hitl/current-change.yaml) and an active GitHub issue.
argument-hint: "[PR number, branch name, or change description]"
disable-model-invocation: true
---

# Downstream Impact Brief

Generate a structured impact brief for a change that is ready for PR. The brief tells downstream stakeholders (PM, QA, Ops) what changed, what can break, and how to deploy safely.

**Input:** $ARGUMENTS (PR number, branch name, or description of the change)

If `$ARGUMENTS` is empty, check for unstaged changes via `git diff` and use those. If no changes found, ask: "What change should I assess? Provide a PR number or describe the change."

**Refusal rule:** If `.hitl/current-change.yaml` does not exist, stop: "No HITL context file found. Run `/apply-change` first to initialize the change context."

---

## Step 1 — Gather context

1. **Read `.hitl/current-change.yaml`** — get the change ID, tier, source artifacts, and manifest domain
2. **Read the diff** — `git diff main...HEAD` or the PR diff
3. **Identify affected domains** — prefer a graph query if the graph is available:
   ```
   /graphify query "domain: <domain-name> components and facade APIs"
   /graphify query "cross-component dependencies for <domain-name>"
   ```
   Fall back to reading `docs/system-manifest.yaml` directly if the graph is unavailable or stale.
4. **Find past incidents in the affected domains** — prefer a graph query:
   ```
   /graphify query "past incidents affecting domain: <domain-name>"
   /graphify query "incident failure modes in <domain-name>"
   ```
   Fall back to reading `docs/04-operations/incident-registry.yaml` directly if the graph is unavailable. If no incidents exist for this domain, say so explicitly — do not skip the check.
5. **Check test coverage for the affected areas** — prefer a graph query:
   ```
   /graphify query "test coverage for domain: <domain-name>"
   /graphify query "existing tests for <component-name>"
   ```
   Fall back to reading `docs/03-engineering/testing/test-registry.yaml` directly if the graph is unavailable.

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

## Step 4 — Update HITL context and PR

Once approved:
1. Update `.hitl/current-change.yaml` — add `rollout_plan` to `required_evidence` and mark `impact_brief: done`
2. Add the brief to the PR description or as a comment on the GitHub issue

---

## Important Rules

- The brief addresses ORGANIZATIONAL risk — downstream, deployment, and stakeholder impact; not technical risk.
- Section 4 (mental model update) must be written for a non-engineer audience
- Reference the incident registry for the affected domains — past failures shape the risk assessment
- If no incidents exist for a domain, say "No prior incidents in this domain" — don't skip the check
- Mark uncertain items with ⚠️ VERIFY so the reviewer knows where human judgment is needed
