#!/usr/bin/env python3
"""Conformance for the First Pass library (dispositions, starters, resurface, permissions).
FR-29 test-plan §4-§9. Adversarial edges included."""
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import check_skips as C
import dispositions as D
import starters as S
import resurface as R
import permissions as P

CATALOG = C.load_catalog(os.path.join(HERE, "..", "..", "ai", "shared", "workflows.yaml"))


# ── dispositions (MENU-2, NOOMIT-1) ───────────────────────────────────────────
def test_floor_menu_is_keep_or_risk_accept():
    assert D.allowed_dispositions(CATALOG["deploy"], 2) == ["keep", "risk_accept"]
    # `packet` becomes floor at tier 3. `impact` used to sit here; it left the plan in #97,
    # because impact analysis is what PRODUCES the plan rather than a step inside one.
    assert D.allowed_dispositions(CATALOG["packet"], 3) == ["keep", "risk_accept"]
    assert D.allowed_dispositions(CATALOG["packet"], 2) != ["keep", "risk_accept"]


def test_no_omit_is_keep_or_starter_only():
    assert D.allowed_dispositions(CATALOG["red"], 2) == ["keep", "starter"]
    assert not D.is_allowed(CATALOG["red"], 2, "defer")
    assert not D.is_allowed(CATALOG["green"], 2, "decline")
    assert D.is_allowed(CATALOG["red"], 2, "starter")


def test_ceremony_and_standard_menus():
    # roi is ceremony with no starter → keep/defer/decline
    assert D.allowed_dispositions(CATALOG["roi"], 2) == ["keep", "defer", "decline"]
    assert not D.is_allowed(CATALOG["roi"], 2, "starter")   # no registry entry
    # test_plan is standard WITH a starter
    assert D.allowed_dispositions(CATALOG["test_plan"], 2) == ["keep", "starter", "defer", "decline"]
    assert D.is_allowed(CATALOG["test_plan"], 2, "decline")


def test_keep_always_allowed_and_junk_rejected():
    assert D.is_allowed(CATALOG["deploy"], 2, "keep")
    assert not D.is_allowed(CATALOG["roi"], 2, "risk_accept")   # not a ledger disposition
    assert not D.is_allowed(CATALOG["roi"], 2, "banana")


# ── starters (STARTER-1/2) ────────────────────────────────────────────────────
def test_acceptance_starter_is_the_working_system_bar():
    out = S.starter_for("packet")
    assert "a working version of the system exists and runs" in out
    assert S.STARTER_MARKER in out


def test_every_starter_marked_and_missing_is_none():
    for k in S.STARTERS:
        assert S.STARTER_MARKER in S.starter_for(k)
    assert S.starter_for("roi") is None and not S.has_starter("roi")


# ── resurface (RESURF-2/3/4) ──────────────────────────────────────────────────
def test_overlap_domain_and_path():
    e = {"domains": ["billing"], "paths": ["src/billing/"]}
    assert R.overlaps(e, ["billing"], [])
    assert R.overlaps(e, [], ["src/billing/refund.py"])
    assert not R.overlaps(e, ["shipping"], ["src/shipping/"])


def test_surface_excludes_ceremony_and_resolved_sorts_floor_first():
    rollup = {"entries": [
        {"step": "roi", "crit": "ceremony", "domains": ["billing"]},          # excluded (ceremony)
        {"step": "qa_verify", "crit": "floor", "domains": ["billing"]},        # included
        {"step": "test_plan", "crit": "standard", "domains": ["billing"]},     # included
        {"step": "docs", "crit": "standard", "domains": ["billing"], "resolved": True},  # excluded (resolved)
        {"step": "impact", "crit": "standard", "domains": ["shipping"]},       # excluded (no overlap)
    ]}
    out = R.surface(rollup, ["billing"], [])
    steps = [e["step"] for e in out]
    assert steps == ["qa_verify", "test_plan"]   # floor first, ceremony/resolved/non-overlap gone


def test_message_is_non_blaming():
    msg = R.message({"step": "qa_verify", "crit": "floor", "disposition": "decline",
                     "actor": "pm", "reason": "v1 speed"}).lower()
    assert not any(w in msg for w in R.BLAME_WORDS)
    assert "qa_verify" in msg and "v1 speed" in msg


# ── permissions (PERM-1/2/3, NEG-10) ──────────────────────────────────────────
def test_critical_actions_always_prompt():
    for a in ("deploy", "promote", "migrate", "external_send", "force_push", "secret_access", "delete"):
        assert P.decide(a, path="src/x.py", scope_paths=["src/"])[0] is True, a


def test_scoped_reads_and_edits_auto_allow():
    assert P.decide("read", "anything")[0] is False
    assert P.decide("edit", "src/billing/x.py", ["src/billing/"])[0] is False
    assert P.decide("write", "src/billing/y.py", ["src/billing/**"])[0] is False


