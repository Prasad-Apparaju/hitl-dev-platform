#!/usr/bin/env python3
"""Wiring conformance — the class of defect unit tests structurally cannot catch.

Every serious defect found in the 2026-08 review rounds had the same shape: machinery that existed,
was correct, was unit-tested, and was connected to nothing.

- `permissions.decide()` was implemented and tested; no caller. CR-15 never engaged.
- `resurface.surface()` was called where its inputs could not yet exist. It matched nothing, silently.
- `check_skips.check()` was gated on a flag the driver never emitted. Certification passed on
  everything.
- The issue-#14 Python probe was fixed in the skills and never carried to `init-project.sh`, so
  onboarded repos got hooks that silently no-op on Windows.
- One false sentence about tier behaviour was copied into five files.

Unit tests passed in all five cases, because in all five cases the unit was fine. The defect lived in
the seam. These tests assert the seams.

A full end-to-end simulation of a 31-step workflow would be slow, brittle, and would still miss most
of the above. Instead this file checks three specific properties:

  REACHABILITY  — every shipped module is actually invoked by something that ships
  CONSISTENCY   — definitions that exist in more than one place agree
  COMPLETENESS  — every hook that exists is wired, and every wired hook exists

Run: python3 -m pytest ci/wiring -q
"""
import io
import os
import re
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # ci/wiring/ -> repo root
AI = os.path.join(ROOT, "ai")
HOOKS = os.path.join(AI, "claude", "hooks")


def _read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def _shipped_text():
    """Everything that ships and could reference a module: skills, hooks, CI, tools."""
    out = []
    for base in (AI, os.path.join(ROOT, "ci"), os.path.join(ROOT, "tools")):
        for dirpath, _dirs, files in os.walk(base):
            if "__pycache__" in dirpath or ".pytest_cache" in dirpath:
                continue
            for f in files:
                if f.startswith("test_") or not f.endswith((".md", ".py", ".sh", ".yml", ".yaml")):
                    continue
                out.append((os.path.join(dirpath, f), _read(os.path.join(dirpath, f))))
    return out


SHIPPED = _shipped_text()


# ── REACHABILITY ──────────────────────────────────────────────────────────────

FIRST_PASS_MODULES = ["check_skips", "resurface", "permissions", "starters",
                      "dispositions", "migrate_project"]


@pytest.mark.parametrize("mod", FIRST_PASS_MODULES)
def test_every_shipped_module_has_a_caller(mod):
    """A module nothing invokes is a promise nothing keeps.

    `permissions.py` sat like this for a full release: implemented, tested, documented in
    `first-pass/permissions.md` as the classifier the driver applies — and never called, so the
    reduced-friction policy it describes did not exist at runtime. `dispositions.py` was the same.

    Counts both call styles: a Python import, and a CLI invocation by filename (several of these
    are invoked as `python3 <path>/<mod>.py` from skill prose, which no import graph would see).
    """
    import_re = re.compile(rf"\b(?:from\s+{mod}\s+import|import\s+{mod})\b")
    cli_re = re.compile(rf"\b{mod}\.py\b")
    callers = [p for p, txt in SHIPPED
               if os.path.basename(p) != f"{mod}.py" and (import_re.search(txt) or cli_re.search(txt))]
    assert callers, (
        f"{mod}.py ships but nothing invokes it — no import, no CLI reference. Either wire it or "
        f"delete it; an untested-in-situ module is worse than an absent one because it reads as "
        f"a working guarantee.")


# ── CONSISTENCY ───────────────────────────────────────────────────────────────

WRAPPER_MARKERS = [
    ("installed_plugins.json", "runtime plugin discovery (pre-v1.0.9 without it)"),
    ("command -v", "the multi-candidate interpreter probe (issue #14)"),
    ("import sys", "the Store-stub smoke test (issue #14)"),
    ("HITL_PY", "the resolved interpreter handed to hooks (issue #14)"),
    ("PYTHONUTF8", "UTF-8 stdout for the breadcrumb glyphs (issue #14)"),
]

# The wrapper body should exist in as FEW places as possible. It is currently two: the skill that
# defines it, and the standalone shell installer which cannot reference a skill at runtime.
WRAPPER_SOURCES = [
    os.path.join(AI, "claude", "start-from-prd", "SKILL.md"),
    os.path.join(ROOT, "tools", "scripts", "init-project.sh"),
]

# These onboarding paths must REFERENCE the definition, never restate it. Both carried their own
# copy and both went stale, shipping hooks that silently no-op on Windows.
WRAPPER_REFERENCERS = [
    os.path.join(AI, "claude", "start-brownfield", "SKILL.md"),
    os.path.join(AI, "claude", "start-migration", "SKILL.md"),
]


@pytest.mark.parametrize("src", WRAPPER_REFERENCERS, ids=lambda p: os.path.basename(os.path.dirname(p)))
def test_onboarding_paths_reference_the_wrapper_rather_than_copy_it(src):
    txt = _read(src)
    assert 'exec bash "$PLUGIN_ROOT/hooks/' not in txt, (
        f"{os.path.relpath(src, ROOT)} contains its own hook-wrapper body. Every copy has drifted "
        f"eventually; reference Step 0 of dev-start-from-prd instead.")
    assert "start-from-prd" in txt, (
        f"{os.path.relpath(src, ROOT)} neither defines nor references the wrapper — onboarding "
        f"through it would create no wrappers at all.")


