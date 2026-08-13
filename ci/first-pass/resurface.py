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
# separators between phrase words — spaces, hyphens, and unicode dashes (codex-10: "should-have" leaked)
_SEP = r"[\s\-‐-―]+"           # one-or-more (required between should/have)
_SEPOPT = r"(?:[\s\-‐-―]+)?"   # optional (careless / care-less / care less)
_BLAME_STEMS = [r"fail\w*", r"neglig\w*", r"care" + _SEPOPT + r"less\w*", r"fault\w*", r"blam\w*",
                r"laz\w*", r"should" + _SEP + r"have", r"sloppy", r"sloppil\w*"]
_BLAME_RE = re.compile(r"\b(?:" + "|".join(_BLAME_STEMS) + r")\b", re.I | re.S)


def _paths_overlap(a, b):
    for p in a:
        for q in b:
            if p and q and (str(p).startswith(str(q)) or str(q).startswith(str(p))):
                return True
    return False


def _strs(x):
    """The hashable string members of a would-be list — tolerates a non-list or exotic members without
    crashing on set() construction (codex-11: crit as [], domains as [[]])."""
    return {v for v in (x if isinstance(x, list) else []) if isinstance(v, str)}


def overlaps(entry, new_domains, new_paths):
    """Does a ledger entry's area intersect the new change's? (domain OR path-prefix intersection.)"""
    if not isinstance(entry, dict):
        return False
    if _strs(entry.get("domains")) & _strs(new_domains):
        return True
    return _paths_overlap(_strs(entry.get("paths")), _strs(new_paths))


def _rank(e):
    c = e.get("crit") if isinstance(e, dict) else None
    return -CRIT_RANK.get(c if isinstance(c, str) else "", 1)   # non-string crit → standard rank, no crash


def surface(rollup, new_domains, new_paths):
    """The unresolved skips to raise at a new overlapping change. A `ceremony` skip is NOT resurfaced
    here (only at its own follow-up); `standard`/`floor` are, escalating by rank (CR-8). Tolerates a
    malformed roll-up / entries without crashing (codex-11)."""
    rollup = rollup if isinstance(rollup, dict) else {}
    out = []
    for e in (rollup.get("entries") if isinstance(rollup.get("entries"), list) else []):
        if not isinstance(e, dict) or e.get("resolved"):
            continue
        if e.get("crit") == "ceremony":
            continue
        if overlaps(e, new_domains, new_paths):
            out.append(e)
    out.sort(key=_rank)   # floor first
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


DEFAULT_CAP = 3


def digest(entries, cap=DEFAULT_CAP):
    """Collapse a surfaced list into something a person will actually read.

    `surface()` returns every unresolved overlapping entry, unbounded and one paragraph each. A domain
    worked on repeatedly accumulates entries faster than they are resolved, so the honest reminder turns
    into a wall that gets skipped — which costs more than saying nothing. Dedupe by (step, area), keep the
    most critical `cap` (the input is already floor-first), and count the rest.

    Returns `(shown, remaining)`. `shown` preserves input order; `remaining` is how many were folded away.
    """
    entries = entries if isinstance(entries, list) else []
    seen, unique = set(), []
    for e in entries:
        if not isinstance(e, dict):
            continue
        area = tuple(sorted(_strs(e.get("domains")))) or tuple(sorted(_strs(e.get("paths"))))
        key = (e.get("step") if isinstance(e.get("step"), str) else "", area)
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    cap = cap if isinstance(cap, int) and cap > 0 else DEFAULT_CAP
    return unique[:cap], max(0, len(unique) - cap)


def render(entries, cap=DEFAULT_CAP, ledger_path=".hitl/skip-ledger.yaml"):
    """The full resurfacing block for a change, or "" when there is nothing to raise."""
    shown, remaining = digest(entries, cap)
    if not shown:
        return ""
    lines = [message(e) for e in shown]
    if remaining:
        lines.append(f"There {'is' if remaining == 1 else 'are'} {remaining} more unresolved "
                     f"{'entry' if remaining == 1 else 'entries'} for this area in {ledger_path}.")
    return "\n\n".join(lines)


