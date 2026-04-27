# Design a Feature — PM Skill

**Input:** $ARGUMENTS (rough idea for a feature)

If `$ARGUMENTS` is empty, ask: "What feature are you thinking about? Describe the rough idea — we'll refine it together."

This is a guided, multi-phase process. Do NOT skip phases. Do NOT jump to writing the PRD until all phases are complete and the PM has approved each one.

---

## Phase 1 — Discovery

Ask the PM these questions one at a time. Wait for answers before moving on.

1. **Who is this for?** Which persona from the PRD (`docs/01-product/prd.md` §3) is the primary user? Is there a secondary user?
2. **What problem does this solve?** What pain exists today? What happens if we don't build this?
3. **What does success look like?** How would you measure whether this feature worked? (metric, behavior change, user feedback)
4. **What's the simplest version?** If you had to ship this in 1 day, what would you cut? That's your MVP.
5. **What's explicitly out of scope?** What should this feature NOT do?

Summarize the answers back to the PM. Get confirmation before proceeding.

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

Before writing to the PRD, assess:

1. **Existing requirements affected** — read `docs/01-product/prd.md` and flag any requirements this feature changes, extends, or conflicts with.
2. **Architecture implications** — read `docs/02-design/technical/hld/index.md`. Does this need a new HLD? New LLD? New ADR?
3. **Dependencies** — does this feature depend on something not yet built? Or does something else depend on this?
4. **Effort estimate** — is this a 1-day, 1-week, or multi-week feature? (inform the PM, don't decide priority for them)

Present the analysis. Get confirmation before proceeding.

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
- **Challenge the PM.** If the feature sounds vague, ask "what does success look like?" If it sounds too big, ask "what's the simplest version?" If it duplicates something, say so.
- **Use Claude Design for every feature that has a UI.** Text-only requirements for UI features are not acceptable.
- **The PM approves each phase before the next.** No phase is auto-approved.
- **Acceptance criteria must be testable.** "User-friendly" is not a criterion. "Empty state shows message X with button Y" is.
- **Read the existing PRD first.** Every feature exists in the context of what's already there. Don't propose something that contradicts or duplicates existing requirements without flagging it.
