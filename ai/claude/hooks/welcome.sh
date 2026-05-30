#!/usr/bin/env bash
# UserPromptSubmit hook: HITL status banner.
# When a change is in progress with a known current_step: shows breadcrumbs every prompt.
# Otherwise: shows the static startup menu once per session.

# --- Graphify pre-flight (advisory only — Graphify is optional) ---
if ! command -v graphify &>/dev/null; then
  echo "HITL NOTE: Graphify is not installed — skills will read docs directly (higher token cost on large projects)." >&2
  echo "To install: uv tool install graphifyy && graphify claude install && graphify ." >&2
elif [[ ! -f "graphify-out/graph.json" ]]; then
  echo "HITL NOTE: Graphify is installed but the graph has not been built for this project." >&2
  echo "Run 'graphify .' in your project root to enable graph queries (optional but recommended)." >&2
fi
# --- end Graphify pre-flight ---

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
    /hitl:dev-start-prd          new project from a PRD
    /hitl:dev-start-brownfield   onboard an existing codebase
    /hitl:dev-start-migration    migrate from one system to another

  Run a change:
    /hitl:dev-practices      begin a new change (full 32-step workflow)

  Roles: /pm  /architect  /qa  /ops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNER

exit 0
