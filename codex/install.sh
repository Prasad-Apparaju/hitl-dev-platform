#!/usr/bin/env bash
# Install HITL enforcement git hooks and AGENTS.md for Codex CLI users.
#
# Usage:
#   bash /path/to/hitl-dev-platform/codex/install.sh [target-repo-path]
#
# If target-repo-path is omitted, installs into the current directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
  echo "AGENTS.md already exists at $AGENTS_DEST"
  echo "  Review $SCRIPT_DIR/AGENTS.md and merge manually."
else
  cp "$SCRIPT_DIR/AGENTS.md" "$AGENTS_DEST"
  echo "✓ Copied AGENTS.md to $TARGET_DIR"
fi

# --- Git hooks ---

for hook in pre-commit post-commit; do
  SRC="$SCRIPT_DIR/git-hooks/$hook"
  DEST="$HOOKS_DIR/$hook"

  if [[ -f "$DEST" ]]; then
    BACKUP="$DEST.hitl-backup"
    cp "$DEST" "$BACKUP"
    echo "  Backed up existing $hook to $hook.hitl-backup"
  fi

  cp "$SRC" "$DEST"
  chmod +x "$DEST"
  echo "✓ Installed $hook hook"
done

# --- codex/scripts in target ---

mkdir -p "$TARGET_DIR/codex/scripts"
cp "$SCRIPT_DIR/scripts/hitl-conventions.sh" "$TARGET_DIR/codex/scripts/hitl-conventions.sh"
chmod +x "$TARGET_DIR/codex/scripts/hitl-conventions.sh"
echo "✓ Copied codex/scripts/hitl-conventions.sh"

echo ""
echo "Setup complete. Next steps:"
echo ""
echo "  1. Edit AGENTS.md — add your project's coding standards and conventions"
echo "     (look for the placeholder sections in the file)"
echo ""
echo "  2. Create your system manifest if you don't have one:"
echo "     cp /path/to/hitl-dev-platform/templates/system-manifest.yaml.template docs/system-manifest.yaml"
echo ""
echo "  3. Start a change:"
echo "     codex 'Initialize HITL context for GH-42: add user notifications'"
echo ""
echo "  4. Before your first PR, run convention checks:"
echo "     bash codex/scripts/hitl-conventions.sh"
echo ""
