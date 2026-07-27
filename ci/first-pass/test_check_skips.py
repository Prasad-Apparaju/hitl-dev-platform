#!/usr/bin/env python3
"""Conformance for the First Pass skip-ledger validator (FR-29 / test-plan §0-§5, §11).

Discipline: the fail-closed core is asserted by MUTATION — each NEG-* feeds hostile input and requires a
BLOCK finding. A green happy path alone is not acceptance (the #10/#35 lesson)."""
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import check_skips as C

WORKFLOWS = os.path.join(HERE, "..", "..", "ai", "shared", "workflows.yaml")
CATALOG = C.load_catalog(WORKFLOWS)


def codes(findings):
    return [f["code"] for f in findings]


def blockers(findings):
    return [f["code"] for f in findings if not f["waivable"]]


def make_change(skips, step_over=None, tier=2, first_pass=True, change_id="GH-1"):
    """Build a change record whose steps[] statuses match the skips (skipped/starter) unless overridden."""
    steps = []
    over = step_over or {}
    for s in skips:
        k = s["step"]
        status = over.get(k, "starter" if s.get("disposition") == "starter" else "skipped")
        steps.append({"n": 1, "key": k, "label": k, "status": status, "phase": "X"})
    # a couple of normal steps too
    steps += [{"n": 2, "key": "green", "label": "GREEN", "status": "done", "phase": "Build"}]
    return {"first_pass": first_pass, "tier": tier, "change_id": change_id,
            "workflow": {"id": "development", "steps": steps}, "skips": skips}


def base_skip(step, **kw):
    d = {"step": step, "actor": "pm@team", "reason": "thin v1", "ts": "2026-07-27T00:00:00Z",
         "disposition": "decline"}
    d.update(kw)
    return d


# ── resolve_crit + catalog ────────────────────────────────────────────────────
def test_resolve_crit_tier_scoped():
    assert C.resolve_crit(CATALOG["impact"], 2) == "standard"
    assert C.resolve_crit(CATALOG["impact"], 3) == "floor"
    assert C.resolve_crit(CATALOG["deploy"], 0) == "floor"
    assert C.resolve_crit(CATALOG["deploy"], 3) == "floor"
    assert C.resolve_crit(CATALOG["roi"], 3) == "ceremony"


def test_catalog_annotated_and_clean():
    # every development step carries a resolvable crit; the real catalog passes the monotonicity lint
    assert all("crit" in m for m in CATALOG.values())
    assert C.lint_catalog(CATALOG) == []
    assert CATALOG["red"].get("no_omit") and CATALOG["green"].get("no_omit")


# ── happy path ────────────────────────────────────────────────────────────────
def test_clean_first_pass_change(tmp_path):
    art = tmp_path / "test-plan.md"
    art.write_text("# starter\nneeds-enhancement: edge cases\n")
    skips = [
        base_skip("roi", disposition="decline"),
        base_skip("figma", disposition="defer", followup_ref="GH-9"),
        base_skip("test_plan", disposition="starter", starter_artifact="test-plan.md"),
        base_skip("deploy", disposition="decline", ack_by="ops-lead"),
    ]
    change = make_change(skips, tier=2)
    findings = C.check(change, CATALOG, tier=2, change_dir=str(tmp_path))
    assert findings == [], codes(findings)


# ── NEG-1/2: never silent ─────────────────────────────────────────────────────
def test_neg1_silent_skip_no_record():
    change = make_change([])
    change["workflow"]["steps"].append({"n": 3, "key": "roi", "label": "ROI", "status": "skipped", "phase": "Design"})
    assert "SILENT_SKIP" in blockers(C.check(change, CATALOG))


def test_neg2_empty_actor_or_reason():
    assert "SILENT_SKIP" in blockers(C.check(make_change([base_skip("roi", actor="")]), CATALOG))
    assert "SILENT_SKIP" in blockers(C.check(make_change([base_skip("roi", reason="  ")]), CATALOG))


def test_bad_disposition_blocks():
    assert "SILENT_SKIP" in blockers(C.check(make_change([base_skip("roi", disposition="maybe")]), CATALOG))


# ── NEG-3/4: floor ────────────────────────────────────────────────────────────
def test_neg3_floor_no_ack():
    # deploy is floor at every tier; skipping it needs ack_by
    b = blockers(C.check(make_change([base_skip("deploy")], tier=2), CATALOG))
    assert "FLOOR_NO_ACK" in b


