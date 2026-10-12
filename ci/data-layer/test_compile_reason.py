#!/usr/bin/env python3
"""Conformance for the formal ontology (FR-31, DL-18 to DL-23, DL-29; ADR-14 to ADR-18). Every
fail-closed case is asserted by MUTATION of the fixture at docs/examples/data-layer: the compiler, the
reasoning stage and the validator must each refuse or report the named case. A green happy path alone
is not acceptance (test plan §0)."""
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOOLS = os.path.join(ROOT, "tools", "data-layer")
FIXTURE = os.path.join(ROOT, "docs", "examples", "data-layer")
SCHEMA = os.path.join(HERE, "data-layer.schema.yaml")
WAIVERS = os.path.join(HERE, "data-layer-waivers.yaml")
sys.path.insert(0, HERE)
import check_data_layer as C  # noqa: E402

rdflib = pytest.importorskip("rdflib")
pytest.importorskip("pyshacl")
pytest.importorskip("owlrl")
from rdflib import Graph, Namespace  # noqa: E402
from rdflib.namespace import OWL, RDF, SH  # noqa: E402

BASE = "https://hitl.dev/ns/system#"
DT = Namespace("https://hitl.dev/ns/decision-trace#")
NS = Namespace(BASE)


@pytest.fixture
def fx(tmp_path):
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURE, dst)
    data = dst / "docs" / "02-design" / "data"
    shutil.rmtree(data / "compiled", ignore_errors=True)
    shutil.rmtree(data / "evidence" / "reasoning", ignore_errors=True)
    return str(dst), str(data)


def sh(args, cwd, ok=True):
    p = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, text=True)
    if ok:
        assert p.returncode == 0, p.stdout + p.stderr
    return p


def compile_(root, data, extra=()):
    return sh([os.path.join(TOOLS, "compile_ontology.py"), "--data-dir", data, "--root", root] + list(extra), root)


def reason(root, data, mode="strict", ok=True, extra=()):
    return sh([os.path.join(TOOLS, "reason.py"), "--data-dir", data, "--root", root, "--mode", mode] + list(extra), root, ok)


def validate(root, data):
    findings, code, _ = C.run(data, SCHEMA, os.path.join(root, "docs", "system-manifest.yaml"), WAIVERS, 3)
    return findings, code


def edit(data, name, fn):
    p = os.path.join(data, name)
    d = yaml.safe_load(open(p))
    fn(d)
    yaml.safe_dump(d, open(p, "w"), sort_keys=False, allow_unicode=True)


def run_record(data):
    return yaml.safe_load(open(os.path.join(data, "compiled", "reasoning-run.yaml")))


def proposed(data):
    return yaml.safe_load(open(os.path.join(data, "compiled", "reasoning-findings.yaml")))["findings"]


# ---------------------------------------------------------------------------
# DL-20: the compiler

def test_cmp1_compile_writes_three_files_and_a_pin(fx):
    root, data = fx
    compile_(root, data)
    comp = os.path.join(data, "compiled")
    for f in ("ontology.ttl", "shapes.ttl", "rules.ttl", "pin.yaml"):
        assert os.path.exists(os.path.join(comp, f)), f
    pin = yaml.safe_load(open(os.path.join(comp, "pin.yaml")))
    assert set(pin["inputs"]) >= {"ontology.yaml", "mappings.yaml", "lineage.yaml", "rules.yaml"}
    assert pin["decision_trace"] == "on"
    findings, code = validate(root, data)
    assert code == 0, [f for f in findings if not f["waivable"]]


def test_cmp2_ontology_has_a_class_per_entity_with_axioms_and_keys(fx):
    root, data = fx
    compile_(root, data)
    g = Graph().parse(os.path.join(data, "compiled", "ontology.ttl"))
    ents = yaml.safe_load(open(os.path.join(data, "ontology.yaml")))["entities"]
    for e in ents:
        assert (NS[e["id"].split(":", 1)[1]], RDF.type, OWL.Class) in g, e["id"]
    assert (NS["order"], OWL.disjointWith, NS["shipment"]) in g
    assert (NS["order.fulfilled-by"], OWL.inverseOf, NS["shipment.fulfils"]) in g
    assert (NS["shipment.carried-by"], RDF.type, OWL.FunctionalProperty) in g
    assert list(g.objects(NS["order"], OWL.hasKey)), "the mapping's natural key becomes owl:hasKey"
    # every assertion carries its confidence and evidence as annotations (ADR-16)
    assert str(g.value(NS["order"], rdflib.URIRef("https://hitl.dev/ns/data-layer#confidence"))) == "confirmed"


