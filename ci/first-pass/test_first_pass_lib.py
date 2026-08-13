#!/usr/bin/env python3
"""Conformance for the First Pass library (dispositions, starters, resurface, permissions).
FR-29 test-plan §4-§9. Adversarial edges included."""
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
    # impact becomes floor at tier 3
    assert D.allowed_dispositions(CATALOG["impact"], 3) == ["keep", "risk_accept"]
    assert D.allowed_dispositions(CATALOG["impact"], 2) != ["keep", "risk_accept"]


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
