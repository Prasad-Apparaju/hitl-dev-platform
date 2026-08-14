"""What we ship into a consumer repo must run there.

Plugin issue #29: the CI-validator sync copied `*.py` wholesale, which dragged the validators' own
dev-repo test suites into consumer projects. Those tests resolve paths like `ai/shared/workflows.yaml`
and `ai/claude/start-change/SKILL.md` — which exist only in this platform repo — so a consumer got
3 collection errors and 68 failures out of the box. It blocked a downstream PR.

Nothing asserted what the sync delivers, which is why it went unnoticed through several releases.
These tests assert exactly that, from two directions:

  1. the copy paths exclude test files, and
  2. a repo built the way onboarding builds one has no unrunnable tests in it.
"""
import io
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
INIT = os.path.join(ROOT, "tools", "scripts", "init-project.sh")
UPDATE_SKILL = os.path.join(ROOT, "ai", "claude", "update", "SKILL.md")

# Directories whose Python is copied into a product repo by onboarding / dev-update.
SYNCED_DIRS = [
    os.path.join(ROOT, "ci", "first-pass"),
    os.path.join(ROOT, "ci", "manifest-agentic"),
    os.path.join(ROOT, "tools", "manifest-agentic"),
]


def test_onboarding_never_copies_a_bare_py_glob():
    """`cp dir/*.py` is the defect. Every copy site must filter tests out."""
    text = io.open(INIT, encoding="utf-8").read()
    offenders = re.findall(r'cp "\$PLATFORM_ROOT/(ci|tools)/[a-z-]+/"\*\.py', text)
    assert not offenders, (
        "init-project.sh copies a bare *.py glob, which ships dev-repo tests: %r" % offenders)


def test_onboarding_helper_excludes_tests():
    text = io.open(INIT, encoding="utf-8").read()
    assert "hitl_copy_tools" in text, "the filtered copy helper is missing"
    assert '! -name "test_*"' in text, "hitl_copy_tools must exclude test files"


def test_dev_update_removes_previously_synced_tests():
    """Fixing the sync forward does not help repos that already have the files."""
    text = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert "test_driver_e2e.py" in text, "dev-update must clean up stale synced tests"
    assert "ci/first-pass/test_check_skips.py" in text
    # Must be an explicit filename list, never a glob that could eat a team's own tests.
    assert "rm -f ci/first-pass/test_*.py" not in text
    assert 'rm -f "$stale"' in text


def test_removal_list_covers_every_test_we_have_ever_synced():
    """A test file added to a synced directory must also be added to dev-update's cleanup list."""
    listed = set(re.findall(r"(?:ci|tools)/[a-z-]+/(test_[a-z0-9_]+\.py)",
                            io.open(UPDATE_SKILL, encoding="utf-8").read()))
    for d in SYNCED_DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("test_") and f.endswith(".py"):
                assert f in listed, (
                    "%s lives in a synced directory but dev-update would never clean it up "
                    "from a consumer repo that already has it" % f)


def _sync_like_onboarding(dest):
    """Reproduce what a product repo receives, using the same filter onboarding uses."""
    for d in SYNCED_DIRS:
        if not os.path.isdir(d):
            continue
        rel = os.path.relpath(d, ROOT)
        out = os.path.join(dest, rel)
        os.makedirs(out, exist_ok=True)
        for f in os.listdir(d):
            if f.endswith(".py") and not f.startswith("test_"):
                shutil.copy(os.path.join(d, f), os.path.join(out, f))
    catalog = os.path.join(ROOT, "ai", "shared", "workflows.yaml")
    if os.path.isfile(catalog):
        shutil.copy(catalog, os.path.join(dest, "ci", "first-pass", "workflows.yaml"))


def test_synced_consumer_repo_collects_cleanly(tmp_path):
    """The reproduction from issue #29: pytest over a synced product repo must not error."""
    dest = tmp_path / "consumer"
    dest.mkdir()
    _sync_like_onboarding(str(dest))
    p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "ci", "tools"],
                       cwd=str(dest), capture_output=True, text=True)
    assert "error" not in p.stdout.lower(), p.stdout[-2000:]
    assert p.returncode in (0, 5), (  # 5 = no tests collected, which is the desired end state
        "collection failed in a synced consumer repo:\n%s" % p.stdout[-2000:])


def test_synced_validator_still_runs_in_a_consumer_repo(tmp_path):
    """Removing the tests must not remove what CI actually invokes."""
    dest = tmp_path / "consumer"
    dest.mkdir()
    _sync_like_onboarding(str(dest))
    (dest / ".hitl").mkdir()
    (dest / ".hitl" / "current-change.yaml").write_text(
        'id: "X-1"\ntier: 1\nfirst_pass: true\n'
        'workflow:\n  name: development\n  steps:\n'
        '    - key: "roi"\n      status: "skipped"\n', encoding="utf-8")
    checker = dest / "ci" / "first-pass" / "check_skips.py"
    assert checker.is_file(), "the validator itself must still be delivered"
    p = subprocess.run([sys.executable, str(checker), ".hitl/current-change.yaml"],
                       cwd=str(dest), capture_output=True, text=True)
    assert p.returncode == 2, (
        "the synced validator must still fail closed on a silent skip; got %s\n%s"
        % (p.returncode, p.stdout + p.stderr))
    assert "SILENT_SKIP" in (p.stdout + p.stderr)
