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

Step lists are seeded **from** `ai/shared/workflows.yaml` (the catalog) — including each step's
`phase` — not hand-copied, so the matrix tracks the catalog and tests only the renderers. The
current step's FULL name (the Phase-2 trail expands it) is seeded from
`ai/claude/dev-practices/workflow-steps.md` for the development workflow, and from the short catalog
label for the others.

## Running

```bash
ci/breadcrumb/run_matrix.sh        # run the matrix; exits non-zero if any case fails
ci/breadcrumb/run_matrix.sh -v     # verbose — also prints each rendered banner
```

Each case builds an isolated temp dir with its own `.hitl/` (and its own throwaway git repo where
the checked-out branch matters), seeds `.hitl/current-change.yaml`, runs the renderers, and asserts
the **Phase-2** output concretely (greps for the expected `▶ <full step name>`, the phase-ribbon
glyphs, and markers — not just exit 0). The temp dirs are removed on exit; no repo files are touched.

Requirements: `bash`, `git`, `jq` (used by the status line), and a working `python3`/`python`
(used only to generate fixtures from the catalog).

## Matrix

Per runtime workflow (`development`, `brownfield`, `migration`, `migration_review`, `prd`):

| Case | Asserts |
|------|---------|
| current at **first** step | trail non-empty; current shown numberless as `▶ <full name>`; phase ribbon shows the current phase `◐`; banner + statusline + library agree; no global `Step N / total` counter |
| current at **middle** step | same, plus the first (now-completed) phase shows `✓` in the ribbon |
| current at **last** step | same |

Plus the cross-cutting cases:

| Case | Asserts |
|------|---------|
| **19a substep** (development) | `hitl_current_n` returns `19a`; trail shows `▶ Architect Code Review` (full name, numberless) in banner, statusline, and library; ribbon shows `Verify ◐` |
| **skipped** step in the window | parser keeps `status: skipped` (now `n\|label\|status\|phase`); current still highlighted by full name; skipped neighbour renders numberless as `·<label>` (open glyph), **not** `✓` |
| **branch mismatch** | `expected_branch` ≠ checked-out branch → soft `⚠` warning in both renderers; trail still renders the full current name (warn, not crash) |
| **block-style YAML** (issue #15) | multi-line `- n:`/`key:`/`label:`/`status:`/`phase:` steps parse identically to flow-map style — both the trail **and** the phase ribbon match flow style |
| **back-compat: steps with no per-step `phase`** | a workflow block whose steps carry no `phase` → ribbon falls back to the lone `current_step.phase` (`<phase> ◐`, not the full ribbon); banner still renders the full trail without crashing |
| **pre-v2 / missing-workflow file** | banner degrades to the "step trail unavailable — run /hitl:dev-update" hint; exits 0; no error leak |
| **completely missing change file** | banner shows the intake gate; statusline shows "no active change"; exits 0 |
| **merged change is inactive** (issue #19) | a valid workflow block marked `status: merged` no longer satisfies the gate — banner forces intake, statusline shows "no active change", no stale trail renders |

The position cases, the substep, skip, mismatch, block, and back-compat cases also assert **no global
`Step N / total` counter leaks** (the Phase-2 trail is numberless and the denominator was replaced by
the phase ribbon). Every case also asserts **no renderer error text leaks** (no awk/jq/python stack
noise, `syntax error`, `command not found`, etc.).

Total: **238 assertions across 24 cases** (the position cases now cover the `docs` workflow too).

## Notes on renderer behaviour observed

- Phase 2: the trail is **numberless**. Neighbours render as `<glyph><short label>` (e.g. `✓Conv`,
  `·Rerun`) and the current step renders as `▶ <full name>` (expanded from `current_step.name`).
  There is no global `Step N / total` counter anywhere — the denominator was replaced by the
  **phase ribbon** (`hitl_render_ribbon`), e.g. `Requirements ✓  Design ✓  Build ◐  Verify ·`.
- `hitl_render_trail` maps only `done → ✓` and `current → ▶`; **every** other status — including
  `skipped` and `open` — renders as `·`. So a `skipped` step is visually indistinguishable from an
  `open` one in the trail today. That is the renderer's current contract, and the matrix asserts it
  (skipped shows as `·<label>`, never `✓<label>`).
- The phase ribbon is driven by each step's per-step `phase` + `status`: a phase shows `✓` when all
  its steps are done, `◐` when it holds the current step (or is partly done), `·` when untouched.
  A change file whose steps carry **no** per-step `phase` falls back to the lone `current_step.phase`
  (`<phase> ◐`) — exercised by the `dev/nophase` back-compat case.
- `hitl_render_trail` windows on the **last** step whose status is `current`, while
  `hitl_current_n` returns the **first**. With a well-formed change file (exactly one `current`
  step) these agree. A malformed file with two `current` steps would make the header (first) and the
  trail window (last) disagree — out of scope for this matrix, noted as a latent edge case.

## Findings

Running the matrix against the **current** (Phase-2) renderers: **238/238 pass, 0 renderer bugs
surfaced.** The renderers correctly handle every workflow, the 19a substep (full name, numberless),
skipped steps, branch mismatch, both YAML styles (trail **and** ribbon), the phase ribbon glyphs,
the no-per-step-phase back-compat fallback, and the zero-steps/missing-file degrade paths.
