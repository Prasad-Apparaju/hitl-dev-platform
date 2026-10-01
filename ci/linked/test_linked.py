#!/usr/bin/env python3
"""Conformance for linked changes (FR-30 slice 0 / test plan NEG-*, CHK-*). The host is a fake `run`
fed canned gh responses; the fail-closed cases feed it the wrong thing."""
import base64
import json
import os
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import linked as L  # noqa: E402

DOCS = "org/docs"
SVC = "org/svc"


def b64(text):
    return base64.b64encode(text.encode()).decode()


class Host:
    """Canned responses keyed by API path prefix; records every call."""

    def __init__(self, routes=None, fail=(), installed=True):
        self.routes = dict(routes or {})
        self.fail = set(fail)
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == "api":
            path = args[1]
            for pat in self.fail:
                if path.startswith(pat):
                    return 1, ""
            for key, val in self.routes.items():
                if path.startswith(key):
                    return 0, val if isinstance(val, str) else json.dumps(val)
            return 1, ""
        if args[0] == "issue":
            return 0, ""
        return 1, ""


def change(path, entries, change_id="SCM-12"):
    yaml.safe_dump({"change_id": change_id, "linked_changes": entries}, open(path, "w"))
    return str(path)


def docs_partner(status="planning", comments=(), merged=False, backlink=False, branch=True):
    rec = {"change_id": "GH-40", "status": status}
    if backlink:
        rec["linked_changes"] = [{"repo": SVC, "change_id": "SCM-12", "role": "code"}]
    routes = {
        "repos/%s/branches" % DOCS: [{"name": "main"}, {"name": "issue/41-other"}] + ([{"name": "issue/40-scm-design"}] if branch else []),
        "repos/%s/contents/.hitl/current-change.yaml" % DOCS: {"content": b64(yaml.safe_dump(rec)), "encoding": "base64"},
        "repos/%s/issues/40/comments" % DOCS: [{"body": c, "user": {"login": "maintainer"}} for c in comments],
        "repos/%s/issues/40" % DOCS: {"state": "open", "id": 4040},
        "repos/%s/collaborators/maintainer/permission" % DOCS: {"permission": "write"},
        "repos/%s/collaborators/stranger/permission" % DOCS: {"permission": "read"},
        "repos/%s/pulls?" % DOCS: [{"number": 7, "merged_at": "2026-09-30T00:00:00Z"}] if merged else [{"number": 7, "merged_at": None}],
        "search/issues": {"items": []},
    }
    return routes


def test_chk3_no_linked_changes_is_satisfied_with_zero_host_reads(tmp_path):
    p = tmp_path / "c.yaml"
    yaml.safe_dump({"change_id": "GH-1"}, open(p, "w"))
    h = Host()
    assert L.main(["need", "docs-approved", "--change", str(p)], run=h) == 0
    assert L.main(["state", "--change", str(p)], run=h) == 0
    assert h.calls == []


