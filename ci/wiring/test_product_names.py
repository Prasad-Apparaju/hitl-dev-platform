"""The light path has one name, written one way, wherever people read it (#125).

Fast Track and Full Scale are the two sizes intake offers. They are product names: people ask for
them by name, so they are capitalized, and a different spelling each time is how a name stops being
findable. "First Pass" was the old user-facing name; it stays as the internal name for the skip
record and its validator, and must not reach people.

Two rules, over the surfaces that reach people:

  casing   "fast track" / "full scale" in any other casing or hyphenated fails. Scanned in every
           markdown file under ai/ (skill prose included: the model copies the casing it is given
           into what it says, so the Step 4 menu comes out however start-change writes it), every
           hook, and the whole-file surfaces below.
  retired  "First Pass" fails in the whole-file surfaces, in what hooks say, and in what skills tell
           the model to print or say: echo/printf strings, blockquotes, `Say:` lines, and bare fenced
           blocks (example output, which the plain-English lint skips). A line saying what it used
           to be called ("then called First Pass") is allowed, so the history stays explicable.

#126 replaces this with a check driven by a names list; these two names become its first entries.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AI = os.path.join(ROOT, "ai")
HOOKS = os.path.join(AI, "claude", "hooks")

# Files where every line reaches a person.
WHOLE_FILE = [
    "ai/shared/templates/claude-md-hitl-block.md",
    "docs/getting-started.md",
    "site/getting-started.html",
    "site/index.html",
    "docs/announcements/first-pass.md",
    "docs/announcements/release-notes-recent-features.md",
    "docs/examples/first-pass/README.md",
]

NAMES = {"Fast Track": re.compile(r"\bfast[ -]track\b", re.I),
         "Full Scale": re.compile(r"\bfull[ -]scale\b", re.I)}
RETIRED = re.compile(r"\bfirst pass\b", re.I)
RETIRED_OK = re.compile(r"\bcalled First Pass\b")

# Link targets, anchors and inline code are addresses, not names: `#fast-track-the-fewest-steps`.
_ADDRESSES = re.compile(r"\]\([^)]*\)|href=\"[^\"]*\"|id=\"[^\"]*\"|`[^`]*`")


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _casing_errors(line):
    text = _ADDRESSES.sub("", line)
    return ["%r should be %r" % (m.group(0), name)
            for name, rx in NAMES.items() for m in rx.finditer(text) if m.group(0) != name]


def _retired(line):
    return bool(RETIRED.search(_ADDRESSES.sub("", line))) and not RETIRED_OK.search(line)


def _ai_markdown():
    for base, _dirs, files in os.walk(AI):
        for f in files:
            if f.endswith(".md"):
                yield os.path.relpath(os.path.join(base, f), ROOT)


def _hook_lines(rel):
    """A hook's non-comment lines: what it prints, including Python heredoc strings.

    Whole-line comments are dropped, and so is a trailing ` # comment` (awk and shell both use it).
    """
    for n, line in enumerate(_read(rel).splitlines(), 1):
        if not line.strip().startswith("#"):
            yield n, re.sub(r"\s#\s.*$", "", line)


def _spoken_skill_lines(rel):
    """What a skill tells the model to print or say to a person."""
    fence = None
    for n, line in enumerate(_read(rel).splitlines(), 1):
        t = line.strip()
        if t.startswith("```"):
            fence = None if fence is not None else t[3:].strip()
            continue
        if fence is not None:
            if fence == "":                                   # bare fence: example output
                yield n, line
            elif re.search(r"\b(echo|printf)\b", t):          # code: only what it prints
                for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', t):
                    yield n, lit
            continue
        if t.startswith(">"):
            yield n, line
        for said in re.findall(r'Say:\s*"([^"]*)"', line):
            yield n, said


# ── casing ───────────────────────────────────────────────────────────────────────────────────────

def test_the_names_are_capitalized_in_everything_under_ai():
    bad = ["%s:%d %s" % (rel, n, "; ".join(_casing_errors(l)))
           for rel in _ai_markdown()
           for n, l in enumerate(_read(rel).splitlines(), 1) if _casing_errors(l)]
    bad += ["%s:%d %s" % (rel, n, "; ".join(_casing_errors(l)))
            for rel in (os.path.relpath(os.path.join(HOOKS, f), ROOT) for f in sorted(os.listdir(HOOKS)))
            if rel.endswith(".sh")
            for n, l in _hook_lines(rel) if _casing_errors(l)]
    assert not bad, "write the names as Fast Track / Full Scale:\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("rel", WHOLE_FILE)
def test_the_names_are_capitalized_where_people_read(rel):
    bad = ["%d: %s" % (n, "; ".join(_casing_errors(l)))
           for n, l in enumerate(_read(rel).splitlines(), 1) if _casing_errors(l)]
    assert not bad, "%s:\n  %s" % (rel, "\n  ".join(bad))


# ── the retired name ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("rel", WHOLE_FILE)
def test_first_pass_does_not_reach_people_in_the_docs(rel):
    bad = ["%d: %s" % (n, l.strip()[:90]) for n, l in enumerate(_read(rel).splitlines(), 1) if _retired(l)]
    assert not bad, "%s still says First Pass (it's Fast Track now):\n  %s" % (rel, "\n  ".join(bad))


def test_first_pass_is_not_what_hooks_say():
    bad = ["%s:%d %s" % (f, n, l.strip()[:90])
           for f in sorted(os.listdir(HOOKS)) if f.endswith(".sh")
           for n, l in _hook_lines(os.path.relpath(os.path.join(HOOKS, f), ROOT)) if _retired(l)]
    assert not bad, "hooks still say First Pass:\n  " + "\n  ".join(bad)


def test_first_pass_is_not_what_skills_tell_the_model_to_say():
    bad = ["%s:%d %s" % (rel, n, l.strip()[:90])
           for rel in _ai_markdown() for n, l in _spoken_skill_lines(rel) if _retired(l)]
    assert not bad, "skills still have people told First Pass:\n  " + "\n  ".join(bad)


# ── the promise, where people look ───────────────────────────────────────────────────────────────

PROMISE = [
    "your goal in one sentence and what done looks like",
    "fewest steps that get you there",
    '"Fast Track" at any point during intake',   # after intake, switching means restarting it
    "The failing test and making it pass always stay",
    "deploy, promote and the retrospective are only dropped if someone accepts the risk by name",
]


def _missing_promise(text):
    flat = re.sub(r"\s+", " ", text.replace("*", "")).lower()
    return [p for p in PROMISE if p.lower() not in flat]


def test_the_claude_md_block_carries_the_promise():
    missing = _missing_promise(_read("ai/shared/templates/claude-md-hitl-block.md"))
    assert not missing, "the CLAUDE.md block lost: %s" % missing


def test_the_banner_relay_carries_the_promise():
    """The paragraph Claude relays when it introduces HITL (#125: people only hear it through Claude)."""
    src = _read("ai/claude/hooks/_steps.sh")
    missing = _missing_promise(src[src.index("hitl_intake_directive() {"):src.index("DIRECTIVE\n}")])
    assert not missing, "the banner relay paragraph lost: %s" % missing


# ── the check itself ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("line,errors", [
    ("pick fast track", 1), ("Fast track", 1), ("FAST TRACK", 1), ("a fast-track change", 1),
    ("full scale instead", 1), ("Fast Track or Full Scale", 0),
    ("see [Fast Track](#fast-track-the-fewest-steps)", 0), ('<a href="#fast-track">x</a>', 0),
    ("the `fast` key", 0), ("fastidious tracking", 0),
])
def test_the_casing_rule(line, errors):
    assert len(_casing_errors(line)) == errors, (line, _casing_errors(line))


