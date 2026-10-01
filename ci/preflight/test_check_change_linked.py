#!/usr/bin/env python3
"""GATE-1 to GATE-5 (FR-30 slice 0): with a `docs` partner declared, the traceability gate looks for
the decision packet and the LLD in the partner's pull request through gh, and a host read that fails
is a failed check, never a pass."""
import base64
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_change as cc  # noqa: E402

PACKET = {"issue": 40, "domains": ["orders"], "source_docs": {"lld": "docs/02-design/lld/scm.md"},
          "rollout": {"risk": "low"}, "tests": {"registry_updated": True}}


class Host:
    def __init__(self, files=(), packet=PACKET, fail=()):
        self.files, self.packet, self.fail, self.calls = list(files), packet, set(fail), []

    def __call__(self, args):
        self.calls.append(args)
        path = args[1]
        if any(path.startswith(f) for f in self.fail):
            return 1, ""
        if path.startswith("search/issues"):
            return 0, json.dumps({"items": [{"number": 7}]})
        if path.startswith("repos/org/docs/pulls/7/files"):
            return 0, json.dumps([[{"filename": f} for f in self.files]])
        if path.startswith("repos/org/docs/pulls/7"):
            return 0, json.dumps({"head": {"sha": "abc1234"}})
        if path.startswith("repos/org/docs/contents/"):
            body = base64.b64encode(yaml.safe_dump(self.packet).encode()).decode()
            return 0, json.dumps({"content": body, "encoding": "base64"})
        return 1, ""


def setup(tmp_path, monkeypatch, partner=True):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    yaml.safe_dump({"domains": {"orders": {"files": ["app/orders/api.py"]}}}, open("docs/system-manifest.yaml", "w"))
    os.makedirs("app/orders")
    (tmp_path / ".hitl").mkdir()
    rec = {"change_id": "SCM-12"}
    if partner:
        rec["linked_changes"] = [{"repo": "org/docs", "change_id": "GH-40", "role": "docs"}]
    yaml.safe_dump(rec, open(".hitl/current-change.yaml", "w"))


def test_gate1_no_partner_behaves_as_before(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, partner=False)
    h = Host()
    monkeypatch.setattr(cc, "GH_RUN", h)
    r = cc.check_decision_packet(["app/orders/api.py"], "12")
    assert not r.passed and "Expected docs/decisions" in r.message
    assert h.calls == []


def test_gate2_packet_found_in_the_partner_pr_and_validated(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    h = Host(files=["docs/decisions/issue-40.yaml", "docs/02-design/lld/scm.md"])
    monkeypatch.setattr(cc, "GH_RUN", h)
    r = cc.check_decision_packet(["app/orders/api.py"], "12")
    assert r.passed and "linked docs partner org/docs" in r.message
    assert any("contents/docs/decisions/issue-40.yaml?ref=abc1234" in c[1] for c in h.calls)


def test_gate2b_an_incomplete_partner_packet_fails(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    h = Host(files=["docs/decisions/issue-40.yaml"], packet={"issue": 40})
    monkeypatch.setattr(cc, "GH_RUN", h)
    r = cc.check_decision_packet(["app/orders/api.py"], "12")
    assert not r.passed and "missing domains, source_docs, rollout" in r.message


def test_gate3_lld_updated_in_the_partner_pr(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(cc, "GH_RUN", Host(files=["docs/02-design/lld/scm.md"]))
    r = cc.check_lld_adr_for_api(["app/orders/controller.py"])
    assert r.passed and "linked docs partner org/docs" in r.message


def test_gate4_partner_pr_without_packet_or_lld_fails(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(cc, "GH_RUN", Host(files=["README.md"]))
    assert not cc.check_decision_packet(["app/orders/api.py"], "12").passed
    r = cc.check_lld_adr_for_api(["app/orders/controller.py"])
    assert not r.passed


def test_gate5_host_read_failure_is_a_failed_check(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(cc, "GH_RUN", Host(files=["docs/decisions/issue-40.yaml"], fail=("search/issues",)))
    r = cc.check_decision_packet(["app/orders/api.py"], "12")
    assert not r.passed and "could not list org/docs pull requests" in r.message
    r = cc.check_lld_adr_for_api(["app/orders/controller.py"])
    assert not r.passed
    monkeypatch.setattr(cc, "GH_RUN", Host(files=["docs/decisions/issue-40.yaml"], fail=("repos/org/docs/contents",)))
    r = cc.check_decision_packet(["app/orders/api.py"], "12")
    assert not r.passed and "could not be read" in r.message
