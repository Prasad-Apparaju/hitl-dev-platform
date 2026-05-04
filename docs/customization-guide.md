# Customization Guide

How to find and edit skills, agents, hooks, and templates — for both Claude Code and Codex users.

## Where platform files live

All skills, agents, and hooks live inside the platform repo. If you followed the recommended setup, that is `~/tools/hitl-dev-platform`. Open that directory, find the file, edit it, save. Changes take effect on the next Claude Code or Codex session — no rebuild or restart needed.

```
~/tools/hitl-dev-platform/
  skills/          ← slash command prompts
  agents/          ← subagent role definitions
  hooks/           ← enforcement scripts (Claude Code)
  codex/           ← Codex-specific files
  templates/       ← document templates used by skills
```

---

## Skills — Claude Code slash commands

| Slash command | File to edit |
|---|---|
| `/start-prd` | `skills/start-prd/SKILL.md` |
| `/start-brownfield` | `skills/start-brownfield/SKILL.md` |
| `/start-migration` | `skills/start-migration/SKILL.md` |
| `/dev-practices` | `skills/dev-practices/SKILL.md` |
| `/apply-change` | `skills/apply-change/SKILL.md` |
| `/check-conventions` | `skills/check-conventions/SKILL.md` |
| `/impact-brief` | `skills/impact-brief/SKILL.md` |
| `/tdd` | `skills/tdd/SKILL.md` |
| `/generate-docs` | `skills/generate-docs/SKILL.md` |
| `/conclude` | `skills/conclude/SKILL.md` |
| `/migrate:review-external-docs` | `skills/migrate/review-external-docs/SKILL.md` |
| `/pm:add-feature` | `skills/pm/add-feature/SKILL.md` |
| `/pm:answer-questions` | `skills/pm/answer-questions/SKILL.md` |
| `/pm:design-feature` | `skills/pm/design-feature/SKILL.md` |
| `/pm:prep-demo` | `skills/pm/prep-demo/SKILL.md` |
| `/pm:prioritize` | `skills/pm/prioritize/SKILL.md` |
| `/pm:report-bug` | `skills/pm/report-bug/SKILL.md` |
| `/pm:review-progress` | `skills/pm/review-progress/SKILL.md` |
| `/pm:review-scope-change` | `skills/pm/review-scope-change/SKILL.md` |
| `/pm:update-requirement` | `skills/pm/update-requirement/SKILL.md` |
| `/qa:plan-tests` | `skills/qa/plan-tests/SKILL.md` |
| `/qa:report-defect` | `skills/qa/report-defect/SKILL.md` |
| `/qa:review-tests` | `skills/qa/review-tests/SKILL.md` |
| `/qa:verify-quality` | `skills/qa/verify-quality/SKILL.md` |
| `/ops:build` | `skills/ops/build/SKILL.md` |
| `/ops:deploy` | `skills/ops/deploy/SKILL.md` |
| `/ops:apply-iac` | `skills/ops/apply-iac/SKILL.md` |
| `/architect:design-system` | `skills/architect/design-system/SKILL.md` |
| `/architect:design-feature` | `skills/architect/design-feature/SKILL.md` |

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
| HLD document | `skills/generate-docs/templates/hld-template.md` |
| LLD component | `skills/generate-docs/templates/lld-component-template.md` |
| ADR | `skills/generate-docs/templates/adr-template.md` |
| New project CLAUDE.md | `skills/generate-docs/templates/CLAUDE.md.template` |
| System manifest schema | `skills/generate-docs/templates/system-manifest.schema.yaml` |

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
