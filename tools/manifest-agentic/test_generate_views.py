#!/usr/bin/env python3
"""Tests for the generated views (#15 / LLD §2.4, §9): deterministic output, the
regenerate-and-diff (cannot-drift) guarantee, and that the generated eval index is
exactly the projection the validator expects (no eval_index_mismatch)."""
import copy
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ci", "manifest-agentic"))
import generate_views as G
import check_manifest_agentic as C

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SHOWCASE = os.path.join(ROOT, "docs/examples/compound-agentic/system-manifest.yaml")


def _caps():
    return yaml.safe_load(open(os.path.join(ROOT, "docs/03-engineering/approved-capabilities.yaml")))["capabilities"]


def test_regenerate_and_diff_is_clean():
    """The committed views must equal a fresh regeneration (the cannot-drift guarantee)."""
    drift = G.generate(SHOWCASE, ROOT, write=False)
    assert drift == [], f"drift detected (regenerate to fix): {drift}"


def test_required_artifact_inventory():
    """LLD §9: paired machine-readable + rendered artifacts for topology, privilege,
    capability, tool, projections (+ observability + eval index)."""
    m = yaml.safe_load(open(SHOWCASE))
    arts = set(G.build_artifacts(m, _caps()))
    d = G.POSTURE_DIR
    required = {
        f"{d}/topology.json", f"{d}/topology.md",
        f"{d}/privilege-posture.json", f"{d}/privilege-posture.md",
        f"{d}/capability-matrix.json", f"{d}/capability-matrix.md",
        f"{d}/tool-matrix.json", f"{d}/tool-matrix.md",
        f"{d}/projections.json", f"{d}/projections.md",
        f"{d}/observability-posture.json", G.EVAL_INDEX,
    }
    assert required <= arts, f"missing required artifacts: {sorted(required - arts)}"


def test_output_is_deterministic():
    m = yaml.safe_load(open(SHOWCASE))
    a1 = G.build_artifacts(m, _caps())
    a2 = G.build_artifacts(copy.deepcopy(m), _caps())
    assert a1 == a2


def test_generated_index_matches_validator_projection():
    """The generated eval index == the inline-spec projection ⇒ no eval_index_mismatch."""
    m = yaml.safe_load(open(SHOWCASE))
    gen_rows = G.project_eval_index(m)
    val_proj = C._eval_projection(m)  # (type, id, spec) tuples
    assert {(r["target_type"], r["target_id"], r["spec_path"]) for r in gen_rows} == set(val_proj)
    # and the validator, reading the generated index on disk, raises no mismatch
    standing = C.run(m, ROOT, 2)[0]
    assert "eval_index_mismatch" not in {b.code for b in standing}


def test_drift_detected_on_manifest_change():
    m = yaml.safe_load(open(SHOWCASE))
    m["domains"]["intake_agent"]["evals"]["spec"] = "docs/03-engineering/evals/component/renamed.yaml"
    fresh = G.build_artifacts(m, _caps())
    on_disk = open(os.path.join(ROOT, G.EVAL_INDEX)).read()
    assert fresh[G.EVAL_INDEX] != on_disk, "a changed inline spec must change the generated index"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nGenerator (views + index): {len(tests)}/{len(tests)} passed")
