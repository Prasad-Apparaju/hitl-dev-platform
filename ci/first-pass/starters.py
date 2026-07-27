#!/usr/bin/env python3
"""First Pass (FR-29) — the starter registry (Phase D, LLD §5, CR-13).

A `starter` is an HONEST-MINIMAL artifact — never a fabricated full one — always emitted with the
`needs-enhancement` marker. The canonical case: acceptance criteria = "a working version of the system."
Steps not in the registry offer no starter (fall back to defer/decline, or keep for a no_omit step)."""
from __future__ import annotations

STARTER_MARKER = "needs-enhancement"

# step_key -> (honest-minimal body, what the enhancement adds)
STARTERS = {
    # acceptance criteria live in the packet/issue — the starter is the single honest bar
    "packet":    ("Acceptance criteria (starter): a working version of the system exists and runs.",
                  "specific behavioral + edge-case acceptance criteria"),
    "test_plan": ("Test plan (starter): one happy-path case per component.",
                  "edge cases, failure modes, and negative tests"),
    "docs":      ("Design (starter): section headings + the decisions already made; gaps marked.",
                  "the sections left as TODO"),
    "impact":    ("Impact (starter): the domains and paths this change touches (mechanically derived).",
                  "full downstream / cross-domain analysis"),
    "rollout":   ("Rollout (starter): deploy, and roll back by redeploying the previous version.",
                  "canary criteria + automated rollback"),
    "red":       ("TDD RED (starter): one happy-path failing test.",
                  "edge cases + failure-mode tests"),
    "green":     ("TDD GREEN (starter): make the happy-path test pass.",
                  "edge cases + failure-mode tests"),
}


def has_starter(step_key):
    return step_key in STARTERS


def starter_for(step_key):
    """The honest-minimal starter text, marked needs-enhancement, or None if the step has no starter."""
    if step_key not in STARTERS:
        return None
    body, enh = STARTERS[step_key]
    return f"{body}\n\n{STARTER_MARKER}: {enh}\n"
