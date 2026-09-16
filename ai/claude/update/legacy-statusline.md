# The legacy statusline a pre-plugin repo carries

Read from Step 4 of `dev-update`. A self-contained sub-procedure: what the stale entry looks like,
why a grep passes it, and how to remove the script without touching a file that is the team's own.

A repo onboarded before the `.hitl/hooks/` layout has a `statusLine` that runs a **pre-plugin standalone script**:

```json
"statusLine": { "type": "command",
  "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/statusline.sh\"" }
```

A `grep "statusLine"` matches that happily, so the check passes and the stale script survives every subsequent upgrade. It hardcodes the 32-step development flow and cannot render any other workflow, so on a 6-step `docs` change it reports `Step 3/32` with a trail of steps the change does not contain — while the `UserPromptSubmit` breadcrumb from `welcome.sh` renders correctly. The human and the model then read two disagreeing status lines, which is very hard to diagnose from inside a session (plugin issue #23 item 1).

If a legacy `.hitl/statusline.sh` is present, delete it during re-sync so nothing can be re-pointed at it:
```bash
if [ -f .hitl/statusline.sh ]; then
  if git ls-files --error-unmatch .hitl/statusline.sh >/dev/null 2>&1; then
    rm -f .hitl/statusline.sh && echo "Removed legacy .hitl/statusline.sh (tracked: recoverable from git)"
  else
    echo "  .hitl/statusline.sh is UNTRACKED: leaving it alone. If it is HITL's legacy script," >&2
    echo "  delete it yourself; if it is yours, move it out of .hitl/." >&2
  fi
fi
```
