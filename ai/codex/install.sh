#!/usr/bin/env bash
# Install HITL enforcement hooks and AGENTS.md for Codex CLI users.
#
# Usage:
#   bash /path/to/hitl-dev-platform/ai/codex/install.sh [target-repo-path]
#
# If target-repo-path is omitted, installs into the current directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="${1:-$(pwd)}"

echo ""
echo "HITL Codex setup → $TARGET_DIR"
echo ""

# Validate target is a git repo
if [[ ! -d "$TARGET_DIR/.git" ]]; then
  echo "ERROR: $TARGET_DIR is not a git repository." >&2
  echo "Run 'git init' in the target directory first." >&2
  exit 1
fi

HOOKS_DIR="$TARGET_DIR/.git/hooks"

# --- AGENTS.md ---

AGENTS_DEST="$TARGET_DIR/AGENTS.md"
if [[ -f "$AGENTS_DEST" ]]; then
  echo "AGENTS.md already exists — review $SCRIPT_DIR/AGENTS.md and merge manually."
else
  cp "$SCRIPT_DIR/AGENTS.md" "$AGENTS_DEST"
  echo "✓ Copied AGENTS.md"
fi

# --- Codex CLI config and lifecycle hooks ---

mkdir -p "$TARGET_DIR/.codex"

if [[ -f "$TARGET_DIR/.ai/codex/config.toml" ]]; then
  echo ".ai/codex/config.toml already exists — review $SCRIPT_DIR/config.toml and merge manually."
else
  cp "$SCRIPT_DIR/config.toml" "$TARGET_DIR/.ai/codex/config.toml"
  echo "✓ Copied .ai/codex/config.toml (review model and approval_policy for your team)"
fi

if [[ -f "$TARGET_DIR/.ai/codex/hooks.json" ]]; then
  echo ".ai/codex/hooks.json already exists — skipping."
else
  cp "$SCRIPT_DIR/hooks.json" "$TARGET_DIR/.ai/codex/hooks.json"
  echo "✓ Copied .ai/codex/hooks.json (lifecycle hooks — requires codex_hooks = true in config.toml)"
fi

# --- Hook scripts (used by both git hooks and Codex lifecycle hooks) ---

mkdir -p "$TARGET_DIR/ai/codex/hook-scripts"
for script in check-hitl-context.sh check-domain-boundary.sh write-session-summary.sh; do
  SRC="$PLATFORM_ROOT/hooks/$script"
  if [[ -f "$SRC" ]]; then
    cp "$SRC" "$TARGET_DIR/ai/codex/hook-scripts/$script"
    chmod +x "$TARGET_DIR/ai/codex/hook-scripts/$script"
    echo "✓ Copied ai/codex/hook-scripts/$script"
  else
    echo "  WARNING: $SRC not found — skipping $script"
  fi
done

# Hook smoke test script
TEST_SCRIPT_SRC="$SCRIPT_DIR/hook-scripts/test-hooks.sh"
if [[ -f "$TEST_SCRIPT_SRC" ]]; then
  cp "$TEST_SCRIPT_SRC" "$TARGET_DIR/ai/codex/hook-scripts/test-hooks.sh"
  chmod +x "$TARGET_DIR/ai/codex/hook-scripts/test-hooks.sh"
  echo "✓ Copied ai/codex/hook-scripts/test-hooks.sh"
fi

# Graphify rebuild hook (triggers incremental graph rebuild on doc writes)
if [[ -f "$PLATFORM_ROOT/hooks/rebuild-graph.sh" ]]; then
  cp "$PLATFORM_ROOT/hooks/rebuild-graph.sh" "$TARGET_DIR/ai/codex/hook-scripts/rebuild-graph.sh"
  chmod +x "$TARGET_DIR/ai/codex/hook-scripts/rebuild-graph.sh"
  echo "✓ Copied ai/codex/hook-scripts/rebuild-graph.sh"
fi

# --- Convention check script and its dependencies ---

mkdir -p "$TARGET_DIR/ai/codex/scripts"
cp "$SCRIPT_DIR/scripts/hitl-conventions.sh" "$TARGET_DIR/ai/codex/scripts/hitl-conventions.sh"
chmod +x "$TARGET_DIR/ai/codex/scripts/hitl-conventions.sh"
echo "✓ Copied ai/codex/scripts/hitl-conventions.sh"

# Manifest drift checker
if [[ -d "$PLATFORM_ROOT/ci/manifest-drift" ]]; then
  mkdir -p "$TARGET_DIR/ci/manifest-drift"
  cp -r "$PLATFORM_ROOT/ci/manifest-drift/." "$TARGET_DIR/ci/manifest-drift/"
  echo "✓ Copied ci/manifest-drift/"
fi

