# Role Definitions

## 2. Role Definitions

Every role is a mix of producing artifacts, reviewing AI drafts, and making decisions. For well-understood, low-ambiguity work, AI drafts and humans review. For ambiguous design problems, debugging depth, security-sensitive decisions, or anything where the right answer requires judgment the AI cannot reliably exercise — humans lead and AI assists. The balance shifts by task, not by role.

> **On "review, don't write":** The goal is not for engineers to stop writing. The goal is that low-value mechanical production (boilerplate, obvious patterns, predictable transforms) does not consume the hours that should go to design, debugging, and judgment. Many experienced engineers find the shift uncomfortable at first; that discomfort is worth naming explicitly.

| Role | In Dev | After handoff to QA/Prod |
|------|--------|------------------------|
| **PM** | Defines requirements. Reviews AI-drafted PRDs. | Reviews demo. Accepts or requests changes. |
| **Architect** | Designs, reviews, gates PRs. Verifies traceability. | Available if QA/Ops need design clarification. |
| **Developer** | Owns everything in dev: code, tests, IaC, docs, QA-level testing, infra setup. Builds until the change is stable enough to hand off. | Pulled in by QA/Ops as needed for fixes. Retroactively applies Ops IaC refinements back to dev. |
| **QA** | Contributes test scenarios from incident registry to the dev test plan (non-blocking input). | Takes the handoff. Runs independent quality verification. Can block promotion if criteria not met. |
| **Ops** | Contributes canary criteria from incident registry (non-blocking input). | Takes the handoff. Refactors baseline IaC Dev provides. Monitors + promotes to production. Can block if system not stable. |
| **Claude** | Drafts docs, generates code + tests, reviews PRs, monitors metrics. Proposes, never decides. | Reports canary metrics. Available to QA/Ops for analysis. |

**The model:** Dev is empowered to do everything in dev — including QA-level testing and Ops-level IaC. Once the build is stable, Dev hands off with evidence (test registry results, impact brief, rollout plan). QA and Ops take it from there independently and pull Dev in as needed. Ops may refactor the IaC Dev provided; Dev retroactively applies those refinements back to the dev environment.

| Common practice | With this process |
|-----------|----------------|
| Write docs by hand | AI drafts most docs. You review, correct, approve — and write the parts that require judgment. |
| Start coding, figure it out as you go | Tell AI what you need. AI drafts the LLD. You review. Iterate — refine, add detail, challenge assumptions — until the doc reflects exactly what should happen. Only then does AI generate code from it. |
| Docs after the feature ships | Docs first. AI drafts them quickly. You spend time thinking and deciding, not formatting. |
| One developer owns a feature end-to-end | The *doc* owns the feature. Any developer (or AI session) can pick it up. |

### 2.1 The Dev Lead's Integration Verification

The lead's final verification step exists because AI code review, even in two rounds, catches *mechanical* issues but misses *intent* issues. Run the feature end-to-end and ask: "Does this actually do what the design said it would?" Check traceability: requirement, design, IaC, code, tests — is the chain unbroken? This catches the cases where each individual piece is correct but the whole does not match the intent.

### 2.2 Vertical Ownership

Every developer owns a full vertical slice — not "the frontend part" or "the backend part." If you are building the monitoring feature, you own the doc, the backend endpoint, the frontend component, the tests, and the bugs. When one person owns the full slice, there is no "it works on my side" across teams. AI helps you move fast across layers you are less familiar with; teammates help with review.

---

