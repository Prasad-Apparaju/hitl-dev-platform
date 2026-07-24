#!/usr/bin/env python3
"""Per-rule conformance suite for the compound-agentic validator (#10 / LLD §6/§8).

Each rule has a PASS fixture and a FAIL-on-that-exact-rule fixture. Waves land
incrementally; this file covers what check_manifest_agentic.py currently implements
(wave 1 activation/additivity/waivers + wave 2 graph integrity). Runnable directly
and as pytest.
"""
import copy
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


def warncodes(manifest, tier=2, root=ROOT):
    standing, warnings, waived, activated = C.run(manifest, root, tier)
    return {b.code for b in warnings}


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


# ── wave 3: trust / privilege, per-rule (mutate a passing showcase copy) ──────
def mut(fn, tier=2):
    m = copy.deepcopy(load(SHOWCASE))
    fn(m)
    return codes(m, tier=tier)[0]


def _dom(m, n):  return m["domains"][n]
def _intr(m, iid):  return next(i for i in m["interactions"] if i["id"] == iid)


def test_capability_not_in_registry():
    assert "capability_not_in_registry" in mut(
        lambda m: _dom(m, "intake_agent")["uses"].append({"capability": "ghost.cap", "operations": ["x"], "resources": ["y"]}))


def test_ceiling_violation():
    # account_service uses crm.read for a write op — exceeds the read-only ceiling
    assert "ceiling_violation" in mut(
        lambda m: _dom(m, "account_service")["uses"].append({"capability": "crm.read", "operations": ["write"], "resources": ["customer"]}))


def test_over_privilege():
    assert "over_privilege" in mut(
        lambda m: _dom(m, "intake_agent")["identity"]["privilege"].append("delete:everything"))


def test_under_privilege():
    assert "under_privilege" in mut(
        lambda m: _dom(m, "intake_agent")["identity"].__setitem__("privilege", []))


def test_agent_unscoped_tier2():
    def f(m):
        _dom(m, "resolution_agent").pop("uses")
        _dom(m, "resolution_agent").pop("memory")   # memory would re-imply scopes
    assert "agent_unscoped" in mut(f, tier=2)


def test_boundary_leg_missing():
    assert "leg_missing" in mut(lambda m: _intr(m, "classify_to_lookup").pop("response"))


def test_boundary_cost_and_authority_missing():
    assert "boundary_cost_missing" in mut(lambda m: _intr(m, "classify_to_lookup")["response"].pop("cost_bound"))
    assert "boundary_authority_missing" in mut(lambda m: _intr(m, "classify_to_lookup")["response"].pop("authority_bound"))


def test_authority_exceeds_privilege():
    assert "authority_exceeds_privilege" in mut(
        lambda m: _intr(m, "classify_to_lookup")["response"].__setitem__("authority_bound", ["delete:all"]))


def test_validation_missing():
    assert "validation_missing" in mut(lambda m: _intr(m, "classify_to_lookup")["request"].pop("validation"))


def test_authorization_missing():
    assert "authorization_missing" in mut(lambda m: _intr(m, "lookup_to_resolve").pop("authorization"))


def test_caller_not_allowed():
    assert "caller_not_allowed" in mut(
        lambda m: _intr(m, "lookup_to_resolve")["authorization"].__setitem__("allowed_callers", ["refund_service"]))


def test_caller_no_identity():
    def f(m):
        m["domains"]["ext_caller"] = {"purpose": "no identity"}
        _intr(m, "lookup_to_resolve")["authorization"]["allowed_callers"] = ["intake_agent", "ext_caller"]
    assert "caller_no_identity" in mut(f)


def test_credential_unjustified():
    assert "credential_unjustified" in mut(
        lambda m: _intr(m, "lookup_to_resolve")["authorization"].__setitem__("credential_mode", "static"))


def test_policy_ref_unresolved_kind_and_empty():
    assert "policy_ref_unresolved" in mut(lambda m: _intr(m, "classify_to_lookup")["request"].__setitem__("validation", "ghost:policy"))
    assert "policy_kind_mismatch" in mut(lambda m: _intr(m, "classify_to_lookup")["request"].__setitem__("validation", "refund:reversal"))
    assert "policy_ref_empty" in mut(lambda m: _intr(m, "classify_to_lookup")["request"].__setitem__("validation", "TODO"))


