---
description: Understand an existing feature's current behavior and collaborate with a PM to produce a structured enhancement request. Works for any feature — product capability, PRD requirement, skill, agent, service, or component. Use when you want to enhance something that already exists, not add something new.
argument-hint: "[feature name, requirement ID, or description of what you want to enhance]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

**If there are no product requirements yet:** if `docs/01-product/prd.md` is absent or lists no functional requirements (no `FR-` entries in §5), stop and output this, do not proceed:

```
No product requirements exist yet, so there is nothing here to work from.
Create the first requirement, then re-run this command:

  /hitl:pm-add-feature      capture a new requirement
  /hitl:pm-design-feature   design a user-facing feature
```

---

# Enhance an Existing Feature — PM Skill

**Input:** $ARGUMENTS (name, ID, or description of the feature to enhance)

If `$ARGUMENTS` is empty, ask: "What feature do you want to enhance? Give a name, requirement ID (e.g., FR-AUTH-2), or a description — e.g., 'the login flow', 'the QA reviewer agent', 'the test coverage report'."

**Graphify pre-flight:** Before Phase 1, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Challenge Level — Ask First

Before Phase 1, ask:

> "What level of challenge would you like?
> - **Rigorous** — I'll push back until I have specific answers. Nothing gets drafted without justification.
> - **Moderate** — I'll ask all questions and flag gaps, but won't block on every one.
> - **Light** — I'll note gaps but move quickly. Good for rough drafts."

Wait for the answer. Apply it throughout.

---

## Phase 1 — Find the Existing Feature

Search for artifacts related to `$ARGUMENTS`. Try all of the following in order and report what you find:

**1a. PRD requirement** — if a requirement ID was given (e.g., `FR-AUTH-2`), look it up directly:
```
/graphify query "requirement <ID> acceptance criteria current behavior"
```
or read `docs/01-product/prd.md` directly.

**1b. HLD / LLD** — look for design docs covering this feature:
```
/graphify query "HLD LLD <feature name> component behavior"
```
or scan `docs/02-design/technical/hld/` and `docs/02-design/technical/lld/`.

**1c. Implementation artifacts** — skills, agents, scripts, source files:
- For a skill: look for `SKILL.md` in `ai/claude/` subdirectories matching the name
- For an agent: look for `AGENT.md` in `ai/claude/agents/` matching the name
- For a service or component: use the system manifest to locate source paths
  ```
  /graphify query "domain <feature name> source path"
  ```
  or read `docs/system-manifest.yaml`.

**1d. GitHub issues** — look for open issues or past PRs related to this feature:
```bash
gh issue list --search "<feature name>" --state all --limit 10 2>/dev/null || echo "GitHub unavailable"
```

After searching, present a summary:

> **Found:**
> - PRD requirement: [ID + title, or "not found"]
> - HLD: [file + section, or "not found"]
> - LLD: [file + section, or "not found"]
> - Implementation: [file path, or "not found"]
> - Related issues: [list, or "none"]

If nothing is found, ask: "I couldn't find artifacts for that. Can you point me to the file, requirement ID, or describe more specifically what you mean?"

If multiple candidates are found, list them and ask the PM to confirm which one they mean before continuing.

---

## Phase 2 — Explain Current Behavior in Business Language

Read the artifacts found in Phase 1. Summarize what the feature **currently does** in plain, non-technical language — as a PM would describe it to a stakeholder. Do not quote code or YAML. Focus on:

- What the feature does and for whom
- What triggers it
- What the output or result is
- What it explicitly does not do (if stated in the docs)
- Any known constraints or limitations

Format:

> **What [feature name] does today:**
>
> [2–5 bullet points in business language]
>
> **Known boundaries:**
> - [What it explicitly does not do, or limitations from the docs]

Then ask: "Does this match your understanding of the current feature? Anything I'm missing or wrong about?"

Wait for confirmation before proceeding.

---

## Phase 3 — Understand the Enhancement Intent

Now interview the PM to understand what they want changed. Do not skip questions. At rigorous level, push back if answers are vague.

Ask these questions one group at a time — do not dump them all at once:

