#!/usr/bin/env python3
"""Conformance for the data-layer validator (FR-31 / test plan §0, §3). Every fail-closed case is
asserted by MUTATION of the fixture at docs/examples/data-layer: a hostile input must produce the
named code with waivable False and exit 2. A green happy path alone is not acceptance."""
import datetime as dt
import os
import re
import shutil
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_data_layer as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIXTURE = os.path.join(ROOT, "docs", "examples", "data-layer")
SCHEMA = os.path.join(HERE, "data-layer.schema.yaml")
WAIVERS = os.path.join(HERE, "data-layer-waivers.yaml")
TODAY = dt.date(2026, 9, 30)


@pytest.fixture
def fx(tmp_path):
    """A private copy of the fixture: (repo root, data dir)."""
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURE, dst)
    return str(dst), str(dst / "docs" / "02-design" / "data")


def run(root, data, waivers=WAIVERS, tier=3, manifest=None):
    findings, code, note = C.run(data, SCHEMA, manifest or os.path.join(root, "docs", "system-manifest.yaml"),
                                 waivers, tier, TODAY)
    return findings, code


def codes(findings, waivable=None):
    return [f["code"] for f in findings if waivable is None or f["waivable"] is waivable]


def edit(data, name, fn):
    p = os.path.join(data, name)
    with open(p) as f:
        d = yaml.safe_load(f)
    fn(d)
    with open(p, "w") as f:
        yaml.safe_dump(d, f, sort_keys=False, allow_unicode=True)


def blocks(findings, code):
    hits = [f for f in findings if f["code"] == code]
    assert hits, "expected %s, got %s" % (code, sorted(set(codes(findings))))
    assert all(f["waivable"] is False for f in hits), "%s must be non-waivable" % code
    return hits


# ---------------------------------------------------------------------------
# FIX-1: the fixture is clean
# ---------------------------------------------------------------------------

def test_fixture_validates_clean(fx):
    root, data = fx
    findings, code = run(root, data)
    assert code == 0
    assert codes(findings, waivable=False) == []
    # the one intended warning: q:5's needs list is unconfirmed (FIX-2)
    assert codes(findings) == ["QUESTION_NEEDS_UNCONFIRMED"]


def test_shipped_schema_is_the_template():
    a = open(SCHEMA).read()
    b = open(os.path.join(ROOT, "ai", "shared", "templates", "data-layer", "data-layer.schema.yaml")).read()
    assert a == b, "ci/data-layer/data-layer.schema.yaml must be identical to the template"


def test_fixture_holds_what_fix2_claims(fx):
    root, data = fx
    src = yaml.safe_load(open(os.path.join(data, "sources.yaml")))
    unext = [s for s in src["sources"] if s["status"] == "declared-not-extracted"]
    assert len(unext) == 1
    maps = yaml.safe_load(open(os.path.join(data, "mappings.yaml")))["mappings"]
    dep = [m for m in maps if m["store"]["source"] == unext[0]["id"]]
    assert dep and all(m["confidence"] == "needs-review" for m in dep)
    fnd = yaml.safe_load(open(os.path.join(data, "findings.yaml")))["findings"]
    neg = [f for f in fnd if f["kind"] == "negative" and f["confidence"] == "confirmed"]
    assert neg and neg[0]["confirmed_by"]["how"] == "verification"
    ont = yaml.safe_load(open(os.path.join(data, "ontology.yaml")))["entities"]
    syn = {}
    for e in ont:
        for s in e.get("synonyms") or []:
            syn.setdefault(s.lower(), []).append(e["id"])
    assert any(len(v) > 1 for v in syn.values()), "one synonym collision"
    qs = yaml.safe_load(open(os.path.join(data, "questions.yaml")))["questions"]
    assert len(qs) == 5 and sum(1 for q in qs if "confirmed_by" not in q) == 1


