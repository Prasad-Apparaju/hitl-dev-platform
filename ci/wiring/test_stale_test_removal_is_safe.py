"""dev-update deletes files from a user's repo. It must only ever delete files that are ours.

The first version of that cleanup matched on filename alone, and was "verified" against a repo
carrying a test named `test_our_house_rules.py`. That is the easy case. The real one is
`test_check_skips.py`: a team writing tests for the shipped validator `check_skips.py` names theirs
exactly that, by pytest convention — and the cleanup step, by removing the shipped tests, invites
them to write it. Filename-matching deleted it, untracked, unrecoverable, and reported success.

Removal is now gated on tracked-in-this-repo AND an exact content match against the manifest of
every version HITL has ever shipped. These tests assert the destructive cases, extracting the real
block from the skill body so they cannot drift from what ships.
"""
import hashlib
import io
import os
import re
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SKILL = os.path.join(ROOT, "ai", "claude", "update", "SKILL.md")
MANIFEST = os.path.join(ROOT, "ci", "retired-tests.sha256")

SHIPPED_BODY = "# a real HITL test body\nimport os\nROOT = os.path.join('ai', 'shared')\n"


def _block():
    """The removal block, lifted out of the shipped skill so the test cannot drift from it."""
    text = io.open(SKILL, encoding="utf-8").read()
    m = re.search(r"(  HASHES=\"\$ROOT/shared/ci/retired-tests\.sha256\".*?\n  fi\n)", text, re.S)
    assert m, "removal block not found in dev-update SKILL.md"
    return m.group(1)


def _repo(tmp_path, files, track=True, manifest_extra=()):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(r), check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=str(r), check=True)
    (r / "seed.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(r), check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=str(r), check=True)
    for rel, body in files.items():
        p = r / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    if track and files:
        subprocess.run(["git", "add", "-A"], cwd=str(r), check=True)
        subprocess.run(["git", "commit", "-qm", "add"], cwd=str(r), check=True)

    plugin = tmp_path / "plugin" / "shared" / "ci"
    plugin.mkdir(parents=True, exist_ok=True)
    lines = ["%s  %s\n" % (hashlib.sha256(SHIPPED_BODY.encode()).hexdigest(), "shipped.py")]
    lines += list(manifest_extra)
    (plugin / "retired-tests.sha256").write_text("".join(lines), encoding="utf-8")
    return r, str(tmp_path / "plugin")


def _run(repo, plugin_root):
    script = 'set -u\nROOT="%s"\n%s' % (plugin_root, _block())
    return subprocess.run(["bash", "-c", script], cwd=str(repo), capture_output=True, text=True)


def test_team_authored_file_with_a_colliding_name_survives(tmp_path):
    """THE regression. Untracked + same name as a shipped test = unrecoverable if deleted."""
    mine = "# our own tests for the HITL validator\n"
    repo, plugin = _repo(tmp_path, {"ci/first-pass/test_check_skips.py": mine}, track=False)
    p = _run(repo, plugin)
    survivor = repo / "ci" / "first-pass" / "test_check_skips.py"
    assert survivor.is_file(), "deleted a team-authored, untracked file:\n%s" % (p.stdout + p.stderr)
    assert survivor.read_text(encoding="utf-8") == mine


def test_tracked_file_with_colliding_name_but_different_content_is_kept_and_reported(tmp_path):
    repo, plugin = _repo(tmp_path, {"ci/first-pass/test_check_skips.py": "# ours, committed\n"})
    p = _run(repo, plugin)
    assert (repo / "ci" / "first-pass" / "test_check_skips.py").is_file()
    assert "kept" in (p.stdout + p.stderr), "a kept file must be reported, not silently ignored"


def test_a_genuinely_shipped_file_is_removed(tmp_path):
    """The cleanup must still do its job, or issue #29 is not fixed."""
    h = hashlib.sha256(SHIPPED_BODY.encode()).hexdigest()
    repo, plugin = _repo(tmp_path, {"ci/first-pass/test_check_skips.py": SHIPPED_BODY},
                         manifest_extra=["%s  test_check_skips.py\n" % h])
    p = _run(repo, plugin)
    assert not (repo / "ci" / "first-pass" / "test_check_skips.py").exists(), p.stdout + p.stderr
    assert "removed" in p.stdout


def test_locally_modified_shipped_test_is_kept(tmp_path):
    """Their edits are theirs. Leave a broken test rather than delete someone's work."""
    h = hashlib.sha256(SHIPPED_BODY.encode()).hexdigest()
    repo, plugin = _repo(tmp_path, {"ci/first-pass/test_check_skips.py": SHIPPED_BODY + "# my edit\n"},
                         manifest_extra=["%s  test_check_skips.py\n" % h])
    _run(repo, plugin)
    assert (repo / "ci" / "first-pass" / "test_check_skips.py").is_file()


def test_symlinked_directory_does_not_reach_outside_the_repo(tmp_path):
    """A symlinked ci/first-pass must not let rm escape the repository."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "test_check_skips.py").write_text(SHIPPED_BODY, encoding="utf-8")
    h = hashlib.sha256(SHIPPED_BODY.encode()).hexdigest()
    repo, plugin = _repo(tmp_path, {}, manifest_extra=["%s  test_check_skips.py\n" % h])
    (repo / "ci").mkdir(parents=True, exist_ok=True)
    os.symlink(str(outside), str(repo / "ci" / "first-pass"))
    _run(repo, plugin)
    assert (outside / "test_check_skips.py").is_file(), "deleted a file outside the repository"


def test_platform_repo_is_never_touched(tmp_path):
    """Run in HITL's own repo, these ARE the real suite."""
    h = hashlib.sha256(SHIPPED_BODY.encode()).hexdigest()
    repo, plugin = _repo(tmp_path, {
        "ci/first-pass/test_check_skips.py": SHIPPED_BODY,
        "ai/claude/start-change/SKILL.md": "# the platform repo marker\n",
    }, manifest_extra=["%s  test_check_skips.py\n" % h])
    _run(repo, plugin)
    assert (repo / "ci" / "first-pass" / "test_check_skips.py").is_file(), \
        "deleted the platform repo's own test suite"


def test_missing_manifest_removes_nothing(tmp_path):
    repo, plugin = _repo(tmp_path, {"ci/first-pass/test_check_skips.py": SHIPPED_BODY})
    os.remove(os.path.join(plugin, "shared", "ci", "retired-tests.sha256"))
    p = _run(repo, plugin)
    assert (repo / "ci" / "first-pass" / "test_check_skips.py").is_file()
    assert "skipping" in p.stdout.lower()


def test_idempotent_and_clean_on_an_empty_repo(tmp_path):
    repo, plugin = _repo(tmp_path, {})
    for _ in range(2):
        p = _run(repo, plugin)
        assert p.returncode == 0, p.stderr


def test_manifest_ships_and_covers_every_listed_filename():
    """Every filename the block can delete must have at least one hash, or cleanup silently no-ops."""
    assert os.path.isfile(MANIFEST), "the hash manifest must exist in the source repo"
    names = {l.split()[1] for l in io.open(MANIFEST, encoding="utf-8")
             if l.strip() and not l.startswith("#")}
    listed = set(re.findall(r"(?:ci|tools)/[a-z-]+/(test_[a-z0-9_]+\.py)", _block()))
    missing = listed - names
    assert not missing, "no shipped hash for %s — cleanup would never remove it" % sorted(missing)
