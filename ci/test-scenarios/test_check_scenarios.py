#!/usr/bin/env python3
"""Conformance for the scenarios validator (FR-36, test plan section 1). Every NEG case differs
from a passing fixture by the one defect it names; the mutation test at the end proves that
removing the defect removes the code, so no case passes for an unrelated reason."""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_scenarios.py")
_spec = importlib.util.spec_from_file_location("check_scenarios", SCRIPT)
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

SCEN_REL = "docs/03-engineering/testing/scenarios/GH-123.md"
E2E = "tests/e2e/checkout.spec.ts"
DASH = chr(0x2014)

CONTEXT = ("Shoppers can enter a discount code at checkout and see the new total before paying. "
           "It matters because support gets a ticket a day about codes that did nothing. "
           "Acceptance criteria are FR-12 in the PRD.")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def scenario(num, title="A blank code leaves the total unchanged", change="GH-123", test=None,
             removed=False, **over):
    sid = "SC-%s-%02d" % (change, num)
    if removed:
        return "### %s: removed\n- Removed by: qa, 2026-10-06, duplicate of SC-GH-123-01\n" % sid
    fields = {"Kind": "acceptance", "Priority": "strongly-recommended", "Serves": "FR-12 AC-2",
              "Added by": "qa", "Given": "a cart with two items totalling 40.00",
              "When": "the shopper submits an empty code",
              "Then": "the total still shows 40.00 and the field says a code is needed",
              "Test": test or E2E}
    fields.update(over)
    body = "".join("- %s: %s\n" % (k, v) for k, v in fields.items() if v is not None)
    return "### %s: %s\n%s" % (sid, title, body)


def doc(scenarios, context=CONTEXT, review="PM: done", heading_context=True, extra=""):
    parts = ["# Test scenarios: GH-123 Discount codes at checkout", "", "| | |", "|---|---|",
             "| Change | GH-123 |", "| Serves | FR-12 |", "| Owner | QA |"]
    if review is not None:
        parts.append("| Review | %s |" % review)
    parts += ["| Written | by HITL at the test plan step, 2026-10-04 |", ""]
    if heading_context:
        parts += ["## What this change does", "", context, ""]
    parts += ["## Scenarios", ""] + list(scenarios) + [extra]
    return "\n".join(parts)


def e2e(*ids, extra_unit=None):
    units = ["test('scenario %s', async ({ page }) => {\n  await page.goto('/');\n});\n" % i for i in ids]
    if extra_unit:
        units.append(extra_unit)
    return "import { test } from '@playwright/test';\n\n" + "\n".join(units)


UNCITED_UNIT = "test('something else', async ({ page }) => {\n  await page.goto('/x');\n});\n"
RECORD_DONE = {"status": "done", "by": "Dana (PM)", "ts": "2026-10-05T14:02:00Z"}
RECORD_SKIPPED = {"status": "skipped", "actor": "Sam (QA)", "pm": "Dana", "reason": "PM on leave",
                  "disposition": "defer", "ts": "2026-10-07T09:10:00Z"}


def record_yaml(change_id="GH-123", scenarios_file=SCEN_REL, review=RECORD_DONE, files=(E2E,)):
    lines = ["change_id: %s" % change_id, "tier: 2", "tests:"]
    if scenarios_file is not None:
        lines.append("  scenarios_file: %s" % scenarios_file)
    if review is not None:
        lines.append("  scenario_review:")
        for k, v in review.items():
            lines.append("    %s: %s" % (k, json.dumps(v) if isinstance(v, str) else v))
    if files is not None:
        lines.append("  files:")
        lines += ["    - %s" % f for f in files]
    return "\n".join(lines) + "\n"


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def build(root, record=None, scenarios=None, tests=None):
    """Write a repo at `root`. Defaults are the passing POS-1 shape; pass None for a part to omit it."""
    if record != "":
        write(root, ".hitl/current-change.yaml", record if record is not None else record_yaml())
    if scenarios != "":
        write(root, SCEN_REL, scenarios if scenarios is not None else doc([scenario(1), scenario(2)]))
    tests = {E2E: e2e("SC-GH-123-01", "SC-GH-123-02")} if tests is None else tests
    for rel, text in tests.items():
        write(root, rel, text)
    return root


