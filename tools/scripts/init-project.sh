#!/usr/bin/env bash
# Bootstrap a new product repository with HITL enforcement.
#
# Usage:
#   bash /path/to/hitl-dev-platform/tools/scripts/init-project.sh <target-dir> [options]
#
# Options:
#   --tool  claude|codex|both   AI tool to configure (default: both)
#   --name  <project-name>      Project name for CLAUDE.md header (default: dirname)
#
# Recommended setup:
#   git clone https://github.com/your-org/hitl-dev-platform ~/tools/hitl-dev-platform
#   bash ~/tools/hitl-dev-platform/tools/scripts/init-project.sh ~/code/my-product
#
# Claude Code — what gets created in the product repo:
#   .claude/settings.json          plugin reference + project-relative hook paths
#   .hitl/hooks/*.sh            wrapper scripts; resolve platform via HITL_PLATFORM_ROOT
#   .semgrep/                   semgrep convention rules (required by /hitl:dev-check-conventions)
#   ci/manifest-drift/       manifest drift checker (required by /hitl:dev-check-conventions)
#   scripts/fix_mermaid_br_tags.py  Mermaid linter (required by /hitl:dev-check-conventions)
#
# Skills, agents, and commands are never copied — they load from the shared
# platform via the Claude Code plugin.
#
# Codex — what gets created (via ai/codex/install.sh):
#   AGENTS.md, .ai/codex/, ai/codex/hook-scripts/, .git/hooks/
#
# Version isolation:
#   All products on one machine share one platform checkout by default.
#   If a product needs a specific platform version, clone the fork to a
#   different path and pass it:
#     git clone ... ~/tools/hitl-dev-platform-v2
#     HITL_PLATFORM_ROOT=~/tools/hitl-dev-platform-v2 \
#       bash ~/tools/hitl-dev-platform-v2/tools/scripts/init-project.sh ~/code/my-product
#
# CI setup:
#   Hook wrappers resolve HITL_PLATFORM_ROOT at runtime. On CI machines, set:
#     export HITL_PLATFORM_ROOT=/path/to/platform-clone
#   or clone to the default path (~/tools/hitl-dev-platform).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ---- Argument parsing ----

TOOL=""
PROJECT_NAME=""
TARGET_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)  TOOL="$2";         shift 2 ;;
    --name)  PROJECT_NAME="$2"; shift 2 ;;
    -*)      echo "Unknown option: $1" >&2; exit 1 ;;
    *)       TARGET_DIR="$1";   shift ;;
  esac
done

if [[ -z "$TARGET_DIR" ]]; then
  echo "Usage: $0 <target-dir> [--tool claude|codex|both] [--name <project-name>]" >&2
  exit 1
fi

# Validate explicit --tool value if provided; otherwise prompt interactively
if [[ -n "$TOOL" && ! "$TOOL" =~ ^(claude|codex|both)$ ]]; then
  echo "ERROR: --tool must be claude, codex, or both" >&2
  exit 1
fi

if [[ -z "$TOOL" ]]; then
  echo ""
  echo "Which AI tool will you use in this project?"
  echo "  1) Claude Code"
  echo "  2) Codex"
  echo "  3) Both"
  echo ""
  read -rp "Enter 1, 2, or 3: " _choice
  case "$_choice" in
    1) TOOL="claude" ;;
    2) TOOL="codex"  ;;
    3) TOOL="both"   ;;
    *) echo "Invalid choice. Run again and enter 1, 2, or 3." >&2; exit 1 ;;
  esac
fi

[[ -z "$PROJECT_NAME" ]] && PROJECT_NAME="$(basename "$TARGET_DIR")"

echo ""
echo "HITL project init"
echo "  Target:   $TARGET_DIR"
echo "  Tool:     $TOOL"
echo "  Project:  $PROJECT_NAME"
echo "  Platform: $PLATFORM_ROOT"
echo ""

# ---- Create target directory and git repo ----

mkdir -p "$TARGET_DIR"

if [[ ! -d "$TARGET_DIR/.git" ]]; then
  git -C "$TARGET_DIR" init -q
  echo "✓ git init"
fi

# ---- Shared: CLAUDE.md ----

CLAUDE_DEST="$TARGET_DIR/CLAUDE.md"
if [[ -f "$CLAUDE_DEST" ]]; then
  echo "  CLAUDE.md already exists — skipping"