**Round 1 — The problem:**
> 1. "What's the gap or problem you're trying to solve? What's happening today that shouldn't be, or what's missing that should be there?"
> 2. "Who experiences this gap — which user, role, or team?"
> 3. "How often does it come up, and what's the impact when it does?"

Wait for answers. Then:

**Round 2 — The outcome:**
> 4. "What should users be able to do after this enhancement that they can't do today?"
> 5. "What does a successful outcome look like — how will you know this worked?"
> 6. "Is there anything about the current behavior that must stay exactly the same?"

Wait for answers. Then:

**Round 3 — Scope and constraints:**
> 7. "Any constraints — timeline, technical, compliance, budget?"
> 8. "Is this a standalone enhancement, or does it unblock something else?"

At **rigorous** level: push back on any answer that is vague or unmeasurable. Examples:
- "faster" → ask: "How much faster? What's the current time and the target?"
- "better UX" → ask: "What specifically is poor about the current UX? What would better look like?"
- "support more cases" → ask: "Which cases specifically? Can you give me 2–3 examples?"

At **moderate** level: flag vagueness but don't block progress.
At **light** level: note gaps inline and continue.

---

## Phase 4 — Draft the Enhancement Request

Synthesize the Phase 2 and 3 outputs into a structured enhancement request. Do not write this until Phase 3 is complete and answers are sufficient.

```markdown
## Enhancement Request: [Feature Name] — [One-Line Description]

**Requirement ID:** [existing ID, e.g., FR-AUTH-2] (enhancement) — or NEW if no existing ID
**Date:** [today's date]
**Requested by:** PM
**Priority:** [ask if not yet stated]
**Estimated tier:** [Tier 1 / Tier 2 / Tier 3 — based on scope; see ADR-0004]

---

### Current behavior

[2–4 sentences from Phase 2 summary — what exists today]

### Problem / gap

[1–3 sentences: what's wrong or missing, who's affected, how often]

### Proposed enhancement

[What should change — 2–5 bullet points, specific and measurable]

### What must not change

[Explicit list of behaviors that must be preserved]

### Acceptance criteria

- [ ] [Specific, testable criterion 1]
- [ ] [Specific, testable criterion 2]
- [ ] [Specific, testable criterion 3]
- [ ] Existing behavior not in scope is unchanged (regression gate)

### Out of scope

[What this enhancement explicitly does not address]

### Open questions

- [Any gap flagged during Phase 3 that still needs an answer]
```

After drafting, show it to the PM and ask:

> "Does this capture what you want? Anything to add, remove, or reword?"

Iterate until the PM approves.

---

## Phase 5 — Record and Hand Off

Once the PM approves the enhancement request:

**5a. Update the PRD** — if an existing requirement ID was found in Phase 1:
- Add the enhancement as a sub-requirement or append it to the existing requirement's acceptance criteria, clearly marked with today's date and "Enhancement:".
- Do not overwrite existing acceptance criteria — append.

If no PRD requirement exists for this feature, add a new requirement entry in the appropriate section of `docs/01-product/prd.md`.

**5b. Create a GitHub issue:**
```bash
gh issue create \
  --title "[Enhancement] <Feature Name>: <one-line description>" \
  --body "$(cat <<'EOF'
## Summary
<paste the enhancement request markdown here>

## Source
Generated via /hitl:pm-enhance-feature

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Show the issue URL.

**5c. Tell the PM what happens next:**

> **Next steps:**
> 1. Architect reviews scope and confirms tier (see ADR-0004)
> 2. If Tier 2+: run `/hitl:architect-design-feature` to produce HLD/LLD before any code is written
> 3. If Tier 1: run `/hitl:dev-practices` directly from the GitHub issue
> 4. Track progress with `/hitl:pm-review-progress`

---

## Never

- Do not draft the enhancement request before Phase 3 is complete
- Do not write code, HLD, or LLD — this skill produces a requirement, not a design
- Do not accept "make it better" or "improve it" as an acceptance criterion — push until it is measurable
- Do not mark done until the PM has explicitly approved the final draft
