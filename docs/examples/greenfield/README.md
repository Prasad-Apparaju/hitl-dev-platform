# Greenfield Starter

Minimal setup to adopt the HITL AI-Driven Development process on a new project.

## Setup (15 minutes)

1. **Install the plugin** (preferred) or copy skills manually:
   - **Plugin install (recommended):** add the hitl-dev-platform repo as a Claude Code plugin — skills, agents, hooks, and commands are auto-discovered.
   - **Manual copy:** copy skills into your repo:
   ```bash
   cp -r ../../ai/ .claude/ai/
   ```

2. **Edit `CLAUDE.md`** — replace the sample conventions with your project's actual rules

3. **Edit `docs/system-manifest.yaml`** — replace the sample domain with your real codebase structure

4. **Edit `convention-checks.yaml`** — replace the sample checks with your project-specific rules

5. **Copy CI actions** to your repo:
   ```bash
   cp ../../ci/*.yml .github/workflows/
   ```

## What you get

- Every AI coding session follows the same workflow automatically
- The system manifest scopes AI context per domain (no "reads too much" hallucinations) — see `docs/system-manifest.yaml` for a realistic 3-domain example
- Convention checks run on every PR via CI
- Issue template includes ROI estimation + downstream impact brief
- Training plan requirement for new capabilities — see `docs/03-engineering/training/agent-architecture-example.md` for a worked example
- 15 templates for common artifacts (test strategy, security audit, best practices, cost analysis, performance, migration mappings, decision catalog, and more)
- Architectural patterns for agentic systems (failure mode taxonomy, idempotency keys)

6. **PR template** is already in place at `.github/PULL_REQUEST_TEMPLATE.md` — it enforces traceability on every pull request (linked issue, manifest domains, design docs, test plan, rollout plan, impact brief)

7. **Decision packets** go in `docs/decisions/issue-NNN.yaml` — Claude generates one per change before writing code. The template is at `../../templates/decision-packet-template.yaml`

## Next steps

- Read [../../docs/playbook/adoption-guide.md](../../docs/playbook/adoption-guide.md) for the full brownfield adoption guide
- Read [../../docs/playbook/process-overview.md](../../docs/playbook/process-overview.md) for the workflow details
- Copy [../../templates/issue-template.md](../../templates/issue-template.md) to `.github/ISSUE_TEMPLATE/`
