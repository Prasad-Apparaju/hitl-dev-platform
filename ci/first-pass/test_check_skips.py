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


# A real change file is seeded from the catalog and carries EVERY step, so the fixture does too.
# It used to seed only the load-bearing ones, which made every other catalog step look deliberately
# deleted — fine while only floor/no_omit absence was checked, wrong once PLAN_PRUNED (CR-3) landed.
# `omit=(...)` is how a test deliberately deletes a step.
LOADBEARING = ["deploy", "promote", "integration_verify", "red", "green",
               "impact", "packet", "arch_review", "qa_verify", "rollout"]


def make_change(skips, step_over=None, tier=2, first_pass=True, change_id="GH-1", omit=()):
    over = step_over or {}
    by_key = {}
    for k in CATALOG:
        if k not in omit:
            by_key[k] = {"n": 1, "key": k, "label": k, "status": "done", "phase": "X"}
    for s in skips:
        k = s["step"]
        if k in omit:                       # omit wins, so "deleted AND recorded" is expressible
            continue
        status = over.get(k, "starter" if s.get("disposition") == "starter" else "skipped")
        by_key[k] = {"n": 1, "key": k, "label": k, "status": status, "phase": "X"}
    for k, v in over.items():                      # allow overriding a load-bearing step's status directly
        if k in by_key:
            by_key[k]["status"] = v
    return {"first_pass": first_pass, "tier": tier, "change_id": change_id,
            "workflow": {"id": "development", "steps": list(by_key.values())}, "skips": skips}


def base_skip(step, **kw):
    d = {"step": step, "actor": "pm@team", "reason": "thin v1", "ts": "2026-07-27T00:00:00Z",
         "disposition": "decline"}
    d.update(kw)
    return d


# ── resolve_crit + catalog ────────────────────────────────────────────────────
def test_resolve_crit_tier_scoped():
    # `packet` stands in for what `impact` used to demonstrate here: impact analysis left the plan
    # in #97, because it is what produces the plan rather than a step inside one.
    assert C.resolve_crit(CATALOG["packet"], 2) == "standard"
    assert C.resolve_crit(CATALOG["packet"], 3) == "floor"
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
    deploy = make_change([base_skip("deploy", disposition="decline", ack_by="ops")], tier=2)
    assert C.check(deploy, CATALOG) == []          # deploy floor: ack is the control, no waiver gate
    for gate in ("qa_verify", "arch_review"):      # floor gates at tier 3 need a waiver
        ch = make_change([base_skip(gate, disposition="decline", ack_by="lead")], tier=3)
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
    ch = make_change([base_skip("roi", disposition="decline")], tier=2)
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


def test_codex1_omitting_a_floor_step_is_incomplete_plan():
    # a load-bearing step DELETED from the plan (not skipped, no record) must BLOCK — the completeness bypass
    ch = make_change([], omit=("deploy",))            # deploy floor step removed from steps[]
    assert "INCOMPLETE_PLAN" in blockers(C.check(ch, CATALOG, tier=2))
    ch2 = make_change([], omit=("red",))              # a no_omit (TDD) step removed
    assert "INCOMPLETE_PLAN" in blockers(C.check(ch2, CATALOG, tier=2))
    # the reviewer's exact case: only a ceremony step present, everything load-bearing gone
    bare = {"first_pass": True, "tier": 4, "workflow": {"id": "development",
            "steps": [{"key": "roi", "status": "done"}]}, "skips": []}
    assert "INCOMPLETE_PLAN" in blockers(C.check(bare, CATALOG))


def test_codex2_falsey_non_bool_first_pass_still_enforces():
    # `first_pass: []` / 0 / "" must NOT be read as false and disable enforcement
    for val in ([], {}, 0, ""):
        ch = {"first_pass": val, "tier": 4, "workflow": {"id": "development",
              "steps": [{"key": "deploy", "status": "skipped"}]}, "skips": []}
        b = blockers(C.check(ch, CATALOG))
        assert "MALFORMED" in b and b, val       # malformed + full enforcement (not clean)
    assert C.check({"first_pass": False, "tier": 2}, CATALOG) == []   # literal false = back-compat clean