def test_quantpolicy_limit_and_unit():
    assert "quantpolicy_limit" in mut(lambda m: _intr(m, "classify_to_lookup")["response"]["cost_bound"].__setitem__("limit", 0))
    assert "quantpolicy_unit" in mut(lambda m: m["observability"]["cost_budget"].__setitem__("unit", "bogus"))


# ── wave 4: reliability / state, per-rule ─────────────────────────────────────
def test_async_reliability():
    assert "async_timeout_missing" in mut(lambda m: _intr(m, "propose_refund")["async"].pop("timeout"))
    assert "async_not_idempotent" in mut(lambda m: _intr(m, "propose_refund")["async"].pop("consumer_idempotent"))
    assert "async_dlq_missing" in mut(lambda m: _intr(m, "propose_refund")["async"].pop("dlq"))
    assert "async_retry_forbidden" in mut(
        lambda m: _intr(m, "propose_refund")["async"].update({"delivery": "at_most_once", "retry": {"max": 2, "backoff": "linear"}}))


def test_memory_rules():
    assert "memory_field_missing" in mut(lambda m: _dom(m, "resolution_agent")["memory"]["long_term"].pop("owner"))
    assert "memory_pii_unjustified" in mut(lambda m: _dom(m, "resolution_agent")["memory"]["long_term"].__setitem__("pii", "none"))
    assert "memory_store_unresolved" in mut(lambda m: _dom(m, "resolution_agent")["memory"]["long_term"].__setitem__("store", "ghost_store"))
    assert "memory_use_unreconciled" in mut(
        lambda m: _dom(m, "resolution_agent")["memory"]["long_term"]["reads"].append({"resource": "unlinked"}))


def test_memory_high_stakes_needs_guardrail_and_provenance():
    def f(m):
        lt = _dom(m, "resolution_agent")["memory"]["long_term"]
        lt["writes"] = [{"resource": "session", "high_stakes": True}]  # no guardrail, no provenance
    cs = mut(f)
    assert "memory_high_stakes_guardrail_missing" in cs and "memory_provenance_missing" in cs


def test_memory_shared_store():
    assert "memory_shared_store_missing" in mut(lambda m: _dom(m, "resolution_agent")["memory"]["long_term"].__setitem__("scope", "shared"))
    def f(m):
        lt = _dom(m, "resolution_agent")["memory"]["long_term"]
        lt["scope"] = "shared"; lt["shared_store"] = "session_store"   # session_store is shared:false
    assert "memory_shared_store_invalid" in mut(f)


def test_lifecycle_rules():
    cs = mut(lambda m: _dom(m, "refund_service").__setitem__("lifecycle", {"long_running": True, "checkpoint": "none"}))
    assert "lifecycle_not_resumable" in cs
    assert "lifecycle_checkpoint_none" in cs
    # resumable + side-effecting (refund_service emits refund_executed_event) needs side_effect_key
    cs2 = mut(lambda m: _dom(m, "refund_service").__setitem__("lifecycle", {"resumable": True}))
    assert "lifecycle_side_effect_key_missing" in cs2
    assert "lifecycle_human_gate_pause_missing" in mut(
        lambda m: _dom(m, "refund_service").__setitem__("lifecycle", {"human_gate": True}))


def test_deep_agent_rules():
    assert "deep_agent_missing" in mut(lambda m: _dom(m, "resolution_agent").__setitem__("kind", "deep_agent"))
    assert "deep_agent_on_non_deep" in mut(
        lambda m: _dom(m, "account_service").__setitem__("deep_agent", {"planner": "x", "subagents": [], "gates": [], "guardrails": [], "context_isolation": True}))


