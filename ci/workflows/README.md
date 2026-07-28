# ci/workflows/

**GitHub Actions workflow templates** — copy to `.github/workflows/` in your product repo.

These are not active for this platform repo. Run `tools/scripts/init-project.sh` to bootstrap a product repo — it copies these workflows and the supporting scripts in `ci/preflight/` and `ci/manifest-drift/`.

| File | What it does |
|------|-------------|
| `traceability-check.yml` | Runs `ci/preflight/check_change.py` on every PR — blocks merge if manifest-domain files changed without a decision packet |
| `convention-check.yml` | Runs semgrep with `.semgrep/` rules + manifest drift check — fails the build on violations |
| `first-pass-check.yml` | Runs `ci/first-pass/check_skips.py` on `.hitl/current-change.yaml` — fails the build on a non-waivable First Pass finding (silent skip, unauthorized floor skip, TDD omission, malformed ledger) |
| `deploy-with-gates.yml.example` | Example deployment workflow with canary gates — rename to `.yml` and adapt to your deploy target |
