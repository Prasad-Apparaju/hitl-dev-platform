# HITL AI-Driven Development Platform

A repeatable process + tooling for teams adopting AI-native development. Copy the templates, fill in your project's conventions, and every developer's Claude instance follows the same standards from day one.

## The Core Idea

The team — PM, Architect, Developers, and AI — discusses every design decision together. Once a decision is finalized, it's captured in documentation: HLDs for architecture, LLDs for component design, ADRs for trade-offs, and a System Manifest for domain boundaries.

From that point forward, **all downstream activities — code generation, testing, code review, deployment planning, and ROI verification — are driven off that documentation.** The documentation is not a record of what was built. It's the specification that drives what gets built.

This inverts the traditional relationship between docs and code. In most teams, documentation is written after the code (if at all) and drifts almost immediately. In this process, documentation is written first — with AI's help, in minutes rather than weeks — and the code is generated from it.

## Quick Start — New Project

```bash
# 1. Copy skills to your repo (shared workflow for every developer's Claude)
cp -r skills/ your-repo/.claude/commands/

# 2. Copy and customize the CLAUDE.md template
cp templates/CLAUDE.md.template your-repo/CLAUDE.md
# Edit: fill in your project's conventions and coding standards

# 3. Generate a system manifest from your codebase
python tools/generate-manifest/generator.py --source your-repo/src --output your-repo/docs/system-manifest.yaml

# 4. Copy convention checker config
cp examples/greenfield/convention-checks.yaml your-repo/
# Edit: add your project-specific checks

# 5. Copy CI actions
cp ci/*.yml your-repo/.github/workflows/
```

Every developer who clones the repo now gets the same process.

## Quick Start — Existing Project (Brownfield)

An architect working with AI can produce the full documentation baseline in one week. See [docs/playbook/adoption-guide.md](docs/playbook/adoption-guide.md) for the day-by-day sprint plan.

## What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| **Skills** | `skills/` | Claude Code skills: 22-step dev workflow + impact analysis. Copy to `.claude/commands/` |
| **Templates** | `templates/` | CLAUDE.md template, system manifest schema, ADR/HLD/LLD/training plan templates, issue template with ROI section |
| **Tools** | `tools/` | Convention checker (pluggable, config-driven), Mermaid fixer, Markdown-to-PDF with Mermaid support |
| **CI Actions** | `ci/` | GitHub Actions for convention checking + manifest drift detection |
| **Examples** | `examples/` | Greenfield starter with minimal CLAUDE.md, manifest, and convention config |
| **Playbook** | `docs/playbook/` | Adoption guide (brownfield one-week sprint) + process overview |
| **Infographics** | `templates/infographic/` | HTML templates for team collaboration diagrams (renderable to PDF) |

## How to Keep in Sync

The update model is **copy, not dependency.** Each project gets its own copy of the skills and tools. Updates are explicit pulls, not automatic:

```bash
# Update skills (overwrite — skills are platform-owned)
cp -r hitl-dev-platform/skills/ your-repo/.claude/commands/

# Update CI actions
cp hitl-dev-platform/ci/*.yml your-repo/.github/workflows/

# DON'T overwrite: CLAUDE.md, system-manifest.yaml, convention-checks.yaml
# Those are project-specific content
```

When the platform adds a new workflow step or improves the convention checker, projects update by pulling the latest and copying the shared files. Project-specific content (CLAUDE.md conventions, manifest domains, check definitions) is never overwritten.

## Philosophy

**Quality over speed.** The goal is meticulous system evolution with minimized problems — not maximum deployment velocity. Every step in the 22-step workflow prevents a specific failure mode.

**Inverse Conway Maneuver for AI agents.** Design the knowledge boundaries explicitly in a System Manifest, and the quality of what agents produce mirrors those boundaries. Scoped agents with clean facades produce modular, convention-honoring output.

**The docs are the moat, not the AI tools.** Every team has access to the same AI models. The competitive advantage is in the documentation that makes those models produce *your* system's conventions, *your* architecture's patterns, *your* domain's edge cases.

**Convention enforcement across all instances.** When 4 developers each use their own Claude Code, consistency comes from three layers: CLAUDE.md (auto-loaded rules), CI checks (automated enforcement), and PR review (human gates). The platform provides all three.

## License

MIT
