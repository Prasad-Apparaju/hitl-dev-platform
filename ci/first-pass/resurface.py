#!/usr/bin/env python3
"""First Pass (FR-29) — resurfacing (Phase E, LLD §6, CR-8/CR-9).

Surfaces unresolved skips at the next change that overlaps the same area, escalating by criticality,
in respectful-persuasive language (never blaming). Persuade at boundaries only — the driver does not
call this mid-build (ADR-5). v1 overlap = manifest-domain or path-prefix intersection."""
from __future__ import annotations
import re
import sys

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


def _norm(p):
    """Path as a tuple of segments, with any glob tail dropped. `src/payments/**` -> ('src','payments')."""
    parts = []
    for seg in str(p).replace("\\", "/").strip("/").split("/"):
        if not seg or seg == ".":
            continue
        if any(ch in seg for ch in "*?["):
            break                      # a glob segment ends the literal prefix we can compare
        parts.append(seg)
    return tuple(parts)


def _paths_overlap(a, b):
    """Do two path sets touch? Compared by SEGMENT, not by raw string.

    A raw `startswith` was wrong in both directions: `src/pay` "matched" `src/payments` (a sibling
    that merely shares a character prefix), while a declared `src/payments/**` failed to match
    `src/payments/api.py` because the literal glob characters broke the comparison — and the schema
    explicitly describes allowed_paths as glob patterns. One direction nagged about unrelated work,
    the other stayed silent on exactly the change that should have been reminded.
    """
    A = [_norm(p) for p in a if str(p).strip()]
    B = [_norm(q) for q in b if str(q).strip()]
    for p in A:
        for q in B:
            n = min(len(p), len(q))
            if p[:n] == q[:n]:         # one is a directory ancestor of the other (or the same path)
                return True
    return False


def _strs(x):
    """The hashable string members of a would-be list — tolerates a non-list or exotic members without
    crashing on set() construction (codex-11: crit as [], domains as [[]])."""
    return {v for v in (x if isinstance(x, list) else []) if isinstance(v, str)}


