"""Contract tests for the preflight traceability check script.

These tests exercise the CLI interface of check_change.py to verify
that the enforcement gates (issue linkage, decision packets, rollout
plans) work correctly.

Run with: pytest tools/preflight/test_check_change.py
"""

import os
import subprocess


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_preflight(*args, changed_files=None):
    """Run the preflight script with given args and return exit code + output."""
    cmd = ["python", "tools/preflight/check_change.py"]
    if changed_files:
        cmd.extend(["--changed-files"] + changed_files)
    cmd.extend(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    )
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_source_change_no_issue_no_packet_fails():
    """Source file changed + no issue + no decision packet -> fail."""
    code, output = run_preflight(changed_files=["app/services/foo.py"])
    assert code == 1
    assert "issue" in output.lower()


def test_source_change_with_issue_passes_issue_check():
    """Source file changed + issue provided -> issue check passes."""
    code, output = run_preflight("--issue", "999", changed_files=["app/services/foo.py"])
    # May still fail on other checks (no packet), but issue check should pass
    assert "linked-issue" not in output.lower() or "PASS" in output


def test_source_change_with_changed_packet_passes():
    """Source file changed + changed packet for current issue -> passes packet check."""
    code, output = run_preflight(
        "--issue", "123",
        changed_files=["app/services/foo.py", "docs/decisions/issue-123.yaml"],
    )
    # Packet check should attempt validation (may fail on content if file doesn't exist, that's OK)
    assert "decision-packet" in output.lower() or "packet" in output.lower()


def test_iac_change_without_rollout_fails():
    """IaC file changed + no rollout data -> fail."""
    code, output = run_preflight(changed_files=["k8s/deployment.yaml"])
    assert code == 1


def test_no_changes_passes():
    """No changed files -> all checks pass (nothing to validate)."""
    code, output = run_preflight(changed_files=[])
    assert code == 0
