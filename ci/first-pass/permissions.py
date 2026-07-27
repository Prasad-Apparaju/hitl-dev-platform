#!/usr/bin/env python3
"""First Pass (FR-29) — permission policy (Phase G, LLD §9, CR-15, ADR-7).

Under First Pass, routine reversible in-scope work proceeds without a prompt; the genuinely critical
still prompts. This is the floor logic applied to tool permissions — NOT `bypassPermissions`.
`decide()` is the single classifier; default is fail-safe (unknown ⇒ prompt)."""
from __future__ import annotations
import os.path
import re

# A Windows drive-letter (C:\) or UNC (\\srv, //srv, \\?\) absolute path — POSIX os.path.isabs misses
# these on a non-Windows runner, so they must be caught explicitly (round-2 MED; Windows is in scope).
_WIN_ABS = re.compile(r"^[A-Za-z]:|^\\\\|^//|^\\\\\?\\")

# Actions that ALWAYS prompt — irreversible / destructive / outward, regardless of scope.
ALWAYS_PROMPT = {"deploy", "promote", "migrate", "external_send", "force_push", "secret_access", "delete"}
# Reversible in-workspace actions that may auto-proceed WHEN in scope.
SCOPED_OK = {"read", "edit", "write"}


def _norm(x):
    """Normalize a path for comparison — collapse `..`/`.` via normpath. Do NOT strip leading dots as a
    char set: `lstrip('./')` turned '.src/x' into 'src/x' and let a hidden dir match scope (round-1 MED-6).
    normpath alone already drops a leading './' while preserving a real leading dot (`.src`)."""
    return os.path.normpath(str(x).replace("\\", "/"))


def _escapes_project(path):
    """True if a path is absolute (POSIX, Windows drive-letter, or UNC) or, after normalization, climbs
    out of the project root ('..')."""
    s = str(path)
    if os.path.isabs(s) or _WIN_ABS.match(s):
        return True
    p = _norm(path)
    return p == ".." or p.startswith("../")


def _in_scope(path, scope_paths):
    """A path is in the change scope if, AFTER normalization, it sits strictly under a declared
    allowed_path (true path-segment containment). Absolute / project-escaping paths are never in scope."""
    if path is None or _escapes_project(path):
        return False
    p = _norm(path)
    for s in (scope_paths or []):
        s = _norm(str(s).rstrip("*"))
        if s and (p == s or p.startswith(s + "/")):   # segment containment, not a bare string prefix
            return True
    return False


def decide(action, path=None, scope_paths=None):
    """Return (prompt: bool, reason: str). prompt=True ⇒ First Pass still asks the human.

    First Pass never means 'bypass all safety': ALWAYS_PROMPT actions prompt even in scope; a scoped
    read/edit/write auto-proceeds only inside the declared scope; anything else fails safe to a prompt."""
    if action in ALWAYS_PROMPT:
        return True, f"{action}: critical/irreversible/outward — prompts even under First Pass"
    if action == "read":
        # reads auto-allow only WITHIN the project — an absolute path or a `..`-escape (e.g. /etc/passwd,
        # ../secrets.env) still prompts (round-1 MED-5: reads were ungated, an exfil surface).
        if path is not None and _escapes_project(path):
            return True, f"read outside the project ({path}) — prompts"
        return False, "in-project read — auto-allowed"
    if action in ("edit", "write"):
        if _in_scope(path, scope_paths):
            return False, "in-scope edit — auto-allowed"
        return True, f"edit outside the change scope ({path}) — prompts"
    return True, f"unknown action '{action}' — fail-safe prompt"