def test_out_of_scope_and_unknown_prompt():
    assert P.decide("edit", "/etc/passwd", ["src/billing/"])[0] is True
    assert P.decide("write", "../other-repo/x", ["src/"])[0] is True
    assert P.decide("frobnicate")[0] is True   # fail-safe default


def test_path_traversal_cannot_escape_scope():
    # a `..` traversal must NOT prefix-match its way back into scope
    assert P.decide("edit", "src/billing/../../../etc/passwd", ["src/billing/"])[0] is True
    assert P.decide("write", "src/billing/../secrets", ["src/billing/**"])[0] is True
    # a sibling that merely shares a name prefix is not in scope ('src/billing-secrets' vs 'src/billing')
    assert P.decide("edit", "src/billing-secrets/x", ["src/billing"])[0] is True


def test_r1_reads_are_scope_gated():
    # round-1 MED-5: reads were ungated — an out-of-project read must now prompt; in-project is fine
    assert P.decide("read", "/etc/passwd", ["src/billing/**"])[0] is True
    assert P.decide("read", "../secrets.env")[0] is True
    assert P.decide("read", "src/anything.py")[0] is False


def test_r1_hidden_dir_not_confused_with_scope():
    # round-1 MED-6: '.src/billing' must NOT normalize to 'src/billing' and auto-allow
    assert P.decide("edit", ".src/billing/x", ["src/billing/**"])[0] is True
    assert P.decide("edit", "src/billing/x", ["src/billing/**"])[0] is False


def test_r1_blame_words_redacted_from_user_reason():
    # round-1 MED-7: blame words in the recorded reason must not leak into the reminder (incl. "should have")
    msg = R.message({"step": "qa_verify", "crit": "floor", "disposition": "decline", "actor": "d",
                     "reason": "the dev failed, was careless and should have known"}).lower()
    assert not any(w in msg for w in R.BLAME_WORDS)


def test_r2_windows_abs_paths_escape_project():
    # round-2 MED: Windows drive-letter / UNC absolute reads must prompt (POSIX isabs misses them)
    for p in ("C:\\secrets", "\\\\srv\\share\\x", "//srv/share/x"):
        assert P.decide("read", p)[0] is True, p


def test_codex8_malformed_permission_inputs_fail_safe():
    # a scalar scope_paths must NOT be iterated char-by-char into scopes 's','r','c' (auto-allowing 's/...')
    assert P.decide("edit", "s/secrets.txt", "src")[0] is True
    assert P.decide("read", None, ["src/**"])[0] is True        # missing read path prompts
    assert P.decide([], "x", ["src"])[0] is True                # non-string action prompts (no crash)
    assert P.decide("edit", 5, ["src"])[0] is True              # non-string path prompts


def test_codex11_resurface_helpers_do_not_crash_on_malformed():
    for bad in ([{"x": 1}],
                {"entries": [{"crit": [], "paths": ["src"], "resolved": False}]},
                {"entries": [{"crit": "standard", "domains": [[]], "resolved": False}]},
                {"entries": "nope"}, None):
        assert isinstance(R.surface(bad, ["api"], ["src/x"]), list)   # returns a list, never raises


def test_r2_blame_redaction_covers_inflections():
    # round-2 LOW: stems + hyphen/space variants + flexible whitespace
    msg = R.message({"reason": "careless, negligence, care-less, should  have, failing, sloppily"}).lower()
    for w in ("careless", "neglig", "care-less", "should  have", "failing", "sloppily"):
        assert w not in msg, w
    assert isinstance(R.message(None), str)   # non-dict entry is safe


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))


# ---------------------------------------------------------------- resurfacing digest (volume)

def _entry(step, crit, domain, resolved=False):
    return {"step": step, "crit": crit, "domains": [domain], "disposition": "decline",
            "actor": "a@b", "reason": "x", "resolved": resolved}


def test_digest_dedupes_by_step_and_area():
    # The same step lightened repeatedly in one domain is one reminder, not one per occurrence.
    dupes = [_entry("qa_verify", "floor", "billing")] * 4
    shown, remaining = R.digest(dupes)
    assert len(shown) == 1 and remaining == 0
    # ...but the same step in a DIFFERENT area is a genuinely different reminder.
    shown, _ = R.digest([_entry("qa_verify", "floor", "billing"), _entry("qa_verify", "floor", "payments")])
    assert len(shown) == 2


def test_digest_caps_and_counts_the_rest():
    entries = [_entry(f"step{i}", "standard", "billing") for i in range(9)]
    shown, remaining = R.digest(entries)
    assert len(shown) == R.DEFAULT_CAP and remaining == 9 - R.DEFAULT_CAP


def test_digest_keeps_the_most_critical_when_capping():
    # surface() sorts floor-first; digest must not reorder it away.
    entries = R.surface({"entries": [_entry("roi_std", "standard", "billing"),
                                     _entry("qa_verify", "floor", "billing"),
                                     _entry("conv", "standard", "billing"),
                                     _entry("rvw", "standard", "billing")]}, ["billing"], [])
    shown, remaining = R.digest(entries, cap=2)
    assert shown[0]["crit"] == "floor" and remaining == 2


