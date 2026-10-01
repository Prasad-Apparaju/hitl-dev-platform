# examples/

**Worked examples** — see the HITL process applied to specific project types.

| Example | What it shows |
|---------|--------------|
| `greenfield/` | A new project set up from scratch with `/hitl:dev-start-from-prd` — PRD, manifest, first decision packet, and initial slice |
| `agentic-advisor/` | A worked run of `hitl:agentic-intake` (the multi-agent front door, EPIC #35) — elicited state, recommendation report, neutral handoff, and system map. See its `README.md`. |
| `data-layer/` | A synthetic fulfilment app with exports, and the data layer `/hitl:dev-map-data-layer` builds from it (FR-31): sources, questions, evidence, per-entity slices and interpretations, the four files, a baseline scorecard. The validator and scorecard tests run on it. |
| `compound-agentic/` | A compound-agentic `system-manifest.yaml` (EPIC #10) that passes `ci/manifest-agentic` end-to-end — the manifest a human authors from the advisor handoff. Pattern: [`compound-agentic-systems.md`](../patterns/compound-agentic-systems.md). |

Examples are read-only reference material. They are not connected to any live system.
