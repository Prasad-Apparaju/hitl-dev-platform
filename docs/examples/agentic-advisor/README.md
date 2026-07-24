# Worked example — Agentic Design Advisor (`hitl:agentic-intake`)

A complete run of the advisor for a small multi-agent **support-assistant**, showing the four artifacts the
intake produces and how they feed manifest authoring. This is the front door to the
[compound-agentic surface](../../patterns/compound-agentic-systems.md); the advisor **recommends and records**,
a human authors the `system-manifest.yaml`, and the `ci/manifest-agentic` validators gate it.

## The scenario

Four components — `intake_agent` (classify), `account_service` (system of record), `resolution_agent` (draft a
resolution), `refund_service` (executes an **irreversible** refund) — with a sync classify edge, a sync
resolve edge, and an **async, side-effecting** refund edge. Risk answers: customer-facing, irreversible side
effects, PII, supervised autonomy. That risk profile is what drives the recommended floor.

## The flow (what `hitl:agentic-intake` does)

```
elicit ──▶ compose ──▶ record ──▶ hand off ──▶ (human authors manifest) ──▶ #10 validates
```

1. **Elicit** the shape + risks by walking the lens catalog adaptively → `agentic-state.yaml`.
2. **Compose** a right-sized recommendation: which lenses are report sections + a recommended floor.
3. **Record** the decisions and any skips → `agentic-decisions.md`.
4. **Render** the evolving map → `system-map.md`.
5. **Hand off** a neutral `agentic-design-handoff.yaml` — no manifest field, only `target_path_hint`s.

## The four files

| File | What it is |
|---|---|
| [`agentic-state.yaml`](agentic-state.yaml) | The canonical elicited state — components, edges, risk answers, deploy decision. The single source the other three are generated from. |
| [`agentic-decisions.md`](agentic-decisions.md) | The **recommendation report** — the recommended floor (`boundary, classify, evals, observability, privilege, reliability`), offered rungs (`deploy`), what's not needed (`memory`), and each recommendation with its manifest-path hint. |
| [`agentic-design-handoff.yaml`](agentic-design-handoff.yaml) | The **neutral handoff** a human authors the manifest from — components (`role` + `proposed_kind`), neutral connections (`transport`), and recommendations with `target_path_hint`s. **No manifest field, not even `kind`.** |
| [`system-map.md`](system-map.md) | The evolving system map — a terminal rendering + a Mermaid graph (getting / available / not-needed). |

## Reading the handoff → authoring the manifest

Each recommendation's `target_path_hint` says **where** it lands in the manifest you author next — e.g.
`privilege → domains[<agent>].identity + .uses`, `observability → observability{tracing, eval_console}`. The
advisor never writes those values; you do, in the design phase. Then:

```bash
python3 ci/manifest-agentic/check_manifest_agentic.py docs/system-manifest.yaml --tier 2
```

gates the manifest you authored. See the compound manifest worked reference at
[`docs/examples/compound-agentic/system-manifest.yaml`](../compound-agentic/system-manifest.yaml) for the
other end of this bridge.

## Regenerating

These four files are **generated from `agentic-state.yaml`** (regenerate-and-diff — don't hand-edit the three
derived files). A re-run recomputes them and reconciles human-owned decisions; the human confirms the diff
before write. The load-bearing property, asserted before every hand-off: the handoff **authors no manifest
field** (`records.handoff_authors_no_manifest_field(handoff) == set()`).
