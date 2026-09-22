#!/usr/bin/env python3
"""Team Pulse: who is on what, what is waiting on someone else, and who can unblock it.

Reads GitHub through `gh` only. Folds commits, pull requests, reviews, issues and comments from
the last N days per person and per epic, reads each epic's checkbox list as a slice tree, and
renders one self-contained HTML page where every number and event links to its GitHub source.

Three commands, so the model-written notes stay a separate step the generator never performs:

  pulse.py collect  --out .hitl/pulse/data.json            # gh -> JSON (facts only)
  pulse.py notes    --data .hitl/pulse/data.json           # the JSON skeleton a model fills in
  pulse.py render   --data .hitl/pulse/data.json [--notes .hitl/pulse/notes.json]
                    --out docs/04-operations/team-pulse.html [--audience team|leads]

Config lives under `team_pulse:` in `.hitl/config.yaml` (see DEFAULTS). Hook and gate comments
never count as human activity: they are dropped by their first line (HOOK_MARKERS). Bots are
dropped by login. Wording on the page is facts and nudges, never verdicts on a person.
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import subprocess
import sys

DEFAULTS = {
    "window_days": 14,
    "stale_review_days": 3,
    "stale_draft_days": 14,
    "stale_epic_days": 14,
    "epic_match": "label:epic | title:\"Epic:\"",
    "change_id_prefix": "GH",
    "exclude_logins": ["dependabot[bot]", "github-actions[bot]"],
    "publish": "file",
    "audience": "team",
    "out_dir": "docs/04-operations",
}

# First lines that mark a comment as HITL's own machinery, not a person (issue #118, item 3).
HOOK_MARKERS = ("**HITL progress**", "⏸ Gate:", "## ⏸ Gate:", "✅ Gate Approved", "## ✅ Gate Approved",
                "## ✅ Ready for Development", "**Skipped:**", "<!-- hitl:")

HOURS_RE = re.compile(
    r"^\s*Hours:\s*(?:session\s+(?P<session>\d+(?:\.\d+)?))?\s*,?\s*"
    r"(?:milestone\s+(?P<ms>[A-Za-z0-9._-]+)\s+(?P<done>\d+(?:\.\d+)?)\s*/\s*(?P<total>\d+(?:\.\d+)?))?\s*$",
    re.M)
CHECKBOX_RE = re.compile(r"^(?P<indent>\s*)[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$", re.M)
ISSUE_REF_RE = re.compile(r"(?:^|[^\w/])#(\d+)\b")


# ── time ─────────────────────────────────────────────────────────────────────────────────────────
def parse_ts(s):
    if not s:
        return None
    s = str(s).replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def days_since(ts, now):
    t = parse_ts(ts)
    return None if t is None else max(0, (now - t).days)


# ── config ───────────────────────────────────────────────────────────────────────────────────────
def load_config(path=".hitl/config.yaml"):
    """The `team_pulse:` block over DEFAULTS. PyYAML when present, else a flat reader."""
    cfg = dict(DEFAULTS)
    if not os.path.isfile(path):
        return cfg
    block = {}
    try:
        import yaml  # noqa
        data = yaml.safe_load(io.open(path, encoding="utf-8")) or {}
        block = data.get("team_pulse") or {}
    except Exception:
        current = None
        for raw in io.open(path, encoding="utf-8"):
            line = raw.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            key, _s, val = line.strip().partition(":")
            if not line.startswith(" "):
                current = key.strip() if val.strip() == "" else None
            elif current == "team_pulse":
                block[key.strip()] = val.strip().strip("'\"")
    for k, v in (block or {}).items():
        if k in ("window_days", "stale_review_days", "stale_draft_days", "stale_epic_days"):
            try:
                cfg[k] = int(v)
            except (TypeError, ValueError):
                pass
        elif k == "exclude_logins":
            cfg[k] = [str(x).strip() for x in (v if isinstance(v, list) else str(v).strip("[]").split(","))
                      if str(x).strip()]
        elif k in cfg:
            cfg[k] = str(v)
    return cfg


# ── gh ───────────────────────────────────────────────────────────────────────────────────────────
def gh_run(args):
    p = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("gh %s: %s" % (" ".join(args[:2]), (p.stderr or p.stdout).strip()[:300]))
    return p.stdout


def gh_json(run, path, paginate=True):
    args = ["api", path, "-H", "Accept: application/vnd.github+json"]
    if paginate:
        args += ["--paginate", "--slurp"]
    out = run(args)
    data = json.loads(out or "[]")
    if paginate and isinstance(data, list) and data and isinstance(data[0], list):
        data = [x for page in data for x in page]
    return data


def repo_slug(run):
    return run(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()


# ── collect ──────────────────────────────────────────────────────────────────────────────────────
def _login(user):
    return (user or {}).get("login") if isinstance(user, dict) else None


def is_bot(login, user=None, cfg=None):
    if not login:
        return True
    if login.endswith("[bot]") or (isinstance(user, dict) and user.get("type") == "Bot"):
        return True
    return login in (cfg or DEFAULTS).get("exclude_logins", [])


def is_hook_comment(body):
    first = (body or "").lstrip().split("\n", 1)[0].strip()
    return any(first.startswith(m) for m in HOOK_MARKERS)


def is_epic(issue, cfg):
    spec = cfg.get("epic_match", DEFAULTS["epic_match"])
    labels = {(l.get("name") or "").lower() for l in issue.get("labels") or [] if isinstance(l, dict)}
    title = issue.get("title") or ""
    for alt in spec.split("|"):
        alt = alt.strip()
        if alt.startswith("label:") and alt[6:].strip().lower() in labels:
            return True
        if alt.startswith("title:") and title.lower().startswith(alt[6:].strip().strip('"\'').lower()):
            return True
    return False


def slice_tree(body):
    """Checkbox lines as a tree. Prose with no checkboxes gives an empty tree, never a wrong one."""
    nodes = []
    for m in CHECKBOX_RE.finditer(body or ""):
        text = m.group("text")
        refs = [int(x) for x in ISSUE_REF_RE.findall(text)]
        nodes.append({"depth": len(m.group("indent").replace("\t", "    ")) // 2, "text": text,
                      "checked": m.group("mark").lower() == "x", "issue": refs[0] if refs else None})
    return nodes


def refs_in(text, prefix):
    """Issue numbers a PR title or branch refers to: #N, GH-N, <prefix>-N, issue/N-..."""
    out = set()
    for x in ISSUE_REF_RE.findall(text or ""):
        out.add(int(x))
    for x in re.findall(r"\b(?:%s|GH)-(\d+)\b" % re.escape(prefix), text or "", re.I):
        out.add(int(x))
    for x in re.findall(r"\bissue/(\d+)\b", text or ""):
        out.add(int(x))
    return out


