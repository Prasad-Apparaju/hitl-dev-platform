# HITL AI-Driven Development Platform

A repeatable process + tooling for teams adopting AI-native development. Copy the templates, fill in your project's conventions, and every developer's AI coding assistant follows the same standards from day one.

> **AI tool note:** This guide uses Claude Code and `CLAUDE.md` as examples. The process works with any AI coding assistant that supports auto-loaded project rules (Cursor, Windsurf, Cline, etc.).

> **Language note:** The enforcement tooling (manifest drift checker, import analysis, Semgrep rules) currently targets Python codebases. The process and documentation workflow are language-agnostic — only the automated checks are Python-first. TypeScript and other language support is planned.

## The Core Idea

The team — PM, Architect, Developers, and AI — discusses every design decision together. Once a decision is finalized, it's captured in documentation: HLDs for architecture, LLDs for component design, ADRs for trade-offs, and a System Manifest for domain boundaries.

From that point forward, **all downstream activities — code generation, testing, code review, deployment planning, and ROI verification — are driven off that documentation.** The documentation is not a record of what was built. It's the specification that drives what gets built.

This inverts the traditional relationship between docs and code. In most teams, documentation is written after the code (if at all) and drifts almost immediately. In this process, documentation is written first — with AI's help, significantly faster (observed in pilot projects) — and the code is generated from it.

## Quick Start — New Project

```bash
# 0. Create target directories (idempotent — safe to re-run)
mkdir -p your-repo/.claude/skills your-repo/.claude/agents your-repo/.claude/commands \
  your-repo/tools your-repo/templates your-repo/.github/workflows your-repo/.github \
  your-repo/.semgrep your-repo/scripts your-repo/.hitl

# 1. Copy skills and agents to your repo
cp -r skills/ your-repo/.claude/skills/
cp -r .claude/agents/ your-repo/.claude/agents/

# 2. Copy and customize the CLAUDE.md template
cp templates/CLAUDE.md.template your-repo/CLAUDE.md
# Edit: fill in your project's conventions and coding standards

# 3. Generate a system manifest from your codebase
python tools/generate-manifest/generator.py --source your-repo/src --output your-repo/docs/system-manifest.yaml

# 3a. (Recommended) Install Graphify — builds a knowledge graph over your design docs
# so AI skills use targeted queries instead of reading the full manifest every time.
# Required once per environment; not re-run per project.
pip install graphifyy && graphify install
# Then from your repo root, build the initial graph:
cd your-repo && graphify . --directed --no-viz
# Start the MCP server so Claude Code can query it:
python3 -m graphify.serve graphify-out/graph.json &
# On large codebases (50+ domains), this step pays off immediately. Skip it on small
# repos — skills fall back to direct file reads automatically.

# 4. Copy convention checker config
cp examples/greenfield/convention-checks.yaml your-repo/
# Edit: add your project-specific checks

# 5. Copy CI actions
# NOTE: These are copyable templates, not active workflows for the platform repo.
# They are designed to run inside your product repo after docs/system-manifest.yaml
# has been generated.
cp ci/*.yml your-repo/.github/workflows/

# 6. Copy preflight script (required by traceability-check.yml)
cp -r tools/preflight/ your-repo/tools/preflight/

# 7. Copy manifest drift checker (required by convention-check.yml)
cp -r tools/manifest-drift/ your-repo/tools/manifest-drift/

# 8. Copy Semgrep rules (required by convention-check.yml)
cp -r .semgrep/ your-repo/.semgrep/

# 9. Copy PR template
mkdir -p your-repo/.github
cp templates/pull-request-template.md your-repo/.github/PULL_REQUEST_TEMPLATE.md

# 10. Copy decision packet template (reference for impact analysis)
cp templates/decision-packet-template.yaml your-repo/templates/decision-packet-template.yaml

# 11. Copy legacy scripts if referenced by your CI
cp -r scripts/ your-repo/scripts/
```

