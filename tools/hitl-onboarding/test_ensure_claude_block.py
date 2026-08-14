"""Tests for the CLAUDE.md HITL-block upsert.

The load-bearing cases are the destructive ones: never lose the team's content, never duplicate
the block, and never swallow a file whose block was truncated.
"""
import io
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ensure_claude_block import apply  # noqa: E402

SCRIPT = os.path.join(HERE, "ensure_claude_block.py")
BLOCK = "<!-- HITL:BEGIN -->\n## This project uses HITL\nRun /hitl:dev-start-change\n<!-- HITL:END -->"


def test_creates_when_absent():
    new, action = apply(None, BLOCK)
    assert action == "created"
    assert "dev-start-change" in new


def test_appends_and_keeps_existing_content():
    cur = "# My Project\n\nOur standards.\n"
    new, action = apply(cur, BLOCK)
    assert action == "appended"
    assert "Our standards." in new, "the team's content must survive"
    assert new.count("HITL:BEGIN") == 1


def test_rerun_refreshes_and_never_duplicates():
    once, _ = apply("# P\n\nmine\n", BLOCK)
    twice, action = apply(once, BLOCK)
    assert action == "current"
    assert twice.count("HITL:BEGIN") == 1
    updated = BLOCK.replace("Run /hitl:dev-start-change", "Run /hitl:dev-start-change first")
    third, action = apply(once, updated)
    assert action == "refreshed"
    assert third.count("HITL:BEGIN") == 1
    assert "first" in third
    assert "mine" in third


def test_refresh_preserves_content_on_both_sides():
    cur = "# Top\n\n" + BLOCK + "\n\n## Local rules\nkeep me\n"
    new, action = apply(cur, BLOCK.replace("HITL\n", "HITL v2\n"))
    assert action == "refreshed"
    assert "# Top" in new and "keep me" in new


def test_unterminated_block_leaves_file_untouched():
    """A BEGIN with no END must not eat everything after the marker."""
    cur = "# P\n<!-- HITL:BEGIN -->\nstale\n\n## Important\nkeep me\n"
    new, action = apply(cur, BLOCK)
    assert action == "unterminated"
    assert new == cur
    assert "keep me" in new


def test_no_trailing_newline_still_separates():
    new, _ = apply("# P\nno trailing newline", BLOCK)
    assert "no trailing newline\n\n<!-- HITL:BEGIN" in new


def _run(tmp_path, current):
    dest = tmp_path / "CLAUDE.md"
    blk = tmp_path / "block.md"
    blk.write_text(BLOCK, encoding="utf-8")
    if current is not None:
        dest.write_text(current, encoding="utf-8")
    p = subprocess.run([sys.executable, SCRIPT, str(dest), str(blk)],
                       capture_output=True, text=True)
    return p, dest


def test_cli_appends_and_exits_zero(tmp_path):
    p, dest = _run(tmp_path, "# P\n\nmine\n")
    assert p.returncode == 0
    body = io.open(dest, encoding="utf-8").read()
    assert "mine" in body and body.count("HITL:BEGIN") == 1


def test_cli_unterminated_exits_3_and_writes_nothing(tmp_path):
    cur = "# P\n<!-- HITL:BEGIN -->\nstale\n## Important\nkeep me\n"
    p, dest = _run(tmp_path, cur)
    assert p.returncode == 3
    assert io.open(dest, encoding="utf-8").read() == cur


def test_cli_missing_template_does_not_crash(tmp_path):
    dest = tmp_path / "CLAUDE.md"
    dest.write_text("# P\n", encoding="utf-8")
    p = subprocess.run([sys.executable, SCRIPT, str(dest), str(tmp_path / "nope.md")],
                       capture_output=True, text=True)
    assert p.returncode == 1
    assert io.open(dest, encoding="utf-8").read() == "# P\n", "must not touch the file"


def test_shipped_block_is_well_formed():
    """The real template must round-trip through its own markers."""
    real = os.path.join(HERE, "..", "..", "ai", "shared", "templates", "claude-md-hitl-block.md")
    if not os.path.isfile(real):
        pytest.skip("block template not present in this layout")
    text = io.open(real, encoding="utf-8").read()
    assert text.count("<!-- HITL:BEGIN") == 1
    assert text.count("<!-- HITL:END -->") == 1
    assert "/hitl:dev-start-change" in text, "the block must name the front door"
    new, action = apply("# P\nmine\n", text)
    assert action == "appended"
    again, action = apply(new, text)
    assert action == "current" and again.count("HITL:BEGIN") == 1
