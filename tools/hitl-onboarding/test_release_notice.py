"""Tests for the release notice opt-in (#116).

The load-bearing cases are the consent ones: nothing is posted without a recorded yes and an
explicit confirmation, the comment is the version and nothing else, nobody is asked twice, a
logged-out gh records nothing, and the user file never carries a handle.

Every gh call goes through a fake runner; no test touches the network or the real home directory.
"""
import io
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import release_notice as rn  # noqa: E402

SCRIPT = os.path.join(HERE, "release_notice.py")
DISCUSSION_JSON = '{"data":{"repository":{"discussion":{"id":"D_resolved"}}}}'
COMMENT_JSON = '{"data":{"addDiscussionComment":{"comment":{"url":"https://github.com/x/discussions/36#c1"}}}}'


class FakeGh:
    """Records every call; answers by the first argument."""

    def __init__(self, logged_in=True, graphql_ok=True, star_ok=True):
        self.calls = []
        self.logged_in = logged_in
        self.graphql_ok = graphql_ok
        self.star_ok = star_ok

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        if args[:2] == ["auth", "status"]:
            return (0, "logged in", "") if self.logged_in else (1, "", "not logged in")
        if args[:2] == ["api", "graphql"]:
            if not self.graphql_ok:
                return 1, "", "graphql failed"
            query = next(a for a in args if a.startswith("query="))
            return 0, (COMMENT_JSON if query.startswith("query=mutation") else DISCUSSION_JSON), ""
        if args[:3] == ["api", "-X", "PUT"]:
            return (0, "", "") if self.star_ok else (1, "", "403")
        raise AssertionError("unexpected gh call: %s" % args)

    @property
    def mutations(self):
        return [c for c in self.calls if c[:2] == ["api", "graphql"]
                and any(a.startswith("query=mutation") for a in c)]

    @property
    def stars(self):
        return [c for c in self.calls if c[:3] == ["api", "-X", "PUT"]]


def run(argv, gh=None, home=None):
    lines = []
    code = rn.main(["--home", str(home), "--today", "2026-09-15"] + argv, gh=gh or FakeGh(), out=lines.append)
    return code, "\n".join(lines)


def record(home, notice="yes", star="no"):
    return run(["record", "--notice", notice, "--star", star, "--version", "2.13.0"], home=home)


# ── consent ──────────────────────────────────────────────────────────────────────────────────────

def test_post_refuses_without_a_recorded_yes(tmp_path):
    gh = FakeGh()
    code, out = run(["post", "--confirmed", "--version", "2.13.0"], gh, tmp_path)
    assert code == 2 and "no recorded yes" in out
    assert gh.mutations == [], "nothing may be posted without a recorded yes"


def test_post_refuses_when_the_recorded_answer_is_no(tmp_path):
    record(tmp_path, notice="no")
    gh = FakeGh()
    code, _ = run(["post", "--confirmed", "--version", "2.13.0"], gh, tmp_path)
    assert code == 2 and gh.mutations == []


def test_post_refuses_without_confirmation(tmp_path):
    record(tmp_path, notice="yes")
    gh = FakeGh()
    code, out = run(["post", "--version", "2.13.0"], gh, tmp_path)
    assert code == 2 and "--confirmed" in out
    assert gh.mutations == []


def test_post_refuses_when_the_version_is_unknown(tmp_path, monkeypatch):
    record(tmp_path, notice="yes")
    monkeypatch.setattr(rn, "installed_version", lambda *a, **k: None)
    gh = FakeGh()
    code, out = run(["post", "--confirmed"], gh, tmp_path)
    assert code == 2 and gh.mutations == [], out


def test_star_refuses_without_a_recorded_yes_or_confirmation(tmp_path):
    gh = FakeGh()
    assert run(["star", "--confirmed"], gh, tmp_path)[0] == 2
    record(tmp_path, notice="no", star="yes")
    assert run(["star"], gh, tmp_path)[0] == 2
    assert gh.stars == []


# ── the comment ──────────────────────────────────────────────────────────────────────────────────

def test_the_body_is_exactly_hitl_and_the_version():
    assert rn.comment_body("2.13.0") == "HITL 2.13.0"


def test_body_mode_prints_the_exact_comment(tmp_path):
    code, out = run(["body", "--version", "2.13.0"], home=tmp_path)
    assert code == 0 and out == "HITL 2.13.0"


def test_post_sends_exactly_the_body_to_the_thread_resolved_by_number(tmp_path):
    record(tmp_path, notice="yes")
    gh = FakeGh()
    code, out = run(["post", "--confirmed", "--version", "2.13.0"], gh, tmp_path)
    assert code == 0, out
    lookup = [c for c in gh.calls if c[:2] == ["api", "graphql"]][0]
    assert "number=%d" % rn.THREAD_NUMBER in lookup and "owner=pappar" in lookup
    assert "name=hitl-claude-plugin" in lookup
    assert len(gh.mutations) == 1
    m = gh.mutations[0]
    assert "body=HITL 2.13.0" in m, m
    assert "id=D_resolved" in m, "the id resolved at runtime is used, not the fallback"
    assert "addDiscussionComment" in next(a for a in m if a.startswith("query="))
    assert "#c1" in out


