#!/usr/bin/env bash
# PostToolUse hook: check that edited files are within the approved manifest domain boundary.
# Handles Claude Code input (tool_name: Edit/Write, tool_input.file_path)
# and Codex input (tool_name: apply_patch, tool_input.command with patch text).
# Emits warnings — does not block.

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
    # Capture Add/Update/Delete paths, Rename destinations, and Move to destinations.
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

CONTEXT_FILE=".hitl/current-change.yaml"
if [[ ! -f "$CONTEXT_FILE" ]]; then
  exit 0  # context check handled by PreToolUse hook
fi

# Extract allowed_paths from context file
ALLOWED_PATHS=$(python3 - << 'PYEOF'
import sys, re

try:
    import yaml
    with open(".hitl/current-change.yaml") as f:
        data = yaml.safe_load(f)
    paths = data.get("allowed_paths", [])
    print("\n".join(paths))
except ImportError:
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
  exit 2
fi

if [[ -z "$ALLOWED_PATHS" ]]; then
  exit 0
fi

CHANGE_ID=$(grep "^change_id:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' || echo "unknown")

# Check each affected source file against allowed_paths
while IFS= read -r file; do
  case "$file" in
    *.py|*.ts|*.js|*.tsx|*.jsx|*.go|*.java|*.rb|*.rs|*.cpp|*.c|*.h) ;;
    *) continue ;;
  esac

  MATCHED=false
  while IFS= read -r pattern; do
    [[ -z "$pattern" ]] && continue
    case "$file" in
      $pattern) MATCHED=true; break ;;
    esac
    PATTERN_DIR="${pattern%%\**}"
    if [[ "$file" == "$PATTERN_DIR"* ]]; then
      MATCHED=true
      break
    fi
  done <<< "$ALLOWED_PATHS"

  if [[ "$MATCHED" == "false" ]]; then
    echo "HITL DOMAIN BOUNDARY WARNING:" >&2
    echo "  File edited: $file" >&2
    echo "  Change: $CHANGE_ID" >&2
    echo "  This file is outside the approved allowed_paths in .hitl/current-change.yaml" >&2
    echo "  Allowed paths:" >&2
    while IFS= read -r p; do echo "    - $p" >&2; done <<< "$ALLOWED_PATHS"
    echo "" >&2
    echo "  If intentional, update allowed_paths and confirm with the architect." >&2
  fi
done <<< "$AFFECTED_PATHS"

exit 0
