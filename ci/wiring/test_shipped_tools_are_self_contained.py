"""What we ship into a consumer repo must run there.

Plugin issue #29: the CI-validator sync copied `*.py` wholesale, dragging each validator's own
dev-repo test suite into consumer projects. Those tests resolve paths that exist only in this
platform repo, so a consumer got collection errors and 68 failures out of the box. It blocked a
downstream PR.

The FIRST version of this guard file was vacuous. An adversarial review reverted the fix to the
original bare glob and all six guards stayed green, because they:
  - asserted a substring that a mere comment satisfies,
  - built the consumer repo with a PYTHON REIMPLEMENTATION of the filter rather than running the
    shipped script, so they tested the test's own copy logic, and
  - pattern-matched one exact `cp` spelling, which any other spelling evades.

So these now execute the real `hitl_copy_tools` out of init-project.sh, in bash, and assert on what
actually lands on disk. A guard that cannot fail is worse than no guard.
"""
import io
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
INIT = os.path.join(ROOT, "tools", "scripts", "init-project.sh")
UPDATE_SKILL = os.path.join(ROOT, "ai", "claude", "update", "SKILL.md")

# Every directory whose Python is copied into a product repo, by onboarding or by dev-update.
SYNCED_DIRS = ["ci/first-pass", "ci/manifest-agentic", "tools/manifest-agentic",
               "ci/manifest-drift", "ci/agentic-advisor"]

# Files that must never reach a consumer: pytest imports conftest.py at collection, so a
# platform-only one blocks collection exactly as a test file does.
FORBIDDEN_PREFIXES = ("test_",)
FORBIDDEN_NAMES = ("conftest.py",)


def _run_real_copy(src, dest):
    """Source hitl_copy_tools out of the SHIPPED script and run it. No reimplementation."""
    script = (
        'set -euo pipefail\n'
        'sed -n "/^hitl_copy_tools()/,/^}/p" %s > /tmp/_hct.sh\n'
        '. /tmp/_hct.sh\n'
        'hitl_copy_tools %s %s\n' % (
            subprocess.list2cmdline([INIT]),
            subprocess.list2cmdline([src]),
            subprocess.list2cmdline([dest]))
    )
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def _offenders(d):
    if not os.path.isdir(d):
        return []
    return [f for f in os.listdir(d)
            if f.startswith(FORBIDDEN_PREFIXES) or f in FORBIDDEN_NAMES or f == "__pycache__"]


@pytest.mark.parametrize("rel", SYNCED_DIRS)
def test_real_copy_helper_delivers_no_tests(tmp_path, rel):
    """Run the shipped helper against each real synced directory and inspect what lands."""
    src = os.path.join(ROOT, rel)
    if not os.path.isdir(src):
        pytest.skip("%s not present" % rel)
    dest = tmp_path / rel
    p = _run_real_copy(src, str(dest))
    assert p.returncode == 0, p.stderr
    bad = _offenders(str(dest))
    assert not bad, "%s delivered files a consumer cannot run: %s" % (rel, bad)


def test_real_copy_helper_still_delivers_the_validators(tmp_path):
    """Filtering must not become 'copy nothing' — that would pass every other guard here."""
    src = os.path.join(ROOT, "ci", "first-pass")
    dest = tmp_path / "out"
    assert _run_real_copy(src, str(dest)).returncode == 0
    got = set(os.listdir(str(dest)))
    assert "check_skips.py" in got, "the validator CI runs must still be delivered: %s" % got


