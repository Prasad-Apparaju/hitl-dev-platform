#!/usr/bin/env python3
"""Preflight traceability check for the HITL dev platform.

Verifies that a change has the required artifacts (issue, decision packet,
LLD/ADR updates, test-registry entry, rollout plan) before code generation
or PR creation.  Runs identically from a developer's terminal and from CI.

Exit code: 0 = all checks pass, 1 = at least one check failed.

Dependencies: Python 3.10+, PyYAML.  Optional: gh CLI (for issue lookup).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # graceful degradation — only needed for manifest-domain check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _git_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Return changed files relative to *base_ref* via git diff."""
    result = _run(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
    if result.returncode != 0:
        # Fall back to unstaged diff (useful outside a PR context)
        result = _run(["git", "diff", "--name-only", "HEAD"])
    return [f for f in result.stdout.strip().splitlines() if f]


def _is_source_file(path: str) -> bool:
    return any(path.endswith(ext) for ext in (".py", ".ts", ".js", ".go", ".java", ".rs"))


def _is_api_or_controller(path: str) -> bool:
    lower = path.lower()
    return "controller" in lower or "router" in lower or "/api/" in lower


def _is_test_file(path: str) -> bool:
    lower = path.lower()
    return "test" in lower or "spec" in lower


def _is_iac_file(path: str) -> bool:
    lower = path.lower()
    return any(
        token in lower
        for token in ("terraform", "helm", "kustomize", "deploy", "infra", ".tf", "k8s")
    )


def _is_doc_lld_or_adr(path: str) -> bool:
    lower = path.lower()
    return "lld" in lower or "adr" in lower


def _is_manifest_domain_file(path: str) -> bool:
    """Check whether *path* falls under a domain listed in system-manifest.yaml."""
    if yaml is None:
        return False
    manifest = Path("docs/system-manifest.yaml")
    if not manifest.exists():
        return False
    try:
        with open(manifest) as f:
            data = yaml.safe_load(f)
        domains = data.get("domains", {})
        for domain in domains.values():
            files = domain.get("files", [])
            if any(path.startswith(f) for f in files):
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

class CheckResult:
    def __init__(self, name: str, passed: bool, message: str):
        self.name = name
        self.passed = passed
        self.message = message

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


def check_linked_issue(changed: list[str], issue: str | None) -> CheckResult:
    """Source files changed -> a linked issue must exist."""
    source_files = [f for f in changed if _is_source_file(f)]
    if not source_files:
        return CheckResult("linked-issue", True, "No source files changed — skipped.")

    # If caller supplied --issue, trust it
    if issue:
        # Optionally verify via gh CLI
        if shutil.which("gh"):
            result = _run(["gh", "issue", "view", issue, "--json", "number"])
            if result.returncode == 0:
                return CheckResult("linked-issue", True, f"Issue #{issue} exists.")
            return CheckResult("linked-issue", False, f"Issue #{issue} not found via gh CLI.")
        return CheckResult("linked-issue", True, f"Issue #{issue} provided (gh not installed — skipped remote check).")

    return CheckResult(
        "linked-issue", False,
        "Source files changed but no --issue provided.  Create or link a GitHub issue.",
    )


def check_decision_packet(changed: list[str]) -> CheckResult:
    """If manifest-domain files changed, a decision packet must exist."""
    domain_files = [f for f in changed if _is_manifest_domain_file(f)]
    if not domain_files:
        return CheckResult("decision-packet", True, "No manifest-domain files changed — skipped.")

    packets = list(Path("docs/decisions").glob("issue-*.yaml")) if Path("docs/decisions").exists() else []
    if packets:
        return CheckResult("decision-packet", True, f"Found {len(packets)} decision packet(s).")
    return CheckResult(
        "decision-packet", False,
        "Manifest-domain files changed but no decision packet found at docs/decisions/issue-*.yaml.",
    )


def check_lld_adr_for_api(changed: list[str]) -> CheckResult:
    """If API/controller files changed, LLD or ADR must also be updated."""
    api_files = [f for f in changed if _is_api_or_controller(f)]
    if not api_files:
        return CheckResult("lld-adr-update", True, "No API/controller files changed — skipped.")

    doc_updates = [f for f in changed if _is_doc_lld_or_adr(f)]
    if doc_updates:
        return CheckResult("lld-adr-update", True, "API files changed and LLD/ADR docs updated.")
    return CheckResult(
        "lld-adr-update", False,
        "API/controller files changed but no LLD or ADR doc was updated in this changeset.",
    )


def check_test_registry(changed: list[str]) -> CheckResult:
    """If test files changed, test-registry.yaml must also be updated."""
    test_files = [f for f in changed if _is_test_file(f)]
    if not test_files:
        return CheckResult("test-registry", True, "No test files changed — skipped.")

    if "test-registry.yaml" in " ".join(changed):
        return CheckResult("test-registry", True, "Test files changed and test-registry.yaml updated.")
    return CheckResult(
        "test-registry", False,
        "Test files changed but test-registry.yaml was not updated.",
    )


def check_rollout_plan(changed: list[str]) -> CheckResult:
    """If IaC/deployment files changed, a rollout plan must exist."""
    iac_files = [f for f in changed if _is_iac_file(f)]
    if not iac_files:
        return CheckResult("rollout-plan", True, "No IaC/deployment files changed — skipped.")

    # Look for rollout plan in decision packets or a dedicated file
    has_plan = False
    decisions_dir = Path("docs/decisions")
    if decisions_dir.exists():
        for packet in decisions_dir.glob("issue-*.yaml"):
            try:
                with open(packet) as f:
                    data = yaml.safe_load(f) if yaml else {}
                if data and "rollout" in str(data).lower():
                    has_plan = True
                    break
            except Exception:
                pass

    # Also accept a rollout-plan.md in the PR
    if any("rollout" in f.lower() for f in changed):
        has_plan = True

    if has_plan:
        return CheckResult("rollout-plan", True, "IaC files changed and rollout plan found.")
    return CheckResult(
        "rollout-plan", False,
        "IaC/deployment files changed but no rollout plan found in decision packets or changed files.",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight traceability check.")
    parser.add_argument("--issue", default=None, help="GitHub issue number linked to this change.")
    parser.add_argument(
        "--changed-files", nargs="*", default=None,
        help="Explicit list of changed files.  If omitted, detected via git diff.",
    )
    parser.add_argument(
        "--base-ref", default="origin/main",
        help="Git base ref for diff (default: origin/main).",
    )
    args = parser.parse_args()

    changed = args.changed_files if args.changed_files else _git_changed_files(args.base_ref)
    if not changed:
        print("[INFO] No changed files detected — nothing to check.")
        return 0

    print(f"Checking {len(changed)} changed file(s)...\n")

    results = [
        check_linked_issue(changed, args.issue),
        check_decision_packet(changed),
        check_lld_adr_for_api(changed),
        check_test_registry(changed),
        check_rollout_plan(changed),
    ]

    for r in results:
        print(r)

    failures = [r for r in results if not r.passed]
    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED.  Address the issues above before proceeding.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
