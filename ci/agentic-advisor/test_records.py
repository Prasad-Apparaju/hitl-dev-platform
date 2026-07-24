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


def test_guard_catches_full_manifest_vocabulary():
    # F2: the NO-AUTHOR guard covers ALL #10 manifest fields, not a 7-key denylist
    for f in ("observability", "orchestration", "segments", "evals", "memory", "lifecycle",
              "deep_agent", "kind_rationale", "authorization", "async", "facade_apis"):
        h = R.generate_handoff(STATE)
        h[f] = {"x": 1}
        assert f in R.handoff_authors_no_manifest_field(h), f


def test_skips_are_projected_not_verbatim():
    # F2: an injected manifest field inside a skip does NOT reach the handoff (skip is projected)
    s = copy.deepcopy(STATE)
    s["skips"] = [{"control": "reliability", "owner": "pm", "reason": "r", "lifecycle": {"x": 1}, "evals": {"y": 2}}]
    h = R.generate_handoff(s)
    assert R.handoff_authors_no_manifest_field(h) == set()
    assert set(h["skips"][0]) == {"control", "owner", "reason"}


def test_ref_integrity():
    # F2: HANDOFF-REF-INTEGRITY — unique ids, hint is a non-empty path string
    h = R.generate_handoff(STATE)
    assert R.handoff_ref_integrity(h) == []
    dup = copy.deepcopy(h)
    dup["recommendations"].append(dict(dup["recommendations"][0]))
    assert R.handoff_ref_integrity(dup)
    empty = copy.deepcopy(h)
    empty["recommendations"][0]["target_path_hint"] = ""
    assert R.handoff_ref_integrity(empty)


def test_validate_skips_rejects_silent():
    # F8 / FLOOR-SKIP-SILENT: a skip must record control+owner+reason
    assert R.validate_skips({"skips": [{"control": "reliability"}]})
    assert R.validate_skips({"skips": [{"control": "x", "owner": "o", "reason": "r"}]}) == []


def test_reconcile_risk_answer_and_removed_edge():
    # F4: a changed risk answer (via depends_on) flags stale; a removed EDGE retires its decision
    old = dict(STATE)
    old["decisions"] = [{"id": "d1", "attaches_to": "e1", "depends_on": ["answers.side_effects"], "chosen": "gate"}]
    new = copy.deepcopy(STATE)
    new["answers"]["side_effects"] = "reversible"
    rec = R.reconcile(old, new)
    assert any(d["id"] == "d1" and d["state"] == "stale" for d in rec["decisions"])
    old2 = dict(STATE)
    old2["decisions"] = [{"id": "d2", "attaches_to": "e1", "chosen": "x"}]
    new2 = copy.deepcopy(STATE)
    new2["edges"] = [e for e in new2["edges"] if e["id"] != "e1"]
    rec2 = R.reconcile(old2, new2)
    assert any(d["id"] == "d2" and d["state"] == "retired" for d in rec2["retired"])


def test_reconcile_carries_deferrals_and_deploy():
    # F4: deferrals + deploy are carried on rerun, not silently dropped
    old = dict(STATE)
    old["deferrals"] = [{"rung": "deploy", "reason": "later"}]
    old["deploy"] = {"recommend": "managed"}
    rec = R.reconcile(old, copy.deepcopy(STATE))
    assert rec["deferrals"] == old["deferrals"] and rec["deploy"] == old["deploy"]


def test_decision_record_renders_decisions():
    # F5: the decision record shows chosen/rejected/rationale
    s = copy.deepcopy(STATE)
    s["decisions"] = [{"attaches_to": "resolver_agent", "chosen": "simple_agent",
                       "rejected": ["deep_agent"], "rationale": "bounded task"}]
    rec = R.generate_decision_record(s)
    assert "Menu decisions" in rec and "simple_agent" in rec and "bounded task" in rec


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
