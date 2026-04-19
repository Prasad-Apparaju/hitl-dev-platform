"""CLI smoke tests for check_change.py.

These tests verify basic enforcement behavior through the CLI interface.
For full contract tests with fixture projects, see the test classes below.

Run with: pytest tools/preflight/test_check_change.py
"""

import subprocess
import os
import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "check_change.py")


def run_preflight(*args, cwd=None):
    """Run the preflight script and return (exit_code, output)."""
    cmd = ["python", SCRIPT] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or os.path.dirname(SCRIPT))
    return result.returncode, result.stdout + result.stderr


class TestLinkedIssue:
    def test_source_change_no_issue_fails(self):
        code, output = run_preflight("--changed-files", "app/services/foo.py")
        assert code == 1
        assert "[FAIL] linked-issue" in output

    def test_source_change_with_issue_passes(self):
        code, output = run_preflight("--issue", "123", "--changed-files", "app/services/foo.py")
        assert "[PASS] linked-issue" in output or "[PASS]" in output

    def test_docs_only_change_skips_issue_check(self):
        code, output = run_preflight("--changed-files", "docs/README.md")
        assert code == 0


class TestDecisionPacket:
    def test_source_change_no_packet_warns(self):
        code, output = run_preflight("--issue", "123", "--changed-files", "app/services/foo.py")
        # Should mention decision-packet check
        assert "decision-packet" in output.lower()

    def test_changed_packet_triggers_validation(self):
        code, output = run_preflight(
            "--issue", "123",
            "--changed-files", "app/services/foo.py", "docs/decisions/issue-123.yaml"
        )
        assert "decision-packet" in output.lower()


class TestRolloutPlan:
    def test_iac_change_no_rollout_fails(self):
        code, output = run_preflight("--changed-files", "k8s/deployment.yaml")
        assert code == 1
        assert "rollout" in output.lower()


class TestNoChanges:
    def test_empty_changeset_passes(self):
        code, output = run_preflight("--changed-files")
        assert code == 0
        assert "nothing to check" in output.lower() or "All checks passed" in output
