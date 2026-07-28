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
