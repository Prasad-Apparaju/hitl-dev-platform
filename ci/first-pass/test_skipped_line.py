#!/usr/bin/env python3
"""The one-line skipped notice on the issue (plugin #34 note, hitl-dev-platform #112 decision).

Asserted by behaviour: the line renders from the ledger, the splice is idempotent and block-first,
`--apply` edits only when the body changes, and a `gh` failure is reported, not swallowed."""
import os
import sys
import subprocess

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import skipped_line as S


def change(skips, cid="GH-123"):
    return {"change_id": cid,
            "workflow": {"steps": [{"key": "roi", "label": "ROI"}, {"key": "figma", "label": "Figma"},
                                   {"key": "test_plan", "label": "Tests"}]},
            "skips": skips}


def test_line_names_each_step_once_with_disposition_reason_and_actor():
    line = S.render_line(change([
        {"step": "roi", "disposition": "decline", "reason": "internal tool", "actor": "pm@team"},
        {"step": "figma", "disposition": "defer", "reason": "no UI change", "actor": "pm@team",
         "followup_ref": "issue:123"},
        {"step": "test_plan", "disposition": "starter", "reason": "thin first pass", "actor": "dev@team"},
    ]))
    assert line.startswith("**Skipped:** ")
    assert "ROI (declined: internal tool)" in line
    assert "Figma (deferred: no UI change)" in line
    assert "Tests (thin version now)" in line and "thin first pass" not in line
    assert "issue:123" not in line                      # the issue itself is not a ticket
    assert "chosen by pm@team, dev@team at plan confirm" in line
    assert line.count("Skipped") == 1


def test_a_real_ticket_is_named_and_a_resolved_skip_says_so():
    line = S.render_line(change([
        {"step": "figma", "disposition": "defer", "reason": "later", "followup_ref": "GH-130", "resolved": True},
    ]))
    assert "Figma (deferred: later, since done, ticket GH-130)" in line


def test_nothing_skipped_renders_empty_and_removes_an_old_block():
    assert S.render_line(change([])) == ""
    body = f"{S.OPEN}\n**Skipped:** old\n{S.CLOSE}\n\n## Problem\ntext"
    assert S.splice(body, "") == "## Problem\ntext"


def test_reason_is_blame_filtered_and_truncated():
    long = "x" * 200
    line = S.render_line(change([{"step": "roi", "disposition": "decline", "reason": long}]))
    assert "x" * 61 not in line and "…" in line
    blamed = S.render_line(change([{"step": "roi", "disposition": "decline",
                                     "reason": "the dev was lazy and sloppy"}]))
    assert "lazy" not in blamed and "sloppy" not in blamed


def test_splice_puts_block_first_and_is_idempotent():
    body = "## Problem\ntext\n"
    once = S.splice(body, "**Skipped:** ROI (declined: x) at plan confirm.")
    assert once.startswith(S.OPEN) and once.endswith("## Problem\ntext\n")
    twice = S.splice(once, "**Skipped:** ROI (declined: x) at plan confirm.")
    assert twice == once
    changed = S.splice(once, "**Skipped:** Figma (deferred: y) at plan confirm.")
    assert changed.count(S.OPEN) == 1 and "ROI" not in changed and "Figma" in changed


def test_issue_number_from_change_id_or_flag():
    assert S.issue_number({"change_id": "GH-123"}) == 123
    assert S.issue_number({"change_id": "GH-123"}, "#77") == 77
    assert S.issue_number({"change_id": "docs-refresh"}) is None


class FakeGh:
    """A gh that serves one issue body and records edits."""
    def __init__(self, body, fail_edit=False):
        self.body, self.edits, self.fail_edit = body, [], fail_edit

    def __call__(self, args, capture_output=True, text=True):
        assert args[0] == "gh"
        if args[1:3] == ["issue", "view"]:
            return subprocess.CompletedProcess(args, 0, stdout=self.body, stderr="")
        if args[1:3] == ["issue", "edit"]:
            if self.fail_edit:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 403: forbidden")
            path = args[args.index("--body-file") + 1]
            self.body = open(path).read()
            self.edits.append(self.body)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(args)


def test_apply_writes_once_then_reports_unchanged():
    gh = FakeGh("## Problem\ntext")
    ch = change([{"step": "roi", "disposition": "decline", "reason": "internal", "actor": "pm@team"}])
    assert S.apply(ch, 123, run=gh) == "written"
    assert gh.body.startswith(S.OPEN) and gh.body.endswith("## Problem\ntext")
    assert S.apply(ch, 123, run=gh) == "unchanged"
    assert len(gh.edits) == 1


def test_apply_removes_the_block_when_nothing_is_skipped_any_more():
    gh = FakeGh(f"{S.OPEN}\n**Skipped:** ROI (declined: x)\n{S.CLOSE}\n\n## Problem\ntext")
    assert S.apply(change([]), 123, run=gh) == "removed"
    assert S.OPEN not in gh.body and gh.body == "## Problem\ntext"


def test_main_reports_a_gh_failure_and_exits_nonzero(tmp_path, capsys):
    import yaml
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(change([{"step": "roi", "disposition": "decline", "reason": "r"}])))
    rc = S.main(["--change", str(p), "--apply"], run=FakeGh("body", fail_edit=True))
    assert rc == 3 and "not updated" in capsys.readouterr().err
    rc = S.main(["--change", str(p)], run=FakeGh("body"))
    assert rc == 0 and "**Skipped:** ROI" in capsys.readouterr().out


def test_main_needs_an_issue_number_to_apply(tmp_path, capsys):
    import yaml
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(change([{"step": "roi", "disposition": "decline", "reason": "r"}], cid="docs")))
    assert S.main(["--change", str(p), "--apply"], run=FakeGh("body")) == 2
    assert "no issue number" in capsys.readouterr().err
