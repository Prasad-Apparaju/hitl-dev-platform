# Compound Agentic System Surface design package

Design for EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10): a
first-class delivery surface for **compound agentic systems** — products that are a graph of
deterministic services, simple agents, and deep agents with sync and **async A2A** edges.
Governs the composition (topology, determinism boundary, A2A contracts, per-agent privilege and
tools, per-segment evals); ships no runtime, backbone, dashboard, or eval engine. Target release:
**2.2.0** (2.x line only).

| Doc | Content | Status |
|---|---|---|
| [00-requirements.md](00-requirements.md) | Problem, surface scope, goals/constraints/non-goals, requirements CR-1..CR-16, traceability, effort scope, version, two-stage Codex validation, success criteria, references | Draft, pending review |
| 01-design.md | HLD: topology model, determinism-boundary discipline, A2A-as-facade encoding, privilege/tool declarations + validators, eval discipline, decisions | To follow (#11) |

Related: `docs/design/platform-bootstrap/` (readiness register + tiered waivers + generated
derived views this reuses) and `docs/design/workflow-model/` (numberless catalog, `cond:` steps,
manifest `facade_apis`). Companion runnable reference product (optional, separate): epic
[#21](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/21).