def test_fix4_interpretations_cite_only_their_slice_and_four_files_cite_origins(fx):
    root, data = fx
    idir = os.path.join(data, "interpretations")
    for n in os.listdir(idir):
        d = yaml.safe_load(open(os.path.join(idir, n)))
        text = yaml.safe_dump(d["proposed"])
        for f in set(re.findall(r"file: (\S+)", text)):
            assert f in d["inputs"], "%s cites %s outside inputs" % (n, f)
    for name in C.FOUR:
        text = open(os.path.join(data, name)).read()
        assert "evidence/slices/" not in text, "%s cites a slice" % name


# ---------------------------------------------------------------------------
# NEG-1 .. NEG-25: each mutation must fail closed with its code
# ---------------------------------------------------------------------------

def _ent(d, i=0):
    return d["entities"][i]


def _map(d, i=0):
    return d["mappings"][i]


NEG = [
    ("NEG-1", "ontology.yaml", lambda d: _ent(d).__setitem__("definition", "Rows written by jobs/nightly_eta.py"), "ONTOLOGY_NAMES_IMPLEMENTATION"),
    ("NEG-2", "ontology.yaml", lambda d: _ent(d)["synonyms"].append("eta_cache"), "ONTOLOGY_NAMES_IMPLEMENTATION"),
    ("NEG-3", "lineage.yaml", lambda d: d["edges"][0].__setitem__("negative", True), "NEGATIVE_AS_EDGE"),
    ("NEG-3b", "ontology.yaml", lambda d: _ent(d)["relationships"][0].__setitem__("polarity", "absent"), "NEGATIVE_AS_EDGE"),
    ("NEG-4", "findings.yaml", lambda d: d["findings"][0].update({"subject": "ent:order", "object": "ent:eta"}), "FINDING_SHAPED_AS_EDGE"),
    ("NEG-5", "mappings.yaml", lambda d: _map(d).__setitem__("confidence", "probable"), "CONFIDENCE_UNKNOWN"),
    ("NEG-5b", "ontology.yaml", lambda d: _ent(d, 1).pop("confidence"), "CONFIDENCE_UNKNOWN"),
    ("NEG-6", "mappings.yaml", lambda d: _map(d).__setitem__("evidence", []), "NO_EVIDENCE"),
    ("NEG-7", "mappings.yaml", lambda d: _map(d)["evidence"][0].__setitem__("item", "ev:app/code/9999"), "EVIDENCE_UNRESOLVED"),
    ("NEG-7b", "mappings.yaml", lambda d: _map(d)["evidence"][0].__setitem__("file", "evidence/app/none.yaml"), "EVIDENCE_UNRESOLVED"),
    ("NEG-7c", "ontology.yaml", lambda d: _ent(d)["evidence"].__setitem__(0, {"file": "evidence/slices/order.yaml", "item": "ev:app/code/0001"}), "EVIDENCE_UNRESOLVED"),
    ("NEG-9", "ontology.yaml", lambda d: _ent(d).pop("confirmed_by"), "CONFIRMED_WITHOUT_PROMOTER"),
    ("NEG-9b", "lineage.yaml", lambda d: d["edges"][0]["confirmed_by"].__setitem__("how", "guess"), "CONFIRMED_WITHOUT_PROMOTER"),
    ("NEG-12", "ontology.yaml", lambda d: _ent(d, 1).__setitem__("id", "ent:order"), "ID_DUPLICATE"),
    ("NEG-12c", "lineage.yaml", lambda d: d["edges"][1].__setitem__("id", "lin:1"), "ID_DUPLICATE"),
    ("NEG-12a", "lineage.yaml", lambda d: d["edges"][0].pop("id"), "ID_MISSING"),
    ("NEG-12a2", "findings.yaml", lambda d: d["findings"][0].pop("id"), "ID_MISSING"),
    ("NEG-13", "lineage.yaml", lambda d: d["edges"][0].__setitem__("relation", "derivedFrom"), "EDGE_TERM_UNKNOWN"),
    ("NEG-14", "lineage.yaml", lambda d: d["edges"][1].update({"subject": "map:order/orders-db.orders", "object": "act:nightly-eta"}), "EDGE_TYPE_MISMATCH"),
    ("NEG-15", "lineage.yaml", lambda d: d["activities"][0].__setitem__("files", []), "ACTIVITY_NO_FILES"),
    ("NEG-16", "mappings.yaml", lambda d: d["mappings"][4].__setitem__("confidence", "inferred"), "UNEXTRACTED_SOURCE_NOT_REVIEW"),
    ("NEG-16b", "mappings.yaml", lambda d: d["mappings"][4]["fields"][0].__setitem__("confidence", "inferred"), "UNEXTRACTED_SOURCE_NOT_REVIEW"),
    ("NEG-16c", "ontology.yaml", lambda d: _ent(d, 4).__setitem__("confidence", "inferred"), "UNEXTRACTED_SOURCE_NOT_REVIEW"),
    ("NEG-17", "mappings.yaml", lambda d: _map(d)["store"].__setitem__("source", "src:nowhere"), "SOURCE_UNKNOWN"),
    ("NEG-17a", "mappings.yaml", lambda d: _map(d).__setitem__("entity", "ent:nowhere"), "MAPPING_ENTITY_UNKNOWN"),
    ("NEG-17a2", "lineage.yaml", lambda d: d["edges"][3].__setitem__("subject", "ent:nowhere"), "EDGE_ENTITY_UNKNOWN"),
    ("NEG-17a3", "findings.yaml", lambda d: d["findings"][0].__setitem__("about", ["ent:nowhere"]), "FINDING_ABOUT_UNKNOWN"),
    ("NEG-19", "sources.yaml", lambda d: d["sources"][3].update({"access": {"granted": "read_only", "mode": "live"}, "authorization": {"by": "x", "at": "2026-09-30T09:00:00Z", "environment": "dev", "statement": "AUTHORIZED"}}), "LIVE_WITHOUT_AUTHORIZATION"),
    ("NEG-19b", "sources.yaml", lambda d: d["sources"][3].update({"access": {"granted": "read_only", "mode": "live"}}), "LIVE_WITHOUT_AUTHORIZATION"),
    ("NEG-22", "ontology.yaml", lambda d: d.__setitem__("extra", 1), "SCHEMA_UNKNOWN_FIELD"),
    ("NEG-22b", "ontology.yaml", lambda d: _ent(d).__setitem__("service", "orders-svc"), "SCHEMA_UNKNOWN_FIELD"),
]


