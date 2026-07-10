---
description: Answer product or business questions about the system using the PRD, HLDs, and existing docs. Use when a PM has questions about current capabilities, scope, or constraints.
argument-hint: "[question about the product or system]"
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

# Answer Open Questions in the PRD

Walk through the Open Questions section and help the PM resolve them.

**Graphify pre-flight:** Before the first step, run:
```bash
[ -f graphify-out/graph.json ] && echo "Graphify: available" || echo "Graphify: unavailable"
```
State the result once — "✅ Graphify available, using graph queries" or "⚠️ Graphify unavailable — using direct doc reads throughout." Apply that result for every step; do not rediscover availability mid-task.

---

## Steps

1. **Get the Open Questions section** — prefer a graph query if available:
   ```
   /graphify query "open questions from PRD with owner and status"
   ```
   Fall back to reading Section 10 of `docs/01-product/prd.md` directly if the graph is unavailable or stale.

2. **Present each open question** one at a time:
   ```
   Question #N: <question text>
   Owner: <who should answer>
   Status: Open

   What's your answer? (or "skip" to move to the next one)
   ```

3. **For each answer the PM provides:**
   - Draft the resolution text
   - Show it to the PM for confirmation
   - On approval, update the PRD: change Status from "Open" to "Resolved" and add the answer

4. **If the PM doesn't know the answer**, suggest:
   - Who to ask (based on the Owner column)
   - What information is needed to answer it
   - Whether the question blocks any current work

5. **After all questions are reviewed**, summarize:
   - N questions resolved this session
   - N questions still open
   - Which open questions block active development

## Important Rules

- Go through questions one at a time — don't dump all at once
- The PM's answer is final — don't argue with product decisions
- If an answer contradicts an existing requirement, flag it but accept the PM's direction
