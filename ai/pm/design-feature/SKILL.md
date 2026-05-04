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

## Challenge Level — Ask First

Before Phase 1, ask:

> "What level of challenge would you like for this session?
>
> - **Rigorous** — I'll push back on vague answers and won't proceed without specifics. Best for high-stakes or complex features.
> - **Moderate** — I'll ask everything but accept reasonable answers. Best for most feature work.
> - **Light** — I'll ask only the key framing questions and move fast. Best for well-understood or low-risk features.
>
> Say **Rigorous**, **Moderate**, or **Light** to set the level."

Apply the chosen level throughout the session as defined in `ai/shared/challenge-stance.md` — Challenge Levels section. Default to **Moderate** if the PM doesn't specify.

---

## Progress Banners

At the start of every phase — before asking any questions or generating content — output the banner for that phase so the PM always knows where they are.

Format: `---` line, then `**Feature Design — Phase N / 7: Name**`, then the trail, then `---`.

| Phase | Banner trail |
|---|---|
| 1 | `▶ Discovery · ○ Journey · ○ Edge Cases · ○ Design · ○ Criteria · ○ Impact · ○ PRD` |
| 2 | `✅ Discovery · ▶ Journey · ○ Edge Cases · ○ Design · ○ Criteria · ○ Impact · ○ PRD` |
| 3 | `✅ Discovery · ✅ Journey · ▶ Edge Cases · ○ Design · ○ Criteria · ○ Impact · ○ PRD` |
| 4 | `✅ Discovery · ✅ Journey · ✅ Edge Cases · ▶ Design · ○ Criteria · ○ Impact · ○ PRD` |
| 5 | `✅ Discovery · ✅ Journey · ✅ Edge Cases · ✅ Design · ▶ Criteria · ○ Impact · ○ PRD` |
| 6 | `✅ Discovery · ✅ Journey · ✅ Edge Cases · ✅ Design · ✅ Criteria · ▶ Impact · ○ PRD` |
| 7 | `✅ Discovery · ✅ Journey · ✅ Edge Cases · ✅ Design · ✅ Criteria · ✅ Impact · ▶ PRD` |

Example (Phase 3):
```
---
**Feature Design — Phase 3 / 7: Edge Cases**
✅ Discovery · ✅ Journey · ▶ Edge Cases · ○ Design · ○ Criteria · ○ Impact · ○ PRD
---
```

---

## Phase 1 — Discovery

*→ Output Phase 1 progress banner.*

Ask the PM these questions one at a time. Wait for answers before moving on. Do not accept vague or aspirational answers — push for specifics.

1. **What is the delivery surface?** Web UI, mobile (iOS/Android/responsive web), API/backend only, agentic workflow (AI agent with no direct UI), internal/ops tool, or a combination? The answer gates which phases apply:
   - Backend-only or API → Phase 2 describes request/response flows, not screen steps; Phase 4 is skipped
   - Agentic → Phase 2 describes the agent's decision path and HITL gates; Phase 4 is replaced with tool/gate design
   - Web or mobile UI → all phases apply, including **Phase 4 UI prototyping with Claude Design**

   If the answer is Web or Mobile, say immediately: "Great — since this has a UI, we'll prototype it with Claude Design in Phase 4. Text-only requirements for UI features are incomplete; the prototype is part of the spec."

   *Follow-up probe (if the answer is vague or combo):* "Just to make sure I design the right flows — is there a primary surface, or are web and mobile truly equal-priority?"

