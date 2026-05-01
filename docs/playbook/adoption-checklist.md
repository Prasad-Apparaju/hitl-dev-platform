# Adoption Checklist

## 7. Adoption Checklist

Use this checklist when considering or implementing this process:

- [ ] **Docs discipline first.** If the team does not currently maintain design docs, do not jump to docs-first AI development. The transition is: (1) start writing docs at all, (2) make them precise enough to generate from, (3) start generating. Skipping to step 3 produces convention drift and hallucination.
- [ ] **Address the cultural barrier.** The tools work. The harder part is helping experienced developers find the right balance for each task — using AI drafting for low-ambiguity, high-volume work while leading directly on design problems, debugging, and security-sensitive decisions. The shift is by task risk and ambiguity, not by ideology. Engineers who feel their craft is being sidelined will disengage; framing this as "AI handles the mechanical parts so you can focus on the judgment parts" lands better than "your job is now review."
- [ ] **Start with one change.** Pick one non-trivial feature, try the doc-first flow, and see what happens. If the generated code is better than what would have been written by hand, the process sells itself. If it is not, either the docs were not precise enough or the feature is not a good fit for this approach.
- [ ] **Recognize that docs are the moat.** Every team has access to the same AI models. The competitive advantage is in the documentation that makes those models produce *your* system's conventions, *your* architecture's patterns, *your* domain's edge cases. A team with 55 well-maintained architectural decisions and 33 precise LLDs will outproduce a team with better AI tools but no docs.
- [ ] **Invest in evals early.** Quality scoring — even simple LLM-judge rubrics — gives you the feedback loop to improve. Without evals, you cannot tell whether AI output is getting better or worse over time, and you cannot compare the effect of process changes. Eval infrastructure is boring to build but transformative to have.
- [ ] **Accept that the process will evolve.** Steps will be added, reordered, and entire concepts introduced late. Treat the process as a living system, not a fixed standard.

> The goal is not to ship faster. The goal is to minimize the problems that come from AI-generated code — convention drift, untraceable decisions, hallucination — so the system evolves correctly. Speed is a side effect of correctness, not a goal in itself.

### Adoption Ladder

**Start here.** You do not need the full process on day one. The repo is designed to be adopted incrementally. Pick the level that matches where your team is right now; add layers as the team matures and you see value.

After 2 weeks at Level 1: every developer's AI assistant follows the same rules; the most common convention drift problem is solved.
After 2 weeks at Level 2: design decisions are captured before code is written; mid-build rework becomes rarer.
After 1 month at Level 3-4: the team has a traceable, enforceable process for non-trivial changes.

| Level | What you adopt | What you get | Effort |
|---|---|---|---|
| **1. Shared AI rules** | `CLAUDE.md` with coding standards + conventions | Every AI session follows the same rules. Convention drift stops. | 1 hour |
| **2. Docs-first for non-trivial changes** | HLD/LLD before code. ADRs for decisions. | Design is reviewed before code exists. Rework drops. | 1 day |
| **3. Decision packets + traceability** | Decision packet per change. PR template with checkboxes. Traceability CI. | Every PR traces to a reviewed decision. Nothing ships undocumented. | 1 day |
| **4. System manifest + domain facades** | Manifest with domains, files, facades, conventions. Manifest drift checker. | AI stays scoped. Cross-domain drift detected. New team members onboard from the manifest. | 1 week |
| **5. Full workflow** | Incident registry, test registry, rollout planning, ROI checks, deployment gates. | Past mistakes don't repeat. Deployments are risk-rated. Investments are measured. | 1-2 weeks |

**For teams not ready for Level 5:** Levels 1-3 are the minimum viable adoption. They give you shared conventions, docs-first design, and basic traceability — the three things that prevent the worst outcomes from AI-assisted development — without the full overhead of the 30-step workflow.

Each level is independently valuable. Level 1 alone eliminates the most common AI coding problem (every session invents its own conventions). Level 2 prevents the second most common problem (code that doesn't match what the team agreed). Levels 3-5 add enforcement and organizational safety.

---

