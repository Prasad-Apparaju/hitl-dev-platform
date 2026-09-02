#!/usr/bin/env python3
"""Conformance for the plan sizer (#97).

Discipline as elsewhere in this directory: the load-bearing rules are asserted by hostile input,
not by a happy path. The two failures this file exists to prevent are (a) the two options
collapsing into the same list, which made an earlier draft of the design unbuildable, and (b) a
rule reading what an area HAS rather than what a change TOUCHES, which made a one-line fix in
well-documented code draw the longest plan.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

import yaml  # noqa: E402
import size_plan as S  # noqa: E402
from check_skips import load_catalog, resolve_crit  # noqa: E402

WORKFLOWS = os.path.join(ROOT, "ai", "shared", "workflows.yaml")
CATALOG = load_catalog(WORKFLOWS)
COSTS = yaml.safe_load(open(WORKFLOWS))["step_costs"]

SMALL = {"area": "billing", "dependents": [], "interfaces_changed": [], "events_changed": [],
         "tests_covering": ["test_refund.py"], "docs_affected": [], "data_migration": False,
         "reaches_production": False, "surfaces": ["api"], "multi_domain": False,
         "source_read_required": False}

BIG = {"area": "billing", "dependents": ["checkout", "reporting"],
       "interfaces_changed": ["RefundService.issue"], "events_changed": ["refund.issued"],
       "tests_covering": ["test_refund.py"], "docs_affected": ["docs/design/billing.md"],
       "data_migration": True, "reaches_production": True, "surfaces": ["api", "data"],
       "multi_domain": True, "source_read_required": False}


def _size(findings, tier):
    return S.size(findings, CATALOG, COSTS, tier, resolve_crit)


# ── the predicate language ───────────────────────────────────────────────────

def test_a_list_is_true_when_it_has_anything_in_it():
    assert S.truth("dependents", {"dependents": ["a"]}) is True
    assert S.truth("dependents", {"dependents": []}) is False


def test_a_missing_field_is_false_not_an_error():
    """An analysis that could not answer a question has not established the fact the rule needs.
    A rule firing on an unanswered question is worse than one that does not fire."""
    assert S.truth("dependents", {}) is False


def test_surfaces_asks_membership():
    assert S.truth("surfaces:ui", {"surfaces": ["ui", "api"]}) is True
    assert S.truth("surfaces:ui", {"surfaces": ["api"]}) is False
    assert S.truth("surfaces:ui", {}) is False


def test_any_and_all_differ():
    f = {"dependents": ["a"], "multi_domain": False}
    assert S.evaluate({"any": ["dependents", "multi_domain"]}, f) is True
    assert S.evaluate({"all": ["dependents", "multi_domain"]}, f) is False


def test_a_malformed_rule_raises_rather_than_defaulting():
    """NEG: silently treating an unreadable rule as true or false is how a step quietly stops
    being sized. It must be loud."""
    for bad in ({"any": []}, {"nope": ["x"]}, {"any": ["x"], "all": ["y"]}, 17):
        try:
            S.evaluate(bad, {})
        except ValueError:
            continue
        raise AssertionError("evaluate accepted %r" % (bad,))


# ── the two options are genuinely different ──────────────────────────────────

def test_fast_and_full_are_not_the_same_list():
    """The failure that made an earlier design unbuildable: one predicate did both jobs, so the
    fast track and full scale resolved identically and the choice offered nothing."""
    o = _size(SMALL, 1)
    assert S.plan(o, "fast") != S.plan(o, "full")
    assert len(S.plan(o, "fast")) < len(S.plan(o, "full"))


def test_a_small_change_draws_a_genuinely_short_plan():
    o = _size(SMALL, 1)
    fast = S.plan(o, "fast")
    assert len(fast) <= 12, fast
    for absent in ("adv_design", "adv_code", "arch_review", "qa_verify", "roi", "training"):
        assert absent not in fast, "%s should not be in a flagged one-line fix's fast track" % absent


def test_a_far_reaching_change_draws_a_long_one():
    o = _size(BIG, 3)
    fast = S.plan(o, "fast")
    for present in ("integration_verify", "review2", "arch_review", "impact_brief", "rollout"):
        assert present in fast, "%s should be in the fast track of a change that reaches that far" % present


# ── what the rules read ──────────────────────────────────────────────────────

def test_documenting_an_area_does_not_lengthen_its_plans():
    """The bug both walkthroughs hit on an earlier draft. `docs_affected` is what THIS CHANGE
    alters, so a change that touches no documented behaviour draws no docs work however
    thoroughly its area is documented."""
    o = _size(SMALL, 1)
    docs = next(x for x in o if x["step"] == "docs")
    assert docs["applies"] is False and "no docs affected" in docs["because"]


def test_a_brand_new_area_with_no_history_still_draws_what_it_needs():
    """The other direction. A new feature has no dependents and no existing tests, so rules keyed
    to an area's history would exclude nearly everything. Keyed to reach, the interface it
    publishes still pulls in the reviews."""
    new = dict(SMALL, dependents=[], tests_covering=[], docs_affected=[],
               interfaces_changed=["NewThing.create"], reaches_production=True)
    fast = S.plan(_size(new, 2), "fast")
    for present in ("arch_review", "review2", "qa_verify", "rollout"):
        assert present in fast, "%s missing for a new published interface" % present


# ── the floor ────────────────────────────────────────────────────────────────

def test_the_locked_set_matches_the_validator():
    """The sizer and check_skips must agree about what is load-bearing, or the plan offers to drop
    something the validator will then block."""
    for tier in (0, 1, 2, 3, 4):
        mine = S.locked_keys(CATALOG, tier, resolve_crit)
        theirs = {k for k, m in CATALOG.items()
                  if resolve_crit(m, tier) == "floor" or m.get("no_omit")}
        assert mine == theirs, (tier, sorted(mine ^ theirs))


def test_a_rule_cannot_drop_a_locked_step():
    """NEG: a locked step whose own rules would drop it must survive."""
    # `integration_verify` is floor at tier 2, and its rules key off dependents / multi_domain /
    # events_changed — all false for SMALL. So the rules say drop it and the floor says keep it,
    # which is the only case that actually proves the override. An earlier version used `deploy`,
    # whose rules say `always` anyway, and passed with the override deleted.
    o = _size(SMALL, 2)
    iv = next(x for x in o if x["step"] == "integration_verify")
    assert iv["locked"] is True, "integration_verify is floor at tier 2"
    assert iv["needed_now"] is True and iv["applies"] is True, \
        "its rules find nothing in this change; the floor must win anyway"
    assert "locked" in iv["because"]


def test_locked_steps_are_never_offered_as_exclusions():
    """They must not appear in `excluded`, because those become `not_applicable` ledger entries and
    check_skips blocks that on a floor step (RULE_OVER_FLOOR). Offering it would build a plan the
    validator refuses."""
    for findings, tier in ((SMALL, 1), (BIG, 3)):
        o = _size(findings, tier)
        locked = S.locked_keys(CATALOG, tier, resolve_crit)
        for opt in ("fast", "full"):
            dropped = {e["step"] for e in S.excluded(o, opt)}
            assert not (dropped & locked), sorted(dropped & locked)


def test_a_step_with_no_rules_fails_closed():
    """NEG: a step nobody wrote a rule for must be kept, not silently dropped."""
    o = S.size(SMALL, {"mystery": {"crit": "standard"}}, {}, 1, resolve_crit)
    assert o[0]["applies"] and o[0]["needed_now"]
    assert "no rules declared" in o[0]["because"]


# ── what a person is shown ───────────────────────────────────────────────────

def test_the_reason_names_the_finding_not_the_rule():
    """A person deciding whether to untick something needs the fact. "3 dependents" is actionable;
    "{any: [dependents]}" is not."""
    o = _size(BIG, 3)
    r = next(x for x in o if x["step"] == "review2")["because"]
    assert "multi domain" in r or "interfaces changed" in r
    assert "any" not in r and "{" not in r


def test_an_exclusion_carries_the_reason_it_was_excluded():
    """These become the ledger's `not_applicable` records, and the reason is what the retrospective
    reads back. An empty one records a step vanishing with no account of why."""
    for e in S.excluded(_size(SMALL, 1), "fast"):
        assert e["reason"].strip(), e


# ── the intake stub ──────────────────────────────────────────────────────────

def test_the_stub_certifies_clean_and_is_deliberately_not_an_active_change():
    """Two properties that pull in opposite directions and both matter.

    It must certify clean, or intake produces a file that fails the validator it is about to run.
    It must NOT count as an active change, because a stub carries no plan, so nothing has
    authorised a source edit yet. An earlier comment in the generator claimed the stub existed to
    satisfy that gate, which is the opposite of what it does.
    """
    import subprocess
    import check_skips as C

    gen = os.path.join(HERE, "gen_change.py")
    out = subprocess.run([sys.executable, gen, "--stub", "GH-1", "main", "2.8.0"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    doc = yaml.safe_load(out.stdout)

    assert C.check(doc, CATALOG) == [], C.check(doc, CATALOG)
    assert doc["status"] == "intake"
    assert doc["tier"] == 3 and doc["tier_provisional"] is True, "provisional tier must fail closed"
    assert "workflow" not in doc and "current_step" not in doc, (
        "a stub with either would satisfy hitl_change_active and unblock edits before a plan exists")
    assert doc["impact_record"], "the stub must name the record, or nothing can check it is missing"
