"""The release gate must fail closed, and its freshness rule must actually bite.

Written mutation-first: every rule is asserted by breaking it, because a gate that only ever sees
well-formed input is a gate nobody has tested. The freshness case is the important one — it is the
only property here that cannot be satisfied by writing a flattering record.
"""
import io
import os
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_review import check  # noqa: E402

SCRIPT = os.path.join(HERE, "check_review.py")
SHA = "a" * 40


def _write(p, doc):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    io.open(str(p), "w", encoding="utf-8").write(yaml.safe_dump(doc, sort_keys=False))


def _setup(tmp_path, record=None, change=None):
    root = tmp_path
    _write(root / ".hitl" / "current-change.yaml",
           change if change is not None else {"change_id": "GH-80", "tier": 2})
    if record is not None:
        _write(root / ".hitl" / "reviews" / "GH-80-round1.yaml", record)
    return (str(root / ".hitl" / "current-change.yaml"), str(root / ".hitl" / "reviews"))


def _record(**over):
    rec = {
        "schema_version": "1.0",
        "change_id": "GH-80",
        "round": 1,
        "reviewed_sha": SHA,
        "scope": "diff v1.0.0..HEAD",
        "reviewer": {"model": "fable", "context": "clean", "spawned_by": "hitl:adversarial-review"},
        "stance": "refute",
        "findings": [{"id": "F1", "severity": "HIGH", "claim": "x", "reproduction": "y",
                      "status": "fixed"}],
        "verdict": "ship",
    }
    rec.update(over)
    return rec


def _codes(blocks):
    return {b.split(":")[0].replace("[BLOCK] ", "").strip() for b in blocks}


def test_a_clean_fresh_review_passes(tmp_path):
    c, r = _setup(tmp_path, _record())
    blocks, _ = check(c, r, sha=SHA)
    assert blocks == [], blocks


def test_no_review_at_all_blocks(tmp_path):
    c, r = _setup(tmp_path, None)
    blocks, _ = check(c, r, sha=SHA)
    assert "REVIEW_MISSING" in _codes(blocks)


def test_review_of_different_code_blocks(tmp_path):
    """THE rule. Review an early draft, keep editing, and the gate must still stop you."""
    c, r = _setup(tmp_path, _record(reviewed_sha="b" * 40))
    blocks, _ = check(c, r, sha=SHA)
    assert "REVIEW_STALE" in _codes(blocks), blocks


def test_open_critical_finding_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "deletes user data", "status": "open"}]))
    blocks, _ = check(c, r, sha=SHA)
    assert "FINDING_OPEN" in _codes(blocks)


def test_open_low_finding_does_not_block(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "LOW", "claim": "typo", "status": "open"}]))
    blocks, _ = check(c, r, sha=SHA)
    assert blocks == []


def test_accepted_finding_needs_an_owner(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "x", "status": "accepted"}]))
    blocks, _ = check(c, r, sha=SHA)
    assert "UNSIGNED_ACCEPTANCE" in _codes(blocks)
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "x", "status": "accepted",
         "accepted_by": "someone"}]))
    assert check(c, r, sha=SHA)[0] == []


def test_verdict_must_be_ship(tmp_path):
    c, r = _setup(tmp_path, _record(verdict="do-not-ship"))
    blocks, _ = check(c, r, sha=SHA)
    assert "VERDICT_NOT_SHIP" in _codes(blocks)


def test_reviewer_sharing_the_authors_context_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(
        reviewer={"model": "fable", "context": "inherited"}))
    blocks, _ = check(c, r, sha=SHA)
    assert "NOT_INDEPENDENT" in _codes(blocks)


def test_confirming_stance_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(stance="confirm"))
    blocks, _ = check(c, r, sha=SHA)
    assert "WRONG_STANCE" in _codes(blocks)


@pytest.mark.parametrize("bad", [
    {"findings": "not-a-list"},
    {"findings": [{"severity": "SEVERE", "claim": "x", "status": "open"}]},
    {"findings": [{"severity": "HIGH", "claim": "x", "status": "maybe"}]},
    {"reviewer": "not-a-mapping"},
    {"reviewed_sha": ""},
])
def test_malformed_records_block_rather_than_pass(tmp_path, bad):
    c, r = _setup(tmp_path, _record(**bad))
    blocks, _ = check(c, r, sha=SHA)
    assert blocks, "malformed record %r passed the gate" % bad


def test_unparseable_record_blocks(tmp_path):
    c, r = _setup(tmp_path, _record())
    io.open(os.path.join(r, "GH-80-round1.yaml"), "w", encoding="utf-8").write("{[not yaml")
    blocks, _ = check(c, r, sha=SHA)
    assert "MALFORMED" in _codes(blocks)


def test_a_review_of_a_different_change_does_not_count(tmp_path):
    c, r = _setup(tmp_path, _record(change_id="GH-79"))
    blocks, _ = check(c, r, sha=SHA)
    assert "REVIEW_MISSING" in _codes(blocks)


def test_latest_round_decides(tmp_path):
    """Round 1 found a CRITICAL; round 2 is clean. The later round governs."""
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "x", "status": "open"}]))
    _write(os.path.join(r, "GH-80-round2.yaml"),
           _record(round=2, findings=[{"id": "F1", "severity": "CRITICAL", "claim": "x",
                                       "status": "fixed"}]))
    blocks, _ = check(c, r, sha=SHA)
    assert blocks == [], blocks


def test_round_one_with_no_findings_warns_but_does_not_block(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[]))
    blocks, warns = check(c, r, sha=SHA)
    assert blocks == []
    assert any("SHALLOW_REVIEW" in w for w in warns)


def test_cli_exit_codes(tmp_path):
    c, r = _setup(tmp_path, _record())
    ok = subprocess.run([sys.executable, SCRIPT, "--change", c, "--reviews", r, "--sha", SHA],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr

    c2, r2 = _setup(tmp_path / "b", _record(reviewed_sha="c" * 40))
    bad = subprocess.run([sys.executable, SCRIPT, "--change", c2, "--reviews", r2, "--sha", SHA],
                         capture_output=True, text=True)
    assert bad.returncode == 2
    assert "REVIEW_STALE" in bad.stdout


def test_gate_defaults_to_head_when_no_sha_given(tmp_path):
    """In a real repo the gate must compare against HEAD without being told."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=str(repo), check=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=str(repo), check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()

    c, r = _setup(repo, _record(reviewed_sha=head))
    assert check(c, r, root=str(repo))[0] == []

    c, r = _setup(repo, _record(reviewed_sha="d" * 40))
    assert "REVIEW_STALE" in _codes(check(c, r, root=str(repo))[0])