def test_neg1_unapproved_docs_partner_blocks(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    h = Host(docs_partner(status="planning"))
    assert L.main(["need", "docs-approved", "--change", p], run=h) == 2
    out = capsys.readouterr().out
    assert "waiting on: org/docs GH-40 is not approved" in out


@pytest.mark.parametrize("kw", [
    dict(status="implementation-approved"),
    dict(comments=["## ✅ Ready for Development\n\nall gates passed"]),
    dict(comments=["## ✅ Gate Approved — LLD review\n\nok"]),
    dict(merged=True),
], ids=["record", "ready-comment", "gate-comment", "merged-pr"])
def test_chk1_each_approval_signal_alone_approves(tmp_path, kw):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    assert L.main(["need", "docs-approved", "--change", p], run=Host(docs_partner(**kw))) == 0


def test_neg8_a_prose_mention_is_not_the_marker(tmp_path):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    h = Host(docs_partner(comments=["I think the gate approved it yesterday", "Gate Approved by me"]))
    assert L.main(["need", "docs-approved", "--change", p], run=h) == 2


def test_neg2_unreadable_record_and_comments_is_exit_3_never_0(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    h = Host(docs_partner(status="implementation-approved"), fail=("repos/%s/contents" % DOCS, "repos/%s/issues/40" % DOCS))
    assert L.main(["need", "docs-approved", "--change", p], run=h) == 3
    assert "host unreadable" in capsys.readouterr().out


def test_neg9_gh_missing_is_exit_3(tmp_path, monkeypatch, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    monkeypatch.setattr(L.shutil, "which", lambda name: None)
    assert L.main(["need", "docs-approved", "--change", p]) == 3
    assert "gh is not installed" in capsys.readouterr().out


def test_chk6_branch_absent_falls_back_to_comments(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    h = Host(docs_partner(branch=False, comments=["## ✅ Ready for Development"]))
    assert L.main(["state", "--change", p], run=h) == 0
    assert "record=none (no issue/40- branch, no merged PR) approved=yes" in capsys.readouterr().out


def test_chk2_state_shows_backlink(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    assert L.main(["state", "--change", p, "--repo", SVC], run=Host(docs_partner(backlink=True))) == 0
    assert "backlink=yes" in capsys.readouterr().out
    assert L.main(["state", "--change", p, "--repo", SVC], run=Host(docs_partner(backlink=False))) == 0
    assert "backlink=no" in capsys.readouterr().out


def test_chk4_two_docs_partners_one_unapproved_names_the_other(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"},
                                      {"repo": "org/docs2", "change_id": "GH-9", "role": "docs"}])
    routes = docs_partner(status="implementation-approved")
    routes.update({
        "repos/org/docs2/branches": [],
        "repos/org/docs2/issues/9/comments": [],
        "repos/org/docs2/issues/9": {"state": "open"},
        "repos/org/docs2/pulls?": [],
    })
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2
    out = capsys.readouterr().out
    assert "org/docs2 GH-9 is not approved" in out and "org/docs GH-40 is not approved" not in out


def provider(merged=True, deployed=("prod",)):
    return {
        "repos/%s/branches" % SVC: [{"name": "issue/14-endpoint"}],
        "repos/%s/contents/.hitl/current-change.yaml" % SVC: {"content": b64("change_id: EMAIL-14\nstatus: merged\n"), "encoding": "base64"},
        "repos/%s/issues/14/comments" % SVC: [{"body": "## 🚀 Deployed to %s\n\n**Deployed at:** x" % e, "user": {"login": "maintainer"}} for e in deployed],
        "repos/%s/issues/14" % SVC: {"state": "closed"},
        "repos/%s/collaborators/maintainer/permission" % SVC: {"permission": "admin"},
        "repos/%s/pulls?" % SVC: [{"number": 3, "merged_at": "2026-09-30T00:00:00Z" if merged else None}],
        "search/issues": {"items": []},
    }


def test_chk5_provider_merged_and_deployed_to_the_asked_env(tmp_path):
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "EMAIL-14", "role": "provider"}])
    assert L.main(["need", "provider-deployed", "--env", "prod", "--change", p], run=Host(provider(deployed=("staging", "prod")))) == 0


def test_neg3_deployed_to_another_env_blocks(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "EMAIL-14", "role": "provider"}])
    assert L.main(["need", "provider-deployed", "--env", "prod", "--change", p], run=Host(provider(deployed=("staging",)))) == 2
    assert "not deployed to prod (deployed: staging)" in capsys.readouterr().out


def test_neg4_deployed_comment_without_a_merged_pr_blocks(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "EMAIL-14", "role": "provider"}])
    assert L.main(["need", "provider-deployed", "--env", "prod", "--change", p], run=Host(provider(merged=False))) == 2
    assert "has no merged PR" in capsys.readouterr().out


def test_provider_deployed_requires_env(tmp_path):
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "EMAIL-14", "role": "provider"}])
    assert L.main(["need", "provider-deployed", "--change", p], run=Host()) == 2


def test_neg5_code_partner_with_open_pr_blocks_the_fold(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "SCM-12", "role": "code"}], change_id="GH-40")
    routes = provider(merged=False)
    routes["repos/%s/branches" % SVC] = [{"name": "issue/12-x"}]
    routes["repos/%s/issues/12/comments" % SVC] = []
    routes["repos/%s/issues/12" % SVC] = {"state": "open"}
    assert L.main(["need", "code-merged", "--change", p], run=Host(routes)) == 2
    assert "has not merged" in capsys.readouterr().out


