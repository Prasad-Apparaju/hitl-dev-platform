#!/usr/bin/env python3
"""Conformance for the Advisor records/handoff (#39 / LLD §7, test-plan). The load-bearing
property: the handoff authors NO manifest field (NO-AUTHOR)."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "agentic-advisor"))
import compose as C
import records as R

STATE = {
    "feature": "refund-assistant",
    "components": [{"id": "intake_agent", "role": "agent", "proposed_kind": "simple_agent", "rationale": "bounded classify"},
                   {"id": "resolver_agent", "role": "agent", "proposed_kind": "simple_agent", "rationale": "bounded draft"},
                   {"id": "refund_service", "role": "service", "proposed_kind": "deterministic", "rationale": "system of record"}],
    "edges": [{"id": "e1", "from": "intake_agent", "to": "resolver_agent", "transport": "sync_call"},
              {"id": "e2", "from": "resolver_agent", "to": "refund_service", "transport": "async_task"}],
    "answers": {"stakes": "customer_facing", "side_effects": "irreversible", "data": "pii",
                "autonomy": "supervised", "scale": "small", "greenfield": True},
    "skips": [{"control": "reliability", "owner": "pm", "reason": "manual rollback for v1"}],
}


def test_handoff_is_neutral_shape():
    h = R.generate_handoff(STATE)
    assert h["schema_version"] == "1.0"
    for c in h["components"]:
        assert set(c) == {"id", "role", "proposed_kind", "rationale"}   # role+proposed_kind, never `kind`
    for cn in h["connections"]:
        assert set(cn) == {"from", "to", "transport"}                   # neutral edge, not `interactions`
    for r in h["recommendations"]:
        assert "target_path_hint" in r and "id" in r
    assert h["skips"] == STATE["skips"]                                 # recorded skip, not a #10 waiver


def test_handoff_authors_no_manifest_field():
    h = R.generate_handoff(STATE)
    assert R.handoff_authors_no_manifest_field(h) == set(), "handoff must contain no system-manifest field"
    # a manifest field injected anywhere is caught
    bad = copy.deepcopy(h)
    bad["components"][0]["kind"] = "simple_agent"
    assert "kind" in R.handoff_authors_no_manifest_field(bad)


def test_decision_record_is_pure_function():
    a = R.generate_decision_record(STATE)
    b = R.generate_decision_record(copy.deepcopy(STATE))
    assert a == b                                                       # REC-GEN: pure function of state
    assert "Floor" in a and "Recorded skips" in a and "reliability" in a


def test_rerun_reconcile_flags_stale_and_retires():
    old = dict(STATE)
    old["decisions"] = [{"id": "d1", "attaches_to": "intake_agent", "chosen": "simple_agent"},
                        {"id": "d2", "attaches_to": "resolver_agent", "chosen": "simple_agent"}]
    new = copy.deepcopy(STATE)
    new["components"][0]["proposed_kind"] = "deep_agent"                # gating input changed ⇒ stale
    new["components"] = [c for c in new["components"] if c["id"] != "resolver_agent"]  # removed ⇒ retired
    rec = R.reconcile(old, new)
    d1 = next(d for d in rec["decisions"] if d["id"] == "d1")
    assert d1["state"] == "stale"
    assert any(d["id"] == "d2" and d["state"] == "retired" for d in rec["retired"])
    assert rec["skips"] == STATE["skips"]                              # skips reconciled, never dropped


def test_skip_is_not_a_waiver():
    # the record uses "skip"; "waiver" is reserved for a human-authored #10 exception (ADV-12)
    rec = R.generate_decision_record(STATE)
    assert "waiver" not in rec.lower()
    assert "skip" in rec.lower()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nRecords/handoff (#39/wave C): {len(tests)}/{len(tests)} passed")
