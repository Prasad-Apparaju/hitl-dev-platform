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
    All scenario flags live under s["answers"] (one canonical location — round-9 M1)."""
    a = s["answers"]
    return {
        "classify":      any_agent(s),
        "boundary":      len(s["edges"]) > 0 and any_agent(s),
        "privilege":     any_agent(s),
        "reliability":   any_async(s) or a["side_effects"] != "none"
                         or a["autonomy"] in ("supervised", "autonomous"),
        "observability": any_agent(s),                      # hard directive: any agentic system
        "memory":        a.get("memory_hint", False),       # canonical input (round-codex: answers.memory_hint)
        "evals":         any_agent(s),
        "deploy":        a.get("greenfield") or a.get("changes_platform")
                         or a.get("adds_durable_runtime") or a.get("deploy_requested", False),
    }.get(lens, False)


def recommended_floor(s):
    """The RECOMMENDED floor — a deterministic function of the safety-relevant risk factors
    (expert judgment, NOT #10 activation). Membership uses only the factors it names."""
    a = s["answers"]
    floor = set()
    if any_agent(s):
        floor |= {"classify", "privilege", "observability", "evals"}
    if len(s["edges"]) > 0 and any_agent(s):
        floor.add("boundary")
    if a["side_effects"] == "irreversible":                                # recommend a human gate
        floor.add("reliability")
    if a["autonomy"] in ("supervised", "autonomous") and a["side_effects"] != "none":  # recommend a kill-switch
        floor.add("reliability")
    if any_async(s):                                                       # async needs idempotency/DLQ design
        floor.add("reliability")
    return floor


def topo_order(included, depends):
    """Deterministic dependency order, LENSES-index tie-break: repeatedly emit the FIRST
    lens in LENSES order whose deps are all already emitted (Kahn, single-ready choice)."""
    order, remaining = [], [l for l in LENSES if l in included]
    while remaining:
        for l in remaining:
            if all(d in order for d in depends.get(l, [])):
                order.append(l)
                remaining.remove(l)
                break
    return order


def compose(s):
    floor = recommended_floor(s)
    included = {l for l in LENSES if relevant(l, s)} | floor               # floor ⊆ included report sections
    rungs = included - floor                                               # offered, deferrable
    order = topo_order(included, DEPENDS)                                  # deterministic: topo, LENSES tie-break
    return {"report_sections": order, "floor": sorted(floor), "rungs": sorted(rungs)}
