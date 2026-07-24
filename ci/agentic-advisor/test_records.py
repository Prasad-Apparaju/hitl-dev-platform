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


def test_reconcile_tolerates_idless_edge_and_string_depends_on():
    # round-2 F4: an id-less edge must not crash reconcile (was `{e["id"]: e}` KeyError);
    # a string `depends_on` is ONE path, not a char-iterable (typo'd path no longer silently confirms).
    old = {"components": [{"id": "a", "proposed_kind": "simple_agent"}],
           "edges": [{"from": "a", "to": "b", "transport": "sync_call"}],   # NO id
           "decisions": [{"id": "d1", "attaches_to": "a", "depends_on": "answers.side_effects", "state": "confirmed"}],
           "answers": {"side_effects": "none"}}
    new = {"components": [{"id": "a", "proposed_kind": "deep_agent"}],       # kind changed ⇒ stale
           "edges": [{"from": "a", "to": "b", "transport": "sync_call"}],
           "answers": {"side_effects": "irreversible"}}                     # depends_on target changed too
    rec = R.reconcile(old, new)                                             # must not raise
    assert rec["decisions"][0]["state"] == "stale"


def test_validate_skips_does_not_crash_on_structure():
    # round-2: a dict/list-valued skip field is FLAGGED, never crashes `.strip()`
    assert R.validate_skips({"skips": [{"control": {"nested": 1}, "owner": "pm", "reason": "r"}]})
    assert R.validate_skips({"skips": ["not-a-dict"]})
    assert R.validate_skips({"skips": None}) == []                          # blank YAML section


def test_generate_handoff_survives_blank_state():
    # round-2 F3: blank/None sections (mid-intake YAML) don't crash record generation
    blank = {"feature": "x", "components": None, "edges": None, "answers": None, "skips": None}
    h = R.generate_handoff(blank)
    assert h["components"] == [] and h["connections"] == [] and h["skips"] == []
    assert R.handoff_authors_no_manifest_field(h) == set()
    assert "Floor" in R.generate_decision_record(blank)


def test_decision_record_tolerates_junk_entries():
    # round-3 H2: non-dict decisions/skips + a non-list `rejected` must not crash the record
    # (every sibling — handoff/reconcile/validate_skips — already tolerates this)
    s = {"feature": "f", "decisions": [{"chosen": "a", "rejected": 5}, "STRAY", None],
         "skips": [{"control": "x", "owner": "o", "reason": "r"}, None]}
    rec = R.generate_decision_record(s)                     # must not raise
    assert "Menu decisions" in rec and "chose **a**" in rec


def test_reconcile_id_overlap_keeps_live_decision():
    # round-3 M1: a decision on component `x` must survive removal of a same-id EDGE `x`
    # (components + edges share the attaches_to namespace — the second disjunct must not fire)
    old = {"components": [{"id": "x", "proposed_kind": "simple_agent"}],
           "edges": [{"id": "x", "from": "a", "to": "b"}],
           "decisions": [{"id": "d1", "attaches_to": "x", "state": "confirmed"}], "answers": {}}
    new = {"components": [{"id": "x", "proposed_kind": "simple_agent"}], "edges": [], "answers": {}}
    rec = R.reconcile(old, new)
    assert rec["decisions"][0]["state"] == "confirmed" and rec["retired"] == []


def test_reconcile_surfaces_typoed_refs():
    # round-3 M2: a ghost attaches_to and a typo'd depends_on both silently disable re-review —
    # reconcile must WARN (never silently leave the decision confirmed with staleness dead)
    old = {"components": [{"id": "a", "proposed_kind": "simple_agent"}], "edges": [],
           "decisions": [{"id": "c", "attaches_to": "ghost", "depends_on": "answers.side_efects"}],
           "answers": {"side_effects": "none"}}
    new = {"components": [{"id": "a", "proposed_kind": "simple_agent"}], "edges": [],
           "answers": {"side_effects": "irreversible"}}
    warns = R.reconcile(old, new)["warnings"]
    assert any("attaches_to" in w for w in warns) and any("depends_on" in w for w in warns)
    # a CORRECT path warns not at all and still flags stale
    good = {"components": [{"id": "a", "proposed_kind": "simple_agent"}], "edges": [],
            "decisions": [{"id": "c2", "attaches_to": "a", "depends_on": "answers.side_effects"}],
            "answers": {"side_effects": "none"}}
    rec = R.reconcile(good, new)
    assert rec["warnings"] == [] and rec["decisions"][0]["state"] == "stale"
    assert R.validate_decision_refs(old)                   # finalize-time check surfaces the same typos


