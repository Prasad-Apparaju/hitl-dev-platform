# Platform Bootstrap design package

Design for plugin issue #21: codify the bridge from "onboarded" to "ready for customer
delivery" (three entry points: brownfield / greenfield / migration).

| Doc | Content | Status |
|---|---|---|
| [00-requirements.md](00-requirements.md) | Problem, verified audit of the shipped surface, layer model, goals/constraints/non-goals, success criteria | Draft |
| [01-design.md](01-design.md) | Readiness register + generated roadmap, `platform` workflow catalog encoding, entry-point derivations, enforcement, open decisions D1-D6 | Draft, decisions open |

Related: `docs/design/workflow-model/` (the 2.0 mechanisms this reuses: `cond:` steps,
tiered waivers, required evidence, numberless catalog).
