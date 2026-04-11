# Greenfield Starter

Minimal setup to adopt the HITL AI-Driven Development process on a new project.

## Setup (15 minutes)

1. **Copy skills** to your repo so every developer's Claude Code gets the workflow:
   ```bash
   cp -r ../../skills/ .claude/commands/
   ```

2. **Edit `CLAUDE.md`** — replace the sample conventions with your project's actual rules

3. **Edit `docs/system-manifest.yaml`** — replace the sample domain with your real codebase structure

4. **Edit `convention-checks.yaml`** — replace the sample checks with your project-specific rules

5. **Copy CI actions** to your repo:
   ```bash
   cp ../../ci/*.yml .github/workflows/
   ```

## What you get

- Every Claude Code session follows the same 22-step workflow automatically
- The system manifest scopes AI context per domain (no "reads too much" hallucinations)
- Convention checks run on every PR via CI
- Issue template includes ROI estimation + downstream impact brief
- Training plan requirement for new capabilities

## Next steps

- Read [../../docs/playbook/adoption-guide.md](../../docs/playbook/adoption-guide.md) for the full brownfield adoption guide
- Read [../../docs/playbook/process-overview.md](../../docs/playbook/process-overview.md) for the workflow details
- Copy [../../templates/issue-template.md](../../templates/issue-template.md) to `.github/ISSUE_TEMPLATE/`