else
  TMPL="$PLATFORM_ROOT/ai/claude/generate-docs/templates/CLAUDE.md.template"
  if [[ -f "$TMPL" ]]; then
    cp "$TMPL" "$CLAUDE_DEST"
    echo "✓ CLAUDE.md — customize with your project's coding standards"
  else
    echo "  WARNING: CLAUDE.md template not found at $TMPL"
  fi
fi

# ---- Shared: docs structure and system manifest ----

mkdir -p \
  "$TARGET_DIR/docs/02-design/technical/hld" \
  "$TARGET_DIR/docs/02-design/technical/lld" \
  "$TARGET_DIR/docs/02-design/technical/adrs" \
  "$TARGET_DIR/docs/session-logs"
echo "✓ docs/ directory structure"

if [[ ! -f "$TARGET_DIR/docs/system-manifest.yaml" ]]; then
  MANIFEST_TMPL="$PLATFORM_ROOT/ai/shared/templates/system-manifest-template.yaml"
  if [[ -f "$MANIFEST_TMPL" ]]; then
    cp "$MANIFEST_TMPL" "$TARGET_DIR/docs/system-manifest.yaml"
    echo "✓ docs/system-manifest.yaml — fill in your domains and API boundaries"
  fi
fi

# ---- Convention tool assets ----
# check-conventions and related skills invoke these tools via project-relative
# paths. They must live in the product repo, not the shared platform.

setup_tools() {
  local copied=0

  if [[ -d "$PLATFORM_ROOT/.semgrep" && ! -d "$TARGET_DIR/.semgrep" ]]; then
    cp -r "$PLATFORM_ROOT/.semgrep" "$TARGET_DIR/.semgrep"
    echo "✓ .semgrep/ (semgrep convention rules)"
    (( copied++ )) || true
  fi

  if [[ -d "$PLATFORM_ROOT/ci/manifest-drift" && ! -d "$TARGET_DIR/ci/manifest-drift" ]]; then
    mkdir -p "$TARGET_DIR/ci"
    cp -r "$PLATFORM_ROOT/ci/manifest-drift" "$TARGET_DIR/ci/manifest-drift"
    echo "✓ ci/manifest-drift/"
    (( copied++ )) || true
  fi

  if [[ -f "$PLATFORM_ROOT/tools/scripts/fix_mermaid_br_tags.py" && ! -f "$TARGET_DIR/scripts/fix_mermaid_br_tags.py" ]]; then
    mkdir -p "$TARGET_DIR/scripts"
    cp "$PLATFORM_ROOT/tools/scripts/fix_mermaid_br_tags.py" "$TARGET_DIR/scripts/fix_mermaid_br_tags.py"
    echo "✓ scripts/fix_mermaid_br_tags.py"
    (( copied++ )) || true
  fi

  [[ $copied -eq 0 ]] && echo "  Convention tools already present — skipping" || true
}

# ---- Claude Code setup ----
# Skills, agents, and commands load from the shared platform via the plugin.
# Hook wrappers use HITL_PLATFORM_ROOT so the product repo is portable across
# machines and CI without hardcoded paths.

