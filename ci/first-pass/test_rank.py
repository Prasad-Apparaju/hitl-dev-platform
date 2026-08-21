#!/usr/bin/env python3
"""Ranking the plan: the order a person reads, and what pins a step to the top."""
import os, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rank as R

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAT = yaml.safe_load(open(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml")))
COSTS = CAT["step_costs"]
SPINE = [s for s in CAT["spine"]["steps"] if "cond" not in s]


def test_a_step_the_change_does_not_engage_drops_one_rank():
    """`iac` is medium on an infrastructure change and less than that on a copy fix."""
    e = COSTS["iac"]
    assert R.shown_rank(e, paths=["infra/main.tf"]) == "medium"
    assert R.shown_rank(e, paths=["docs/readme.md"]) == "low"


def test_an_incident_in_the_area_raises_one_rank():
    e = COSTS["docs"]
    assert R.shown_rank(e, paths=["docs/x.md"]) == "medium"
    assert R.shown_rank(e, paths=["docs/x.md"], risky_domain=True) == "high"


def test_modulation_never_moves_a_locked_step():
    """A floor or no_omit step is pinned to high however the signals fall — the rank and the flag
    must never disagree, or someone reading ranks drops something the flags protect."""
    for key in ("deploy", "promote", "red", "green"):
        assert R.shown_rank(COSTS[key], paths=["nothing/relevant"], locked=True) == "high"

    # The cases above are all base-high, so they pass even with the pin removed — mutation testing
    # caught that. `pentest` is floor AND engages only on a security change, so on any other change
    # the modulation WOULD demote it. That is the case the pin exists for.
    assert R.shown_rank(COSTS["pentest"], paths=["scripts/demo.sh"], profile="fix") == "medium", (
        "precondition: unlocked, this step demotes")
    assert R.shown_rank(COSTS["pentest"], paths=["scripts/demo.sh"], profile="fix",
                        locked=True) == "high", "a floor step must not be argued down the list"


def test_missing_data_degrades_quietly_rather_than_raising():
    """A project with no step_costs, no manifest and no registry still gets a usable order."""
    ranked = R.rank_plan(SPINE, {}, tier=1)
    assert len(ranked) == len(SPINE)
    assert all(r["rank"] in R.RANKS for r in ranked)
    assert R.shown_rank(None) == "medium"
    assert R.shown_rank({"forgo_cost": "banana"}) == "medium"
    assert R.risky_domains(None, None) == {}
    assert R.touches_risky(["a/b"], None) is False


def test_absent_engages_counts_as_engaged():
    """Guessing 'not engaged' would silently demote every step nobody annotated."""
    assert R.engaged(None) and R.engaged("") and R.engaged({}) is True


def test_locked_steps_sort_first_then_by_rank_then_catalog_order():
    ranked = R.rank_plan(SPINE, COSTS, tier=2, paths=["src/app.py"], profile="fix")
    locked = [r for r in ranked if r["locked"]]
    assert locked and all(r["locked"] for r in ranked[:len(locked)]), "locked steps must lead"
    tail = [r for r in ranked if not r["locked"]]
    idx = [R.RANKS.index(r["rank"]) for r in tail]
    assert idx == sorted(idx, reverse=True), "unlocked steps must run high -> low"
    highs = [r["pos"] for r in tail if r["rank"] == "high"]
    assert highs == sorted(highs), "ties must keep catalog order so the list is stable"


def test_the_customers_change_puts_the_cheap_stuff_last():
    """One env var in a shell script: nothing it engages should outrank what it does."""
    ranked = R.rank_plan(SPINE, COSTS, tier=1, paths=["scripts/demo.sh"], profile="fix",
                         tags=["chore"])
    order = [r["key"] for r in ranked if not r["locked"]]
    for cheap in ("figma", "roi", "training", "figma_compare", "roi_30", "roi_90"):
        assert order.index(cheap) > order.index("review1"), (
            "%s outranks the code review on a one-line script change" % cheap)


def test_every_step_carries_its_protects_sentence_through():
    ranked = R.rank_plan(SPINE, COSTS, tier=2)
    blank = [r["key"] for r in ranked if not r["protects"].strip()]
    assert not blank, "these would render an empty reason beside their checkbox: %s" % blank
