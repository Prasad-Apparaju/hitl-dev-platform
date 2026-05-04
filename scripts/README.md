# scripts/

**Setup scripts** — run once to bootstrap a product repo.

| Script | What it does |
|--------|-------------|
| `init-project.sh` | Bootstraps a product repo: creates `CLAUDE.md`, `docs/system-manifest.yaml`, wires up the Claude Code plugin and Codex hooks, installs git hooks, and copies enforcement tools. Accepts `--tool claude\|codex\|both` (default: both) and `--name <project-name>`. |
| `fix_mermaid_br_tags.py` | Removes `<br/>` tags from Mermaid blocks for Obsidian compatibility. Run on any doc that will be viewed in Obsidian. |

**Usage:**
```bash
bash ~/tools/hitl-dev-platform/scripts/init-project.sh ~/code/my-product
```
