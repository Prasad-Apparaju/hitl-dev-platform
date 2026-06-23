# Breadcrumb test matrix

Verifies that the HITL breadcrumb renderers show the correct status for every runtime workflow
and a representative set of step states. Implements the stated success criterion in
[`docs/design/workflow-model/00-requirements.md`](../../docs/design/workflow-model/00-requirements.md) §6
and [`02-rollout.md`](../../docs/design/workflow-model/02-rollout.md) §6:

> Every workflow is verified to actually run end to end, and the breadcrumb shows the correct
> status — proven by **exercising the renderers**, not by reading the catalog.

## What it exercises

The three real artifacts, unmodified:

- `ai/claude/hooks/_steps.sh` — the dependency-free awk parser/renderer library
- `ai/claude/hooks/welcome.sh` — the `UserPromptSubmit` banner
- `ai/claude/hooks/statusline-hitl.sh` — the status line (reads JSON on stdin)

Step lists are seeded **from** `ai/shared/workflows.yaml` (the catalog), not hand-copied, so the
matrix tracks the catalog and tests only the renderers.

## Running

```bash
ci/breadcrumb/run_matrix.sh        # run the matrix; exits non-zero if any case fails
ci/breadcrumb/run_matrix.sh -v     # verbose — also prints each rendered banner
```

Each case builds an isolated temp dir with its own `.hitl/` (and its own throwaway git repo where
the checked-out branch matters), seeds `.hitl/current-change.yaml`, runs the renderers, and asserts
the output concretely (greps for the expected `▶label`, denominator, and markers — not just exit 0).
The temp dirs are removed on exit; no repo files are touched.

Requirements: `bash`, `git`, `jq` (used by the status line), and a working `python3`/`python`
(used only to generate fixtures from the catalog).

## Matrix

Per runtime workflow (`development`, `brownfield`, `migration`, `migration_review`, `prd`):

| Case | Asserts |
|------|---------|
| current at **first** step | trail non-empty; `▶<first>.<label>`; correct denominator; banner + statusline + library agree |
| current at **middle** step | same |
| current at **last** step | same |

Plus the cross-cutting cases:

| Case | Asserts |
|------|---------|
| **19a substep** (development) | `hitl_current_n` returns `19a`; trail shows `▶19a.ArchRvw` in banner, statusline, and library |
| **skipped** step in the window | parser keeps `status: skipped`; current still highlighted; skipped step renders as `·` (open glyph), **not** `✓` |
| **branch mismatch** | `expected_branch` ≠ checked-out branch → soft `⚠` warning in both renderers; trail still renders (warn, not crash) |
| **block-style YAML** (issue #15) | multi-line `- n:`/`key:`/`label:`/`status:` steps parse identically to flow-map style |
| **pre-v2 / missing-workflow file** | banner degrades to the "step trail unavailable — run /hitl:dev-update" hint; exits 0; no error leak |
| **completely missing change file** | banner shows the intake gate; statusline shows "no active change"; exits 0 |

Every case also asserts **no renderer error text leaks** (no awk/jq/python stack noise,
`syntax error`, `command not found`, etc.).

Total: **136 assertions across 21 cases.**

## Notes on renderer behaviour observed

- `hitl_render_trail` maps only `done → ✓` and `current → ▶`; **every** other status — including
  `skipped` and `open` — renders as `·`. So a `skipped` step is visually indistinguishable from an
  `open` one in the trail today. That is the renderer's current contract, and the matrix asserts it
  (skipped shows as `·`, never `✓`). If Phase 2 wants a distinct skipped glyph (e.g. `⊘`), that is a
  renderer change, and this test's `dev/skip` assertion is the place to update.
- `hitl_render_trail` windows on the **last** step whose status is `current`, while
  `hitl_current_n` returns the **first**. With a well-formed change file (exactly one `current`
  step) these agree. A malformed file with two `current` steps would make the header (first) and the
  trail window (last) disagree — out of scope for this matrix, noted as a latent edge case.

## Findings

Running the matrix against the **current** renderers: **136/136 pass, 0 renderer bugs surfaced.**
The renderers correctly handle every workflow, the 19a substep, skipped steps, branch mismatch,
both YAML styles, and the zero-steps/missing-file degrade paths.
