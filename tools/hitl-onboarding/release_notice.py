#!/usr/bin/env python3
"""Release notices, a star, and one share line: opt in once, nothing posted without a yes (#116).

HITL is maintained by one person and has no way to tell users a new version exists. The channel is
one pinned discussion thread on the plugin repo, "Who uses HITL". Anyone who comments on it gets
GitHub's own notification when the maintainer posts a release there. This script gets a person
onto that thread with explicit consent, asks nobody twice, and posts nothing on its own.

The answers belong to a person, not a project, so they live in a user-level file,
`$HITL_HOME/release-notice.yaml` (default `~/.hitl/`). It carries the answers, a date and the
version; never a handle, an email or a repo name. The project file `.hitl/config.yaml` records
only that the share line was shown in a retrospective.

Modes:
    state                      first line: already-answered | gh-logged-out | ask
                               `ask` is followed by the two questions, word for word
    record --notice yes|no --star yes|no|skipped [--version X]
    body   [--version X]       prints the exact comment: `HITL X`
    post   --confirmed [--version X]   refuses without --confirmed and without a recorded yes
    star   --confirmed         refuses without --confirmed and without a recorded yes
    share-line                 prints the share line
    share-line-retro --change <id>     prints it once per project, then never

Every `gh` call goes through one runner so tests never touch the network. Exit codes: 0 done or
nothing to do, 1 a gh call failed, 2 refused (no consent, no confirmation, unknown version).
"""
import argparse
import datetime
import io
import json
import os
import subprocess
import sys

OWNER = "pappar"
REPO = "hitl-claude-plugin"
THREAD_NUMBER = 36
THREAD_TITLE = "Who uses HITL"
THREAD_URL = "https://github.com/%s/%s/discussions/%d" % (OWNER, REPO, THREAD_NUMBER)
# Resolved by number at post time; this is the fallback if the lookup fails.
THREAD_ID_FALLBACK = "D_kwDOScpDp84ApGxb"
WALKTHROUGH_URL = "https://prasad-apparaju.github.io/hitl-dev-platform/"

HOME_ENV = "HITL_HOME"
USER_FILE_NAME = "release-notice.yaml"
# The whole schema of the user file. No handle, no login, no email, no repo: GitHub already shows
# the handle and date on the comment, and this file must not be a second copy of anything.
USER_FILE_FIELDS = ("release_notice", "star", "asked_at", "version_at_ask")
PROJECT_FILE = os.path.join(".hitl", "config.yaml")
PROJECT_KEY = "share_line"

NOTICE_QUESTION = (
    "HITL is maintained by one person. Do you want a note when a new version ships? "
    "Yes posts one comment under your GitHub account on the \"%s\" thread in the plugin repo. "
    "The comment is the version number only, like `HITL 2.13.0`, and you see it before it is "
    "posted. GitHub shows your handle and the date on every comment. You can delete the comment "
    "or unsubscribe at any time. (yes / no, default no)" % THREAD_TITLE)
STAR_QUESTION = (
    "Star the plugin repo so others can find it? Yes stars %s/%s under your account. "
    "One click on GitHub undoes it. (yes / no, default no)" % (OWNER, REPO))

SHARE_LINE = (
    "If HITL helped, this is what to send someone:\n"
    "\n"
    "```\n"
    "claude plugin marketplace add %s/%s\n"
    "claude plugin install hitl@hitl\n"
    "```\n"
    "The walkthrough is at %s" % (OWNER, REPO, WALKTHROUGH_URL))

QUERY_DISCUSSION_ID = (
    "query($owner:String!,$name:String!,$number:Int!){"
    "repository(owner:$owner,name:$name){discussion(number:$number){id}}}")
MUTATION_ADD_COMMENT = (
    "mutation($id:ID!,$body:String!){"
    "addDiscussionComment(input:{discussionId:$id,body:$body}){comment{url}}}")


# ── gh ───────────────────────────────────────────────────────────────────────────────────────────

def run_gh(args):
    """The one place gh is invoked. Returns (exit code, stdout, stderr)."""
    try:
        p = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    except OSError as exc:
        return 127, "", str(exc)
    return p.returncode, p.stdout, p.stderr


# ── the installed version, the way dev-update reads it ───────────────────────────────────────────

