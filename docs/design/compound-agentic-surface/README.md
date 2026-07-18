# Compound Agentic System Surface — design package (the *how*)

Design (**how**) for EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10): a
first-class delivery surface for **compound agentic systems** — products that are a graph of
deterministic services, simple agents, and deep agents with sync and **async A2A** edges.

The **requirements (what)** live one layer up, under the product area:
[`docs/01-product/compound-agentic-surface/requirements.md`](../../01-product/compound-agentic-surface/requirements.md)
(elaborating PRD **FR-26**). This folder holds only the design.

| Doc | Content | Status |
|---|---|---|
| 01-design.md | HLD: topology model, determinism-boundary discipline, A2A-as-facade encoding, privilege/tool declarations + validators, eval discipline, decisions | To follow (#11) |
| adr-*.md | Architecture decisions (framework-agnostic, governs-not-runtime, edge-typing) | To follow (#11) |

Governs the composition; ships no runtime, backbone, dashboard, or eval engine. Target release:
**2.2.0** (2.x line only). Related: `docs/design/platform-bootstrap/`, `docs/design/workflow-model/`.
Companion runnable reference product (optional, separate): epic
[#21](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/21).