@pytest.mark.parametrize("tid,fname,mut,code", NEG, ids=[n[0] for n in NEG])
def test_mutation_fails_closed(fx, tid, fname, mut, code):
    root, data = fx
    edit(data, fname, mut)
    findings, exit_code = run(root, data)
    blocks(findings, code)
    assert exit_code == 2


def test_neg2_pass_case_own_store_name_is_allowed(fx):
    root, data = fx
    edit(data, "ontology.yaml", lambda d: _ent(d)["synonyms"].append("ORDERS"))
    findings, code = run(root, data)
    assert "ONTOLOGY_NAMES_IMPLEMENTATION" not in codes(findings)
    assert code == 0


def test_neg8_evidence_type_unknown(fx):
    root, data = fx
    edit(data, "evidence/app/code-20260930T0900.yaml", lambda d: d.__setitem__("evidence_type", "guess"))
    findings, code = run(root, data)
    blocks(findings, "EVIDENCE_TYPE_UNKNOWN")
    assert code == 2


def test_neg10_interpretation_proposing_confirmed(fx):
    root, data = fx
    edit(data, "interpretations/order.yaml", lambda d: d["proposed"]["ontology"].__setitem__("confidence", "confirmed"))
    findings, code = run(root, data)
    blocks(findings, "MODEL_WROTE_CONFIRMED")
    assert code == 2


def test_neg11_citation_outside_inputs(fx):
    root, data = fx
    # another entity's slice
    edit(data, "interpretations/order.yaml",
         lambda d: d["proposed"]["ontology"]["evidence"].append({"file": "evidence/slices/eta.yaml", "item": "ev:app/code/0009"}))
    findings, code = run(root, data)
    blocks(findings, "CITATION_OUTSIDE_INPUTS")
    assert code == 2


