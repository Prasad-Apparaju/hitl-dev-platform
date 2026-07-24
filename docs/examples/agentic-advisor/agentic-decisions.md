# Agentic design decisions — support-assistant

*Generated from `.hitl/agentic-state.yaml` — do not edit (regenerate-and-diff).*

## Recommended workflow

- **Floor (shouldn't be skipped):** boundary, classify, evals, observability, privilege, reliability
- **Offered rungs:** deploy
- **Not needed:** memory

## Recommendations (a human authors the manifest; #10 validates)

- **classify** (floor) — proposed_kind + rationale per component (deep_agent structure where deep)  ·  hint: `domains[<agent>].kind (+ deep_agent{...}) — authored anew by the design role`
- **boundary** (floor) — inter-component contract + trust-leg controls (validate stochastic→deterministic; cost/authority into agents)  ·  hint: `interactions[].response.validation + callee facade_apis`
- **privilege** (floor) — least-privilege identity + per-use capabilities per agent  ·  hint: `domains[<agent>].identity + .uses`
- **reliability** (floor) — async idempotency/DLQ + lifecycle (human-gate/resumability) + kill-switch  ·  hint: `interactions[].async + domains[<agent>].lifecycle + top-level sagas`
- **observability** (floor) — tracing + PM eval-console  ·  hint: `top-level observability{tracing,eval_console} (#10 check_observability enforces)`
- **evals** (floor) — per-agent eval spec + one e2e flow  ·  hint: `domains[<agent>].evals + segments[e2e].evals`
- **deploy** (rung) — build-vs-buy decision (managed unless a reason to build) + portability diligence  ·  hint: `carried to the platform/ops track (FR-25) — authors no manifest field`

## Deploy decision (recorded, human-carried)

- recommend **managed**, chosen **managed** — carried to platform/ops (FR-25)
