# commands/

**Lightweight Claude Code slash commands** — simpler than skills.

Commands are single `.md` files: frontmatter (`description`, `argument-hint`) plus a short prompt. Unlike skills, which orchestrate multi-phase workflows, they are focused one-shot operations.

**Every command here ships.** A command whose name matches a skill is excluded by the build (`skill_exists_for_cmd` in `scripts/build.sh`), because the skill supersedes it. 27 such stubs — each one a two-line "invoke the X skill" pointer left from before commands merged into skills — were removed in this directory's last cleanup. Anything added here must have no matching skill, or it will silently not ship.

Note these are model-invocable: none set `disable-model-invocation`, so Claude may select them on its own. Their `description` is what that choice is made from.

| Command | What it does |
|---------|-------------|
| `architect/review-design.md` | Review HLD/LLD/ADR — approve design before implementation |
| `architect/verify-traceability.md` | Verify issue→design→code→tests→brief chain before merge |
| `ops/review-release.md` | Assess rollout plan and canary criteria before release |
| `ops/monitor-canary.md` | Read dashboards for active canary, produce go/no-go |
| `dev/check-implementation.md` | Compare implementation against the approved LLD and manifest |

The distinction from `ai/claude/`: commands are stateless one-shot prompts; skills orchestrate multi-step workflows with approval gates and produce artifacts.
