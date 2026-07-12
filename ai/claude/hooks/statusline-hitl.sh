#!/usr/bin/env bash
# HITL status line for Claude Code
# Reads the active HITL context and emits a persistent status bar line showing the current
# change, phase, step, and a windowed step trail — driven by the self-describing `workflow`
# block in current-change.yaml via the shared _steps.sh parser (no hardcoded step model, so it
# can never drift from the welcome banner).
#
# Claude Code pipes a JSON object to stdin containing: cwd, model, context_window.
# Wire up in .claude/settings.json:
#   "statusLine": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh\""

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
YAML_FILE="$ROOT/.hitl/current-change.yaml"

# Shared parser/rendering library (lives beside this script).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh"

input=$(cat)

cwd=$(echo "$input"   | jq -r '.cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input"  | jq -r '.context_window.used_percentage // empty')

# ANSI color codes
COLOR_GREEN='\033[32m'
COLOR_YELLOW='\033[33m'
COLOR_RED='\033[31m'
COLOR_CYAN='\033[36m'
COLOR_MAGENTA='\033[35m'
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
if hitl_change_active "$YAML_FILE"; then
  change_id=$(hitl_scalar "$YAML_FILE" change_id)
  tier=$(hitl_scalar "$YAML_FILE" tier)
  step_name=$(hitl_cs_field "$YAML_FILE" name)    # tolerant of quoted/unquoted, block/flow
  phase=$(hitl_cs_field "$YAML_FILE" phase)

  # Branch reconciliation marker (issue #12). Only the hard mismatch is shown; `unverifiable`
  # is tolerated silently (issue #15 — it was permanent noise on long-lived branches).
  warn=""
  [ "$(hitl_branch_reconcile "$YAML_FILE" "$branch")" = "mismatch" ] && warn=" ${COLOR_RED}⚠ branch≠${change_id}${COLOR_RESET}"

  cur=$(hitl_current_n "$YAML_FILE")
  if hitl_has_workflow "$YAML_FILE" && [ -n "$cur" ]; then
    wf=$(hitl_workflow_field "$YAML_FILE" id)
    total=$(hitl_total "$YAML_FILE")
    [ -z "$step_name" ] && step_name=$(hitl_current_label "$YAML_FILE")
    trail=$(hitl_render_trail "$YAML_FILE" color)
    hitl_segment="  ${COLOR_MAGENTA}|${COLOR_RESET}  HITL: ${phase:-$wf} · Step ${cur}/${total}: ${step_name} [${change_id} · T${tier}]${warn}\n     ${trail}"
  else
    num=$(hitl_cs_field "$YAML_FILE" number)
    hitl_segment="  ${COLOR_MAGENTA}|${COLOR_RESET}  HITL: ${phase:-change} · Step ${num:-?} [${change_id} · T${tier}]${warn}  (run /hitl:dev-update for the step trail)"
  fi
else
  hitl_segment="  ${COLOR_MAGENTA}|${COLOR_RESET}  ${COLOR_YELLOW}HITL: no active change — run /hitl:dev-start-change${COLOR_RESET}"
fi

# ── Platform chip: shown only while the project is not delivery-ready ──────────────────────
# Reads the readiness register with grep only (statusline runs per prompt; keep it cheap).
# Disappears permanently once /hitl:ops-plan-platform verify-ready flips delivery_ready.
REGISTER="$ROOT/docs/04-operations/platform-readiness.yaml"
platform_segment=""
if [ -f "$REGISTER" ] && ! grep -qE '^delivery_ready:[[:space:]]*true' "$REGISTER" 2>/dev/null; then
  gaps=$(grep -cE '^[[:space:]]*status:[[:space:]]*gap' "$REGISTER" 2>/dev/null || echo 0)
  platform_segment="  ${COLOR_MAGENTA}|${COLOR_RESET}  ${COLOR_YELLOW}platform: ${gaps} gap(s) — not delivery-ready${COLOR_RESET}"
fi

printf "%s  %s%b%b" "$cwd" "$model" "$ctx_segment" "$branch_segment"
[ -n "$hitl_segment" ] && printf "\n%b" "$hitl_segment"
[ -n "$platform_segment" ] && printf "%b" "$platform_segment"