def run(root, stage="review", **kw):
    findings, summary = C.safe_analyze(".hitl/current-change.yaml", stage=stage, root=root, **kw)
    return findings, C.exit_code(findings, kw.pop("strict", False)), summary


def codes(findings):
    return [f["code"] for f in findings]


def blockers(findings, code):
    hits = [f for f in findings if f["code"] == code]
    assert hits, "expected %s, got %s" % (code, sorted(set(codes(findings))))
    assert all(f["waivable"] is False for f in hits), "%s must block" % code
    return hits


def warnings(findings, code):
    hits = [f for f in findings if f["code"] == code]
    assert hits, "expected %s, got %s" % (code, sorted(set(codes(findings))))
    assert all(f["waivable"] is True for f in hits), "%s must warn" % code
    return hits


# ---------------------------------------------------------------------------
# POS
# ---------------------------------------------------------------------------

def test_pos_1_two_cited_review_done(tmp_path):
    build(str(tmp_path))
    findings, code, summary = run(str(tmp_path))
    assert findings == [] and code == 0
    assert summary == {"scenarios": 2, "cited": 2, "deferred": 0, "review": "done"}


def test_pos_2_deferred_with_owner_and_reason(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, test='deferred (qa, "needs the clock fixture")')]),
          tests={E2E: e2e("SC-GH-123-01")})
    findings, code, summary = run(str(tmp_path))
    assert code == 0 and findings == []
    assert summary["deferred"] == 1 and summary["cited"] == 1


def test_pos_3_removed_between_live(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, removed=True), scenario(3)]),
          tests={E2E: e2e("SC-GH-123-01", "SC-GH-123-03")})
    findings, code, summary = run(str(tmp_path))
    assert code == 0 and findings == []
    assert summary["scenarios"] == 2


def test_pos_4_underscore_citation_in_python_name(tmp_path):
    py = "tests/integration/test_checkout.py"
    build(str(tmp_path), record=record_yaml(files=(py,)), scenarios=doc([scenario(1, test=py)]),
          tests={py: "def test_blank_code_leaves_total_SC_GH_123_01():\n    assert True\n"})
    findings, code, summary = run(str(tmp_path))
    assert code == 0 and "SCENARIO_UNCITED" not in codes(findings)
    assert summary["cited"] == 1


def test_pos_5_unit_test_without_id_is_exempt(tmp_path):
    unit = "tests/unit/test_cart.py"
    build(str(tmp_path), record=record_yaml(files=(E2E, unit)),
          tests={E2E: e2e("SC-GH-123-01", "SC-GH-123-02"), unit: "def test_total():\n    assert 1 + 1 == 2\n"})
    findings, code, _ = run(str(tmp_path))
    assert code == 0 and "TEST_UNCITED" not in codes(findings)


def test_pos_6_review_pending_at_review_stage_warns(tmp_path):
    build(str(tmp_path), record=record_yaml(review={"status": "pending"}),
          scenarios=doc([scenario(1), scenario(2)], review="PM: pending"))
    findings, code, _ = run(str(tmp_path), stage="review")
    assert code == 0
    warnings(findings, "REVIEW_PENDING")


def test_pos_7_review_skipped_complete_at_verify(tmp_path):
    build(str(tmp_path), record=record_yaml(review=RECORD_SKIPPED),
          scenarios=doc([scenario(1), scenario(2)], review="PM: skipped"))
    findings, code, _ = run(str(tmp_path), stage="verify")
    assert code == 0 and findings == []


