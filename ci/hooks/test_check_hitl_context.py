"""Regression tests for check-hitl-context.sh path normalization (plugin issue #20).

Claude Code sends tool_input.file_path as an ABSOLUTE path. The hook must:
  - honor the .hitl/ and .claude/ bootstrap exemption for absolute paths,
  - ignore paths outside the project (scratchpads, user-level config),
  - still block guarded project files, absolute or relative.

Each test builds a temporary HITL project (a .hitl/ dir, optionally an active
change file) and invokes the hook exactly as the harness does: JSON on stdin,
cwd = project root. Exit 0 = allow, exit 2 = block.
"""

import json
import os
import subprocess
import pytest

HOOK = os.path.join(
    os.path.dirname(__file__), "..", "..", "ai", "claude", "hooks", "check-hitl-context.sh"
)


def run_hook(project_dir, tool_name, tool_input, env_extra=None):
    """Invoke the hook as the harness does and return (exit_code, stderr)."""
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    if env_extra:
        env.update(env_extra)
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(
        ["bash", os.path.abspath(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
    )
    return result.returncode, result.stderr


@pytest.fixture
def hitl_project(tmp_path):
    """A HITL project with .hitl/ present but NO active change (layer-1 blocking)."""
    (tmp_path / ".hitl").mkdir()
    (tmp_path / ".claude").mkdir()
    return tmp_path


class TestBootstrapExemptionAbsolutePaths:
    """The bug: absolute paths never matched the .hitl/.claude exemption."""

    def test_absolute_hitl_path_allowed(self, hitl_project):
        code, _ = run_hook(
            hitl_project, "Write",
            {"file_path": str(hitl_project / ".hitl" / "current-change.yaml")},
        )
        assert code == 0

    def test_absolute_claude_path_allowed(self, hitl_project):
        code, _ = run_hook(
            hitl_project, "Write",
            {"file_path": str(hitl_project / ".claude" / "settings.json")},
        )
        assert code == 0

    def test_relative_hitl_path_still_allowed(self, hitl_project):
        code, _ = run_hook(
            hitl_project, "Write", {"file_path": ".hitl/current-change.yaml"}
        )
        assert code == 0


class TestOutOfProjectPaths:
    """The bug: paths outside the project were gated as if they were project source."""

    def test_absolute_tmp_scratchpad_allowed(self, hitl_project, tmp_path_factory):
        outside = tmp_path_factory.mktemp("scratchpad") / "notes.py"
        code, _ = run_hook(hitl_project, "Write", {"file_path": str(outside)})
        assert code == 0

    def test_relative_parent_escape_allowed(self, hitl_project):
        code, _ = run_hook(hitl_project, "Write", {"file_path": "../outside.py"})
        assert code == 0

    def test_symlinked_project_root_still_contained(self, hitl_project, tmp_path_factory):
        # File addressed via a symlink to the project must count as INSIDE it.
        link = tmp_path_factory.mktemp("links") / "proj"
        link.symlink_to(hitl_project)
        code, _ = run_hook(
            hitl_project, "Write", {"file_path": str(link / "src" / "app.py")}
        )
        assert code == 2


class TestGuardedPathsStillBlocked:
    """The fix must not weaken layer 1: project files stay blocked with no active change."""

    def test_absolute_project_source_blocked(self, hitl_project):
        code, err = run_hook(
            hitl_project, "Write", {"file_path": str(hitl_project / "src" / "app.py")}
        )
        assert code == 2
        assert "no active change" in err

    def test_relative_project_source_blocked(self, hitl_project):
        code, _ = run_hook(hitl_project, "Edit", {"file_path": "src/app.py"})
        assert code == 2

    def test_relative_docs_blocked_without_change(self, hitl_project):
        code, _ = run_hook(hitl_project, "Write", {"file_path": "docs/readme.md"})
        assert code == 2

    def test_dot_slash_normalization_unchanged(self, hitl_project):
        code, _ = run_hook(hitl_project, "Write", {"file_path": "./src/app.py"})
        assert code == 2


class TestClaudeProjectDirEnv:
    """CLAUDE_PROJECT_DIR, when set by the harness, defines the project root."""

    def test_root_taken_from_env_not_cwd(self, hitl_project, tmp_path_factory):
        other_root = tmp_path_factory.mktemp("other-project")
        # Absolute path inside OTHER root: with CLAUDE_PROJECT_DIR pointing there,
        # a .hitl/ path under it is a bootstrap path even though cwd is elsewhere.
        code, _ = run_hook(
            hitl_project, "Write",
            {"file_path": str(other_root / ".hitl" / "current-change.yaml")},
            env_extra={"CLAUDE_PROJECT_DIR": str(other_root)},
        )
        assert code == 0


class TestApplyPatchPaths:
    """Codex apply_patch paths are relative; behavior must be unchanged."""

    def test_patch_source_file_blocked(self, hitl_project):
        cmd = "*** Update File: src/app.py\n@@\n-a\n+b\n"
        code, _ = run_hook(hitl_project, "apply_patch", {"command": cmd})
        assert code == 2

    def test_patch_hitl_file_allowed(self, hitl_project):
        cmd = "*** Add File: .hitl/current-change.yaml\n+change_id: 1\n"
        code, _ = run_hook(hitl_project, "apply_patch", {"command": cmd})
        assert code == 0


class TestNonHitlProject:
    def test_no_hitl_dir_skips(self, tmp_path):
        code, _ = run_hook(tmp_path, "Write", {"file_path": "src/app.py"})
        assert code == 0
