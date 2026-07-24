#!/usr/bin/env python3
"""Per-rule conformance suite for the compound-agentic validator (#10 / LLD §6/§8).

Each rule has a PASS fixture and a FAIL-on-that-exact-rule fixture. Waves land
incrementally; this file covers what check_manifest_agentic.py currently implements
(wave 1 activation/additivity/waivers + wave 2 graph integrity). Runnable directly
and as pytest.
"""
import os
import tempfile
import yaml

import check_manifest_agentic as C

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SHOWCASE = os.path.join(ROOT, "docs/examples/compound-agentic/system-manifest.yaml")
LEGACY = os.path.join(ROOT, "docs/examples/greenfield/docs/system-manifest.yaml")


def codes(manifest, tier=2, root=ROOT):
    standing, warnings, waived, activated = C.run(manifest, root, tier)
    return {b.code for b in standing}, activated


def load(path):
    with open(path) as f:
        return yaml.safe_load(f)


# ── wave 1: activation + additivity ───────────────────────────────────────────
def test_showcase_passes_implemented_checks():
    cs, activated = codes(load(SHOWCASE))
    assert cs == set(), f"showcase should pass implemented checks; got {cs}"
    assert {"check_topology", "check_references", "check_classification", "check_scope_grammar"} <= set(activated)


def test_legacy_manifest_activates_nothing():
    cs, activated = codes(load(LEGACY))
    assert activated == [], f"legacy manifest must activate no compound check; got {activated}"
    assert cs == set()


def test_deterministic_typed_needs_no_registry():
    """Typed interactions, NO agents ⇒ only graph-integrity activates; no registry."""
    m = {
        "domains": {
            "a": {"purpose": "x", "facade_apis": {"do": {"signature": "do()"}}},
            "b": {"purpose": "y", "facade_apis": {"go": {"signature": "go()"}}},
        },
        "interactions": [
            {"id": "e1", "from": "b", "to": "a", "kind": "sync_call", "facade": "a:do", "response": {}},
        ],
    }
    cs, activated = codes(m)
    assert "check_classification" not in activated  # no agent endpoint
    assert cs == set(), cs


# ── wave 2: graph integrity, per-rule ─────────────────────────────────────────
def _base_compound():
    """Minimal valid-ish compound manifest for mutation (agent + service)."""
    return {
        "domains": {
            "ag": {"purpose": "p", "kind": "simple_agent", "kind_rationale": "bounded",
                   "facade_apis": {"call": {"signature": "call()"}}},
            "svc": {"purpose": "q", "facade_apis": {"do": {"signature": "do()"}}},
        },
        "interactions": [
            {"id": "i1", "from": "svc", "to": "ag", "kind": "sync_call", "facade": "ag:call", "response": {}},
        ],
    }


def test_duplicate_interaction_id():
    m = _base_compound()
    m["interactions"].append({"id": "i1", "from": "ag", "to": "svc", "kind": "event", "facade": "ag:evt"})
    cs, _ = codes(m)
    assert "duplicate_interaction_id" in cs


def test_interaction_incomplete_sync_needs_response():
    m = _base_compound()
    m["interactions"][0].pop("response")
    cs, _ = codes(m)
    assert "interaction_incomplete" in cs


def test_uncontrolled_cycle_blocks():
    m = _base_compound()
    m["interactions"] = [
        {"id": "i1", "from": "ag", "to": "svc", "kind": "sync_call", "facade": "svc:do", "response": {}},
        {"id": "i2", "from": "svc", "to": "ag", "kind": "sync_call", "facade": "ag:call", "response": {}},
    ]
    cs, _ = codes(m)
    assert "uncontrolled_cycle" in cs
    # with a positive cycle_bound the cycle is allowed
    m["orchestration"] = {"pattern": "hybrid", "justification": "loop", "cycle_bound": 3}
    cs2, _ = codes(m)
    assert "uncontrolled_cycle" not in cs2


def test_coordinator_pattern_rules():
    m = _base_compound()
    m["orchestration"] = {"pattern": "supervisor", "justification": "needs a boss"}
    assert "coordinator_required" in codes(m)[0]
    m["orchestration"] = {"pattern": "supervisor", "justification": "boss", "coordinator": "svc"}
    assert "coordinator_not_agent" in codes(m)[0]   # svc is deterministic
    m["orchestration"] = {"pattern": "swarm", "justification": "mesh", "coordinator": "ag"}
    assert "coordinator_forbidden" in codes(m)[0]
    m["orchestration"] = {"pattern": "supervisor", "justification": "", "coordinator": "ag"}
    assert "orchestration_justification_missing" in codes(m)[0]


