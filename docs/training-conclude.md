# /conclude Skill — Training Plan

> **Status:** Complete

After completing this plan, you will be able to use `/conclude` to turn a Slack design-room thread into documented GitHub artifacts (ADR, issue, HLD/LLD updates) following the team's development process.

**Audience:** Primary = dev team (use the skill daily). Secondary = PM team (understand what artifacts get produced).
**Estimated time:** 30 minutes total
**Prerequisites:**
- Familiarity with the team's ADR format (`templates/adr-template.md`)
- Slack MCP integration configured (for reading threads)
- Access to the project's `docs/system-manifest.yaml`

---

## Module 1: When to Use /conclude (10 min)

### Goal
Understand when `/conclude` applies and when it doesn't.

### Key Concepts

`/conclude` documents **decided** discussions — not open ones. The trigger is a team member recognizing that a thread has reached consensus. Common signals:
- "Decision: we're going with X"
- "Agreed — let's do Y"
- A thread where everyone stopped debating and the last message is an action item

**When NOT to use it:**
- Thread is still open (no decision yet)
- Decision was trivial (no ADR needed — e.g., "let's use tabs not spaces")
- Decision was already documented elsewhere

### Checkpoint
1. A thread has 15 messages debating two approaches. The last message says "Let's go with option A, it's simpler." Is this ready for `/conclude`? *(Yes — clear decision signal)*
2. A thread has 5 messages exploring an idea but ends with "let me think about this more." Is this ready? *(No — no decision reached)*

---

## Module 2: Running /conclude End-to-End (20 min)

### Goal
Run `/conclude` against a real or example thread and produce artifacts.

### Reading
| File | What to focus on |
|------|-----------------|
| `skills/conclude.md` | The 6 steps and the human gates at each step |
| `templates/adr-template.md` | The ADR structure — especially Context, Decision, Alternatives, ROI |
| `docs/system-manifest.yaml` (in your project) | How domains and facade APIs are listed — `/conclude` cross-references this |

### Hands-on Exercise

1. Open Claude Code in your project repo
2. Run: `/conclude [paste a Slack thread URL from #styleflow-design-room]`
3. Review the summary Claude presents — is the decision accurate?
4. Review the ADR draft — does the rationale match the thread?
5. Check that affected domains match what the manifest says
6. Approve or correct each artifact
7. Verify the PR was created and the Slack thread got a reply with links

### Checkpoint
1. What happens if Claude can't find a clear decision in the thread? *(It tells you and asks you to point to the decision message — it never infers)*
2. Why does the skill ask for ROI even if the thread didn't discuss it? *(Every decision has a cost; documenting expected return enables 30/90-day verification)*
3. Who gets listed as Deciders in the ADR? *(The thread participants — with a flag if a key role was missing)*

---

## Summary

| You now understand | Evidence |
|-------------------|----------|
| When to use `/conclude` | Module 1 checkpoint — decision signals vs. open threads |
| The 6-step flow with human gates | Module 2 exercise — ran it end-to-end |
| How it cross-references the manifest | Module 2 — verified affected domains |

## Next Steps
- Use `/conclude` on the next design thread that reaches a decision
- Review the generated ADRs after a week — are they accurate? Adjust the skill if patterns emerge.

## Related
- [Issue #2](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/2) — Implementation issue
- `skills/conclude.md` — The skill definition
- `templates/adr-template.md` — ADR format the skill generates
