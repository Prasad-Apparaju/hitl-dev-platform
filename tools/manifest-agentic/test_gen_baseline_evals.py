#!/usr/bin/env python3
"""Tests for the baseline eval-spec generator (CR-20 / LLD §7.4)."""
import os
import sys
import tempfile
import yaml

sys.path.insert(0, os.path.dirname(__file__))
import gen_baseline_evals as G

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SHOWCASE = os.path.join(ROOT, "docs/examples/compound-agentic/system-manifest.yaml")


def test_check_reports_missing_targets():
    with tempfile.TemporaryDirectory() as d:
        missing, _ = G.generate(SHOWCASE, d, write=False)
    # every agent domain + the e2e segment
    assert any("intake_agent" in r for r in missing)
    assert any("resolution_agent" in r for r in missing)
    assert any("refund_flow" in r for r in missing)
    assert not any("account_service" in r for r in missing)  # deterministic ⇒ not a mandatory target


def test_generated_spec_is_baseline_only_not_approved():
    with tempfile.TemporaryDirectory() as d:
        G.generate(SHOWCASE, d, write=True)
        sp = yaml.safe_load(open(os.path.join(d, "docs/03-engineering/evals/component/intake_agent.yaml")))
    assert sp["kind"] == "eval"
    assert sp["approval"]["decision"] == "baseline_only"   # does NOT satisfy Tier-2 coverage until a human approves
    ids = [c["id"] for c in sp["cases"]]
    assert any("satisfies_fr" in i for i in ids)           # seeded from owning_fr
    assert any("privilege_boundary" in i for i in ids)     # seeded from the privilege boundary


def test_merge_preserves_human_edited_cases():
    with tempfile.TemporaryDirectory() as d:
        G.generate(SHOWCASE, d, write=True)
        path = os.path.join(d, "docs/03-engineering/evals/component/intake_agent.yaml")
        sp = yaml.safe_load(open(path))
        sp["cases"].append({"id": "human_case", "given": "x", "expect": "y", "source": "acceptance_criterion", "edited": True})
        yaml.safe_dump(sp, open(path, "w"), sort_keys=False)
        G.generate(SHOWCASE, d, write=True)   # regenerate
        sp2 = yaml.safe_load(open(path))
    assert "human_case" in [c["id"] for c in sp2["cases"]]  # human-edited case survives regeneration


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nBaseline eval generator: {len(tests)}/{len(tests)} passed")
