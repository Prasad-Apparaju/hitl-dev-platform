# HITL Quick Start

> **AI tool note:** This guide uses Claude Code as the primary example. Codex CLI is fully supported — pass `--tool codex` or `--tool both` to `init-project.sh`.

> **Language note:** Convention enforcement (semgrep rules, manifest drift checker) currently targets Python codebases. The process and doc workflow are language-agnostic.

## The Core Idea

The team — PM, Architect, Developers, and AI — discusses every design decision together. Once finalized, it's captured in version-controlled docs: HLDs for architecture, LLDs for component design, ADRs for trade-offs, and a System Manifest for domain boundaries.

From that point forward, **all downstream work — code generation, testing, deployment — is driven from that documentation.** The docs are not a record of what was built. They are the specification that drives what gets built.

---

## Quick Start — New Project

**Step 1: Fork and clone the platform once per machine**

```bash
# Fork https://github.com/your-org/hitl-dev-platform on GitHub, then:
git clone https://github.com/YOUR-ORG/hitl-dev-platform ~/tools/hitl-dev-platform
```

The platform stays at this shared path. All product repos reference it — nothing is copied except product-specific files.

**Step 2: Bootstrap your product repo**

```bash
bash ~/tools/hitl-dev-platform/tools/scripts/init-project.sh ~/code/my-product
```

Default is `--tool both` (Claude Code + Codex). Use `--tool claude` or `--tool codex` if you only need one.

**What gets created in your product repo:**

| File / directory | Purpose |
|---|---|
| `CLAUDE.md` | Your project's coding standards — edit this |
| `AGENTS.md` | Codex reads this automatically — edit this |
| `docs/system-manifest.yaml` | Domain and API boundary definitions — fill in |
| `docs/02-design/` | HLD, LLD, ADR directories |
| `.claude/settings.json` | Plugin reference + hook wiring |
| `.hitl/hooks/*.sh` | Hook wrappers (resolve platform via `HITL_PLATFORM_ROOT`) |
| `.semgrep/` | Semgrep convention rules (required by `/check-conventions`) |
| `ci/manifest-drift/` | Manifest drift checker (required by `/check-conventions`) |
| `tools/scripts/fix_mermaid_br_tags.py` | Mermaid linter (required by `/check-conventions`) |

Skills, agents, and commands are **not** copied — they load from the shared platform via the Claude Code plugin.

**Step 3: Edit your project-specific files**

```bash
# Fill in your project's coding standards and conventions
$EDITOR ~/code/my-product/CLAUDE.md

# Document your domains and API boundaries
$EDITOR ~/code/my-product/docs/system-manifest.yaml
```

**Step 4: (Optional) Generate a manifest from an existing codebase**

```bash
python ~/tools/hitl-dev-platform/tools/generate-manifest/generator.py \
  --source ~/code/my-product/src \
  --output ~/code/my-product/docs/system-manifest.yaml
```

**Step 5: (Optional) Install Graphify for large codebases**

Graphify builds a knowledge graph over your design docs. Skills fall back to direct file reads without it — add it once your repo has enough domains that full-manifest reads become expensive.

```bash
pip install graphifyy && graphify install
cd ~/code/my-product && graphify . --directed --no-viz
python3 -m graphify.serve graphify-out/graph.json &
```

**Step 6: Copy CI templates**

```bash
mkdir -p ~/code/my-product/.github/workflows
cp ~/tools/hitl-dev-platform/ci/workflows/*.yml ~/code/my-product/.github/workflows/
cp ~/tools/hitl-dev-platform/templates/pull-request-template.md \
   ~/code/my-product/.github/PULL_REQUEST_TEMPLATE.md
```

Every developer who clones the product repo now gets the same process.

---

## Quick Start — Existing Project (Brownfield)

Run `init-project.sh` against your existing repo. It is idempotent — it skips files that already exist:

```bash
bash ~/tools/hitl-dev-platform/tools/scripts/init-project.sh ~/code/existing-repo
```

Then generate the system manifest baseline:

```bash
python ~/tools/hitl-dev-platform/tools/generate-manifest/generator.py \
  --source ~/code/existing-repo/src \
  --output ~/code/existing-repo/docs/system-manifest.yaml
```

