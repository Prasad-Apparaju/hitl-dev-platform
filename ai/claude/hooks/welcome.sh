#!/usr/bin/env bash
# UserPromptSubmit hook: HITL status banner.
# When a change is in progress with a known current_step: shows breadcrumbs every prompt.
# Otherwise: shows the static startup menu once per session.

[[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently

# Source .env if present — makes LLM keys (e.g. for Graphify) available without manual export.
if [[ -f ".env" ]]; then
  set -a; source ".env"; set +a
fi

HITL_FILE=".hitl/current-change.yaml"
SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Abbreviated step names (indices 1–32; 19a handled as substep of 19)
NAMES=("" "Issue" "Figma" "Impact" "ROI" "Docs" "IaC" "Tests" "Train" "Packet"
       "RED" "TstRvw" "Dsn+" "VfyRED" "GREEN" "VfyGRN" "Refact"
       "Conv" "Rvw1" "Rvw2" "Rerun" "Recncl" "QAVfy" "ImpBrf"
       "Rollout" "VfyPR" "IntVfy" "Figma2" "Deploy" "Promote" "Pentest" "30dROI" "90dROI")

show_breadcrumbs() {
  # Parse current_step block from the YAML (controlled schema, no full parser needed)
  local cs_block
  cs_block=$(awk '/^current_step:/{f=1;next} f && /^[^ ]/{exit} f{print}' "$HITL_FILE")

  local step_num step_name phase change_id tier substep
  step_num=$(echo "$cs_block"  | awk '/number:/{print $2}')
  step_name=$(echo "$cs_block" | awk -F'"' '/name:/{print $2}')
  phase=$(echo "$cs_block"     | awk -F'"' '/phase:/{print $2}')
  substep=$(echo "$cs_block"   | awk -F'"' '/substep:/{print $2}')
  change_id=$(awk '/^change_id:/{print $2}' "$HITL_FILE")
  tier=$(awk '/^tier:/{print $2}' "$HITL_FILE")

  # Validate — fall through to static menu if step_num is missing
  [[ -z "$step_num" || ! "$step_num" =~ ^[0-9]+$ ]] && return 1

  # Compute display step (e.g. "19a" when substep is set)
  local display_step="${step_num}"
  [[ -n "$substep" ]] && display_step="${step_num}${substep}"

  # Build trail: show a window of 7 steps centred on current step (3 back + current + 3 ahead)
  local win_start=$(( step_num - 3 )); (( win_start < 1  )) && win_start=1
  local win_end=$(( step_num + 3 ));   (( win_end  > 32 )) && win_end=32

  local trail=""
  (( win_start > 1 )) && trail="… "
  for (( i=win_start; i<=win_end; i++ )); do
    local name="${NAMES[$i]}"
    if [[ -n "$substep" && "$i" -eq "$step_num" ]]; then
      # Parent step is done; substep is current
      trail+="✓${i}.${name} ▶${display_step}.ArchRvw "
    elif (( i <  step_num )); then trail+="✓${i}.${name} "
    elif (( i == step_num )); then trail+="▶${i}.${name} "
    else                           trail+="·${i}.${name} "
    fi
  done
  (( win_end < 32 )) && trail+="…"

  echo "$SEP"
  printf "  HITL — %s  •  Step %s / 32: %s\n" "$phase" "$display_step" "$step_name"
  printf "  change: %s  •  tier: %s\n"         "$change_id" "$tier"
  echo  ""
  printf "  %s\n" "$trail"
  echo "$SEP"
  return 0
}

# Branch / change_id mismatch check — inject warning into model context on every prompt.
# This surfaces the stale-context problem even when check-hitl-context doesn't fire
# (e.g. the user asks a question rather than triggering an Edit/Write).
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
BRANCH_ISSUE=$(echo "$CURRENT_BRANCH" | sed -n 's|issue/\([0-9]*\)-.*|\1|p')
if [[ -f "$HITL_FILE" && -n "$BRANCH_ISSUE" ]]; then
  YAML_CHANGE_ID=$(grep "^change_id:" "$HITL_FILE" | awk '{print $2}' | tr -d '"' || echo "")
  YAML_ISSUE=$(echo "$YAML_CHANGE_ID" | sed -n 's|GH-\([0-9]*\)|\1|p')
  if [[ -n "$YAML_ISSUE" && "$BRANCH_ISSUE" != "$YAML_ISSUE" ]]; then
    echo "$SEP"
    echo "  ⚠️  HITL CONTEXT MISMATCH"
    echo ""
    echo "  Git branch : $CURRENT_BRANCH  (issue #$BRANCH_ISSUE)"
    echo "  YAML       : $YAML_CHANGE_ID  (issue #$YAML_ISSUE)"
    echo ""
    echo "  The branch and HITL context are out of sync."
    echo "  Source edits are blocked. Claude's context may contain stale data"
    echo "  from the previous issue — do not rely on any prior analysis."
    echo ""
    echo "  To fix:"
    echo "    /hitl:dev-switch-context         reload context for issue #$BRANCH_ISSUE"
    echo "    git checkout issue/$YAML_ISSUE-... return to the issue #$YAML_ISSUE branch"
    echo "    New session (recommended)         start a fresh Claude Code session"
    echo "$SEP"
    exit 0
  fi
fi

# When a change is in progress, show breadcrumbs on every prompt
if [[ -f "$HITL_FILE" ]] && grep -q "^current_step:" "$HITL_FILE" 2>/dev/null; then
  show_breadcrumbs && exit 0
fi

# No active change — show static startup menu once per session
SESSION_MARKER="${TMPDIR:-${TMP:-/tmp}}/hitl-welcomed-${PPID}"
[[ -f "$SESSION_MARKER" ]] && exit 0
touch "$SESSION_MARKER"

cat << 'BANNER'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HITL AI-Driven Development — platform active

  Start a project:
    /hitl:dev-start-from-prd    new project from a PRD
    /hitl:dev-start-brownfield  onboard an existing codebase
    /hitl:dev-start-migration   migrate from one system to another

  Run a change:
    /hitl:dev-practices      begin a new change (full 32-step workflow)

  Roles: /pm  /architect  /qa  /ops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNER

exit 0