def test_real_copy_helper_excludes_a_planted_test_and_conftest(tmp_path):
    """Mutation-style: plant the exact files that caused #29 and prove they do not travel."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "tool.py").write_text("# validator\n", encoding="utf-8")
    (src / "test_tool.py").write_text("import ai.shared\n", encoding="utf-8")
    (src / "conftest.py").write_text("import ai.shared\n", encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "tool.cpython-313.pyc").write_bytes(b"\x00")
    dest = tmp_path / "dest"
    assert _run_real_copy(str(src), str(dest)).returncode == 0
    got = set(os.listdir(str(dest)))
    assert got == {"tool.py"}, "expected only the validator, got %s" % got


def test_onboarding_routes_every_tool_directory_through_the_filter(tmp_path):
    """`cp -r` on ci/manifest-drift bypassed the filter entirely and shipped its tests + .pyc."""
    text = io.open(INIT, encoding="utf-8").read()
    assert 'cp -r "$PLATFORM_ROOT/ci/manifest-drift"' not in text, (
        "manifest-drift is copied wholesale, bypassing the test filter")
    for rel in ("ci/first-pass", "ci/manifest-agentic", "tools/manifest-agentic", "ci/manifest-drift"):
        assert 'hitl_copy_tools "$PLATFORM_ROOT/%s"' % rel in text, (
            "%s does not go through hitl_copy_tools" % rel)


def test_generated_gitignore_excludes_bytecode():
    """We copy .py in, so bytecode appears next to it; without this it gets committed."""
    text = io.open(INIT, encoding="utf-8").read()
    assert "__pycache__" in text, "onboarding must add __pycache__ to the consumer .gitignore"


def test_dev_update_cleanup_is_reachable_when_already_on_the_latest_version():
    """The cleanup only ran on the update AFTER the one that shipped it.

    Step 3 said "already on the latest version — no changes" **and stop**, before the re-sync
    steps. A user whose version already matched could therefore never get the repair, which is
    precisely the state they are in when they re-run the command to fix something.
    """
    text = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert 'Already on the latest version." and stop' not in text, (
        "Step 3 still stops before the re-sync steps")
    assert "do not stop" in text.lower(), "Step 3 must continue to the re-sync steps"


def test_dev_update_rereads_itself_after_updating():
    """A fix shipped IN dev-update must run on the update that delivers it, not the next one."""
    text = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert "skills/dev-update/SKILL.md" in text, (
        "dev-update must re-read its own newly installed copy after Step 2")
    assert "follow the file, not your context" in text.lower()


def test_removal_list_covers_every_test_in_a_synced_directory():
    """Add a test to a synced directory and it must also be listed for cleanup."""
    import re
    listed = set(re.findall(r"(?:ci|tools)/[a-z-]+/(test_[a-z0-9_]+\.py)",
                            io.open(UPDATE_SKILL, encoding="utf-8").read()))
    for rel in SYNCED_DIRS:
        d = os.path.join(ROOT, rel)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("test_") and f.endswith(".py"):
                assert f in listed, (
                    "%s/%s is synced-adjacent but dev-update would never clean it from a "
                    "consumer repo that already has it" % (rel, f))


def test_synced_validator_still_runs_in_a_consumer_repo(tmp_path):
    """End to end: build a consumer the real way, then run what its CI runs."""
    dest = tmp_path / "consumer"
    (dest / ".hitl").mkdir(parents=True)
    for rel in ("ci/first-pass", "ci/manifest-agentic", "tools/manifest-agentic"):
        src = os.path.join(ROOT, rel)
        if os.path.isdir(src):
            assert _run_real_copy(src, str(dest / rel)).returncode == 0
    catalog = os.path.join(ROOT, "ai", "shared", "workflows.yaml")
    if os.path.isfile(catalog):
        import shutil
        shutil.copy(catalog, str(dest / "ci" / "first-pass" / "workflows.yaml"))
    (dest / ".hitl" / "current-change.yaml").write_text(
        'id: "X-1"\ntier: 1\nfirst_pass: true\n'
        'workflow:\n  name: development\n  steps:\n'
        '    - key: "roi"\n      status: "skipped"\n', encoding="utf-8")

    collect = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "."],
                             cwd=str(dest), capture_output=True, text=True)
    assert "error" not in collect.stdout.lower(), collect.stdout[-2000:]

    run = subprocess.run([sys.executable, "ci/first-pass/check_skips.py",
                          ".hitl/current-change.yaml"], cwd=str(dest),
                         capture_output=True, text=True)
    assert run.returncode == 2, "the synced validator must still fail closed:\n%s" % (
        run.stdout + run.stderr)
