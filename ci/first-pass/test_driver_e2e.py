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


# ── the starter path: absent from this file's first version, which is how B1 shipped ──

def test_starter_emits_the_key_the_validator_actually_reads(gen, tmp_path):
    """The generator wrote `artifact_path`; the validator and schema both read `starter_artifact`.
    Every starter disposition therefore failed certification — the one seam this file exists to
    guard, broken for one of the three dispositions, because no test used a starter."""
    art = tmp_path / "test-plan.md"
    art.write_text("# starter\nneeds-enhancement: edge cases\n", encoding="utf-8")
    rc, doc, err = run_gen(gen, tmp_path, choices={
        "actor": "qa@team",
        "choices": {"test_plan": {"disposition": "starter", "reason": "thin first pass",
                                  "starter_artifact": "test-plan.md"}}})
    assert rc == 0, err
    entry = doc["skips"][0]
    assert "starter_artifact" in entry and "artifact_path" not in entry
    assert [s for s in doc["workflow"]["steps"] if s["key"] == "test_plan"][0]["status"] == "starter"
    assert C.check(doc, CATALOG, tier=2, change_dir=str(tmp_path)) == []


def test_keep_is_not_a_record_and_not_a_crash(gen, tmp_path):
    """`keep` is on the user-facing menu, so it is a plausible entry in the choices file. It means
    'leave the step alone' — not a KeyError."""
    rc, doc, err = run_gen(gen, tmp_path, choices={
        "actor": "a@b", "choices": {"roi": {"disposition": "keep", "reason": "n/a"}}})
    assert rc == 0, err
    assert "first_pass" not in doc and "skips" not in doc
    assert [s for s in doc["workflow"]["steps"] if s["key"] == "roi"][0]["status"] in ("open", "current")


@pytest.mark.parametrize("bad,expect", [
    ({"actor": "a", "choices": {"roi": {"disposition": "nope", "reason": "x"}}}, "disposition"),
    ({"actor": "a", "choices": {"roi": {"disposition": "decline"}}}, "reason"),
    ({"actor": "a", "choices": {"roi": "decline"}}, "must be an object"),
    ({"actor": "a", "choices": ["roi"]}, "must be an object"),
    (["not", "a", "dict"], "must be a JSON object"),
    ({"actor": 5, "choices": {}}, "must be a string"),
])
def test_malformed_choices_refuse_clearly_rather_than_traceback(gen, tmp_path, bad, expect):
    rc, doc, err = run_gen(gen, tmp_path, choices=bad)
    assert rc != 0 and doc is None
    assert expect in err, err
    assert "Traceback" not in err, "a malformed input must produce a message, not a stack trace"


def test_a_non_numeric_tier_refuses(gen, tmp_path):
    rc, _, err = run_gen(gen, tmp_path, tier="19a", choices=None)
    assert rc != 0 and "tier must be an integer" in err


def test_lightening_every_step_refuses(gen, tmp_path):
    """`current` must never point at a lightened step. With nothing kept there is no honest
    pointer and no change left to run."""
    steps = yaml.safe_load(io.open(os.path.join(ROOT, "ai", "shared", "workflows.yaml"),
                                   encoding="utf-8"))["workflows"]["docs"]["steps"]
    rc, _, err = run_gen(gen, tmp_path, wf="docs", choices={
        "actor": "a@b",
        "choices": {s["key"]: {"disposition": "decline", "reason": "x"} for s in steps}})
    assert rc != 0 and "no change left to run" in err


# ── the bash wrapper around the generator (untested by the subprocess harness above) ──

def test_the_wrapper_only_replaces_the_change_file_on_success():
    """Every generator refusal writes nothing to stdout, so an unconditional `mv` drops an EMPTY
    file over the live change file — re-creating the clobber the temp file exists to prevent, and
    deleting the user's choices on the way. The subprocess harness above cannot see this: it runs
    the Python directly and never executes the shell around it."""
    text = io.open(SKILL, encoding="utf-8").read()
    tail = text.split("current-change.yaml.tmp", 1)[1]
    assert "rc=$?" in tail, "the generator's exit status must be captured"
    mv_line = [ln for ln in tail.splitlines() if ln.strip().startswith("mv ")][0]
    guard = tail[:tail.index(mv_line)]
    assert "$rc -eq 0" in guard and "-s .hitl/current-change.yaml.tmp" in guard, \
        "mv must be guarded by both a zero exit and a non-empty temp file"
    assert "rm -f .hitl/first-pass-choices.json" in tail.split(mv_line, 1)[1], \
        "choices may only be consumed after a successful mv"


def test_unknown_workflow_refuses_without_a_traceback(gen, tmp_path):
    rc, _, err = run_gen(gen, tmp_path, choices=None, wf="not-a-workflow")
    assert rc != 0 and "unknown workflow" in err and "Traceback" not in err


def test_a_quote_in_the_branch_name_cannot_produce_unparsable_yaml(gen, tmp_path):
    """This exited 0 with non-empty output and broken YAML. The shell guard checks status and
    emptiness, not validity, so it installed the unparsable file over the live change file."""
    cpath = str(tmp_path / "absent.json")
    r = subprocess.run([sys.executable, gen, "development", "GH-1", 'issue/1-a"b', "9.9.9",
                        "2", cpath, "", ""], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    doc = yaml.safe_load(r.stdout)          # must not raise
    assert doc["expected_branch"] == 'issue/1-a"b'


def test_a_starter_outside_the_registry_refuses(gen, tmp_path):
    """The menu only offers `starter` for registered steps, but a menu is not an enforcement
    boundary — a hand-written choices file could otherwise certify an invented starter."""
    rc, _, err = run_gen(gen, tmp_path, choices={
        "actor": "a@b",
        "choices": {"roi": {"disposition": "starter", "reason": "thin",
                            "starter_artifact": "roi.md"}}})
    assert rc != 0 and "no registered starter" in err