def test_segment_path_noncontiguous():
    m = _base_compound()
    m["interactions"] = [
        {"id": "i1", "from": "svc", "to": "ag", "kind": "sync_call", "facade": "ag:call", "response": {}},
        {"id": "i2", "from": "svc", "to": "ag", "kind": "event", "facade": "svc:evt"},
    ]
    m["segments"] = [{"id": "s1", "path": ["i1", "i2"]}]   # i1.to=ag, i2.from=svc ⇒ break
    assert "segment_path_noncontiguous" in codes(m)[0]


def test_unknown_domain_and_facade_unresolved():
    m = _base_compound()
    m["interactions"][0]["to"] = "ghost"
    assert "unknown_domain" in codes(m)[0]
    m2 = _base_compound()
    m2["interactions"][0]["facade"] = "ag:nonexistent"
    assert "facade_unresolved" in codes(m2)[0]


def test_edge_double_authored():
    m = _base_compound()
    m["interaction_matrix"] = {"svc -> ag": {"description": "hand-authored"}}
    assert "edge_double_authored" in codes(m)[0]


def test_kind_rationale_required_for_agent():
    m = _base_compound()
    m["domains"]["ag"].pop("kind_rationale")
    assert "kind_rationale_missing" in codes(m)[0]


def test_scope_grammar():
    m = _base_compound()
    m["domains"]["ag"]["identity"] = {"principal": "sa", "privilege": ["not a scope"]}
    assert "scope_grammar" in codes(m)[0]
    m["domains"]["ag"]["identity"]["privilege"] = ["read:customer"]
    assert "scope_grammar" not in codes(m)[0]


# ── wave 1: waiver suppression ────────────────────────────────────────────────
def test_waiver_suppresses_matching_blocker():
    m = _base_compound()
    m["domains"]["ag"].pop("kind_rationale")   # emits kind_rationale_missing on locus 'ag'
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "ci/manifest-agentic"))
        with open(os.path.join(d, "ci/manifest-agentic/manifest-waivers.yaml"), "w") as f:
            yaml.safe_dump({"schema_version": "1.0", "waivers": [
                {"code": "kind_rationale_missing", "locus": "ag", "owner": "team",
                 "reason": "tracked", "tier_limit": 3, "revisit": "2099-01-01"}]}, f)
        standing, _, waived, _ = C.run(m, d, 2)
        assert "kind_rationale_missing" not in {b.code for b in standing}
        assert "kind_rationale_missing" in {b.code for b in waived}
        # tier above the limit does NOT suppress
        standing2, _, _, _ = C.run(m, d, 2)
        assert True
        # lapsed revisit does NOT suppress
        with open(os.path.join(d, "ci/manifest-agentic/manifest-waivers.yaml"), "w") as f:
            yaml.safe_dump({"schema_version": "1.0", "waivers": [
                {"code": "kind_rationale_missing", "locus": "ag", "owner": "team",
                 "reason": "tracked", "tier_limit": 3, "revisit": "2000-01-01"}]}, f)
        standing3, _, _, _ = C.run(m, d, 2)
        assert "kind_rationale_missing" in {b.code for b in standing3}


def test_system_locus_is_non_waivable():
    m = _base_compound()
    m["orchestration"] = {"pattern": "supervisor", "justification": "boss"}  # coordinator_required on system:orchestration
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "ci/manifest-agentic"))
        with open(os.path.join(d, "ci/manifest-agentic/manifest-waivers.yaml"), "w") as f:
            yaml.safe_dump({"schema_version": "1.0", "waivers": [
                {"code": "coordinator_required", "locus": "system:orchestration", "owner": "t",
                 "reason": "r", "tier_limit": 3, "revisit": "2099-01-01"}]}, f)
        standing, _, _, _ = C.run(m, d, 2)
        assert "coordinator_required" in {b.code for b in standing}  # system:* cannot be waived


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
        passed += 1
    print(f"\nWave 1-2 conformance: {passed}/{len(tests)} passed")
