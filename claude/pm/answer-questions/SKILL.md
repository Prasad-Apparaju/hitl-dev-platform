---
name: pm-answer-questions
description: Answer product or business questions about the system using the PRD, HLDs, and existing docs. Use when a PM has questions about current capabilities, scope, or constraints.
argument-hint: "[question about the product or system]"
disable-model-invocation: true
---
# Answer Open Questions in the PRD

Walk through the Open Questions section and help the PM resolve them.

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