@pytest.mark.parametrize("entry", [
    {"repo": DOCS, "change_id": "GH-40", "role": "upstream"},
    {"repo": "docs", "change_id": "GH-40", "role": "docs"},
    {"repo": DOCS, "change_id": "DOCS", "role": "docs"},
    "GH-40",
], ids=["role", "repo", "no-digits", "not-a-mapping"])
def test_neg6_malformed_entries_fail_before_any_host_read(tmp_path, entry, capsys):
    p = change(tmp_path / "c.yaml", [entry])
    h = Host()
    assert L.main(["need", "docs-approved", "--change", p], run=h) == 2
    assert "MALFORMED" in capsys.readouterr().out and h.calls == []


def test_neg7_fetch_refuses_a_branch_reference(tmp_path, capsys):
    h = Host()
    assert L.main(["fetch", "org/docs@main:docs/x.md", "--out-dir", str(tmp_path)], run=h) == 2
    assert "not a pin" in capsys.readouterr().out and h.calls == []
    assert L.main(["fetch", "org/docs@abc1234:../x.md", "--out-dir", str(tmp_path)], run=h) == 2


def test_chk7_fetch_writes_the_pinned_file_and_prints_the_path(tmp_path, capsys):
    sha = "0123456789abcdef0123456789abcdef01234567"
    h = Host({"repos/org/docs/contents/docs/02-design/lld/scm.md?ref=%s" % sha: {"content": b64("# LLD v1"), "encoding": "base64"}})
    assert L.main(["fetch", "org/docs@%s:docs/02-design/lld/scm.md" % sha, "--out-dir", str(tmp_path)], run=h) == 0
    path = capsys.readouterr().out.strip()
    assert path == os.path.join(str(tmp_path), "org", "docs", sha, "docs", "02-design", "lld", "scm.md")
    assert open(path).read() == "# LLD v1"
    h.routes["repos/org/docs/contents/docs/02-design/lld/scm.md?ref=%s" % sha] = {"content": b64("# LLD v2"), "encoding": "base64"}
    assert L.main(["fetch", "org/docs@%s:docs/02-design/lld/scm.md" % sha, "--out-dir", str(tmp_path)], run=h) == 0
    assert open(path).read() == "# LLD v2"


def test_fetch_of_a_missing_file_is_exit_3(tmp_path):
    assert L.main(["fetch", "org/docs@abcdef1:docs/none.md", "--out-dir", str(tmp_path)], run=Host()) == 3