setup_claude() {
  mkdir -p "$TARGET_DIR/.claude"
  local SETTINGS="$TARGET_DIR/.claude/settings.json"

  if [[ -f "$SETTINGS" ]]; then
    echo "  .claude/settings.json already exists — skipping"
  else
    cat > "$SETTINGS" <<JSON
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "bash .hitl/hooks/welcome.sh" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash .hitl/hooks/check-hitl-context.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash .hitl/hooks/check-domain-boundary.sh" },
          { "type": "command", "command": "bash .hitl/hooks/rebuild-graph.sh" },
          { "type": "command", "command": "bash .hitl/hooks/sync-step-to-issue.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "bash .hitl/hooks/write-session-summary.sh" }
        ]
      }
    ]
  }
}
JSON
    echo "✓ .claude/settings.json"
  fi

  # Skills — symlinks from .claude/commands/ to the platform SKILL.md files.
  # Claude Code discovers commands from this directory; symlinks mean platform
  # updates propagate without re-running this script.
  local CMDS_DIR="$TARGET_DIR/.claude/commands"
  if [[ ! -d "$CMDS_DIR" ]]; then
    mkdir -p "$CMDS_DIR"

    # Flat skills
    for skill in start-prd start-brownfield start-migration dev-practices apply-change \
                 check-conventions impact-brief tdd generate-docs conclude review-lld-adherence; do
      local src="$PLATFORM_ROOT/ai/claude/$skill/SKILL.md"
      [[ -f "$src" ]] && ln -sf "$src" "$CMDS_DIR/$skill.md"
    done

    # Namespaced skills — subdirectory prefix becomes /namespace:command
    for ns in architect qa ops pm migrate; do
      mkdir -p "$CMDS_DIR/$ns"
      find "$PLATFORM_ROOT/ai/claude/$ns" -name "SKILL.md" 2>/dev/null | while read -r f; do
        local cmd; cmd=$(basename "$(dirname "$f")")
        ln -sf "$f" "$CMDS_DIR/$ns/$cmd.md"
      done
    done

    local count; count=$(find "$CMDS_DIR" -name "*.md" | wc -l | tr -d ' ')
    echo "✓ .claude/commands/ — $count skill symlinks → $PLATFORM_ROOT"
  else
    echo "  .claude/commands/ already exists — skipping"
  fi

  # Hook wrappers — project-relative scripts that resolve the platform path at
  # runtime via HITL_PLATFORM_ROOT, falling back to the path baked in at init time.
  local HOOKS_DIR="$TARGET_DIR/.hitl/hooks"
  if [[ ! -d "$HOOKS_DIR" ]]; then
    mkdir -p "$HOOKS_DIR"
    local DEFAULT_PLATFORM="$PLATFORM_ROOT"
    for hook in welcome check-hitl-context check-domain-boundary rebuild-graph \
                write-session-summary sync-step-to-issue; do
      cat > "$HOOKS_DIR/$hook.sh" <<WRAPPER
#!/usr/bin/env bash
exec bash "\${HITL_PLATFORM_ROOT:-$DEFAULT_PLATFORM}/ai/claude/hooks/$hook.sh" "\$@"
WRAPPER
      chmod 750 "$HOOKS_DIR/$hook.sh"
    done
    echo "✓ .hitl/hooks/ — wrappers resolving via HITL_PLATFORM_ROOT (default: $DEFAULT_PLATFORM)"
  else
    echo "  .hitl/hooks/ already exists — skipping"
  fi

  # Graphify knowledge graph support
  if [[ ! -f "$TARGET_DIR/.graphifyignore" && -f "$PLATFORM_ROOT/.graphifyignore" ]]; then
    cp "$PLATFORM_ROOT/.graphifyignore" "$TARGET_DIR/.graphifyignore"
    echo "✓ .graphifyignore"
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
    echo "✓ .mcp.json (Graphify MCP server — requires: pip install 'graphifyy[mcp]')"
  fi
}

# ---- Codex setup ----
# AGENTS.md and hook scripts are copied into the product repo because Codex
# has no plugin system — it reads AGENTS.md from the project root only.
# ai/codex/install.sh owns all Codex setup logic; delegate to avoid duplication.

setup_codex() {
  bash "$PLATFORM_ROOT/ai/codex/install.sh" "$TARGET_DIR"
}

# ---- Run selected setup ----

setup_tools
[[ "$TOOL" == "claude" || "$TOOL" == "both" ]] && setup_claude
[[ "$TOOL" == "codex"  || "$TOOL" == "both" ]] && setup_codex

# ---- Done ----

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit CLAUDE.md — add your project's coding standards"
[[ "$TOOL" == "codex" || "$TOOL" == "both" ]] && \
  echo "  2. Edit AGENTS.md — Codex reads this automatically (your copy, customize freely)"
echo "  3. Edit docs/system-manifest.yaml — document your domains and API boundaries"
echo ""
echo "To edit a skill, agent, or hook prompt:"
echo "  Platform: $PLATFORM_ROOT"
echo "  Guide:    $PLATFORM_ROOT/docs/customization-guide.md"
echo ""
echo "CI setup — set HITL_PLATFORM_ROOT before running Claude Code:"
echo "  export HITL_PLATFORM_ROOT=/path/to/your-platform-clone"
echo "  (or clone to the default: ~/tools/hitl-dev-platform)"
echo ""