Every developer who clones the repo now gets the same process.

## Quick Start — Existing Project (Brownfield)

An architect working with AI can produce the documentation baseline in a sprint — typically one to two weeks for a medium-sized system, longer for larger platforms. See [docs/playbook/adoption-guide.md](docs/playbook/adoption-guide.md) for scope expectations by system size.

## What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| **Skills** | `skills/` | Claude Code skills: dev workflow, TDD, impact brief, conventions. Copy to `.claude/skills/` |
| **Agents** | `.claude/agents/` | Role subagents: PM reviewer, architect, developer, QA, ops, conformance reviewer. Copy to `.claude/agents/` |
| **Templates** | `templates/` | 15 templates: CLAUDE.md, system manifest, ADR, training plan, issue, test strategy, security audit, best practices, cost analysis, performance, data model mapping, API contract mapping, decision catalog, test registry, incident registry |
| **Patterns** | `docs/patterns/` | Architectural patterns: failure mode taxonomy, idempotency keys |
| **Tools** | `tools/` | Convention checker (pluggable, config-driven), Mermaid fixer, Markdown-to-PDF with Mermaid support |
| **CI Actions** | `ci/` | GitHub Actions for convention checking + manifest drift detection |

> **CI note:** The workflows under `ci/` are copyable templates, not active workflows for this platform repo. They are designed to run inside your product repo after `docs/system-manifest.yaml` has been generated. Copy them to `.github/workflows/` in your target repo.
| **Examples** | `examples/` | Greenfield starter with minimal CLAUDE.md, manifest, and convention config |
| **Playbook** | `docs/playbook/` | Adoption guide (brownfield one-week sprint) + process overview |
| **Infographics** | `templates/infographic/` | HTML templates for team collaboration diagrams (renderable to PDF) |

## How to Keep in Sync

The update model is **copy, not dependency.** Each project gets its own copy of the skills and tools. Updates are explicit pulls, not automatic:

```bash
# Update skills and agents (overwrite — platform-owned)
cp -r hitl-dev-platform/skills/ your-repo/.claude/skills/
cp -r hitl-dev-platform/agents/ your-repo/.claude/agents/

# Update CI actions
cp hitl-dev-platform/ci/*.yml your-repo/.github/workflows/

# Update preflight, manifest-drift, semgrep rules, scripts
cp -r hitl-dev-platform/tools/preflight/ your-repo/tools/preflight/
cp -r hitl-dev-platform/tools/manifest-drift/ your-repo/tools/manifest-drift/
cp -r hitl-dev-platform/.semgrep/ your-repo/.semgrep/
cp -r hitl-dev-platform/scripts/ your-repo/scripts/

# DON'T overwrite: CLAUDE.md, system-manifest.yaml, convention-checks.yaml
# Those are project-specific content
```

When the platform adds a new workflow step or improves the convention checker, projects update by pulling the latest and copying the shared files. Project-specific content (CLAUDE.md conventions, manifest domains, check definitions) is never overwritten.

## Philosophy

**Quality over speed.** The goal is meticulous system evolution with minimized problems — not maximum deployment velocity. Every step in the 30-step workflow prevents a specific failure mode.

**Inverse Conway Maneuver for AI agents.** Design the knowledge boundaries explicitly in a System Manifest, and the quality of what agents produce mirrors those boundaries. Scoped agents with clean facades produce modular, convention-honoring output.

**The docs are the moat, not the AI tools.** Every team has access to the same AI models. The competitive advantage is in the documentation that makes those models produce *your* system's conventions, *your* architecture's patterns, *your* domain's edge cases.

**Convention enforcement across all instances.** When 4 developers each use their own Claude Code, consistency comes from three layers: CLAUDE.md (auto-loaded rules), CI checks (automated enforcement), and PR review (human gates). The platform provides all three.

## License

MIT