def collect(run=gh_run, cfg=None, now=None, repo=None):
    cfg = cfg or dict(DEFAULTS)
    now = now or dt.datetime.now(dt.timezone.utc)
    repo = repo or repo_slug(run)
    since = (now - dt.timedelta(days=cfg["window_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = "per_page=100"
    commits = gh_json(run, f"repos/{repo}/commits?since={since}&{q}")
    prs = [p for p in gh_json(run, f"repos/{repo}/pulls?state=all&sort=updated&direction=desc&{q}")
           if parse_ts(p.get("updated_at")) and parse_ts(p["updated_at"]) >= now - dt.timedelta(days=cfg["window_days"])
           or p.get("state") == "open"]
    issues_raw = gh_json(run, f"repos/{repo}/issues?state=all&since={since}&{q}")
    open_issues = gh_json(run, f"repos/{repo}/issues?state=open&{q}")
    comments = gh_json(run, f"repos/{repo}/issues/comments?since={since}&{q}")
    review_comments = gh_json(run, f"repos/{repo}/pulls/comments?since={since}&{q}")

    issues = {}
    for it in issues_raw + open_issues:
        if isinstance(it, dict) and "pull_request" not in it:
            issues[it["number"]] = it
    reviews = {}
    for p in prs:
        try:
            reviews[p["number"]] = gh_json(run, f"repos/{repo}/pulls/{p['number']}/reviews?{q}")
        except RuntimeError:
            reviews[p["number"]] = []

    def ev(kind, who, ts, text, url, ref=None):
        return {"kind": kind, "who": who, "ts": ts, "text": (text or "").strip().split("\n", 1)[0][:120],
                "url": url, "ref": ref}

    events = []
    unattributed = []
    for c in commits:
        who = _login(c.get("author"))
        msg = ((c.get("commit") or {}).get("message") or "")
        ts = ((c.get("commit") or {}).get("author") or {}).get("date")
        if not who:
            unattributed.append({"sha": (c.get("sha") or "")[:7], "name": ((c.get("commit") or {}).get("author") or {}).get("name"),
                                 "url": c.get("html_url"), "ts": ts})
            continue
        if is_bot(who, c.get("author"), cfg):
            continue
        events.append(ev("commit", who, ts, msg, c.get("html_url"), (c.get("sha") or "")[:7]))
    for p in prs:
        who = _login(p.get("user"))
        if is_bot(who, p.get("user"), cfg):
            continue
        events.append(ev("pr_opened", who, p.get("created_at"), p.get("title"), p.get("html_url"), p["number"]))
        if p.get("merged_at"):
            events.append(ev("pr_merged", _login(p.get("merged_by")) or who, p.get("merged_at"), p.get("title"), p.get("html_url"), p["number"]))
        for r in reviews.get(p["number"], []):
            rw = _login(r.get("user"))
            if rw and not is_bot(rw, r.get("user"), cfg) and r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED"):
                events.append(ev("review", rw, r.get("submitted_at"), f"{r.get('state','').lower()} on #{p['number']}", r.get("html_url") or p.get("html_url"), p["number"]))
    for it in issues_raw:
        if "pull_request" in it:
            continue
        who = _login(it.get("user"))
        if who and not is_bot(who, it.get("user"), cfg) and parse_ts(it.get("created_at")) and parse_ts(it["created_at"]) >= now - dt.timedelta(days=cfg["window_days"]):
            events.append(ev("issue_opened", who, it.get("created_at"), it.get("title"), it.get("html_url"), it["number"]))
    hours = []
    for c in comments + review_comments:
        who = _login(c.get("user"))
        if is_bot(who, c.get("user"), cfg) or is_hook_comment(c.get("body")):
            continue
        num = None
        m = re.search(r"/(?:issues|pulls)/(\d+)$", c.get("issue_url") or c.get("pull_request_url") or "")
        if m:
            num = int(m.group(1))
        events.append(ev("comment", who, c.get("created_at"), c.get("body"), c.get("html_url"), num))
        for hm in HOURS_RE.finditer(c.get("body") or ""):
            if hm.group("session") is None and hm.group("ms") is None:
                continue
            hours.append({"who": who, "ts": c.get("created_at"), "url": c.get("html_url"),
                          "session": float(hm.group("session")) if hm.group("session") else None,
                          "milestone": hm.group("ms"),
                          "done": float(hm.group("done")) if hm.group("done") else None,
                          "total": float(hm.group("total")) if hm.group("total") else None})
    events = [e for e in events if e["who"] and parse_ts(e["ts"])]
    events.sort(key=lambda e: e["ts"], reverse=True)

    # pull requests, slimmed
    pr_rows = []
    for p in prs:
        rv = [r for r in reviews.get(p["number"], []) if _login(r.get("user")) and not is_bot(_login(r.get("user")), r.get("user"), cfg)]
        pr_rows.append({
            "number": p["number"], "title": p.get("title"), "author": _login(p.get("user")), "draft": bool(p.get("draft")),
            "state": "merged" if p.get("merged_at") else p.get("state"), "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"), "merged_at": p.get("merged_at"), "merged_by": _login(p.get("merged_by")),
            "url": p.get("html_url"), "branch": (p.get("head") or {}).get("ref"),
            "requested_reviewers": [_login(u) for u in p.get("requested_reviewers") or [] if _login(u)],
            "reviews": [{"who": _login(r.get("user")), "state": r.get("state"), "ts": r.get("submitted_at")} for r in rv],
            "refs": sorted(refs_in((p.get("title") or "") + " " + ((p.get("head") or {}).get("ref") or "") + " " + (p.get("body") or "")[:400], cfg["change_id_prefix"])),
        })

    # epics
    epics = []
    for it in sorted(issues.values(), key=lambda i: i["number"]):
        if it.get("state") != "open" or not is_epic(it, cfg):
            continue
        tree = slice_tree(it.get("body"))
        for node in tree:
            n = node["issue"]
            if n is not None and n not in issues:
                try:
                    one = gh_json(run, f"repos/{repo}/issues/{n}", paginate=False)
                    if isinstance(one, dict) and "number" in one:
                        issues[n] = one
                except RuntimeError:
                    pass
        epics.append({"number": it["number"], "title": it.get("title"), "url": it.get("html_url"),
                      "owners": [_login(a) for a in it.get("assignees") or [] if _login(a)],
                      "updated_at": it.get("updated_at"), "tree": tree})

    issue_rows = {n: {"number": n, "title": i.get("title"), "state": i.get("state"), "url": i.get("html_url"),
                      "assignees": [_login(a) for a in i.get("assignees") or [] if _login(a)],
                      "updated_at": i.get("updated_at"), "closed_at": i.get("closed_at")}
                  for n, i in issues.items()}
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "repo": repo, "window_days": cfg["window_days"],
            "config": {k: cfg[k] for k in ("stale_review_days", "stale_draft_days", "stale_epic_days", "change_id_prefix")},
            "events": events, "prs": pr_rows, "issues": issue_rows, "epics": epics, "hours": hours,
            "unattributed_commits": unattributed}


# ── derive ───────────────────────────────────────────────────────────────────────────────────────
def _issue_activity(data, n, now):
    """Days since the last human event on issue n, or since its update, or None."""
    best = None
    for e in data["events"]:
        if e.get("ref") == n and e["kind"] in ("comment", "issue_opened"):
            d = days_since(e["ts"], now)
            best = d if best is None or (d is not None and d < best) else best
    if best is None:
        it = data["issues"].get(n) or data["issues"].get(str(n))
        if it:
            best = days_since(it.get("updated_at"), now)
    return best


def pr_review_state(pr):
    if pr["draft"]:
        return "draft"
    if any(r["state"] in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED") for r in pr["reviews"]):
        return "reviewed"
    return "unreviewed"


def slice_state(data, node, now):
    n = node["issue"]
    if node["checked"]:
        return "done"
    if n is None:
        return "no issue yet"
    it = data["issues"].get(n) or data["issues"].get(str(n))
    if it and it.get("state") == "closed":
        return "done"
    for pr in data["prs"]:
        if pr["state"] == "open" and n in pr["refs"]:
            return "draft PR" if pr["draft"] else "PR in review"
    d = _issue_activity(data, n, now)
    if d is None:
        return "idle"
    return f"active {d}d" if d <= data["config"]["stale_review_days"] else f"idle {d}d"


def derive(data, now=None):
    """Per-person and per-epic views plus the attention strip. Pure; no gh."""
    now = now or parse_ts(data["generated_at"]) or dt.datetime.now(dt.timezone.utc)
    cfg = data["config"]
    people = {}
    for e in data["events"]:
        p = people.setdefault(e["who"], {"login": e["who"], "last": None, "tally": {}, "latest": [], "issues": set(), "open_prs": []})
        p["tally"][e["kind"]] = p["tally"].get(e["kind"], 0) + 1
        if p["last"] is None or e["ts"] > p["last"]:
            p["last"] = e["ts"]
        if len(p["latest"]) < 5:
            p["latest"].append(e)
        if e.get("ref") and e["kind"] in ("comment", "issue_opened") and (e["ref"] in data["issues"] or str(e["ref"]) in data["issues"]):
            p["issues"].add(e["ref"])
    for pr in data["prs"]:
        if pr["state"] == "open" and pr["author"] in people:
            people[pr["author"]]["open_prs"].append({"number": pr["number"], "title": pr["title"], "url": pr["url"],
                                                      "draft": pr["draft"], "idle_days": days_since(pr["updated_at"], now),
                                                      "review": pr_review_state(pr)})
    for p in people.values():
        p["issues"] = sorted(p["issues"])
        p["last_days"] = days_since(p["last"], now)
        p["review_load"] = sum(1 for pr in data["prs"] if pr["state"] == "open" and p["login"] in pr["requested_reviewers"])

    epics = []
    for ep in data["epics"]:
        rows = [dict(node, state=slice_state(data, node, now)) for node in ep["tree"]]
        flags = []
        if not ep["owners"]:
            flags.append("no owner")
        if rows and all(r["issue"] is None for r in rows):
            flags.append("no slice has an issue")
        if not rows:
            flags.append("no checkbox list")
        untouched = days_since(ep["updated_at"], now)
        if untouched is not None and untouched > cfg["stale_epic_days"]:
            flags.append(f"epic untouched {untouched}d")
        for pr in data["prs"]:
            if pr["state"] == "open" and not pr["draft"] and pr_review_state(pr) == "unreviewed" and any(r["issue"] in pr["refs"] for r in rows):
                age = days_since(pr["created_at"], now)
                if age is not None and age > cfg["stale_review_days"]:
                    flags.append(f"PR #{pr['number']} unreviewed {age}d")
        done = sum(1 for r in rows if r["state"] == "done")
        epics.append(dict(ep, rows=rows, flags=flags, done=done, total=len(rows)))

    attention = []
    for ep in epics:
        for f in ep["flags"]:
            attention.append({"kind": "epic", "text": f"Epic #{ep['number']}: {f}", "url": ep["url"]})
    for pr in data["prs"]:
        if pr["state"] != "open":
            continue
        idle = days_since(pr["updated_at"], now) or 0
        age = days_since(pr["created_at"], now) or 0
        if pr["draft"] and idle > cfg["stale_draft_days"]:
            attention.append({"kind": "draft", "text": f"Draft PR #{pr['number']} idle {idle}d", "url": pr["url"]})
        elif not pr["draft"] and pr_review_state(pr) == "unreviewed" and age > cfg["stale_review_days"]:
            attention.append({"kind": "review", "text": f"PR #{pr['number']} needs a reviewer ({age}d)", "url": pr["url"]})
    self_merged = [pr for pr in data["prs"] if pr["state"] == "merged" and pr["merged_by"] and pr["merged_by"] == pr["author"] and not pr["reviews"]]
    for pr in self_merged:
        attention.append({"kind": "merge", "text": f"PR #{pr['number']} merged by its author with no review", "url": pr["url"]})
    for c in data.get("unattributed_commits", []):
        attention.append({"kind": "commit", "text": f"Commit {c['sha']} by \"{c.get('name')}\" is not linked to a GitHub account", "url": c["url"]})

    # hours: latest milestone line per person per milestone; sessions summed
    hours = {}
    for h in sorted(data.get("hours", []), key=lambda x: x["ts"] or ""):
        row = hours.setdefault(h["who"], {"session_total": 0.0, "milestones": {}})
        if h["session"] is not None:
            row["session_total"] += h["session"]
        if h["milestone"] and h["done"] is not None and h["total"]:
            row["milestones"][h["milestone"]] = {"done": h["done"], "total": h["total"], "url": h["url"]}
    return {"people": sorted(people.values(), key=lambda p: p["last"] or "", reverse=True),
            "epics": epics, "attention": attention, "hours": hours}


# ── notes ────────────────────────────────────────────────────────────────────────────────────────
def notes_template(data):
    view = derive(data)
    return {"rule": "Facts from data.json only. One sentence per person saying what they are on. Per epic: one summary "
                    "sentence and one nudge naming the thing that is waiting and who can supply it. No praise, no blame, "
                    "no hedging, no verdicts on a person.",
            "people": {p["login"]: "" for p in view["people"]},
            "epics": {str(e["number"]): {"summary": "", "nudge": ""} for e in view["epics"]}}


# ── render ───────────────────────────────────────────────────────────────────────────────────────
def _h(x):
    return html.escape("" if x is None else str(x))


def _a(text, url):
    return f'<a href="{_h(url)}">{_h(text)}</a>' if url else _h(text)


def tally_url(repo, login, kind):
    """The GitHub search that produces one tally, so the number can be checked in one click."""
    base = f"https://github.com/{repo}"
    q = {"commit": f"{base}/commits?author={login}",
         "pr_opened": f"{base}/pulls?q=is%3Apr+author%3A{login}",
         "pr_merged": f"{base}/pulls?q=is%3Apr+is%3Amerged+author%3A{login}",
         "review": f"{base}/pulls?q=is%3Apr+reviewed-by%3A{login}",
         "comment": f"{base}/issues?q=commenter%3A{login}",
         "issue_opened": f"{base}/issues?q=is%3Aissue+author%3A{login}",
         "review_load": f"{base}/pulls?q=is%3Apr+is%3Aopen+review-requested%3A{login}"}
    return q.get(kind, base)


CSS = """
:root{--ink:#1c2430;--mut:#5c6a78;--rule:#d9dfe5;--paper:#f7f8f9;--card:#fff;--warn:#a8661a;--warn-soft:#f6ecdd;--ok:#2b7a4b;--acc:#1f6f8b}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;padding:24px 28px 56px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 10px}h3{font-size:16px;margin:0 0 6px}
.sub{color:var(--mut);margin:0 0 18px}a{color:var(--acc)}
.strip{background:var(--warn-soft);border-left:3px solid var(--warn);padding:10px 14px}.strip li{margin:2px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:12px 14px}
.tally{color:var(--mut);font-size:13px}.now{margin:6px 0 8px}.ev{font-size:13px;color:var(--mut);margin:0;padding-left:18px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--rule);vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.st{display:inline-block;padding:1px 7px;border-radius:10px;font-size:12px;background:#e9edf0}.st.done{background:#dff1e6;color:var(--ok)}.st.idle{background:var(--warn-soft);color:var(--warn)}
.flag{color:var(--warn)}.bar{height:8px;background:#e9edf0;border-radius:4px;position:relative;margin-top:4px}.bar i{position:absolute;left:0;top:0;bottom:0;background:var(--acc);border-radius:4px}
.foot{color:var(--mut);font-size:12px;margin-top:36px;border-top:1px solid var(--rule);padding-top:10px}
"""


def render(data, notes=None, audience="team", view=None):
    """One self-contained page. `audience` is team or leads; leads adds one section and nothing else changes."""
    view = view or derive(data)
    notes = notes or {}
    pn = notes.get("people") or {}
    en = notes.get("epics") or {}
    cfg = data["config"]
    out = []
    out.append(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
               f"<title>Team Pulse · {_h(data['repo'])}</title><style>{CSS}</style></head><body>")
    out.append(f"<h1>Team Pulse</h1><p class='sub'>{_a(data['repo'], 'https://github.com/' + data['repo'])} · last {data['window_days']} days · "
               f"generated {_h(data['generated_at'])} · {'leads view' if audience == 'leads' else 'team view'}</p>")

    out.append("<h2>Needs attention</h2>")
    if view["attention"]:
        out.append("<div class='strip'><ul>" + "".join(f"<li>{_a(a['text'], a['url'])}</li>" for a in view["attention"]) + "</ul></div>")
    else:
        out.append("<p class='sub'>Nothing past the thresholds.</p>")

    out.append("<h2>Epics</h2>")
    if not view["epics"]:
        out.append("<p class='sub'>No open epics found (label <code>epic</code> or a title starting with <code>Epic:</code>).</p>")
    for ep in view["epics"]:
        n = en.get(str(ep["number"])) or {}
        owners = ", ".join(_a(o, 'https://github.com/' + o) for o in ep['owners']) or 'none'
        out.append(f"<div class='card'><h3>{_a('#' + str(ep['number']) + ' ' + (ep['title'] or ''), ep['url'])} "
                   f"<span class='tally'>{_a(str(ep['done']) + '/' + str(ep['total']) + ' slices done', ep['url'])} · owner {owners}</span></h3>")
        if n.get("summary"):
            out.append(f"<p class='now'>{_h(n['summary'])}</p>")
        if ep["flags"]:
            out.append("<p class='flag'>" + " · ".join(_h(f) for f in ep["flags"]) + "</p>")
        if n.get("nudge"):
            out.append(f"<p><strong>Nudge.</strong> {_h(n['nudge'])}</p>")
        if ep["rows"]:
            out.append("<table><thead><tr><th>Slice</th><th>Issue</th><th>State</th></tr></thead><tbody>")
            for r in ep["rows"]:
                it = data["issues"].get(r["issue"]) or data["issues"].get(str(r["issue"])) if r["issue"] is not None else None
                cls = "done" if r["state"] == "done" else ("idle" if r["state"].startswith("idle") or r["state"] == "no issue yet" else "")
                out.append(f"<tr><td style='padding-left:{8 + 16 * r['depth']}px'>{_h(r['text'])}</td>"
                           f"<td>{_a('#' + str(r['issue']), it['url']) if it else (_h('#' + str(r['issue'])) if r['issue'] else '')}</td>"
                           f"<td><span class='st {cls}'>{_h(r['state'])}</span></td></tr>")
            out.append("</tbody></table>")
        out.append("</div>")

    out.append("<h2>People</h2><div class='grid'>")
    for p in view["people"]:
        t = p["tally"]
        tally = " · ".join(_a(f"{t[k]} {label}", tally_url(data['repo'], p['login'], k))
                           for k, label in (("commit", "commits"), ("pr_opened", "PRs opened"), ("pr_merged", "merged"),
                                            ("review", "reviews"), ("comment", "comments"), ("issue_opened", "issues opened")) if t.get(k))
        last_url = p["latest"][0]["url"] if p["latest"] else None
        out.append(f"<div class='card'><h3>{_a(p['login'], 'https://github.com/' + p['login'])} <span class='tally'>{_a('last active ' + str(p['last_days']) + 'd ago', last_url)}</span></h3>")
        out.append(f"<p class='tally'>{tally or 'no activity in the window'}</p>")
        if pn.get(p["login"]):
            out.append(f"<p class='now'>{_h(pn[p['login']])}</p>")
        if p["open_prs"]:
            out.append("<ul class='ev'>" + "".join(
                f"<li>{_a('PR #' + str(pr['number']) + ' ' + (pr['title'] or ''), pr['url'])} · {'draft' if pr['draft'] else pr['review']} · idle {pr['idle_days']}d</li>"
                for pr in p["open_prs"]) + "</ul>")
        if p["latest"]:
            out.append("<ul class='ev'>" + "".join(f"<li>{_h(e['kind'].replace('_', ' '))}: {_a(e['text'], e['url'])}</li>" for e in p["latest"]) + "</ul>")
        out.append("</div>")
    out.append("</div>")

    if audience == "leads":
        out.append("<h2>Planning (leads only)</h2>")
        out.append("<table><thead><tr><th>Person</th><th>Session hours (window)</th><th>Milestones</th><th>Review load</th><th>Flags</th></tr></thead><tbody>")
        for p in view["people"]:
            hr = view["hours"].get(p["login"], {"session_total": 0.0, "milestones": {}})
            ms = "".join(
                f"<div>{_a(k, v['url'])} {v['done']:g}/{v['total']:g}<div class='bar'><i style='width:{min(100, 100 * v['done'] / v['total']):.0f}%'></i></div></div>"
                for k, v in hr["milestones"].items())
            flags = []
            if p["last_days"] is not None and p["last_days"] > cfg["stale_epic_days"]:
                flags.append(f"idle {p['last_days']}d")
            for ep in view["epics"]:
                if p["login"] in ep["owners"] and any(f.startswith("epic untouched") for f in ep["flags"]):
                    flags.append(f"owner of untouched epic #{ep['number']}")
            sess_url = tally_url(data['repo'], p['login'], 'comment')
            out.append(f"<tr><td>{_a(p['login'], 'https://github.com/' + p['login'])}</td><td>{_a(format(hr['session_total'], 'g'), sess_url)}</td><td>{ms or '—'}</td>"
                       f"<td>{_a(str(p['review_load']), tally_url(data['repo'], p['login'], 'review_load'))}</td><td class='flag'>{_h(', '.join(flags))}</td></tr>")
        out.append("</tbody></table>")

    out.append("<p class='foot'>Every number and event links to its GitHub source. Hook and gate comments are not counted as activity. "
               "Notes are written from the collected data only and say what is waiting, never a verdict on a person. "
               "Generated by HITL Team Pulse.</p></body></html>")
    return "\n".join(out)


# ── cli ──────────────────────────────────────────────────────────────────────────────────────────
def main(argv=None, run=gh_run):
    ap = argparse.ArgumentParser(description="Team Pulse: collect from gh, render a page.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("--out", default=".hitl/pulse/data.json"); c.add_argument("--repo"); c.add_argument("--config", default=".hitl/config.yaml"); c.add_argument("--window-days", type=int)
    n = sub.add_parser("notes"); n.add_argument("--data", default=".hitl/pulse/data.json")
    r = sub.add_parser("render"); r.add_argument("--data", default=".hitl/pulse/data.json"); r.add_argument("--notes"); r.add_argument("--out"); r.add_argument("--audience", choices=["team", "leads"]); r.add_argument("--config", default=".hitl/config.yaml")
    a = ap.parse_args(argv)
    if a.cmd == "collect":
        cfg = load_config(a.config)
        if a.window_days:
            cfg["window_days"] = a.window_days
        try:
            data = collect(run, cfg, repo=a.repo)
        except RuntimeError as e:
            print(f"team-pulse: {e}", file=sys.stderr)
            return 3
        d = os.path.dirname(a.out)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(data, indent=1, sort_keys=True))
        v = derive(data)
        print(f"team-pulse: {len(v['people'])} people, {len(v['epics'])} epics, {len(v['attention'])} attention items -> {a.out}")
        return 0
    data = json.load(io.open(a.data, encoding="utf-8"))
    if a.cmd == "notes":
        print(json.dumps(notes_template(data), indent=1))
        return 0
    cfg = load_config(a.config)
    audience = a.audience or cfg["audience"]
    notes = json.load(io.open(a.notes, encoding="utf-8")) if a.notes and os.path.isfile(a.notes) else None
    page = render(data, notes, audience)
    out = a.out or os.path.join(cfg["out_dir"], "team-pulse.html" if audience == "team" else "team-pulse-leads.html")
    d = os.path.dirname(out)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(out, "w", encoding="utf-8").write(page)
    v = derive(data)
    print(f"team-pulse: wrote {out} ({audience}); {len(v['attention'])} attention items")
    for item in v["attention"][:3]:
        print(f"  - {item['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
