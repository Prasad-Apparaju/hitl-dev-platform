"""Anthropic's skill authoring guide, held as tests so the 2026-10-06 cleanup does not regrow (#151).

- A SKILL.md body stays under 500 lines (skill-lint) and, for the skills that run long workflows,
  under about 5,000 tokens, because Claude Code re-attaches only the first 5,000 tokens of an
  invoked skill after compaction.
- Skill bodies carry rules, not history: issue numbers, version lessons and review-round
  references belong in CHANGELOG and docs/design/, not in what the model reads every run.
- A reference file over 100 lines has a contents list at the top, so a partial read can still
  find its section.
- Descriptions are third person and within the listing limit.

Run: python3 -m pytest ci/wiring/test_skill_guide.py -q
"""
import glob
import io
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SKILLS = sorted(glob.glob(os.path.join(ROOT, "ai", "claude", "**", "SKILL.md"), recursive=True))

# Skills whose body must survive compaction re-attachment whole: long, multi-step, stateful.
LONG_WORKFLOWS = ("start-change", "start-brownfield", "start-from-prd", "start-migration", "update",
                  "architect/design-feature", "architect/design-system", "tdd")
TOKEN_CEILING = 5500          # chars / 4 overestimates code-heavy bodies; a hair above the 5,000-token re-attach
HISTORY = re.compile(r"(?<![A-Za-z])#\d{2,3}\b|codex-\d|\bround[- ]\d|\b2\.\d+\.\d+\b(?!\s*or later)|plugin issue")
HISTORY_CEILING = 3           # a skill may name a version it checks at runtime, not tell its story


def _split(path):
    s = io.open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", s, re.S)
    return (m.group(1), s[m.end():]) if m else ("", s)


def _rel(path):
    return os.path.relpath(path, os.path.join(ROOT, "ai", "claude"))


@pytest.mark.parametrize("path", SKILLS, ids=_rel)
def test_long_workflow_skills_fit_the_compaction_reattach(path):
    rel = _rel(path)
    if not any(rel.startswith(k) for k in LONG_WORKFLOWS):
        pytest.skip("not a long-workflow skill")
    _, body = _split(path)
    tokens = len(body) // 4
    assert tokens <= TOKEN_CEILING, (
        "%s body is about %d tokens; only the first 5,000 come back after compaction, so move step "
        "detail into a reference file beside SKILL.md" % (rel, tokens))


@pytest.mark.parametrize("path", SKILLS, ids=_rel)
def test_skill_bodies_carry_rules_not_history(path):
    _, body = _split(path)
    # bash fences and their comments may cite a version; prose may not tell the story
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    hits = HISTORY.findall(prose)
    assert len(hits) <= HISTORY_CEILING, (
        "%s cites history %d times in prose (%s); keep the rule, drop the story (CHANGELOG and "
        "docs/design keep it)" % (_rel(path), len(hits), ", ".join(hits[:6])))


def test_reference_files_over_100_lines_have_a_contents_list():
    refs = [p for p in glob.glob(os.path.join(ROOT, "ai", "shared", "*.md"))]
    refs += [p for p in glob.glob(os.path.join(ROOT, "ai", "claude", "**", "*.md"), recursive=True)
             if not p.endswith("SKILL.md") and "/templates/" not in p and "/agents/" not in p
             and "/plugin/" not in p and "/hooks/" not in p]
    missing = []
    for p in refs:
        s = io.open(path := p, encoding="utf-8").read()
        if s.count("\n") > 100 and not re.search(r"^## Contents", s, re.M):
            missing.append(os.path.relpath(p, ROOT))
    assert not missing, "reference files over 100 lines with no '## Contents' list: " + ", ".join(missing)


@pytest.mark.parametrize("path", SKILLS, ids=_rel)
def test_description_is_third_person_and_within_the_listing_limit(path):
    fm, _ = _split(path)
    m = re.search(r"^description:\s*(.*)$", fm, re.M)
    desc = (m.group(1).strip().strip("\"'") if m else "")
    assert desc, "%s has no description" % _rel(path)
    assert len(desc) <= 1024, "%s description is %d chars; the platform limit is 1,024" % (_rel(path), len(desc))
    assert not re.search(r"\b(I can|I will|I'll|you can use this)\b", desc, re.I), \
        "%s description is not third person" % _rel(path)
