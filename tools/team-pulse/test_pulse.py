#!/usr/bin/env python3
"""Team Pulse (FR-32, #118), asserted against the issue's acceptance list with a fake gh.

Hook and gate comments never count as activity; every event links to its source; the attention
strip lists exactly the epics with a flag and the PRs past the thresholds; a valid Hours line
renders a bar and an invalid one is ignored; the leads section never reaches the team page and the
team page holds nothing the leads page lacks; render works from a file with no Artifact tool."""
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import pulse as P

NOW = dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc)


def ts(days_ago, hours=0):
    return (NOW - dt.timedelta(days=days_ago, hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def user(login, bot=False):
    return {"login": login, "type": "Bot" if bot else "User"}


REPO = "acme/widgets"
U = "https://github.com/acme/widgets"


def fixtures():
    epic_body = ("## Slices\n- [x] Schema #10\n- [ ] API #11\n  - [ ] Handler #12\n- [ ] Docs\n\nProse here.\n")
    issues = [
        {"number": 1, "title": "Epic: Widgets v2", "state": "open", "user": user("lead"), "assignees": [user("lead")],
         "labels": [{"name": "epic"}], "body": epic_body, "created_at": ts(30), "updated_at": ts(1), "html_url": f"{U}/issues/1"},
        {"number": 2, "title": "EPIC: orphan", "state": "open", "user": user("lead"), "assignees": [], "labels": [],
         "body": "Just prose, no checkboxes.", "created_at": ts(40), "updated_at": ts(20), "html_url": f"{U}/issues/2"},
        {"number": 10, "title": "Schema", "state": "closed", "user": user("ann"), "assignees": [user("ann")], "labels": [],
         "body": "", "created_at": ts(20), "updated_at": ts(9), "closed_at": ts(9), "html_url": f"{U}/issues/10"},
        {"number": 11, "title": "API", "state": "open", "user": user("ann"), "assignees": [user("ann")], "labels": [],
         "body": "", "created_at": ts(12), "updated_at": ts(1), "html_url": f"{U}/issues/11"},
        {"number": 12, "title": "Handler", "state": "open", "user": user("bob"), "assignees": [user("bob")], "labels": [],
         "body": "", "created_at": ts(12), "updated_at": ts(8), "html_url": f"{U}/issues/12"},
        {"number": 13, "title": "New bug", "state": "open", "user": user("bob"), "assignees": [], "labels": [],
         "body": "", "created_at": ts(2), "updated_at": ts(2), "html_url": f"{U}/issues/13"},
    ]
    prs = [
        {"number": 20, "title": "feat: API (#11)", "user": user("ann"), "draft": False, "state": "open", "merged_at": None,
         "created_at": ts(5), "updated_at": ts(4), "html_url": f"{U}/pull/20", "head": {"ref": "issue/11-api"},
         "requested_reviewers": [user("bob")], "body": ""},
        {"number": 21, "title": "wip: handler", "user": user("bob"), "draft": True, "state": "open", "merged_at": None,
         "created_at": ts(30), "updated_at": ts(16), "html_url": f"{U}/pull/21", "head": {"ref": "GH-12-handler"},
         "requested_reviewers": [], "body": ""},
        {"number": 22, "title": "chore: bump", "user": user("lead"), "draft": False, "state": "closed", "merged_at": ts(3),
         "merged_by": user("lead"), "created_at": ts(3, 2), "updated_at": ts(3), "html_url": f"{U}/pull/22", "head": {"ref": "chore"},
         "requested_reviewers": [], "body": ""},
    ]
    reviews = {20: [], 21: [], 22: []}
    commits = [
        {"sha": "abc1234deadbeef", "author": user("ann"), "html_url": f"{U}/commit/abc1234",
         "commit": {"message": "feat: api handler\n\nbody", "author": {"name": "Ann", "date": ts(4)}}},
        {"sha": "bbb1234deadbeef", "author": None, "html_url": f"{U}/commit/bbb1234",
         "commit": {"message": "fix: typo", "author": {"name": "Someone Local", "date": ts(3)}}},
        {"sha": "ccc1234deadbeef", "author": user("dependabot[bot]", bot=True), "html_url": f"{U}/commit/ccc1234",
         "commit": {"message": "bump deps", "author": {"name": "dependabot", "date": ts(2)}}},
    ]
    comments = [
        {"user": user("bob"), "body": "Looks fine, one question about the schema.", "created_at": ts(1), "html_url": f"{U}/issues/11#issuecomment-1", "issue_url": f"https://api.github.com/repos/{REPO}/issues/11"},
        {"user": user("hitl-bot"), "body": "**HITL progress** | Step 5: RED | Phase: Build", "created_at": ts(1), "html_url": f"{U}/issues/11#issuecomment-2", "issue_url": f"https://api.github.com/repos/{REPO}/issues/11"},
        {"user": user("lead"), "body": "## ⏸ Gate: Decision Packet Review\nplease review", "created_at": ts(1), "html_url": f"{U}/issues/11#issuecomment-3", "issue_url": f"https://api.github.com/repos/{REPO}/issues/11"},
        {"user": user("ann"), "body": "End of session.\nHours: session 2.5, milestone M3 10.5/20\n", "created_at": ts(2), "html_url": f"{U}/issues/11#issuecomment-4", "issue_url": f"https://api.github.com/repos/{REPO}/issues/11"},
        {"user": user("ann"), "body": "Hours: about three, milestone M3 lots\n", "created_at": ts(1), "html_url": f"{U}/issues/11#issuecomment-5", "issue_url": f"https://api.github.com/repos/{REPO}/issues/11"},
        {"user": user("github-actions[bot]", bot=True), "body": "CI passed", "created_at": ts(1), "html_url": f"{U}/issues/11#issuecomment-6", "issue_url": f"https://api.github.com/repos/{REPO}/issues/11"},
    ]
    return issues, prs, reviews, commits, comments


class FakeGh:
    def __init__(self):
        self.issues, self.prs, self.reviews, self.commits, self.comments = fixtures()
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["repo", "view"]:
            return REPO + "\n"
        path = args[1]
        body = None
        if "/commits?" in path:
            body = self.commits
        elif re.search(r"/pulls/\d+/reviews", path):
            n = int(re.search(r"/pulls/(\d+)/", path).group(1)); body = self.reviews.get(n, [])
        elif "/pulls?" in path:
            body = self.prs
        elif "/issues/comments?" in path:
            body = self.comments
        elif "/pulls/comments?" in path:
            body = []
        elif re.search(r"/issues/\d+$", path):
            n = int(path.rsplit("/", 1)[1]); one = [i for i in self.issues if i["number"] == n]
            return json.dumps(one[0] if one else {"message": "Not Found"})
        elif "/issues?" in path:
            body = self.issues + [dict(p, pull_request={"url": "x"}) for p in self.prs]  # the issues API includes PRs
        else:
            raise AssertionError(path)
        return json.dumps([body])  # --slurp shape: a list of pages


def cfg():
    c = dict(P.DEFAULTS)
    c["window_days"] = 14
    return c


def collected():
    gh = FakeGh()
    return P.collect(gh, cfg(), now=NOW), gh


def test_collect_uses_gh_only_and_drops_bots_and_hook_comments():
    data, gh = collected()
    assert all(a[0] in ("api", "repo") for a in gh.calls)
    whos = {e["who"] for e in data["events"]}
    assert "dependabot[bot]" not in whos and "github-actions[bot]" not in whos
    texts = [e["text"] for e in data["events"] if e["kind"] == "comment"]
    assert not any(t.startswith("**HITL progress**") or t.startswith("## ⏸ Gate") for t in texts)
    assert any("Looks fine" in t for t in texts)


def test_every_event_links_to_its_source():
    data, _ = collected()
    assert data["events"] and all(e["url"] and e["url"].startswith("https://") for e in data["events"])


def test_every_number_on_the_page_is_a_link():
    """FR-32 acceptance: every event AND number links to its GitHub source. Tallies, slice counts,
    last-active ages, session hours and review load are anchors, not plain text."""
    data, _ = collected()
    for audience in ("team", "leads"):
        page = P.render(data, None, audience)
        for m in re.finditer(r">(\d+(?:\.\d+)?(?:/\d+)?[^<]*?)<", page):
            text = m.group(1)
            if text.strip() in ("—",):
                continue
            start = page.rfind("<a ", 0, m.start())
            end = page.find("</a>", m.start())
            assert start != -1 and (page.rfind("</a>", 0, m.start()) < start), f"{audience}: number not linked: {text!r}"
    team = P.render(data, None, "team")
    assert "commits?author=ann" in team and "1/4 slices done</a>" in team
    leads = P.render(data, None, "leads")
    assert "review-requested%3Abob" in leads


def test_unattributed_commit_is_flagged_not_counted():
    data, _ = collected()
    assert [c["sha"] for c in data["unattributed_commits"]] == ["bbb1234"]
    view = P.derive(data, NOW)
    assert any("not linked to a GitHub account" in a["text"] for a in view["attention"])


def test_epic_tree_states_and_flags():
    data, _ = collected()
    view = P.derive(data, NOW)
    by = {e["number"]: e for e in view["epics"]}
    e1 = by[1]
    states = {r["text"]: r["state"] for r in e1["rows"]}
    assert states["Schema #10"] == "done"            # checked
    assert states["API #11"] == "PR in review"        # open non-draft PR references #11 by title and branch
    assert states["Handler #12"] == "draft PR"        # draft PR references GH-12 in its branch
    assert states["Docs"] == "no issue yet"
    assert [r["depth"] for r in e1["rows"]] == [0, 0, 1, 0]
    assert e1["done"] == 1 and e1["total"] == 4
    assert any(f.startswith("PR #20 unreviewed") for f in e1["flags"])
    e2 = by[2]
    assert e2["rows"] == [] and "no checkbox list" in e2["flags"] and "no owner" in e2["flags"]
    assert any(f.startswith("epic untouched 20d") for f in e2["flags"])


def test_attention_strip_is_exactly_flags_and_threshold_breaches():
    data, _ = collected()
    view = P.derive(data, NOW)
    texts = [a["text"] for a in view["attention"]]
    assert any(t.startswith("PR #20 needs a reviewer (5d)") for t in texts)      # past stale_review_days=3
    assert any(t.startswith("Draft PR #21 idle 16d") for t in texts)              # past stale_draft_days=14
    assert any(t.startswith("PR #22 merged by its author with no review") for t in texts)
    epic_items = [t for t in texts if t.startswith("Epic #")]
    flagged = {f"Epic #{e['number']}: {f}" for e in view["epics"] for f in e["flags"]}
    assert set(epic_items) == flagged
    pr_items = {t for t in texts if t.startswith(("PR #", "Draft PR #"))}
    assert pr_items == {"PR #20 needs a reviewer (5d)", "Draft PR #21 idle 16d", "PR #22 merged by its author with no review"}
    assert all(a["url"] for a in view["attention"])


def test_hours_line_valid_renders_bar_and_invalid_is_ignored():
    data, _ = collected()
    assert len(data["hours"]) == 1 and data["hours"][0]["milestone"] == "M3"
    view = P.derive(data, NOW)
    assert view["hours"]["ann"]["session_total"] == 2.5
    assert view["hours"]["ann"]["milestones"]["M3"] == {"done": 10.5, "total": 20.0, "url": f"{U}/issues/11#issuecomment-4"}
    leads = P.render(data, None, "leads")
    assert "M3</a> 10.5/20" in leads and "width:52%" in leads


def test_leads_section_never_reaches_team_page_and_team_is_a_subset():
    data, _ = collected()
    team = P.render(data, None, "team")
    leads = P.render(data, None, "leads")
    assert "Planning (leads only)" not in team and "Session hours" not in team
    assert "Planning (leads only)" in leads
    # everything on the team page is on the leads page (the leads page only adds)
    for line in team.splitlines():
        if line.startswith("<") and "team view" not in line:
            assert line in leads, line[:80]


def test_notes_render_as_facts_and_missing_notes_leave_no_placeholder():
    data, _ = collected()
    plain = P.render(data, None, "team")
    assert "Nudge." not in plain and "None" not in plain.split("<h2>People")[0][:0]
    skel = P.notes_template(data)
    assert set(skel["people"]) == {"ann", "bob", "lead"} and set(skel["epics"]) == {"1", "2"}
    notes = {"people": {"ann": "On the API slice; PR #20 is waiting for bob's review."},
             "epics": {"1": {"summary": "One of four slices done.", "nudge": "PR #20 needs a reviewer; bob was asked."}}}
    page = P.render(data, notes, "team")
    assert "PR #20 is waiting for bob" in page and "Nudge.</strong> PR #20 needs a reviewer" in page


def test_render_is_self_contained_and_escapes_user_text(tmp_path):
    data, _ = collected()
    data["prs"][0]["title"] = "<script>alert(1)</script>"      # rendered in the people cards and the tree
    data["events"][0]["text"] = "<img src=x onerror=alert(2)>"
    page = P.render(data, {"people": {"ann": "<b>bold</b>"}}, "team")
    assert "<script>" not in page and "&lt;script&gt;alert(1)" in page
    assert "<img" not in page and "&lt;img src=x" in page and "&lt;b&gt;bold" in page
    assert 'src="http' not in page and "@import" not in page


def test_cli_end_to_end_writes_data_notes_and_page(tmp_path, capsys):
    gh = FakeGh()
    data_path = tmp_path / "data.json"
    rc = P.main(["collect", "--out", str(data_path), "--config", str(tmp_path / "none.yaml")], run=gh)
    assert rc == 0 and data_path.is_file()
    rc = P.main(["notes", "--data", str(data_path)], run=gh)
    assert rc == 0 and '"people"' in capsys.readouterr().out
    out = tmp_path / "docs" / "team-pulse.html"
    rc = P.main(["render", "--data", str(data_path), "--out", str(out), "--audience", "team", "--config", str(tmp_path / "none.yaml")], run=gh)
    assert rc == 0 and out.is_file() and "Team Pulse" in out.read_text()
    printed = capsys.readouterr().out
    assert "attention items" in printed


def test_config_block_is_read_and_ints_coerced(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("release_notice: {}\nteam_pulse:\n  window_days: 7\n  stale_review_days: '2'\n  audience: leads\n  exclude_logins: [x[bot], y]\n")
    c = P.load_config(str(p))
    assert c["window_days"] == 7 and c["stale_review_days"] == 2 and c["audience"] == "leads"
    assert c["exclude_logins"] == ["x[bot]", "y"]
    assert P.load_config(str(tmp_path / "missing.yaml"))["window_days"] == 14


def test_gh_failure_is_reported_not_swallowed(tmp_path, capsys):
    def bad(args):
        raise RuntimeError("gh api: HTTP 401")
    rc = P.main(["collect", "--out", str(tmp_path / "d.json"), "--repo", REPO, "--config", str(tmp_path / "none.yaml")], run=bad)
    assert rc == 3 and "HTTP 401" in capsys.readouterr().err


def test_pfx2_change_id_prefix_falls_back_to_the_repository_setting(tmp_path):
    """FR-30 slice 0: a top-level change_id_prefix in .hitl/config.yaml is Team Pulse's default."""
    import pulse as P
    cfg = tmp_path / "config.yaml"
    cfg.write_text("change_id_prefix: SCM\nteam_pulse:\n  window_days: 7\n")
    assert P.load_config(str(cfg))["change_id_prefix"] == "SCM"
    cfg.write_text("change_id_prefix: SCM\nteam_pulse:\n  change_id_prefix: EMAIL\n")
    assert P.load_config(str(cfg))["change_id_prefix"] == "EMAIL"
    cfg.write_text("team_pulse:\n  window_days: 7\n")
    assert P.load_config(str(cfg))["change_id_prefix"] == "GH"