def test_neg11b_citing_the_source_file_behind_the_slice_is_outside_inputs(fx):
    root, data = fx
    edit(data, "interpretations/order.yaml",
         lambda d: d["proposed"]["ontology"]["evidence"].append({"file": "evidence/app/code-20260930T0900.yaml", "item": "ev:app/code/0001"}))
    findings, code = run(root, data)
    blocks(findings, "CITATION_OUTSIDE_INPUTS")


def test_neg12b_interpretation_edge_with_an_id(fx):
    root, data = fx
    edit(data, "interpretations/eta.yaml", lambda d: d["proposed"]["lineage"]["edges"][0].__setitem__("id", "lin:1"))
    findings, code = run(root, data)
    blocks(findings, "ID_PROPOSED_BY_MODEL")


def test_neg18_live_evidence_without_authorization(fx):
    root, data = fx
    edit(data, "evidence/orders-db/profile-20260930T0940.yaml",
         lambda d: d.__setitem__("access", {"mode": "live", "environment": "prod", "read_only": True}))
    findings, code = run(root, data)
    blocks(findings, "LIVE_WITHOUT_AUTHORIZATION")


def test_neg20_write_access_recorded(fx):
    root, data = fx
    edit(data, "evidence/orders-db/profile-20260930T0940.yaml", lambda d: d["access"].__setitem__("read_only", False))
    findings, _ = run(root, data)
    blocks(findings, "WRITE_ACCESS_RECORDED")
    with open(os.path.join(data, "run.log"), "a") as f:
        f.write("2026-09-30T10:00:00Z profile_adapter src:orders-db mode=live env=prod read_only=true calls=count,insert result=ok\n")
    findings, _ = run(root, data)
    hits = blocks(findings, "WRITE_ACCESS_RECORDED")
    assert any("insert" in h["message"] for h in hits)


def test_neg21_boundary_entity_absent_from_ontology(fx):
    root, data = fx
    man = os.path.join(root, "docs", "system-manifest.yaml")
    d = yaml.safe_load(open(man))
    d["domains"]["orders"]["boundary_entities"]["Invoice"] = {"shape": "id: integer\n", "consumed_by": ["fulfilment"]}
    yaml.safe_dump(d, open(man, "w"), sort_keys=False)
    findings, code = run(root, data)
    hits = [f for f in findings if f["code"] == "BOUNDARY_NOT_IN_ONTOLOGY"]
    assert hits and hits[0]["waivable"] is True and hits[0]["locus"] == "invoice"
    assert code == 0  # waivable: a warning


def _waiver_file(tmp, rows):
    p = os.path.join(tmp, "data-layer-waivers.yaml")
    yaml.safe_dump({"schema_version": "1.0", "waivers": rows}, open(p, "w"))
    return p


def _add_invoice(root):
    man = os.path.join(root, "docs", "system-manifest.yaml")
    d = yaml.safe_load(open(man))
    d["domains"]["orders"]["boundary_entities"]["Invoice"] = {"shape": "id: integer\n", "consumed_by": []}
    yaml.safe_dump(d, open(man, "w"), sort_keys=False)


def test_a_valid_waiver_suppresses_the_boundary_finding(fx, tmp_path):
    root, data = fx
    _add_invoice(root)
    w = _waiver_file(str(tmp_path), [{"code": "BOUNDARY_NOT_IN_ONTOLOGY", "locus": "invoice", "owner": "orders-team",
                                      "reason": "billing onboards next quarter", "tier_limit": 3, "revisit": "2026-12-31"}])
    findings, code = run(root, data, waivers=w)
    hit = [f for f in findings if f["code"] == "BOUNDARY_NOT_IN_ONTOLOGY"][0]
    assert hit.get("waived") is True
    _, _, note = C.run(data, SCHEMA, os.path.join(root, "docs", "system-manifest.yaml"), w, 3, TODAY)
    assert note != "warnings" or [f for f in findings if f["waivable"] and not f.get("waived")]