def test_digest_tolerates_malformed_input():
    assert R.digest("not a list") == ([], 0)
    assert R.digest([None, 3, {"step": "x"}])[0] == [{"step": "x"}]
    assert R.digest([_entry("a", "floor", "b")], cap=0)[0]      # a nonsense cap falls back, never empties


def test_render_is_empty_when_nothing_to_raise():
    assert R.render([]) == ""


def test_render_appends_a_count_only_when_some_were_folded_away():
    few = [_entry("a", "floor", "billing")]
    assert "more unresolved" not in R.render(few)
    many = [_entry(f"s{i}", "standard", "billing") for i in range(6)]
    out = R.render(many)
    assert "3 more unresolved entries" in out and ".hitl/skip-ledger.yaml" in out


# ---------------------------------------------------------------- roll-up + CLI lifecycle

def _write(p, text):
    p.write_text(text, encoding="utf-8")
    return str(p)


_CHANGE = """change_id: GH-501
tier: 2
first_pass: true
manifest:
  domain: billing
allowed_paths:
  - src/billing/
skips:
  - { step: qa_verify, crit: floor, actor: "a@b", reason: "thin", disposition: decline, resolved: false }
"""


def test_to_rollup_stamps_scope_and_is_idempotent():
    import yaml
    change = yaml.safe_load(_CHANGE)
    rollup, added, _ = R.to_rollup(change, {})
    assert added == 1
    e = rollup["entries"][0]
    assert e["domains"] == ["billing"] and e["paths"] == ["src/billing/"] and e["change_id"] == "GH-501"
    # re-running the impact step must not duplicate
    rollup, added, _ = R.to_rollup(change, rollup)
    assert added == 0 and len(rollup["entries"]) == 1


def test_to_rollup_gives_each_entry_its_own_lists():
    # Sharing one list object across entries makes yaml.safe_dump emit &id001/*id001 anchors into the
    # ledger, which is valid YAML but hostile to anyone reading or diffing it.
    import yaml
    change = yaml.safe_load(_CHANGE)
    change["skips"].append({"step": "test_plan", "crit": "standard", "actor": "a@b",
                            "reason": "x", "disposition": "defer", "resolved": False})
    rollup, _, _ = R.to_rollup(change, {})
    a, b = rollup["entries"]
    assert a["domains"] is not b["domains"] and a["paths"] is not b["paths"]
    assert "&id" not in yaml.safe_dump(rollup, sort_keys=False)


def test_cli_does_not_resurface_a_change_to_itself(tmp_path, capsys):
    # After --append, a change's own skips overlap its own scope by construction. Reminding someone
    # about a decision they made minutes earlier at intake reads as nagging, not care.
    chg = _write(tmp_path / "c.yaml", _CHANGE)
    led = str(tmp_path / "l.yaml")
    assert R.main(["--change", chg, "--rollup", led, "--append"]) == 0
    assert "No unresolved skips overlap this change." in capsys.readouterr().out


def test_cli_resurfaces_to_a_later_change_in_the_same_area(tmp_path, capsys):
    chg = _write(tmp_path / "c.yaml", _CHANGE)
    led = str(tmp_path / "l.yaml")
    R.main(["--change", chg, "--rollup", led, "--append"])
    capsys.readouterr()
    later = _write(tmp_path / "c2.yaml",
                   "change_id: GH-502\nmanifest:\n  domain: billing\nallowed_paths:\n  - src/billing/\n")
    R.main(["--change", later, "--rollup", led])
    assert "qa_verify" in capsys.readouterr().out


def test_a_scope_less_change_still_reads_project_wide_entries(tmp_path, capsys):
    # The onboarding and docs routes that justified project-wide scope are exactly the ones that never
    # acquire scope. Returning early for them made the read dead precisely where it was needed.
    led = str(tmp_path / "l.yaml")
    first = _write(tmp_path / "a.yaml",
                   "change_id: GH-A\nskips:\n  - { step: qa_verify, crit: floor, actor: a, reason: b, disposition: decline }\n")
    R.main(["--change", first, "--rollup", led, "--append"])
    capsys.readouterr()
    second = _write(tmp_path / "b.yaml",
                    "change_id: GH-B\nskips:\n  - { step: rollout, crit: standard, actor: a, reason: b, disposition: decline }\n")
    R.main(["--change", second, "--rollup", led, "--append"])
    assert "qa_verify" in capsys.readouterr().out, "GH-A's project-wide skip must reach GH-B"


# ---------------------------------------------------------------- project migration

import migrate_project as M  # noqa: E402


def test_merge_permissions_never_clobbers_what_a_team_added():
    before = {"statusLine": "x", "hooks": {"Stop": []},
              "permissions": {"allow": ["Bash(theirtool *)"], "deny": ["Read(./private/**)"]}}
    after, added = M.merge_permissions(before)
    assert "Bash(theirtool *)" in after["permissions"]["allow"]
    assert "Read(./private/**)" in after["permissions"]["deny"]
    assert after["statusLine"] == "x" and after["hooks"] == {"Stop": []}
    assert added["allow"] and added["deny"]