def test_chk8_issue_repo_reads_the_config(tmp_path, capsys):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("issues:\n  epics: org/docs\n  slices: org/svc\n")
    assert L.main(["issue-repo", "epic", "--config", str(cfg)]) == 0
    assert capsys.readouterr().out.strip() == "-R org/docs"
    for kind in ("slice", "bug", "followup"):
        assert L.main(["issue-repo", kind, "--config", str(cfg)]) == 0
        assert capsys.readouterr().out.strip() == "-R org/svc"
    assert L.main(["issue-repo", "epic", "--config", str(tmp_path / "none.yaml")]) == 0
    assert capsys.readouterr().out.strip() == ""
    cfg.write_text("issues:\n  epics: not a repo\n")
    assert L.main(["issue-repo", "epic", "--config", str(cfg)]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_chk9_link_sub_posts_the_child_id_or_comments(capsys):
    h = Host({"repos/org/svc/issues/12": {"id": 777}, "repos/org/docs/issues/40/sub_issues": {}})
    assert L.main(["link-sub", "org/docs#40", "org/svc#12"], run=h) == 0
    post = [c for c in h.calls if "sub_issues" in c[1]]
    assert post and "-F" in post[0] and "sub_issue_id=777" in post[0]
    assert "linked org/svc#12 under org/docs#40" in capsys.readouterr().out

    class Refusing(Host):
        def __call__(self, args):
            self.calls.append(args)
            if args[0] == "api" and "sub_issues" in args[1]:
                return 1, ""
            return super().__call__(args)
    h = Refusing({"repos/org/svc/issues/12": {"id": 777}})
    assert L.main(["link-sub", "org/docs#40", "org/svc#12"], run=h) == 0
    assert any(c[0] == "issue" and c[1] == "comment" for c in h.calls)
    assert L.main(["link-sub", "docs#40", "org/svc#12"], run=h) == 2


def test_chk10_hostile_host_bodies_never_traceback(tmp_path):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    routes = docs_partner()
    routes["repos/%s/contents/.hitl/current-change.yaml" % DOCS] = {"content": b64("- a\n- b\n"), "encoding": "base64"}
    routes["repos/%s/issues/40/comments" % DOCS] = "not json"
    code = L.main(["need", "docs-approved", "--change", p], run=Host(routes))
    assert code in (2, 3)
    routes["repos/%s/issues/40/comments" % DOCS] = [{"body": None}, "x", {}]
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2
    yaml.safe_dump({"change_id": "X", "linked_changes": "nope"}, open(p, "w"))
    assert L.main(["state", "--change", p], run=Host()) == 2
    open(p, "w").write("- a\n")
    assert L.main(["state", "--change", p], run=Host()) == 2


def test_missing_change_file_means_no_linked_changes(tmp_path):
    assert L.main(["need", "docs-approved", "--change", str(tmp_path / "none.yaml")], run=Host()) == 0


# ---------------------------------------------------------------------------
# Round 1 review: the PR search matches loosely; a 404 is a wrong link, not an unreadable host
# ---------------------------------------------------------------------------

def test_neg10_a_search_hit_that_never_names_the_change_id_does_not_approve(tmp_path, capsys):
    """S1: GH-14's search found PR #57 (head issue/56-first-pass-wiring) with no GH- id in it at all."""
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-14", "role": "docs"}])
    routes = {
        "repos/%s/branches" % DOCS: [{"name": "main"}],
        "repos/%s/issues/14/comments" % DOCS: [],
        "repos/%s/issues/14" % DOCS: {"state": "closed"},
        "search/issues": {"items": [{"number": 57, "title": "first pass wiring", "body": "closes the gap", "pull_request": {"merged_at": "2026-08-01T00:00:00Z"}}]},
    }
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2
    assert "approved=no merged=no" in capsys.readouterr().out
    # the same PR naming the id as a whole word counts; GH-142 does not count for GH-14
    routes["search/issues"] = {"items": [{"number": 57, "title": "GH-142 release", "body": "", "pull_request": {"merged_at": "2026-08-01T00:00:00Z"}}]}
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2
    routes["search/issues"] = {"items": [{"number": 57, "title": "wiring (GH-14)", "body": "", "pull_request": {"merged_at": "2026-08-01T00:00:00Z"}}]}
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 0


def test_mentions_is_a_whole_word_match():
    assert L.mentions("fixes GH-14 today", "GH-14") and L.mentions("(GH-14)", "GH-14") and L.mentions("GH-14", "GH-14")
    assert not L.mentions("GH-142", "GH-14") and not L.mentions("GH-14a", "GH-14") and not L.mentions("", "GH-14")
    assert L.mentions("wrapper drift (#60)", "GH-60", 60) and not L.mentions("fixes #601", "GH-60", 60) and not L.mentions("#60", "GH-60")


def test_neg11_a_merged_pr_on_a_deleted_branch_is_found_by_its_hash_form_or_head_ref(tmp_path, capsys):
    """Round 2 N1: GH-60's PR #64 merged from issue/60-wrapper-drift, branch deleted, title says #60."""
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-60", "role": "docs"}])
    base = {
        "repos/%s/branches" % DOCS: [{"name": "main"}],
        "repos/%s/issues/60/comments" % DOCS: [],
        "repos/%s/issues/60" % DOCS: {"state": "closed"},
        "search/issues?q=repo:%s+is:pr+GH-60" % DOCS: {"items": []},
    }
    routes = dict(base)
    routes["search/issues?q=repo:%s+is:pr+60" % DOCS] = {"items": [{"number": 64, "title": "wrapper drift (#60)", "body": "", "pull_request": {"merged_at": "2026-08-01T00:00:00Z"}}]}
    routes["repos/%s/pulls/64" % DOCS] = {"head": {"ref": "issue/60-wrapper-drift"}, "merged_at": "2026-08-01T00:00:00Z"}
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 0
    assert "approved=yes merged=yes" in capsys.readouterr().out
    # head ref alone, title silent, body silent: the pull read tells the branch
    routes = dict(base)
    routes["search/issues?q=repo:%s+is:pr+60" % DOCS] = {"items": [{"number": 64, "title": "wrapper drift", "body": "", "pull_request": {}}]}
    routes["repos/%s/pulls/64" % DOCS] = {"head": {"ref": "issue/60-wrapper-drift"}, "merged_at": "2026-08-01T00:00:00Z"}
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 0
    # a PR for #601 on another branch is not GH-60's
    routes = dict(base)
    routes["search/issues?q=repo:%s+is:pr+60" % DOCS] = {"items": [{"number": 70, "title": "fixes #601", "body": "", "pull_request": {"merged_at": "2026-08-01T00:00:00Z"}}]}
    routes["repos/%s/pulls/70" % DOCS] = {"head": {"ref": "issue/601-x"}, "merged_at": "2026-08-01T00:00:00Z"}
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2


def test_d1_a_missing_partner_issue_is_exit_2_not_found(tmp_path, capsys):
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-999", "role": "docs"}])
    routes = {"repos/%s/branches" % DOCS: [], "repos/%s" % DOCS: {"name": "docs"}}   # the repo exists, the issue does not
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes, fail=("repos/%s/issues/999" % DOCS,))) == 2
    assert "not found: org/docs has no issue 999" in capsys.readouterr().out
    # the repo itself unreadable: still exit 3
    assert L.main(["need", "docs-approved", "--change", p], run=Host({"repos/%s/branches" % DOCS: []})) == 3