def test_codex3_missing_or_null_status_blocks():
    # deploy (floor) present in the plan but with NO status / explicit null must not pass as clean
    steps = [{"key": k, "status": "done"} for k in LOADBEARING if k != "deploy"]
    for bad_deploy in ({"key": "deploy"}, {"key": "deploy", "status": None}):
        ch = {"first_pass": True, "tier": 2, "workflow": {"id": "development", "steps": steps + [bad_deploy]}, "skips": []}
        assert "INVALID_STATUS" in blockers(C.check(ch, CATALOG, tier=2)), bad_deploy


def test_codex4_starter_mark_is_non_waivable(tmp_path):
    bad = tmp_path / "s.md"; bad.write_text("# complete, no marker\n")
    ch = make_change([base_skip("test_plan", disposition="starter", starter_artifact="s.md")], tier=2)
    assert "STARTER_MARK" in blockers(C.check(ch, CATALOG, change_dir=str(tmp_path)))   # now blocks (exit 2)
    assert "STARTER_MARK" in C.NON_WAIVABLE


def test_r1_starter_marker_must_head_a_line(tmp_path):
    buried = tmp_path / "x.md"; buried.write_text("# looks done\n<!-- needs-enhancement -->\n")
    ch = {"first_pass": True, "tier": 2, "workflow": {"steps": [{"key": "test_plan", "status": "starter"}]},
          "skips": [base_skip("test_plan", disposition="starter", starter_artifact="x.md")]}
    assert "STARTER_MARK" in codes(C.check(ch, CATALOG, change_dir=str(tmp_path)))


def test_back_compat_non_first_pass():
    # A genuinely legacy change — no first_pass, nothing lightened — still validates clean.
    # This is the back-compat guarantee: pre-FR-29 files must keep passing untouched.
    change = {"tier": 2, "workflow": {"steps": [{"key": "roi", "status": "open"},
                                                {"key": "red", "status": "done"}]}, "skips": []}
    assert C.check(change, CATALOG) == []


def test_lightened_without_first_pass_is_a_blocker():
    # The inverse of back-compat, and the bug this check exists for: `skipped`/`starter` are written
    # only by the First Pass driver (schema: change-context.schema.yaml), so a lightened step with no
    # `first_pass` flag means enforcement silently never engaged and the ledger was never certified.
    # Previously this returned [] — a clean bill of health on an unenforced change.
    change = {"tier": 2, "workflow": {"steps": [{"key": "roi", "status": "skipped"}]}, "skips": []}
    fs = C.check(change, CATALOG)
    assert "FP_UNDECLARED" in codes(fs)
    assert "FP_UNDECLARED" in blockers(fs)


def test_unattributed_skips_without_first_pass_is_a_blocker():
    # Records present, flag absent, and nobody's name on them: still uncertified.
    bare = {k: v for k, v in base_skip("roi").items() if k != "actor"}
    change = {"tier": 2, "workflow": {"steps": [{"key": "roi", "status": "open"}]},
              "skips": [bare]}
    fs = C.check(change, CATALOG)
    assert "FP_UNDECLARED" in codes(fs)
    assert "FP_UNDECLARED" in blockers(fs)


def test_the_message_never_prescribes_falsifying_the_flag():
    """It used to say "Set `first_pass: true`" — on a change that never ran First Pass.

    Following your own validator's advice should not require recording something untrue. That
    instruction is why an honest decline was more expensive than a silent one.
    """
    bare = {k: v for k, v in base_skip("roi").items() if k != "actor"}
    fs = C.check({"tier": 2, "workflow": {"steps": [{"key": "roi", "status": "open"}]},
                  "skips": [bare]}, CATALOG)
    msg = " ".join(f["message"] for f in fs if f["code"] == "FP_UNDECLARED")
    assert "Set `first_pass: true` if the change is running First Pass" not in msg
    assert "ack_by" in msg or "actor" in msg, msg


def test_an_attributed_skip_outside_first_pass_is_accepted_and_still_enforced():
    """The 2am path. Declining with a name on it must not turn CI red...

    ...but accepting it must not mean skipping enforcement either: a floor step declined with a
    name and no waiver has to still block, or this trade would be worse than the red PR it removes.
    """
    ok = {"tier": 2, "workflow": {"steps": [{"key": "roi", "status": "skipped"}]},
          "skips": [base_skip("roi")]}
    fs = C.check(ok, CATALOG)
    assert "FP_UNDECLARED" not in codes(fs), "an attributed decline should not be refused"

    floor = {"tier": 2, "workflow": {"steps": [{"key": "deploy", "status": "skipped"}]},
             "skips": [dict(base_skip("deploy"), disposition="decline")]}
    fs2 = C.check(floor, CATALOG)
    assert blockers(fs2), "a floor step declined with only a name must still block"


