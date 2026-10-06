# Hook re-wire: what Step 4 checks and why

Read from Step 4 of `dev-update`. What each wrapper marker protects, what each `.claude/settings.json` absence means, and why that file is repaired and never replaced. The commands are in Step 4 itself.

## The wrapper markers

Every marker is load-bearing, and a wrapper can carry one current marker while another is stale; checking a single marker is how such drift goes unnoticed.

| Marker | What it protects |
|---|---|
| `installed_plugins.json` | current plugin discovery; without it the wrapper looks for the plugin where current Claude Code does not record it, and every hook fails to find it |
| `command -v` and `HITL_PY` | the interpreter probe; without it a bare `python3` is the Microsoft Store stub on Windows (on PATH, runs nothing), so every hook silently no-ops |
| `first-pass-permissions.sh` present | the permission policy; without this wrapper the policy never engages |

Any missing marker means the wrappers predate the current template. They are regenerated as a set, all nine, from the single definition in Step 0 of `/hitl:dev-start-from-prd`, never patched one by one.

## What each settings.json absence means

- `$CLAUDE_PROJECT_DIR` absent: the hook commands use relative paths and fail whenever Claude Code's working directory differs from the project root.
- `statusLine` absent, a bare string, or pointing anywhere other than `hooks/statusline-hitl.sh`: the persistent HITL breadcrumb is missing or wrong. A bare-string `statusLine` passes a grep for the script name and renders nothing, which is why the step asserts shape and target, not presence.
- `hitl-gate` absent from `SessionStart`: the session-start change-intake gate never fires.

## Repair, never replace

The settings template in Step 0 of `/hitl:dev-start-from-prd` is a complete file, not a merge. Deleting the repo's file and writing the template takes the team's `permissions`, `env`, MCP wiring and every non-HITL hook with it, and the trigger is common: any project with its own `statusLine` matches on first upgrade. So the file is backed up, only the wrong keys are added or corrected, and the diff is shown before writing. The template is written wholesale only when the file is absent or unparseable, and the step says so when it does.