2. **Who is this for?** Which persona from the PRD (`docs/01-product/prd.md` §3) is the primary user? Is there a secondary user?
3. **What evidence confirms this is a real problem?** What are users doing or saying that points to this gap? (Support tickets, user research, analytics, churn feedback.)

   *Follow-up probe (after any answer):* "Do you have a rough sense of how widespread this is — even a ballpark? If not, no worries — we can add it to the open items list."
   - If they give a data point: accept it, note it.
   - If they say "not sure" / "add to TODO": record it and proceed. See [TODO Deferral](../../shared/challenge-stance.md#todo-deferral).

4. **What problem does this solve?** What pain exists today? What is the user doing right now as a workaround?
5. **What happens if we don't build this?** Is this blocking users, causing churn, or just a nice-to-have? The answer determines priority.
6. **What does success look like?** What would tell you this feature worked?

   *Follow-up probe (after any answer):* "Do you have a rough current baseline — even approximate — or a hypothesis for how you'd validate this? If not, we can park it in open items."
   - Accept: rough metric, hypothesis + validation plan, or acknowledged gap + TODO.
   - Do not demand an exact number. See rule 3 in [challenge-stance.md](../../shared/challenge-stance.md).

7. **What's the simplest version?** If you had to ship this in 1 day, what would you cut? That's your MVP — and it's probably what you should validate first.
8. **What's explicitly out of scope?** What should this feature NOT do? Unstated non-goals become scope creep.
9. **Does this conflict with anything we've already built or committed to?** Query the PRD for conflicts now — prefer a graph query:
   ```
   /graphify query "existing requirements related to <feature-topic>"
   ```
   Fall back to reading `docs/01-product/prd.md` directly if the graph is unavailable. Flag any requirement this extends, contradicts, or duplicates.

**Behavior by level:**

| | Rigorous | Moderate | Light |
|---|---|---|---|
| Questions asked | All 9 | All 9 | 1 (delivery surface), 3 (evidence), 6 (success), 9 (conflicts) |
| Blockers | 1 (delivery surface) only — everything else can be deferred via TODO | 1 (delivery surface) and 4 (problem statement) only | 1 (delivery surface) only |
| Follow-up probes | Questions 1, 3, 6 — one gentle clarifying probe each | Questions 3 and 6 only | None |
| Vague answers | One follow-up probe; if still vague, offer TODO deferral | Offer TODO deferral | Note as gap, proceed |
| TODO deferral | Available for any question | Available for any question | Available for any question |

**TODO deferral is available at all levels.** Any time the PM says "not sure", "add to TODO", "come back to this", or similar — record the item and proceed. Do not block on it.

Summarize the answers back to the PM. Include an **Open Items** section listing any TODO-deferred questions:

> **Open items to revisit before this feature ships:**
> - [ ] [Question label]: [what's missing]

Get confirmation before proceeding to Phase 2.

**Create a draft GitHub issue immediately after Phase 1 is approved.** The feature needs to exist in the tracker before design work starts — the team should be able to see what's in progress:

```bash
gh issue create \
  --title "feat: <feature name>" \
  --body "## Status: Requirements in progress (Phase 1 / 7 complete)\n\n**Problem:** <problem statement from Q4>\n**Evidence:** <evidence from Q3>\n**Success looks like:** <from Q6>\n**Out of scope:** <from Q8>\n\n*PRD reference will be added at Phase 7. Acceptance criteria live in the PRD, not this issue.*" \
  --label "requirements"
```

Note the issue number — it will be updated with the full spec at Phase 7.

---

## Phase 2 — User Journey

*→ Output Phase 2 progress banner.*

Walk through the feature step by step. The format depends on the delivery surface confirmed in Phase 1.

**Web UI / Mobile:** Walk through screen by screen.
1. **Entry point:** How does the user discover or reach this feature? (navigation, link, notification, redirect)
2. **For each screen/step:** What does the user see? What actions can they take? What data is displayed and where does it come from? What happens when they complete the action?
3. **Happy path:** Walk through the complete flow end-to-end.
4. **Alternative paths:** What if the user goes back? Refreshes? Opens in a new tab?

**API / Backend only:** Walk through the contract.
1. **Trigger:** What calls this? (other service, scheduled job, user action upstream)
2. **Request shape:** What inputs are required? What is optional?
3. **Processing steps:** What does the system do? What can fail at each step?
4. **Response shape:** What is returned on success? On each failure mode?
5. **Side effects:** What else changes — database, events emitted, downstream calls?

**Agentic workflow:** Walk through the agent's decision path.
1. **Trigger:** What initiates the agent? (user prompt, event, schedule)
2. **Tool access:** What tools does the agent have? What can each tool do and what are its limits?
3. **Decision points:** Where does the agent choose between paths? What are the branch conditions?
4. **HITL gates:** At which points must a human review, correct, or approve before the agent continues? What happens if the human rejects?
5. **Output:** What does the agent produce? Who or what consumes it?
6. **Failure modes:** What happens if a tool call fails? If the agent is uncertain? If the human is unavailable?

Present the journey as a numbered flow. Get confirmation before proceeding.

---

## Phase 3 — Edge Cases & Error Handling

*→ Output Phase 3 progress banner.*

For each step in the journey, ask:

1. **What if the data is empty?** (no campaigns, no garments, no history) — what does the user see?
2. **What if the data is huge?** (1000 items, long text, large images) — pagination? truncation?
3. **What if the action fails?** (API error, timeout, rate limit) — what does the user see? Can they retry?
4. **What if the user is unauthorized?** (not logged in, wrong role, wrong brand)
5. **What if they double-click?** (duplicate submissions, idempotency)
6. **What if they're on mobile?** (responsive? or desktop-only for now?)

Present a table of edge cases with proposed handling. Get confirmation before proceeding.

---

## Phase 4 — Design Artifacts (conditional on delivery surface)

*→ Output Phase 4 progress banner.*

**Backend / API only:** Skip this phase. Acceptance criteria in Phase 5 will be contract-shaped (request/response format, error codes, edge cases). Proceed to Phase 5.

**Agentic workflow:** Skip visual prototyping. Instead, produce:
1. **Tool schema** — for each tool the agent uses: name, inputs, outputs, and failure modes.
2. **Decision flow** — a numbered sequence showing trigger → tool calls → decision branches → output. Include the conditions at each branch.
3. **HITL gate definitions** — for each gate: what the human sees, what they can approve/reject/correct, and what the agent does with each response.
4. **Guardrails** — what the agent must never do autonomously (irreversible actions, external sends, data deletion). These become hard HITL gates.

Present to the PM. Get explicit approval: "Agent design approved" before proceeding.

**Web UI / Mobile:** A visual reference is required before Phase 5. Text-only requirements for UI features are incomplete — the visual IS the spec for the frontend team. **Do not proceed to Phase 5 without one.**

Say to the PM:

> "Let's prototype this with Claude Design now — I'll generate screens for each step we mapped in Phase 2. If you'd rather start from something you already have (Figma file, tool screenshot, hand-drawn sketch), share it and I'll annotate it instead. Otherwise, let's go."

**Primary path — Claude Design (preferred):**
1. Generate screens for every journey step from Phase 2.
2. Include states for every screen: default, empty, loading, error, success.
3. Follow existing UI patterns — read `V1/web/components/` for the design system (shadcn/ui, Tailwind).
4. Show the flow — how screens connect.
5. Present and iterate until the PM is satisfied.

**Alternative — PM provides an existing visual (Figma export, tool screenshot, hand-drawn sketch):**
1. Read the image.
2. Annotate: which Phase 3 edge cases are handled vs missing; which screen states are covered vs absent.
3. Propose what the missing states should look like.
4. Iterate until the PM is satisfied.

Get explicit approval: "Design approved" before proceeding to Phase 5.

---

## Phase 5 — Acceptance Criteria

*→ Output Phase 5 progress banner.*

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

*→ Output Phase 6 progress banner.*

Before writing to the PRD, assess honestly. Surface risks and costs — do not make the feature sound easier than it is.

1. **Existing requirements affected** — prefer a graph query to find conflicts:
   ```
   /graphify query "requirements related to <feature-topic> or <domain>"
   ```
   Fall back to reading `docs/01-product/prd.md` directly if the graph is unavailable. Flag any requirement this feature changes, extends, or conflicts with. If a conflict exists, it must be resolved before writing to the PRD.
2. **Architecture implications** — read `docs/02-design/technical/hld/index.md`. Does this need a new HLD? New LLD? New ADR? Will this require changes to the system manifest?
3. **Dependencies** — does this feature depend on something not yet built? If yes, which features are blocked until that dependency is resolved?
4. **Effort estimate** — is this a 1-day, 1-week, or multi-week feature? Provide a range, not a single number. (Inform the PM; do not decide priority for them.)
5. **Scope check** — given the effort estimate, ask the PM: "Is the validated hypothesis from Phase 1 actually worth this effort? Could a smaller experiment test the same assumption first?"
6. **Technical debt** — will this feature create technical debt that slows future work? If yes, quantify it (e.g., "this adds a third auth path that will need consolidation in the next quarter").

Present the analysis including any concerns. Do not soften the effort estimate or risk assessment to make the feature more appealing. Get confirmation before proceeding.

---

## Phase 7 — Write to PRD

*→ Output Phase 7 progress banner.*

Only after ALL phases are approved:

1. **Draft the requirement** in `docs/01-product/prd.md` following the existing format:
   - FR ID (next available)
   - Description
   - Priority (ask the PM)
   - Acceptance criteria (from Phase 5)

2. **Draft the use case** if this is a new user journey:
   - Actor, preconditions, flow, expected outcome, error scenarios

3. **Save the UX design** — export the Claude Design prototype to `docs/02-design/ux/<feature-name>/` as reference for the architect.

4. **Update the GitHub issue** created in Phase 1 — update the title only, then add the PRD reference as a comment. Do NOT overwrite the body: the problem statement and rationale captured in Phase 1 are the permanent audit trail.
   ```bash
   gh issue edit <issue-number-from-phase-1> --title "feat: <short description>"
   gh issue comment <issue-number-from-phase-1> \
     --body "## ✅ Requirements Complete\n\nPRD: FR-<ID> — \`docs/01-product/prd.md\`\nDesign: \`docs/02-design/ux/<feature-name>/\`\n\nAcceptance criteria are in the PRD at FR-<ID>."
   ```

5. **Present the final output** to the PM:
   - PRD section (requirement + use case)
   - UX design reference
   - GitHub issue link
   - Impact analysis summary

