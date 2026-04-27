#!/usr/bin/env bash
# Stop hook — appends a session entry to docs/session-logs/all-sessions.md
# Fires automatically when Claude finishes a response.
# The entry is minimal (timestamp + branch). The developer fills in details.

set -euo pipefail

LOG_DIR="docs/session-logs"
LOG_FILE="$LOG_DIR/all-sessions.md"
DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H:%M")
BRANCH=$(git branch --show-current 2>/dev/null || echo "no-branch")

mkdir -p "$LOG_DIR"

if [ ! -f "$LOG_FILE" ]; then
  echo "# Session Log" > "$LOG_FILE"
  echo "" >> "$LOG_FILE"
fi

echo "- $DATE $TIME | branch: $BRANCH" >> "$LOG_FILE"