An architect working with AI can produce the full documentation baseline in a sprint — typically one to two weeks for a medium-sized system. See [docs/playbook/adoption-guide.md](playbook/adoption-guide.md) for scope expectations by system size.

---

## Additional products on the same machine

The platform stays in one place. Just run `init-project.sh` for each new product:

```bash
bash ~/tools/hitl-dev-platform/tools/scripts/init-project.sh ~/code/product-b
bash ~/tools/hitl-dev-platform/tools/scripts/init-project.sh ~/code/product-c
```

---

## Version isolation

By default all products on one machine share one platform checkout and pick up changes immediately when you `git pull` in the platform. That is the right default for a team maintaining one standard.

If a specific product needs to stay pinned to an older platform version:

```bash
# Clone a second copy of the platform at a specific tag
git clone https://github.com/YOUR-ORG/hitl-dev-platform ~/tools/hitl-dev-platform-v1
cd ~/tools/hitl-dev-platform-v1 && git checkout v1.0.0

# Bootstrap the product against that version
bash ~/tools/hitl-dev-platform-v1/tools/scripts/init-project.sh ~/code/legacy-product
```

The hook wrappers in `.hitl/hooks/` use `HITL_PLATFORM_ROOT` at runtime — setting it overrides which platform clone is used without re-running init.

---

## CI setup

Hook wrappers resolve the platform at runtime via `HITL_PLATFORM_ROOT`. On CI machines:

```yaml
# .github/workflows/your-workflow.yml
- name: Install HITL platform
  run: git clone https://github.com/YOUR-ORG/hitl-dev-platform ~/tools/hitl-dev-platform

- name: Set platform path
  run: echo "HITL_PLATFORM_ROOT=$HOME/tools/hitl-dev-platform" >> $GITHUB_ENV
```

Or set `HITL_PLATFORM_ROOT` to the path where the platform is cloned in your CI environment.

---

## Keeping the platform up to date

Skills and agents update for all products immediately when you pull in the platform clone:

```bash
cd ~/tools/hitl-dev-platform
git fetch upstream && git merge upstream/main
```

Convention tools (`.semgrep/`, `ci/manifest-drift/`, `tools/scripts/`) are copies in each product repo. Refresh them by re-running init (it skips files that already exist — pass `--force` manually if you want to overwrite):

```bash
# Manual refresh of convention tools
cp -r ~/tools/hitl-dev-platform/.semgrep/ ~/code/my-product/.semgrep/
cp -r ~/tools/hitl-dev-platform/ci/manifest-drift/ ~/code/my-product/ci/manifest-drift/
cp ~/tools/hitl-dev-platform/tools/scripts/fix_mermaid_br_tags.py ~/code/my-product/scripts/
```

Never overwrite: `CLAUDE.md`, `AGENTS.md`, `docs/system-manifest.yaml` — those are project-specific.

---

## What's Included

| Component | Location in platform | Notes |
|---|---|---|
| Skills (slash commands) | `ai/` | Loaded via plugin — not copied |
| Agents (subagents) | `agents/` | Loaded via plugin — not copied |
| Templates | `templates/` | Referenced; copy on demand |
| Convention rules | `.semgrep/` | Copied to product repos by init |
| Manifest drift checker | `ci/manifest-drift/` | Copied to product repos by init |
| CI actions | `ci/workflows/` | Copy once to `.github/workflows/` |
| Patterns / playbook | `docs/` | Reference from platform |
| Codex files | `codex/` | Copied to product repos by init |

---

## Philosophy

**Quality over speed.** The goal is meticulous system evolution with minimized problems — not maximum deployment velocity. Every step in the workflow prevents a specific failure mode.

**The docs are the moat, not the AI tools.** Every team has access to the same AI models. The competitive advantage is in the documentation that makes those models produce *your* system's conventions, *your* architecture's patterns, *your* domain's edge cases.

**Convention enforcement across all instances.** When multiple developers each use their own Claude Code, consistency comes from three layers: CLAUDE.md (auto-loaded rules), CI checks (automated enforcement), and PR review (human gates). The platform provides all three.

---

## License

MIT
