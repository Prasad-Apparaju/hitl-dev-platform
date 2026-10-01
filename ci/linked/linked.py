#!/usr/bin/env python3
"""Linked changes (FR-30 slice 0, EPIC #105). Design: docs/design/multi-repo-workspace/03-lld.md.

A change that spans repositories stays one change per repository; each record names its partners in
`linked_changes` ({repo, change_id, role, issue?}). This script reads a partner's state from the host
through `gh`, never from its code, and answers:

    linked.py state      [--change .hitl/current-change.yaml] [--json]
    linked.py need       docs-approved | provider-deployed --env <env> | code-merged
    linked.py fetch      owner/repo@<commit>:<path>  [--out-dir .hitl/linked]
    linked.py issue-repo epic | slice | bug | followup  [--config .hitl/config.yaml]
    linked.py link-sub   owner/repo#<epic> owner/repo#<child>
    linked.py resolve    <PREFIX>-<n>   -> prints "-R owner/repo <n>" from .hitl/config.yaml prefixes and the partners

Exit codes: 0 satisfied; 2 not satisfied, or the record is malformed; 3 the host could not be read
(which read is printed). Unreadable is never a pass.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(2)

ROLES = ("docs", "provider", "consumer", "code")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REF_RE = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{7,40}):(.+)$")
APPROVED_MARKERS = ("## ✅ Ready for Development", "## ✅ Gate Approved")
APPROVER_PERMISSIONS = ("admin", "maintain", "write")
DEPLOYED_MARKER = "## 🚀 Deployed to "
EXIT_OK, EXIT_NO, EXIT_HOST = 0, 2, 3


class HostError(Exception):
    """A read the host refused or that could not run. Carries the read that failed."""


class NotFound(Exception):
    """The partner's issue does not exist on the host: a wrong link, not an unreadable host."""


def mentions(text, change_id: str, issue: int | None = None) -> bool:
    """The change id as a whole word (GH-14 must not match GH-142 or a PR that never names it), or the
    host's own cross-reference form `#<n>` (every merged issue-branch PR in the field uses it)."""
    t = str(text or "")
    if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(str(change_id)), t):
        return True
    return issue is not None and re.search(r"(?<![A-Za-z0-9])#%d(?![0-9])" % issue, t) is not None


class Malformed(Exception):
    pass


# ---------------------------------------------------------------------------
# The one way to the host
# ---------------------------------------------------------------------------

def gh_run(args: list[str]) -> tuple[int, str]:
    if shutil.which("gh") is None:
        raise HostError("gh is not installed (https://cli.github.com); the partner's state cannot be read")
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise HostError("gh %s timed out" % " ".join(args[:3]))
    return r.returncode, r.stdout


def gh_json(run, path: str, paginate: bool = False):
    """GET one API path as JSON; raise HostError on a non-zero exit or unparseable body."""
    args = ["api", path]
    if paginate:
        args += ["--paginate", "--slurp"]
    code, out = run(args)
    if code != 0:
        raise HostError("gh api %s failed (exit %d)" % (path, code))
    try:
        data = json.loads(out or "null")
    except json.JSONDecodeError:
        raise HostError("gh api %s returned something that is not JSON" % path)
    if paginate and isinstance(data, list) and data and isinstance(data[0], list):
        data = [x for page in data for x in page]
    return data


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------

def _digits(change_id) -> int | None:
    m = re.search(r"(\d+)\s*$", str(change_id or ""))
    return int(m.group(1)) if m else None


