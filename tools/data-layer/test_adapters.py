#!/usr/bin/env python3
"""Conformance for the data-layer adapters (FR-31 / test plan §2, §4a, §5). The committed fixture at
docs/examples/data-layer is what these scripts produce: the tests assert that, item by item."""
import datetime as dt
import os
import shutil
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import assign_ids  # noqa: E402
import code_adapter  # noqa: E402
import dl_common  # noqa: E402
import intake_scan  # noqa: E402
import manifest_tie  # noqa: E402
import profile_adapter as P  # noqa: E402
import slice_evidence  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIXTURE = os.path.join(ROOT, "docs", "examples", "data-layer")
DATA = "docs/02-design/data"
AT = dt.datetime(2026, 9, 30, 9, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def fx(tmp_path):
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURE, dst)
    return str(dst)


def load(p):
    return yaml.safe_load(open(p))


def items(doc):
    return [(i["kind"], i["locator"], i["data"]) for i in doc["items"]]


def run(script, args, cwd):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + args, cwd=cwd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# SCAN
# ---------------------------------------------------------------------------

def test_scan1_proposes_every_declared_source_with_its_kind_and_no_values(fx):
    doc = intake_scan.proposal(fx)
    by = {s["id"]: s for s in doc["sources"]}
    assert by["src:app"]["kind"] == "code"
    assert by["src:orders-db"]["kind"] == "relational" and "docker-compose.yml:12" in by["src:orders-db"]["declared_from"]
    assert by["src:shipments-db"]["kind"] == "document"
    assert by["src:warehouse"]["kind"] == "unknown" and "app/settings.py:5" in by["src:warehouse"]["declared_from"]
    # a bare env-var reference folds into the source its connection string named, not a duplicate
    assert "src:database" not in by and "src:mongo" not in by
    assert "app/settings.py:3" in by["src:orders-db"]["declared_from"]
    text = yaml.safe_dump(doc)
    assert "postgresql://" not in text and "mongodb://" not in text
    for s in doc["sources"]:
        for where in s["declared_from"]:
            f = where.split(":")[0]
            assert f == "." or os.path.exists(os.path.join(fx, f))


def test_scan2_empty_repo_proposes_only_the_code_source(tmp_path):
    (tmp_path / "README.md").write_text("nothing here\n")
    doc = intake_scan.proposal(str(tmp_path))
    assert [s["id"] for s in doc["sources"]] == ["src:app"]


# ---------------------------------------------------------------------------
# CODE
# ---------------------------------------------------------------------------

def test_code1_adapter_reproduces_the_committed_code_evidence(fx):
    got, coverage = code_adapter.scan(fx)
    committed = load(os.path.join(fx, DATA, "evidence", "app", "code-20260930T0900.yaml"))
    assert [(i["kind"], i["locator"], i["data"]) for i in got] == items(committed)
    assert coverage == committed["coverage"]
    kinds = {i["kind"] for i in got}
    assert {"orm_entity", "store_literal", "read", "write", "join", "key_use"} <= kinds
    join = [i for i in got if i["kind"] == "join"][0]
    assert join["data"] == {"left": "orders", "right": "shipments", "keys": {"left": "order_no", "right": "order_no"}}
    orm = {i["data"]["class"]: i["data"] for i in got if i["kind"] == "orm_entity"}
    assert orm["Order"]["relationships"] == [{"to": "OrderLine", "kind": "one-to-many"}]
    assert orm["OrderLine"]["foreign_keys"] == [{"field": "order_id", "to": "orders.id"}]
    for i in got:
        f, line = i["locator"].rsplit(":", 1)
        assert open(os.path.join(fx, f)).read().splitlines()[int(line) - 1]


def test_code1_env_lookups_are_not_store_literals(fx):
    got, _ = code_adapter.scan(fx)
    assert not [i for i in got if i["kind"] == "store_literal" and i["data"]["store"] in ("DATABASE_URL", "MONGO_URI")]