def test_neg4_floor_hard_gate_no_waiver():
    # qa_verify is floor at tier 3 AND a hard-gate step → needs a waiver even with ack
    skip = base_skip("qa_verify", ack_by="qa-lead")
    b = blockers(C.check(make_change([skip], tier=3), CATALOG))
    assert "FLOOR_NO_WAIVER" in b
    # with a waiver linked, that blocker clears
    skip2 = base_skip("qa_verify", ack_by="qa-lead", waiver_ref="W-12")
    assert "FLOOR_NO_WAIVER" not in blockers(C.check(make_change([skip2], tier=3), CATALOG))


def test_floor_only_at_high_tier():
    # qa_verify at tier 2 is standard → no floor requirements
    assert C.check(make_change([base_skip("qa_verify")], tier=2), CATALOG) == []


# ── NEG-5: no_omit (TDD) ──────────────────────────────────────────────────────
def test_neg5_no_omit_cannot_defer_or_decline():
    assert "NO_OMIT" in blockers(C.check(make_change([base_skip("red", disposition="defer")]), CATALOG))
    assert "NO_OMIT" in blockers(C.check(make_change([base_skip("green", disposition="decline")]), CATALOG))


def test_no_omit_starter_is_allowed(tmp_path):
    art = tmp_path / "red-starter.md"
    art.write_text("one happy-path test\nneeds-enhancement: edge cases\n")
    skip = base_skip("red", disposition="starter", starter_artifact="red-starter.md")
    assert C.check(make_change([skip]), CATALOG, change_dir=str(tmp_path)) == []


# ── NEG-6: starter marking ────────────────────────────────────────────────────
def test_neg6_starter_missing_or_unmarked(tmp_path):
    # no artifact path
    assert "STARTER_MARK" in codes(C.check(make_change([base_skip("test_plan", disposition="starter")]), CATALOG))
    # artifact exists but not marked
    bad = tmp_path / "x.md"; bad.write_text("# looks complete\n")
    skip = base_skip("test_plan", disposition="starter", starter_artifact="x.md")
    assert "STARTER_MARK" in codes(C.check(make_change([skip]), CATALOG, change_dir=str(tmp_path)))


# ── NEG-7: ledger ↔ steps ─────────────────────────────────────────────────────
def test_neg7_ledger_step_mismatch():
    # a skip record whose step is 'done' in steps[] (not skipped/starter)
    change = make_change([base_skip("roi")], step_over={"roi": "done"})
    assert "LEDGER_STEPS" in codes(C.check(change, CATALOG))
    # a skip record for a step absent from steps[] (not auto-added)
    change2 = {"first_pass": True, "tier": 2, "change_id": "GH-1",
               "workflow": {"id": "development", "steps": [{"n": 2, "key": "green", "status": "done", "phase": "Build"}]},
               "skips": [base_skip("ghost_step")]}
    assert "LEDGER_STEPS" in codes(C.check(change2, CATALOG))


# ── NEG-8: catalog monotonicity ───────────────────────────────────────────────
def test_neg8_crit_monotonicity():
    bad = {"x": {"key": "x", "crit": "floor", "crit_by_tier": {3: "ceremony"}}}
    assert "CRIT_MONOTONIC" in codes(C.lint_catalog(bad))
    good = {"x": {"key": "x", "crit": "standard", "crit_by_tier": {3: "floor"}}}
    assert C.lint_catalog(good) == []


# ── NEG-9: roll-up ────────────────────────────────────────────────────────────
def test_neg9_rollup_missing():
    change = make_change([base_skip("roi")], change_id="GH-7")
    empty_rollup = {"entries": []}
    assert "ROLLUP" in codes(C.check(change, CATALOG, rollup=empty_rollup))
    full = {"entries": [{"change_id": "GH-7", "step": "roi"}]}
    assert "ROLLUP" not in codes(C.check(change, CATALOG, rollup=full))


# ── non-waivable set + back-compat ────────────────────────────────────────────
def test_core_findings_are_non_waivable():
    for code in ("SILENT_SKIP", "FLOOR_NO_ACK", "FLOOR_NO_WAIVER", "NO_OMIT",
                 "UNKNOWN_STEP", "INVALID_STATUS", "INVALID_TIER"):
        assert code in C.NON_WAIVABLE


# ── round-1 adversarial regressions (a mismatch must fail CLOSED, not coerce to a safe default) ──
def test_r1_unknown_step_key_blocks_not_degrades_to_standard():
    # a floor key with a trailing space / wrong case is UNKNOWN, never resolved to `standard` (CRIT-1)
    for k in ("deploy ", "Deploy", "dep loy"):
        ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": k, "status": "skipped"}]},
              "skips": [base_skip(k, disposition="decline")]}
        assert "UNKNOWN_STEP" in blockers(C.check(ch, CATALOG)), k