def test_post_falls_back_to_the_recorded_id_when_the_lookup_fails(tmp_path):
    record(tmp_path, notice="yes")

    class Gh(FakeGh):
        def __call__(self, args):
            if args[:2] == ["api", "graphql"] and not any(a.startswith("query=mutation") for a in args):
                self.calls.append(list(args))
                return 1, "", "boom"
            return FakeGh.__call__(self, args)

    gh = Gh()
    code, _ = run(["post", "--confirmed", "--version", "2.13.0"], gh, tmp_path)
    assert code == 0
    assert "id=" + rn.THREAD_ID_FALLBACK in gh.mutations[0]


def test_a_failed_post_says_how_to_do_it_by_hand(tmp_path):
    record(tmp_path, notice="yes")
    gh = FakeGh(graphql_ok=False)
    code, out = run(["post", "--confirmed", "--version", "2.13.0"], gh, tmp_path)
    assert code == 1 and "HITL 2.13.0" in out and rn.THREAD_URL in out


def test_the_comment_carries_no_repo_name_email_or_handle(tmp_path):
    body = rn.comment_body("2.13.0")
    assert "@" not in body and "/" not in body and body.split() == ["HITL", "2.13.0"]


# ── asked once ───────────────────────────────────────────────────────────────────────────────────

def test_state_asks_when_nothing_is_recorded_and_gh_is_logged_in(tmp_path):
    code, out = run(["state"], FakeGh(), tmp_path)
    assert code == 0 and out.splitlines()[0] == "ask"
    assert rn.NOTICE_QUESTION in out and rn.STAR_QUESTION in out


def test_a_recorded_answer_means_state_says_already_answered(tmp_path):
    record(tmp_path, notice="no")
    gh = FakeGh()
    code, out = run(["state"], gh, tmp_path)
    assert code == 0 and out.splitlines()[0] == "already-answered"
    assert rn.NOTICE_QUESTION not in out
    assert gh.calls == [], "an answered person costs no gh call"


def test_no_is_a_complete_answer_and_is_never_revisited(tmp_path):
    record(tmp_path, notice="no", star="no")
    code, out = run(["record", "--notice", "yes", "--star", "yes", "--version", "9.9.9"], home=tmp_path)
    assert code == 0 and "already recorded" in out
    assert rn.load_record(str(tmp_path))["release_notice"] == "no"
    assert rn.load_record(str(tmp_path))["version_at_ask"] == "2.13.0"


def test_logged_out_means_skipped_and_nothing_recorded(tmp_path):
    code, out = run(["state"], FakeGh(logged_in=False), tmp_path)
    assert code == 0 and out.splitlines()[0] == "gh-logged-out"
    assert "asked next time" in out
    assert not os.path.exists(rn.user_file(str(tmp_path)))
    assert rn.load_record(str(tmp_path)) == {}
    # And the next run, logged in, asks.
    assert run(["state"], FakeGh(), tmp_path)[1].splitlines()[0] == "ask"


# ── the user file ────────────────────────────────────────────────────────────────────────────────

def test_the_user_file_schema_has_no_handle_login_or_email():
    for field in rn.USER_FILE_FIELDS:
        for banned in ("handle", "login", "email", "user", "name", "org", "repo"):
            assert banned not in field, field
    assert rn.USER_FILE_FIELDS == ("release_notice", "star", "asked_at", "version_at_ask")


def test_no_handle_is_ever_written_to_the_user_file(tmp_path):
    record(tmp_path, notice="yes", star="yes")
    text = io.open(rn.user_file(str(tmp_path)), encoding="utf-8").read()
    body = "\n".join(l for l in text.splitlines() if not l.startswith("#"))
    keys = [l.split(":")[0] for l in body.splitlines() if l.strip()]
    assert keys == list(rn.USER_FILE_FIELDS), keys
    for banned in ("handle", "login", "email", "@", "pappar", "hitl-claude-plugin"):
        assert banned not in body, "%r in the user file" % banned


def test_the_script_never_asks_gh_who_the_user_is():
    src = io.open(SCRIPT, encoding="utf-8").read()
    assert "viewer" not in src and '"user"' not in src and "api/user\"" not in src
    assert "/user/starred/" in src, "the star call is the only /user path"


def test_the_home_env_override_is_honoured(tmp_path, monkeypatch):
    monkeypatch.setenv(rn.HOME_ENV, str(tmp_path / "elsewhere"))
    assert rn.user_file() == str(tmp_path / "elsewhere" / rn.USER_FILE_NAME)
    monkeypatch.delenv(rn.HOME_ENV)
    assert rn.user_file().startswith(os.path.expanduser("~"))


# ── the star ─────────────────────────────────────────────────────────────────────────────────────