def test_first_pass_false_with_clean_plan_still_passes():
    # Explicit `first_pass: false` on an untouched plan is a legitimate, deliberate state.
    change = {"tier": 2, "first_pass": False,
              "workflow": {"steps": [{"key": "roi", "status": "open"}]}, "skips": []}
    assert C.check(change, CATALOG) == []


def test_defer_without_followup_warns_not_blocks():
    fs = C.check(make_change([base_skip("figma", disposition="defer")]), CATALOG)
    assert "DEFER_NO_FOLLOWUP" in codes(fs) and "DEFER_NO_FOLLOWUP" not in blockers(fs)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))


def test_low_tier_must_name_a_person_and_a_reason():
    # Tier is self-declared and nothing validates it against the change's actual shape. Tier <= 1 is
    # what unlocks the batch-decline path at intake, so the declaration is held to the same standard
    # as a skip: accountable to a human, with a reason. (The floor demotion that matters is 3 -> 2 —
    # see test_the_big_floor_demotion_is_three_to_two — and it requires no attribution at all.)
    fs = C.check(make_change([], tier=1), CATALOG, tier=1)
    assert "TIER_UNATTRIBUTED" in codes(fs)
    assert "TIER_UNATTRIBUTED" not in blockers(fs)      # accounted for, not blocked


def test_low_tier_with_attribution_is_clean():
    change = make_change([], tier=1)
    change["tier_set_by"] = "arch@team"
    change["tier_reason"] = "single-function regression, no interface change"
    assert C.check(change, CATALOG, tier=1) == []


def test_tier_two_and_above_needs_no_attribution():
    # The default path is unchanged — attribution is the price of the LIGHT path, not of every change.
    assert C.check(make_change([], tier=2), CATALOG, tier=2) == []


# ── the tier facts the doctrine asserts, pinned to the catalog ────────────────
# Five shipped files stated "a low tier demotes impact/packet/arch_review/qa_verify/rollout from
# floor to standard". That was false: those five are crit_by_tier {3: floor}, so they are already
# standard at tier 2 and the 2->1 boundary does not move them. Prose drifted from the catalog and
# nothing caught it. These tests make the catalog the arbiter.

def test_the_big_floor_demotion_is_three_to_two():
    # Four now, not five: `impact` left the plan in #97. The demotion it describes is unchanged
    # for the rest, and `retro` joined as floor at EVERY tier so it never appears in a demotion.
    five = ["packet", "arch_review", "qa_verify", "rollout"]
    for k in five:
        assert C.resolve_crit(CATALOG[k], 3) == "floor", f"{k} should be floor at tier 3"
        assert C.resolve_crit(CATALOG[k], 2) == "standard", f"{k} should be standard at tier 2"


def test_two_to_one_moves_only_integration_verify():
    moved = {k for k, m in CATALOG.items()
             if C.resolve_crit(m, 2) == "floor" and C.resolve_crit(m, 1) != "floor"}
    assert moved == {"integration_verify"}, (
        "the 2->1 demotion set changed; every doctrine sentence naming it must be updated too")


def test_deploy_and_promote_never_demote():
    for t in range(5):
        assert C.resolve_crit(CATALOG["deploy"], t) == "floor"
        assert C.resolve_crit(CATALOG["promote"], t) == "floor"


# ── PLAN_PRUNED (CR-3 / CR-16): deleting a step is not a way to skip it silently ──

def test_deleting_a_ceremony_step_warns():
    # Previously certified clean: no record, no actor, no reason, and invisible in the trail.
    fs = C.check(make_change([], omit=("roi",)), CATALOG)
    assert "PLAN_PRUNED" in codes(fs)
    assert "PLAN_PRUNED" not in blockers(fs)      # waivable — pruning can be legitimate, not silent


def test_deleting_a_standard_step_warns():
    fs = C.check(make_change([], omit=("conventions",)), CATALOG)
    assert "PLAN_PRUNED" in codes(fs) and "conventions" in str(fs)


