# tools/

**Developer utilities** — run manually from the command line, not by CI or Claude.

| Tool | What it does |
|------|-------------|
| `generate-manifest/` | Auto-generates `docs/system-manifest.yaml` from a codebase via AST scanning. Run once during brownfield onboarding. |
| `render-pdf/` | Renders markdown files with Mermaid diagrams to PDF. |
| `read-risk.py` | Reads risk scores from the incident registry for a given domain. |
| `scripts/fix_mermaid_br_tags.py` | Mermaid compatibility fixer — also called by `/check-conventions`. |
| `scripts/init-project.sh` | Bootstraps a product repo with the HITL platform. |

CI enforcement scripts (`preflight/`, `manifest-drift/`) live in `ci/` alongside the workflows that invoke them.