def test_star_puts_the_users_star_on_the_plugin_repo(tmp_path):
    record(tmp_path, notice="no", star="yes")
    gh = FakeGh()
    code, out = run(["star", "--confirmed"], gh, tmp_path)
    assert code == 0 and gh.stars == [["api", "-X", "PUT", "/user/starred/pappar/hitl-claude-plugin"]]
    assert "undoes it" in out


# ── the share line ───────────────────────────────────────────────────────────────────────────────

def test_share_line_has_the_install_commands_and_the_walkthrough():
    assert "claude plugin marketplace add pappar/hitl-claude-plugin" in rn.SHARE_LINE
    assert "claude plugin install hitl@hitl" in rn.SHARE_LINE
    assert rn.WALKTHROUGH_URL in rn.SHARE_LINE
    assert rn.SHARE_LINE.startswith("If HITL helped, this is what to send someone:")


def test_the_retro_share_line_prints_once_per_project_and_then_never(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    code, out = run(["share-line-retro", "--change", "GH-1", "--project", str(proj)], home=tmp_path)
    assert code == 0 and out == rn.SHARE_LINE
    cfg = io.open(str(proj / ".hitl" / "config.yaml"), encoding="utf-8").read()
    assert "shown_in_retro: GH-1" in cfg and "shown_at: 2026-09-15" in cfg
    for _ in range(2):
        code, out = run(["share-line-retro", "--change", "GH-2", "--project", str(proj)], home=tmp_path)
        assert code == 0 and out == "", "the second retrospective prints nothing"
    assert "GH-2" not in io.open(str(proj / ".hitl" / "config.yaml"), encoding="utf-8").read()


def test_the_retro_share_line_keeps_other_project_config(tmp_path):
    proj = tmp_path / "proj"
    (proj / ".hitl").mkdir(parents=True)
    (proj / ".hitl" / "config.yaml").write_text("team: payments\nlimits:\n  tier: 2\n", encoding="utf-8")
    run(["share-line-retro", "--change", "GH-1", "--project", str(proj)], home=tmp_path)
    cfg = rn._load_yaml(str(proj / ".hitl" / "config.yaml"))
    assert cfg["team"] == "payments" and cfg["limits"] == {"tier": "2"}
    assert cfg["share_line"]["shown_in_retro"] == "GH-1"


def test_the_project_file_carries_no_personal_data(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    record(tmp_path, notice="yes", star="yes")
    run(["share-line-retro", "--change", "GH-1", "--project", str(proj)], home=tmp_path)
    cfg = io.open(str(proj / ".hitl" / "config.yaml"), encoding="utf-8").read()
    assert "release_notice" not in cfg and "star" not in cfg and "@" not in cfg


# ── the version, the way dev-update reads it ─────────────────────────────────────────────────────

def test_installed_version_reads_installed_plugins_json_then_settings(tmp_path):
    plugins = tmp_path / "installed_plugins.json"
    settings = tmp_path / "settings.json"
    plugins.write_text('{"plugins":{"hitl@hitl":[{"version":"2.13.0","installPath":"/x"}]}}', encoding="utf-8")
    assert rn.installed_version(str(plugins), str(settings)) == "2.13.0"
    plugins.unlink()
    root = tmp_path / "plug"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"version":"2.12.1"}', encoding="utf-8")
    settings.write_text('{"plugins":[{"path":"%s"}]}' % root, encoding="utf-8")
    assert rn.installed_version(str(plugins), str(settings)) == "2.12.1"
    settings.unlink()
    assert rn.installed_version(str(plugins), str(settings)) is None


# ── the cli ──────────────────────────────────────────────────────────────────────────────────────

def test_cli_post_refuses_and_exits_2_without_touching_gh(tmp_path):
    """The real entry point, with the real runner. No record exists, so gh is never reached."""
    p = subprocess.run([sys.executable, SCRIPT, "--home", str(tmp_path), "post", "--confirmed",
                        "--version", "2.13.0"], capture_output=True, text=True)
    assert p.returncode == 2 and "Nothing was sent" in p.stdout


def test_cli_record_writes_the_user_file_under_home(tmp_path):
    p = subprocess.run([sys.executable, SCRIPT, "--home", str(tmp_path), "record", "--notice", "no",
                        "--star", "skipped", "--version", "2.13.0"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert rn.load_record(str(tmp_path)) == {"release_notice": "no", "star": "skipped",
                                             "asked_at": rn.datetime.date.today().isoformat(),
                                             "version_at_ask": "2.13.0"}


def test_cli_rejects_an_answer_outside_the_choices(tmp_path):
    p = subprocess.run([sys.executable, SCRIPT, "--home", str(tmp_path), "record", "--notice", "maybe",
                        "--star", "no"], capture_output=True, text=True)
    assert p.returncode == 2 and not os.path.exists(rn.user_file(str(tmp_path)))


@pytest.mark.parametrize("text", [rn.NOTICE_QUESTION, rn.STAR_QUESTION, rn.SHARE_LINE])
def test_what_people_read_is_plain(text):
    assert "—" not in text, "no em dashes in what a person reads"
    assert "default no" in text or text is rn.SHARE_LINE