def test_cmp3_decision_trace_module_is_on_by_default_and_off_needs_a_reason(fx):
    root, data = fx
    compile_(root, data)
    g = Graph().parse(os.path.join(data, "compiled", "ontology.ttl"))
    for c in ("Decision", "Policy", "Exception", "Approval", "Precedent"):
        assert (DT[c], RDF.type, OWL.Class) in g, c
    s = Graph().parse(os.path.join(data, "compiled", "shapes.ttl"))
    assert (DT.DecisionShape, RDF.type, SH.NodeShape) in s
    cfg = os.path.join(root, ".hitl")
    os.makedirs(cfg, exist_ok=True)
    yaml.safe_dump({"data_layer": {"decision_trace": "off"}}, open(os.path.join(cfg, "config.yaml"), "w"))
    p = compile_(root, data) if False else sh([os.path.join(TOOLS, "compile_ontology.py"), "--data-dir", data, "--root", root], root, ok=False)
    assert p.returncode == 2 and "recorded decision" in p.stdout
    yaml.safe_dump({"data_layer": {"decision_trace": "off", "decision_trace_reason": "batch system, no decisions"}},
                   open(os.path.join(cfg, "config.yaml"), "w"))
    compile_(root, data)
    g = Graph().parse(os.path.join(data, "compiled", "ontology.ttl"))
    assert (DT.Decision, RDF.type, OWL.Class) not in g


def test_cmp4_stale_pin_is_rejected_by_the_validator(fx):
    root, data = fx
    compile_(root, data)
    edit(data, "ontology.yaml", lambda d: d["entities"][0].__setitem__("definition", "changed after compile"))
    findings, code = validate(root, data)
    hits = [f for f in findings if f["code"] == "COMPILED_STALE"]
    assert hits and all(f["waivable"] is False for f in hits) and code == 2


# ---------------------------------------------------------------------------
# DL-21: the reasoning stage

def test_rsn1_strict_loads_confirmed_only_and_exploratory_adds_inferred(fx):
    root, data = fx
    compile_(root, data)
    reason(root, data, "strict")
    r = run_record(data)
    assert r["loaded"]["inferred"] == 0 and r["loaded"]["needs-review"] == 0 and r["loaded"]["confirmed"] > 0
    assert r["seen"]["needs-review"] > 0, "the fixture has needs-review assertions to drop"
    reason(root, data, "exploratory")
    r = run_record(data)
    assert r["loaded"]["inferred"] > 0 and r["loaded"]["needs-review"] == 0
    findings, code = validate(root, data)
    assert code == 0, [f for f in findings if not f["waivable"]]


def test_rsn2_needs_review_is_refused_and_a_run_that_loaded_it_fails_the_validator(fx):
    root, data = fx
    compile_(root, data)
    p = reason(root, data, "strict", ok=False, extra=["--include-needs-review"])
    assert p.returncode == 2 and "REFUSED" in p.stdout
    reason(root, data, "strict")
    rec = run_record(data)
    rec["loaded"]["needs-review"] = 3
    yaml.safe_dump(rec, open(os.path.join(data, "compiled", "reasoning-run.yaml"), "w"))
    findings, code = validate(root, data)
    hits = [f for f in findings if f["code"] == "REASONING_LOADED_NEEDS_REVIEW"]
    assert hits and hits[0]["waivable"] is False and code == 2


def test_rsn3_rules_fire_on_instances_and_the_run_says_how_many(fx):
    root, data = fx
    compile_(root, data)
    reason(root, data, "exploratory")
    r = run_record(data)
    assert r["rules_fired"]["rule:late-order"] > 0
    assert r["checks"]["shacl"].startswith("ran: conforms")


def test_rsn4_a_contradiction_becomes_an_inconsistency_finding_with_inference_evidence(fx):
    root, data = fx

    def contradict(d):
        for e in d["entities"]:
            if e["id"] == "ent:shipment":
                e["axioms"] = [{"kind": "subclass_of", "target": "ent:order", "confidence": "inferred",
                                "evidence": e["evidence"][:1]}]
    edit(data, "ontology.yaml", contradict)      # Order disjoint Shipment, Shipment subclass Order
    compile_(root, data)
    reason(root, data, "exploratory")
    r = run_record(data)
    assert r["results"]["inconsistency"] > 0 or r["results"]["unsatisfiable"] > 0, r
    fs = proposed(data)
    bad = [f for f in fs if f["kind"] in ("inconsistency", "unsatisfiable")]
    assert bad and all(f["confidence"] == "inferred" for f in bad)
    ev = bad[0]["evidence"][0]
    evdoc = yaml.safe_load(open(os.path.join(data, ev["file"])))
    assert evdoc["evidence_type"] == "inference" and any(it["id"] == ev["item"] for it in evdoc["items"])
    # strict never sees it: the contradicting axiom is inferred
    reason(root, data, "strict")
    assert run_record(data)["results"]["inconsistency"] == 0


def test_rsn5_a_duplicate_natural_key_in_the_data_is_a_violation_not_a_merge(fx):
    root, data = fx
    exp = os.path.join(root, "exports", "orders.jsonl")
    rows = [l for l in open(exp) if l.strip()]
    dup = json.loads(rows[0])
    dup["id"] = 999
    with open(exp, "a") as f:
        f.write(json.dumps(dup) + "\n")
    compile_(root, data)
    reason(root, data, "strict")
    r = run_record(data)
    assert r["checks"]["keys"].startswith("ran: 1 duplicate key group")
    fs = [f for f in proposed(data) if f["kind"] == "violation"]
    assert fs and "share the key" in fs[0]["statement"]