def test_m2_reference_commit_is_lowercase_hex(tmp_path):
    assert L.main(["fetch", "org/docs@ABCDEF1:docs/x.md", "--out-dir", str(tmp_path)], run=Host()) == 2


def test_pfx1_a_prefixed_change_id_still_yields_its_issue_number(tmp_path):
    """PFX-1: gen_change --stub SCM-12 writes change_id SCM-12, and the branch reconcile matches issue/12-x."""
    import subprocess
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    gen = os.path.join(root, "ci", "first-pass", "gen_change.py")
    r = subprocess.run([sys.executable, gen, "--stub", "SCM-12", "issue/12-x", "2.15.0"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rec = yaml.safe_load(r.stdout)
    assert rec["change_id"] == "SCM-12"
    f = tmp_path / "c.yaml"
    f.write_text('change_id: "SCM-12"\nworkflow:\n  id: development\n  steps:\n    - { n: 1, key: issue, label: "Issue", status: current }\n')
    steps = os.path.join(root, "ai", "claude", "hooks", "_steps.sh")
    r = subprocess.run(["bash", "-c", "source '%s'; hitl_branch_reconcile '%s' issue/12-x; hitl_branch_reconcile '%s' issue/13-x" % (steps, f, f)], capture_output=True, text=True)
    assert r.stdout.split() == ["match", "mismatch"], r.stdout + r.stderr


# ---------------------------------------------------------------------------
# 2.16.1: #146 approver permission, #144 deployments from the record and the merge commit, #145 resolve
# ---------------------------------------------------------------------------

def test_neg12_a_marker_from_a_non_writer_does_not_approve(tmp_path, capsys):
    """#146 item 2: a hand-typed Gate Approved from anyone must not approve a design."""
    p = change(tmp_path / "c.yaml", [{"repo": DOCS, "change_id": "GH-40", "role": "docs"}])
    routes = docs_partner()
    routes["repos/%s/issues/40/comments" % DOCS] = [{"body": "## ✅ Gate Approved — LLD", "user": {"login": "stranger"}}]
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2
    assert "ignored-markers=1" in capsys.readouterr().out
    # the permission read failing is not a pass either
    routes["repos/%s/issues/40/comments" % DOCS] = [{"body": "## ✅ Gate Approved — LLD", "user": {"login": "nobody"}}]
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 2
    # a writer's marker approves
    routes["repos/%s/issues/40/comments" % DOCS] = [{"body": "## ✅ Gate Approved — LLD", "user": {"login": "maintainer"}}]
    assert L.main(["need", "docs-approved", "--change", p], run=Host(routes)) == 0


def test_chk11_deployments_in_the_record_count_without_a_comment(tmp_path, capsys):
    """#144: ops-deploy writes deployments: [{environment}] and the consumer's gate reads it."""
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "EMAIL-14", "role": "provider"}])
    routes = provider(deployed=())
    routes["repos/%s/contents/.hitl/current-change.yaml" % SVC] = {"content": b64("change_id: EMAIL-14\nstatus: merged\ndeployments:\n  - { environment: qa, artifact: a, at: x }\n  - { environment: prod, artifact: a, at: y }\n"), "encoding": "base64"}
    assert L.main(["need", "provider-deployed", "--env", "qa", "--change", p], run=Host(routes)) == 0
    assert L.main(["need", "provider-deployed", "--env", "staging", "--change", p], run=Host(routes)) == 2
    # a deploy step done with no environment recorded says so plainly and does not pass
    routes["repos/%s/contents/.hitl/current-change.yaml" % SVC] = {"content": b64("change_id: EMAIL-14\nworkflow:\n  steps:\n    - { n: 27, key: deploy, status: done }\n"), "encoding": "base64"}
    assert L.main(["need", "provider-deployed", "--env", "qa", "--change", p], run=Host(routes)) == 2
    assert "deploy step done but no environment recorded" in capsys.readouterr().out


