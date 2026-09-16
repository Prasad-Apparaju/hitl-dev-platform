"""The QA skills stop on a missing PRD, not on a PRD written without `FR-` numbers (#114).

`qa-plan-tests`, `qa-review-tests` and `qa-verify-quality` opened with one precondition that stopped
when `docs/01-product/prd.md` was absent OR had no `FR-` entries in section 5. `FR-` numbering is
what `pm-add-feature` writes, so the second half stopped every brownfield or migration repo whose
PRD predates HITL, at a blocking gate, and told the person to create their first requirement.

These checks hold the split in the skill text: an absent PRD still stops; a PRD with no `FR-`
entries is said in one line, the fallback is named (the acceptance criteria on the issue, which the
packet gate approved against), and the skill continues. The section number is not hardcoded.
"""
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
QA = os.path.join(ROOT, "ai", "claude", "qa")
SKILLS = ["plan-tests", "review-tests", "verify-quality"]

FALLBACK_LINE = "The PRD has no FR- entries, so the acceptance criteria on the issue are used instead."


def _preconditions(skill):
    """The text between the frontmatter and the first rule, where every stop-and-output lives."""
    with open(os.path.join(QA, skill, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    body = text.split("---", 2)[2]
    return body.split("\n---\n", 1)[0]


def _stop_conditions(pre):
    """The clause of each stop sentence: what sits between 'if' and 'stop'."""
    return re.findall(r"if `docs/01-product/prd\.md` (.*?), stop", pre)


@pytest.mark.parametrize("skill", SKILLS)
def test_an_absent_prd_still_stops(skill):
    pre = _preconditions(skill)
    conditions = _stop_conditions(pre)
    assert conditions == ["is absent"], conditions
    assert "No product requirements exist yet" in pre
    assert "/hitl:pm-add-feature" in pre


@pytest.mark.parametrize("skill", SKILLS)
def test_no_fr_entries_alone_does_not_stop(skill):
    pre = _preconditions(skill)
    for clause in _stop_conditions(pre):
        assert "FR-" not in clause, clause
    assert "lists no functional requirements" not in pre
    assert "§" not in pre, "the requirements section number is not hardcoded"
    assert "has no `FR-` entries" in pre and "do not stop" in pre


@pytest.mark.parametrize("skill", SKILLS)
def test_the_gap_is_said_once_and_the_fallback_is_named(skill):
    pre = _preconditions(skill)
    assert "Say so in one line and continue" in pre
    assert "acceptance criteria on the GitHub issue" in pre
    assert "which the packet gate approved against" in pre
    assert FALLBACK_LINE in pre, "the one line the person sees"
    assert "—" not in FALLBACK_LINE


@pytest.mark.parametrize("skill", SKILLS)
def test_step_one_reads_the_issue_when_the_prd_has_no_fr_entries(skill):
    with open(os.path.join(QA, skill, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    step1 = text[text.index("## Step 1"):]
    assert "If the PRD has no `FR-` entries, the acceptance criteria on the issue are the source." in step1