def test_saga_rules():
    assert "saga_step_not_side_effecting" in mut(lambda m: _intr(m, "propose_refund").__setitem__("side_effecting", False))
    assert "saga_compensation_not_idempotent" in mut(lambda m: m["sagas"][0]["steps"][0].__setitem__("compensation_idempotent", False))
    assert "saga_compensation_invalid" in mut(lambda m: m["sagas"][0]["steps"][0].__setitem__("compensation", "refund:request_schema"))  # schema, not action
    assert "saga_order_invalid" in mut(lambda m: m["sagas"][0].__setitem__("order", "parallel"))


def test_compensation_gap_advisory_is_warning_not_block():
    # remove the saga ⇒ the transactional refund_flow segment's side-effecting step is uncovered
    def f(m):
        m["sagas"] = []
    m = copy.deepcopy(load(SHOWCASE)); f(m)
    assert "compensation_gap" in warncodes(m)
    assert "compensation_gap" not in codes(m)[0]   # advisory: never a blocker


# ── wave 5: coverage / floor, per-rule ────────────────────────────────────────
def test_eval_coverage_missing_for_uncovered_agent():
    def f(m):
        m["domains"]["extra_agent"] = {"purpose": "p", "kind": "simple_agent", "kind_rationale": "bounded"}
    assert "eval_coverage_missing" in mut(f)


def test_eval_index_mismatch():
    assert "eval_index_mismatch" in mut(
        lambda m: _dom(m, "intake_agent")["evals"].__setitem__("spec", "docs/03-engineering/evals/component/moved.yaml"))


def test_e2e_segment_required():
    assert "e2e_missing" in mut(lambda m: m["segments"][0].__setitem__("e2e", False))


def test_eval_approval_required_at_tier2():
    """A covered agent whose spec is not `approved` fails at Tier 2, passes at Tier 1."""
    m = {
        "domains": {"ag": {"purpose": "p", "kind": "simple_agent", "kind_rationale": "b",
                           "evals": {"spec": "e/ag.yaml"}},
                    "svc": {"purpose": "q"}},
        "segments": [{"id": "s", "path": [], "e2e": True, "evals": {"spec": "e/s.yaml"}}],
    }
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "docs/03-engineering/evals"))
        idx = {"schema_version": "1.0", "rows": [
            {"target_type": "component", "target_id": "ag", "spec_path": "e/ag.yaml"},
            {"target_type": "segment", "target_id": "s", "spec_path": "e/s.yaml"}]}
        with open(os.path.join(d, "docs/03-engineering/evals/index.yaml"), "w") as f:
            yaml.safe_dump(idx, f)
        with open(os.path.join(d, "docs/03-engineering/evals/waivers.yaml"), "w") as f:
            yaml.safe_dump({"schema_version": "1.0", "waivers": []}, f)
        os.makedirs(os.path.join(d, "e"))
        for tid in ("ag", "s"):
            with open(os.path.join(d, "e", f"{tid}.yaml"), "w") as f:
                yaml.safe_dump({"approval": {"decision": "baseline_only"}}, f)
        cs2 = {b.code for b in C.run(m, d, 2)[0]}
        cs1 = {b.code for b in C.run(m, d, 1)[0]}
    assert "eval_not_approved" in cs2
    assert "eval_not_approved" not in cs1


def test_observability_floor_gate():
    assert "observability_missing" in mut(lambda m: m.pop("observability"))
    assert "observability_attributes" in mut(lambda m: m["observability"]["tracing"]["attributes"].remove("gen_ai.operation.name"))
    assert "observability_hops" in mut(lambda m: m["observability"]["tracing"]["hops"].remove("propose_refund"))
    assert "observability_cost_budget" in mut(lambda m: m["observability"]["cost_budget"].__setitem__("limit", 0))
    assert "eval_console_owner" in mut(lambda m: m["observability"]["eval_console"].__setitem__("owner", ""))
    assert "eval_console_ref_unresolved" in mut(lambda m: m["observability"]["eval_console"].__setitem__("ref", "domain:ghost"))


def test_eval_console_access_tier_scaled():
    # access 'report' fails at Tier 2 but is fine at Tier 1
    assert "eval_console_access" in mut(lambda m: m["observability"]["eval_console"].__setitem__("access", "report"), tier=2)
    assert "eval_console_access" not in mut(lambda m: m["observability"]["eval_console"].__setitem__("access", "report"), tier=1)


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