def test_recording_a_skip_instead_of_deleting_avoids_the_warning():
    # The honest path stays cheaper than deletion: keep the step, mark it skipped, record it.
    assert "PLAN_PRUNED" not in codes(C.check(make_change([base_skip("roi")]), CATALOG))


def test_a_step_both_deleted_and_recorded_is_a_ledger_mismatch_not_a_prune():
    # Deleting the step while keeping its record is not "pruned with a record" — the record now points
    # at a step the plan does not contain, which is the stronger LEDGER_STEPS finding. PLAN_PRUNED is
    # for the case with no record at all, so it must not fire here and mask the mismatch.
    change = make_change([base_skip("roi")], omit=("roi",))
    assert "roi" not in {s["key"] for s in change["workflow"]["steps"]}
    fs = C.check(change, CATALOG)
    assert "LEDGER_STEPS" in codes(fs)
    assert "PLAN_PRUNED" not in codes(fs)


def test_deleting_a_load_bearing_step_still_blocks_not_warns():
    # floor/no_omit keep the stronger, non-waivable finding — PLAN_PRUNED must not soften it.
    fs = C.check(make_change([], omit=("deploy",)), CATALOG)
    assert "INCOMPLETE_PLAN" in blockers(fs)
    assert "deploy" not in [f["message"] for f in fs if f["code"] == "PLAN_PRUNED"]


def test_a_complete_plan_warns_about_nothing():
    assert C.check(make_change([]), CATALOG) == []


# --- the fourth disposition (#97) ------------------------------------------------------------

def test_not_applicable_is_a_valid_disposition():
    """A right-sized plan drops steps because the rules say they do not apply, which is not the
    same act as a human declining them. Without a disposition for it, the only cheap option is
    `decline`, and the ledger then records someone declining ~25 steps they never looked at — which
    the closing retrospective reads back as "what was left out and why"."""
    assert "not_applicable" in C.DISPOSITIONS


def test_a_rule_may_not_retire_a_floor_step():
    """NEG: `not_applicable` is the rules speaking, and the rules may not retire a load-bearing
    step. If they could, the floor is a hole — any step dropped by asserting a rule excluded it,
    with no ack_by, no waiver, and nobody's judgement on the record."""
    ch = make_change([base_skip("deploy", disposition="not_applicable")], tier=2)
    assert "RULE_OVER_FLOOR" in blockers(C.check(ch, CATALOG))


def test_a_rule_may_not_retire_a_no_omit_step():
    ch = make_change([base_skip("red", disposition="not_applicable")], tier=1)
    assert "RULE_OVER_FLOOR" in blockers(C.check(ch, CATALOG))


def test_rule_over_floor_is_non_waivable():
    """Consistent with the other floor protections: a waiver clears a risk, never a bypass."""
    assert "RULE_OVER_FLOOR" in C.NON_WAIVABLE


def test_not_applicable_still_needs_an_actor_and_a_reason():
    """One confirmation records the whole set, and the human who confirmed owns it. A rule doing
    the deciding is not the same as nobody being accountable for the decision."""
    ch = make_change([{"step": "roi", "disposition": "not_applicable"}], tier=1)
    assert "SILENT_SKIP" in blockers(C.check(ch, CATALOG))


def test_not_applicable_on_an_ordinary_step_certifies_clean():
    ch = make_change([base_skip("roi", disposition="not_applicable",
                                reason="no user-facing surface in this change")], tier=1)
    assert "RULE_OVER_FLOOR" not in codes(C.check(ch, CATALOG))
    assert "SILENT_SKIP" not in codes(C.check(ch, CATALOG))


def test_not_applicable_does_not_resurface():
    """Nothing was deferred, so there is nothing to come back to. Nagging about work nobody chose
    to postpone is what gets resurfacing switched off."""
    sys.path.insert(0, HERE)
    import resurface as R
    rollup = {"entries": [
        {"change_id": "GH-9", "step": "roi", "crit": "standard", "resolved": False,
         "disposition": "not_applicable", "domains": ["billing"], "paths": []},
        {"change_id": "GH-9", "step": "docs", "crit": "standard", "resolved": False,
         "disposition": "decline", "domains": ["billing"], "paths": []}]}
    raised = [e["step"] for e in R.surface(rollup, ["billing"], [])]
    assert raised == ["docs"], raised


# --- the intake stub (#97) --------------------------------------------------------------------

