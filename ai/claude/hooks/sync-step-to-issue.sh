#!/usr/bin/env bash
# PostToolUse hook: post a GitHub issue comment when current_step advances.
# Fires on any Edit/Write tool call; exits silently if the file isn't the HITL context.
# Uses /tmp/hitl-last-step-<change_id> to detect advancement — skips duplicate posts.
# Non-blocking — never exits with a non-zero code that would surface to the user.

[[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently

set -uo pipefail

# Resolve a working Python interpreter (Windows-safe; see issue #14). $HITL_PY is set by the hook
# wrapper; otherwise probe. No usable Python → skip (this hook is advisory/non-blocking).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$SCRIPT_DIR/_steps.sh"
PY=$(hitl_python) || exit 0

HITL_FILE=".hitl/current-change.yaml"

INPUT=$(cat)

# Extract the written file path from the tool input JSON
FILE_PATH=$(export _INPUT="$INPUT"; "$PY" -c "
import json, os, sys
try:
    d = json.loads(os.environ.get('_INPUT', '{}'))
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" 2>/dev/null || true)

# Only act when the HITL context file itself was written
[[ "$FILE_PATH" != *"$HITL_FILE" && "$FILE_PATH" != "$HITL_FILE" ]] && exit 0
[[ ! -f "$HITL_FILE" ]] && exit 0

# Read fields — awk-only, no yaml parser dependency
CHANGE_ID=$(awk '/^change_id:/{print $2}' "$HITL_FILE" | tr -d '"')
TIER=$(awk '/^tier:/{print $2}' "$HITL_FILE" | tr -d '"')

# Parse current_step block
CS_BLOCK=$(awk '/^current_step:/{f=1;next} f && /^[^ ]/{exit} f{print}' "$HITL_FILE")
STEP_NUM=$(echo "$CS_BLOCK" | awk '/number:/{print $2}')
STEP_NAME=$(echo "$CS_BLOCK" | awk -F'"' '/name:/{print $2}')
PHASE=$(echo "$CS_BLOCK" | awk -F'"' '/phase:/{print $2}')

# Require a valid step number
[[ -z "$STEP_NUM" || ! "$STEP_NUM" =~ ^[0-9]+$ ]] && exit 0

# Skip placeholder change_id written before the GitHub issue is created
[[ "$CHANGE_ID" == "migration-setup" || -z "$CHANGE_ID" ]] && exit 0

# Extract numeric issue number from GH-N format
ISSUE_NUM="${CHANGE_ID#GH-}"
[[ "$ISSUE_NUM" == "$CHANGE_ID" || -z "$ISSUE_NUM" ]] && exit 0  # not GH-N format

# Step advancement check — only post when the step number actually increases
CACHE_FILE="${TMPDIR:-${TMP:-/tmp}}/hitl-last-step-${CHANGE_ID}"
LAST_STEP=0
[[ -f "$CACHE_FILE" ]] && LAST_STEP=$(cat "$CACHE_FILE" 2>/dev/null || echo 0)

# Exit without posting if step hasn't advanced
[[ "$STEP_NUM" -le "$LAST_STEP" ]] && exit 0

# Post comment — silently skip if gh is unavailable or the issue doesn't exist
if command -v gh &>/dev/null; then
    BODY="**HITL progress** | Step ${STEP_NUM}: ${STEP_NAME} | Phase: ${PHASE} | Tier: ${TIER}"
    gh issue comment "$ISSUE_NUM" --body "$BODY" &>/dev/null || true
fi

# Record the step we just posted so future edits at the same step are silent
echo "$STEP_NUM" > "$CACHE_FILE"

exit 0
