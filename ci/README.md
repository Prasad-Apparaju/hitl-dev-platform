# ci/

**Copyable CI workflow templates** — for GitHub Actions in your product repo.

These are **not active** for this platform repo. Copy them to `.github/workflows/` in your product repo after running `scripts/init-project.sh`.

| File | What it does |
|------|-------------|
| `traceability-check.yml` | Runs `tools/preflight/check_change.py` on every PR — blocks merge if manifest-domain files changed without a decision packet |
| `convention-check.yml` | Runs semgrep with `.semgrep/` rules — fails the build on convention violations |
| `deploy-with-gates.yml.example` | Example deployment workflow with canary gates and go/no-go criteria — rename to `.yml` and adapt to your deploy target |
