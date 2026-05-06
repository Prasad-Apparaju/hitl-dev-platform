#!/usr/bin/env bash
# UserPromptSubmit hook: HITL status banner.
# When a change is in progress with a known current_step: shows breadcrumbs every prompt.
# Otherwise: shows the static startup menu once per session.

HITL_FILE=".hitl/current-change.yaml"
SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Abbreviated step names (indices 1–31)
NAMES=("" "Issue" "Figma" "Impact" "ROI" "Docs" "IaC" "Tests" "Train" "Packet"
       "RED" "TstRvw" "Dsn+" "VfyRED" "GREEN" "VfyGRN" "Refact"
       "Conv" "Rvw1" "Rvw2" "Rerun" "Recncl" "QAVfy" "ImpBrf"
       "Rollout" "PR" "IntVfy" "Figma2" "Deploy" "Promote" "30dROI" "90dROI")

show_breadcrumbs() {
  # Parse current_step block from the YAML (controlled schema, no full parser needed)
  local cs_block
  cs_block=$(awk '/^current_step:/{f=1;next} f && /^[^ ]/{exit} f{print}' "$HITL_FILE")

  local step_num step_name phase change_id tier
  step_num=$(echo "$cs_block"  | awk '/number:/{print $2}')
  step_name=$(echo "$cs_block" | awk -F'"' '/name:/{print $2}')
  phase=$(echo "$cs_block"     | awk -F'"' '/phase:/{print $2}')
  change_id=$(awk '/^change_id:/{print $2}' "$HITL_FILE")
  tier=$(awk '/^tier:/{print $2}' "$HITL_FILE")

  # Validate — fall through to static menu if step_num is missing
  [[ -z "$step_num" || ! "$step_num" =~ ^[0-9]+$ ]] && return 1

  # Build trail: show a window of 9 steps centred on current step
  local win_start=$(( step_num - 4 )); (( win_start < 1  )) && win_start=1
  local win_end=$(( step_num + 4 ));   (( win_end  > 31 )) && win_end=31

  local trail=""
  (( win_start > 1 )) && trail="… "
  for (( i=win_start; i<=win_end; i++ )); do
    local name="${NAMES[$i]}"
    if   (( i <  step_num )); then trail+="✓${i}.${name}  "
    elif (( i == step_num )); then trail+="▶${i}.${name}  "
    else                           trail+="·${i}.${name}  "
    fi
  done
  (( win_end < 31 )) && trail+="…"

  echo "$SEP"
  printf "  HITL — %s  •  Step %d / 31: %s\n" "$phase" "$step_num" "$step_name"
  printf "  change: %s  •  tier: %s\n"         "$change_id" "$tier"
  echo  ""
  printf "  %s\n" "$trail"
  echo "$SEP"
  return 0
}

# When a change is in progress, show breadcrumbs on every prompt
if [[ -f "$HITL_FILE" ]] && grep -q "^current_step:" "$HITL_FILE" 2>/dev/null; then
  show_breadcrumbs && exit 0
fi

# No active change — show static startup menu once per session
SESSION_MARKER="/tmp/hitl-welcomed-${PPID}"
[[ -f "$SESSION_MARKER" ]] && exit 0
touch "$SESSION_MARKER"

cat << 'BANNER'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HITL AI-Driven Development — platform active

  Start a project:
    /start-prd          new project from a PRD
    /start-brownfield   onboard an existing codebase
    /start-migration    migrate from one system to another

  Run a change:
    /dev-practices      begin a new change (full 31-step workflow)

  Roles: /pm  /architect  /qa  /ops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNER

exit 0
