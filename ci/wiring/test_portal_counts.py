"""The portal states numbers in prose and nothing held them: on 2026-10-08 three pages said 52
skills, 8 hooks and 25 templates two releases after those stopped being true, and the home page's
What's new stopped at 2.12 while 2.18 shipped. The version stamp never drifted because a wiring test
holds it to plugin.json. These tests hold the prose counts and the What's new cards the same way.

Each count is computed from its source in the tree, not from a document, and the page must state
that exact number in the sentence that carries it.

Run: python3 -m pytest ci/wiring/test_portal_counts.py -q
"""
import glob
import io
import json
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SITE = os.path.join(ROOT, "site")
AI = os.path.join(ROOT, "ai")


def _page(name):
    return io.open(os.path.join(SITE, name), encoding="utf-8").read()


def _skills():
    """What lands as skill directories in the built plugin: every SKILL.md under ai/claude."""
    return len(glob.glob(os.path.join(AI, "claude", "**", "SKILL.md"), recursive=True))


def _hooks():
    """Shell hooks shipped in hooks/: the wired ones, the deploy gate, and the mod modules."""
    sh = [os.path.basename(p) for p in glob.glob(os.path.join(AI, "claude", "hooks", "*.sh"))]
    sh = [s for s in sh if s != "_steps.sh"]
    gate = [s for s in sh if s == "check-platform-ready.sh"]
    hooks_json = json.load(io.open(os.path.join(AI, "claude", "hooks", "hooks.json"), encoding="utf-8"))
    return len(sh) - len(gate), len(gate), len(hooks_json.get("modules", []))


def _templates():
    files = glob.glob(os.path.join(AI, "shared", "templates", "*.yaml"))
    files += glob.glob(os.path.join(AI, "shared", "templates", "*.md"))
    files += glob.glob(os.path.join(AI, "claude", "generate-docs", "templates", "*.md"))
    return len(files)


def _steps():
    cat = yaml.safe_load(io.open(os.path.join(AI, "shared", "workflows.yaml"), encoding="utf-8"))
    numbered = lettered = 0
    for wf in cat["workflows"].values():
        for st in wf.get("steps", []):
            if re.fullmatch(r"\d+", str(st.get("n"))):
                numbered += 1
            else:
                lettered += 1
    return len(cat["workflows"]), numbered, lettered


def _latest_release():
    text = io.open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(r"^## \[(\d+)\.(\d+)\.(\d+)\]", text, re.M)
    assert m, "CHANGELOG.md has no released section heading"
    return m.group(1), m.group(2)


def test_architecture_pillar_counts():
    page = _page("architecture.html")
    wired, gate, mods = _hooks()
    for needle in ('<span class="count">%d skills</span>' % _skills(),
                   '<span class="count">%d wired + %d deploy gate + %d mod</span>' % (wired, gate, mods),
                   '<span class="count">%d templates + 8 ADR stubs</span>' % _templates(),
                   '<span class="count">1 catalog · %d workflows</span>' % _steps()[0]):
        assert needle in page, "architecture.html does not say: %s" % needle


def test_compare_hook_count():
    wired, _gate, _mods = _hooks()
    assert "(%d hooks, settings, ADR stubs)" % wired in _page("compare.html")


def test_going_ai_native_skill_count():
    assert "%d skills" % _skills() in _page("going-ai-native.html")


def test_catalog_card_step_counts():
    workflows, numbered, lettered = _steps()
    needle = "All %d workflows, their phases, %d numbered steps and %d lettered substeps" % (workflows, numbered, lettered)
    assert needle in _page("index.html"), "index.html catalog card does not say: %s" % needle


def test_whats_new_carries_the_latest_release():
    major, minor = _latest_release()
    page = _page("index.html")
    assert 'pill live">%s.%s<' % (major, minor) in page, (
        "index.html What's new has no card for %s.%s; add one before releasing" % (major, minor))


def test_compare_names_the_latest_release():
    major, minor = _latest_release()
    page = _page("compare.html")
    assert "(%s.%s)" % (major, minor) in page, "compare.html's 2.x card does not name %s.%s" % (major, minor)