@pytest.mark.parametrize("line,flagged", [
    ("run First Pass", True), ("a first pass at v1", True),
    ("In 2.4.0 this was a mode you had to ask for, then called First Pass", False),
    ("`ci/first-pass/check_skips.py`", False), ("[example](../examples/first-pass/README.md)", False),
    ("first_pass: true", False),
])
def test_the_retired_rule(line, flagged):
    assert _retired(line) is flagged, line


def test_a_trailing_hook_comment_is_not_spoken(tmp_path, monkeypatch):
    hook = tmp_path / "h.sh"
    hook.write_text('glyph="x"      # First Pass: internal\necho "First Pass on"\n# First Pass\n')
    monkeypatch.setattr(sys.modules[__name__], "ROOT", str(tmp_path))
    assert [l for _n, l in _hook_lines("h.sh") if _retired(l)] == ['echo "First Pass on"']


def test_example_output_in_a_bare_fence_is_spoken_but_bash_comments_are_not(tmp_path, monkeypatch):
    skill = tmp_path / "ai" / "x.md"
    skill.parent.mkdir()
    skill.write_text('```\n  First Pass   3 steps\n```\n```bash\n# First Pass internals\n'
                     'echo "First Pass installed"\n```\n> Say First Pass\n8. Say: "the First Pass file"\n')
    monkeypatch.setattr(sys.modules[__name__], "ROOT", str(tmp_path))
    spoken = [l for _n, l in _spoken_skill_lines("ai/x.md")]
    assert spoken == ["  First Pass   3 steps", "First Pass installed", "> Say First Pass",
                      "the First Pass file"], spoken
