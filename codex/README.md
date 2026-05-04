# HITL for Codex CLI

This directory contains everything needed to use the HITL AI-Driven Development methodology with [Codex CLI](https://github.com/openai/codex).

## What's here

| File | Purpose |
|------|---------|
| `AGENTS.md` | Full HITL workflow as Codex instructions — copy to your project root |
| `config.toml` | Reference Codex CLI config (`~/.codex/config.toml` or `.codex/config.toml`) |
| `hooks.json` | Codex lifecycle hooks — copy to `.codex/hooks.json` for real-time enforcement |
| `hook-scripts/` | Hook scripts used by both Codex lifecycle hooks and git hooks |
| `git-hooks/pre-commit` | Blocks source commits without `.hitl/current-change.yaml`; strict mode also enforces status and boundary |
| `git-hooks/post-commit` | Writes a session summary to `docs/session-logs/` after each commit |
| `scripts/hitl-conventions.sh` | Runs semgrep, manifest drift, and Mermaid checks before a PR |
| `install.sh` | Copies all of the above into your project in one command |

## Prerequisites

- [Codex CLI](https://github.com/openai/codex) installed and authenticated
- `git` and a GitHub account
- `python3` available on PATH (used by hooks for YAML parsing)

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

The installer copies:
- `AGENTS.md` → project root
- `.codex/config.toml` → Codex CLI config (review model and `approval_policy`)
- `.codex/hooks.json` → Codex lifecycle hooks (real-time enforcement)
- `codex/hook-scripts/` → scripts used by both Codex and git hooks
- `.git/hooks/pre-commit` and `.git/hooks/post-commit` → git-level enforcement
- `codex/scripts/hitl-conventions.sh` → convention check runner
- `ci/manifest-drift/`, `scripts/fix_mermaid_br_tags.py`, `.semgrep/` → convention check dependencies
- `ai/templates/hld-template.md`, `ai/templates/lld-component-template.md` → design doc templates

**4. Enable Codex lifecycle hooks**

Open `.codex/config.toml` and confirm:
```toml
[features]
codex_hooks = true
```

This enables `.codex/hooks.json`, which runs HITL context checks before every Write/Edit — the same real-time enforcement as Claude Code's PreToolUse/PostToolUse hooks.

**5. Edit `AGENTS.md`**

Fill in your project's coding standards — language, framework, test framework, naming conventions. Everything else is pre-written.

**6. Create a GitHub issue for your first feature**

```bash
gh issue create --title "Add [feature name]" --body "..."
```

The HITL process requires a GitHub issue before any Tier 1+ change.

**7. Start your first change**

```bash
codex "Initialize the HITL change context for GH-1: [feature description]"
```

Codex reads `AGENTS.md` automatically and follows the Change Initialization workflow: impact analysis, documentation plan, test plan, and creation of `.hitl/current-change.yaml`. It will not write code until you confirm the plan.

## What happens during development

```bash
# Design first (Tier 2+ changes)
codex "Generate the HLD for the authentication service"
# → Codex creates docs/02-design/technical/hld/auth-service.md using ai/templates/hld-template.md
# → You review and approve before it proceeds to LLD

# Then implement with TDD
codex "Run the TDD workflow for the user login component"
# → Codex generates tests first, stops for your review
# → After 'tests approved', generates implementation code

# Check conventions before PR
bash codex/scripts/hitl-conventions.sh

# Commit — pre-commit hook verifies .hitl/current-change.yaml exists
git add . && git commit -m "feat: add user login"
# → post-commit writes docs/session-logs/hitl-session-GH-1-<timestamp>.md
```

## Enforcement layers

| Layer | What it enforces | When |
|-------|-----------------|------|
| `AGENTS.md` instructions | Checks context file before source edits; refuses to implement without approved LLD | Every Codex prompt |
| Codex lifecycle hooks (`.codex/hooks.json`) | Blocks Write/Edit before context file exists; warns on boundary violations after edits | Every file edit (requires `codex_hooks = true`) |
| `pre-commit` hook (default) | Blocks source commits without context file; warns on status and boundary issues | Every `git commit` |
| `pre-commit` hook (strict mode) | Also blocks Tier 2+ commits without `implementation-approved`; blocks boundary violations | Every `git commit` with `HITL_STRICT=1` |
| `post-commit` hook | Writes session summary with evidence checklist | Every `git commit` |
| `hitl-conventions.sh` | Semgrep violations, manifest drift, Mermaid `<br/>` tags | Run manually before PR |

### Enable strict mode for git hooks

```bash
git config hitl.strict true   # project-level (recommended for Tier 2+ teams)
# or
HITL_STRICT=1 git commit ...  # one-off override
```

Strict mode blocks Tier 2+ source commits unless status is `implementation-approved` or later, and blocks domain boundary violations outright.

## Keeping in sync with the platform

All installed files are copies, not dependencies. To pull in updates:

```bash
# Re-run the installer (backs up existing hooks, skips AGENTS.md if already customised)
bash /path/to/hitl-dev-platform/codex/install.sh /path/to/my-project
```

Don't overwrite `AGENTS.md` if you've added project-specific conventions — merge manually instead.

## Further reading

- [Full HITL methodology](../README.md)
- [31-step workflow reference](../docs/playbook/workflow-reference.md)
- [Process tiers and when to abbreviate](../docs/playbook/common-pitfalls.md)
- [Adoption checklist](../docs/playbook/adoption-checklist.md)