def test_code2_other_languages_are_counted_not_guessed(fx):
    (os.path.join(fx, "web")) and os.makedirs(os.path.join(fx, "web"), exist_ok=True)
    open(os.path.join(fx, "web", "app.js"), "w").write('db.collection("secrets").find({})\n')
    got, coverage = code_adapter.scan(fx)
    assert coverage["files_skipped"]["other_language"] == 1
    assert not [i for i in got if (i["data"].get("store") == "secrets")]


def test_code_tenant_template_and_sql_strings(tmp_path):
    (tmp_path / "svc.py").write_text(
        'db = client.get_database("x")\n'
        'coll = db[f"orders_{tenant}"]\n'
        'rows = conn.execute("SELECT a.id FROM invoices a JOIN payments p ON a.id = p.invoice_id")\n')
    got, _ = code_adapter.scan(str(tmp_path))
    lit = [i for i in got if i["kind"] == "store_literal"][0]
    assert lit["data"]["store"] == "orders_{tenant}" and lit["data"]["template"] == "orders_{tenant}"
    join = [i for i in got if i["kind"] == "join"][0]
    assert join["data"]["right"] == "payments" and join["data"]["keys"] == {"left": "id", "right": "invoice_id"}
    assert {i["data"]["store"] for i in got if i["kind"] == "read"} == {"invoices", "payments"}


def test_code_cli_writes_the_envelope_and_the_log(fx):
    shutil.rmtree(os.path.join(fx, DATA, "evidence", "app"))
    os.remove(os.path.join(fx, DATA, "run.log"))
    r = run("code_adapter.py", ["--root", ".", "--data-dir", DATA, "--taken-at", "2026-09-30T09:00:00Z"], fx)
    assert r.returncode == 0, r.stderr
    doc = load(os.path.join(fx, DATA, "evidence", "app", "code-20260930T0900.yaml"))
    assert doc["evidence_type"] == "code" and doc["access"]["read_only"] is True and doc["items"][0]["id"] == "ev:app/code/0001"
    log = open(os.path.join(fx, DATA, "run.log")).read()
    assert "code_adapter src:app mode=offline" in log and "calls=scan result=ok" in log


# ---------------------------------------------------------------------------
# PROF
# ---------------------------------------------------------------------------

def test_prof1_offline_profile_reproduces_the_committed_evidence(fx):
    fetch = P.ExportFetch(os.path.join(fx, "exports"))
    os.chdir(fx)
    keys = P.keys_from_code_evidence(os.path.join(fx, DATA, "evidence", "app", "code-20260930T0900.yaml"))
    got = P.profile(fetch, ["eta_cache", "shipments"], 500, keys, fetch.locator, False)
    committed = load(os.path.join(fx, DATA, "evidence", "shipments-db", "profile-20260930T0945.yaml"))
    assert [(i["kind"], i["locator"], i["data"]) for i in got] == items(committed)
    pres = [i for i in got if i["kind"] == "field_presence" and i["data"]["store"] == "shipments"][0]
    assert pres["data"]["present_pct"]["carrier_ref"] == 0.0
    ov = [i for i in got if i["kind"] == "key_overlap"][0]
    assert ov["data"] == {"left": "orders.order_no", "right": "shipments.order_no", "left_rows": 20, "matched": 18, "share": 0.9}


def test_prof1_schema_dump(fx):
    got = P.parse_schema_dump(os.path.join(fx, "exports", "orders-schema.sql"))
    committed = load(os.path.join(fx, DATA, "evidence", "orders-db", "schema-20260930T0930.yaml"))
    assert [(i["kind"], i["data"]) for i in got] == [(i["kind"], i["data"]) for i in committed["items"]]
    assert got[1]["data"]["foreign_keys"] == [{"field": "order_id", "to": "orders.id"}]


def test_prof2_no_values_leave_the_sample(fx):
    fetch = P.ExportFetch(os.path.join(fx, "exports"))
    got = P.profile(fetch, ["orders"], 500, [], fetch.locator, True)
    text = yaml.safe_dump(got)
    assert "PO-48000" not in text and "t1" not in text


