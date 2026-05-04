# tools/

**Python enforcement tools** — run in CI or from the command line, not by Claude.

| Tool | What it does |
|------|-------------|
| `preflight/check_change.py` | Validates that every PR touching manifest-domain files has an approved decision packet. Run in CI via `ci/traceability-check.yml`. |
| `manifest-drift/` | Detects when source files have drifted outside their declared manifest domain boundaries. Run via `/check-conventions` or CI. |
| `generate-manifest/` | Auto-generates `docs/system-manifest.yaml` from a codebase via AST scanning. Run once during brownfield onboarding. |
| `render-pdf/` | Renders markdown files with Mermaid diagrams to PDF. |
| `read-risk.py` | Reads risk scores from the incident registry for a given domain. |

These tools run against your **product repo**, not this platform repo. The CI templates in `tools/ci/` wire them into GitHub Actions — copy those workflows to `.github/workflows/` in your product repo.

See `tools/scripts/fix_mermaid_br_tags.py` for the Mermaid compatibility fixer (separate from enforcement).

**Setup scripts** are in `tools/scripts/` — see `tools/scripts/init-project.sh`.
**CI workflow templates** are in `tools/ci/` — copy to `.github/workflows/` in your product repo.
