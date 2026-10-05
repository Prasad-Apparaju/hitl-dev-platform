"""Breadcrumb band (FR-37) seams: the ignore line reaches every path that writes a product repo's
.gitignore, the plugin build ships the module and not its tests, and _steps.sh stays the only
renderer. The mod's own footprint is asserted in ci/breadcrumb-mod/ by `claude plugin validate`.

Run: python3 -m pytest ci/wiring/test_breadcrumb_band_wiring.py -q
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOKS = os.path.join(ROOT, "ai", "claude", "hooks")


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def test_ignore_line_in_the_three_places_that_write_a_product_gitignore():
    for rel in ("tools/scripts/init-project.sh",
                "ai/claude/start-from-prd/SKILL.md",
                "ai/claude/update/SKILL.md"):
        assert ".hitl/breadcrumb.txt" in _read(rel), "%s does not add the band cache ignore line" % rel


def test_the_module_is_listed_and_present():
    import json
    hooks = json.load(io.open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8"))
    assert hooks.get("modules") == ["./breadcrumb-band.js"], hooks
    assert "hooks" not in hooks, "the plugin's settings hooks live in each product repo, not in hooks.json"
    assert os.path.isfile(os.path.join(HOOKS, "breadcrumb-band.js"))


def test_the_plugin_build_ships_js_and_skips_tests():
    """The sibling plugin repo's build.sh copies hooks; it must take *.js and leave tests/ behind."""
    build = os.path.join(ROOT, "..", "hitl-claude-plugin", "scripts", "build.sh")
    if not os.path.isfile(build):
        import pytest
        pytest.skip("plugin repo not checked out beside this one")
    text = io.open(build, encoding="utf-8").read()
    m = re.search(r'find "\$SOURCE_DIR/ai/claude/hooks".*', text)
    assert m, "no hooks find line in build.sh"
    assert '-name "*.js"' in m.group(0), m.group(0)
    assert '! -path "*/tests/*"' in m.group(0), m.group(0)


def test_steps_sh_is_the_only_renderer():
    """The ribbon separators are composed in _steps.sh and nowhere else under hooks/. The mod file
    may mention the current-step marker only to find it, never to build a ribbon."""
    for name in os.listdir(HOOKS):
        path = os.path.join(HOOKS, name)
        if not os.path.isfile(path) or name == "_steps.sh":
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        assert " › " not in text.replace("`", ""), "%s composes a ribbon (contains the phase separator)" % name


def test_renderer_writes_the_cache_from_both_callers():
    steps = _read("ai/claude/hooks/_steps.sh")
    assert "hitl_write_breadcrumb_cache()" in steps and "hitl_breadcrumb_mode()" in steps
    for rel in ("ai/claude/hooks/welcome.sh", "ai/claude/hooks/statusline-hitl.sh"):
        assert "hitl_write_breadcrumb_cache" in _read(rel), rel
    assert 'exit 0' in _read("ai/claude/hooks/welcome.sh").split('hitl_breadcrumb_mode')[1][:600], \
        "welcome.sh does not quiet the transcript in band mode"