def test_pos_8_draft_stage_uncited_scenario_warns(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, test="none yet")]),
          tests={E2E: e2e("SC-GH-123-01", extra_unit=UNCITED_UNIT)})
    findings, code, _ = run(str(tmp_path), stage="draft")
    warnings(findings, "SCENARIO_UNCITED")
    warnings(findings, "TEST_UNCITED")
    assert code == 0


# ---------------------------------------------------------------------------
# NEG
# ---------------------------------------------------------------------------

def test_neg_1_record_names_missing_file(tmp_path):
    build(str(tmp_path), record=record_yaml(scenarios_file="docs/nope.md"))
    findings, code, _ = run(str(tmp_path))
    blockers(findings, "FILE_MISSING")
    assert code == 2


def test_neg_2_no_scenarios_file_field_at_verify(tmp_path):
    build(str(tmp_path), record=record_yaml(scenarios_file=None))
    findings, code, _ = run(str(tmp_path), stage="verify")
    blockers(findings, "FILE_MISSING")
    assert code == 2


def test_neg_3_heading_without_colon(tmp_path):
    bad = "### SC-GH-123-1 title\n- Kind: acceptance\n"
    build(str(tmp_path), scenarios=doc([scenario(1), bad]))
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "MALFORMED")
    assert any(h["locus"].startswith(SCEN_REL + ":") and h["locus"].rsplit(":", 1)[1].isdigit() for h in hits)
    assert code == 2


def test_neg_4_missing_then(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, Then=None)]))
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "MALFORMED")
    assert any("Then" in h["message"] for h in hits)
    assert code == 2


def test_neg_5_kind_outside_enum(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, Kind="manual")]))
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "MALFORMED")
    assert any("manual" in h["message"] for h in hits)
    assert code == 2


def test_neg_6_id_from_another_change(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, change="GH-999")]),
          tests={E2E: e2e("SC-GH-123-01", "SC-GH-999-02")})
    findings, code, _ = run(str(tmp_path))
    blockers(findings, "ID_PREFIX")
    assert code == 2


def test_neg_7_duplicate_id(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(1, title="Another")]))
    findings, code, _ = run(str(tmp_path))
    blockers(findings, "ID_DUPLICATE")
    assert code == 2


def test_neg_8_gap_in_sequence(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(3)]),
          tests={E2E: e2e("SC-GH-123-01", "SC-GH-123-03")})
    findings, code, _ = run(str(tmp_path))
    blockers(findings, "ID_SEQUENCE")
    assert code == 2


def test_neg_9_no_context_section(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2)], heading_context=False))
    findings, code, _ = run(str(tmp_path))
    blockers(findings, "CONTEXT_MISSING")
    assert code == 2


def test_neg_10_none_yet_and_no_citing_test(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, test="none yet")]),
          tests={E2E: e2e("SC-GH-123-01")})
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "SCENARIO_UNCITED")
    assert "SC-GH-123-02" in hits[0]["message"]
    assert code == 2


def test_neg_11_deferred_without_reason(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, test="deferred (qa)")]),
          tests={E2E: e2e("SC-GH-123-01")})
    findings, code, _ = run(str(tmp_path))
    blockers(findings, "DEFERRAL_INCOMPLETE")
    assert code == 2




def line_of(text, needle):
    """1-based line number of the first line containing `needle`."""
    return next(i for i, l in enumerate(text.split("\n"), 1) if needle in l)


def test_neg_12_e2e_unit_without_id_in_test_set(tmp_path):
    text = e2e("SC-GH-123-01", "SC-GH-123-02", extra_unit=UNCITED_UNIT)
    build(str(tmp_path), tests={E2E: text})
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "TEST_UNCITED")
    assert hits[0]["locus"] == "%s:%d" % (E2E, line_of(text, "something else"))
    assert code == 2


def test_neg_13_e2e_unit_without_id_outside_test_set(tmp_path):
    other = "tests/e2e/other.spec.ts"
    build(str(tmp_path), tests={E2E: e2e("SC-GH-123-01", "SC-GH-123-02"), other: e2e(extra_unit=UNCITED_UNIT)})
    findings, code, _ = run(str(tmp_path))
    assert "TEST_UNCITED" not in codes(findings) and code == 0


