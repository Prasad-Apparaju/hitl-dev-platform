#!/usr/bin/env bash
# PreToolUse hook: verify HITL context file exists before source code edits
# Runs before Write/Edit tool calls that target source files.
# Exits 2 to block the tool call with a message; exits 0 to allow it.

set -euo pipefail

# Read tool input from stdin (Claude Code passes JSON: {"tool_name": "...", "tool_input": {...}})
INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Only check Edit/Write tools
if [[ "$TOOL" != "Edit" && "$TOOL" != "Write" ]]; then
  exit 0
fi

# Only check source code paths (not docs, not .hitl itself, not tests setup)
if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Skip docs, config, templates, hooks, .hitl itself
SKIP_PATTERNS=("docs/" ".hitl/" "templates/" "hooks/" ".claude/" ".github/" "*.md" "*.yaml" "*.yml" "*.json" "*.sh" "*.toml" "*.cfg" "*.ini")
for pattern in "${SKIP_PATTERNS[@]}"; do
  case "$FILE_PATH" in
    $pattern) exit 0 ;;
    */$pattern) exit 0 ;;
  esac
done

# Source code patterns: .py, .ts, .js, .go, .java, .rb, .rs, .cpp, .c, .h, .tsx, .jsx
case "$FILE_PATH" in
  *.py|*.ts|*.js|*.tsx|*.jsx|*.go|*.java|*.rb|*.rs|*.cpp|*.c|*.h)
    ;;  # fall through to check
  *)
    exit 0  # not a source file we care about
    ;;
esac

# Check for HITL context file
CONTEXT_FILE=".hitl/current-change.yaml"
if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "HITL CONTEXT MISSING: No .hitl/current-change.yaml found." >&2
  echo "Before editing source code, initialize the change context:" >&2
  echo "  Run: /apply-change [issue-number] [description]" >&2
  echo "This creates the required context file and verifies source artifacts exist." >&2
  exit 2
fi

# Verify required fields are present
REQUIRED_FIELDS=("change_id" "tier" "status" "manifest")
for field in "${REQUIRED_FIELDS[@]}"; do
  if ! grep -q "^${field}:" "$CONTEXT_FILE" 2>/dev/null; then
    echo "HITL CONTEXT INCOMPLETE: .hitl/current-change.yaml is missing required field: ${field}" >&2
    echo "Re-run /apply-change to regenerate the context file." >&2
    exit 2
  fi
done

# Check status — warn if not implementation-approved for source edits
STATUS=$(grep "^status:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' || echo "unknown")
if [[ "$STATUS" == "planning" || "$STATUS" == "design-review" ]]; then
  echo "HITL WARNING: Change status is '${STATUS}' — design approval is pending." >&2
  echo "Source code edits before design approval are recorded but not blocked." >&2
  echo "Ensure LLD is approved before requesting code review." >&2
  # Exit 0 to warn but not block (hooks exit 2 to block)
fi

exit 0
