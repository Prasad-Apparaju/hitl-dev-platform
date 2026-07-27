#!/usr/bin/env python3
"""First Pass (FR-29) — permission policy (Phase G, LLD §9, CR-15, ADR-7).

Under First Pass, routine reversible in-scope work proceeds without a prompt; the genuinely critical
still prompts. This is the floor logic applied to tool permissions — NOT `bypassPermissions`.
`decide()` is the single classifier; default is fail-safe (unknown ⇒ prompt)."""
from __future__ import annotations

# Actions that ALWAYS prompt — irreversible / destructive / outward, regardless of scope.
ALWAYS_PROMPT = {"deploy", "promote", "migrate", "external_send", "force_push", "secret_access", "delete"}
# Reversible in-workspace actions that may auto-proceed WHEN in scope.
SCOPED_OK = {"read", "edit", "write"}


def _in_scope(path, scope_paths):
    """A path is in scope if it sits under the project root / a declared allowed_path prefix."""
    if path is None:
        return False
    p = str(path).lstrip("./")
    for s in (scope_paths or []):
        s = str(s).rstrip("*").lstrip("./")
        if s and p.startswith(s):
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
