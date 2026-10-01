#!/usr/bin/env python3
"""Conformance for the data-layer scorecard (FR-31 / test plan §4: SCORE-*, BASE-*)."""
import datetime as dt
import os
import re
import shutil
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scorecard as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIXTURE = os.path.join(ROOT, "docs", "examples", "data-layer")
RUN_AT = dt.datetime(2026, 9, 30, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def data(tmp_path):
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURE, dst)
    return str(dst / "docs" / "02-design" / "data")


def edit(data, name, fn):
    p = os.path.join(data, name)
    d = yaml.safe_load(open(p))
    fn(d)
    yaml.safe_dump(d, open(p, "w"), sort_keys=False, allow_unicode=True)


def public(m):
    return {k: v for k, v in m.items() if not k.startswith("_")}


def test_score1_fixture_metrics_equal_the_committed_baseline(data):
    m = public(S.compute(data, RUN_AT))
    base = yaml.safe_load(open(os.path.join(data, "scorecard.yaml")))["metrics"]
    assert m == base, "the committed scorecard.yaml must be what the script computes"


def test_score1_hand_computed_values(data):
    m = S.compute(data, RUN_AT)
    assert m["verification_rate"] == {"entities": 0.167, "fields": 0.105, "edges": 0.25}
    assert m["entities_without_mapping"] == ["ent:carrier"]
    assert m["sources_not_extracted"] == ["src:warehouse"]
    assert m["open_high_findings"] == 1 and m["negative_edges"] == 0
    assert m["answerable"] == {"yes": 3, "no": 1, "unconfirmed": 1, "total": 5}
    assert m["collisions"] == [["ent:delivery-slot", "ent:shipment", "synonym: delivery"],
                               ["ent:eta", "ent:shipment", "natural key ['order_no'] in src:shipments-db"]]
    assert m["_waiting"] == {"q:4": ["ent:delivery-slot", "map:delivery-slot/warehouse.delivery_slots"]}


def test_score2_answerability_flips_with_confidence_and_confirmation(data):
    edit(data, "lineage.yaml", lambda d: d["edges"][0].__setitem__("confidence", "needs-review"))
    m = S.compute(data, RUN_AT)
    assert m["answerable"]["yes"] == 1 and m["answerable"]["no"] == 3   # q:1 and q:2 now wait on lin:1
    assert m["_waiting"]["q:1"] == ["lin:1"]
    edit(data, "questions.yaml", lambda d: d["questions"][0].pop("confirmed_by"))
    m = S.compute(data, RUN_AT)
    assert m["answerable"]["unconfirmed"] == 2


def test_score3_synonym_collisions_case_fold(data):
    edit(data, "ontology.yaml", lambda d: d["entities"][1]["synonyms"].append("DELIVERY"))
    m = S.compute(data, RUN_AT)
    syn = [c for c in m["collisions"] if c[2] == "synonym: delivery"]
    assert len(syn) == 3  # order-line now collides with both shipment and delivery-slot


def test_score3_natural_key_collision_only_within_one_source(data):
    m = S.compute(data, RUN_AT)
    assert ["ent:eta", "ent:shipment", "natural key ['order_no'] in src:shipments-db"] in m["collisions"]
    # the same key in two different sources is not a collision
    edit(data, "mappings.yaml", lambda d: d["mappings"][2]["store"].__setitem__("source", "src:app"))
    m = S.compute(data, RUN_AT)
    assert not [c for c in m["collisions"] if "natural key" in c[2]]


def test_score4_age_uses_taken_at_not_mtime(data):
    m = S.compute(data, RUN_AT + dt.timedelta(days=10))
    assert m["evidence_age_days"] == {"oldest": 10, "newest": 10, "median": 10}
    p = os.path.join(data, "evidence", "app", "code-20260930T0900.yaml")
    os.utime(p, (0, 0))
    m = S.compute(data, RUN_AT)
    assert m["evidence_age_days"]["oldest"] == 0


def test_base1_identical_run_has_no_regression(data):
    m = S.compute(data, RUN_AT)
    rows = S.diff(m, public(m), 90)
    assert all(r["regression"] is False for r in rows)
    assert all(r["before"] == r["after"] for r in rows)