def installed_version(plugins_json=None, settings_json=None):
    """`~/.claude/plugins/installed_plugins.json` first, then the settings.json fallback. None if
    neither names a version."""
    plugins_json = plugins_json or os.path.expanduser("~/.claude/plugins/installed_plugins.json")
    settings_json = settings_json or os.path.expanduser("~/.claude/settings.json")
    try:
        with io.open(plugins_json, encoding="utf-8") as fh:
            entry = json.load(fh)["plugins"]["hitl@hitl"][0]
        return str(entry["version"])
    except Exception:
        pass
    try:
        with io.open(settings_json, encoding="utf-8") as fh:
            data = json.load(fh)
        for p in data.get("plugins", []):
            path = p if isinstance(p, str) else p.get("path", "")
            pj = os.path.join(path, ".claude-plugin", "plugin.json")
            if os.path.isfile(pj):
                with io.open(pj, encoding="utf-8") as fh:
                    return str(json.load(fh)["version"])
    except Exception:
        pass
    return None


def comment_body(version):
    """The whole comment. The version and nothing else."""
    return "HITL %s" % version


# ── tiny YAML: flat maps and one level of nesting, no dependency ─────────────────────────────────

def _load_yaml(path):
    """Enough YAML for the two files this script owns. Returns {} when the file is absent."""
    if not os.path.isfile(path):
        return {}
    data, current = {}, None
    with io.open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            indented = line.startswith(" ")
            key, _sep, val = line.strip().partition(":")
            val = val.strip().strip("'\"")
            if indented and current is not None:
                data[current][key.strip()] = val
            elif val == "":
                current = key.strip()
                data[current] = {}
            else:
                current = None
                data[key.strip()] = val
    return data


def _dump_yaml(data, header=None):
    out = [] if header is None else [header]
    for key, val in data.items():
        if isinstance(val, dict):
            out.append("%s:" % key)
            out.extend("  %s: %s" % (k, v) for k, v in val.items())
        else:
            out.append("%s: %s" % (key, val))
    return "\n".join(out) + "\n"


def _write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ── the user record ──────────────────────────────────────────────────────────────────────────────

def user_dir(home=None):
    return home or os.environ.get(HOME_ENV) or os.path.expanduser(os.path.join("~", ".hitl"))


def user_file(home=None):
    return os.path.join(user_dir(home), USER_FILE_NAME)


def load_record(home=None):
    rec = _load_yaml(user_file(home))
    return rec if rec.get("release_notice") in ("yes", "no") else {}


USER_FILE_HEADER = ("# HITL release notice answers for this machine account. Answers, a date and "
                    "the version: no handle, no email, no repo name.")


def save_record(notice, star, version, home=None, today=None):
    rec = {"release_notice": notice, "star": star,
           "asked_at": today or datetime.date.today().isoformat(),
           "version_at_ask": version or "unknown"}
    assert tuple(rec) == USER_FILE_FIELDS
    _write(user_file(home), _dump_yaml(rec, USER_FILE_HEADER))
    return rec


# ── modes ────────────────────────────────────────────────────────────────────────────────────────

def cmd_state(args, gh, out):
    rec = load_record(args.home)
    if rec:
        out("already-answered")
        out("Release notice: answered %s on %s. Not asking again." % (rec["release_notice"], rec.get("asked_at", "?")))
        return 0
    code, _o, _e = gh(["auth", "status"])
    if code != 0:
        out("gh-logged-out")
        out("Release notice: gh is not logged in, so the question is skipped this time. "
            "Nothing is recorded; it is asked next time.")
        return 0
    out("ask")
    out("")
    out("Question 1 (release notice, default no):")
    out(NOTICE_QUESTION)
    out("")
    out("Question 2 (star, default no):")
    out(STAR_QUESTION)
    return 0


def cmd_record(args, gh, out):
    rec = load_record(args.home)
    if rec:
        out("Release notice: already recorded on %s. Nothing changed." % rec.get("asked_at", "?"))
        return 0
    version = args.version or installed_version() or "unknown"
    rec = save_record(args.notice, args.star, version, args.home, args.today)
    out("Recorded: release notice %s, star %s. Kept in %s." % (rec["release_notice"], rec["star"], user_file(args.home)))
    return 0


def _resolve_version(args, out):
    version = args.version or installed_version()
    if not version:
        out("Refusing: the installed HITL version could not be read, so the comment body cannot be exact. "
            "Pass --version.")
    return version


def cmd_body(args, gh, out):
    version = _resolve_version(args, out)
    if not version:
        return 2
    out(comment_body(version))
    return 0