@pytest.mark.parametrize("row", [
    {"code": "BOUNDARY_NOT_IN_ONTOLOGY", "locus": "invoice", "owner": "o", "reason": "r", "tier_limit": 3, "revisit": "2026-01-01"},   # lapsed
    {"code": "BOUNDARY_NOT_IN_ONTOLOGY", "locus": "invoice", "owner": "o", "reason": "r", "tier_limit": 2, "revisit": "2026-12-31"},   # tier too low
    {"code": "BOUNDARY_NOT_IN_ONTOLOGY", "locus": "Invoice", "owner": "o", "reason": "r", "tier_limit": 3, "revisit": "2026-12-31"},   # CapCase locus
    {"code": "BOUNDARY_NOT_IN_ONTOLOGY", "locus": "invoice", "owner": "", "reason": "r", "tier_limit": 3, "revisit": "2026-12-31"},    # no owner
], ids=["lapsed", "tier", "locus-case", "no-owner"])
def test_neg24_a_bad_waiver_does_not_suppress(fx, tmp_path, row):
    root, data = fx
    _add_invoice(root)
    findings, _ = run(root, data, waivers=_waiver_file(str(tmp_path), [row]))
    hit = [f for f in findings if f["code"] == "BOUNDARY_NOT_IN_ONTOLOGY"][0]
    assert not hit.get("waived")


def test_neg25_a_waiver_for_a_non_waivable_code_is_ignored(fx, tmp_path):
    root, data = fx
    edit(data, "mappings.yaml", lambda d: _map(d).__setitem__("evidence", []))
    w = _waiver_file(str(tmp_path), [{"code": "NO_EVIDENCE", "locus": "map:order/orders-db.orders", "owner": "o",
                                      "reason": "r", "tier_limit": 3, "revisit": "2026-12-31"}])
    findings, code = run(root, data, waivers=w)
    blocks(findings, "NO_EVIDENCE")
    assert code == 2


# ---------------------------------------------------------------------------
# NEG-23 / VAL-4: malformed and hostile input never tracebacks
# ---------------------------------------------------------------------------

def test_neg23_malformed_shapes(fx):
    root, data = fx
    p = os.path.join(data, "ontology.yaml")
    for text in ["- a\n- b\n", "schema_version: '1.0'\nentities: []\nentities: []\n", "schema_version: '1.0'\n\tentities: []\n", ""]:
        open(p, "w").write(text)
        findings, code = run(root, data)
        blocks(findings, "MALFORMED")
        assert code == 2


def test_val4_hostile_input_fails_closed(fx, tmp_path, monkeypatch):
    root, data = fx
    open(os.path.join(data, "findings.yaml"), "wb").write(b"\xff\xfe\x00\x00binary")
    findings, code = run(root, data)
    blocks(findings, "MALFORMED")
    outside = tmp_path / "outside.yaml"
    outside.write_text("schema_version: '1.0'\nentities: []\n")
    os.remove(os.path.join(data, "ontology.yaml"))
    os.symlink(str(outside), os.path.join(data, "ontology.yaml"))
    findings, code = run(root, data)
    blocks(findings, "MALFORMED")
    monkeypatch.setattr(C, "MAX_BYTES", 10)
    findings, code = run(root, data)
    blocks(findings, "MALFORMED")
    assert code == 2


def test_val3_absent_layer_is_absent_not_passed(tmp_path):
    findings, code, note = C.run(str(tmp_path / "nowhere"), SCHEMA, None, None, 3, TODAY)
    assert findings == [] and code == 0 and note.startswith("data layer: absent")


def test_val5_manifest_that_does_not_parse_is_one_finding_and_the_files_are_still_checked(fx):
    root, data = fx
    man = os.path.join(root, "docs", "system-manifest.yaml")
    open(man, "w").write("domains: [\n")
    edit(data, "mappings.yaml", lambda d: _map(d).__setitem__("evidence", []))
    findings, code = run(root, data)
    assert [f for f in findings if f["code"] == "MALFORMED" and "manifest" in f["message"]]
    blocks(findings, "NO_EVIDENCE")


def test_val2_strict_turns_a_warning_into_exit_1(fx, capsys):
    root, data = fx
    args = ["--data-dir", data, "--manifest", os.path.join(root, "docs", "system-manifest.yaml"),
            "--schema", SCHEMA, "--waivers", WAIVERS]
    assert C.main(args) == 0
    assert C.main(args + ["--strict"]) == 1