def test_merge_permissions_is_idempotent():
    merged, _ = M.merge_permissions({})
    again, added = M.merge_permissions(merged)
    assert added == {"allow": [], "deny": []}
    assert again["permissions"] == merged["permissions"]


def test_merge_permissions_adds_a_missing_block():
    for ok in ({}, {"permissions": None}, {"permissions": {}}):
        merged, _ = M.merge_permissions(ok)
        assert set(M.DENY) <= set(merged["permissions"]["deny"])


def test_merge_permissions_refuses_shapes_it_cannot_merge():
    # Valid JSON, wrong shape. Silently replacing it would delete a team's configuration in order
    # to add ours — worse than the invalid-JSON path, which already refuses.
    import pytest
    for junk in (["not", "an", "object"], {"permissions": ["a"]}, {"permissions": {"allow": {"a": 1}}}):
        with pytest.raises(M.Unmergeable):
            M.merge_permissions(junk)


def test_audit_tolerates_an_unhashable_status():
    # `x in set()` raises on an unhashable value; an advisory audit must not traceback mid-migration.
    assert M.audit_change_file({"workflow": {"steps": [{"key": "roi", "status": ["done"]}]}}) == []


def test_merge_permissions_never_adds_an_interpreter():
    # The rule the whole allowlist design rests on: redirection rides along on a match, so an
    # allowlisted interpreter is an unprompted arbitrary write.
    banned = ("python", "python3", "node", "bun", "npx", "pip", "bash", "sh", "deno", "ruby")
    for entry in M.ALLOW:
        cmd = entry[len("Bash("):].split()[0]
        assert cmd not in banned, f"{entry} allowlists an interpreter"


def test_audit_flags_a_change_lightened_without_the_flag():
    change = {"workflow": {"steps": [{"key": "roi", "status": "skipped"}]},
              "skips": [{"step": "roi"}]}
    reasons = M.audit_change_file(change)
    assert len(reasons) == 2 and any("roi" in r for r in reasons)


def test_audit_is_quiet_for_a_declared_or_untouched_change():
    assert M.audit_change_file({"first_pass": True, "skips": [{"step": "roi"}]}) == []
    assert M.audit_change_file({"workflow": {"steps": [{"key": "roi", "status": "open"}]}}) == []
    assert M.audit_change_file("not a mapping") == []


def test_append_without_an_area_records_project_wide(tmp_path, capsys):
    # Most routes (onboarding, migration, docs) never declare a manifest domain, and CR-10 makes the
    # ledger durable for the PROJECT. Refusing there left their skips only in a change file the next
    # intake overwrites. No area now means project-wide, which overlaps everything, rather than an
    # empty area that could match nothing and was invisible forever.
    import yaml
    chg = _write(tmp_path / "c.yaml",
                 "change_id: GH-1\nskips:\n  - { step: qa_verify, crit: floor, actor: a, reason: b, disposition: decline }\n")
    led = tmp_path / "l.yaml"
    assert R.main(["--change", chg, "--rollup", str(led), "--append"]) == 0
    assert "project-wide" in capsys.readouterr().out
    entry = yaml.safe_load(led.read_text())["entries"][0]
    assert entry["project_wide"] is True


def test_a_project_wide_entry_resurfaces_at_any_later_change(tmp_path, capsys):
    chg = _write(tmp_path / "c.yaml",
                 "change_id: GH-1\nskips:\n  - { step: qa_verify, crit: floor, actor: a, reason: b, disposition: decline }\n")
    led = str(tmp_path / "l.yaml")
    R.main(["--change", chg, "--rollup", led, "--append"])
    capsys.readouterr()
    later = _write(tmp_path / "c2.yaml",
                   "change_id: GH-2\nmanifest:\n  domain: anything\nallowed_paths:\n  - src/x/\n")
    R.main(["--change", later, "--rollup", led])
    assert "qa_verify" in capsys.readouterr().out


def test_a_later_scoped_run_narrows_its_own_project_wide_entry(tmp_path, capsys):
    # The development route appends at intake (no scope) and again at its impact step (scope known).
    # The second run must persist the narrowing even though it adds nothing.
    import yaml
    skips = "skips:\n  - { step: qa_verify, crit: floor, actor: a, reason: b, disposition: decline }\n"
    led = str(tmp_path / "l.yaml")
    R.main(["--change", _write(tmp_path / "c.yaml", "change_id: GH-1\n" + skips),
            "--rollup", led, "--append"])
    R.main(["--change", _write(tmp_path / "c2.yaml",
                               "change_id: GH-1\nmanifest:\n  domain: payments\n" + skips),
            "--rollup", led, "--append"])
    entries = yaml.safe_load(open(led, encoding="utf-8"))["entries"]
    assert len(entries) == 1
    assert entries[0].get("project_wide") is None and entries[0]["domains"] == ["payments"]


