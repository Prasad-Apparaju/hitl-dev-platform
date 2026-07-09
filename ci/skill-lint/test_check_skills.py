"""Tests for the SKILL.md linter. Run: pytest ci/skill-lint/test_check_skills.py"""

from __future__ import annotations

from pathlib import Path

import check_skills as cs


def _skill(tmp: Path, rel: str, body: str) -> Path:
    p = tmp / rel / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


VALID = """---
name: do-a-thing
description: Processes a thing. Use this when the user needs a thing processed.
---

# Do a thing
Body content.
"""


def test_valid_skill_passes(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "do-a-thing", VALID)
    rep = cs.run(root)
    assert rep.fails == []


def test_missing_description_fails(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "x", "---\nname: x\n---\n\nbody\n")
    rep = cs.run(root)
    assert any(f.criterion == "description" for f in rep.fails)


def test_missing_name_is_note_not_fail_by_default(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "x", "---\ndescription: Does x. Use when needed.\n---\n\nbody\n")
    rep = cs.run(root)
    assert rep.fails == []
    assert rep.name_fallback == 1


def test_missing_name_fails_under_require_name(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "x", "---\ndescription: Does x. Use when needed.\n---\n\nbody\n")
    rep = cs.run(root, require_name=True)
    assert any(f.criterion == "name" for f in rep.fails)


def test_bad_name_format_fails_when_present(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "x", "---\nname: Bad_Name\ndescription: d. Use when needed.\n---\n\nb\n")
    rep = cs.run(root)
    assert any(f.criterion == "name" for f in rep.fails)


def test_reserved_word_in_name_fails(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "x", "---\nname: claude-helper\ndescription: d. Use when.\n---\n\nb\n")
    rep = cs.run(root)
    assert any("reserved" in f.detail for f in rep.fails)


def test_overlong_body_fails(tmp_path: Path):
    root = tmp_path / "ai"
    body = "---\nname: big\ndescription: d. Use when needed.\n---\n\n" + "\n".join(
        f"line {i}" for i in range(cs.BODY_MAX_LINES + 5))
    _skill(root, "big", body)
    rep = cs.run(root)
    assert any(f.criterion == "body" for f in rep.fails)


def test_malformed_frontmatter_fails(tmp_path: Path):
    root = tmp_path / "ai"
    _skill(root, "x", "no frontmatter here\njust text\n")
    rep = cs.run(root)
    assert any(f.criterion == "frontmatter" for f in rep.fails)
