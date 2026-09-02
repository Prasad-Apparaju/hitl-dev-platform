#!/usr/bin/env python3
"""Conformance for the closing retrospective (#98 / design: progress-and-retro).

The load-bearing property: the retrospective authors NO workflow-catalog rule field (NO-EDIT).
Mirrors ci/agentic-advisor/test_records.py, which enforces the same boundary for the Advisor.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "retro"))
import retro_records as R

CHANGE = {
    "change_id": "GH-500-add-env-var",
    "tier": 2,
    "requirement": "Add the STRIPE_WEBHOOK_SECRET env var to the payments service.",
    "source_artifacts": {"issue": "https://example.invalid/issues/500"},
    "impact_record": ".hitl/impact/GH-500-add-env-var.yaml",
    "workflow": {
        "id": "development",
        "steps": [
            {"n": 1, "key": "issue", "label": "Issue", "status": "done"},
            {"n": 12, "key": "docs", "label": "Docs", "status": "skipped"},
            {"n": 21, "key": "qa_verify", "label": "QAVfy", "status": "done"},
            {"n": 23, "key": "rollout", "label": "Rollout", "status": "skipped"},
            {"n": 29, "key": "retro", "label": "Retro", "status": "current"},
        ],
    },
    "skips": [
        {"step": "docs", "disposition": "decline", "reason": "no user-facing surface",
         "actor": "a.dev"},
        {"step": "rollout", "disposition": "decline", "reason": "config only, no rollout",
         "ack_by": "a.lead"},
    ],
    "acceptance_criteria": [
        {"id": "AC-1", "criterion": "the var is read at boot", "verified": True},
        {"id": "AC-2", "criterion": "a missing var fails closed", "verified": False},
    ],
}

IMPACT = {
    "rule_outcomes": [
        {"step": "docs", "applies": True, "needed_now": True,
         "because": "one area depends on this", "judged": False},
        {"step": "rollout", "applies": False, "needed_now": False,
         "because": "no interface files in the change", "judged": False},
        {"step": "qa_verify", "applies": True, "needed_now": True,
         "because": "acceptance criteria present", "judged": True},
    ]
}


# ── The boundary ──────────────────────────────────────────────────────────────────────────
def test_retro_authors_no_catalog_field():
    retro = R.build_retro(CHANGE, IMPACT)
    assert R.retro_authors_no_catalog_field(retro) == set(), \
        "the retrospective must contain no workflow-catalog rule field"


def test_boundary_catches_an_authored_rule_field():
    bad = copy.deepcopy(R.build_retro(CHANGE, IMPACT))
    bad["sizing"][0]["needed_now"] = False          # the raw rule key, not the projection
    assert "needed_now" in R.retro_authors_no_catalog_field(bad)

    worse = copy.deepcopy(R.build_retro(CHANGE, IMPACT))
    worse["recommended_catalog"] = {"docs": {"crit": "ceremony"}}
    assert "crit" in R.retro_authors_no_catalog_field(worse)


def test_boundary_walks_nested_lists_and_dicts():
    bad = {"a": [{"b": [{"engages": "always"}]}]}
    assert "engages" in R.retro_authors_no_catalog_field(bad)


def test_catalog_fields_are_derived_from_the_real_catalog():
    """A new rule field in the catalog must widen the ban without editing this module."""
    for field in ("crit", "engages", "needed_now", "forgo_cost", "command"):
        assert field in R.CATALOG_FIELDS, f"{field} must be a guarded rule field"


def test_catalog_resolves_in_the_shipped_plugin_layout(tmp_path):
    """The built plugin flattens the catalog to shared/workflows.yaml, one level above
    shared/tools/retro/. Resolving only the source path degrades the ban set silently."""
    plugin = tmp_path / "shared"
    (plugin / "tools" / "retro").mkdir(parents=True)
    (plugin / "workflows.yaml").write_text(
        "step_costs:\n  retro:\n    engages: always\n    forgo_cost: high\n"
        "workflows:\n  development:\n    steps:\n"
        "      - { n: 1, key: a, label: A, phase: P, crit: floor, command: x, no_omit: true }\n"
    )
    here = str(plugin / "tools" / "retro")
    cands = (os.path.normpath(os.path.join(here, "..", "..", "ai", "shared", "workflows.yaml")),
             os.path.normpath(os.path.join(here, "..", "..", "workflows.yaml")))
    resolved = R._resolve_catalog(cands)
    assert resolved is not None, "the plugin-layout catalog must resolve"
    names = R._catalog_field_names(resolved)
    for field in ("engages", "forgo_cost", "crit", "command", "no_omit"):
        assert field in names, f"{field} must be derived from the shipped catalog"


def test_catalog_resolution_survives_no_catalog_at_all():
    names = R._catalog_field_names("/nonexistent/workflows.yaml")
    assert R._STATIC_CATALOG_FIELDS <= names, "must fall back to the static floor, not empty"


def test_observations_use_the_projected_channel_only():
    for obs in R.sizing_observations(CHANGE, IMPACT):
        assert set(obs) <= set(R.OBSERVATION_FIELDS), f"unprojected key in {obs}"


# ── What it reads ─────────────────────────────────────────────────────────────────────────
def test_open_items_carry_skips_with_owner_and_reason():
    items = {i["step"]: i for i in R.open_items(CHANGE) if i["step"]}
    assert items["docs"]["disposition"] == "decline"
    assert items["docs"]["owner"] == "a.dev"
    assert items["rollout"]["owner"] == "a.lead"


def test_open_items_include_unverified_criteria():
    labels = [i["label"] for i in R.open_items(CHANGE) if i["state"] == "unverified"]
    assert "AC-2" in labels and "AC-1" not in labels


def test_sizing_flags_a_dropped_step_the_rule_wanted():
    by_step = {o["step"]: o for o in R.sizing_observations(CHANGE, IMPACT)}
    assert "the rule said it was needed now" in by_step["docs"]["observed"]
    assert by_step["docs"]["concluded_needed_now"] is True
    assert by_step["rollout"]["observed"] == "dropped from the plan"


def test_sizing_marks_a_judged_outcome():
    by_step = {o["step"]: o for o in R.sizing_observations(CHANGE, IMPACT)}
    assert by_step["qa_verify"]["judged"] is True


def test_missing_rule_outcomes_is_empty_not_an_error():
    assert R.sizing_observations(CHANGE, {}) == []
    assert R.sizing_observations(CHANGE, None) == []


# ── The voice ─────────────────────────────────────────────────────────────────────────────
def test_blame_words_are_redacted_from_echoed_reasons():
    change = copy.deepcopy(CHANGE)
    change["skips"][0]["reason"] = "the team failed to write docs, sloppy work"
    text = R.render(R.build_retro(change, IMPACT))
    assert R.blame_words_in(text) == set(), f"blame vocabulary survived into {text!r}"


def test_blame_lint_is_the_resurfacing_one():
    assert R.blame_words_in("this failed badly")


# ── The document ──────────────────────────────────────────────────────────────────────────
def test_render_has_the_three_parts():
    text = R.render(R.build_retro(CHANGE, IMPACT))
    for heading in ("## What happened", "## What is still open",
                    "## How the sizing turned out"):
        assert heading in text, f"missing {heading}"


def test_render_states_the_boundary_rather_than_proposing_an_edit():
    text = R.render(R.build_retro(CHANGE, IMPACT))
    assert "Changing a rule is a change" in text


def test_render_tolerates_an_empty_change():
    assert R.render(R.build_retro({}, {}))


if __name__ == "__main__":                                   # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
