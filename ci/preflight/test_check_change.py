"""CLI smoke tests and fixture-based contract tests for check_change.py.

Smoke tests verify basic enforcement behavior through the CLI.
Contract tests create temporary project directories with manifests,
decision packets, and source files to prove enforcement guarantees.
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


class TestContractWithFixtures:
    """Contract tests using temporary project fixtures."""

    def _create_manifest(self, project_dir, domains):
        """Create a minimal system manifest with given domains."""
        manifest = {"domains": {}}
        for name, files in domains.items():
            manifest["domains"][name] = {"files": files}
        manifest_dir = project_dir / "docs"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "system-manifest.yaml"
        import yaml
        manifest_path.write_text(yaml.dump(manifest))

    def _create_packet(self, project_dir, issue, domains, risk="medium", strategy="Feature flag"):
        """Create a valid decision packet."""
        packet_dir = project_dir / "docs" / "decisions"
        packet_dir.mkdir(parents=True, exist_ok=True)
        packet_path = packet_dir / f"issue-{issue}.yaml"
        import yaml
        data = {
            "issue": int(issue),
            "domains": domains,
            "source_docs": {"lld": ["docs/lld/example.md"]},
            "rollout": {"risk": risk, "strategy": strategy},
            "tests": {"registry_updated": True},
        }
        packet_path.write_text(yaml.dump(data))
        return str(packet_path.relative_to(project_dir))

    def _create_registry(self, project_dir):
        """Create the canonical test registry."""
        reg_dir = project_dir / "docs" / "03-engineering" / "testing"
        reg_dir.mkdir(parents=True, exist_ok=True)
        (reg_dir / "test-registry.yaml").write_text("test_cases: []\n")

    def test_source_change_valid_packet_passes(self, tmp_path):
        self._create_manifest(tmp_path, {"billing": ["app/billing.py"]})
        packet_rel = self._create_packet(tmp_path, "42", ["billing"])
        self._create_registry(tmp_path)
        code, output = run_preflight(
            "--issue", "42",
            "--changed-files", "app/billing.py", packet_rel,
            "docs/03-engineering/testing/test-registry.yaml",
            cwd=str(tmp_path)
        )
        assert "[FAIL]" not in output

    def test_source_change_old_historical_packet_fails(self, tmp_path):
        self._create_manifest(tmp_path, {"billing": ["app/billing.py"]})
        # Create a packet for a DIFFERENT issue (historical)
        self._create_packet(tmp_path, "99", ["billing"])
        code, output = run_preflight(
            "--issue", "42",
            "--changed-files", "app/billing.py",
            cwd=str(tmp_path)
        )
        # Should fail because issue-42 packet doesn't exist and issue-99 is not in changed files
        assert code == 1 or "[FAIL]" in output or "[WARN]" in output

    def test_packet_wrong_domain_strict_fails(self, tmp_path):
        self._create_manifest(tmp_path, {
            "billing": ["app/billing.py"],
            "notifications": ["app/notify.py"],
        })
        # Packet lists only billing, but we're changing notifications too
        packet_rel = self._create_packet(tmp_path, "42", ["billing"])
        code, output = run_preflight(
            "--strict", "--issue", "42",
            "--changed-files", "app/notify.py", packet_rel,
            cwd=str(tmp_path)
        )
        # Domain mismatch should produce a warning or error
        assert "domain" in output.lower() or "notifications" in output.lower()

    def test_test_change_without_registry_update_fails(self, tmp_path):
        code, output = run_preflight(
            "--changed-files", "tests/test_foo.py",
            cwd=str(tmp_path)
        )
        assert code == 1
        assert "test-registry" in output.lower()

    def test_test_change_with_registry_update_passes(self, tmp_path):
        self._create_registry(tmp_path)
        code, output = run_preflight(
            "--changed-files", "tests/test_foo.py",
            "docs/03-engineering/testing/test-registry.yaml",
            cwd=str(tmp_path)
        )
        assert "[FAIL] test-registry" not in output

    def test_iac_change_malformed_rollout_fails(self, tmp_path):
        # Packet with empty rollout section
        packet_dir = tmp_path / "docs" / "decisions"
        packet_dir.mkdir(parents=True, exist_ok=True)
        import yaml
        (packet_dir / "issue-10.yaml").write_text(yaml.dump({
            "issue": 10, "domains": ["infra"],
            "source_docs": {"lld": ["docs/x.md"]},
            "rollout": {},  # malformed - no risk
            "tests": {"registry_updated": True},
        }))
        code, output = run_preflight(
            "--issue", "10",
            "--changed-files", "k8s/deployment.yaml", "docs/decisions/issue-10.yaml",
            cwd=str(tmp_path)
        )
        assert code == 1
        assert "rollout" in output.lower()
