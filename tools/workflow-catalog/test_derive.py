"""Tests for the numberless-catalog deriver. Run: pytest tools/workflow-catalog/test_derive.py"""

from __future__ import annotations

import derive


def _steps(*specs):
    """specs: (key, phase) or (key, phase, parent) for substeps."""
    out = []
    for spec in specs:
        if len(spec) == 3:
            out.append({"key": spec[0], "label": spec[0], "phase": spec[1],
                        "substep": True, "parent": spec[2]})
        else:
            out.append({"key": spec[0], "label": spec[0], "phase": spec[1]})
    return out


def test_sequential_numbering():
    d = derive.derive_steps(_steps(("a", "P1"), ("b", "P1"), ("c", "P2")))
    assert [x["n"] for x in d] == ["1", "2", "3"]
    assert derive.total_of(d) == 3


def test_substep_gets_letter_and_does_not_increment_total():
    d = derive.derive_steps(_steps(
        ("rev1", "Verify"), ("rev2", "Verify"), ("arch", "Verify", "rev2"), ("rerun", "Verify")))
    ns = [x["n"] for x in d]
    assert ns == ["1", "2", "2a", "3"]
    assert derive.total_of(d) == 3  # substep did not bump the denominator


def test_phase_relative_numbering():
    d = derive.derive_steps(_steps(
        ("a", "Design"), ("b", "Design"), ("c", "Build"), ("d", "Build")))
    assert [x["phase_step"] for x in d] == ["Design.1", "Design.2", "Build.1", "Build.2"]


def test_substep_phase_step_letter():
    d = derive.derive_steps(_steps(("r1", "Verify"), ("r2", "Verify"), ("a", "Verify", "r2")))
    assert d[-1]["phase_step"] == "Verify.2a"


def test_active_steps_filters_conditionals():
    steps = [
        {"key": "x", "phase": "P"},
        {"key": "perf_step", "phase": "P", "cond": "perf"},
        {"key": "sec_step", "phase": "P", "cond": "security"},
    ]
    base = derive.active_steps(steps, None)
    assert [s["key"] for s in base] == ["x"]
    with_perf = derive.active_steps(steps, {"perf"})
    assert [s["key"] for s in with_perf] == ["x", "perf_step"]


def test_inserting_a_step_renumbers_downstream_with_zero_key_changes():
    before = derive.derive_steps(_steps(("a", "P"), ("b", "P"), ("c", "P")))
    after = derive.derive_steps(_steps(("a", "P"), ("new", "P"), ("b", "P"), ("c", "P")))
    # keys are stable; only the derived numbers shift
    assert {x["key"]: x["n"] for x in before} == {"a": "1", "b": "2", "c": "3"}
    assert {x["key"]: x["n"] for x in after} == {"a": "1", "new": "2", "b": "3", "c": "4"}


# --- profile / tag resolution (against the real catalog) ---

import yaml  # noqa: E402
from pathlib import Path  # noqa: E402

CATALOG = yaml.safe_load((Path(derive.__file__).parent / "catalog.yaml").read_text())


def _keys(profile, tags=None):
    return [s["key"] for s in derive.profile_steps(CATALOG, profile, tags)]


def test_feature_profile_equals_base_spine():
    # Feature activates nothing and excludes nothing: identical to the spine base view,
    # which is what reproduces the runtime `development` workflow.
    feature = _keys("feature")
    base = [s["key"] for s in derive.active_steps(CATALOG["spine"]["steps"], None)]
    assert feature == base
    assert "baseline" not in feature and "pentest" not in feature


def test_security_profile_activates_sec_design_and_pentest():
    keys = _keys("security")
    assert "sec_design" in keys and "pentest" in keys
    r = derive.resolve(CATALOG, "security")
    assert "security_review" in r["required_evidence"]
    assert r["skip_authority"].get("security_review") == "never"


def test_upgrade_profile_activates_cve_audit_only():
    keys = _keys("upgrade")
    assert "cve_audit" in keys
    assert "sec_design" not in keys and "pentest" not in keys
    assert "cve_audit" in derive.resolve(CATALOG, "upgrade")["required_evidence"]


def test_perf_tag_activates_baseline_and_adds_evidence():
    assert "baseline" not in _keys("feature")
    assert "baseline" in _keys("feature", ["perf"])
    assert "perf_budget_met" in derive.resolve(CATALOG, "feature", ["perf"])["required_evidence"]


def test_tech_change_excludes_functional_steps():
    keys = _keys("tech_change")
    for excluded in ("figma", "roi", "training", "figma_compare"):
        assert excluded not in keys


def test_tags_compose_evidence():
    r = derive.resolve(CATALOG, "fix", ["refactor", "perf"])
    ev = r["required_evidence"]
    assert "regression_test" in ev          # from fix
    assert "behavior_unchanged" in ev        # from refactor
    assert "perf_budget_met" in ev           # from perf
