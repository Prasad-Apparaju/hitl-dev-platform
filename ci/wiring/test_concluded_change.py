"""A concluded change must not brick the repo with unactionable advice.

GH-58 merged, its branch was deleted, and the change file stayed on main at
`status: implementation-approved`. Every edit in the repo was then blocked with
"run /hitl:dev-switch-context" — pointing at a branch that no longer exists.

Two mechanisms are asserted here:
  1. `status: merged` deactivates a change (shipped 2.4.5) — so the front door is re-entered.
  2. A missing expected_branch is reported as a CONCLUDED change, not a context mismatch.

These are run as real processes against real git repos, because the defect was in how the shell
hooks read git state, which no in-process test would have seen.
"""
import os
import re
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOKS = os.path.join(ROOT, "ai", "claude", "hooks")
CONTEXT_HOOK = os.path.join(HOOKS, "check-hitl-context.sh")

CHANGE = """\
schema_version: "2.0"
change_id: "GH-58"
tier: 2
status: {status}
expected_branch: "{branch}"
allowed_paths:
  - "ai/"
workflow:
  id: development
  steps:
    - {{n: 1, key: "issue", name: "Issue", phase: "Requirements", status: "current"}}
"""


def _git(cwd, *args):
    subprocess.run(("git",) + args, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _repo(tmp_path, status, expected_branch, make_branch=None, on_branch="main"):
    r = tmp_path / "repo"
    (r / ".hitl").mkdir(parents=True)
    _git(str(r), "init", "-q", "-b", "main")
    _git(str(r), "config", "user.email", "t@t")
    _git(str(r), "config", "user.name", "t")
    (r / "seed.txt").write_text("x", encoding="utf-8")
    _git(str(r), "add", "-A")
    _git(str(r), "commit", "-qm", "seed")
    if make_branch:
        _git(str(r), "branch", make_branch)
    if on_branch != "main":
        _git(str(r), "checkout", "-q", on_branch)
    (r / ".hitl" / "current-change.yaml").write_text(
        CHANGE.format(status=status, branch=expected_branch), encoding="utf-8")
    return r


def _edit(repo, path="ai/thing.py"):
    payload = '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' % path
    return subprocess.run(["bash", CONTEXT_HOOK], cwd=str(repo), input=payload,
                          capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)})


def test_branch_deleted_reports_concluded_not_mismatch():
    """The bug: a deleted branch produced 'run dev-switch-context', which cannot be done."""
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(pathlib.Path(td), '"implementation-approved"', "issue/58-gone")
        p = _edit(repo)
        assert p.returncode == 2, "a concluded change must still block edits (fail closed)"
        err = p.stderr
        # Properties, not phrases (#91 rewrote the wording). What must hold: the message says the
        # change is over, names the real remedy, and never advises switching to a branch that is
        # gone — the 2.6.1 defect, where the only advice offered was impossible to follow.
        assert re.search(r"(?i)looks (complete|finished)|has (merged|finished)", err), err
        assert re.search(r"(?i)no longer exists|is gone", err), err
        assert 'status: "merged"' in err, "must name the actual remedy"
        assert "dev-switch-context" not in err, "must not advise switching to a deleted branch"


def test_live_branch_still_reports_mismatch():
    """The opposite case must be untouched: a real branch that exists is a genuine mismatch."""
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(pathlib.Path(td), '"implementation-approved"', "issue/99-live",
                     make_branch="issue/99-live")
        p = _edit(repo)
        assert p.returncode == 2
        # A live branch is a mismatch, not a conclusion: switching is real advice here.
        assert "dev-switch-context" in p.stderr, "switching IS the right advice here"
        assert not re.search(r"(?i)looks (complete|finished)|is gone", p.stderr), (
            "a live change must not be reported as finished — that pushes someone into re-intake "
            "and loses their step progress")


def test_merged_status_deactivates_and_forces_re_intake():
    """status: merged means done — the gate must fall through to 'no active change'."""
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(pathlib.Path(td), '"merged"', "issue/58-gone")
        p = _edit(repo)
        assert p.returncode == 2
        assert re.search(r"(?i)nothing is tracked|no active change", p.stderr), p.stderr
        assert "dev-start-change" in p.stderr, "must send them through the front door"


def test_on_the_expected_branch_is_never_blocked_by_this_rule():
    """Working on the change's own branch must stay clean."""
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(pathlib.Path(td), '"implementation-approved"', "issue/99-live",
                     make_branch="issue/99-live", on_branch="issue/99-live")
        p = _edit(repo)
        assert p.returncode == 0, p.stderr


def test_branch_gone_helper_is_conservative_about_unfetched_branches():
    """A branch present only as a remote-tracking ref must NOT count as gone.

    Wrongly declaring a live change concluded pushes someone into re-intake and loses their
    step progress, so the helper has to see neither a local branch nor a remote ref.
    """
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(pathlib.Path(td), '"implementation-approved"', "issue/77-remote")
        # Fabricate a remote-tracking ref without a local branch, as a fresh clone would have.
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                             capture_output=True, text=True).stdout.strip()
        _git(str(repo), "update-ref", "refs/remotes/origin/issue/77-remote", sha)
        probe = subprocess.run(
            ["bash", "-c",
             'source "%s/_steps.sh"; hitl_branch_gone .hitl/current-change.yaml' % HOOKS],
            cwd=str(repo), capture_output=True, text=True)
        assert probe.returncode == 1, "a remote-only branch must not be treated as gone"