def test_neg_14_review_pending_at_verify_blocks(tmp_path):
    build(str(tmp_path), record=record_yaml(review={"status": "pending"}),
          scenarios=doc([scenario(1), scenario(2)], review="PM: pending"))
    findings, code, _ = run(str(tmp_path), stage="verify")
    blockers(findings, "REVIEW_PENDING")
    assert code == 2


def test_neg_15_done_without_ts(tmp_path):
    build(str(tmp_path), record=record_yaml(review={"status": "done", "by": "Dana (PM)"}))
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "REVIEW_RECORD_INCOMPLETE")
    assert "ts" in hits[0]["message"]
    assert code == 2


def test_neg_16_skipped_without_pm(tmp_path):
    rec = {k: v for k, v in RECORD_SKIPPED.items() if k != "pm"}
    build(str(tmp_path), record=record_yaml(review=rec),
          scenarios=doc([scenario(1), scenario(2)], review="PM: skipped"))
    findings, code, _ = run(str(tmp_path), stage="verify")
    hits = blockers(findings, "REVIEW_RECORD_INCOMPLETE")
    assert "pm" in hits[0]["message"]
    assert code == 2


def test_neg_17_header_review_disagrees_with_record(tmp_path):
    build(str(tmp_path), record=record_yaml(review={"status": "pending"}),
          scenarios=doc([scenario(1), scenario(2)], review="PM: done"))
    findings, code, _ = run(str(tmp_path), stage="review")
    warnings(findings, "REVIEW_HEADER_STALE")
    assert code == 0


def test_neg_18_length_warning_and_strict(tmp_path):
    padding = " ".join(["word"] * 1100)
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2)], extra="\n## Notes\n\n" + padding + "\n"))
    findings, code, _ = run(str(tmp_path))
    warnings(findings, "LENGTH")
    assert code == 0
    assert C.exit_code(findings, strict=True) == 1


def test_neg_19_em_dash_warns(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, Then="the total is unchanged %s nothing else" % DASH)]))
    findings, code, _ = run(str(tmp_path))
    hits = warnings(findings, "PLAIN")
    assert "em dash" in hits[0]["message"]
    assert code == 0


def test_neg_20_duplicate_yaml_key_is_malformed_not_traceback(tmp_path):
    build(str(tmp_path), record=record_yaml() + "tests:\n  files: []\n")
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "MALFORMED")
    assert "duplicate" in hits[0]["message"]
    assert code == 2


def test_neg_21_symlink_out_of_repo_is_malformed(tmp_path):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside.md"
    outside.write_text(doc([scenario(1), scenario(2)]))
    build(str(repo), scenarios="")
    link = repo / SCEN_REL
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(str(outside), str(link))
    findings, code, _ = run(str(repo))
    hits = blockers(findings, "MALFORMED")
    assert "outside" in hits[0]["message"]
    assert code == 2


def test_neg_21b_oversized_file_is_malformed(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "MAX_BYTES", 100)
    build(str(tmp_path))
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "MALFORMED")
    assert "larger" in hits[0]["message"]
    assert code == 2


def test_neg_22_no_files_and_no_git_is_unscoped_but_scenarios_still_checked(tmp_path):
    build(str(tmp_path), record=record_yaml(files=None),
          scenarios=doc([scenario(1), scenario(2, test="none yet")]),
          tests={E2E: e2e("SC-GH-123-01")})
    env_root = str(tmp_path)
    assert subprocess.run(["git", "-C", env_root, "rev-parse"], capture_output=True).returncode != 0
    findings, code, _ = run(env_root)
    warnings(findings, "TESTS_UNSCOPED")
    blockers(findings, "SCENARIO_UNCITED")
    assert code == 2