def test_r1_unrecognized_status_blocks():
    # a floor step hidden behind a bogus status ('declined') with NO record must BLOCK (CRIT-2)
    for status in ("declined", "omitted", "n/a", "lightened", ""):
        ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "deploy", "status": status}]}, "skips": []}
        assert "INVALID_STATUS" in blockers(C.check(ch, CATALOG)), status


def test_r1_non_int_tier_blocks_and_fails_safe_high():
    # string/bool tier must BLOCK and not default to 2 (which would miss tier-3 floors) (HIGH-3)
    for t in ("3", True, -1, 9, 2.0):
        ch = {"first_pass": True, "tier": t, "workflow": {"steps": [{"key": "arch_review", "status": "skipped"}]},
              "skips": [base_skip("arch_review", disposition="decline")]}
        b = blockers(C.check(ch, CATALOG))
        assert "INVALID_TIER" in b and "FLOOR_NO_ACK" in b, t   # floor enforced at fail-safe tier 4


def test_r1_hard_gate_set_is_accurate():
    # dead entries do no harm; deploy/promote are ack-only (no waiver); real gates need a waiver (HIGH-4)
    deploy = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "deploy", "status": "skipped"}]},
              "skips": [base_skip("deploy", disposition="decline", ack_by="ops")]}
    assert C.check(deploy, CATALOG) == []          # deploy floor: ack is the control, no waiver gate
    for gate in ("qa_verify", "arch_review"):      # floor gates at tier 3 need a waiver
        ch = {"first_pass": True, "tier": 3, "workflow": {"steps": [{"key": gate, "status": "skipped"}]},
              "skips": [base_skip(gate, disposition="decline", ack_by="lead")]}
        assert "FLOOR_NO_WAIVER" in blockers(C.check(ch, CATALOG)), gate


def test_r2_starter_artifact_directory_blocks_not_crashes(tmp_path):
    # round-2 HIGH: a starter_artifact pointing at a directory must BLOCK (STARTER_MARK), never crash open()
    (tmp_path / "adir").mkdir()
    ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "test_plan", "status": "starter"}]},
          "skips": [base_skip("test_plan", disposition="starter", starter_artifact="adir")]}
    assert "STARTER_MARK" in codes(C.check(ch, CATALOG, change_dir=str(tmp_path)))   # no exception


def test_r2_malformed_structures_fail_closed():
    # round-2 MED: a `steps`/`skips` mapping (not list) must not coerce to empty and hide a floor skip
    ch = {"first_pass": True, "tier": 3, "workflow": {"steps": {"qa_verify": "skipped"}}, "skips": []}
    assert "MALFORMED" in blockers(C.check(ch, CATALOG))
    ch2 = {"first_pass": True, "tier": 2, "workflow": {"steps": []}, "skips": {"x": 1}}
    assert "MALFORMED" in blockers(C.check(ch2, CATALOG))


def test_r2_duplicate_step_key_flagged():
    ch = {"first_pass": True, "tier": 2,
          "workflow": {"steps": [{"key": "deploy", "status": "skipped"}, {"key": "deploy", "status": "done"}]},
          "skips": [base_skip("deploy", disposition="decline", ack_by="ops")]}
    assert "MALFORMED" in blockers(C.check(ch, CATALOG))


def test_r2_resolve_crit_is_monotonic_safe():
    # a demoting crit_by_tier can never LOWER a floor at runtime (defense-in-depth), and the lint blocks it
    assert C.resolve_crit({"crit": "floor", "crit_by_tier": {4: "ceremony"}}, 4) == "floor"
    assert C.resolve_crit({"crit": "standard", "crit_by_tier": {3: "floor"}}, 3) == "floor"
    assert "CRIT_MONOTONIC" in C.NON_WAIVABLE
    assert any(f["code"] == "CRIT_MONOTONIC" for f in C.lint_catalog({"x": {"key": "x", "crit": "floor", "crit_by_tier": {3: "ceremony"}}}))


