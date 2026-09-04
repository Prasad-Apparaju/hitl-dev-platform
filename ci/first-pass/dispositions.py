#!/usr/bin/env python3
"""First Pass (FR-29) — the disposition menu constraints (Phase C, LLD §10.1, CR-6/CR-14).

Given a step's criticality + no_omit, which menu options may the team pick. `keep` is the pre-selected
default (CR-1: doing nothing runs the full plan), with one bounded exception: at tier 0/1 a `ceremony`
step may be presented pre-marked `decline` (CR-1 as amended 2026-08-13). `standard`, `floor` and
`no_omit` keep `keep` as the default at every tier, and nothing is written before a human confirms.
The floor routes to a risk-accept path (ack + waiver, §7). A no_omit step (TDD) may be thinned to a
starter but never deferred/declined.

TWO VOCABULARIES — read this before using either function. `allowed_dispositions()` returns MENU
options, which include `risk_accept` (what a human REQUESTS for a floor step). `is_allowed()`
validates LEDGER dispositions, which are only defer/decline/starter — a floor skip is RECORDED as a
decline carrying `ack_by`, and check_skips enforces that ack. So `is_allowed(deploy, 2, "decline")`
is True while `"decline"` is absent from that step's menu, and `is_allowed(..., "risk_accept")` is
False while it IS on the menu. Both are correct; they answer different questions. Validate a written
record with `is_allowed`, present choices with `allowed_dispositions`."""
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
    """Is a chosen LEDGER disposition valid for this step? `keep` always; `starter` needs a registry
    entry; a `no_omit` step forbids defer/decline. A floor skip is reachable (its extra ack/waiver
    requirement is enforced by check_skips, not here — `risk_accept` is a menu label, not a ledger
    value).

    `not_applicable` (#97) is the RULES excluding a step, not a person declining it, so it is NOT a
    menu option — `allowed_dispositions` never offers it. It is valid as a ledger value on any step
    the rules may decide about, which is anything not floor and not no_omit — plus a `cond:` step
    (#102): a conditional step whose activator did not fire was never in the plan for the floor to
    protect, so the rules may record it not_applicable even when it is floor (pentest). check_skips
    enforces the same boundary independently with RULE_OVER_FLOOR, because a rule retiring a
    load-bearing step is a hole straight through the floor. The two rules MUST agree: when this one
    lagged behind check_skips, the generator refused the record the sizer produced and intake died on
    every ordinary change.
    """
    if disposition == "keep":
        return True
    if disposition == "not_applicable":
        if step_meta.get("cond"):
            return True
        return not (_c.resolve_crit(step_meta, tier) == "floor" or step_meta.get("no_omit"))
    if disposition not in ("defer", "decline", "starter"):
        return False
    if disposition == "starter" and not _s.has_starter(step_meta.get("key")):
        return False
    if step_meta.get("no_omit") and disposition in ("defer", "decline"):
        return False
    return True