def test_missing_change_id_shows_everything_and_says_why(tmp_path, capsys):
    # We cannot tell our own entries from anyone else's without an id. Suppressing entries we cannot
    # identify would hide real risk to avoid a nuisance, so show them and explain.
    led = _write(tmp_path / "l.yaml", yaml_dump_entries())
    chg = _write(tmp_path / "c.yaml",
                 "manifest:\n  domain: billing\nallowed_paths:\n  - src/billing/\n")
    R.main(["--change", chg, "--rollup", led])
    out = capsys.readouterr()
    assert "qa_verify" in out.out
    assert "change_id missing" in out.err


def yaml_dump_entries():
    import yaml
    return yaml.safe_dump({"entries": [
        {"step": "qa_verify", "crit": "floor", "actor": "a@b", "reason": "x",
         "disposition": "decline", "resolved": False, "change_id": "GH-OTHER",
         "domains": ["billing"], "paths": ["src/billing/"]}]}, sort_keys=False)


def test_to_rollup_dedupes_within_a_single_change_file(tmp_path):
    # A change file can legitimately carry two records for one step (migrated or hand-edited). The
    # dedupe set must see what this loop just appended, not only what was already in the roll-up.
    import yaml
    change = yaml.safe_load(_CHANGE)
    change["skips"].append(dict(change["skips"][0]))          # exact duplicate (change_id, step)
    rollup, added, _ = R.to_rollup(change, {})
    assert added == 1 and len(rollup["entries"]) == 1


def test_a_missing_change_id_never_narrows_someone_elses_entry(tmp_path):
    # Without an id every record collapses onto ("", step), so narrowing would rewrite a DIFFERENT
    # change's area with this change's scope.
    import yaml
    skips = "skips:\n  - { step: qa_verify, crit: floor, actor: a, reason: b, disposition: decline }\n"
    led = str(tmp_path / "l.yaml")
    R.main(["--change", _write(tmp_path / "a.yaml", skips), "--rollup", led, "--append"])
    R.main(["--change", _write(tmp_path / "b.yaml", "manifest:\n  domain: other\n" + skips),
            "--rollup", led, "--append"])
    e = yaml.safe_load(open(led, encoding="utf-8"))["entries"][0]
    assert e.get("project_wide") is True and e.get("domains") in (None, [])


def test_digest_keeps_distinct_project_wide_records_apart():
    # All project-wide entries share an empty area, so keying on (step, area) alone collapsed every
    # change that lightened the same step into one — and counted the rest as zero.
    entries = [{"step": "qa_verify", "crit": "floor", "change_id": c, "project_wide": True,
                "actor": "a", "reason": c} for c in ("GH-1", "GH-2", "GH-3")]
    shown, remaining = R.digest(entries, cap=2)
    assert len(shown) == 2 and remaining == 1


# ── path overlap by segment, not by raw string ────────────────────────────────

def test_a_sibling_sharing_a_character_prefix_does_not_overlap():
    # `src/pay`.startswith-matched `src/payments`, so an unrelated change got nagged.
    assert not R._paths_overlap({"src/pay"}, {"src/payments"})


def test_a_declared_glob_overlaps_the_files_it_covers():
    # The literal `**` broke the comparison, so the change that SHOULD have been reminded was not.
    assert R._paths_overlap({"src/payments/**"}, {"src/payments/api.py"})


def test_directory_and_file_relationships_overlap_either_way():
    assert R._paths_overlap({"src/payments"}, {"src/payments/api.py"})
    assert R._paths_overlap({"src/payments/api.py"}, {"src/payments"})
    assert R._paths_overlap({"src/"}, {"src/anything/deep.py"})
    assert not R._paths_overlap({"src/billing"}, {"src/shipping"})


def test_historical_duplicate_entries_are_normalised_then_narrowed():
    # The earlier dedupe bug could write two entries for one (change_id, step). Preventing new ones
    # does not repair the old: `by_key` keeps only the last, so a later narrowing fixed that one and
    # left the other project-wide forever.
    dup = {"entries": [
        {"change_id": "GH-DUP", "step": "qa_verify", "crit": "floor", "project_wide": True, "resolved": False},
        {"change_id": "GH-DUP", "step": "qa_verify", "crit": "floor", "project_wide": True, "resolved": False}]}
    change = {"change_id": "GH-DUP", "manifest": {"domain": "billing"},
              "skips": [{"step": "qa_verify", "crit": "floor", "actor": "a", "reason": "b",
                         "disposition": "decline"}]}
    rollup, added, changed = R.to_rollup(change, dup)
    assert len(rollup["entries"]) == 1 and added == 0 and changed >= 1
    assert not rollup["entries"][0].get("project_wide")
    assert rollup["entries"][0]["domains"] == ["billing"]


