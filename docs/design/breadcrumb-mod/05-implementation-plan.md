# Breadcrumb as a Mod: Implementation Plan

> Status: **draft v1 (2026-10-05)**. One slice, built on branch `issue/150-breadcrumb-mod`.

| Phase | What | Files | Proven by |
|---|---|---|---|
| A. Renderer | Mode reader, cache writer, plain hint; both callers write; welcome quiets in band mode | `ai/claude/hooks/_steps.sh`, `welcome.sh`, `statusline-hitl.sh` | Matrix case (test plan 1); the 271 existing assertions unchanged |
| B. Mod | `hooks.json`, `breadcrumb-band.js`, its tests | `ai/claude/hooks/` | `claude plugin test` (test plan 2) |
| C. Guard | Assembler and pytest; CI installs the CLI | `ci/breadcrumb-mod/`, `.github/workflows/tests.yml` | Test plan 3 |
| D. Wiring | Ignore line in three places; plugin build copies `*.js`; this repo's `.gitignore` | `init-project.sh`, `start-from-prd`, `dev-update`, plugin `build.sh`, `.gitignore` | Test plan 4 |
| E. Docs | CHANGELOG, getting-started, PRD row, requirements | as named | Doc checks |
| F. Gates | pytest, skill-lint, derive verify, matrix, plugin build | | All green |
| G. Review | One clean-context validation review of the branch, then merge to main | `.hitl/reviews/incoming/` | Verdict |
| H. Release | 2.18.0 by `docs/releasing.md`; the upgrade lens checks the band on a real session and the no-mod surfaces | | Owner's call |

A and B run in parallel (an agent builds B from the LLD; the renderer edits are by hand). C after
B. D and E alongside. F, G, H in order.
