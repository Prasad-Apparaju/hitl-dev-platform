#!/usr/bin/env python3
"""Conformance for the Advisor map renderer (#40 / LLD §6, test-plan MAP-*/ROLE-TOTAL)."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "agentic-advisor"))
import compose as C
import render_map as M

SCEN = {
    "feature": "refund-assistant",
    "components": [{"id": "intake_agent", "role": "agent", "proposed_kind": "simple_agent"},
                   {"id": "account_service", "role": "service", "proposed_kind": "deterministic"},
                   {"id": "sessions", "role": "datastore", "proposed_kind": "deterministic"}],
    "edges": [{"id": "e1", "from": "intake_agent", "to": "account_service", "transport": "sync_call"},
              {"id": "e2", "from": "account_service", "to": "sessions", "transport": "async_task"}],
    "answers": {"stakes": "internal", "side_effects": "none", "autonomy": "assisted", "greenfield": True},
}


def test_render_two_core_renderings():
    out = M.render(SCEN)
    assert set(out) == {"terminal", "mermaid"}
    assert "graph LR" in out["mermaid"] and "intake_agent" in out["mermaid"]
    assert "intake_agent" in out["terminal"] and "getting:" in out["terminal"]


def test_no_br_in_mermaid():
    # mermaid must not use <br/> (repo lint) — labels use " · "
    assert "<br" not in M.render(SCEN)["mermaid"]


def test_role_total():
    assert M.validate_roles(SCEN) == []
    bad = copy.deepcopy(SCEN)
    bad["components"][0]["role"] = "robot"        # not in the enum
    assert "intake_agent" in M.validate_roles(bad)
    missing = copy.deepcopy(SCEN)
    missing["components"][0].pop("role")
    assert "intake_agent" in M.validate_roles(missing)


def test_not_needed_breakdown():
    getting, available, not_needed = M._breakdown(SCEN, C.compose(SCEN))
    assert "memory" in not_needed              # no memory_hint ⇒ not recommended
    assert "reliability" in getting            # the async edge makes reliability floor-level
    assert "classify" in getting


def test_mermaid_edges_are_valid_form():
    # F6: no combined inline+pipe label; dotted arrow for async/event; every pipe label non-empty
    m = M.render(SCEN)["mermaid"]
    assert "-. async .->" not in m and "-. event .->" not in m
    assert "||" not in m                       # an empty pipe label is a parse error
    assert "-.->" in m                         # the async edge uses a dotted arrow


def test_deterministic():
    assert M.render(SCEN) == M.render(copy.deepcopy(SCEN))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nMap renderer (#40/wave D): {len(tests)}/{len(tests)} passed")