def test_normalisation_prefers_the_scoped_copy_of_a_duplicate():
    dup = {"entries": [
        {"change_id": "GH-D", "step": "roi", "project_wide": True},
        {"change_id": "GH-D", "step": "roi", "domains": ["billing"]}]}
    rollup, _, _ = R.to_rollup({"change_id": "GH-D", "skips": []}, dup)
    assert len(rollup["entries"]) == 1 and rollup["entries"][0].get("domains") == ["billing"]


def test_not_applicable_is_refused_on_a_load_bearing_step():
    """Defence in depth (#97). check_skips blocks this with RULE_OVER_FLOOR, but the generator
    refuses it earlier via is_allowed, so a bad choices file never reaches the ledger at all.
    A mutation that let it through was caught by nothing until this test existed."""
    assert D.is_allowed(CATALOG["roi"], 2, "not_applicable") is True
    assert D.is_allowed(CATALOG["deploy"], 2, "not_applicable") is False
    # #102: a conditional step is the one floor step the rules may record not_applicable — when its
    # activator did not fire it was never in the plan. Must agree with check_skips' exemption.
    assert CATALOG["pentest"].get("cond") and D.is_allowed(CATALOG["pentest"], 3, "not_applicable") is True
    assert D.is_allowed(CATALOG["pentest"], 3, "decline") is True, "active pentest may be declined (then FLOOR_NO_ACK applies)"
    assert D.is_allowed(CATALOG["red"], 1, "not_applicable") is False, "no_omit too"
    assert D.is_allowed(CATALOG["packet"], 3, "not_applicable") is False, "floor at tier 3"
    assert D.is_allowed(CATALOG["packet"], 2, "not_applicable") is True, "standard at tier 2"


def test_not_applicable_is_never_a_menu_option():
    """It is the rules speaking, not a choice a person is offered. If it appeared on the menu a
    human could pick it, and the ledger would record a rule that never fired."""
    for key in ("roi", "docs", "conventions"):
        assert "not_applicable" not in D.allowed_dispositions(CATALOG[key], 2)


# ---------------------------------------------------------------- migrate_project: the change-file audit (#103)
#
# The audit used to coerce an unreadable change file to `{}` and then certify it "consistent" with
# exit 0. On a python3 without PyYAML that was every dev-update run. Four states, kept apart:
# absent and empty are clean; unreadable and not-a-mapping mean the audit did not run and must fail.

def _migrate_root(tmp_path, change_text=None):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    if change_text is not None:
        (tmp_path / ".hitl").mkdir()
        (tmp_path / ".hitl" / "current-change.yaml").write_text(change_text, encoding="utf-8")
    return str(tmp_path)


def test_migrate_absent_change_file_is_clean(tmp_path, capsys):
    rc = M.main(["--root", _migrate_root(tmp_path)])
    assert rc == 0
    assert "change file" not in capsys.readouterr().out.lower().replace("active change file is", "")


