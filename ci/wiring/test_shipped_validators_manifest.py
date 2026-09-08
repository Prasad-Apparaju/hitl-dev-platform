"""The shipped-validators manifest (plugin #35) must list every synced validator in the tree, or
dev-update will treat the version about to ship as a repo edit the next time it differs."""
import io, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GEN = os.path.join(ROOT, "tools", "scripts", "shipped-validators-hashes.py")


def test_every_current_synced_validator_is_in_the_manifest():
    r = subprocess.run([sys.executable, GEN, "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_paths_are_the_paths_dev_update_installs_at():
    sys.path.insert(0, os.path.join(ROOT, "ci", "first-pass"))
    import migrate_project as M
    dsts = {s["dst"] for s in M.SYNC_SETS if "glob" in s} | {s["dst"] for s in M.SYNC_SETS if "glob" not in s}
    for line in io.open(os.path.join(ROOT, "ci", "shipped-validators.sha256"), encoding="utf-8"):
        parts = line.split("#", 1)[0].split()
        if len(parts) < 2:
            continue
        rel = parts[1]
        assert rel in dsts or os.path.dirname(rel) in dsts, f"{rel} is not a dev-update install path"


def test_the_manifest_ships_with_the_plugin_build():
    build = os.path.join(ROOT, "..", "hitl-claude-plugin", "scripts", "build.sh")
    if not os.path.isfile(build):
        import pytest
        pytest.skip("plugin repo not checked out beside this one")
    assert "shipped-validators.sha256" in io.open(build, encoding="utf-8").read(), (
        "build.sh does not copy ci/shipped-validators.sha256 into shared/ci/")
