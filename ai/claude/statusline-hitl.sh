#!/usr/bin/env bash
# HITL status line for Claude Code
# Preserves the global status line output (cwd, model, context bar, git branch)
# and appends the current HITL step when a change is in progress.

YAML_FILE="$(dirname "$0")/../.hitl/current-change.yaml"

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
branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
branch_segment=""
[ -n "$branch" ] && branch_segment=" ${COLOR_CYAN}git:(${branch})${COLOR_RESET}"

# HITL step (appended only when .hitl/current-change.yaml exists)
hitl_segment=""
if [ -f "$YAML_FILE" ]; then
  cs_block=$(awk '/^current_step:/{f=1;next} f && /^[^ ]/{exit} f{print}' "$YAML_FILE")
  step_num=$(echo "$cs_block"  | awk '/number:/{print $2}')
  step_name=$(echo "$cs_block" | awk -F'"' '/name:/{print $2}')
  phase=$(echo "$cs_block"     | awk -F'"' '/phase:/{print $2}')
  change_id=$(awk '/^change_id:/{print $2}' "$YAML_FILE")
  tier=$(awk '/^tier:/{print $2}' "$YAML_FILE")

  if [ -n "$phase" ] && [ -n "$step_num" ] && [ -n "$step_name" ]; then
    hitl_segment="  \033[35m|\033[0m  HITL: ${phase} | Step ${step_num}: ${step_name} [${change_id} · T${tier}]"
  fi
fi

printf "%s  %s%b%b%b" "$cwd" "$model" "$ctx_segment" "$branch_segment" "$hitl_segment"
