#!/usr/bin/env bash
# PostToolUse hook: check that edited files are within the approved manifest domain boundary.
# Runs after Write/Edit tool calls. Emits warnings to the conversation — does not block.

set -euo pipefail

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Only check Edit/Write
if [[ "$TOOL" != "Edit" && "$TOOL" != "Write" ]]; then
  exit 0
fi

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

CONTEXT_FILE=".hitl/current-change.yaml"
if [[ ! -f "$CONTEXT_FILE" ]]; then
  exit 0  # context check is handled by PreToolUse hook
fi

# Extract allowed_paths from context file using grep — no PyYAML dependency
# Reads the allowed_paths block as lines indented under the key
ALLOWED_PATHS=$(python3 - << 'PYEOF'
import sys, re

try:
    import yaml
    with open(".hitl/current-change.yaml") as f:
        data = yaml.safe_load(f)
    paths = data.get("allowed_paths", [])
    print("\n".join(paths))
except ImportError:
    # PyYAML not installed — fall back to line-by-line grep
    in_block = False
    with open(".hitl/current-change.yaml") as f:
        for line in f:
            if line.startswith("allowed_paths:"):
                in_block = True
                continue
            if in_block:
                m = re.match(r"^\s+-\s+(.+)", line)
                if m:
                    print(m.group(1).strip())
                elif line and not line[0].isspace():
                    break
except Exception as e:
    print(f"HITL_PARSE_ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)

PYEXIT=$?
if [[ $PYEXIT -ne 0 ]]; then
  echo "HITL BOUNDARY CHECK ERROR: failed to parse .hitl/current-change.yaml" >&2
  echo "  Boundary enforcement is disabled for this edit." >&2
  echo "  Fix the context file and re-run to restore enforcement." >&2
  exit 0  # warn but don't block on parse failure
fi

if [[ -z "$ALLOWED_PATHS" ]]; then
  exit 0  # no allowed_paths configured — skip check
fi

# Check if the edited file matches any allowed path pattern
MATCHED=false
while IFS= read -r pattern; do
  [[ -z "$pattern" ]] && continue
  # Simple glob matching: replace ** with wildcard
  case "$FILE_PATH" in
    $pattern) MATCHED=true; break ;;
  esac
  # Also check prefix match for directories
  PATTERN_DIR="${pattern%%\**}"
  if [[ "$FILE_PATH" == "$PATTERN_DIR"* ]]; then
    MATCHED=true
    break
  fi
done <<< "$ALLOWED_PATHS"

if [[ "$MATCHED" == "false" ]]; then
  CHANGE_ID=$(grep "^change_id:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' || echo "unknown")
  echo "HITL DOMAIN BOUNDARY WARNING:" >&2
  echo "  File edited: $FILE_PATH" >&2
  echo "  Change: $CHANGE_ID" >&2
  echo "  This file is outside the approved allowed_paths in .hitl/current-change.yaml" >&2
  echo "  Allowed paths:" >&2
  while IFS= read -r p; do echo "    - $p" >&2; done <<< "$ALLOWED_PATHS"
  echo "" >&2
  echo "  If this edit is intentional, update allowed_paths in the context file and" >&2
  echo "  confirm with the architect that the domain boundary expansion is approved." >&2
fi

exit 0
