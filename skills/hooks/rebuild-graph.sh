#!/usr/bin/env bash
# PostToolUse hook: incrementally rebuild the Graphify knowledge graph after design doc writes.
# Skips silently if graphify is not installed or no graph has been built yet.
# Handles both Claude Code input (tool_name: Edit/Write) and Codex apply_patch input.

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(export _HITL_HOOK_INPUT="$INPUT"; python3 << 'PYEOF' 2>/dev/null
import json, os, sys, re

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
    pattern = r'^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Rename File: .+ => (.+)$|^\*\*\* Move to: (.+)$'
    for m in re.finditer(pattern, cmd, re.MULTILINE):
        p = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if p:
            paths.append(p)

# Return first doc path found
for p in paths:
    if p.startswith("docs/"):
        print(p)
        break
PYEOF
)

# Only trigger on design doc writes
[[ -n "$FILE_PATH" ]] || exit 0
[[ "$FILE_PATH" == docs/* ]] || exit 0

# Skip silently if graphify is not installed or no graph has been built yet
command -v graphify &>/dev/null || exit 0
[[ -d "graphify-out" ]] || exit 0

# Incremental rebuild — only reprocesses changed files via SHA256 cache
echo "HITL GRAPH: Rebuilding knowledge graph for $FILE_PATH (background) ..." >&2
graphify . --update --no-viz --directed >/dev/null 2>&1 &
echo "HITL GRAPH: Graph rebuild started (PID $!). Query after a moment or run 'graphify check-update docs/' to verify." >&2

exit 0