def test_prof_csv_export(tmp_path):
    (tmp_path / "parts.csv").write_text("part_id,desc\n1,bolt\n2,\n")
    fetch = P.ExportFetch(str(tmp_path))
    got = P.profile(fetch, ["parts"], 500, [], lambda s: s, False)
    assert got[0]["data"]["rows"] == 2 and got[1]["data"]["present_pct"] == {"part_id": 100.0, "desc": 50.0}


# ---------------------------------------------------------------------------
# AUTH / SRC
# ---------------------------------------------------------------------------

class FakeFetch:
    def __init__(self):
        self.calls = []

    def stores(self):
        self.calls.append("stores")
        return ["orders"]

    def count(self, store):
        self.calls.append("count")
        return 2

    def sample(self, store, n):
        self.calls.append("sample")
        return [{"id": 1, "order_no": "A"}, {"id": 2, "order_no": "B"}]


def _set_source(fx, **changes):
    p = os.path.join(fx, DATA, "sources.yaml")
    d = load(p)
    for s in d["sources"]:
        if s["id"] == "src:warehouse":
            s.update(changes)
    yaml.safe_dump(d, open(p, "w"), sort_keys=False)


def test_auth1_live_without_authorization_is_refused_and_logged(fx):
    _set_source(fx, access={"granted": "read_only", "mode": "live"})
    r = run("profile_adapter.py", ["--source", "src:warehouse", "--data-dir", DATA, "--live", "--driver", "mongo"], fx)
    assert r.returncode == dl_common.EXIT_REFUSED
    assert "result=refused reason=no_authorization" in open(os.path.join(fx, DATA, "run.log")).read().splitlines()[-1]
    assert not os.path.exists(os.path.join(fx, DATA, "evidence", "warehouse"))


def test_auth2_live_with_authorization_uses_only_read_calls(fx, monkeypatch):
    au = {"by": "ta@team", "at": "2026-09-30T09:00:00Z", "environment": "prod", "statement": "AUTHORIZED"}
    _set_source(fx, access={"granted": "read_only", "mode": "live"}, authorization=au)
    src = dl_common.find_source(os.path.join(fx, DATA), "src:warehouse")
    assert dl_common.authorization_ok(src) == (True, "")
    fetch = FakeFetch()
    for m in ("insert", "update", "delete", "write", "execute"):
        assert not hasattr(fetch, m)
    code, path = P.run_live(os.path.join(fx, DATA), "src:warehouse", fetch, 500, [], AT, False, src)
    assert code == 0 and set(fetch.calls) == {"stores", "count", "sample"}
    doc = load(path)
    assert doc["access"] == {"mode": "live", "environment": "prod", "read_only": True, "authorization": {"by": "ta@team", "at": "2026-09-30T09:00:00Z"}}
    log = open(os.path.join(fx, DATA, "run.log")).read().splitlines()[-1]
    assert "mode=live env=prod read_only=true calls=stores,count,sample(500) result=ok" in log
    assert dl_common.find_source(os.path.join(fx, DATA), "src:warehouse")["status"] == "extracted"


def test_auth2_a_fetch_with_a_write_method_is_refused(fx):
    au = {"by": "ta@team", "at": "2026-09-30T09:00:00Z", "environment": "prod", "statement": "AUTHORIZED"}
    _set_source(fx, access={"granted": "read_only", "mode": "live"}, authorization=au)
    src = dl_common.find_source(os.path.join(fx, DATA), "src:warehouse")

    class Bad(FakeFetch):
        def insert(self, *a):
            pass
    with pytest.raises(AssertionError):
        P.run_live(os.path.join(fx, DATA), "src:warehouse", Bad(), 500, [], AT, False, src)


def test_auth3_environment_mismatch_is_refused(fx):
    au = {"by": "ta@team", "at": "2026-09-30T09:00:00Z", "environment": "dev", "statement": "AUTHORIZED"}
    _set_source(fx, access={"granted": "read_only", "mode": "live"}, authorization=au)
    r = run("profile_adapter.py", ["--source", "src:warehouse", "--data-dir", DATA, "--live", "--driver", "mongo"], fx)
    assert r.returncode == dl_common.EXIT_REFUSED
    assert "reason=environment_mismatch" in open(os.path.join(fx, DATA, "run.log")).read()


