#!/usr/bin/env bash
# PreToolUse hook: the First Pass reduced-friction permission policy (CR-15 / ADR-7).
#
# This is the wiring `shared/first-pass/permissions.md` always described and nothing ever
# implemented: `ci/first-pass/permissions.py::decide()` existed, was unit-tested, and had no caller,
# so a change marked `first_pass: true` still prompted for every routine in-scope action.
#
# Behaviour, deliberately narrow:
#   - Not a HITL project, no active change, or `first_pass` not literally true → exit 0, say nothing.
#     Normal prompting applies. First Pass is opt-in and this hook is silent outside it.
#   - Under First Pass, ask decide() whether this action is routine and in scope. Only when it says
#     "do not prompt" does the hook emit an `allow` decision. Anything else → exit 0 (ask as usual).
#
# It never emits `deny` and never emits `allow` for a critical action: decide()'s ALWAYS_PROMPT set
# (deploy, promote, migrate, force-push, secret access, delete, external send) and anything out of
# scope or malformed fail safe to a prompt. First Pass never means "bypass all safety" (CR-15).
#
# Scope comes from the change's `allowed_paths` plus its manifest domain paths — the same scope the
# domain-boundary hook enforces, so the two cannot disagree.

[[ -d ".hitl" ]] || exit 0          # not a HITL project — skip silently

set -uo pipefail                    # NOT -e: this hook must fail open, never break a tool call

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh" 2>/dev/null || exit 0

PY=$(hitl_python) || exit 0
[[ -f ".hitl/current-change.yaml" ]] || exit 0

INPUT=$(cat)

export _HITL_HOOK_INPUT="$INPUT"
"$PY" << 'PYEOF' 2>/dev/null || exit 0
import json, os, sys

# Fail open on anything unexpected: this hook can only ever REMOVE a prompt, so a silent exit 0
# leaves the user exactly where they were without it.
def out(decision=None):
    if decision:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": decision,
            "permissionDecisionReason": "First Pass: routine in-scope action (CR-15)"}}))
    sys.exit(0)

try:
    import yaml
except Exception:
    out()

try:
    data = json.loads(os.environ.get("_HITL_HOOK_INPUT", "{}"))
except Exception:
    out()

try:
    with open(".hitl/current-change.yaml", encoding="utf-8") as fh:
        change = yaml.safe_load(fh) or {}
except Exception:
    out()
if not isinstance(change, dict):
    out()

# Opt-in, and strictly: a non-bool `first_pass` is malformed, not permission to relax anything.
if change.get("first_pass") is not True:
    out()
if str(change.get("status", "")).strip() == "merged":
    out()

for d in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "shared/ci/first-pass"),
          "ci/first-pass"):
    if os.path.isfile(os.path.join(d, "permissions.py")):
        sys.path.insert(0, d)
        break
try:
    from permissions import decide
except Exception:
    out()

# Tool → action. Only the routine ones are named; everything unlisted falls through to a prompt,
# which is why this map is a whitelist rather than a translation table.
TOOL_ACTIONS = {"Read": "read", "Grep": "read", "Glob": "read", "NotebookRead": "read",
                "Edit": "edit", "Write": "write", "NotebookEdit": "edit", "MultiEdit": "edit"}
action = TOOL_ACTIONS.get(data.get("tool_name", ""))
if not action:
    out()          # Bash and everything else keeps prompting — shell commands are not "routine"

ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
path = ti.get("file_path") or ti.get("path") or ti.get("notebook_path") or ti.get("pattern")

# Scope = allowed_paths + manifest domain paths, the same scope check-domain-boundary.sh enforces.
scope = [p for p in (change.get("allowed_paths") or []) if isinstance(p, str) and p.strip()]
m = change.get("manifest") if isinstance(change.get("manifest"), dict) else {}
for dom in (m.get("domains") if isinstance(m.get("domains"), list) else []):
    if isinstance(dom, dict):
        scope += [p for p in (dom.get("paths") or []) if isinstance(p, str) and p.strip()]

# An edit/write with no declared scope must NOT be auto-allowed — that is the whole project.
if action in ("edit", "write") and not scope:
    out()

prompt, _reason = decide(action, path=path, scope_paths=scope or None)
out(None if prompt else "allow")
PYEOF
exit 0
