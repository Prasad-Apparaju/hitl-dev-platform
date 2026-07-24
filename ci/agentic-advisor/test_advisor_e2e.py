#!/usr/bin/env python3
"""End-to-end conformance for the Advisor (#41 / test-plan E2E-*). Runs the full pipeline
(scenario → compose → records → map) and asserts the boundary the feature exists to hold:
a non-expert gets a right-sized report + neutral handoff that authors NO manifest field."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "agentic-advisor"))
import compose as C
import records as R
import render_map as M

# The worked example: a support assistant (4 components, 2 agents), irreversible refund, PII, supervised.
SUPPORT = {
    "feature": "support-assistant",
    "components": [
        {"id": "intake_agent",     "role": "agent",     "proposed_kind": "simple_agent", "rationale": "bounded classify task"},
        {"id": "account_service",  "role": "service",   "proposed_kind": "deterministic", "rationale": "system of record"},
        {"id": "resolution_agent", "role": "agent",     "proposed_kind": "simple_agent", "rationale": "bounded draft task"},
        {"id": "refund_service",   "role": "service",   "proposed_kind": "deterministic", "rationale": "executes an irreversible refund"},
    ],
    "edges": [
        {"id": "classify",  "from": "intake_agent",     "to": "account_service",  "transport": "sync_call"},
        {"id": "resolve",   "from": "intake_agent",     "to": "resolution_agent", "transport": "sync_call"},
        {"id": "refund",    "from": "resolution_agent", "to": "refund_service",   "transport": "async_task", "side_effecting": True},
    ],
    "answers": {"stakes": "customer_facing", "side_effects": "irreversible", "data": "pii",
                "autonomy": "supervised", "scale": "small", "greenfield": True},
    "skips": [],
    "deploy": {"recommend": "managed", "chosen": "managed", "carry_to": "platform/ops (FR-25)"},
}


def test_e2e_non_expert_gets_report_floor_record_handoff():
    composed = C.compose(SUPPORT)
    # a right-sized floor (safety factors incl. async + irreversible ⇒ reliability)
    assert set(composed["floor"]) == {"classify", "boundary", "privilege", "reliability", "observability", "evals"}
    assert composed["rungs"] == ["deploy"]
    handoff = R.generate_handoff(SUPPORT, composed)
    record = R.generate_decision_record(SUPPORT, composed)
    rendered = M.render(SUPPORT, composed)
    assert handoff and record and rendered["terminal"] and rendered["mermaid"]


def test_e2e_handoff_authors_no_manifest_field():
    handoff = R.generate_handoff(SUPPORT)
    assert R.handoff_authors_no_manifest_field(handoff) == set()   # the load-bearing boundary


def test_e2e_roles_total_and_deploy_recorded():
    assert M.validate_roles(SUPPORT) == []                          # every component has one role
    assert "deploy" in C.compose(SUPPORT)["report_sections"]        # greenfield ⇒ deploy lens present
    assert "platform/ops" in R.generate_decision_record(SUPPORT)    # deploy decision recorded + human-carried


def test_single_lens_rerun_supported():
    # STANDALONE-LENS: a team may re-run scoped to one lens (there is no separate hitl:agentic-privilege command)
    one = {"components": [{"id": "a1", "role": "agent", "proposed_kind": "simple_agent"}],
           "edges": [], "answers": {"side_effects": "none", "autonomy": "assisted"}}
    r = C.compose(one)
    assert "privilege" in r["report_sections"]                      # the privilege section is reachable on its own


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nAdvisor e2e (#41/wave F): {len(tests)}/{len(tests)} passed")