def test_migrate_empty_change_file_is_clean_and_says_empty(tmp_path, capsys):
    rc = M.main(["--root", _migrate_root(tmp_path, "")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "empty" in out and "consistent" not in out


def test_migrate_lightened_change_is_advisory_exit_0(tmp_path, capsys):
    txt = "change_id: GH-1\nskips:\n  - {step: red}\nworkflow:\n  steps:\n    - {key: red, status: skipped}\n"
    rc = M.main(["--root", _migrate_root(tmp_path, txt)])
    out = capsys.readouterr().out
    assert rc == 0, "the lightened report is advisory — check_skips.py is the gate"
    assert "1 skip record(s)" in out and "lightened step(s): red" in out
    assert "consistent" not in out


def test_migrate_first_pass_declared_is_consistent(tmp_path, capsys):
    txt = "change_id: GH-1\nfirst_pass: true\nskips:\n  - {step: red}\n"
    rc = M.main(["--root", _migrate_root(tmp_path, txt)])
    assert rc == 0 and "consistent" in capsys.readouterr().out


def test_migrate_invalid_yaml_fails_closed(tmp_path, capsys):
    rc = M.main(["--root", _migrate_root(tmp_path, "change_id: [unclosed\n")])
    out = capsys.readouterr().out
    assert rc == 1
    assert "could not read" in out and "did NOT run" in out
    assert "consistent" not in out, "an unreadable file must never be certified"


def test_migrate_non_mapping_fails_closed(tmp_path, capsys):
    for txt in ("- a\n- b\n", "just a scalar\n", "42\n"):
        rc = M.main(["--root", _migrate_root(tmp_path, txt)])
        out = capsys.readouterr().out
        assert rc == 1, txt
        assert "not a mapping" in out and "consistent" not in out, txt
        (tmp_path / ".hitl" / "current-change.yaml").unlink()
        (tmp_path / ".hitl").rmdir()
        (tmp_path / ".claude" / "settings.json").unlink()
        (tmp_path / ".claude").rmdir()


def test_migrate_without_pyyaml_reports_and_fails(tmp_path, capsys, monkeypatch):
    # The reported symptom: Homebrew python3, no PyYAML. `sys.modules[name] = None` makes
    # `import yaml` raise ImportError, which is exactly what the operator's interpreter did.
    txt = "change_id: GH-1\nskips:\n  - {step: red}\n"
    root = _migrate_root(tmp_path, txt)
    monkeypatch.setitem(sys.modules, "yaml", None)
    rc = M.main(["--root", root])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no PyYAML" in out and "did NOT run" in out
    assert "consistent" not in out, "two real findings were silently certified clean before this fix"


# ---------------------------------------------------------------- migrate_project: validator sync (#104)
#
# dev-update used to `cp` the plugin's validators over the repo's copies. A repo that had fixed a
# validator ahead of upstream lost the fix on the next update — five times downstream, including runs
# with no version change. The sync is now the co-owned protocol Step 4.7 already applies to .semgrep/.

def _plugin(tmp_path):
    pr = tmp_path / "plugin"
    (pr / "shared" / "ci" / "first-pass").mkdir(parents=True)
    (pr / "shared" / "ci" / "first-pass" / "check_skips.py").write_text("SHIPPED v2\n")
    (pr / "shared" / "ci" / "first-pass" / "permissions.py").write_text("SHIPPED perms\n")
    (pr / "shared" / "ci" / "first-pass" / "test_check_skips.py").write_text("a test — must never ship\n")
    (pr / "shared" / "workflows.yaml").write_text("workflows: shipped\n")
    (pr / "shared" / "ci-workflows").mkdir()
    (pr / "shared" / "ci-workflows" / "first-pass-check.yml").write_text("on: push  # shipped\n")
    (pr / "shared" / "ci" / "manifest-agentic").mkdir()
    (pr / "shared" / "ci" / "manifest-agentic" / "check_manifest_agentic.py").write_text("SHIPPED agentic\n")
    (pr / "shared" / "ci" / "manifest-agentic" / "manifest-waivers.yaml").write_text("waivers: []  # starter\n")
    (pr / "shared" / "ci" / "manifest-drift").mkdir()
    (pr / "shared" / "ci" / "manifest-drift" / "check_manifest_drift.py").write_text("SHIPPED drift\n")
    return pr


def _project(tmp_path):
    root = tmp_path / "repo"
    (root / "ci" / "first-pass").mkdir(parents=True)
    return root


def test_sync_installs_absent_keeps_modified_and_ignores_repo_files(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    fp = root / "ci" / "first-pass"
    (fp / "check_skips.py").write_text("SHIPPED v2\nplus the GH-488 fix the repo made\n")   # modified
    (fp / "my_own_tool.py").write_text("ours\n")                                               # repo-added
    r = M.sync_validators(str(root), str(pr), apply=True)
    out = capsys.readouterr().out
    assert "ci/first-pass/permissions.py" in r["installed"]
    assert (fp / "permissions.py").read_text() == "SHIPPED perms\n"
    assert r["modified"] == ["ci/first-pass/check_skips.py"]
    assert "GH-488 fix the repo made" in (fp / "check_skips.py").read_text(), "the repo's fix must survive"
    assert "KEPT yours" in out and "+plus the GH-488 fix" not in out and "-plus the GH-488 fix" in out
    assert "ASK, per file" in out and "--overwrite ci/first-pass/check_skips.py" in out
    assert (fp / "my_own_tool.py").read_text() == "ours\n" and "my_own_tool" not in out


def test_sync_dry_run_writes_nothing(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    (root / "ci" / "first-pass" / "check_skips.py").write_text("modified\n")
    r = M.sync_validators(str(root), str(pr), apply=False)
    out = capsys.readouterr().out
    assert r["installed"] and not (root / "ci" / "first-pass" / "permissions.py").exists()
    assert "would install" in out and "dry run" in out
    assert (root / "ci" / "first-pass" / "check_skips.py").read_text() == "modified\n"


def test_sync_identical_files_are_silent(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    M.sync_validators(str(root), str(pr), apply=True)
    capsys.readouterr()
    r = M.sync_validators(str(root), str(pr), apply=True)
    out = capsys.readouterr().out
    assert not r["installed"] and not r["modified"]
    assert "already current" in out and "check_skips" not in out


def test_sync_overwrites_only_the_file_named(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    fp = root / "ci" / "first-pass"
    (fp / "check_skips.py").write_text("modified A\n")
    (fp / "permissions.py").write_text("modified B\n")
    r = M.sync_validators(str(root), str(pr), apply=True, overwrite=["ci/first-pass/check_skips.py"])
    assert r["overwritten"] == ["ci/first-pass/check_skips.py"]
    assert (fp / "check_skips.py").read_text() == "SHIPPED v2\n"
    assert (fp / "permissions.py").read_text() == "modified B\n", "a yes to one file is not a yes to another"
    assert r["modified"] == ["ci/first-pass/permissions.py"]


def test_sync_honours_the_optout_file(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    (root / "ci" / "first-pass" / ".hitl-optout").write_text("# removed on purpose\npermissions.py\n")
    r = M.sync_validators(str(root), str(pr), apply=True)
    out = capsys.readouterr().out
    assert not (root / "ci" / "first-pass" / "permissions.py").exists()
    assert r["opted_out"] == ["ci/first-pass/permissions.py"] and "opted out" in out


def test_sync_never_installs_tests(tmp_path):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    M.sync_validators(str(root), str(pr), apply=True)
    assert not (root / "ci" / "first-pass" / "test_check_skips.py").exists()


def test_sync_install_only_files_are_the_repos_after_install(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    M.sync_validators(str(root), str(pr), apply=True)
    wf = root / ".github" / "workflows" / "first-pass-check.yml"
    wv = root / "ci" / "manifest-agentic" / "manifest-waivers.yaml"
    assert wf.read_text().startswith("on: push") and wv.exists()
    wf.write_text("on: pull_request  # customised\n")
    wv.write_text("waivers:\n  - id: W-1\n")
    capsys.readouterr()
    r = M.sync_validators(str(root), str(pr), apply=True)
    out = capsys.readouterr().out
    assert wf.read_text().startswith("on: pull_request") and "W-1" in wv.read_text()
    assert not r["modified"] and "first-pass-check" not in out and "waivers" not in out


def test_sync_if_present_set_is_skipped_when_the_repo_lacks_it(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    r = M.sync_validators(str(root), str(pr), apply=True)
    assert not (root / "ci" / "manifest-drift").exists()
    assert any("manifest-drift" in x for x in r["skipped_sets"])
    (root / "ci" / "manifest-drift").mkdir()
    capsys.readouterr()
    r = M.sync_validators(str(root), str(pr), apply=True)
    assert "ci/manifest-drift/check_manifest_drift.py" in r["installed"]


def test_sync_refuses_to_run_in_the_platform_repo(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    (root / "ai" / "claude" / "start-change").mkdir(parents=True)
    (root / "ai" / "claude" / "start-change" / "SKILL.md").write_text("x")
    r = M.sync_validators(str(root), str(pr), apply=True)
    assert not r["installed"] and "platform repo" in capsys.readouterr().out


def test_sync_cli_is_a_separate_mode(tmp_path, capsys):
    pr, root = _plugin(tmp_path), _project(tmp_path)
    rc = M.main(["--root", str(root), "--sync-validators", str(pr), "--apply"])
    out = capsys.readouterr().out
    assert rc == 0 and "installed ci/first-pass/check_skips.py" in out
    assert "permissions already current" not in out, "sync mode must not run the settings migration"


# ---------------------------------------------------------------- migrate_project: statusLine shape (#96)

def _settings_root(tmp_path, statusline):
    root = tmp_path / "proj"
    (root / ".claude").mkdir(parents=True)
    doc = {"permissions": {"allow": [], "deny": []}}
    if statusline is not None:
        doc["statusLine"] = statusline
    (root / ".claude" / "settings.json").write_text(json.dumps(doc, indent=2) + "\n")
    return root


def test_a_string_statusline_is_wrapped_into_an_object_on_apply(tmp_path, capsys):
    """The v2.6.3 re-wire wrote a bare string; the grep check saw the script name inside it and
    passed. The migrator now wraps it, and only it."""
    root = _settings_root(tmp_path, 'bash "$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh"')
    rc = M.main(["--root", str(root), "--apply"])
    out = capsys.readouterr().out
    assert rc == 0 and "string form wrapped" in out and "written to" in out
    doc = json.loads((root / ".claude" / "settings.json").read_text())
    assert doc["statusLine"] == {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh"'}
    assert "permissions" in doc, "the rest of the file survives"


def test_a_string_statusline_dry_run_reports_and_writes_nothing(tmp_path, capsys):
    root = _settings_root(tmp_path, 'bash x.sh')
    before = (root / ".claude" / "settings.json").read_text()
    M.main(["--root", str(root)])
    out = capsys.readouterr().out
    assert "string form wrapped" in out and "not hooks/statusline-hitl.sh" in out and "dry run" in out
    assert (root / ".claude" / "settings.json").read_text() == before


def test_a_correct_statusline_is_left_alone_and_reported_current(tmp_path, capsys):
    good = {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh"'}
    root = _settings_root(tmp_path, good)
    M.main(["--root", str(root), "--apply"])
    assert "= statusLine current" in capsys.readouterr().out
    assert json.loads((root / ".claude" / "settings.json").read_text())["statusLine"] == good


def test_a_missing_or_stale_statusline_is_reported_not_rewritten(tmp_path, capsys):
    root = _settings_root(tmp_path, None)
    M.main(["--root", str(root), "--apply"])
    assert "statusLine is missing" in capsys.readouterr().out
    stale = {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.hitl/statusline.sh"'}
    root2 = _settings_root(tmp_path / "b", stale)
    M.main(["--root", str(root2), "--apply"])
    out = capsys.readouterr().out
    assert "statusLine points at" in out and "legacy" in out
    assert json.loads((root2 / ".claude" / "settings.json").read_text())["statusLine"] == stale
