#!/usr/bin/env bash
# PreToolUse hook: verify HITL context file exists before source code edits.
# Handles Claude Code input (tool_name: Edit/Write, tool_input.file_path)
# and Codex input (tool_name: apply_patch, tool_input.command with patch text).
# Exits 2 to block the tool call; exits 0 to allow.

[[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently

set -euo pipefail

INPUT=$(cat)

# Extract affected file paths from hook input — supports both input shapes.
# JSON is passed via env var so the heredoc can provide the Python script via stdin.
AFFECTED_PATHS=$(export _HITL_HOOK_INPUT="$INPUT"; python3 << 'PYEOF' 2>/dev/null
import sys, json, re, os

try:
    data = json.loads(os.environ.get("_HITL_HOOK_INPUT", "{}"))
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")
paths = []

if tool in ("Edit", "Write"):
    fp = data.get("tool_input", {}).get("file_path", "")
    if fp:
        paths.append(fp)
elif tool == "apply_patch":
    cmd = data.get("tool_input", {}).get("command", "")
    # Patch headers: *** Add/Update/Delete File: path
    # *** Rename File: old => new  (capture new name)
    # *** Move to: new-path  (destination of an Update File + Move to pair)
    pattern = r'^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Rename File: .+ => (.+)$|^\*\*\* Move to: (.+)$'
    for m in re.finditer(pattern, cmd, re.MULTILINE):
        p = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if p:
            paths.append(p)

print("\n".join(paths))
PYEOF
)

if [[ -z "$AFFECTED_PATHS" ]]; then
  exit 0
fi

# Check if any affected path is a source file
SOURCE_FILE_FOUND=false
while IFS= read -r file; do
  case "$file" in
    *.py|*.ts|*.js|*.tsx|*.jsx|*.go|*.java|*.rb|*.rs|*.cpp|*.c|*.h)
      SOURCE_FILE_FOUND=true
      break
      ;;
  esac
done <<< "$AFFECTED_PATHS"

if [[ "$SOURCE_FILE_FOUND" == "false" ]]; then
  exit 0
fi

# Check for HITL context file
CONTEXT_FILE=".hitl/current-change.yaml"
if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "HITL CONTEXT MISSING: No .hitl/current-change.yaml found." >&2
  echo "Before editing source code, initialize the change context:" >&2
  echo "  Codex: run the Change Initialization workflow in AGENTS.md" >&2
  echo "  Claude Code: /hitl:apply-change [issue-number] [description]" >&2
  echo "This creates the required context file and verifies source artifacts exist." >&2
  exit 2
fi

# Verify required fields are present
REQUIRED_FIELDS=("change_id" "tier" "status" "manifest")
for field in "${REQUIRED_FIELDS[@]}"; do
  if ! grep -q "^${field}:" "$CONTEXT_FILE" 2>/dev/null; then
    echo "HITL CONTEXT INCOMPLETE: .hitl/current-change.yaml is missing required field: ${field}" >&2
    echo "Re-run the Change Initialization workflow to regenerate the context file." >&2
    exit 2
  fi
done

# Block source code edits unless the design has been approved.
# Only these statuses permit writing source files:
STATUS=$(grep "^status:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' || echo "unknown")
ALLOWED_STATUSES=("implementation-approved" "conformance-review-pending" "qa-review-pending" "pr-ready" "merged")

ALLOWED=false
for s in "${ALLOWED_STATUSES[@]}"; do
  if [[ "$STATUS" == "$s" ]]; then
    ALLOWED=true
    break
  fi
done

if [[ "$ALLOWED" == "false" ]]; then
  echo "HITL BLOCKED: status '${STATUS}' does not permit source code edits." >&2
  echo "Design approval is required before writing implementation code." >&2
  echo "  • If design is in progress: wait for the architect to reach the next gate." >&2
  echo "  • If a gate is awaiting review: run /hitl:ta-approve to advance it." >&2
  echo "  • If status is 'blocked': resolve the finding in .hitl/current-change.yaml first." >&2
  exit 2
fi

exit 0
