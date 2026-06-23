# tools/workflow-catalog/

Phase 1 of the workflow-model redesign (see
[docs/design/workflow-model/](../../docs/design/workflow-model/)): the **numberless catalog** plus the
generator that derives positional numbers from it.

## Why

Today `ai/shared/workflows.yaml` stores a hand-maintained `n` per step, so inserting or reordering a
step renumbers everything downstream and every reference goes stale. Here, identity is the stable
`key`; numbers are **derived from position** by `derive.py` and live only at the display layer.

## Files

| File | What |
|---|---|
| `catalog.yaml` | The numberless source of truth: the shared delivery `spine` (with conditional steps flagged `cond:`) and the own-spine `workflows` (establishment + review). No `n`, no `total`. |
| `derive.py` | Derives `n` / `total` / `phase.step`; verifies, prints an overview, or emits numbered steps. |
| `test_derive.py` | Unit tests for the numbering logic. |

## Use

```bash
python3 tools/workflow-catalog/derive.py verify     # derived numbers reproduce the runtime catalog?
python3 tools/workflow-catalog/derive.py overview   # markdown overview of every workflow
python3 tools/workflow-catalog/derive.py numbered spine
pytest tools/workflow-catalog/test_derive.py
```

## The verify contract (why this is safe to land now)

`derive.py verify` checks that the numberless catalog, once numbered, **matches the current runtime
`ai/shared/workflows.yaml`** on `n` / `key` / `label` / `phase` / `total` for every workflow
(`spine`→`development`, `greenfield`→`prd`, and the rest by name). A clean verify proves the eventual
cutover (Phase 2: make the runtime read derived numbers) is **lossless**. Until then this is a
**parallel artifact** — nothing at runtime reads it, so Phase 1 carries zero runtime risk.

## Not yet here (next slices)

- Profile/tag resolution (Feature/Fix/Tech Change/Upgrade/Security selecting spine steps + tags tuning
  required-evidence). The `cond:` flags and the conditional spine slots are present; the resolution
  engine and per-profile required-evidence are the next slice.
- The runtime cutover (seed/parser read derived numbers) — Phase 2.