def test_neg_23_six_sentence_context_warns(tmp_path):
    ctx = "One. Two. Three. Four. Five. Six."
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2)], context=ctx))
    findings, code, _ = run(str(tmp_path))
    hits = warnings(findings, "CONTEXT_LONG")
    assert "6 sentences" in hits[0]["message"]
    assert code == 0


def test_neg_24_json_output_is_a_list_of_findings(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2, test="none yet")]),
          tests={E2E: e2e("SC-GH-123-01")})
    r = subprocess.run([sys.executable, SCRIPT, "--json"], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 2 and "Traceback" not in r.stderr
    out = json.loads(r.stdout)
    assert isinstance(out, list) and out
    assert all(set(f) == {"code", "message", "waivable", "locus"} for f in out)


def test_neg_25_comment_inside_unit_cites(tmp_path):
    unit = "test('expired code', async ({ page }) => {\n  // covers SC-GH-123-02\n  await page.goto('/');\n});\n"
    build(str(tmp_path), tests={E2E: e2e("SC-GH-123-01", extra_unit=unit)})
    findings, code, summary = run(str(tmp_path))
    assert code == 0 and findings == []
    assert summary["cited"] == 2


def test_neg_26_playwright_skip_unit_without_id(tmp_path):
    unit = "test.skip('pending environment', async ({ page }) => {\n  await page.goto('/');\n});\n"
    text = e2e("SC-GH-123-01", "SC-GH-123-02", extra_unit=unit)
    build(str(tmp_path), tests={E2E: text})
    findings, code, _ = run(str(tmp_path))
    hits = blockers(findings, "TEST_UNCITED")
    assert hits[0]["locus"] == "%s:%d" % (E2E, line_of(text, "test.skip("))
    assert code == 2


def test_neg_27_draft_stage_duplicate_id_still_blocks(tmp_path):
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(1, title="Twice", test="none yet")]))
    findings, code, _ = run(str(tmp_path), stage="draft")
    blockers(findings, "ID_DUPLICATE")
    assert code == 2


# ---------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------

