"""Tests for check_manifest_drift — focused on manifest-driven scan-root derivation."""

import subprocess
import sys
from pathlib import Path

import check_manifest_drift as drift

SCRIPT = Path(__file__).with_name("check_manifest_drift.py")


def test_derive_source_dirs_from_listed_files():
    manifest = {
        "domains": {
            "services": {"files": ["backend/services/auth.py"]},
            "api": {"files": ["backend/api/users.py", "web/routes.py"]},
        }
    }
    assert drift._derive_source_dirs(manifest) == ["backend/", "web/"]


def test_derive_source_dirs_ignores_dotfiles_and_blanks():
    manifest = {"domains": {"d": {"files": [".hidden/x.py", "", "src/a.py"]}}}
    assert drift._derive_source_dirs(manifest) == ["src/"]


def test_derive_source_dirs_empty_manifest():
    assert drift._derive_source_dirs({}) == []


def _run(cwd: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=cwd, capture_output=True, text=True
    )
    return result.stdout


def test_self_derivation_flags_orphan_in_nonstandard_layout(tmp_path):
    """A 'backend/' layout the old hardcoded app/ src/ default would have missed."""
    (tmp_path / "backend/services").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "backend/services/auth.py").write_text("def authenticate(): pass\n")
    (tmp_path / "backend/services/orphan.py").write_text("def stray(): pass\n")
    (tmp_path / "docs/system-manifest.yaml").write_text(
        "domains:\n  services:\n    files:\n      - backend/services/auth.py\n"
    )
    out = _run(tmp_path)
    assert "backend/services/orphan.py" in out
    assert "UNLISTED FILE" in out
