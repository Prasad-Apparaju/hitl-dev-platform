"""The text HITL ships to people is plain English (ai/shared/plain-english.md).

Four surfaces speak to a person: hook and breadcrumb messages, the lines a skill tells the model to
say (blockquotes), the document templates, and the preferences block written into CLAUDE.md. Each
is scanned for the marks in the rule's table. The skills' own instructions to the model are not
scanned: they are read by a model, not a person, and the rule is about what reaches people.
"""
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AI = os.path.join(ROOT, "ai")
HOOKS = os.path.join(AI, "claude", "hooks")

# The words. Each is a regex, matched case-insensitively on word boundaries.
TELLS = [
    r"it'?s worth noting",
    r"\bgreat question\b", r"\bcertainly\b", r"\babsolutely\b",
    r"i'?d be happy to", r"\bhappy to help\b", r"\bfeel free to\b", r"\blet me know if\b",
    r"\bdelve\b", r"\bleverag(e|es|ing)\b", r"\butiliz(e|es|ing)\b", r"\bharness(es|ing)?\b",
    r"\bunlock(s|ing)?\b", r"\bempower(s|ing)?\b", r"\belevat(e|es|ing)\b", r"\bstreamlin(e|es|ing)\b",
    r"\brobust\b", r"\bseamless(ly)?\b", r"\bcomprehensive\b", r"\bcrucial\b", r"\bpivotal\b",
    r"\bgame[- ]changer\b", r"\bnot just \w+(\s\w+){0,4} but (also )?\b", r"in today'?s",
    r"\bmight potentially\b", r"\bcould possibly\b",
]
TELL_RE = re.compile("|".join("(%s)" % t for t in TELLS), re.IGNORECASE)
# Sentence openers: "Note that" and "Importantly" are tells only where they open a sentence; "I'll
# note that we did" is a verb doing its job.
OPENER_RE = re.compile(r'(?:^|[.!?:]\s+|>\s*"?\s*|\*\*\s*)(Note that|Importantly)\b')
EM_DASH = "—"


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _strip_fences(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)


def _marks(line):
    found = []
    if EM_DASH in line:
        found.append("em dash")
    m = TELL_RE.search(line) or OPENER_RE.search(line)
    if m:
        found.append("'%s'" % m.group(0).strip())
    return found


# ── surface 1: what hooks print ──────────────────────────────────────────────────────────────────

def _hook_spoken_lines(path):
    """Lines a hook prints to a person: echo/printf string literals and heredoc bodies.

    Comments are skipped. Variable expansions and printf formats are left in; they carry no words.
    """
    out = []
    in_heredoc = None
    for raw in _read(path).splitlines():
        line = raw.rstrip("\n")
        t = line.strip()
        if in_heredoc:
            if t == in_heredoc:
                in_heredoc = None
            elif t.startswith("#") or not t:
                continue
            elif '"' not in t and re.search(r"^(except|try|if|elif|else|for|while|def|class|import|from|return|with|pass|continue|break)\b|=", t):
                continue  # code with, at most, a trailing comment
            elif re.search(r"\b(append|print|raise|SystemExit|block)\s*\(|^\s*f?\"|=\s*f?\"", t):
                # A Python heredoc: only the string literals are spoken; the rest is code.
                for lit in re.findall(r'f?"((?:[^"\\]|\\.)*)"', t):
                    out.append(lit)
            else:
                out.append(line)
            continue
        if t.startswith("#"):
            continue
        m = re.search(r"<<-?\s*'?([A-Z_]+)'?\s*$", t)
        if m:
            in_heredoc = m.group(1)
            continue
        if re.match(r"^(echo|printf)\b", t) or re.search(r"\b(echo|printf)\s+\"", t):
            for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', t):
                out.append(lit)
    return out


@pytest.mark.parametrize("hook", sorted(f for f in os.listdir(HOOKS) if f.endswith(".sh")))
def test_hook_messages_are_plain_english(hook):
    offenders = ["%s -> %s" % (", ".join(_marks(l)), l.strip()[:90])
                 for l in _hook_spoken_lines(os.path.join(HOOKS, hook)) if _marks(l)]
    assert not offenders, "%s speaks Claudish:\n  %s" % (hook, "\n  ".join(offenders))


# ── surface 2: what skills tell the model to say ─────────────────────────────────────────────────

def _skill_files():
    for base, _dirs, files in os.walk(os.path.join(AI, "claude")):
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(base, f)
    for f in os.listdir(os.path.join(AI, "shared")):
        if f.endswith(".md"):
            yield os.path.join(AI, "shared", f)


def test_the_lines_skills_tell_the_model_to_say_are_plain_english():
    """A blockquote in a skill is the text the model is told to put in front of someone."""
    offenders = []
    for p in _skill_files():
        rel = os.path.relpath(p, ROOT)
        for n, line in enumerate(_strip_fences(_read(p)).splitlines(), 1):
            if line.lstrip().startswith(">") and _marks(line):
                offenders.append("%s:%d %s -> %s" % (rel, n, ", ".join(_marks(line)), line.strip()[:80]))
    assert not offenders, "quoted lines speaking Claudish:\n  " + "\n  ".join(offenders[:40])


# ── surface 3: the document templates ────────────────────────────────────────────────────────────

TEMPLATE_DIRS = (os.path.join(AI, "shared", "templates"), os.path.join(AI, "claude", "generate-docs", "templates"))


def test_document_templates_are_plain_english():
    offenders = []
    for d in TEMPLATE_DIRS:
        for f in sorted(os.listdir(d)):
            if not f.endswith((".md", ".template")):
                continue
            p = os.path.join(d, f)
            for n, line in enumerate(_strip_fences(_read(p)).splitlines(), 1):
                if line.strip().startswith("<!--"):
                    continue
                if _marks(line):
                    offenders.append("%s:%d %s -> %s" % (os.path.relpath(p, ROOT), n, ", ".join(_marks(line)), line.strip()[:80]))
    assert not offenders, "templates speaking Claudish:\n  " + "\n  ".join(offenders[:40])


# ── surface 4: the preferences block written into CLAUDE.md ──────────────────────────────────────

def test_the_preferences_block_is_plain_english():
    body = _read(os.path.join(AI, "claude", "preferences", "SKILL.md"))
    m = re.search(r'BLOCK = """(.*?)"""', body, flags=re.S)
    assert m, "the preferences BLOCK literal moved; this check went blind"
    offenders = ["%s -> %s" % (", ".join(_marks(l)), l.strip()[:80]) for l in m.group(1).splitlines() if _marks(l)]
    assert not offenders, "the block HITL writes into CLAUDE.md speaks Claudish:\n  " + "\n  ".join(offenders)


# ── the rule itself, and the banner that points at it ───────────────────────────────────────────

def test_the_rule_ships_and_the_banner_points_at_it():
    rule = os.path.join(AI, "shared", "plain-english.md")
    assert os.path.isfile(rule), "ai/shared/plain-english.md is missing"
    steps = _read(os.path.join(HOOKS, "_steps.sh"))
    welcome = _read(os.path.join(HOOKS, "welcome.sh"))
    assert "plain-english" in steps, "the intake banner does not point at the rule"
    assert "plain-english" in welcome, "the active-change banner does not point at the rule"
