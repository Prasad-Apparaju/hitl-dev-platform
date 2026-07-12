#!/usr/bin/env bash
# PreToolUse hook: enforce HITL change intake before edits.
# Handles Claude Code input (tool_name: Edit/Write, tool_input.file_path)
# and Codex input (tool_name: apply_patch, tool_input.command with patch text).
# Exits 2 to block the tool call; exits 0 to allow.
#
# Gate layers (least → most permissive):
#   1. No active change for this branch → block ALL edits (except .hitl/ and .claude/ bootstrap
#      paths) until the user picks an issue + workflow via /hitl:dev-start-change. This is the
#      hard wall behind the per-turn intake directive — chatting can't bypass it into doing work.
#   2. Branch ↔ change mismatch → block ALL edits until realigned (issue #12).
#   3. Source-code edits additionally require an approved design status (unchanged) — docs and
#      design artifacts stay writable during the design phase.

[[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh"

# Resolve a working Python interpreter (Windows-safe; see issue #14). $HITL_PY is set by the hook
# wrapper; otherwise probe. No usable Python → skip path-extraction (fails open, as before).
PY=$(hitl_python) || exit 0

INPUT=$(cat)

# Extract affected file paths from hook input — supports both input shapes.
# JSON is passed via env var so the heredoc can provide the Python script via stdin.
AFFECTED_PATHS=$(export _HITL_HOOK_INPUT="$INPUT"; "$PY" << 'PYEOF' 2>/dev/null
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

# Normalize to project-relative paths (issue #20). Claude Code sends file_path ABSOLUTE, so
# without this the .hitl/.claude bootstrap exemption never matches and files outside the
# project (scratchpads, user-level config) get gated as if they were project source.
# realpath on both sides resolves symlinks (e.g. macOS /tmp -> /private/tmp) so containment
# checks compare like with like. Paths that resolve outside the project are dropped: HITL
# governs this project's files only.
root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
resolved = []
for p in paths:
    if os.path.isabs(p):
        try:
            rel = os.path.relpath(os.path.realpath(p), root)
        except ValueError:
            continue  # different drive (Windows) — outside the project
    else:
        rel = os.path.normpath(p)
    if rel == ".." or rel.startswith(".." + os.sep):
        continue  # outside the project
    resolved.append(rel.replace(os.sep, "/"))

print("\n".join(resolved))
PYEOF
)

if [[ -z "$AFFECTED_PATHS" ]]; then
  exit 0
fi

# Bootstrap exemption: edits under .hitl/ and .claude/ are always allowed so that the change
# file, hooks, and settings can be written to *create* a change (otherwise intake itself, and
# onboarding, would be blocked — chicken-and-egg). Classify the affected paths.
GUARDED_FOUND=false       # any path that is NOT a bootstrap path
SOURCE_FILE_FOUND=false   # any guarded path that is source code
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  # Normalize a leading ./
  rel="${file#./}"
  case "$rel" in
    .hitl/*|.claude/*) continue ;;   # bootstrap path — exempt
  esac
  GUARDED_FOUND=true
  case "$rel" in
    *.py|*.ts|*.js|*.tsx|*.jsx|*.go|*.java|*.rb|*.rs|*.cpp|*.c|*.h)
      SOURCE_FILE_FOUND=true
      ;;
  esac
done <<< "$AFFECTED_PATHS"

# Only bootstrap paths touched → always allow.
if [[ "$GUARDED_FOUND" == "false" ]]; then
  exit 0
fi

CONTEXT_FILE=".hitl/current-change.yaml"

# ── Layer 1: no active change → block all guarded edits ───────────────────────────────────────
if ! hitl_change_active "$CONTEXT_FILE"; then
  echo "HITL BLOCKED: no active change for this project/branch." >&2
  echo "You must select an issue and workflow before editing files." >&2
  echo "  Claude Code: run /hitl:dev-start-change" >&2
  echo "  Codex:       run the Change Initialization workflow in AGENTS.md" >&2
  echo "(Edits under .hitl/ and .claude/ are exempt so intake can write the change file.)" >&2
  exit 2
fi

# Verify required fields are present (file is active but may be malformed/partial).
REQUIRED_FIELDS=("change_id" "tier" "status")
for field in "${REQUIRED_FIELDS[@]}"; do
  if ! grep -q "^${field}:" "$CONTEXT_FILE" 2>/dev/null; then
    echo "HITL CONTEXT INCOMPLETE: .hitl/current-change.yaml is missing required field: ${field}" >&2
    echo "Re-run the change initialization / start workflow to regenerate the context file." >&2
    exit 2
  fi
done

# ── Layer 2: branch ↔ change mismatch → block all guarded edits (issue #12) ───────────────────
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [[ "$(hitl_branch_reconcile "$CONTEXT_FILE" "$CURRENT_BRANCH")" == "mismatch" ]]; then
  CHANGE_ID=$(hitl_scalar "$CONTEXT_FILE" change_id)
  echo "HITL CONTEXT MISMATCH: branch '${CURRENT_BRANCH}' does not match active change ${CHANGE_ID}." >&2
  echo "All edits are blocked until the context is realigned." >&2
  echo "  • Run /hitl:dev-switch-context to reload context for this branch." >&2
  echo "  • Or run /hitl:dev-start-change to select the correct change." >&2
  exit 2
fi

# ── Layer 3: source-code edits require an approved design status (unchanged) ───────────────────
# Docs and design artifacts remain writable during design; only source code is gated on approval.
if [[ "$SOURCE_FILE_FOUND" == "true" ]]; then
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
fi

exit 0