def overlaps(entry, new_domains, new_paths):
    """Does a ledger entry's area intersect the new change's? (domain OR path-prefix intersection.)

    An entry recorded with no area is `project_wide`: it came from a route that has no manifest scope
    yet (onboarding, migration, docs), and the honest reading of "we skipped this while standing the
    project up" is that it applies everywhere rather than nowhere. Before this, an empty area matched
    nothing and the skip was invisible forever."""
    if not isinstance(entry, dict):
        return False
    if entry.get("project_wide"):
        return True
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
        # Project-wide entries all have an empty area, so keying on (step, area) alone collapsed
        # every change that lightened the same step into one — silently, and without counting the
        # rest as folded away. Distinguish them by change so distinct decisions stay visible.
        ident = e.get("change_id") if not area else ""
        key = (e.get("step") if isinstance(e.get("step"), str) else "", area, ident)
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

    Idempotent on (change_id, step) so re-running the impact step cannot duplicate entries.
    Returns `(rollup, added, narrowed)` — `narrowed` counts entries whose project-wide area was
    replaced with a real one, which is a write the caller must persist even when nothing was added."""
    rollup = rollup if isinstance(rollup, dict) else {}
    entries = rollup.get("entries") if isinstance(rollup.get("entries"), list) else []
    doms, paths = scope(change)
    cid = change.get("change_id") if isinstance(change.get("change_id"), str) else ""

    # Normalise duplicates already in the ledger before doing anything else. An earlier version of
    # this function deduped against the roll-up but not against its own appends, so it could write
    # two entries for one (change_id, step). Preventing new ones does not repair the old: with two,
    # `by_key` keeps only the last, so a later narrowing fixes that one and leaves the other
    # project-wide forever. Collapse them here, keeping the first and preferring any that already
    # carry a real area.
    deduped, seen_keys, merged = [], {}, 0
    for e in entries:
        if not isinstance(e, dict):
            deduped.append(e)
            continue
        k = (e.get("change_id"), e.get("step"))
        if k not in seen_keys:
            seen_keys[k] = len(deduped)
            deduped.append(e)
            continue
        kept = deduped[seen_keys[k]]
        if kept.get("project_wide") and not e.get("project_wide"):
            deduped[seen_keys[k]] = e          # the scoped copy is the better record
        merged += 1
    entries = deduped
    by_key = {(e.get("change_id"), e.get("step")): e for e in entries if isinstance(e, dict)}
    have = set(by_key)
    added = narrowed = 0
    for s in (change.get("skips") if isinstance(change.get("skips"), list) else []):
        if not isinstance(s, dict):
            continue
        key = (cid, s.get("step"))
        if key in have:
            # Already recorded. If we now know the area and the stored entry was project-wide, narrow
            # it: intake records before scope exists, the impact step records after.
            prior = by_key[key]
            # Only narrow when we can actually identify the entry as ours. With no change_id every
            # record collapses onto the key ("", step), so narrowing would rewrite a DIFFERENT
            # change's area with this change's scope.
            if cid and (doms or paths) and prior.get("project_wide"):
                prior["domains"], prior["paths"] = list(doms), list(paths)
                prior.pop("project_wide", None)
                narrowed += 1
            continue
        e = dict(s)
        e["change_id"] = cid
        if not doms and not paths:
            e["project_wide"] = True
        # Per-entry copies: sharing one list object makes safe_dump emit YAML anchors (&id001/*id001)
        # into a file humans read and other tools parse.
        e["domains"] = list(doms)
        e["paths"] = list(paths)
        e.setdefault("resolved", False)
        entries.append(e)
        # A change file can carry two records for one step, so the dedupe must see what this loop
        # just appended — in BOTH structures, or the second duplicate finds the key present in
        # `have` and absent from `by_key`.
        have.add(key)
        by_key[key] = e
        added += 1
    rollup["entries"] = entries
    return rollup, added, narrowed + merged


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
    doms, paths = scope(change)

    # Append regardless of scope. CR-10 makes the ledger durable for a PROJECT, and most routes
    # (onboarding, migration, docs) never declare a manifest domain at all — refusing there left
    # their skips recorded only in a change file the next intake overwrites. Without an area the
    # entry is marked project_wide and overlaps everything; the development route re-runs this after
    # its impact step and narrows the entry to the real scope.
    if a.append:
        rollup, added, narrowed = to_rollup(change, rollup)
        if added or narrowed:
            with io.open(a.rollup, "w", encoding="utf-8") as fh:
                yaml.safe_dump(rollup, fh, sort_keys=False, allow_unicode=True)
        if narrowed:
            print(f"Narrowed {narrowed} project-wide entr{'y' if narrowed == 1 else 'ies'} to this "
                  f"change's declared area.")
        if added:
            if not doms and not paths:
                print(f"Recorded {added} skip(s) as project-wide — this change has no manifest domain "
                      f"or allowed_paths. They will resurface at any later change until resolved.")

    # No early return when this change lacks scope. A project-wide entry overlaps everything, so a
    # scope-less change is exactly where those need to be read — the onboarding and docs routes that
    # justified project-wide scope in the first place are precisely the ones that never get scope.
    # Returning here made the read dead for them, which is the bug project-wide was meant to fix.
    # Never resurface a change's own decisions back at it. Once --append has folded this change's skips
    # into the roll-up, they overlap its own scope by construction, and reminding someone about a choice
    # they made minutes ago at intake reads as nagging rather than care.
    # Exclude this change's own entries — with --append they are in the roll-up by now, and
    # reminding someone of a decision they made minutes ago reads as nagging. Only exclude on a real
    # id: if change_id is missing we cannot tell ours from anyone's, and suppressing entries we
    # cannot identify would hide real risk to avoid a nuisance. Say so instead.
    cid = change.get("change_id")
    cid = cid.strip() if isinstance(cid, str) else ""
    if not cid:
        print("(change_id missing — cannot separate this change's own entries; showing all)",
              file=sys.stderr)
    hits = [e for e in surface(rollup, doms, paths)
            if not (cid and isinstance(e, dict) and str(e.get("change_id") or "").strip() == cid)]
    out = render(hits, cap=a.cap, ledger_path=a.rollup)
    print(out if out else "No unresolved skips overlap this change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