def test_a_genuine_stub_certifies_clean():
    """Under right-sizing the plan does not exist until impact analysis has run, so intake writes a
    stub. Certifying it against the plan checks produced 9 blocking INCOMPLETE_PLANs and 25
    PLAN_PRUNED warnings for a change nobody had sized yet."""
    stub = {"change_id": "GH-1", "tier": 3, "tier_provisional": True,
            "status": "intake", "first_pass": True}
    assert C.check(stub, CATALOG) == []


def test_intake_status_does_not_exempt_a_change_that_has_a_plan():
    """NEG: the exemption is the dangerous part, because "no plan block" is what a bypass looks
    like. Claiming intake while carrying a plan is itself a block, AND every normal check still
    runs — so the status cannot be used to un-certify planned work."""
    # omit a floor step, so INCOMPLETE_PLAN would fire on any change that is actually certified
    ch = make_change([], tier=2, omit=("deploy",))
    ch["status"] = "intake"
    found = C.check(ch, CATALOG)
    assert "INTAKE_NOT_EMPTY" in blockers(found)
    # the plan checks still ran: the status did not buy an exemption from them
    assert "INCOMPLETE_PLAN" in blockers(found), codes(found)


def test_intake_status_does_not_exempt_a_change_that_has_skips():
    ch = {"change_id": "GH-1", "tier": 2, "status": "intake", "first_pass": True,
          "skips": [base_skip("roi")]}
    assert "INTAKE_NOT_EMPTY" in blockers(C.check(ch, CATALOG))


def test_intake_not_empty_is_non_waivable():
    assert "INTAKE_NOT_EMPTY" in C.NON_WAIVABLE


def test_a_provisional_tier_may_not_survive_past_intake():
    """NEG: the stub's tier is HITL's placeholder, not a human's declaration. Step 4 replaces it
    with one proposed from impact findings and confirmed by a person. A provisional tier on a
    planned change means that confirmation never happened."""
    ch = make_change([], tier=3)
    ch["tier_provisional"] = True
    assert "TIER_PROVISIONAL" in blockers(C.check(ch, CATALOG))


def test_the_provisional_tier_is_the_strictest_one():
    """It fails closed. If anything does resolve criticality against a stub, it resolves at the
    tier that locks the most, not the least."""
    assert C.resolve_crit(CATALOG["packet"], 3) == "floor"
    assert C.resolve_crit(CATALOG["packet"], 1) != "floor"


# --- the impact record (#97, impl review 1) ----------------------------------------------------

