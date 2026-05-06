#!/usr/bin/env bash
# HITL status line for Claude Code
# Reads .hitl/current-change.yaml from the project root and emits a compact breadcrumb.

YAML_FILE="$(dirname "$0")/../.hitl/current-change.yaml"

# Exit silently if the file does not exist
[ -f "$YAML_FILE" ] || exit 0

# Extract fields with python3 (available on macOS without extra deps)
python3 - "$YAML_FILE" <<'PYEOF'
import sys, re

path = sys.argv[1]
with open(path) as f:
    text = f.read()

def get(key, text):
    m = re.search(r'^\s*' + key + r':\s*["\']?([^"\'\n]+)["\']?\s*$', text, re.MULTILINE)
    return m.group(1).strip() if m else ''

change_id = get('change_id', text)
tier       = get('tier', text)
phase      = get('phase', text)
number     = get('number', text)
name       = get('name', text)

if not (phase and number and name):
    sys.exit(0)

print(f"HITL: {phase} | Step {number}: {name} [{change_id} · T{tier}]")
PYEOF
