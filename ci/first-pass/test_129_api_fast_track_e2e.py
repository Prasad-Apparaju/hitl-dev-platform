#!/usr/bin/env python3
"""#129 end to end: an API change, Fast Track, nothing ticked, must certify.

The sizer, the generator and the validator each passed their own tests while the seam between
them refused every API change: the sizer recorded an active `baseline` as not_applicable and
check_skips (rightly) blocked it. This runs the three as intake runs them.
"""
import json
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import check_skips as C  # noqa: E402

CATALOG = C.load_catalog(os.path.join(ROOT, "ai", "shared", "workflows.yaml"))
FINDINGS = {"area": "billing", "surfaces": ["api"], "security_sensitive": False,
            "dependencies_changed": False, "dependents": [], "interfaces_changed": []}


def _intake(tmp_path, tier, choices_from):
    """Size, write the outcomes back, turn the menu into choices, generate, and return the change."""
    rec = tmp_path / ".hitl" / "impact" / "GH-1.yaml"
    rec.parent.mkdir(parents=True)
    rec.write_text(yaml.safe_dump({"change_id": "GH-1", "workflow": "development",
                                   "findings": FINDINGS}), encoding="utf-8")
    out = subprocess.run([sys.executable, os.path.join(HERE, "size_plan.py"), str(rec),
                          str(tier), "fast"], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    sized = json.loads(out.stdout)
    body = yaml.safe_load(rec.read_text(encoding="utf-8"))
    body["rule_outcomes"] = sized["outcomes"]          # Step 4 writes the outcomes back
    rec.write_text(yaml.safe_dump(body), encoding="utf-8")
    choices = {"actor": "dev@team", "choices": choices_from(sized)}
    cpath = tmp_path / "choices.json"
    cpath.write_text(json.dumps(choices), encoding="utf-8")
    r = subprocess.run([sys.executable, os.path.join(HERE, "gen_change.py"), "development", "GH-1",
                        "issue/1-x", "9.9.9", str(tier), str(cpath), "dev@team", "one endpoint"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    doc = yaml.safe_load(r.stdout)
    doc["impact_record"] = ".hitl/impact/GH-1.yaml"    # the stub names it; the generator carries it
    return sized, doc


def _nothing_ticked(sized):
    """Fast Track as proposed: the rules' exclusions and the sizer's proposed defers, unchanged."""
    ch = {e["step"]: {"disposition": "not_applicable", "reason": e["reason"]} for e in sized["excluded"]}
    ch.update({p["step"]: {"disposition": p["disposition"], "reason": p["reason"]} for p in sized["proposed"]})
    return ch


def test_api_change_fast_track_with_nothing_ticked_certifies(tmp_path):
    sized, doc = _intake(tmp_path, 2, _nothing_ticked)
    # Baseline is still offered: it is left out of Fast Track, so it is an add-back box.
    assert "baseline" not in sized["plan"] and "baseline" in sized["plan"] + [p["step"] for p in sized["proposed"]]
    assert [e for e in sized["excluded"] if e["step"] == "baseline"] == []
    found = C.check(doc, CATALOG, tier=2, change_dir=str(tmp_path))
    assert [f["code"] for f in found if not f["waivable"]] == [], found
    entry = next(s for s in doc["skips"] if s["step"] == "baseline")
    assert entry["disposition"] == "defer" and entry["actor"] == "dev@team"
    assert entry["reason"] == "not required before this ships"
    # The only thing left to say is that the deferral has no fast-follow linked yet: a warning.
    assert {f["code"] for f in found} <= {"DEFER_NO_FOLLOWUP"}, found


def test_recording_the_active_step_as_not_applicable_is_still_refused(tmp_path):
    """The old sizer output, fed through the same pipeline, blocks. This is the mutation: if the
    sizer ever puts an active conditional step back into `excluded`, the first test goes red for
    exactly this reason."""
    def old(sized):
        ch = _nothing_ticked(sized)
        ch["baseline"] = {"disposition": "not_applicable", "reason": "not required before this ships"}
        return ch
    _, doc = _intake(tmp_path, 2, old)
    codes = {f["code"] for f in C.check(doc, CATALOG, tier=2, change_dir=str(tmp_path)) if not f["waivable"]}
    assert "COND_UNCONFIRMED" in codes, codes


def test_the_security_steps_are_untouched_by_129(tmp_path):
    sized, doc = _intake(tmp_path, 3, _nothing_ticked)
    ex = {e["step"]: e["reason"] for e in sized["excluded"]}
    for k in ("sec_design", "cve_audit", "pentest"):
        assert ex[k].startswith("conditional ("), (k, ex.get(k))
        assert next(s for s in doc["skips"] if s["step"] == k)["disposition"] == "not_applicable"
    assert [f["code"] for f in C.check(doc, CATALOG, tier=3, change_dir=str(tmp_path)) if not f["waivable"]] == []