def test_a_named_impact_record_that_is_missing_blocks():
    """The design, the schema header and the generator's comment all said this blocks. None of them
    wrote the check — the recurring defect of this repo, appearing inside the fix for it."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/nope.yaml"
        assert "IMPACT_RECORD" in blockers(C.check(ch, CATALOG, change_dir=d))


def test_an_empty_impact_record_blocks_too():
    import os as _os
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        _os.makedirs(_os.path.join(d, ".hitl", "impact"))
        open(_os.path.join(d, ".hitl", "impact", "x.yaml"), "w").write("change_id: GH-1\n")
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/x.yaml"
        assert "IMPACT_RECORD" in blockers(C.check(ch, CATALOG, change_dir=d)), \
            "an empty record is the same as none"


def test_an_unreadable_impact_record_fails_closed():
    """NEG: a record we cannot parse is not one we can vouch for."""
    import os as _os
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        _os.makedirs(_os.path.join(d, ".hitl", "impact"))
        open(_os.path.join(d, ".hitl", "impact", "x.yaml"), "w").write("{ not: [valid\n")
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/x.yaml"
        assert "IMPACT_RECORD" in blockers(C.check(ch, CATALOG, change_dir=d))


def test_a_real_impact_record_certifies_clean():
    import os as _os
    import tempfile
    import yaml as _y
    with tempfile.TemporaryDirectory() as d:
        _os.makedirs(_os.path.join(d, ".hitl", "impact"))
        _y.safe_dump({"change_id": "GH-1", "findings": {"area": "billing"}},
                     open(_os.path.join(d, ".hitl", "impact", "x.yaml"), "w"))
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/x.yaml"
        assert not [c for c in codes(C.check(ch, CATALOG, change_dir=d)) if "IMPACT" in c]


def test_a_change_naming_no_record_is_not_reported():
    """Every change file written before this feature is in that state, and they are not wrong. The
    design says a NAMED record that is missing blocks; it does not say one must be named."""
    ch = make_change([], tier=2)
    assert not [c for c in codes(C.check(ch, CATALOG)) if "IMPACT" in c]


def test_impact_record_is_non_waivable():
    assert "IMPACT_RECORD" in C.NON_WAIVABLE


def test_the_impact_record_resolves_from_the_repo_root():
    """The pointer is repo-root relative (".hitl/impact/<id>.yaml"), and `run()` passes the
    directory CONTAINING the change file — `<repo>/.hitl`. Joining them looked for
    `<repo>/.hitl/.hitl/impact/...`, so every right-sized change died on a non-waivable block.

    The other four tests pass `change_dir=<repo root>`, which encodes the INTENDED semantics and
    never exercises the path run() builds. This one uses the real directory layout."""
    import os as _os
    import tempfile
    with tempfile.TemporaryDirectory() as root:
        _os.makedirs(_os.path.join(root, ".hitl", "impact"))
        import yaml as _y
        _y.safe_dump({"change_id": "GH-1", "findings": {"area": "b"}},
                     open(_os.path.join(root, ".hitl", "impact", "GH-1.yaml"), "w"))
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/GH-1.yaml"
        # change_dir as run() computes it: the directory holding the change file
        found = C.check(ch, CATALOG, change_dir=_os.path.join(root, ".hitl"))
        assert not [c for c in codes(found) if "IMPACT" in c], codes(found)


def test_a_record_for_a_different_change_blocks():
    """The schema said a mismatch is a blocking error; nothing implemented it, so a plan could be
    justified by another change's sizing and certify clean. That is worse than no record, because
    it looks accounted for."""
    import os as _os
    import tempfile
    import yaml as _y
    with tempfile.TemporaryDirectory() as root:
        _os.makedirs(_os.path.join(root, ".hitl", "impact"))
        _y.safe_dump({"change_id": "GH-999", "workflow": "development", "findings": {"area": "b"}},
                     open(_os.path.join(root, ".hitl", "impact", "x.yaml"), "w"))
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/x.yaml"
        assert "IMPACT_RECORD" in blockers(C.check(ch, CATALOG,
                                                   change_dir=_os.path.join(root, ".hitl")))


def test_a_record_sized_against_another_workflow_blocks():
    import os as _os
    import tempfile
    import yaml as _y
    with tempfile.TemporaryDirectory() as root:
        _os.makedirs(_os.path.join(root, ".hitl", "impact"))
        _y.safe_dump({"change_id": "GH-1", "workflow": "brownfield", "findings": {"area": "b"}},
                     open(_os.path.join(root, ".hitl", "impact", "x.yaml"), "w"))
        ch = make_change([], tier=2)
        ch["impact_record"] = ".hitl/impact/x.yaml"
        assert "IMPACT_RECORD" in blockers(C.check(ch, CATALOG,
                                                   change_dir=_os.path.join(root, ".hitl")))


# ── conditional steps (#102) ─────────────────────────────────────────────────

def _with_record(ch, d, outcomes, findings=None):
    """Write an impact record under `d` and point the change at it. `outcomes` is
    {step: applies}; `findings` defaults to a change where the security question WAS asked."""
    import os as _os
    import yaml as _y
    _os.makedirs(_os.path.join(d, ".hitl", "impact"), exist_ok=True)
    body = {"change_id": ch["change_id"], "workflow": "development",
            "findings": {"area": "billing", "security_sensitive": False} if findings is None else findings,
            "rule_outcomes": [{"step": k, "applies": v, "needed_now": v,
                               "because": "conditional not activated" if not v else "fired"}
                              for k, v in outcomes.items()]}
    _y.safe_dump(body, open(_os.path.join(d, ".hitl", "impact", "x.yaml"), "w"))
    ch["impact_record"] = ".hitl/impact/x.yaml"
    return ch


def _na(step, cond="security"):
    return base_skip(step, disposition="not_applicable",
                     reason="conditional (%s) not activated: none of security sensitive, interfaces changed, data migration" % cond)


def test_an_inactive_conditional_may_be_not_applicable_even_when_floor():
    """pentest is `cond: security` and `floor`. When its activator did not fire the sizer records it
    not_applicable — the step was never in the plan for the floor to protect. RULE_OVER_FLOOR and the
    floor-authority checks must not fire on it; before #102 the step could not appear at all.
    The exemption rests on the impact record saying the activator did not fire."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ch = _with_record(make_change([_na("pentest")], tier=3), d, {"pentest": False})
        codes = blockers(C.check(ch, CATALOG, change_dir=d))
        assert "RULE_OVER_FLOOR" not in codes and "FLOOR_NO_ACK" not in codes, codes
        assert "COND_UNCONFIRMED" not in codes, codes