def resolve_discussion_id(gh, out):
    code, stdout, _err = gh(["api", "graphql", "-f", "query=" + QUERY_DISCUSSION_ID,
                             "-f", "owner=" + OWNER, "-f", "name=" + REPO,
                             "-F", "number=%d" % THREAD_NUMBER])
    if code == 0:
        try:
            did = json.loads(stdout)["data"]["repository"]["discussion"]["id"]
            if did:
                return did
        except (ValueError, KeyError, TypeError):
            pass
    out("Could not look the thread up by number; using its recorded id.")
    return THREAD_ID_FALLBACK


def cmd_post(args, gh, out):
    rec = load_record(args.home)
    if rec.get("release_notice") != "yes":
        out("Refusing to post: no recorded yes to the release notice question. Nothing was sent.")
        return 2
    if not args.confirmed:
        out("Refusing to post: show the person the comment (`body`) first, then pass --confirmed. Nothing was sent.")
        return 2
    version = _resolve_version(args, out)
    if not version:
        return 2
    body = comment_body(version)
    did = resolve_discussion_id(gh, out)
    code, stdout, err = gh(["api", "graphql", "-f", "query=" + MUTATION_ADD_COMMENT,
                            "-f", "id=" + did, "-f", "body=" + body])
    if code != 0:
        out("Could not post the comment (%s). You can add `%s` by hand at %s"
            % ((err or stdout).strip()[:200] or "gh failed", body, THREAD_URL))
        return 1
    url = ""
    try:
        url = json.loads(stdout)["data"]["addDiscussionComment"]["comment"]["url"] or ""
    except (ValueError, KeyError, TypeError):
        pass
    out("Posted `%s` on the \"%s\" thread. %s" % (body, THREAD_TITLE, url or THREAD_URL))
    out("Delete the comment or unsubscribe there at any time.")
    return 0


def cmd_star(args, gh, out):
    rec = load_record(args.home)
    if rec.get("star") != "yes":
        out("Refusing to star: no recorded yes to the star question. Nothing was sent.")
        return 2
    if not args.confirmed:
        out("Refusing to star: pass --confirmed after the person said yes. Nothing was sent.")
        return 2
    code, stdout, err = gh(["api", "-X", "PUT", "/user/starred/%s/%s" % (OWNER, REPO)])
    if code != 0:
        out("Could not star %s/%s (%s). It can be starred on GitHub in one click."
            % (OWNER, REPO, (err or stdout).strip()[:200] or "gh failed"))
        return 1
    out("Starred %s/%s. One click on GitHub undoes it." % (OWNER, REPO))
    return 0


def cmd_share_line(args, gh, out):
    out(SHARE_LINE)
    return 0


def cmd_share_line_retro(args, gh, out):
    path = os.path.join(args.project or ".", PROJECT_FILE)
    cfg = _load_yaml(path)
    shown = cfg.get(PROJECT_KEY)
    if isinstance(shown, dict) and shown.get("shown_in_retro"):
        return 0
    cfg[PROJECT_KEY] = {"shown_in_retro": args.change,
                        "shown_at": args.today or datetime.date.today().isoformat()}
    _write(path, _dump_yaml(cfg))
    out(SHARE_LINE)
    return 0


# ── cli ──────────────────────────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--home", help="directory of the user file (default $%s or ~/.hitl)" % HOME_ENV)
    p.add_argument("--today", help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="mode")
    sub.required = True
    sub.add_parser("state")
    r = sub.add_parser("record")
    r.add_argument("--notice", required=True, choices=["yes", "no"])
    r.add_argument("--star", required=True, choices=["yes", "no", "skipped"])
    r.add_argument("--version")
    b = sub.add_parser("body")
    b.add_argument("--version")
    po = sub.add_parser("post")
    po.add_argument("--confirmed", action="store_true")
    po.add_argument("--version")
    st = sub.add_parser("star")
    st.add_argument("--confirmed", action="store_true")
    sub.add_parser("share-line")
    sr = sub.add_parser("share-line-retro")
    sr.add_argument("--change", required=True)
    sr.add_argument("--project")
    return p


COMMANDS = {"state": cmd_state, "record": cmd_record, "body": cmd_body, "post": cmd_post,
            "star": cmd_star, "share-line": cmd_share_line, "share-line-retro": cmd_share_line_retro}


def main(argv=None, gh=run_gh, out=print):
    args = build_parser().parse_args(argv)
    return COMMANDS[args.mode](args, gh, out)


if __name__ == "__main__":
    sys.exit(main())
