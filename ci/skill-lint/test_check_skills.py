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


# ---------------------------------------------------------------------------
# Reference checks (issue: the 2.4.6 broken worked-example link, and the three
# gaps that let it pass a clean run). Each case below was found by an independent
# adversarial audit; they are locked in so the guard cannot quietly regress again.
# ---------------------------------------------------------------------------

FM = "---\ndescription: Fixture. Use when testing references.\n---\n\n"


def _tree(tmp_path: Path):
    """A miniature source tree: ai/claude/<skill>/ plus ai/shared/ and a NON-shipped docs/."""
    root = tmp_path / "ai"
    (root / "shared" / "first-pass").mkdir(parents=True)
    (root / "shared" / "first-pass" / "real.md").write_text("# shared\n")
    (tmp_path / "docs" / "examples").mkdir(parents=True)
    (tmp_path / "docs" / "examples" / "worked.md").write_text("# worked\n")
    return root


def test_legit_shared_hop_is_not_flagged(tmp_path: Path):
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "[ok](../../shared/first-pass/real.md)\n")
    rep = cs.run(root)
    assert not [f for f in rep.fails if f.criterion.startswith("ref")]


def test_escape_into_unpackaged_dir_fails_even_though_it_resolves(tmp_path: Path):
    """The 2.4.6 defect: resolves in the source repo, points at nothing once installed."""
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "[bad](../../../docs/examples/worked.md)\n")
    rep = cs.run(root)
    assert any(f.criterion == "ref-escapes" for f in rep.fails)


def test_escape_check_uses_path_resolution_not_substring_counting(tmp_path: Path):
    """`foo/../bar.md` climbs nowhere; counting '../' called it an escape."""
    root = _tree(tmp_path)
    (root / "claude" / "t").mkdir(parents=True, exist_ok=True)
    (root / "claude" / "t" / "bar.md").write_text("# bar\n")
    _skill(root, "claude/t", FM + "[noop](foo/../bar.md)\n")
    rep = cs.run(root)
    assert not [f for f in rep.fails if f.criterion.startswith("ref")]


def test_missing_directory_target_is_reported(tmp_path: Path):
    """Gating existence behind endswith('.md') is half of why the original bug was invisible."""
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "[d](examples/)\n")
    rep = cs.run(root)
    assert any(f.criterion == "ref-missing" for f in rep.fails)


def test_link_title_and_angle_brackets_are_parsed(tmp_path: Path):
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + '[t](missing.md "Some Title")\n[a](<missing spaced.md>)\n')
    rep = cs.run(root)
    assert len([f for f in rep.fails if f.criterion == "ref-missing"]) == 2


def test_reference_style_link_is_checked(tmp_path: Path):
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "[refstyle]: ../../../../way/up/high.md\n")
    rep = cs.run(root)
    assert any(f.criterion == "ref-escapes" for f in rep.fails)


def test_anchor_only_link_is_ignored(tmp_path: Path):
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "[anch](#section)\n")
    rep = cs.run(root)
    assert not [f for f in rep.fails if f.criterion.startswith("ref")]


def test_link_inside_a_fence_is_ignored(tmp_path: Path):
    """Emitted templates: the skill writes this link into the USER's docs, where it is correct."""
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "```markdown\n[Deployment View](deployment-view.md)\n```\n")
    rep = cs.run(root)
    assert not [f for f in rep.fails if f.criterion.startswith("ref")]


def test_nested_fences_do_not_leak(tmp_path: Path):
    """A ```` fence holding an ODD number of ``` fences flipped a boolean toggle inside-out."""
    root = _tree(tmp_path)
    body = FM + "````markdown\n```bash\necho hi\n```\n[Deployment View](deployment-view.md)\n````\n"
    _skill(root, "claude/t", body)
    rep = cs.run(root)
    assert not [f for f in rep.fails if f.criterion.startswith("ref")]


def test_unterminated_fence_is_an_error_not_a_silent_skip(tmp_path: Path):
    """An unclosed fence blanked the rest of the file, hiding real defects after it."""
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "```bash\necho oops\n\n[hidden](../../../../way/up.md)\n")
    rep = cs.run(root)
    assert any(f.criterion == "fence" for f in rep.fails)


def test_reference_findings_report_the_real_line(tmp_path: Path):
    """Every ref finding used to report body_start, so it pointed at the frontmatter boundary."""
    root = _tree(tmp_path)
    _skill(root, "claude/t", FM + "filler\nfiller\n[bad](../../../docs/examples/worked.md)\n")
    rep = cs.run(root)
    f = next(f for f in rep.fails if f.criterion == "ref-escapes")
    assert f.line >= 7, f"expected the link's own line, got {f.line}"
