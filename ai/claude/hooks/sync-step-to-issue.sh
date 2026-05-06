#!/usr/bin/env bash
# PostToolUse hook: post a GitHub issue comment whenever current_step advances.
# Fires on any Edit/Write tool call; exits silently if the file isn't the HITL context.
# Non-blocking — never exits with a non-zero code that would surface to the user.

set -uo pipefail

HITL_FILE=".hitl/current-change.yaml"

INPUT=$(cat)

# Extract the written file path from the tool input JSON
FILE_PATH=$(export _INPUT="$INPUT"; python3 -c "
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

# Post comment — silently skip if gh is unavailable or the issue doesn't exist
if command -v gh &>/dev/null; then
    BODY="**HITL progress** | Step ${STEP_NUM}: ${STEP_NAME} | Phase: ${PHASE} | Tier: ${TIER}"
    gh issue comment "$ISSUE_NUM" --body "$BODY" &>/dev/null || true
fi

exit 0
