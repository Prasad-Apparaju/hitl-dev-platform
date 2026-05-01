# HITL for Codex CLI

This directory contains everything needed to use the HITL AI-Driven Development methodology with [Codex CLI](https://github.com/openai/codex).

## What's here

| File | Purpose |
|------|---------|
| `AGENTS.md` | Full HITL workflow as Codex instructions — copy to your project root |
| `codex.json` | Reference Codex CLI config (model + approval mode) |
| `git-hooks/pre-commit` | Blocks commits on source files without `.hitl/current-change.yaml`; warns on domain boundary violations |
| `git-hooks/post-commit` | Writes a session summary to `docs/session-logs/` after each commit |
| `scripts/hitl-conventions.sh` | Runs semgrep, manifest drift, and Mermaid checks before a PR |
| `install.sh` | Copies the above into your project in one command |

## Prerequisites

- [Codex CLI](https://github.com/openai/codex) installed and authenticated
- `git` and a GitHub account
- `python3` available on PATH (used by the git hooks for YAML parsing)

## Setup for a new project

**1. Clone this platform repo**

```bash
git clone https://github.com/Prasad-Apparaju/hitl-dev-platform.git
```

**2. Initialize your project repo** (skip if it already exists)

```bash
mkdir my-project && cd my-project && git init
```

**3. Run the installer**

```bash
bash /path/to/hitl-dev-platform/codex/install.sh /path/to/my-project
```

The installer:
- Copies `codex/AGENTS.md` to your project root
- Installs `pre-commit` and `post-commit` git hooks
- Copies `codex/scripts/hitl-conventions.sh` to `codex/scripts/` in your project

**4. Edit `AGENTS.md`**

Open the `AGENTS.md` that was just copied to your project root. Fill in your project's coding standards — language, framework, test framework, naming conventions. Everything else is pre-written.

**5. Create a GitHub issue for your first feature**

```bash
gh issue create --title "Add [feature name]" --body "..."
```

The HITL process requires a GitHub issue before any Tier 1+ change. This is how the AI knows what it's implementing and why.

**6. Start your first change**

```bash
codex "Initialize the HITL change context for GH-1: [feature description]"
```

Codex reads `AGENTS.md` automatically at startup and follows the Change Initialization workflow: impact analysis, documentation plan, test plan, and creation of `.hitl/current-change.yaml`. It will not write code until you confirm the plan.

## What happens during development

Once the context file exists, the typical session looks like:

```bash
# Design first (Tier 2+ changes)
codex "Generate the HLD for the authentication service"
# → Codex creates docs/02-design/technical/hld/auth-service.md
# → You review and approve before it proceeds to LLD

# Then implement with TDD
codex "Run the TDD workflow for the user login component"
# → Codex generates tests first, stops for your review
# → After 'tests approved', generates implementation code

# Check conventions before PR
bash codex/scripts/hitl-conventions.sh

# Commit — the pre-commit hook verifies .hitl/current-change.yaml exists
git add . && git commit -m "feat: add user login"
# → post-commit hook writes docs/session-logs/hitl-session-GH-1-<timestamp>.md
```

## Enforcement

| Layer | What it enforces | When |
|-------|-----------------|------|
| `AGENTS.md` instructions | Checks for context file before source edits; refuses to implement without approved LLD | Every Codex session |
| `pre-commit` hook | Blocks commits on source files without `.hitl/current-change.yaml` | Every `git commit` |
| `pre-commit` hook | Warns if staged files are outside `allowed_paths` in the context file | Every `git commit` |
| `post-commit` hook | Writes session summary with evidence checklist | Every `git commit` |
| `hitl-conventions.sh` | Semgrep violations, manifest drift, Mermaid `<br/>` tags | Run manually before PR |

**Tradeoff vs Claude Code:** Claude Code's `PreToolUse` hook blocks individual file edits in real time. Git hooks fire at commit time, so Codex can edit source files freely within a session and is blocked at commit if no context exists. The `AGENTS.md` instructions ask Codex to check for the file before editing, providing a second line of defence.

## Keeping in sync with the platform

`AGENTS.md` and the hook scripts are copies, not dependencies. To pull in updates:

```bash
# From inside your project
cp /path/to/hitl-dev-platform/codex/AGENTS.md AGENTS.md
cp /path/to/hitl-dev-platform/codex/git-hooks/pre-commit .git/hooks/pre-commit
cp /path/to/hitl-dev-platform/codex/git-hooks/post-commit .git/hooks/post-commit
cp /path/to/hitl-dev-platform/codex/scripts/hitl-conventions.sh codex/scripts/hitl-conventions.sh
```

Don't overwrite `AGENTS.md` if you've added project-specific conventions to it — merge manually instead.

## Further reading

- [Full HITL methodology](../README.md)
- [30-step workflow reference](../docs/playbook/workflow-reference.md)
- [Process tiers and when to abbreviate](../docs/playbook/common-pitfalls.md)
- [Adoption checklist](../docs/playbook/adoption-checklist.md)
