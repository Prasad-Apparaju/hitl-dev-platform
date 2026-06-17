#!/usr/bin/env bash
# UserPromptSubmit hook: HITL status banner.
# - No active change for this branch → inject the mandatory intake directive (forces change
#   selection before any work; see hitl-gate.sh for the SessionStart counterpart).
# - Active change → show the breadcrumb (header + windowed step trail) on every prompt,
#   driven entirely by the self-describing `workflow` block in current-change.yaml.
# - Branch ↔ change mismatch (issue #12) → append a warning marker.
#
# The step model is NEVER hardcoded here — it is read from the change file via _steps.sh, so
# this banner and the persistent status line (statusline-hitl.sh) can never drift.

[[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently

# Source .env if present — makes LLM keys (e.g. for Graphify) available without manual export.
if [[ -f ".env" ]]; then
  set -a; source ".env"; set +a
fi

# Shared parser/rendering library (lives beside this script in both source and plugin layouts).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh"

HITL_FILE=".hitl/current-change.yaml"
SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

# ── No active change → force intake (the "you must pick an issue + workflow" gate) ─────────────
if ! hitl_change_active "$HITL_FILE"; then
  hitl_intake_directive
  exit 0
fi

# ── Active change → render the breadcrumb from the embedded workflow block ─────────────────────
# Header fields. change_id/tier are top-level; the human-readable step name + phase come from
# the current_step compat pointer; the step number/total/trail come from the embedded block.
change_id=$(hitl_scalar "$HITL_FILE" change_id)
tier=$(hitl_scalar "$HITL_FILE" tier)
cs_block=$(awk '/^current_step:/{f=1;next} f && /^[^ ]/{exit} f{print}' "$HITL_FILE")
step_name=$(echo "$cs_block" | awk -F'"' '/name:/{print $2}')
phase=$(echo "$cs_block"     | awk -F'"' '/phase:/{print $2}')

# Branch reconciliation marker (issue #12).
warn=""
case "$(hitl_branch_reconcile "$HITL_FILE" "$CURRENT_BRANCH")" in
  mismatch)     warn="   ⚠ branch=${CURRENT_BRANCH} ≠ ${change_id} — context may be stale; run /hitl:dev-switch-context" ;;
  unverifiable) warn="   ⚠ branch=${CURRENT_BRANCH} (can't verify against ${change_id})" ;;
esac

echo "$SEP"
if hitl_has_workflow "$HITL_FILE"; then
  wf=$(hitl_workflow_field "$HITL_FILE" id)
  cur=$(hitl_current_n "$HITL_FILE")
  total=$(hitl_total "$HITL_FILE")
  [[ -z "$step_name" ]] && step_name=$(hitl_current_label "$HITL_FILE")
  printf "  HITL — %s  •  Step %s / %s: %s\n" "${phase:-$wf}" "${cur:-?}" "${total:-?}" "$step_name"
  printf "  change: %s  •  tier: %s  •  workflow: %s\n" "$change_id" "${tier:-?}" "$wf"
  [[ -n "$warn" ]] && echo "$warn"
  echo ""
  printf "  %s\n" "$(hitl_render_trail "$HITL_FILE")"
else
  # Back-compat: pre-v2 file with a bare current_step and no embedded workflow block.
  num=$(echo "$cs_block" | awk '/number:/{print $2}')
  printf "  HITL — %s  •  Step %s: %s\n" "${phase:-change}" "${num:-?}" "$step_name"
  printf "  change: %s  •  tier: %s\n" "$change_id" "${tier:-?}"
  [[ -n "$warn" ]] && echo "$warn"
  echo ""
  echo "  (step trail unavailable — run /hitl:dev-update to migrate this change to the"
  echo "   self-describing workflow format)"
fi
echo "$SEP"
exit 0
