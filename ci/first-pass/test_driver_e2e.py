#!/usr/bin/env python3
"""End-to-end conformance for the First Pass DRIVER path (intake -> ledger -> certify).

Why this file exists: every unit in ci/first-pass/ passed while the driver never emitted
`first_pass`, so `check()` early-returned and the certification step users are told to run
reported clean on every change. Unit coverage cannot catch that — the defect lives in the seam
between the skill's generator and the validator, and nothing exercised the seam.

So these tests run the generator **as it actually ships**: extracted verbatim from the fenced
heredoc in `dev-start-change`'s SKILL.md. If someone edits that block and breaks the contract,
this fails. If someone rewrites the skill so the block can no longer be found, this fails too,
which is the point — a driver that cannot be located cannot be trusted.
"""
import io
import json
import os
import re
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SKILL = os.path.join(ROOT, "ai", "claude", "start-change", "SKILL.md")
sys.path.insert(0, HERE)
import check_skips as C  # noqa: E402

CATALOG = C.load_catalog(os.path.join(ROOT, "ai", "shared", "workflows.yaml"))


def _generator_source():
    """The Step 6 generator, lifted verbatim out of the shipped skill."""
    text = io.open(SKILL, encoding="utf-8").read()
    m = re.search(r"<< 'PY'.*?\n(.*?)\nPY\n", text, re.S)
    assert m, "Step 6 generator heredoc not found in start-change/SKILL.md"
    return m.group(1)


@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    p = tmp_path_factory.mktemp("driver") / "gen.py"
    p.write_text(_generator_source(), encoding="utf-8")
    return str(p)


def run_gen(gen, tmp_path, tier=2, choices=None, set_by="", reason="", wf="development"):
    """Run the generator the way Step 6 runs it. Returns (returncode, parsed_yaml_or_None, stderr)."""
    cpath = str(tmp_path / "choices.json")
    if choices is None:
        cpath = str(tmp_path / "absent.json")
    else:
        io.open(cpath, "w", encoding="utf-8").write(json.dumps(choices))
    r = subprocess.run([sys.executable, gen, wf, "GH-1", "issue/1-x", "9.9.9",
                        str(tier), cpath, set_by, reason],
                       capture_output=True, text=True, cwd=ROOT)
    doc = yaml.safe_load(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    return r.returncode, doc, r.stderr


CHOICES = {"actor": "arch@team",
           "choices": {"roi": {"disposition": "decline", "reason": "internal tool"},
                       "figma": {"disposition": "defer", "reason": "no UI", "followup_ref": "GH-9"}}}


# ── the seam that shipped broken ──────────────────────────────────────────────

def test_dispositions_produce_an_enforced_ledger(gen, tmp_path):
    """The whole point: choices in, a change file the validator actually enforces out."""
    rc, doc, err = run_gen(gen, tmp_path, choices=CHOICES)
    assert rc == 0, err
    assert doc["first_pass"] is True, "generator must declare First Pass when dispositions were chosen"
    assert {s["step"] for s in doc["skips"]} == {"roi", "figma"}
    lightened = {s["key"] for s in doc["workflow"]["steps"] if s["status"] in ("skipped", "starter")}
    assert lightened == {"roi", "figma"}, "statuses and ledger must agree"
    # and the certification step now tests something
    assert C.check(doc, CATALOG, tier=2) == []


def test_a_plain_change_does_not_claim_first_pass(gen, tmp_path):
    """Emitting the flag unconditionally would switch on brief mode and reduced-friction
    permissions for every change. Absent choices, it must not appear at all."""
    rc, doc, err = run_gen(gen, tmp_path, choices=None)
    assert rc == 0, err
    assert "first_pass" not in doc and "skips" not in doc
    assert C.check(doc, CATALOG, tier=2) == []


def test_the_original_defect_is_caught_if_it_returns(gen, tmp_path):
    """Regression guard for the exact shipped bug: a lightened plan with the flag missing."""
    rc, doc, _ = run_gen(gen, tmp_path, choices=CHOICES)
    assert rc == 0
    del doc["first_pass"]
    assert "FP_UNDECLARED" in [f["code"] for f in C.check(doc, CATALOG, tier=2) if not f["waivable"]]


def test_ledger_survives_seeding(gen, tmp_path):
    """Step 4b used to record into a file Step 6 then overwrote. The records must come OUT of
    the generator, not be written before it and hope."""
    rc, doc, _ = run_gen(gen, tmp_path, choices=CHOICES)
    assert rc == 0 and doc["skips"], "dispositions must survive the step that writes the file"
    for entry in doc["skips"]:
        assert entry["actor"] == "arch@team" and entry["reason"]
        assert entry["resolved"] is False
        assert entry["crit"] in ("ceremony", "standard", "floor")


def test_current_never_lands_on_a_lightened_step(gen, tmp_path):
    rc, doc, _ = run_gen(gen, tmp_path, choices=CHOICES)
    assert rc == 0
    current = [s for s in doc["workflow"]["steps"] if s["status"] == "current"]
    assert len(current) == 1 and current[0]["key"] not in CHOICES["choices"]


# ── refusals: a half-valid ledger is worse than none ──────────────────────────

def test_low_tier_without_attribution_refuses(gen, tmp_path):
    rc, doc, err = run_gen(gen, tmp_path, tier=1, choices=None)
    assert rc != 0 and doc is None
    assert "TIER_SET_BY" in err


def test_low_tier_with_attribution_records_who_and_why(gen, tmp_path):
    rc, doc, err = run_gen(gen, tmp_path, tier=1, choices=None,
                           set_by="arch@team", reason="single-function regression")
    assert rc == 0, err
    assert doc["tier_set_by"] == "arch@team" and doc["tier_reason"]
    assert C.check(doc, CATALOG, tier=1) == []


def test_choices_naming_unknown_steps_refuse(gen, tmp_path):
    rc, _, err = run_gen(gen, tmp_path, choices={"actor": "a@b",
                                                 "choices": {"nope": {"disposition": "decline", "reason": "x"}}})
    assert rc != 0 and "not in the development workflow" in err


def test_choices_without_an_actor_refuse(gen, tmp_path):
    rc, _, err = run_gen(gen, tmp_path,
                         choices={"choices": {"roi": {"disposition": "decline", "reason": "x"}}})
    assert rc != 0 and "actor" in err


# ── the generator must work for every shipped workflow, not just development ──

@pytest.mark.parametrize("wf", sorted(yaml.safe_load(
    io.open(os.path.join(ROOT, "ai", "shared", "workflows.yaml"), encoding="utf-8"))["workflows"]))
def test_every_workflow_seeds(gen, tmp_path, wf):
    rc, doc, err = run_gen(gen, tmp_path, choices=None, wf=wf)
    assert rc == 0, f"{wf}: {err}"
    assert doc["workflow"]["id"] == wf and doc["workflow"]["steps"]
    assert sum(1 for s in doc["workflow"]["steps"] if s["status"] == "current") == 1