def load_change(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise Malformed("%s could not be read: %s" % (path, e.__class__.__name__))
    if d is None:
        return {}
    if not isinstance(d, dict):
        raise Malformed("%s is not a mapping" % path)
    return d


def partners(change: dict) -> list[dict]:
    """The validated linked_changes list. Raises Malformed before any host read."""
    raw = change.get("linked_changes")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise Malformed("linked_changes must be a list")
    out = []
    for i, e in enumerate(raw):
        if not isinstance(e, dict):
            raise Malformed("linked_changes[%d] is not a mapping" % i)
        repo, cid, role = e.get("repo"), e.get("change_id"), e.get("role")
        if not isinstance(repo, str) or not REPO_RE.match(repo):
            raise Malformed("linked_changes[%d].repo %r is not owner/name" % (i, repo))
        if role not in ROLES:
            raise Malformed("linked_changes[%d].role %r is not one of %s" % (i, role, list(ROLES)))
        issue = e.get("issue", _digits(cid))
        if issue is None or not str(issue).isdigit():
            raise Malformed("linked_changes[%d] has no issue number (change_id %r has no digits and no issue: field)" % (i, cid))
        out.append({"repo": repo, "change_id": str(cid), "role": role, "issue": int(issue)})
    return out


# ---------------------------------------------------------------------------
# Reading one partner from the host
# ---------------------------------------------------------------------------

def _first_line(body) -> str:
    return (str(body or "").strip().splitlines() or [""])[0].strip()


def read_partner(run, p: dict, own_repo: str | None = None, own_change_id: str | None = None) -> dict:
    repo, n = p["repo"], p["issue"]
    owner = repo.split("/")[0]
    # the branch, by the issue/<n>- convention
    branch = None
    try:
        for b in gh_json(run, "repos/%s/branches?per_page=100" % repo, paginate=True) or []:
            name = b.get("name") if isinstance(b, dict) else None
            if isinstance(name, str) and name.startswith("issue/%d-" % n):
                branch = name
                break
    except HostError:
        branch = None  # the record read is optional; comments decide
    record, backlink, record_ref = None, None, None

    def _read_record(ref):
        doc = gh_json(run, "repos/%s/contents/.hitl/current-change.yaml?ref=%s" % (repo, ref))
        body = base64.b64decode((doc or {}).get("content", "") or "").decode("utf-8", "replace")
        rec = yaml.safe_load(body)
        return rec if isinstance(rec, dict) else None

    if branch:
        try:
            record, record_ref = _read_record(branch), branch
        except (HostError, yaml.YAMLError, ValueError):
            record = None
    code, out = run(["api", "repos/%s/issues/%d" % (repo, n)])
    if code != 0:
        probe, _ = run(["api", "repos/%s" % repo])
        if probe == 0:
            raise NotFound("%s has no issue %d (the link names a wrong change id or issue)" % (repo, n))
        raise HostError("gh api repos/%s/issues/%d failed (exit %d)" % (repo, n, code))
    try:
        issue = json.loads(out or "null")
    except json.JSONDecodeError:
        raise HostError("gh api repos/%s/issues/%d returned something that is not JSON" % (repo, n))
    comments = gh_json(run, "repos/%s/issues/%d/comments?per_page=100" % (repo, n), paginate=True) or []
    # a marker counts only from an author with write access on the repository (#146): a hand-typed
    # "Gate Approved" from anyone must not approve a design
    perm_cache: dict = {}

    def _approver(login) -> bool:
        if not login:
            return False
        if login not in perm_cache:
            try:
                d = gh_json(run, "repos/%s/collaborators/%s/permission" % (repo, login))
                perm_cache[login] = (d or {}).get("permission") in APPROVER_PERMISSIONS
            except HostError:
                perm_cache[login] = False
        return perm_cache[login]

    approved_firsts, ignored = [], []
    for c in comments:
        if not isinstance(c, dict):
            continue
        f = _first_line(c.get("body"))
        if f == APPROVED_MARKERS[0] or f.startswith(APPROVED_MARKERS[1]) or f.startswith(DEPLOYED_MARKER):
            if _approver(((c.get("user") or {}).get("login"))):
                approved_firsts.append(f)
            else:
                ignored.append(f)
    approved_by = None
    if any(f == APPROVED_MARKERS[0] or f.startswith(APPROVED_MARKERS[1]) for f in approved_firsts):
        approved_by = "comment"
    prs = []
    if branch:
        try:
            prs += gh_json(run, "repos/%s/pulls?state=all&head=%s:%s" % (repo, owner, branch)) or []
        except HostError:
            pass
    try:
        # the search matches loosely (GH-14 found a PR that never names it): a hit counts only when its
        # head branch is the partner's issue branch (kept on the PR after the branch is deleted) or the
        # change id, or the host's #<n> form, is a whole word in its title or body
        seen = {x.get("number") for x in prs if isinstance(x, dict)}
        for q in (p["change_id"], "%d" % n):
            found = gh_json(run, "search/issues?q=repo:%s+is:pr+%s" % (repo, q))
            for x in (found or {}).get("items", []) if isinstance(found, dict) else []:
                if not isinstance(x, dict) or x.get("number") in seen:
                    continue
                named = mentions(x.get("title"), p["change_id"], n) or mentions(x.get("body"), p["change_id"], n)
                if not named:
                    try:
                        pr = gh_json(run, "repos/%s/pulls/%s" % (repo, x.get("number")))
                        named = str(((pr or {}).get("head") or {}).get("ref", "")).startswith("issue/%d-" % n)
                        if named and pr.get("merged_at"):
                            x = dict(x, pull_request=dict(x.get("pull_request") or {}, merged_at=pr["merged_at"]))
                    except HostError:
                        named = False
                if named:
                    seen.add(x.get("number"))
                    prs.append(x)
    except HostError as e:
        if not prs:
            raise e
    merged = any(isinstance(x, dict) and (x.get("merged_at") or (x.get("pull_request") or {}).get("merged_at")) for x in prs)
    if record is None and merged:
        # the branch is gone after merge: the record lives at the PR's merge commit (#144)
        for x in prs:
            if not isinstance(x, dict) or not (x.get("merged_at") or (x.get("pull_request") or {}).get("merged_at")):
                continue
            sha = x.get("merge_commit_sha")
            if not sha and x.get("number"):
                try:
                    sha = (gh_json(run, "repos/%s/pulls/%s" % (repo, x["number"])) or {}).get("merge_commit_sha")
                except HostError:
                    sha = None
            if sha:
                try:
                    record, record_ref = _read_record(sha), sha[:7]
                    if record is not None:
                        break
                except (HostError, yaml.YAMLError, ValueError):
                    record = None
    if record is not None and own_repo and own_change_id:
        backlink = any(isinstance(y, dict) and y.get("repo") == own_repo and str(y.get("change_id")) == str(own_change_id)
                       for y in (record.get("linked_changes") or []) if isinstance(record.get("linked_changes"), list))
    if record is not None and record.get("status") == "implementation-approved":
        approved_by = "record"
    if merged and approved_by is None:
        approved_by = "merged"
    # deployments: the record's list first, then the issue comment (#144)
    deployed = set()
    for d in (record or {}).get("deployments") or []:
        if isinstance(d, dict) and d.get("environment"):
            deployed.add(str(d["environment"]))
    deploy_step_done = any(isinstance(st, dict) and st.get("key") == "deploy" and st.get("status") == "done"
                           for st in ((record or {}).get("workflow") or {}).get("steps") or []) if record else False
    deployed |= {f[len(DEPLOYED_MARKER):].strip().strip("`*") for f in approved_firsts if f.startswith(DEPLOYED_MARKER)}
    deployed = sorted(deployed)
    return {
        "repo": repo, "change_id": p["change_id"], "role": p["role"], "issue": n, "branch": branch,
        "record_ref": record_ref,
        "issue_state": (issue or {}).get("state") if isinstance(issue, dict) else None,
        "status": (record or {}).get("status") if record else None,
        "approved": approved_by is not None, "approved_by": approved_by,
        "merged": merged, "deployed": deployed, "deploy_step_done": deploy_step_done,
        "ignored_markers": len(ignored), "backlink": backlink,
    }


def fmt(s: dict) -> str:
    if s["status"]:
        rec = "%s@%s" % (s["status"], s.get("record_ref") or "?")
    else:
        rec = "none (no issue/%d- branch, no merged PR)" % s["issue"] if not s.get("branch") else "none"
    extra = "" if s["backlink"] is None else " backlink=%s" % ("yes" if s["backlink"] else "no")
    if s.get("ignored_markers"):
        extra += " ignored-markers=%d(not from a writer)" % s["ignored_markers"]
    return "%-8s %-10s %-28s issue=%s record=%s approved=%s merged=%s deployed=%s%s" % (
        s["role"], s["change_id"], s["repo"], s.get("issue_state") or "?", rec,
        "yes" if s["approved"] else "no", "yes" if s["merged"] else "no",
        "[%s]" % ",".join(s["deployed"]), extra)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_state(run, change_path: str, as_json: bool, own_repo: str | None) -> int:
    change = load_change(change_path)
    ps = partners(change)
    if not ps:
        print("no linked changes")
        return EXIT_OK
    states = [read_partner(run, p, own_repo, change.get("change_id")) for p in ps]
    if as_json:
        print(json.dumps(states, indent=2))
    else:
        for s in states:
            print(fmt(s))
    return EXIT_OK


def cmd_need(run, what: str, env: str | None, change_path: str, own_repo: str | None) -> int:
    change = load_change(change_path)
    ps = partners(change)
    role = {"docs-approved": "docs", "provider-deployed": "provider", "code-merged": "code"}[what]
    mine = [p for p in ps if p["role"] == role]
    if not mine:
        print("no linked changes" if not ps else "no %s partner declared" % role)
        return EXIT_OK
    waiting = []
    for p in mine:
        s = read_partner(run, p, own_repo, change.get("change_id"))
        print(fmt(s))
        if what == "docs-approved" and not s["approved"]:
            waiting.append("%s %s is not approved (%s, no approval comment, no merged PR)" % (s["repo"], s["change_id"], ("record status %s" % s["status"]) if s["status"] else ("no record: no issue/%d- branch" % s["issue"] if not s.get("branch") else "record unreadable")))
        elif what == "provider-deployed":
            if not s["merged"]:
                waiting.append("%s %s has no merged PR" % (s["repo"], s["change_id"]))
            elif env not in s["deployed"]:
                how = "deploy step done but no environment recorded (add deployments: [{environment: %s}] to its record, or the Deployed comment)" % env if s.get("deploy_step_done") else ("deployed: %s" % ", ".join(s["deployed"]) if s["deployed"] else "no deployment recorded")
                waiting.append("%s %s is not deployed to %s (%s)" % (s["repo"], s["change_id"], env, how))
        elif what == "code-merged" and not s["merged"]:
            waiting.append("%s %s has not merged" % (s["repo"], s["change_id"]))
    if waiting:
        print("waiting on: " + "; ".join(waiting))
        return EXIT_NO
    print("satisfied: %s" % what)
    return EXIT_OK


def cmd_fetch(run, ref: str, out_dir: str) -> int:
    m = REF_RE.match(ref)
    if not m:
        print("refused: a pinned reference is owner/repo@<commit sha>:<path>; a branch name is not a pin (%s)" % ref)
        return EXIT_NO
    repo, commit, path = m.group(1), m.group(2).lower(), m.group(3).lstrip("/")
    if ".." in path.split("/"):
        print("refused: the path escapes (%s)" % path)
        return EXIT_NO
    doc = gh_json(run, "repos/%s/contents/%s?ref=%s" % (repo, path, commit))
    if not isinstance(doc, dict) or doc.get("encoding") != "base64":
        raise HostError("repos/%s/contents/%s@%s is not a file" % (repo, path, commit))
    body = base64.b64decode(doc.get("content", "") or "")
    dest = os.path.join(out_dir, *repo.split("/"), commit, *path.split("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(body)
    print(dest)
    return EXIT_OK


def load_config(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def cmd_issue_repo(kind: str, config_path: str) -> int:
    cfg = load_config(config_path)
    issues = cfg.get("issues") if isinstance(cfg.get("issues"), dict) else {}
    key = "epics" if kind == "epic" else "slices"
    repo = issues.get(key)
    if isinstance(repo, str) and REPO_RE.match(repo):
        print("-R %s" % repo)
    return EXIT_OK


def cmd_resolve(ident: str, config_path: str, change_path: str) -> int:
    """<PREFIX>-<n> -> "-R owner/repo <n>" from config `prefixes:` (and `repo`/`change_id_prefix`) and the partners."""
    m = re.fullmatch(r"([A-Za-z][A-Za-z0-9]*)-(\d+)", ident.strip())
    if not m:
        if ident.strip().isdigit():
            print("ambiguous: a bare number; use <PREFIX>-%s" % ident.strip())
        else:
            print("not a change id: %s" % ident)
        return EXIT_NO
    prefix, n = m.group(1), m.group(2)
    cfg = load_config(config_path)
    table = {}
    own = cfg.get("change_id_prefix") or "GH"
    if isinstance(cfg.get("repo"), str) and REPO_RE.match(cfg["repo"]):
        table[str(own).upper()] = cfg["repo"]
    for k, v in (cfg.get("prefixes") or {}).items() if isinstance(cfg.get("prefixes"), dict) else []:
        if isinstance(v, str) and REPO_RE.match(v):
            table[str(k).upper()] = v
    try:
        for p in partners(load_change(change_path)):
            pm = re.match(r"([A-Za-z][A-Za-z0-9]*)-\d+$", p["change_id"])
            if pm:
                table.setdefault(pm.group(1).upper(), p["repo"])
    except Malformed:
        pass
    if prefix.upper() == str(own).upper():
        print(n)      # this repository, no -R needed
        return EXIT_OK
    repo = table.get(prefix.upper())
    if repo is None:
        print("unknown prefix %s; add prefixes: { %s: owner/repo } to .hitl/config.yaml" % (prefix, prefix))
        return EXIT_NO
    print("-R %s %s" % (repo, n))
    return EXIT_OK


def cmd_link_sub(run, epic: str, child: str) -> int:
    m1, m2 = re.match(r"^(.+)#(\d+)$", epic), re.match(r"^(.+)#(\d+)$", child)
    if not (m1 and m2 and REPO_RE.match(m1.group(1)) and REPO_RE.match(m2.group(1))):
        print("refused: give owner/repo#<epic> owner/repo#<child>")
        return EXIT_NO
    erepo, en, crepo, cn = m1.group(1), int(m1.group(2)), m2.group(1), int(m2.group(2))
    try:
        child_doc = gh_json(run, "repos/%s/issues/%d" % (crepo, cn))
        cid = (child_doc or {}).get("id")
        code, _ = run(["api", "repos/%s/issues/%d/sub_issues" % (erepo, en), "-X", "POST", "-F", "sub_issue_id=%s" % cid])
        if code == 0:
            print("linked %s#%d under %s#%d" % (crepo, cn, erepo, en))
            return EXIT_OK
    except HostError:
        pass
    code, _ = run(["issue", "comment", str(en), "-R", erepo, "--body", "Slice: %s#%d" % (crepo, cn)])
    print("sub-issue link refused by the host; commented on %s#%d instead" % (erepo, en) if code == 0
          else "could not link or comment on %s#%d" % (erepo, en))
    return EXIT_OK


def main(argv=None, run=gh_run) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("state"); s.add_argument("--change", default=".hitl/current-change.yaml"); s.add_argument("--json", action="store_true"); s.add_argument("--repo", help="this repository as owner/name, for the backlink check")
    n = sub.add_parser("need"); n.add_argument("what", choices=["docs-approved", "provider-deployed", "code-merged"]); n.add_argument("--env"); n.add_argument("--change", default=".hitl/current-change.yaml"); n.add_argument("--repo")
    f = sub.add_parser("fetch"); f.add_argument("ref"); f.add_argument("--out-dir", default=".hitl/linked")
    i = sub.add_parser("issue-repo"); i.add_argument("kind", choices=["epic", "slice", "bug", "followup"]); i.add_argument("--config", default=".hitl/config.yaml")
    l = sub.add_parser("link-sub"); l.add_argument("epic"); l.add_argument("child")
    r = sub.add_parser("resolve"); r.add_argument("id"); r.add_argument("--config", default=".hitl/config.yaml"); r.add_argument("--change", default=".hitl/current-change.yaml")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "state":
            return cmd_state(run, a.change, a.json, a.repo)
        if a.cmd == "need":
            if a.what == "provider-deployed" and not a.env:
                print("need provider-deployed takes --env <environment>")
                return EXIT_NO
            return cmd_need(run, a.what, a.env, a.change, a.repo)
        if a.cmd == "fetch":
            return cmd_fetch(run, a.ref, a.out_dir)
        if a.cmd == "issue-repo":
            return cmd_issue_repo(a.kind, a.config)
        if a.cmd == "link-sub":
            return cmd_link_sub(run, a.epic, a.child)
        if a.cmd == "resolve":
            return cmd_resolve(a.id, a.config, a.change)
    except Malformed as e:
        print("MALFORMED: %s" % e)
        return EXIT_NO
    except NotFound as e:
        print("not found: %s" % e)
        return EXIT_NO
    except HostError as e:
        print("host unreadable: %s" % e)
        return EXIT_HOST
    return EXIT_NO


if __name__ == "__main__":
    sys.exit(main())
