#!/usr/bin/env python3
"""First Pass (FR-29) — the disposition menu constraints (Phase C, LLD §10.1, CR-6/CR-14).

Given a step's criticality + no_omit, which menu options may the team pick. `keep` is always the
pre-selected default (CR-1: doing nothing runs the full plan). The floor routes to a risk-accept path
(ack + waiver, §7). A no_omit step (TDD) may be thinned to a starter but never deferred/declined."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import check_skips as _c
import starters as _s


def allowed_dispositions(step_meta, tier):
    """Ordered list of the menu options offered for a step. `keep` first (the default)."""
    crit = _c.resolve_crit(step_meta, tier)
    key = step_meta.get("key")
    if crit == "floor":
        # a floor skip is only reachable via an explicit, authorized risk-accept (§7)
        return ["keep", "risk_accept"]
    opts = ["keep"]
    if _s.has_starter(key):
        opts.append("starter")
    if step_meta.get("no_omit"):
        return opts                      # keep [+ starter] — never defer/decline (CR-6)
    opts += ["defer", "decline"]
    return opts


def is_allowed(step_meta, tier, disposition):
    """Is a chosen LEDGER disposition (keep|defer|decline|starter) valid for this step? `keep` always;
    `starter` needs a registry entry; a `no_omit` step forbids defer/decline. A floor skip is reachable
    (its extra ack/waiver requirement is enforced by check_skips, not here — `risk_accept` is a menu
    label, not a ledger value)."""
    if disposition == "keep":
        return True
    if disposition not in ("defer", "decline", "starter"):
        return False
    if disposition == "starter" and not _s.has_starter(step_meta.get("key")):
        return False
    if step_meta.get("no_omit") and disposition in ("defer", "decline"):
        return False
    return True
