# Worked example — First Pass (FR-29)

A Tier-2 refund feature (`GH-123`, billing domain) run in **First Pass** — the thin-whole-first,
skip-with-record mode. It shows the ledger, a starter artifact, the project roll-up, and how the change
validates and renders.

## What the team lightened

| step | criticality | disposition | why | record |
|------|-------------|-------------|-----|--------|
| ROI (4) | ceremony | **decline** | internal tool; ROI self-evident | recorded, never silent |
| Test plan (7) | standard | **starter** | thin v1 | [`test-plan.starter.md`](test-plan.starter.md), marked *needs-enhancement* |
| Deploy (28) | **floor** | decline | manual deploy for v1 | required `ack_by: ops-lead` (a floor skip) |

Everything else (impact, RED/GREEN, reviews) runs as normal. TDD was **not** skippable (it is `no_omit`).

## The files

- [`current-change.yaml`](current-change.yaml) — the change record with `first_pass: true` and the `skips[]` ledger.
- [`test-plan.starter.md`](test-plan.starter.md) — the honest-minimal starter (one happy-path case), marked *needs-enhancement*.
- [`skip-ledger.yaml`](skip-ledger.yaml) — the project roll-up (`.hitl/skip-ledger.yaml`) with domains/paths for cross-change recall.

## Validate it

```bash
python3 ci/first-pass/check_skips.py docs/examples/first-pass/current-change.yaml \
    --rollup docs/examples/first-pass/skip-ledger.yaml
# → "First Pass skip ledger: clean." (exit 0)
```

The validator is fail-closed: drop the deploy `ack_by`, or set RED to `defer`, and it exits 2 with a
non-waivable blocker (`FLOOR_NO_ACK`, `NO_OMIT`).

## The breadcrumb shows the shape

```
… ✓Impact ⊘ROI ◐Tests ▶ Write Failing Test ⊘Deploy …
```

`⊘` = skipped (defer/decline), `◐` = starter (needs-enhancement) — visually distinct from open (`·`), so
the trail *is* the First Pass shape at a glance (CR-16). When the deferred/started work later lands, its
glyph flips to `✓`.

## What comes next (iteration)

The `test_plan` starter's fast-follow is to *enhance* it (edge cases). The `roi` decline is a deliberate
choice. Both are in the roll-up, so a later change touching `billing` will see them resurfaced — politely.
