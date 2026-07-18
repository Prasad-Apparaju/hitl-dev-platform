# Metrics Generation — design package (the *how*)

Design (**how**) for EPIC [#22](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/22):
derive framework-effectiveness metrics from HITL's durable artifacts, emit a machine-readable
metrics register + a rendered local report. Governs the derivation; ships no dashboard, DB, BI, or
phone-home.

The **requirements (what)** live one layer up, under the product area:
[`docs/01-product/metrics-generation/requirements.md`](../../01-product/metrics-generation/requirements.md)
(elaborating PRD **FR-27**). This folder holds only the design.

| Doc | Content | Status |
|---|---|---|
| 01-design.md | HLD: derivation model, metrics-register schema, report generator, evidence-class labeling, baseline capture, decisions | To follow (#23) |
| adr-*.md | Architecture decisions (governs-not-runtime, no phone-home, evidence-class enforcement) | To follow (#23) |

Target release: **2.3.0** (2.x line only). Reuses the token-cost/readiness-register and
generated-view precedents. Related: `docs/design/platform-bootstrap/`, `docs/design/compound-agentic-surface/`.
