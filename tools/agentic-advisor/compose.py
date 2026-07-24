#!/usr/bin/env python3
"""Agentic Design Advisor — composer (EPIC #35 / FR-28 / LLD §4).

A RECOMMENDATION engine: given the elicited scenario (components + edges + risk
answers), recommend WHICH lenses this change needs (the report sections) and a
RECOMMENDED FLOOR (the controls that shouldn't be skipped). It authors no manifest,
imports/predicts no #10 activation, proves no equivalence — the Advisor recommends,
and #10 enforces its own checks at design time on the human-authored manifest.

Deterministic: the same scenario → the identical recommendation report (ADV-12). The
floor membership uses ONLY the safety-relevant risk factors (agent presence, edges,
side_effects, autonomy, async transport) — NOT Tier, which produces no computed field
(round-10 blocker 4). `Tier`/`stakes` may inform a human-confirmed advisory depth note
elsewhere; the composer takes no tier input.
"""
from __future__ import annotations
import sys

# Report-section lenses (not separate commands — round-9 M9). Stable order = topo tie-break.
LENSES = ["classify", "boundary", "privilege", "reliability", "observability", "memory", "evals", "deploy"]

DEPENDS = {
    "boundary": ["classify"], "privilege": ["classify"], "reliability": ["boundary"],
    "observability": ["classify"], "memory": ["classify"], "evals": ["classify"], "deploy": ["classify"],
}


# One component schema everywhere (round-10 B3): the composer/map/rerun read `proposed_kind` —
# the same field the canonical state (§7.1) and fixtures use. `classify` runs FIRST (DEPENDS),
# so `proposed_kind` is populated before any lens/floor needs `any_agent` (no circularity).
def any_agent(s):
    return any(c.get("proposed_kind") in ("simple_agent", "deep_agent") for c in s["components"])


def any_async(s):
    # edge transport (a factual property), not a design kind
    return any(e.get("transport") in ("async_task", "event") for e in s["edges"])


def relevant(lens, s):
    """Proportionality: a lens is a report section only if the scenario has data for it.
    All scenario flags live under s["answers"] (one canonical location — round-9 M1). Every
    read defaults so a PARTIALLY-elicited state (mid-intake render) never crashes (F3)."""
    a = s.get("answers", {})
    side, auto = a.get("side_effects", "none"), a.get("autonomy", "assisted")
    return {
        "classify":      any_agent(s),
        "boundary":      len(s["edges"]) > 0 and any_agent(s),
        "privilege":     any_agent(s),
        "reliability":   any_async(s) or side != "none" or auto in ("supervised", "autonomous"),
        "observability": any_agent(s),                      # hard directive: any agentic system
        "memory":        a.get("memory_hint", False),       # canonical input (round-codex: answers.memory_hint)
        "evals":         any_agent(s),
        "deploy":        a.get("greenfield") or a.get("changes_platform")
                         or a.get("adds_durable_runtime") or a.get("deploy_requested", False),
    }.get(lens, False)


def recommended_floor(s):
    """The RECOMMENDED floor — a deterministic function of the safety-relevant risk factors
    (expert judgment, NOT #10 activation). Membership uses only the factors it names; all
    reads default (F3)."""
    a = s.get("answers", {})
    side, auto = a.get("side_effects", "none"), a.get("autonomy", "assisted")
    floor = set()
    if any_agent(s):
        floor |= {"classify", "privilege", "observability", "evals"}
    if len(s["edges"]) > 0 and any_agent(s):
        floor.add("boundary")
    if side == "irreversible":                                # recommend a human gate
        floor.add("reliability")
    if auto in ("supervised", "autonomous") and side != "none":  # recommend a kill-switch
        floor.add("reliability")
    if any_async(s):                                          # async needs idempotency/DLQ design
        floor.add("reliability")
    return floor


def topo_order(included, depends):
    """Deterministic dependency order, LENSES-index tie-break: repeatedly emit the FIRST lens
    in LENSES order whose IN-SET deps are already emitted. A dep NOT in `included` can never
    arrive, so it is not a blocker (F1: e.g. reliability without boundary on a single
    irreversible agent). A termination guard flushes any residue rather than looping."""
    order, remaining = [], [l for l in LENSES if l in included]
    while remaining:
        progressed = False
        for l in remaining:
            if all(d in order for d in depends.get(l, []) if d in included):   # only wait on IN-SET deps
                order.append(l)
                remaining.remove(l)
                progressed = True
                break
        if not progressed:                                   # unreachable now; guard against any future cycle
            order.extend(remaining)
            break
    return order


PROPOSED_KINDS = {"deterministic", "simple_agent", "deep_agent"}
TRANSPORTS = {"sync_call", "async_task", "event"}


def validate_scenario(s):
    """Return enum errors (so a typo'd proposed_kind/transport is surfaced, not silently
    demoted — F8). The intake calls this before composing/handing off."""
    errs = []
    for c in s.get("components", []):
        pk = c.get("proposed_kind")
        if pk is not None and pk not in PROPOSED_KINDS:
            errs.append(f"component {c.get('id')}: unknown proposed_kind '{pk}' (expected {sorted(PROPOSED_KINDS)})")
    for e in s.get("edges", []):
        t = e.get("transport")
        if t is not None and t not in TRANSPORTS:
            errs.append(f"edge {e.get('id')}: unknown transport '{t}' (expected {sorted(TRANSPORTS)})")
    return errs


def compose(s):
    floor = recommended_floor(s)
    included = {l for l in LENSES if relevant(l, s)} | floor               # floor ⊆ included report sections
    rungs = included - floor                                               # offered, deferrable
    order = topo_order(included, DEPENDS)                                  # deterministic: topo, LENSES tie-break
    return {"report_sections": order, "floor": sorted(floor), "rungs": sorted(rungs)}


if __name__ == "__main__":       # CLI: read a scenario JSON on stdin, print the composed report
    import json
    s = json.load(sys.stdin)
    print(json.dumps(compose(s), indent=2))