def test_the_label_alone_does_not_exempt_a_conditional_floor_step():
    """`pentest: not_applicable` hand-written on a change with no record is one word walking a floor
    step past the gate. Without the record the step counts as active: the floor checks apply AND
    the mismatch is named."""
    ch = make_change([_na("pentest")], tier=3)
    codes = blockers(C.check(ch, CATALOG))
    assert "COND_UNCONFIRMED" in codes and "RULE_OVER_FLOOR" in codes, codes


def test_a_record_showing_the_activator_fired_refutes_not_applicable():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ch = _with_record(make_change([_na("pentest")], tier=3), d, {"pentest": True},
                          findings={"area": "billing", "security_sensitive": True})
        codes = blockers(C.check(ch, CATALOG, change_dir=d))
        assert "COND_UNCONFIRMED" in codes and "RULE_OVER_FLOOR" in codes, codes


def test_a_record_with_no_outcome_for_the_step_does_not_exempt_it():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ch = _with_record(make_change([_na("pentest")], tier=3), d, {"deploy": True})
        assert "COND_UNCONFIRMED" in blockers(C.check(ch, CATALOG, change_dir=d))


def test_silence_on_the_security_question_is_not_a_no():
    """The sizer reads a missing `security_sensitive` as false, so a change nobody asked about sizes
    exactly like a harmless one. The gate is where the record is in hand, so it is where "nobody
    asked" is caught. A non-security conditional (baseline) does not need the answer."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        unasked = {"area": "billing"}
        ch = _with_record(make_change([_na("sec_design")], tier=2), d, {"sec_design": False}, findings=unasked)
        assert "COND_UNCONFIRMED" in blockers(C.check(ch, CATALOG, change_dir=d))
        ch = _with_record(make_change([_na("cve_audit", "upgrade")], tier=2), d, {"cve_audit": False}, findings=unasked)
        assert "COND_UNCONFIRMED" in blockers(C.check(ch, CATALOG, change_dir=d)), "cve_audit engages on the answer too"
        ch = _with_record(make_change([_na("baseline", "perf")], tier=2), d, {"baseline": False}, findings=unasked)
        assert "COND_UNCONFIRMED" not in codes(C.check(ch, CATALOG, change_dir=d))


def test_cond_unconfirmed_is_non_waivable():
    assert "COND_UNCONFIRMED" in C.NON_WAIVABLE


def test_an_active_conditional_is_protected_like_any_floor_step():
    """Any disposition other than not_applicable means the step WAS active — a human is skipping it.
    Then the floor applies in full: a floor skip needs ack_by."""
    ch = make_change([base_skip("pentest", disposition="decline", reason="no time")], tier=3)
    assert "FLOOR_NO_ACK" in blockers(C.check(ch, CATALOG))


def test_the_conditional_exemption_does_not_leak_to_ordinary_floor_steps():
    ch = make_change([base_skip("deploy", disposition="not_applicable")], tier=2)
    assert "RULE_OVER_FLOOR" in blockers(C.check(ch, CATALOG))
    assert not CATALOG["deploy"].get("cond")


# ── #111: departing upward from a light proposal is attributed too ────────────────────────────────

def test_tier_above_a_light_proposal_needs_attribution():
    ch = make_change([], tier=2); ch["tier_proposed"] = 1
    assert "TIER_UNATTRIBUTED" in codes(C.check(ch, CATALOG))
    ch["tier_set_by"] = "pm@team"; ch["tier_reason"] = "touches payments after all"
    assert "TIER_UNATTRIBUTED" not in codes(C.check(ch, CATALOG))
    ch2 = make_change([], tier=2); ch2["tier_proposed"] = 2
    assert "TIER_UNATTRIBUTED" not in codes(C.check(ch2, CATALOG)), "agreeing with the proposal needs nothing"