@pytest.mark.parametrize("src", WRAPPER_SOURCES, ids=lambda p: os.path.basename(os.path.dirname(p)) or os.path.basename(p))
@pytest.mark.parametrize("marker,why", WRAPPER_MARKERS, ids=lambda x: x if isinstance(x, str) and " " not in x else "")
def test_every_wrapper_generator_carries_every_marker(src, marker, why):
    """The hook-wrapper body is defined in four places. It has drifted twice.

    `init-project.sh` kept emitting the pre-issue-#14 wrapper long after the skills were fixed, so
    every repo onboarded through it got hooks that silently do nothing on Windows. Nothing detected
    that, because `dev-update`'s staleness check tested one marker and the drift was in another.
    """
    txt = _read(src)
    assert marker in txt, (
        f"{os.path.relpath(src, ROOT)} generates hook wrappers without {marker!r} — {why}. "
        f"All wrapper generators must stay in step; this is the drift that shipped broken hooks.")


def test_the_generated_wrapper_matches_the_authoritative_template():
    """Beyond markers: init-project.sh's output must not diverge structurally from the skill's."""
    script = _read(os.path.join(ROOT, "tools", "scripts", "init-project.sh"))
    skill = _read(os.path.join(AI, "claude", "start-from-prd", "SKILL.md"))
    for token in ("for _c in python3 python py", "PYTHONIOENCODING"):
        assert token in script and token in skill, (
            f"{token!r} present in only one wrapper generator — they have drifted again.")


def test_doctrine_about_tiers_matches_the_catalog():
    """Prose asserting catalog facts must be checkable against the catalog.

    One false sentence — that a low tier demotes five named steps — was copied into five shipped
    files and survived review. The tier facts themselves are pinned in ci/first-pass; this asserts
    no shipped text reasserts the disproved version.
    """
    bad = []
    for p, txt in SHIPPED:
        if "demotes" in txt and re.search(r"tier\s*(<=|≤)\s*1[^.]{0,80}demotes", txt):
            bad.append(os.path.relpath(p, ROOT))
    assert not bad, (
        "these files claim tier <= 1 demotes steps from floor to standard, which the catalog "
        f"contradicts (the five-step demotion is 3 -> 2): {bad}")


# ── COMPLETENESS ──────────────────────────────────────────────────────────────

def _hook_names():
    return sorted(f[:-3] for f in os.listdir(HOOKS)
                  if f.endswith(".sh") and not f.startswith("_"))


@pytest.mark.parametrize("hook", _hook_names())
def test_every_hook_that_exists_is_wired_somewhere(hook):
    """A hook file nobody registers never runs. `first-pass-permissions.sh` would have been
    exactly this had the onboarding settings block not been updated alongside it."""
    refs = [p for p, txt in SHIPPED if hook in txt and not p.endswith(f"{hook}.sh")]
    assert refs, (
        f"ai/claude/hooks/{hook}.sh exists but no skill, settings template, or script references "
        f"it — it will never fire.")


def test_every_wired_hook_exists():
    """The inverse: a settings template naming a hook that isn't there fails at runtime, silently."""
    missing = []
    have = set(_hook_names())
    for p, txt in SHIPPED:
        if not p.endswith("SKILL.md"):
            continue
        for name in re.findall(r"\.hitl/hooks/([a-z0-9-]+)\.sh", txt):
            if name not in have and name != "statusline":
                missing.append((os.path.relpath(p, ROOT), name))
    assert not missing, f"settings wiring names hooks that do not exist in ai/claude/hooks/: {missing}"


def test_the_onboarding_paths_agree_on_the_hook_list():
    """Three onboarding skills each enumerate the hooks to create. They must not disagree —
    a repo's enforcement should not depend on which command onboarded it."""
    lists = {}
    for f in ("start-from-prd", "start-brownfield", "start-migration"):
        txt = _read(os.path.join(AI, "claude", f, "SKILL.md"))
        m = re.search(r"wrapper for each of these \w+ hooks: (.+?)\. \(", txt, re.S)
        assert m, f"{f}: could not find the hook list — the wording changed, so this check went blind"
        lists[f] = sorted(re.findall(r"`([a-z0-9-]+)`", m.group(1)))
    first = next(iter(lists.values()))
    assert all(v == first for v in lists.values()), f"onboarding paths disagree on hooks: {lists}"


def test_every_reviewer_agent_carries_the_adversarial_stance():
    """A reviewer asked to confirm will confirm.

    Every HITL reviewer opened with "ensure X is sound" / "verify Y is sufficient" — questions
    shaped to be answered yes. In this framework's own review rounds, the same model on the same
    code returned clean when asked to verify and returned blockers when asked to refute. The stance
    is duplicated across five agent files by necessity (they ship standalone); this makes the
    duplication a checked invariant instead of drift bait.
    """
    reviewers = [f for f in os.listdir(os.path.join(AI, "claude", "agents"))
                 if f.endswith("-reviewer.md")]
    assert reviewers, "no reviewer agents found — this check went blind"
    missing = [f for f in reviewers
               if "Try to refute, not to confirm" not in _read(os.path.join(AI, "claude", "agents", f))]
    assert not missing, f"reviewer agents without the adversarial stance: {sorted(missing)}"


def test_the_skip_ledger_is_never_retired_with_the_change_file():
    """CR-10 makes the ledger durable across changes. The retirement step removes the change file
    and handoff prose at `promote`; if it ever removed the ledger too, every past skip would vanish
    and resurfacing would only ever see the current change."""
    txt = _read(os.path.join(AI, "claude", "dev-practices", "workflow-steps.md"))
    assert "Retire the change's working artifacts" in txt, "the retirement step is gone"
    retire = txt[txt.index("Retire the change's working artifacts"):][:1200]
    assert "skip-ledger.yaml" in retire and "Do not touch" in retire, (
        "the retirement step must explicitly protect .hitl/skip-ledger.yaml")
    assert not re.search(r"rm\b[^\n]*skip-ledger", retire), (
        "the retirement step deletes the durable ledger — CR-10 violation")