# --------------------------------------------------------------------------- scope + CLI
# The roll-up and the resurfacing read BOTH need the change's area, and a change does not know its
# area until the impact step declares it. That is why neither belongs at intake.

def scope(change):
    """(domains, paths) for a change record, tolerating both manifest shapes in the wild."""
    change = change if isinstance(change, dict) else {}
    m = change.get("manifest") if isinstance(change.get("manifest"), dict) else {}
    doms, paths = [], []
    if isinstance(m.get("domain"), str):
        doms.append(m["domain"])
    for d in (m.get("domains") if isinstance(m.get("domains"), list) else []):
        if isinstance(d, dict):
            if isinstance(d.get("name"), str):
                doms.append(d["name"])
            paths += [p for p in (d.get("paths") if isinstance(d.get("paths"), list) else []) if isinstance(p, str)]
    paths += [p for p in (change.get("allowed_paths") if isinstance(change.get("allowed_paths"), list) else [])
              if isinstance(p, str)]
    return doms, paths


def to_rollup(change, rollup):
    """Fold this change's skips into the roll-up, stamped with the area they apply to.

    Idempotent on (change_id, step) so re-running the impact step cannot duplicate entries."""
    rollup = rollup if isinstance(rollup, dict) else {}
    entries = rollup.get("entries") if isinstance(rollup.get("entries"), list) else []
    doms, paths = scope(change)
    cid = change.get("change_id") if isinstance(change.get("change_id"), str) else ""
    have = {(e.get("change_id"), e.get("step")) for e in entries if isinstance(e, dict)}
    added = 0
    for s in (change.get("skips") if isinstance(change.get("skips"), list) else []):
        if not isinstance(s, dict) or (cid, s.get("step")) in have:
            continue
        e = dict(s)
        e["change_id"] = cid
        # Per-entry copies: sharing one list object makes safe_dump emit YAML anchors (&id001/*id001)
        # into a file humans read and other tools parse.
        e["domains"] = list(doms)
        e["paths"] = list(paths)
        e.setdefault("resolved", False)
        entries.append(e)
        added += 1
    rollup["entries"] = entries
    return rollup, added


def main(argv=None):
    import argparse, yaml, io
    ap = argparse.ArgumentParser(description="Resurface unresolved skips overlapping this change.")
    ap.add_argument("--change", default=".hitl/current-change.yaml")
    ap.add_argument("--rollup", default=".hitl/skip-ledger.yaml")
    ap.add_argument("--append", action="store_true",
                    help="fold this change's skips into the roll-up first (run once, at the impact step)")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP)
    a = ap.parse_args(argv)

    def load(p):
        try:
            with io.open(p, encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except FileNotFoundError:
            return {}

    change, rollup = load(a.change), load(a.rollup)
    if a.append:
        rollup, added = to_rollup(change, rollup)
        if added:
            with io.open(a.rollup, "w", encoding="utf-8") as fh:
                yaml.safe_dump(rollup, fh, sort_keys=False, allow_unicode=True)

    doms, paths = scope(change)
    if not doms and not paths:
        print("No domain or allowed_paths on this change yet — resurfacing needs the impact step first.")
        return 0
    # Never resurface a change's own decisions back at it. Once --append has folded this change's skips
    # into the roll-up, they overlap its own scope by construction, and reminding someone about a choice
    # they made minutes ago at intake reads as nagging rather than care.
    cid = change.get("change_id") if isinstance(change.get("change_id"), str) else None
    hits = [e for e in surface(rollup, doms, paths)
            if not (cid and isinstance(e, dict) and e.get("change_id") == cid)]
    out = render(hits, cap=a.cap, ledger_path=a.rollup)
    print(out if out else "No unresolved skips overlap this change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