def test_src1_missing_driver_is_recorded_not_raised(fx, monkeypatch):
    au = {"by": "ta@team", "at": "2026-09-30T09:00:00Z", "environment": "prod", "statement": "AUTHORIZED"}
    _set_source(fx, access={"granted": "read_only", "mode": "live"}, authorization=au, status="declared")
    r = run("profile_adapter.py", ["--source", "src:warehouse", "--data-dir", DATA, "--live", "--driver", "snowflake"], fx)
    assert r.returncode == dl_common.EXIT_UNREADABLE
    assert "Traceback" not in r.stderr
    assert "reason=driver_missing" in open(os.path.join(fx, DATA, "run.log")).read()
    assert dl_common.find_source(os.path.join(fx, DATA), "src:warehouse")["status"] == "declared-not-extracted"


def test_src2_every_exit_leaves_a_log_line(fx):
    before = len(open(os.path.join(fx, DATA, "run.log")).read().splitlines())
    run("profile_adapter.py", ["--source", "src:orders-db", "--data-dir", DATA, "--export", "nowhere"], fx)
    run("profile_adapter.py", ["--source", "src:orders-db", "--data-dir", DATA, "--schema-dump", "nowhere.sql"], fx)
    after = open(os.path.join(fx, DATA, "run.log")).read().splitlines()
    assert len(after) == before + 2 and all("result=refused" in l for l in after[-2:])


def test_env1_every_evidence_file_the_adapters_write_passes_the_validator_core(fx):
    sys.path.insert(0, os.path.join(ROOT, "ci", "data-layer"))
    import check_data_layer as C
    schema = yaml.safe_load(open(os.path.join(ROOT, "ci", "data-layer", "data-layer.schema.yaml")))
    ch = C.Checker(os.path.join(fx, DATA), schema, None, None, 3, dt.date(2026, 9, 30))
    ch.load_evidence()
    assert ch.findings == []


# ---------------------------------------------------------------------------
# SLICE / IDS
# ---------------------------------------------------------------------------

def test_slice1_slicer_reproduces_the_committed_slices(fx):
    data = os.path.join(fx, DATA)
    cands = load(os.path.join(data, "candidates.yaml"))["candidates"]
    got = slice_evidence.slices(data, cands, dt.datetime(2026, 9, 30, 10, 0, tzinfo=dt.timezone.utc))
    for name, doc in got.items():
        committed = load(os.path.join(data, "evidence", "slices", name + ".yaml"))
        assert doc == committed, name
    for name, doc in got.items():
        for it in doc["items"]:
            origin = load(os.path.join(data, it["origin"]["file"]))
            assert it["origin"]["item"] in {i["id"] for i in origin["items"]}
    # an item that names only another entity is not in this one's slice
    assert not [i for i in got["order-line"]["items"] if i["data"].get("store") == "shipments"]


def test_slice1_propose_lists_orm_classes_and_bare_stores(fx):
    doc = slice_evidence.propose(os.path.join(fx, DATA))
    ids = [c["entity"] for c in doc["candidates"]]
    assert ids == ["ent:delivery-slot", "ent:eta", "ent:order", "ent:order-line", "ent:shipment"]


def test_slice2_an_entity_nothing_names_gets_an_empty_slice(fx):
    got = slice_evidence.slices(os.path.join(fx, DATA), [{"entity": "ent:nothing", "classes": [], "stores": ["ghost"], "fields": []}], AT)
    assert got["nothing"]["items"] == []


