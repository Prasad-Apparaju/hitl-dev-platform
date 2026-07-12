# ci/

**CI enforcement** — GitHub Actions workflows and the Python scripts they invoke.

Copy `workflows/*.yml` to `.github/workflows/` in your product repo. The enforcement scripts (`preflight/`, `manifest-drift/`) are copied to the same `ci/` path in your product repo by `tools/scripts/init-project.sh`.

| Path | What it does |
|------|-------------|
| `workflows/traceability-check.yml` | Blocks PR merge if manifest-domain files changed without a decision packet |
| `workflows/convention-check.yml` | Runs semgrep rules + manifest drift check on every PR |
| `workflows/deploy-with-gates.yml.example` | Example canary deployment workflow — rename and adapt |
| `preflight/check_change.py` | Called by `traceability-check.yml` — validates decision packets |
| `manifest-drift/` | Called by `convention-check.yml` — detects files drifting outside declared domains |
| `skill-lint/check_skills.py` | Lints every `SKILL.md` against the Agent Skills schema (Part A acceptance criteria); run on PRs touching `ai/claude/**` |
| `hooks/test_check_hitl_context.py` | Regression tests for the intake-gate hook's path handling (issue #20); run on PRs touching `ai/claude/hooks/**` |
