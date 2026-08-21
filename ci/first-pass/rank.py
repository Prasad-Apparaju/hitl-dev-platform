#!/usr/bin/env python3
"""Rank the steps of a plan by what it costs to skip each one.

Read at intake so the selection list puts the consequential choices at the top and shows, beside
each unticked box, what the reader gives up.

`forgo_cost` in the catalog is the cost of skipping a step ON A CHANGE THAT ENGAGES IT — not an
average. The rank a person sees is modulated:

  down one   when `engages` does not match this change
  up one     when the change touches a manifest domain with entries in the incident registry
  never past the floor — modulation reorders the list, it does not unlock a floor step or soften
             `no_omit`. Those are decided by tier and by signature.

Degrading quietly is a requirement, not a nicety: a project with no manifest, no registry, or no
`step_costs` block still has to produce a usable order. Missing data means "no signal", never an
error and never a raise.
"""
import fnmatch

RANKS = ("low", "medium", "high")


def _idx(rank):
    try:
        return RANKS.index(str(rank).strip().lower())
    except ValueError:
        return 1                      # an unreadable rank sorts as medium rather than crashing


def engaged(engages, *, paths=(), profile="", tags=(), multi_domain=False):
    """Does this change engage the step? Unknown/absent `engages` counts as engaged.

    Absent means the step's author did not narrow it, so it applies. Guessing "not engaged" would
    silently demote every step nobody has annotated.
    """
    if engages in (None, "", "always"):
        return True
    if not isinstance(engages, dict):
        return True
    if not any(engages.get(k) for k in ("paths", "profiles", "tags", "multi_domain")):
        return True                   # `engages: {}` states no criteria, which is not the same as
                                      # stating criteria that fail. An empty dict demoting the step
                                      # is the silent-demotion this function exists to avoid.
    if engages.get("multi_domain") and multi_domain:
        return True
    if profile and profile in (engages.get("profiles") or []):
        return True
    if set(tags or ()) & set(engages.get("tags") or ()):
        return True
    globs = engages.get("paths") or []
    for p in paths or ():
        for g in globs:
            # fnmatch does not treat "/" specially, so "**/x" and "dir/**" both behave as intended
            # for the shapes used here.
            if fnmatch.fnmatch(p, g) or fnmatch.fnmatch(p, g.replace("**/", "*")):
                return True
    return False


def shown_rank(entry, *, paths=(), profile="", tags=(), multi_domain=False, risky_domain=False,
               locked=False):
    """The rank to sort and label by. `locked` (floor at this tier, or no_omit) pins it to high."""
    if locked:
        return "high"
    i = _idx((entry or {}).get("forgo_cost", "medium"))
    if not engaged((entry or {}).get("engages"), paths=paths, profile=profile, tags=tags,
                   multi_domain=multi_domain):
        i -= 1
    if risky_domain:
        i += 1
    return RANKS[max(0, min(len(RANKS) - 1, i))]


def rank_plan(steps, costs, *, tier=2, paths=(), profile="", tags=(), multi_domain=False,
              risky_domain=False):
    """Order a plan's steps most-consequential first.

    Returns dicts carrying the step, its shown rank, whether it is locked, and the `protects`
    sentence. Ties keep catalog order so the list is stable between runs.
    """
    costs = costs or {}
    out = []
    for pos, s in enumerate(steps or []):
        key = s.get("key")
        crit = (s.get("crit_by_tier") or {}).get(tier, s.get("crit", "standard"))
        locked = crit == "floor" or bool(s.get("no_omit"))
        entry = costs.get(key) or {}
        out.append({
            "key": key,
            "step": s,
            "locked": locked,
            "lock_reason": ("floor at tier %s" % tier) if crit == "floor" else
                           ("thinnable, never dropped" if s.get("no_omit") else ""),
            "rank": shown_rank(entry, paths=paths, profile=profile, tags=tags,
                               multi_domain=multi_domain, risky_domain=risky_domain, locked=locked),
            "protects": entry.get("protects", ""),
            "pos": pos,
        })
    out.sort(key=lambda r: (not r["locked"], -_idx(r["rank"]), r["pos"]))
    return out


def risky_domains(manifest, incidents):
    """Domain names that appear in the incident registry. Either input may be absent."""
    doms = {}
    for d in ((manifest or {}).get("domains") or []):
        if isinstance(d, dict) and d.get("name"):
            doms[d["name"]] = [p for p in (d.get("paths") or []) if isinstance(p, str)]
    named = set()
    for i in ((incidents or {}).get("incidents") or []):
        if isinstance(i, dict):
            for f in ("domain", "domains", "area"):
                v = i.get(f)
                if isinstance(v, str):
                    named.add(v)
                elif isinstance(v, list):
                    named |= {x for x in v if isinstance(x, str)}
    return {d: doms[d] for d in doms if d in named}


def touches_risky(paths, risky):
    """Does any changed path fall inside a domain that has burned this project before?"""
    for dom_paths in (risky or {}).values():
        for dp in dom_paths:
            pref = dp.rstrip("*").rstrip("/")
            for p in paths or ():
                if pref and (p == pref or p.startswith(pref + "/")):
                    return True
    return False
