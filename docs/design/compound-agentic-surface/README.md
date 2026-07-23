# Compound Agentic System Surface — design package (the *how*)

Design (**how**) for EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10): a
first-class delivery surface for **compound agentic systems** — products that are a graph of
deterministic services, simple agents, and deep agents with sync and **async A2A** edges.

The **requirements (what)** live one layer up, under the product area:
[`docs/01-product/compound-agentic-surface/requirements.md`](../../01-product/compound-agentic-surface/requirements.md)
(elaborating PRD **FR-26**). This folder holds only the design.

| Doc | Content | Status |
|---|---|---|
| [01-design.md](01-design.md) | HLD (v3.2): manifest extensions, `interactions` edge model, determinism-boundary per leg, A2A-as-facade encoding, per-check activation, eval + saga discipline, decisions D1-D13 | Draft, core-lock applied, pending Codex round 5 |
| [02-adrs.md](02-adrs.md) | ADR-1..ADR-13 (v3.2) formalizing D1-D13 (alternatives + concrete cost) | Accepted, core-lock applied |
| [03-lld.md](03-lld.md) | LLD (v3.2): exact schema field types, scope grammar, needed-privilege algorithm, validator signatures + test matrix | Draft, pending Codex round 5 |
| [04-revision-plan.md](04-revision-plan.md) | Codex review response (rounds 1-4) + the round-4 **core scope lock** fix-map | Living |

The round-4 review drove a **core scope lock** ([`../agentic-core-scope.md`](../agentic-core-scope.md)):
eval coverage → per-agent + e2e (universal deferred); saga → declared-only + compensation-gap advisory
(required-when deferred); CR-6 sync reliability narrowed; delegated authority deferred. The
**Agentic Design Advisor** (FR-28, [`../agentic-design-advisor/`](../agentic-design-advisor/)) is this
surface's right-sizing front door.

Governs the composition; ships no runtime, backbone, dashboard, or eval engine. Target release:
**2.2.0** (2.x line only). Related: `docs/design/platform-bootstrap/`, `docs/design/workflow-model/`.
Companion runnable reference product (optional, separate): epic
[#21](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/21).