def test_rsn6_without_the_libraries_the_stage_is_skipped_not_failed(fx, monkeypatch):
    root, data = fx
    compile_(root, data)
    env = dict(os.environ, PYTHONPATH=os.path.join(root, "nolib"))
    os.makedirs(os.path.join(root, "nolib", "pyshacl"), exist_ok=True)
    open(os.path.join(root, "nolib", "pyshacl", "__init__.py"), "w").write("raise ImportError('shadowed for the test')\n")
    p = subprocess.run([sys.executable, os.path.join(TOOLS, "reason.py"), "--data-dir", data, "--root", root],
                       cwd=root, capture_output=True, text=True, env=env)
    assert p.returncode == 0 and "SKIPPED" in p.stdout, p.stdout + p.stderr


# ---------------------------------------------------------------------------
# DL-18, DL-19, DL-29: the validator on the new families

def test_val1_axiom_with_unknown_target_or_kind_fails_closed(fx):
    root, data = fx
    edit(data, "ontology.yaml", lambda d: d["entities"][0]["axioms"].append(
        {"kind": "disjoint_with", "target": "ent:nowhere", "confidence": "inferred", "evidence": d["entities"][0]["evidence"][:1]}))
    findings, code = validate(root, data)
    assert [f for f in findings if f["code"] == "AXIOM_TARGET_UNKNOWN" and f["waivable"] is False] and code == 2
    root, data = fx
    edit(data, "ontology.yaml", lambda d: d["entities"][0]["axioms"].__setitem__(0, dict(d["entities"][0]["axioms"][0], kind="disjoint")))
    findings, code = validate(root, data)
    assert [f for f in findings if f["code"] == "MALFORMED" and "axiom kind" in f["message"]]


def test_val2_axiom_without_evidence_is_rejected(fx):
    root, data = fx
    edit(data, "ontology.yaml", lambda d: d["entities"][0]["axioms"][0].__setitem__("evidence", []))
    findings, code = validate(root, data)
    assert [f for f in findings if f["code"] == "NO_EVIDENCE" and "axioms[0]" in f["locus"]] and code == 2


def test_val3_rules_file_is_checked_when_present(fx):
    root, data = fx
    findings, code = validate(root, data)
    assert code == 0
    edit(data, "rules.yaml", lambda d: d["rules"][0]["formal"].__setitem__("target", "ent:nowhere"))
    findings, code = validate(root, data)
    assert [f for f in findings if f["code"] == "RULE_TARGET_UNKNOWN" and f["waivable"] is False] and code == 2
    root, data = fx
    edit(data, "rules.yaml", lambda d: d["rules"][0].__setitem__("status", "maybe"))
    findings, code = validate(root, data)
    assert [f for f in findings if f["code"] == "MALFORMED" and "status" in f["message"]]


def test_val4_rules_file_absent_is_not_missing(fx):
    root, data = fx
    os.remove(os.path.join(data, "rules.yaml"))
    findings, code = validate(root, data)
    assert not [f for f in findings if f["code"] == "FILE_MISSING" and "rules" in f["locus"]]
    assert code == 0


def test_val5_action_catalog_is_optional_and_checked_when_on(fx):
    root, data = fx
    findings, code = validate(root, data)
    assert code == 0 and not os.path.exists(os.path.join(data, "actions.yaml"))
    actions = {"schema_version": "1.1", "actions": [{
        "id": "axn:approve-late-order", "name": "Approve a late order", "reads": ["ent:order", "ent:eta"],
        "writes": ["ent:order"], "rules": ["rule:late-order"], "roles": ["ops-lead"], "emits": "dt:Decision",
        "preconditions": [{"target": "ent:order", "sparql": "SELECT $this WHERE { $this :order.late true }",
                           "message": "only a late order can be approved late"}],
        "confidence": "inferred", "evidence": [{"file": "evidence/app/code-20260930T0900.yaml", "item": "ev:app/code/0011"}]}]}
    yaml.safe_dump(actions, open(os.path.join(data, "actions.yaml"), "w"))
    findings, code = validate(root, data)
    assert code == 0, [f for f in findings if not f["waivable"]]
    compile_(root, data)
    s = Graph().parse(os.path.join(data, "compiled", "shapes.ttl"))
    assert (NS["axn.approve-late-order"], RDF.type, rdflib.URIRef("https://hitl.dev/ns/data-layer#Action")) in s
    assert list(s.subjects(SH.targetClass, NS["order"])), "a precondition shape targets the entity"
    edit(data, "actions.yaml", lambda d: d["actions"][0].__setitem__("reads", ["ent:nowhere"]))
    findings, code = validate(root, data)
    assert [f for f in findings if f["code"] == "ACTION_REF_UNKNOWN" and f["waivable"] is False] and code == 2


def test_val6_inference_evidence_type_is_accepted_by_the_core(fx):
    root, data = fx
    compile_(root, data)
    reason(root, data, "exploratory")
    findings, code = validate(root, data)
    assert not [f for f in findings if f["code"] == "EVIDENCE_TYPE_UNKNOWN"]
    assert code == 0