def test_cli_empty_dir_blocks_without_traceback(tmp_path):
    r = subprocess.run([sys.executable, SCRIPT], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr and "Traceback" not in r.stdout
    assert "[BLOCK] MALFORMED" in r.stdout or "[BLOCK] FILE_MISSING" in r.stdout
    assert r.stdout.rstrip().splitlines()[-1].startswith("Scenarios: ")


def test_cli_passing_fixture_exits_zero_with_verdict(tmp_path):
    build(str(tmp_path))
    r = subprocess.run([sys.executable, SCRIPT, "--stage", "verify"], cwd=str(tmp_path),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "Scenarios: 2 scenarios, 2 cited, 0 deferred, review done."


def test_cli_file_override_and_tests_root(tmp_path):
    alt = "docs/alt.md"
    spec_file = "checks/e2e/flow.spec.ts"
    build(str(tmp_path), record=record_yaml(scenarios_file="docs/missing.md", files=(spec_file,)),
          scenarios="", tests={spec_file: e2e("SC-GH-123-01", "SC-GH-123-02")})
    write(str(tmp_path), alt, doc([scenario(1, test=spec_file), scenario(2, test=spec_file)]))
    r = subprocess.run([sys.executable, SCRIPT, "--file", alt, "--tests", "checks"], cwd=str(tmp_path),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_bare_numeric_change_id_accepts_prefixed_scenario_ids(tmp_path):
    build(str(tmp_path), record=record_yaml(change_id="123"))
    findings, code, _ = run(str(tmp_path))
    assert "ID_PREFIX" not in codes(findings) and code == 0


# ---------------------------------------------------------------------------
# Mutation: every blocker disappears when its one defect is removed
# ---------------------------------------------------------------------------

def _pending_pair():
    rec = record_yaml(review={"status": "pending"})
    return (dict(record=rec, scenarios=doc([scenario(1), scenario(2)], review="PM: pending")),
            dict(record=record_yaml(review=RECORD_DONE)))


MUTATIONS = {
    "FILE_MISSING": (dict(record=record_yaml(scenarios_file="docs/nope.md")), dict()),
    "MALFORMED": (dict(scenarios=doc([scenario(1), scenario(2, Kind="manual")])), dict()),
    "ID_PREFIX": (dict(scenarios=doc([scenario(1), scenario(2, change="GH-999")]),
                       tests={E2E: e2e("SC-GH-123-01", "SC-GH-999-02")}), dict()),
    "ID_DUPLICATE": (dict(scenarios=doc([scenario(1), scenario(1, title="Twice")])), dict()),
    "ID_SEQUENCE": (dict(scenarios=doc([scenario(1), scenario(3)]), tests={E2E: e2e("SC-GH-123-01", "SC-GH-123-03")}),
                    dict()),
    "CONTEXT_MISSING": (dict(scenarios=doc([scenario(1), scenario(2)], heading_context=False)), dict()),
    "SCENARIO_UNCITED": (dict(scenarios=doc([scenario(1), scenario(2, test="none yet")]), tests={E2E: e2e("SC-GH-123-01")}),
                         dict()),
    "DEFERRAL_INCOMPLETE": (dict(scenarios=doc([scenario(1), scenario(2, test="deferred (qa)")]), tests={E2E: e2e("SC-GH-123-01")}),
                            dict(scenarios=doc([scenario(1), scenario(2, test='deferred (qa, "later")')]),
                                 tests={E2E: e2e("SC-GH-123-01")})),
    "TEST_UNCITED": (dict(tests={E2E: e2e("SC-GH-123-01", "SC-GH-123-02", extra_unit=UNCITED_UNIT)}), dict()),
    "REVIEW_PENDING": _pending_pair(),
    "REVIEW_RECORD_INCOMPLETE": (dict(record=record_yaml(review={"status": "done", "by": "Dana (PM)"})), dict()),
}

BLOCKER_CODES = sorted({"FILE_MISSING", "MALFORMED", "ID_PREFIX", "ID_DUPLICATE", "ID_SEQUENCE", "CONTEXT_MISSING",
                        "SCENARIO_UNCITED", "DEFERRAL_INCOMPLETE", "TEST_UNCITED", "REVIEW_PENDING",
                        "REVIEW_RECORD_INCOMPLETE"})


def test_every_blocker_code_has_a_mutation():
    assert sorted(MUTATIONS) == BLOCKER_CODES


@pytest.mark.parametrize("code", BLOCKER_CODES)
def test_mutation(code, tmp_path):
    bad, good = MUTATIONS[code]
    stage = "verify"
    build(str(tmp_path / "bad"), **bad)
    findings, rc, _ = run(str(tmp_path / "bad"), stage=stage)
    blockers(findings, code)
    assert rc == 2
    build(str(tmp_path / "good"), **good)
    findings, rc, _ = run(str(tmp_path / "good"), stage=stage)
    assert code not in codes(findings), "removing the defect must remove %s, got %s" % (code, codes(findings))
    assert rc == 0, codes(findings)


def test_review_header_with_detail_is_not_stale(tmp_path):
    """The skills write 'PM: done, <date>' and 'PM: skipped (<reason>)'; only the first word is the status."""
    build(str(tmp_path), scenarios=doc([scenario(1), scenario(2)], review="PM: done, 2026-10-05"))
    findings, code, _ = run(str(tmp_path))
    assert "REVIEW_HEADER_STALE" not in codes(findings), codes(findings)
    assert code == 0


def test_no_scenarios_file_field_at_draft_is_not_file_missing(tmp_path):
    rec = record_yaml().replace("scenarios_file", "scenarios_file_absent")
    build(str(tmp_path), record=rec)
    findings, code, _ = run(str(tmp_path), stage="draft")
    assert "FILE_MISSING" not in codes(findings), codes(findings)
    findings, code, _ = run(str(tmp_path), stage="review")
    assert "FILE_MISSING" in codes(findings)
