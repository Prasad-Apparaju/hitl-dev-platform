#!/usr/bin/env bash
# HITL status line for Claude Code
# Reads the active HITL context and emits a persistent status bar line showing
# the current change, phase, step, and a windowed step trail.
#
# Claude Code pipes a JSON object to stdin containing: cwd, model, context_window.
# Wire up in .claude/settings.json:
#   "statusLine": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh\""

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
YAML_FILE="$ROOT/.hitl/current-change.yaml"

input=$(cat)

cwd=$(echo "$input"   | jq -r '.cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input"  | jq -r '.context_window.used_percentage // empty')

# ANSI color codes
COLOR_GREEN='\033[32m'
COLOR_YELLOW='\033[33m'
COLOR_RED='\033[31m'
COLOR_CYAN='\033[36m'
COLOR_RESET='\033[0m'

# Context window progress bar
ctx_segment=""
if [ -n "$used" ]; then
  pct=$(printf '%.0f' "$used")
  if   [ "$pct" -le 50 ]; then color="$COLOR_GREEN"
  elif [ "$pct" -le 75 ]; then color="$COLOR_YELLOW"
  else                          color="$COLOR_RED"
  fi
  filled=$(( pct / 10 ))
  empty=$(( 10 - filled ))
  filled_bar=""; for i in $(seq 1 $filled); do filled_bar="${filled_bar}█"; done
  empty_bar="";  for i in $(seq 1 $empty);  do empty_bar="${empty_bar}░";  done
  ctx_segment=" [${color}${filled_bar}${COLOR_RESET}${empty_bar}] ${color}${pct}%${COLOR_RESET}"
fi

# Git branch
branch=$(git -C "$ROOT" branch --show-current 2>/dev/null)
branch_segment=""
[ -n "$branch" ] && branch_segment=" ${COLOR_CYAN}git:(${branch})${COLOR_RESET}"

# ── HITL step + trail ───────────────────────────────────────────────────────
hitl_segment=""
if [ -f "$YAML_FILE" ]; then
  cs_block=$(awk '/^current_step:/{f=1;next} f && /^[^ ]/{exit} f{print}' "$YAML_FILE")
  step_num=$(echo "$cs_block"  | awk '/number:/{print $2}')
  step_name=$(echo "$cs_block" | awk -F'"' '/name:/{print $2}')
  phase=$(echo "$cs_block"     | awk -F'"' '/phase:/{print $2}')
  change_id=$(awk '/^change_id:/{print $2}' "$YAML_FILE")
  tier=$(awk '/^tier:/{print $2}' "$YAML_FILE")

  if [ -n "$phase" ] && [ -n "$step_num" ]; then

    declare -a NAMES=()
    total=0

    case "$phase" in
      "Migration Setup")
        NAMES=("" "Context" "CLAUDE.md" "Manifest" "DirSetup" "ExtDocs" "Registries" "Issue" "Handoff")
        total=8
        ;;
      "Development")
        NAMES=("" "Issue" "Figma" "Impact" "ROI" "Docs" "IaC" "Tests" "Train" "Packet"
               "RED" "TstRvw" "Dsn+" "VfyRED" "GREEN" "VfyGRN" "Refact"
               "Conv" "Rvw1" "Rvw2" "Rerun" "Recncl" "QAVfy" "ImpBrf"
               "Rollout" "PR" "IntVfy" "Figma2" "Deploy" "Promote" "30dROI" "90dROI")
        total=31
        ;;
    esac

    # Windowed trail: 3 back + current + 3 ahead
    trail=""
    if [ ${#NAMES[@]} -gt 0 ]; then
      win_start=$(( step_num - 3 )); (( win_start < 1    )) && win_start=1
      win_end=$(( step_num + 3 ));   (( win_end  > total )) && win_end=$total

      (( win_start > 1 ))   && trail="… "
      for (( i=win_start; i<=win_end; i++ )); do
        name="${NAMES[$i]}"
        if   (( i <  step_num )); then trail+="✓${i}.${name} "
        elif (( i == step_num )); then trail+="\033[32m▶${i}.${name}\033[0m "
        else                          trail+="·${i}.${name} "
        fi
      done
      (( win_end < total )) && trail+="…"
    fi

    hitl_segment="  \033[35m|\033[0m  HITL: ${phase} · Step ${step_num}/${total}: ${step_name} [${change_id} · T${tier}]\n     ${trail}"
  fi
fi

printf "%s  %s%b%b" "$cwd" "$model" "$ctx_segment" "$branch_segment"
[ -n "$hitl_segment" ] && printf "\n%b" "$hitl_segment"