def test_static_fallback_is_superset_of_live_vocabulary():
    # round-3 L1: if the #10 import ever fails, the fallback must never be WEAKER than the live
    # derivation — so a manifest field can't slip past the guard in degraded mode.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ci", "manifest-agentic"))
    import check_manifest_agentic as m10
    live = set()
    for fields in m10.FIELD_SPEC.values():
        live |= set(fields)
    assert (live - R._HANDOFF_NEUTRAL) <= R._STATIC_MANIFEST_FIELDS


def test_records_tolerate_none_root():
    # round-3 L4
    assert R.generate_handoff(None)["components"] == []
    assert "Floor" in R.generate_decision_record(None)
    assert R.reconcile(None, None)["decisions"] == []


def test_verbatim_channels_cannot_smuggle_via_neutral_keys():
    # round-4 F2 (the near-miss on NO-AUTHOR): role/proposed_kind/transport were emitted verbatim,
    # so a dict keyed only on neutral names (id/from/to/owner — all real #10 fields, excluded from
    # the guard) rode into the handoff carrying an authored manifest value. Now scalar-coerced.
    s = {"feature": "f",
         "components": [{"id": "a", "role": {"id": "i1", "from": "x", "to": "billing", "owner": "attacker"},
                         "proposed_kind": {"kind": "deep_agent", "uses": ["invoke:billing"]}}],
         "edges": [{"id": "e", "from": "a", "to": "a", "transport": {"async": {"delivery": "at_least_once"}}}],
         "answers": {}}
    h = R.generate_handoff(s)
    assert R.handoff_authors_no_manifest_field(h) == set()          # nothing smuggled
    c0, cn0 = h["components"][0], h["connections"][0]
    assert c0["role"] is None and c0["proposed_kind"] is None and cn0["transport"] is None  # coerced, not verbatim
    # a well-formed scalar still passes through untouched
    good = R.generate_handoff({"components": [{"id": "a", "role": "agent", "proposed_kind": "simple_agent"}],
                               "edges": [{"id": "e", "from": "a", "to": "a", "transport": "sync_call"}]})
    assert good["components"][0]["role"] == "agent" and good["connections"][0]["transport"] == "sync_call"


def test_container_valued_ids_and_refs_do_not_crash():
    # round-4 F1: an unhashable (dict/list) id / attaches_to must not crash the id-keyed maps —
    # every gate function degrades it to unresolvable and (where appropriate) warns.
    assert R.validate_decision_refs({"decisions": [{"id": "d", "attaches_to": {"a": 1}}]})   # warns, no crash
    rec = R.reconcile({"components": [{"id": {"x": 1}}], "edges": [{"id": ["y"]}],
                       "decisions": [{"id": "d", "attaches_to": {"a": 1}}]}, {"components": []})
    assert isinstance(rec["decisions"], list)                       # did not raise


def test_reconcile_retires_on_namespace_flip():
    # round-4 F3 (inverse of M1): component `x` removed while an edge `x` appears is NOT the same
    # entity — the decision must retire, not silently survive attached to the impostor.
    old = {"components": [{"id": "x", "proposed_kind": "simple_agent"}], "edges": [],
           "decisions": [{"id": "d1", "attaches_to": "x", "state": "confirmed"}], "answers": {}}
    new = {"components": [], "edges": [{"id": "x", "from": "a", "to": "b"}], "answers": {}}
    rec = R.reconcile(old, new)
    assert rec["decisions"] == [] and [d["attaches_to"] for d in rec["retired"]] == ["x"]
    # and the M1 keep-case (component stays, same-id edge removed) must STILL be preserved
    keep = R.reconcile({"components": [{"id": "x", "proposed_kind": "simple_agent"}], "edges": [{"id": "x", "from": "a", "to": "b"}],
                        "decisions": [{"id": "d", "attaches_to": "x"}], "answers": {}},
                       {"components": [{"id": "x", "proposed_kind": "simple_agent"}], "edges": [], "answers": {}})
    assert keep["decisions"][0]["state"] == "confirmed" and keep["retired"] == []


def test_validate_skips_tolerates_none_root():
    assert R.validate_skips(None) == []                             # round-4 F4


def test_malformed_depends_on_is_warned_not_ignored():
    # round-4 F6: a dict-valued depends_on can't resolve — it must warn, not silently no-op
    assert R.validate_decision_refs({"components": [{"id": "a"}],
                                     "decisions": [{"id": "d", "attaches_to": "a", "depends_on": {"x": 1}}]})


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
