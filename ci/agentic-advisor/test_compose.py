#!/usr/bin/env python3
"""Per-rule conformance for the Advisor composer (#35 / LLD §4, test-plan §4).
Runnable directly and as pytest. Fixtures use the canonical `proposed_kind`/`transport`
shape (round-10 B3)."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "agentic-advisor"))
import compose as C

# ── canonical fixtures (test-plan §4) ─────────────────────────────────────────
LOW = {  # Tier-1, 2 agents, read-only, internal, greenfield
    "components": [{"id": "a1", "role": "agent", "proposed_kind": "simple_agent"},
                   {"id": "a2", "role": "agent", "proposed_kind": "simple_agent"}],
    "edges": [{"id": "e1", "from": "a1", "to": "a2", "transport": "sync_call"}],
    "answers": {"stakes": "internal", "side_effects": "none", "data": "none",
                "autonomy": "assisted", "scale": "small", "greenfield": True},
}
HIGH = {  # Tier-2, 4 components (2 agents), irreversible, PII, supervised, one async edge, greenfield
    "components": [{"id": "a1", "role": "agent", "proposed_kind": "simple_agent"},
                   {"id": "a2", "role": "agent", "proposed_kind": "simple_agent"},
                   {"id": "s1", "role": "service", "proposed_kind": "deterministic"},
                   {"id": "d1", "role": "datastore", "proposed_kind": "deterministic"}],
    "edges": [{"id": "e1", "from": "a1", "to": "s1", "transport": "sync_call"},
              {"id": "e2", "from": "a1", "to": "a2", "transport": "sync_call"},
              {"id": "e3", "from": "a2", "to": "d1", "transport": "async_task"}],
    "answers": {"stakes": "customer_facing", "side_effects": "irreversible", "data": "pii",
                "autonomy": "supervised", "scale": "small", "greenfield": True},
}
ASYNC_ONLY = {  # reversible, assisted, one async edge — reliability must still be floor-level
    "components": [{"id": "a1", "role": "agent", "proposed_kind": "simple_agent"},
                   {"id": "a2", "role": "agent", "proposed_kind": "simple_agent"}],
    "edges": [{"id": "e1", "from": "a1", "to": "a2", "transport": "async_task"}],
    "answers": {"stakes": "low", "side_effects": "reversible", "data": "internal",
                "autonomy": "assisted", "scale": "small"},
}


def test_compose_low():
    r = C.compose(LOW)
    assert r["report_sections"] == ["classify", "boundary", "privilege", "observability", "evals", "deploy"]
    assert r["floor"] == ["boundary", "classify", "evals", "observability", "privilege"]
    assert r["rungs"] == ["deploy"]                      # deploy is a rung (greenfield), never floor


def test_compose_high():
    r = C.compose(HIGH)
    assert r["report_sections"] == ["classify", "boundary", "privilege", "reliability", "observability", "evals", "deploy"]
    assert r["floor"] == ["boundary", "classify", "evals", "observability", "privilege", "reliability"]
    assert r["rungs"] == ["deploy"]


def test_async_reliability_is_floor_level():
    # reversible + assisted, but one async edge ⇒ reliability recommended in the floor (blocker 4)
    r = C.compose(ASYNC_ONLY)
    assert "reliability" in r["floor"]
    assert r["report_sections"] == ["classify", "boundary", "privilege", "reliability", "observability", "evals"]
    assert r["rungs"] == []                              # not greenfield ⇒ no deploy


def test_prune_deploy_when_not_greenfield():
    m = copy.deepcopy(LOW)
    m["answers"].pop("greenfield")                       # a change to an existing system
    assert "deploy" not in C.compose(m)["report_sections"]


def test_compose_takes_no_tier_and_is_deterministic():
    import inspect
    assert "tier" not in inspect.signature(C.compose).parameters   # no tier input (no computed depth)
    assert C.compose(HIGH) == C.compose(copy.deepcopy(HIGH))         # deterministic (ADV-12)


def test_topo_order_high_reliability_before_deploy():
    # the LENSES-tie-break Kahn (not a generic batching Kahn) puts reliability before deploy
    inc = {"classify", "boundary", "privilege", "reliability", "observability", "evals", "deploy"}
    assert C.topo_order(inc, C.DEPENDS) == ["classify", "boundary", "privilege", "reliability", "observability", "evals", "deploy"]


def test_no_hang_reliability_without_boundary():
    # F1: a single irreversible agent, no edges ⇒ reliability recommended WITHOUT boundary — must not hang
    r = C.compose({"components": [{"id": "a1", "role": "agent", "proposed_kind": "simple_agent"}],
                   "edges": [], "answers": {"side_effects": "irreversible", "autonomy": "assisted"}})
    assert "reliability" in r["floor"] and "boundary" not in r["report_sections"]


def test_partial_state_does_not_crash():
    # F3: a mid-intake render with answers not yet elicited must not KeyError
    r = C.compose({"components": [{"id": "a1", "role": "agent", "proposed_kind": "simple_agent"}], "edges": [], "answers": {}})
    assert r["report_sections"]


def test_blank_yaml_sections_degrade_to_empty():
    # round-2 F3: empty YAML sections parse to None (not []); accessors must degrade, not crash
    r = C.compose({"feature": "x", "components": None, "edges": None, "answers": None})
    assert r == {"report_sections": [], "floor": [], "rungs": []}
    # a non-dict answers / non-list components likewise degrade (compose never crashes)
    assert C.compose({"components": "oops", "edges": 5, "answers": ["bad"]})["report_sections"] == []
    # validate_scenario is the FINALIZE validator: it surfaces malformed entries (doesn't crash, doesn't skip silently)
    errs = C.validate_scenario({"components": [None, "x"], "edges": [None]})
    assert len(errs) == 3


def test_validate_scenario_flags_container_valued_enum_without_crashing():
    # round-3 H1: a YAML slip making proposed_kind/transport a list/dict is unhashable — the
    # `in` test must be guarded so the gate FLAGS it instead of crashing with TypeError.
    errs = C.validate_scenario({"components": [{"id": "a", "proposed_kind": ["deep_agent"]}],
                                "edges": [{"id": "e", "transport": {"k": 1}}]})
    assert len(errs) == 2


def test_none_root_does_not_crash():
    # round-3 L4: a None root (empty file) degrades, never AttributeErrors
    assert C.compose(None) == {"report_sections": [], "floor": [], "rungs": []}
    assert C.validate_scenario(None) == []


def test_validate_scenario_flags_container_valued_id():
    # round-4 F1: a dict/list id breaks id-keying downstream (unhashable) — surface it, don't stay silent
    errs = C.validate_scenario({"components": [{"id": {"x": 1}, "proposed_kind": "simple_agent"}],
                                "edges": [{"id": ["e"], "transport": "sync_call"}]})
    assert len(errs) == 2


def test_validate_scenario_flags_bad_enums():
    # F8: a typo'd proposed_kind / transport is surfaced, not silently demoted
    errs = C.validate_scenario({"components": [{"id": "a1", "proposed_kind": "deep-agent"}],
                                "edges": [{"id": "e1", "transport": "stream"}]})
    assert len(errs) == 2


def test_no_agent_no_sections():
    det = {"components": [{"id": "s1", "role": "service", "proposed_kind": "deterministic"}],
           "edges": [], "answers": {"side_effects": "none", "autonomy": "assisted"}}
    r = C.compose(det)
    assert r["report_sections"] == [] and r["floor"] == []   # not agentic ⇒ nothing recommended


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nComposer (#39/wave A): {len(tests)}/{len(tests)} passed")
