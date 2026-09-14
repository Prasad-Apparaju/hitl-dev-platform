"""Step 4 shows what Fast Track leaves out, and asks with checkboxes, without being asked.

In a 2.12.1 session a person had to ask to see the steps before they could select or skip any, and
was never shown a checkbox. The skill said the list came "on request" and the menu was prose. These
checks hold the fix in the skill text: the list every time, the plan asked with AskUserQuestion,
and the left-out steps offered as multiSelect boxes.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SKILL = os.path.join(ROOT, "ai", "claude", "start-change", "SKILL.md")


def _step4():
    with open(SKILL, encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("## Step 4 ")
    end = text.index("## Step 5", start) if "## Step 5" in text[start:] else len(text)
    return text[start:end]


def test_left_out_steps_are_listed_every_time():
    s = _step4()
    assert "list what Fast Track leaves out, one step per line, every time" in s
    assert "Do not wait to" in s
    assert "Fast Track leaves out (most consequential first):" in s


def test_plan_is_asked_with_the_question_tool():
    s = _step4()
    assert "AskUserQuestion" in s
    for option in ("Fast Track (Recommended)", "Full Scale", "Pick steps myself"):
        assert option in s, option


def test_left_out_steps_are_checkboxes():
    s = _step4()
    assert "multiSelect" in s
    assert "Add back" in s and "Leave out" in s
    # The tool's limits, so the model does not try twenty boxes or a one-option question.
    assert "sixteen boxes" in s
    assert "at least two" in s
    # A 2.13 sandbox run failed its first call on repeated question text (InputValidationError).
    assert "question texts" in s and "repeat" in s


def test_pick_steps_myself_gets_both_screens():
    s = " ".join(_step4().split())
    # "for Fast Track, the checkboxes" alone read as Fast Track only, leaving Pick without Add back.
    assert "for Fast Track and for Pick steps myself, the checkboxes" in s
    assert 'second checkbox screen** after the "Add back" one' in s


def test_protected_steps_are_never_checkboxes():
    assert "Steps that always stay are never checkboxes" in _step4()


def test_the_list_is_not_only_on_request():
    s = _step4()
    # "on request" survives only for the full ordered plan, never for what is left out.
    for m in re.finditer(r"on request", s):
        line = s[s.rfind("\n", 0, m.start()) + 1:s.find("\n", m.end())]
        assert "full ordered plan" in line, line


def test_fallback_keeps_the_list():
    assert "print the same lists numbered" in " ".join(_step4().split())
