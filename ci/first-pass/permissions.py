#!/usr/bin/env python3
"""First Pass (FR-29) — permission policy (Phase G, LLD §9, CR-15, ADR-7).

Under First Pass, routine reversible in-scope work proceeds without a prompt; the genuinely critical
still prompts. This is the floor logic applied to tool permissions — NOT `bypassPermissions`.
`decide()` is the single classifier; default is fail-safe (unknown ⇒ prompt)."""
from __future__ import annotations
import os.path

# Actions that ALWAYS prompt — irreversible / destructive / outward, regardless of scope.
ALWAYS_PROMPT = {"deploy", "promote", "migrate", "external_send", "force_push", "secret_access", "delete"}
# Reversible in-workspace actions that may auto-proceed WHEN in scope.
SCOPED_OK = {"read", "edit", "write"}


def _norm(x):
    """Normalize a path for scope comparison — resolve `..`/`.` so a traversal can't prefix-match a
    scope (e.g. 'src/billing/../../../etc' must NOT count as under 'src/billing')."""
    return os.path.normpath(str(x).replace("\\", "/")).lstrip("./")


def _in_scope(path, scope_paths):
    """A path is in scope if, AFTER normalization, it sits under a declared allowed_path prefix.
    An absolute path or one that escapes the project root (starts with '..') is never in scope."""
    if path is None:
        return False
    p = _norm(path)
    if os.path.isabs(str(path)) or p.startswith("..") or p == "..":
        return False
    for s in (scope_paths or []):
        s = _norm(str(s).rstrip("*"))
        if s and (p == s or p.startswith(s + "/")):   # true path-segment containment, not bare prefix
            return True
    return False


def decide(action, path=None, scope_paths=None):
    """Return (prompt: bool, reason: str). prompt=True ⇒ First Pass still asks the human.

    First Pass never means 'bypass all safety': ALWAYS_PROMPT actions prompt even in scope; a scoped
    read/edit/write auto-proceeds only inside the declared scope; anything else fails safe to a prompt."""
    if action in ALWAYS_PROMPT:
        return True, f"{action}: critical/irreversible/outward — prompts even under First Pass"
    if action == "read":
        return False, "in-project read — auto-allowed"
    if action in ("edit", "write"):
        if _in_scope(path, scope_paths):
            return False, "in-scope edit — auto-allowed"
        return True, f"edit outside the change scope ({path}) — prompts"
    return True, f"unknown action '{action}' — fail-safe prompt"
