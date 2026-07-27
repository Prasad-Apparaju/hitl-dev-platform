#!/usr/bin/env python3
"""First Pass (FR-29) — resurfacing (Phase E, LLD §6, CR-8/CR-9).

Surfaces unresolved skips at the next change that overlaps the same area, escalating by criticality,
in respectful-persuasive language (never blaming). Persuade at boundaries only — the driver does not
call this mid-build (ADR-5). v1 overlap = manifest-domain or path-prefix intersection."""
from __future__ import annotations
import re

CRIT_RANK = {"ceremony": 0, "standard": 1, "floor": 2}
# Words/phrases the resurfacing voice must never use (CR-9). Lint target.
BLAME_WORDS = {"failed", "negligent", "careless", "fault", "blame", "lazy", "should have", "sloppy"}
# Redaction stems — catch inflections (failing, negligence, carelessly), hyphen/space variants
# (care-less), and flexible whitespace (should  have / should\nhave).
_BLAME_STEMS = [r"fail\w*", r"neglig\w*", r"care[\s-]?less\w*", r"fault\w*", r"blam\w*",
                r"laz\w*", r"should\s+have", r"sloppy", r"sloppily"]
_BLAME_RE = re.compile(r"\b(?:" + "|".join(_BLAME_STEMS) + r")\b", re.I | re.S)


def _paths_overlap(a, b):
    for p in a:
        for q in b:
            if p and q and (str(p).startswith(str(q)) or str(q).startswith(str(p))):
                return True
    return False


def overlaps(entry, new_domains, new_paths):
    """Does a ledger entry's area intersect the new change's? (domain OR path-prefix intersection.)"""
    if not isinstance(entry, dict):
        return False
    ed = set(entry.get("domains") or [])
    if ed & set(new_domains or []):
        return True
    return _paths_overlap(entry.get("paths") or [], new_paths or [])


def surface(rollup, new_domains, new_paths):
    """The unresolved skips to raise at a new overlapping change. A `ceremony` skip is NOT resurfaced
    here (only at its own follow-up); `standard`/`floor` are, escalating by rank (CR-8)."""
    out = []
    for e in ((rollup or {}).get("entries") or []):
        if not isinstance(e, dict) or e.get("resolved"):
            continue
        if e.get("crit") == "ceremony":
            continue
        if overlaps(e, new_domains, new_paths):
            out.append(e)
    out.sort(key=lambda e: -CRIT_RANK.get(e.get("crit"), 1))   # floor first
    return out


def _clean(text):
    """Redact blame words from INTERPOLATED (user-supplied) content so the reminder can't blame even if
    the recorded reason does (round-1 MED-7: the lint only covered the template, not the reason echoed
    into it). CR-9: the resurfacing voice never blames."""
    return _BLAME_RE.sub("[…]", str(text))


def message(entry):
    """A respectful, persuasive, NON-blaming reminder for one entry (CR-9)."""
    entry = entry if isinstance(entry, dict) else {}
    step = _clean(entry.get("step", "a step"))
    crit = entry.get("crit", "standard")
    lead = {"floor": "Worth a careful look", "standard": "A quick heads-up"}.get(crit, "A note")
    tail = " (this one was on the recommended floor, so it may be worth doing before you go further)" if crit == "floor" else ""
    return (f"{lead}: last time work touched this area, '{step}' was lightened "
            f"({_clean(entry.get('disposition', 'skipped'))} by {_clean(entry.get('actor', 'the team'))} — "
            f"reason: {_clean(entry.get('reason', 'n/a'))}). Since this change overlaps, it may be a good moment "
            f"to fold in the enhancement — happy to scope it{tail}.")