def test_edge_rule_warnings_are_waivable(fx):
    root, data = fx
    edit(data, "lineage.yaml", lambda d: d["edges"][1].__setitem__("rule", "SELECT order_no FROM orders WHERE status = 'open'"))
    findings, code = run(root, data)
    hit = [f for f in findings if f["code"] == "EDGE_RULE_IS_CODE"]
    assert hit and hit[0]["waivable"] and code == 0
    edit(data, "lineage.yaml", lambda d: d["edges"][1].__setitem__("rule", "Never reads closed orders."))
    findings, code = run(root, data)
    assert [f for f in findings if f["code"] == "EDGE_READS_NEGATIVE"] and code == 0


def test_file_missing_is_a_warning_and_the_rest_is_still_checked(fx):
    root, data = fx
    os.remove(os.path.join(data, "findings.yaml"))
    findings, code = run(root, data)
    assert [f for f in findings if f["code"] == "FILE_MISSING" and f["waivable"]]
    assert code == 0


def test_every_code_has_a_mutation():
    """Every code the validator can emit is exercised somewhere in this file (test plan §0)."""
    src = open(os.path.join(HERE, "check_data_layer.py")).read()
    emitted = set(re.findall(r'self\.add\("([A-Z_]+)"', src))
    tests = open(__file__).read()
    missing = sorted(c for c in emitted if c not in tests)
    assert not missing, "codes with no test: %s" % missing


def test_val6_the_core_runs_on_a_rules_stub(fx):
    """ADR-13: the shared core (confidence, evidence, promoter) checks a foreign family unchanged."""
    root, data = fx
    schema = yaml.safe_load(open(SCHEMA))
    ch = C.Checker(data, schema, None, None, 3, TODAY)
    ch.load_evidence()
    rule = {"id": "rule:1", "statement": "URGENT when needed within 14 days", "confidence": "confirmed",
            "evidence": [{"file": "evidence/app/code-20260930T0900.yaml", "item": "ev:app/code/0006"}]}
    ch.assertion(rule, "rule:1")
    assert codes(ch.findings) == ["CONFIRMED_WITHOUT_PROMOTER"]
    rule["confirmed_by"] = {"who": "pm@team", "at": "2026-09-30T12:00:00Z", "how": "human"}
    ch.findings.clear()
    ch.assertion(rule, "rule:1")
    assert ch.findings == []


def test_question_needing_an_unknown_id_is_a_warning(fx):
    root, data = fx
    edit(data, "questions.yaml", lambda d: d["questions"][0]["needs"]["edges"].append("lin:99"))
    findings, code = run(root, data)
    hit = [f for f in findings if f["code"] == "QUESTION_NEEDS_UNKNOWN"]
    assert hit and hit[0]["waivable"] and hit[0]["locus"] == "q:1" and code == 0


def test_fix3_every_template_parses_and_carries_only_schema_keys():
    tdir = os.path.join(ROOT, "ai", "shared", "templates", "data-layer")
    schema = yaml.safe_load(open(SCHEMA))
    files = schema["files"]
    for name in ("sources.yaml", "questions.yaml", "ontology.yaml", "mappings.yaml", "lineage.yaml", "findings.yaml"):
        d = yaml.safe_load(open(os.path.join(tdir, name)))
        assert set(d) <= set(files[name]["top"]), name
        spec = files[name]
        if "entries" in spec:
            for e in d[spec["entries"]]:
                assert set(e) <= set(spec["entry"]["keys"]), (name, set(e) - set(spec["entry"]["keys"]))
        else:
            for a in d["activities"]:
                assert set(a) <= set(spec["activity"]["keys"])
            for e in d["edges"]:
                assert set(e) <= set(spec["edge"]["keys"])
    d = yaml.safe_load(open(os.path.join(tdir, "interpretation.yaml")))
    assert set(d) <= set(files["interpretation"]["top"]) and set(d["proposed"]) <= set(files["interpretation"]["proposed"]["keys"])
