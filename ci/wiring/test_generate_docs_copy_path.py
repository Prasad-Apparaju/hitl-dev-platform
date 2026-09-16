"""The manual skill copy names a real destination (#121).

When `claude/` moved under `ai/` (May 2026) a path rewrite turned the manual-copy destination in
`dev-generate-docs` into `.ai/claude/ai/claude/`, a doubled path that exists nowhere. The migration
guide and the greenfield example carried the same string. The plugin build's source-path guard had
to allowlist it to ship. The destination is the repo's `.claude/`, where Claude Code reads project
skills, hooks and agents.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GENERATE_DOCS = os.path.join(ROOT, "ai", "claude", "generate-docs", "SKILL.md")

DOUBLED = ("ai/claude/ai/claude", ".claude/claude/")


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _shipped_and_read():
    for top in ("ai", "docs"):
        for base, dirs, files in os.walk(os.path.join(ROOT, top)):
            # Session logs are git-ignored operational notes, not something a reader is sent to.
            dirs[:] = [d for d in dirs if d != "session-logs"]
            for f in files:
                if f.endswith((".md", ".yaml", ".yml", ".sh", ".json")):
                    yield os.path.relpath(os.path.join(base, f), ROOT)


def test_generate_docs_copies_skills_into_dot_claude():
    text = _read(os.path.relpath(GENERATE_DOCS, ROOT))
    assert "copy skills to `.claude/` if they don't exist" in text
    assert "`cp -r ai/claude/ <your-repo>/.claude/`" in text


def test_no_doubled_copy_path_reaches_a_reader():
    offenders = ["%s: %s" % (rel, needle)
                 for rel in _shipped_and_read()
                 for needle in DOUBLED if needle in _read(rel)]
    assert not offenders, "\n  ".join(offenders)
