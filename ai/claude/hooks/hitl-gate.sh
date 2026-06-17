#!/usr/bin/env bash
# SessionStart hook: HITL change-intake gate.
# Fires once when a Claude Code session starts. If this is a HITL project but no change is
# active for the current branch, it injects the mandatory intake directive so the very first
# thing the session does is take the user through issue-selection → workflow classification →
# step plan → write+push current-change.yaml. The UserPromptSubmit hook (welcome.sh) re-injects
# the same directive every turn until a change is active, and check-hitl-context.sh hard-blocks
# edits in the meantime — together that is the enforceable equivalent of "you must pick a
# workflow before doing any work."
#
# Wire up in .claude/settings.json:
#   "SessionStart": [{ "hooks": [{ "type": "command",
#     "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/hitl-gate.sh\"" }] }]

[[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh"

HITL_FILE=".hitl/current-change.yaml"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

# No active change at all → force intake.
if ! hitl_change_active "$HITL_FILE"; then
  hitl_intake_directive
  exit 0
fi

# Active change, but it belongs to a different branch (inherited current-change.yaml, issue #12)
# → warn that the session is about to operate under the wrong change and must realign first.
if [[ "$(hitl_branch_reconcile "$HITL_FILE" "$CURRENT_BRANCH")" == "mismatch" ]]; then
  change_id=$(hitl_scalar "$HITL_FILE" change_id)
  cat <<DIRECTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️  HITL — BRANCH ↔ CHANGE MISMATCH

  Git branch        : ${CURRENT_BRANCH}
  Active change     : ${change_id}  (.hitl/current-change.yaml)

  This branch is operating under a change that doesn't match it — the change
  file was likely inherited from another branch. Source edits are blocked until
  this is realigned. Do NOT trust prior analysis in context.

  Resolve before doing any work:
    • /hitl:dev-switch-context     reload context for this branch's issue
    • /hitl:dev-start-change       select the correct change for this branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIRECTIVE
  exit 0
fi

exit 0
