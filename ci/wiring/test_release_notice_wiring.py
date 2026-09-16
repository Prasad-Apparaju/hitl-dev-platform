"""The release-notice opt-in is wired where it belongs and held out of everywhere else (#116).

Four skills ask, through one script: the three onboarding skills at their completion step and
`dev-update` for projects onboarded earlier. The question says the default is no and that the
comment is shown before it is posted. The share line appears in the three closing messages and
once in the retrospective, and never in a hook, the breadcrumb, the statusline or the gate. The
user file the answers land in has no field that could name a person.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AI = os.path.join(ROOT, "ai")
HOOKS = os.path.join(AI, "claude", "hooks")

sys.path.insert(0, os.path.join(ROOT, "tools", "hitl-onboarding"))
import release_notice as rn  # noqa: E402

ONBOARDING = ["ai/claude/start-brownfield/SKILL.md", "ai/claude/start-from-prd/SKILL.md",
              "ai/claude/start-migration/SKILL.md"]
UPDATE = "ai/claude/update/SKILL.md"
RETRO = "ai/claude/retro/SKILL.md"
ASKING = ONBOARDING + [UPDATE]

INSTALL_LINE = "claude plugin marketplace add pappar/hitl-claude-plugin"
SHARE_SENTENCE = "If HITL helped, this is what to send someone:"
NEVER_HERE = ["hitl-gate.sh", "statusline-hitl.sh", "welcome.sh", "_steps.sh"]


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# ── the four skills ask through the one script ───────────────────────────────────────────────────

@pytest.mark.parametrize("rel", ASKING)
def test_the_skill_runs_the_script_from_the_plugin(rel):
    text = _read(rel)
    assert "shared/tools/hitl-onboarding/release_notice.py" in text, "%s does not run release_notice.py" % rel
    assert re.search(r'python3 "\$RN" state', text), "%s never asks the script whether to ask" % rel
    for mode in ("record --notice", "body", "post --confirmed", "star --confirmed"):
        assert mode in text, "%s never runs `%s`" % (rel, mode)


@pytest.mark.parametrize("rel", ASKING)
def test_the_skill_records_before_it_posts_and_shows_the_body_first(rel):
    text = _read(rel)
    i_state, i_record = text.index('"$RN" state'), text.index("record --notice")
    i_body, i_post = text.index('"$RN" body'), text.index("post --confirmed")
    assert i_state < i_record < i_body < i_post, "%s: order must be state, record, body, post" % rel
    assert "only then" in text[i_body:i_post], "%s: the comment must be shown before it is posted" % rel


@pytest.mark.parametrize("rel", ONBOARDING)
def test_onboarding_asks_at_the_completion_step_not_step_0(rel):
    text = _read(rel)
    step0 = text.index("## Step 0")
    step1 = text.index("## Step 1")
    assert "release_notice.py" not in text[step0:step1], "%s asks in Step 0; it belongs at completion" % rel
    assert text.index("release_notice.py") < text.index("Output this exactly:"), (
        "%s must ask before the closing message" % rel)


def test_dev_update_asks_after_step_4_9_and_before_step_5():
    text = _read(UPDATE)
    assert text.index("## Step 4.9") < text.index("## Step 4.10") < text.index("## Step 5"), (
        "Step 4.10 is not between 4.9 and 5")
    assert "release_notice.py" in text[text.index("## Step 4.10"):text.index("## Step 5")]


# ── the question text holds the consent rule ─────────────────────────────────────────────────────

def test_the_question_says_the_default_is_no():
    assert "default no" in rn.NOTICE_QUESTION
    assert "default no" in rn.STAR_QUESTION


def test_the_question_says_the_comment_is_shown_before_it_is_posted():
    assert "you see it before it is posted" in rn.NOTICE_QUESTION


def test_the_question_says_what_the_comment_is_and_how_to_leave():
    q = rn.NOTICE_QUESTION
    assert "version number only" in q and "HITL 2.13.0" in q
    assert "handle" in q and "date" in q, "the person must know GitHub shows both"
    assert "delete the comment or unsubscribe" in q
    assert "maintained by one person" in q


def test_the_skills_say_an_empty_answer_is_no():
    for rel in ASKING:
        assert "An empty answer is no" in _read(rel), rel


def test_the_state_output_is_relayed_word_for_word():
    for rel in ASKING:
        assert "word for\nword" in _read(rel) or "word for word" in _read(rel), rel


# ── the share line: three closing messages and one retrospective ─────────────────────────────────

@pytest.mark.parametrize("rel", ONBOARDING)
def test_the_closing_message_ends_with_the_share_line(rel):
    text = _read(rel)
    closing = text[text.index("Output this exactly:"):]
    assert SHARE_SENTENCE in closing, "%s closing message has no share line" % rel
    assert INSTALL_LINE in closing and "claude plugin install hitl@hitl" in closing
    assert rn.WALKTHROUGH_URL in closing
    assert text.count(SHARE_SENTENCE) == 1, "%s: the share line is shown once" % rel


def test_the_share_line_in_the_skills_is_the_scripts_share_line():
    for rel in ONBOARDING:
        assert rn.SHARE_LINE in _read(rel), "%s: the closing message and the script differ" % rel


def test_the_retro_shows_the_share_line_once_and_only_when_done():
    text = _read(RETRO)
    step4 = text[text.index("## Step 4"):text.index("## Step 5")]
    assert "share-line-retro --change" in step4
    assert "status: merged" in step4, "the retro must gate the line on the change reaching done"
    assert "shown, not asked" in step4
    assert "prints nothing" in step4


def test_dev_update_has_no_share_line():
    text = _read(UPDATE)
    assert SHARE_SENTENCE not in text
    assert "no share line here" in text


# ── held out of every hook, the breadcrumb, the statusline and the gate ─────────────────────────

def test_the_share_line_is_in_no_hook():
    bad = []
    for f in sorted(os.listdir(HOOKS)):
        text = _read(os.path.relpath(os.path.join(HOOKS, f), ROOT))
        for needle in (INSTALL_LINE, SHARE_SENTENCE, rn.WALKTHROUGH_URL, "release_notice"):
            if needle in text:
                bad.append("%s: %s" % (f, needle))
    assert not bad, "the share line leaked into a hook:\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("hook", NEVER_HERE)
def test_the_named_surfaces_exist_and_carry_nothing(hook):
    path = os.path.join(HOOKS, hook)
    assert os.path.isfile(path), "%s moved; this check went blind" % hook
    text = _read(os.path.relpath(path, ROOT))
    assert INSTALL_LINE not in text and SHARE_SENTENCE not in text and "discussions/36" not in text


def test_no_hook_talks_to_the_discussion_thread():
    for f in sorted(os.listdir(HOOKS)):
        text = _read(os.path.relpath(os.path.join(HOOKS, f), ROOT))
        assert "addDiscussionComment" not in text and rn.THREAD_URL not in text, f


# ── the user file names nobody ───────────────────────────────────────────────────────────────────

def test_the_recorded_user_file_schema_has_no_handle_login_or_email():
    fields = rn.USER_FILE_FIELDS
    for banned in ("handle", "login", "email", "user", "name", "org", "repo"):
        assert not any(banned in f for f in fields), (banned, fields)
    assert set(fields) == {"release_notice", "star", "asked_at", "version_at_ask"}


def test_the_user_file_is_per_person_not_per_project():
    assert rn.USER_FILE_NAME == "release-notice.yaml"
    assert rn.user_dir("/x") == "/x"
    assert rn.user_dir().startswith(os.path.expanduser("~")) or os.environ.get(rn.HOME_ENV)
    assert rn.PROJECT_FILE == os.path.join(".hitl", "config.yaml")
    assert rn.PROJECT_KEY == "share_line"


# ── the pointers ─────────────────────────────────────────────────────────────────────────────────

def test_the_docs_point_at_the_thread():
    assert rn.THREAD_URL in _read("docs/getting-started.md")
    assert rn.THREAD_URL in _read("docs/releasing.md")
    assert SHARE_SENTENCE not in _read("docs/getting-started.md"), "no share wording in the docs"
