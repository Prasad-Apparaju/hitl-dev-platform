#!/usr/bin/env bash
# Bootstrap a new product repository with HITL enforcement.
#
# Usage:
#   bash /path/to/hitl-dev-platform/scripts/init-project.sh <target-dir> [options]
#
# Options:
#   --tool  claude|codex|both   AI tool to configure (default: both)
#   --name  <project-name>      Project name for CLAUDE.md header (default: dirname)
#
# Recommended setup:
#   git clone https://github.com/your-org/hitl-dev-platform ~/tools/hitl-dev-platform
#   bash ~/tools/hitl-dev-platform/scripts/init-project.sh ~/code/my-product
#
# Claude Code: skills, agents, and hooks are referenced from the shared platform —
#              nothing is copied into the product repo.
# Codex:       AGENTS.md and hook scripts are copied into the product repo
#              (Codex has no plugin system; files must live in the project root).
#
# CI note: Claude Code hooks use absolute paths to the platform. On CI machines,
#          clone the platform to the same path before running Claude Code:
#          git clone https://github.com/your-org/hitl-dev-platform ~/tools/hitl-dev-platform

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---- Argument parsing ----

TOOL="both"
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

if [[ ! "$TOOL" =~ ^(claude|codex|both)$ ]]; then
  echo "ERROR: --tool must be claude, codex, or both" >&2
  exit 1
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
  TMPL="$PLATFORM_ROOT/skills/generate-docs/templates/CLAUDE.md.template"
  if [[ -f "$TMPL" ]]; then
    cp "$TMPL" "$CLAUDE_DEST"
    echo "✓ CLAUDE.md — edit this to add your project's coding standards and conventions"
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

MANIFEST_DEST="$TARGET_DIR/docs/system-manifest.yaml"
if [[ ! -f "$MANIFEST_DEST" ]]; then
  MANIFEST_TMPL="$PLATFORM_ROOT/templates/system-manifest-template.yaml"
  if [[ -f "$MANIFEST_TMPL" ]]; then
    cp "$MANIFEST_TMPL" "$MANIFEST_DEST"
    echo "✓ docs/system-manifest.yaml — fill in your domains and API boundaries"
  fi
fi

# ---- Claude Code setup ----
# Skills, agents, and hooks are referenced from the shared platform via the plugin
# path. No platform files are copied into the product repo.

setup_claude() {
  mkdir -p "$TARGET_DIR/.claude"
  local SETTINGS="$TARGET_DIR/.claude/settings.json"

  if [[ -f "$SETTINGS" ]]; then
    echo "  .claude/settings.json already exists — add plugin entry manually:"
    echo "    \"plugins\": [\"$PLATFORM_ROOT/.claude-plugin/plugin.json\"]"
    return
  fi

  # Hooks use absolute paths so they resolve correctly regardless of the
  # product repo's working directory.
  cat > "$SETTINGS" <<JSON
{
  "plugins": ["$PLATFORM_ROOT/.claude-plugin/plugin.json"],
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$PLATFORM_ROOT/hooks/check-hitl-context.sh\""
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
            "command": "bash \"$PLATFORM_ROOT/hooks/check-domain-boundary.sh\""
          },
          {
            "type": "command",
            "command": "bash \"$PLATFORM_ROOT/hooks/rebuild-graph.sh\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$PLATFORM_ROOT/hooks/write-session-summary.sh\""
          }
        ]
      }
    ]
  }
}
JSON
  echo "✓ .claude/settings.json (plugin + hooks → platform at $PLATFORM_ROOT)"
}

# ---- Codex setup ----
# AGENTS.md and hook scripts are copied into the product repo because Codex
# has no plugin system — it reads AGENTS.md from the project root only.
# The existing codex/install.sh handles all Codex setup; we delegate to it.

setup_codex() {
  bash "$PLATFORM_ROOT/codex/install.sh" "$TARGET_DIR"
}

# ---- Run selected setup ----

[[ "$TOOL" == "claude" || "$TOOL" == "both" ]] && setup_claude
[[ "$TOOL" == "codex"  || "$TOOL" == "both" ]] && setup_codex

# ---- Done ----

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit CLAUDE.md — add your project's coding standards and conventions"
if [[ "$TOOL" == "codex" || "$TOOL" == "both" ]]; then
  echo "  2. Edit AGENTS.md — Codex reads this automatically (it's your copy, customize freely)"
fi
echo "  3. Edit docs/system-manifest.yaml — document your domains and API boundaries"
echo ""
echo "To edit a skill, agent, or hook prompt:"
echo "  Platform: $PLATFORM_ROOT"
echo "  Guide:    $PLATFORM_ROOT/docs/customization-guide.md"
echo ""
if [[ "$TOOL" == "claude" || "$TOOL" == "both" ]]; then
  echo "CI setup — Claude Code hooks need the platform available on CI machines:"
  echo "  Add a setup step: git clone <your-fork-url> $PLATFORM_ROOT"
  echo ""
fi
