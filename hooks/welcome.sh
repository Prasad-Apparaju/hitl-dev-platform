#!/usr/bin/env bash
# UserPromptSubmit hook: display HITL welcome banner once per session.
# Uses a per-session temp file keyed on parent PID so the banner shows
# on the first prompt only, then stays silent for the rest of the session.

SESSION_MARKER="/tmp/hitl-welcomed-${PPID}"

if [[ -f "$SESSION_MARKER" ]]; then
  exit 0
fi

touch "$SESSION_MARKER"

cat << 'BANNER'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HITL AI-Driven Development — platform active

  Getting started:
    /start           set up a new project or onboard this codebase
    /dev-practices   begin a new change (full 30-step workflow)
    /                browse all 30 commands

  Roles: /pm  /architect  /qa  /ops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNER

exit 0
