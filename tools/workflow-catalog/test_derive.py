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