@pytest.mark.parametrize("mutate,metric", [
    (lambda d: d["edges"][0].__setitem__("confidence", "inferred"), "verification_rate.edges"),
    (lambda d: d["edges"][0].__setitem__("confidence", "needs-review"), "answerable.yes"),
], ids=["edge-rate-falls", "answerable-falls"])
def test_base2_each_regression_direction_is_marked(data, mutate, metric):
    base = public(S.compute(data, RUN_AT))
    edit(data, "lineage.yaml", mutate)
    rows = S.diff(S.compute(data, RUN_AT), base, 90)
    assert [r for r in rows if r["metric"] == metric and r["regression"]]


def test_base2_a_metric_moving_the_good_way_is_not_a_regression(data):
    base = public(S.compute(data, RUN_AT))
    edit(data, "findings.yaml", lambda d: d["findings"][0].__setitem__("status", "resolved"))
    rows = S.diff(S.compute(data, RUN_AT), base, 90)
    row = [r for r in rows if r["metric"] == "open_high_findings"][0]
    assert row["before"] == 1 and row["after"] == 0 and row["regression"] is False


def test_base2_stale_evidence_regresses_against_the_config_ceiling(data):
    m = S.compute(data, RUN_AT + dt.timedelta(days=100))
    assert [r for r in S.diff(m, None, 90) if r["metric"] == "evidence_age_days.oldest" and r["regression"]]
    assert not [r for r in S.diff(m, None, 120) if r["regression"]]


def test_base3_exit_codes(data, tmp_path, capsys):
    base = os.path.join(data, "scorecard.yaml")
    args = ["--data-dir", data, "--run-at", "2026-09-30T12:00:00Z", "--no-write", "--config", str(tmp_path / "none.yaml")]
    assert S.main(args + ["--baseline", base, "--strict"]) == 0
    edit(data, "lineage.yaml", lambda d: d["edges"][0].__setitem__("confidence", "needs-review"))
    assert S.main(args + ["--baseline", base]) == 0
    assert S.main(args + ["--baseline", base, "--strict"]) == 1
    assert S.main(args + ["--baseline", str(tmp_path / "missing.yaml"), "--strict"]) == 0
    assert "does not exist" in capsys.readouterr().out


def test_base4_report_is_plain_english_and_regressions_come_first(data):
    base = public(S.compute(data, RUN_AT))
    edit(data, "lineage.yaml", lambda d: d["edges"][0].__setitem__("confidence", "needs-review"))
    m = S.compute(data, RUN_AT)
    text = S.report(m, S.diff(m, base, 90), "advisory", "Diffed against the last run.")
    assert "—" not in text
    for word in ("leverage", "robust", "seamless", "comprehensive", "delve", "Note that", "It's worth noting"):
        assert word not in text
    assert text.index("## Regressions") < text.index("## Metrics")
    assert "q:1 waits on lin:1" in text
    assert len(text.splitlines()) < 60


def test_writes_scorecard_yaml_and_md(data, tmp_path):
    out = tmp_path / "s.yaml"
    rep = tmp_path / "s.md"
    assert S.main(["--data-dir", data, "--run-at", "2026-09-30T12:00:00Z", "--out", str(out), "--report", str(rep),
                   "--config", str(tmp_path / "none.yaml")]) == 0
    d = yaml.safe_load(open(out))
    assert d["mode"] == "advisory" and d["run_at"] == "2026-09-30T12:00:00Z" and "metrics" in d
    assert rep.read_text().startswith("# Data layer scorecard")


def test_mode_line_reads_the_config(data, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("data_layer:\n  blocking: true\n  stale_evidence_days: 30\n")
    assert S.config(str(cfg)) == {"blocking": True, "stale_evidence_days": 30}
    assert S.config(str(tmp_path / "none.yaml")) == S.DEFAULTS


def test_absent_layer(tmp_path, capsys):
    assert S.main(["--data-dir", str(tmp_path / "nowhere")]) == 0
    assert "absent" in capsys.readouterr().out