def test_r3_hostile_input_fails_closed_never_crashes(tmp_path):
    # round-3: run() must return findings (exit-2 material), never traceback, on hostile top-level input
    import yaml
    cases = [
        {"first_pass": True, "workflow": "development"},                       # workflow a string
        {"first_pass": True, "workflow": None, "skips": []},                   # workflow null
        {"first_pass": True, "tier": 2, "workflow": {"id": "developement",     # typo'd workflow id
         "steps": [{"key": "deploy", "status": "skipped"}]},
         "skips": [base_skip("deploy", disposition="decline")]},
        {"first_pass": True, "workflow": {"steps": [{"key": ["a"], "status": "skipped"}]}, "skips": []},  # unhashable key
        {"first_pass": True, "workflow": {"steps": [{"key": "deploy", "status": ["skipped"]}]},           # unhashable status
         "skips": [base_skip("deploy", disposition="decline", ack_by="x")]},
    ]
    wpath = os.path.join(HERE, "..", "..", "ai", "shared", "workflows.yaml")
    for i, ch in enumerate(cases):
        p = tmp_path / f"c{i}.yaml"; p.write_text(yaml.safe_dump(ch))
        fs = C.run(str(p), wpath)                       # must not raise
        assert any(not f["waivable"] for f in fs), (i, fs)   # and must block


def test_r3_malformed_catalog_cbt_does_not_crash():
    # round-3 MED: a nested-dict crit_by_tier value must be ignored, not crash resolve_crit / lint_catalog
    assert C.resolve_crit({"crit": "standard", "crit_by_tier": {3: {"nested": 1}}}, 3) == "standard"
    assert isinstance(C.lint_catalog({"x": {"key": "x", "crit": "floor", "crit_by_tier": {3: {"n": 1}}}}), list)
    # float-int crit_by_tier key now works instead of being silently ignored
    assert C.resolve_crit({"crit": "standard", "crit_by_tier": {2.0: "floor"}}, 2) == "floor"


def test_r3_non_dict_and_keyless_step_entries_flagged():
    ch = {"first_pass": True, "tier": 2, "skips": [],
          "workflow": {"steps": ["deploy", 42, {"status": "skipped"}]}}   # non-dicts + a keyless dict
    assert "MALFORMED" in blockers(C.check(ch, CATALOG))


def test_r4_unhashable_crit_and_status_do_not_crash():
    # round-4 LOW-1: a non-string `crit` value is unhashable — must not crash resolve_crit / lint_catalog
    assert C.resolve_crit({"crit": ["floor"]}, 2) == "standard"
    assert isinstance(C.lint_catalog({"x": {"key": "x", "crit": ["floor"]}}), list)
    # round-4 LOW-2: a non-string status must be flagged, not crash the SILENT_SKIP loop
    ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "deploy", "status": ["skipped"]}]},
          "skips": [base_skip("deploy", disposition="decline", ack_by="x")]}
    assert "INVALID_STATUS" in blockers(C.check(ch, CATALOG))


def test_r4_malformed_rollup_warns_not_blocks():
    # round-4 LOW-3: a malformed AUXILIARY roll-up warns (waivable), it does not block the change
    ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "roi", "status": "skipped"}]},
          "skips": [base_skip("roi", disposition="decline")]}
    fs = C.check(ch, CATALOG, rollup=[1, 2])
    assert [f for f in fs if not f["waivable"]] == []      # no blocker
    assert any(f["code"] == "ROLLUP" for f in fs)          # but a warning


def test_r4_duplicate_yaml_key_rejected(tmp_path):
    # round-4 LOW-4: a forged ledger hiding a skip behind a duplicate `workflow:` key must be rejected
    p = tmp_path / "dup.yaml"
    p.write_text("first_pass: true\ntier: 2\n"
                 "workflow:\n  steps: [ { key: deploy, status: skipped } ]\n"
                 "workflow:\n  steps: []\nskips: []\n")
    fs = C.run(str(p), os.path.join(HERE, "..", "..", "ai", "shared", "workflows.yaml"))
    assert any(not f["waivable"] for f in fs)              # MALFORMED, blocks


def test_r1_starter_marker_must_head_a_line(tmp_path):
    buried = tmp_path / "x.md"; buried.write_text("# looks done\n<!-- needs-enhancement -->\n")
    ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "test_plan", "status": "starter"}]},
          "skips": [base_skip("test_plan", disposition="starter", starter_artifact="x.md")]}
    assert "STARTER_MARK" in codes(C.check(ch, CATALOG, change_dir=str(tmp_path)))


def test_back_compat_non_first_pass():
    # a change without first_pass validates clean even with junk skip data
    change = {"tier": 2, "workflow": {"steps": [{"key": "roi", "status": "skipped"}]}, "skips": []}
    assert C.check(change, CATALOG) == []


def test_defer_without_followup_warns_not_blocks():
    fs = C.check(make_change([base_skip("figma", disposition="defer")]), CATALOG)
    assert "DEFER_NO_FOLLOWUP" in codes(fs) and "DEFER_NO_FOLLOWUP" not in blockers(fs)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