def test_chk12_the_record_is_read_at_the_merge_commit_once_the_branch_is_gone(tmp_path, capsys):
    """#144: after merge the issue branch is deleted; the record lives at the PR's merge commit."""
    p = change(tmp_path / "c.yaml", [{"repo": SVC, "change_id": "EMAIL-14", "role": "provider"}])
    routes = provider(deployed=())
    routes["repos/%s/branches" % SVC] = [{"name": "main"}]                      # branch gone
    routes["repos/%s/pulls?" % SVC] = []
    routes["search/issues"] = {"items": [{"number": 3, "title": "EMAIL-14 endpoint", "body": "", "pull_request": {"merged_at": "2026-09-30T00:00:00Z"}}]}
    routes["repos/%s/pulls/3" % SVC] = {"head": {"ref": "issue/14-endpoint"}, "merged_at": "2026-09-30T00:00:00Z", "merge_commit_sha": "feedface0000"}
    del routes["repos/%s/contents/.hitl/current-change.yaml" % SVC]
    routes["repos/%s/contents/.hitl/current-change.yaml?ref=feedface0000" % SVC] = {"content": b64("change_id: EMAIL-14\nstatus: merged\ndeployments:\n  - { environment: prod, artifact: a, at: y }\n"), "encoding": "base64"}
    assert L.main(["need", "provider-deployed", "--env", "prod", "--change", p], run=Host(routes)) == 0
    assert "record=merged@feedfac" in capsys.readouterr().out


def test_resolve_prefixed_ids(tmp_path, capsys):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("repo: org/svc\nchange_id_prefix: SVC\nprefixes:\n  DOCS: org/docs\n")
    chg = change(tmp_path / "c.yaml", [{"repo": "org/email", "change_id": "EMAIL-14", "role": "provider"}])
    assert L.main(["resolve", "SVC-3", "--config", str(cfg), "--change", chg]) == 0
    assert capsys.readouterr().out.strip() == "3"
    assert L.main(["resolve", "DOCS-7", "--config", str(cfg), "--change", chg]) == 0
    assert capsys.readouterr().out.strip() == "-R org/docs 7"
    assert L.main(["resolve", "EMAIL-9", "--config", str(cfg), "--change", chg]) == 0
    assert capsys.readouterr().out.strip() == "-R org/email 9"
    assert L.main(["resolve", "7", "--config", str(cfg), "--change", chg]) == 2
    assert "ambiguous" in capsys.readouterr().out
    assert L.main(["resolve", "XYZ-1", "--config", str(cfg), "--change", chg]) == 2