def test_ids1_existing_ids_are_kept_and_new_ones_take_the_next_integer(fx):
    data = os.path.join(fx, DATA)
    prev = os.path.join(fx, "prev")
    os.makedirs(prev)
    shutil.copy(os.path.join(data, "lineage.yaml"), prev)
    shutil.copy(os.path.join(data, "findings.yaml"), prev)
    d = load(os.path.join(data, "lineage.yaml"))
    for e in d["edges"]:
        e.pop("id")
    d["edges"].append({"relation": "used", "subject": "act:nightly-eta", "object": "ent:carrier", "rule": "x",
                       "confidence": "inferred", "evidence": [{"file": "evidence/app/code-20260930T0900.yaml", "item": "ev:app/code/0001"}]})
    yaml.safe_dump(d, open(os.path.join(data, "lineage.yaml"), "w"), sort_keys=False)
    f = load(os.path.join(data, "findings.yaml"))
    for x in f["findings"]:
        x.pop("id")
    yaml.safe_dump(f, open(os.path.join(data, "findings.yaml"), "w"), sort_keys=False)
    out = assign_ids.run(data, prev)
    assert out["lineage.yaml"] == {"kept": 4, "assigned": 1} and out["findings.yaml"] == {"kept": 3, "assigned": 0}
    d2 = load(os.path.join(data, "lineage.yaml"))
    assert [e["id"] for e in d2["edges"]] == ["lin:1", "lin:2", "lin:3", "lin:4", "lin:5"]
    assert list(d2["edges"][0].keys())[0] == "id"


def test_ids2_two_new_edges_get_two_ids(tmp_path):
    new = [{"relation": "used", "subject": "act:a", "object": "ent:x"}, {"relation": "used", "subject": "act:a", "object": "ent:y"}]
    assign_ids.assign(new, [{"id": "lin:7", "relation": "used", "subject": "act:z", "object": "ent:z"}], "lin", assign_ids.edge_key)
    assert [e["id"] for e in new] == ["lin:8", "lin:9"]


# ---------------------------------------------------------------------------
# TIE
# ---------------------------------------------------------------------------

def test_tie1_to_tie4_boundary_entities_from_mappings(fx):
    data = os.path.join(fx, DATA)
    maps = load(os.path.join(data, "mappings.yaml"))["mappings"]
    ents = {e["id"]: e for e in load(os.path.join(data, "ontology.yaml"))["entities"]}
    man = load(os.path.join(fx, "docs", "system-manifest.yaml"))
    block, unowned = manifest_tie.derive(maps, ents, man["domains"])
    assert list(block) == ["orders"] and list(block["orders"]) == ["Order"]
    assert block["orders"]["Order"]["consumed_by"] == ["fulfilment"]
    assert "promised_date: date" in block["orders"]["Order"]["shape"]
    assert "Estimated arrival" not in str(block)       # written and read inside one domain: not a boundary
    assert unowned == []
    # TIE-3: a human key survives, shape is refreshed
    man["domains"]["orders"]["boundary_entities"]["Order"]["note"] = "keep me"
    man["domains"]["orders"]["boundary_entities"]["Order"]["shape"] = "stale"
    out = manifest_tie.apply(man, block)
    be = out["domains"]["orders"]["boundary_entities"]["Order"]
    assert be["note"] == "keep me" and be["shape"] != "stale"
    # TIE-4: a path no domain owns is reported and produces no entry
    maps[0]["read_by"].append("scripts/export.py")
    block, unowned = manifest_tie.derive(maps, ents, man["domains"])
    assert unowned == ["scripts/export.py"]


def test_tie5_and_tie6_block_matches_the_fixture_and_is_restored_after_a_generator_rerun(fx):
    man_path = os.path.join(fx, "docs", "system-manifest.yaml")
    original = load(man_path)
    d = load(man_path)
    del d["domains"]["orders"]["boundary_entities"]       # what a generator re-run does
    yaml.safe_dump(d, open(man_path, "w"), sort_keys=False)
    r = run("manifest_tie.py", ["--data-dir", DATA, "--manifest", "docs/system-manifest.yaml"], fx)
    assert r.returncode == 0, r.stderr
    assert load(man_path)["domains"]["orders"]["boundary_entities"] == original["domains"]["orders"]["boundary_entities"]