# Mermaid fixer script
if [[ -f "$PLATFORM_ROOT/scripts/fix_mermaid_br_tags.py" ]]; then
  mkdir -p "$TARGET_DIR/scripts"
  cp "$PLATFORM_ROOT/scripts/fix_mermaid_br_tags.py" "$TARGET_DIR/scripts/fix_mermaid_br_tags.py"
  echo "✓ Copied scripts/fix_mermaid_br_tags.py"
fi

# Semgrep rules
if [[ -d "$PLATFORM_ROOT/.semgrep" ]]; then
  cp -r "$PLATFORM_ROOT/.semgrep" "$TARGET_DIR/.semgrep"
  echo "✓ Copied .semgrep/"
fi

# --- HLD/LLD templates ---

mkdir -p "$TARGET_DIR/templates"
for tmpl in hld-template.md lld-component-template.md; do
  SRC="$PLATFORM_ROOT/ai/claude/generate-docs/templates/$tmpl"
  if [[ -f "$SRC" ]]; then
    cp "$SRC" "$TARGET_DIR/ai/shared/templates/$tmpl"
    echo "✓ Copied ai/shared/templates/$tmpl"
  fi
done

# --- Claude Code hooks (.ai/claude/settings.json) ---

mkdir -p "$TARGET_DIR/.claude"
CLAUDE_SETTINGS="$TARGET_DIR/.ai/claude/settings.json"

if [[ -f "$CLAUDE_SETTINGS" ]]; then
  echo "  .ai/claude/settings.json already exists — add rebuild-graph hook manually if needed:"
  echo "    PostToolUse / Edit|Write → bash ai/codex/hook-scripts/rebuild-graph.sh"
else
  cat > "$CLAUDE_SETTINGS" << 'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash ai/codex/hook-scripts/check-hitl-context.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash ai/codex/hook-scripts/check-domain-boundary.sh"
          },
          {
            "type": "command",
            "command": "bash ai/codex/hook-scripts/rebuild-graph.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ai/codex/hook-scripts/write-session-summary.sh"
          }
        ]
      }
    ]
  }
}
JSON
  echo "✓ Created .ai/claude/settings.json (Claude Code hooks — HITL context, boundary check, graph rebuild)"
fi

# --- Graphify knowledge graph (optional) ---

if [[ ! -f "$TARGET_DIR/.graphifyignore" ]]; then
  if [[ -f "$PLATFORM_ROOT/.graphifyignore" ]]; then
    cp "$PLATFORM_ROOT/.graphifyignore" "$TARGET_DIR/.graphifyignore"
    echo "✓ Copied .graphifyignore"
  fi
fi

if [[ ! -f "$TARGET_DIR/.mcp.json" ]]; then
  cat > "$TARGET_DIR/.mcp.json" << 'JSON'
{
  "mcpServers": {
    "graphify": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "graphify.serve", "graphify-out/graph.json"]
    }
  }
}
JSON
  echo "✓ Created .mcp.json (Graphify MCP server — requires: pip install 'graphifyy[mcp]')"
else
  echo "  .mcp.json already exists — add Graphify server entry manually if needed"
fi

if command -v graphify &>/dev/null; then
  echo "  Graphify detected. After setup, build the initial graph:"
  echo "    cd $TARGET_DIR && graphify . --directed --no-viz"
  echo "  Then start the MCP server for AI queries:"
  echo "    python3 -m graphify.serve graphify-out/graph.json"
else
  echo "  Graphify not installed. Install with:"
  echo "    pip install graphifyy && graphify install"
  echo "  Then run: graphify . --directed --no-viz"
fi

# --- Git hooks ---

for hook in pre-commit post-commit; do
  SRC="$SCRIPT_DIR/git-hooks/$hook"
  DEST="$HOOKS_DIR/$hook"

  if [[ -f "$DEST" ]]; then
    cp "$DEST" "$DEST.hitl-backup"
    echo "  Backed up existing $hook to $hook.hitl-backup"
  fi

  cp "$SRC" "$DEST"
  chmod +x "$DEST"
  echo "✓ Installed .git/hooks/$hook"
done

echo ""
echo "Setup complete. Next steps:"
echo ""
echo "  1. Edit AGENTS.md — add your project's coding standards and conventions"
echo ""
echo "  2. Review .ai/codex/config.toml — set model and approval_policy for your team"
echo "     codex_hooks = true enables real-time HITL context checks (same timing as Claude Code)"
echo ""
echo "  3. Create your system manifest if you don't have one:"
echo "     mkdir -p docs && cp /path/to/hitl-dev-platform/ai/shared/templates/system-manifest-template.yaml docs/system-manifest.yaml"
echo ""
echo "  4. Start a change:"
echo "     codex 'Initialize HITL context for GH-42: add user notifications'"
echo ""
echo "  5. Before your first PR, run convention checks:"
echo "     bash ai/codex/scripts/hitl-conventions.sh"
echo ""
