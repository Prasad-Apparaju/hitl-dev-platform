#!/usr/bin/env bash
# Stop hook: generate a HITL session summary when Claude Code finishes a session.
# Lists artifacts changed, evidence collected, and missing evidence.

set -euo pipefail

CONTEXT_FILE=".hitl/current-change.yaml"
if [[ ! -f "$CONTEXT_FILE" ]]; then
  exit 0  # no active change — nothing to summarize
fi

CHANGE_ID=$(grep "^change_id:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' 2>/dev/null || echo "unknown")
STATUS=$(grep "^status:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' 2>/dev/null || echo "unknown")
TIER=$(grep "^tier:" "$CONTEXT_FILE" | awk '{print $2}' | tr -d '"' 2>/dev/null || echo "unknown")

# Get changed files from git
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")
STAGED_FILES=$(git diff --name-only --cached 2>/dev/null || echo "")
ALL_CHANGED=$(echo -e "$CHANGED_FILES\n$STAGED_FILES" | sort -u | grep -v '^$' || echo "")

# Get required evidence from context file
REQUIRED_EVIDENCE=$(python3 - << 'PYEOF'
import yaml
try:
    with open(".hitl/current-change.yaml") as f:
        data = yaml.safe_load(f)
    ev = data.get("required_evidence", [])
    print("\n".join(ev) if ev else "none specified")
except Exception:
    print("error reading context file")
PYEOF
)

SUMMARY_DIR="docs/session-logs"
mkdir -p "$SUMMARY_DIR"
TIMESTAMP=$(date +"%Y-%m-%d-%H%M%S")
SUMMARY_FILE="$SUMMARY_DIR/hitl-session-${CHANGE_ID}-${TIMESTAMP}.md"

cat > "$SUMMARY_FILE" << SUMMARY
# HITL Session Summary

- **Change:** $CHANGE_ID
- **Tier:** $TIER
- **Status at session end:** $STATUS
- **Timestamp:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Files Changed This Session

$(if [[ -n "$ALL_CHANGED" ]]; then echo "$ALL_CHANGED" | sed 's/^/- /'; else echo "_No tracked changes detected._"; fi)

## Required Evidence Status

$(echo "$REQUIRED_EVIDENCE" | sed 's/^/- [ ] /')

## Next Steps

Review the evidence checklist above and ensure all required items are complete before creating the PR.

Run \`/check-conventions\` to verify code quality before PR creation.

SUMMARY

echo "" >&2
echo "HITL Session Summary written to: $SUMMARY_FILE" >&2

exit 0
