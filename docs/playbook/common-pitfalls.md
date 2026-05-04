# Common Pitfalls

## 6. Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **Shipping without issues** | Code works, tests pass, but there is zero traceability. No link from requirements to design to code. When someone later asks "why does this integration use this retry strategy?", the answer is buried in a chat transcript. | Add a preflight check that blocks code generation if no issue is linked. GitHub issue first, always (step 1). |
| **Skipping the training plan** | Architectural decisions around new techniques (e.g., Thompson sampling, bandit routing) ship without training materials. A developer encountering the new pattern for the first time has to reverse-engineer it from code. | Use the conditional training plan stub (step 8). The trigger list is explicit. |
| **Using the full process for trivial changes** | A one-line config change goes through 20 steps. The overhead exceeds the value. | Use the light path decision table below. |
| **Using the full process for cross-cutting changes** | A cross-cutting change (new convention, framework upgrade, security patch) is treated as a single pipeline. But it has n-domain impact, and the pipeline's single Design PR does not adequately capture the review burden. | The hierarchical knowledge architecture helps (the architect decomposes across domains), but the human review bottleneck at the integration verification step does not scale. If the lead has to verify integration across 8 domains in one PR, something will get missed. Break cross-cutting changes into domain-scoped PRs. |

### 6.1 Process Tiers by Change Type

Not every change needs the full workflow. Use this table to decide the right process weight. **The full 31-step workflow is for Tier 3.** Most routine work is Tier 1 or Tier 2.

| Tier | Change type | Required artifacts | Required human gates | Overhead |
|------|-------------|-------------------|---------------------|----------|
| **0 — Trivial** | Typo, config value, log message | Linked issue or task | Standard PR review | Minutes |
| **1 — Bug fix** | Regression fix, minor behavioral correction | Issue + regression test first + risk note | PR review | 30-60 min |
| **2 — Normal feature** | Bounded, well-understood change within one domain | Issue + LLD update + test plan + impact brief | Design review + PR review | Hours to 1-2 days |
| **3 — Non-trivial / cross-domain** | Migrations, cross-domain changes, AI/agentic systems, security, data model changes | Full workflow: HLD/LLD + ADR + test plan + downstream impact brief + rollout plan | Design PR + two-round code review + integration verify | Days to weeks |
| **4 — Incident / P0** | Active production problem | Fix first + incident registry entry + full docs within 48 hours | Senior sign-off on fix + post-mortem | Immediate fix, deferred docs |

When in doubt, use the heavier tier. "Trivial" is a judgment call — sometimes what looks trivial has cross-domain or architectural implications that surface later. If you find yourself writing more than a few lines or touching more than one domain, move up a tier.

### 6.2 Architect Capacity and Delegation

The architect/lead is a bottleneck by design — they are the quality gate. But the bottleneck must scale with team size and handle unavailability gracefully.

**Scaling by team size:**

- **Teams of 3-5:** One architect can handle all gates (design approval, code review, integration verification).
- **Teams of 6-10:** Architect delegates code review Round 1 to senior engineers, retains design approval and integration verification.
- **Teams of 10+:** Consider splitting into domain leads, each owning their manifest domain's gates. The architect retains cross-domain design approval.

**When the architect is unavailable:**

| Gate | Substitute | Constraint |
|---|---|---|
| **Design approval** | Technical advisor (or most senior engineer if advisor unavailable) | Must have context on the affected domain |
| **Code review Round 1** | Any team member can perform Round 1 | Round 2 waits for architect return (max 24h) |
| **Integration verification** | Most experienced engineer on the affected domain | Documents any judgment calls for architect post-review |
| **Emergency (P0)** | Any senior engineer can approve | Architect reviews post-merge within 48h |

Gates should not block progress for more than 24 hours. When a substitute approves, the decision is documented and the architect reviews within the specified window.

See [ai/templates/team-responsibilities-template.md](../../ai/templates/team-responsibilities-template.md) for the full delegation framework.

### 6.3 Evidence Taxonomy

The claims in this repo have different levels of support. They are labeled here to avoid overstating certainty.

| Status | Meaning |
|--------|---------|
| **Measured** | Quantified outcome from at least one real project |
| **Observed** | Directional pattern seen in practice, not formally measured |
| **Hypothesis** | Reasonable expectation based on mechanism, not yet validated |
| **Open question** | Genuinely unknown; research or case studies needed |

Selected claims and their status:

| Claim | Status |
|-------|--------|
| AI-generated code drifts across sessions without shared conventions | Observed — consistent pattern in pilot projects |
| The manifest reduces hallucinated cross-domain dependencies | Observed — fewer cross-domain violations after manifest adoption |
| Documentation-first reduces mid-build rework | Observed — fewer design-level rewrites after the design PR gate was introduced |
| The baseline sprint produces an accurate-enough starting point | Observed — initial accuracy varies widely; 70% is a rough midpoint, not a floor |
| Two-round code review saves time vs. one thorough review | Open question — directional intuition, no measurement |
| The process improves lead time or defect escape rate | Open question — anecdotally positive, not formally measured |
| "Days rather than sprints" for a bounded feature | Hypothesis — depends heavily on LLD precision and team familiarity with the workflow |
| One architect can baseline any brownfield system in one week | Hypothesis — feasible for small-to-medium systems; larger systems take longer |

See [evidence.md](evidence.md) for a fuller breakdown.

### 6.4 Open Questions

- **Exploratory work**: How to handle genuinely exploratory work where the design emerges from the code. The design-first approach has clear value, but some tasks require building before knowing what to build.
- **Developer identity**: How to onboard developers who are uncomfortable with the shift away from writing as primary output. Some engineers derive identity from writing code; the process should acknowledge this explicitly.
- **Manifest accuracy**: How to keep the manifest accurate as the system evolves fast. The generator script helps, but human-authored blurbs (mutation descriptions, preconditions, the "IRREVERSIBLE" annotation on side effects) require judgment that cannot be automated yet.
- **Two-round review ROI**: Whether the two-round code review actually saves time compared to a single thorough review is an open question without data.
- **Measurement**: How to quantify the process's impact on lead time, defect rates, and onboarding speed. Without measurement, the strongest claims remain hypotheses.

---

