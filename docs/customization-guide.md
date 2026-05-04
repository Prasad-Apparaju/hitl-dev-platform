# Customization Guide

How to find and edit skills, agents, hooks, and templates — for both Claude Code and Codex users.

## Where platform files live

All skills, agents, and hooks live inside the platform repo. If you followed the recommended setup, that is `~/tools/hitl-dev-platform`. Open that directory, find the file, edit it, save. Changes take effect on the next Claude Code or Codex session — no rebuild or restart needed.

```
~/tools/hitl-dev-platform/
  claude/          ← slash command prompts
  agents/          ← subagent role definitions
  hooks/           ← enforcement scripts (Claude Code)
  codex/           ← Codex-specific files
  shared/templates/       ← document templates used by skills
```

---

## Skills — Claude Code slash commands

| Slash command | File to edit |
|---|---|
| `/start-prd` | `claude/start-prd/SKILL.md` |
| `/start-brownfield` | `claude/start-brownfield/SKILL.md` |
| `/start-migration` | `claude/start-migration/SKILL.md` |
| `/dev-practices` | `claude/dev-practices/SKILL.md` |
| `/apply-change` | `claude/apply-change/SKILL.md` |
| `/check-conventions` | `claude/check-conventions/SKILL.md` |
| `/impact-brief` | `claude/impact-brief/SKILL.md` |
| `/tdd` | `claude/tdd/SKILL.md` |
| `/generate-docs` | `claude/generate-docs/SKILL.md` |
| `/conclude` | `claude/conclude/SKILL.md` |
| `/migrate:review-external-docs` | `claude/migrate/review-external-docs/SKILL.md` |
| `/pm:add-feature` | `claude/pm/add-feature/SKILL.md` |
| `/pm:answer-questions` | `claude/pm/answer-questions/SKILL.md` |
| `/pm:design-feature` | `claude/pm/design-feature/SKILL.md` |
| `/pm:prep-demo` | `claude/pm/prep-demo/SKILL.md` |
| `/pm:prioritize` | `claude/pm/prioritize/SKILL.md` |
| `/pm:report-bug` | `claude/pm/report-bug/SKILL.md` |
| `/pm:review-progress` | `claude/pm/review-progress/SKILL.md` |
| `/pm:review-scope-change` | `claude/pm/review-scope-change/SKILL.md` |
| `/pm:update-requirement` | `claude/pm/update-requirement/SKILL.md` |
| `/qa:plan-tests` | `claude/qa/plan-tests/SKILL.md` |
| `/qa:report-defect` | `claude/qa/report-defect/SKILL.md` |
| `/qa:review-tests` | `claude/qa/review-tests/SKILL.md` |
| `/qa:verify-quality` | `claude/qa/verify-quality/SKILL.md` |
| `/ops:build` | `claude/ops/build/SKILL.md` |
| `/ops:deploy` | `claude/ops/deploy/SKILL.md` |
| `/ops:apply-iac` | `claude/ops/apply-iac/SKILL.md` |
| `/architect:design-system` | `claude/architect/design-system/SKILL.md` |
| `/architect:design-feature` | `claude/architect/design-feature/SKILL.md` |

---

## Agents — subagents invoked by skills

| Agent role | File to edit |
|---|---|
| Architect reviewer | `agents/architect-reviewer.md` |
| Developer implementer | `agents/developer-implementer.md` |
| Ops release reviewer | `agents/ops-release-reviewer.md` |
| PM reviewer | `agents/pm-reviewer.md` |
| QA reviewer | `agents/qa-reviewer.md` |
| Spec conformance reviewer | `agents/spec-conformance-reviewer.md` |

---

## Hooks — enforcement scripts (Claude Code)

| What it enforces | File to edit |
|---|---|
| Pre-write: blocks edits without active change context | `hooks/check-hitl-context.sh` |
| Post-write: warns on cross-domain boundary violations | `hooks/check-domain-boundary.sh` |
| Post-write: incremental knowledge graph rebuild | `hooks/rebuild-graph.sh` |
| Session stop: writes session summary to `docs/session-logs/` | `hooks/write-session-summary.sh` |

---

## Templates used by skills

| Template | File |
|---|---|
| HLD document | `claude/generate-docs/templates/hld-template.md` |
| LLD component | `claude/generate-docs/templates/lld-component-template.md` |
| ADR | `claude/generate-docs/templates/adr-template.md` |
| New project CLAUDE.md | `claude/generate-docs/templates/CLAUDE.md.template` |
| System manifest schema | `claude/generate-docs/templates/system-manifest.schema.yaml` |

---

## Codex users

Codex reads `AGENTS.md` from your **product repo root** — that file is your copy, installed by `init-project.sh`. Edit it directly; your customizations won't be overwritten by platform updates.

The hook scripts Codex uses are also copies in your product repo under `codex/hook-scripts/`:

| What it enforces | File in your product repo |
|---|---|
| Pre-write: blocks edits without active change context | `codex/hook-scripts/check-hitl-context.sh` |
| Post-write: domain boundary check | `codex/hook-scripts/check-domain-boundary.sh` |
| Session summary | `codex/hook-scripts/write-session-summary.sh` |
| Knowledge graph rebuild | `codex/hook-scripts/rebuild-graph.sh` |

To pull an updated hook script from the platform without touching `AGENTS.md`:

```bash
bash ~/tools/hitl-dev-platform/codex/install.sh .
# install.sh backs up existing hooks and skips AGENTS.md if already present
```

---

## Pulling platform updates into your fork

After merging upstream changes, skills and agents update immediately for Claude Code (they're referenced, not copied). For Codex hook scripts, re-run the installer above.

```bash
cd ~/tools/hitl-dev-platform
git fetch upstream
git merge upstream/main   # review CHANGELOG.md first
```
