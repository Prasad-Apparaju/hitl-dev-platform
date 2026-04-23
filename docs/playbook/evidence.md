# What We Have Observed So Far

This page separates what we know from what we believe. Claims in the README and playbook are labeled with one of four statuses.

## Evidence taxonomy

| Status | Meaning |
|--------|---------|
| **Measured** | Quantified outcome from at least one real project, with a baseline and comparison |
| **Observed** | Directional pattern seen in practice across multiple projects, not formally measured |
| **Hypothesis** | Reasonable expectation based on mechanism; not yet validated in practice |
| **Open question** | Genuinely unknown; would benefit from structured case studies or measurement |

---

## Process claims

### Documentation-first reduces mid-build rework

**Status: Observed**

In projects that adopted the design PR gate, design-level rewrites after coding started dropped noticeably. The mechanism is clear: if the team catches a design problem in a document review, they fix a paragraph; if they catch it after implementation, they fix code, tests, and sometimes the design of adjacent systems.

Not measured formally. "Fewer rewrites" is directional; we do not have before/after sprint velocity numbers.

### The manifest reduces hallucinated cross-domain dependencies

**Status: Observed**

After teams adopted the system manifest and domain boundaries, AI-generated code produced fewer unexpected cross-domain imports and fewer violations of interface contracts. Specialist agents that read only their domain's facade context made fewer changes outside their scope.

Not measured against a control group. Could partially reflect increased team discipline rather than the manifest itself.

### Convention drift stops when CLAUDE.md is shared

**Status: Observed**

Projects without shared AI rules saw consistent naming, error handling, and structural inconsistencies across developers. Projects with shared CLAUDE.md saw faster convergence and fewer convention-related code review comments.

### Initial baseline accuracy is partial

**Status: Observed**

AI-generated documentation baselines from reverse-engineering are incomplete and partially inaccurate. The 70% figure cited in the adoption guide is a rough midpoint; actual accuracy depends on system size, how well-documented the existing code is, and how much tribal knowledge the architect supplies. Some sections reach 90%; some start at 40%.

### The process compresses implementation time for well-scoped changes

**Status: Hypothesis**

When the LLD is written precisely and the AI session can reference it directly, code generation is fast and requires fewer correction cycles. The hypothesis is that this makes implementation faster net-of-process-overhead. We believe this is true for Tier 2-3 changes with good documentation; we do not have measured before/after timelines.

### Two-round code review saves time vs. one thorough review

**Status: Open question**

The intuition: Round 1 catches structural problems before test investment; Round 2 catches behavioral problems after tests exist. Finding structural problems post-tests means the tests are also wrong. In theory, two targeted reviews are more efficient than one broad review. In practice, we do not have data comparing total time spent.

---

## Brownfield claims

### An architect can baseline a medium system in one sprint

**Status: Hypothesis**

Plausible for small-to-medium systems with an architect who knows the codebase. Not validated on large legacy platforms, systems with extensive external integration surface, or codebases where most knowledge is tribal. The adoption guide now gives estimates by system size.

### Accuracy improves predictably through normal use

**Status: Hypothesis**

The mechanism is sound: every change that touches a domain also corrects the docs for that domain. Hot paths get corrected faster; cold paths stay inaccurate longer. Whether this produces the specific accuracy curve in the adoption guide is unknown — the curve is illustrative, not measured.

---

## Migration claims

### Vertical slice migration reduces risk vs. big-bang rewrites

**Status: Observed**

Migrating one endpoint or domain at a time allows incremental verification and contained rollback. Big-bang rewrites have a longer tail of subtle integration failures. This is widely observed in the industry, not just in our projects.

### Each slice takes days to weeks

**Status: Hypothesis**

Depends heavily on slice size, complexity, how many external dependencies the slice has, and team familiarity with the target architecture. "Days to weeks" is a wide range and the right answer is "it depends."

---

## What we want to measure next

- Lead time per change type (Tier 1-3) before and after process adoption
- Defect escape rate (bugs found in production vs. caught in review) before and after
- Onboarding time for new developers on process-documented repos vs. undocumented repos
- Time-in-review per PR before and after the design PR gate was introduced
- Two-round vs. one-round code review: time spent, defects caught, re-opens

If your team adopts this process and measures any of the above, we would like to hear from you.

---

## What we want to know but cannot answer yet

- **Does this work for TypeScript-first teams?** The enforcement tooling is Python-centric. Observations come from Python projects.
- **Does architect-as-bottleneck scale?** All observed projects had a strong architect or senior lead. We have not observed adoption attempts with weak architecture ownership.
- **Does the process reduce technical debt accumulation?** Plausible mechanism (conventions enforced, decisions documented), but no measurement.
- **Does it change how teams communicate?** The design room concept is intuitive but unvalidated. Whether shared AI-assisted design threads actually improve team communication quality is unknown.
