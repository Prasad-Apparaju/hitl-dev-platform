---
name: pm-design-feature
description: Collaborate with PM to design a feature from a rough idea into a structured requirement with user stories, acceptance criteria, and scope boundaries.
argument-hint: "[rough feature idea]"
disable-model-invocation: true
---
# Design a Feature — PM Skill

**Input:** $ARGUMENTS (rough idea for a feature)

If `$ARGUMENTS` is empty, ask: "What feature are you thinking about? Describe the rough idea — we'll refine it together."

This is a guided, multi-phase process. Do NOT skip phases. Do NOT jump to writing the PRD until all phases are complete and the PM has approved each one.

---

## Phase 1 — Discovery

Ask the PM these questions one at a time. Wait for answers before moving on. Do not accept vague or aspirational answers — push for specifics.

1. **Who is this for?** Which persona from the PRD (`docs/01-product/prd.md` §3) is the primary user? Is there a secondary user?
2. **What evidence confirms this is a real problem?** Cite specific data: support tickets, user research sessions, usage analytics, churn feedback. "We think users want this" is not evidence — ask until a specific data point is provided.
3. **What problem does this solve?** What pain exists today? What is the user doing right now as a workaround?
4. **What happens if we don't build this?** Is this blocking users, causing churn, or just a nice-to-have? The answer determines priority.
5. **What does success look like?** Name a specific metric with its current measured value and a target. "Improve engagement" is not an answer. "Increase campaign creation rate from 2.3/week to 4/week, measured by analytics event X" is.
6. **What's the simplest version?** If you had to ship this in 1 day, what would you cut? That's your MVP — and it's probably what you should validate first.
7. **What's explicitly out of scope?** What should this feature NOT do? Unstated non-goals become scope creep.
8. **Does this conflict with anything we've already built or committed to?** Read `docs/01-product/prd.md` now. Flag any requirement this extends, contradicts, or duplicates.

Summarize the answers back to the PM. If any answer is vague, ask for the specific data point before summarizing. Get confirmation before proceeding.

---

## Phase 2 — User Journey

Walk through the feature step by step from the user's perspective.

1. **Entry point:** How does the user discover or reach this feature? (navigation, link, notification, redirect)
2. **For each screen/step:**
   - What does the user see?
   - What actions can they take?
   - What data is displayed? Where does it come from?
   - What happens when they complete the action?
3. **Happy path:** Walk through the complete flow end-to-end.
4. **Alternative paths:** What if the user goes back? Refreshes? Opens in a new tab?

Present the journey as a numbered flow. Get confirmation before proceeding.

---

## Phase 3 — Edge Cases & Error Handling

For each step in the journey, ask:

1. **What if the data is empty?** (no campaigns, no garments, no history) — what does the user see?
2. **What if the data is huge?** (1000 items, long text, large images) — pagination? truncation?
3. **What if the action fails?** (API error, timeout, rate limit) — what does the user see? Can they retry?
4. **What if the user is unauthorized?** (not logged in, wrong role, wrong brand)
5. **What if they double-click?** (duplicate submissions, idempotency)
6. **What if they're on mobile?** (responsive? or desktop-only for now?)

Present a table of edge cases with proposed handling. Get confirmation before proceeding.

---

## Phase 4 — UX Design

Use **Claude Design** to create a visual prototype.

1. **Generate screens** for each step in the user journey from Phase 2.
2. **Include states:**
   - Default state (data loaded normally)
   - Empty state (no data yet)
   - Loading state (waiting for response)
   - Error state (something went wrong)
   - Success state (action completed)
3. **Follow existing UI patterns** — read `V1/web/components/` for the current design system (shadcn/ui, Tailwind). Match the existing look and feel.
4. **Show the flow** — how screens connect to each other.

Present the prototype to the PM. Iterate until they're satisfied. Get explicit approval: "Design approved" before proceeding.

---

## Phase 5 — Acceptance Criteria

For each behavior in the approved design, write a testable acceptance criterion:

- **Format:** "Given [context], when [action], then [result]"
- **Cover:** happy path, each edge case from Phase 3, each error state from Phase 4
- **Be specific:** include numbers, limits, exact messages where possible

Example:
- "Given a brand with 0 campaigns, when the user opens the campaign list, then they see an empty state with the message 'No campaigns yet' and a 'Create Campaign' button"
- "Given the user clicks Publish twice within 1 second, then only one post is created (idempotent)"

Present the full list. Get confirmation before proceeding.

---

## Phase 6 — Impact Analysis

Before writing to the PRD, assess honestly. Surface risks and costs — do not make the feature sound easier than it is.

1. **Existing requirements affected** — read `docs/01-product/prd.md` carefully. Flag any requirement this feature changes, extends, or conflicts with. If a conflict exists, it must be resolved before writing to the PRD.
2. **Architecture implications** — read `docs/02-design/technical/hld/index.md`. Does this need a new HLD? New LLD? New ADR? Will this require changes to the system manifest?
3. **Dependencies** — does this feature depend on something not yet built? If yes, which features are blocked until that dependency is resolved?
4. **Effort estimate** — is this a 1-day, 1-week, or multi-week feature? Provide a range, not a single number. (Inform the PM; do not decide priority for them.)
5. **Scope check** — given the effort estimate, ask the PM: "Is the validated hypothesis from Phase 1 actually worth this effort? Could a smaller experiment test the same assumption first?"
6. **Technical debt** — will this feature create technical debt that slows future work? If yes, quantify it (e.g., "this adds a third auth path that will need consolidation in the next quarter").

Present the analysis including any concerns. Do not soften the effort estimate or risk assessment to make the feature more appealing. Get confirmation before proceeding.

---

## Phase 7 — Write to PRD

Only after ALL phases are approved:

1. **Draft the requirement** in `docs/01-product/prd.md` following the existing format:
   - FR ID (next available)
   - Description
   - Priority (ask the PM)
   - Acceptance criteria (from Phase 5)

2. **Draft the use case** if this is a new user journey:
   - Actor, preconditions, flow, expected outcome, error scenarios

3. **Save the UX design** — export the Claude Design prototype to `docs/02-design/ux/<feature-name>/` as reference for the architect.

4. **Create a GitHub issue:**
   ```bash
   gh issue create --title "feat: <short description>" --body "PRD: FR-<ID>\nDesign: docs/02-design/ux/<feature-name>/\n\nAcceptance criteria:\n<from Phase 5>"
   ```

5. **Present the final output** to the PM:
   - PRD section (requirement + use case)
   - UX design reference
   - GitHub issue link
   - Impact analysis summary

---

## Important Rules

- **Never skip phases.** The due diligence IS the value. A requirement without edge cases and a mockup is incomplete.
- **Challenge the PM.** If the feature sounds vague, ask "what does success look like?" If it sounds too big, ask "what's the simplest version?" If it duplicates something, say so. If you can't find the supporting data, ask for it before continuing.
- **Do not validate what the PM hasn't justified.** Enthusiasm is not a requirement. If the PM says "users will love this," ask what evidence supports that. Accept data; not optimism.
- **Use Claude Design for every feature that has a UI.** Text-only requirements for UI features are not acceptable.
- **The PM approves each phase before the next.** No phase is auto-approved.
- **Acceptance criteria must be testable.** "User-friendly" is not a criterion. "Empty state shows message X with button Y" is.
- **Read the existing PRD first.** Every feature exists in the context of what's already there. Don't propose something that contradicts or duplicates existing requirements without flagging it.
- **Surface the real cost.** Do not let a feature sound easy in Phase 6 if the architecture implies it isn't. The PM needs accurate information to prioritize.
