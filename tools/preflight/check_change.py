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
# Issue discovery from decision packets
# ---------------------------------------------------------------------------

def _discover_issue_from_decision_packets(changed: list[str]) -> str | None:
    """Try to find an issue number from decision packets in the changed files ONLY.

    Does NOT fall back to scanning all historical packets — that would pick up
    stale packets unrelated to the current change.
    """
    if yaml is None:
        return None

    # Only look at decision packets that are part of this changeset
    packet_paths = [f for f in changed if f.startswith("docs/decisions/issue-") and f.endswith(".yaml")]

    for packet_path in packet_paths:
        try:
            with open(packet_path) as f:
                data = yaml.safe_load(f)
            if data and "issue" in data:
                return str(data["issue"])
        except Exception:
            continue
    return None


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


def check_linked_issue(changed: list[str], issue: str | None, *, strict: bool = False) -> CheckResult:
    """Source files changed -> a linked issue must exist."""
    source_files = [f for f in changed if _is_source_file(f)]
    if not source_files:
        return CheckResult("linked-issue", True, "No source files changed — skipped.")

    # If caller supplied --issue, trust it
    if issue:
        # Verify via gh CLI if available.  In strict mode, a failed verification
        # is an error (bogus issue numbers must not pass CI).  In non-strict mode
        # treat failure as a warning since gh may fail due to missing GH_TOKEN or
        # network issues.
        if shutil.which("gh"):
            result = _run(["gh", "issue", "view", issue, "--json", "number"])
            if result.returncode == 0:
                return CheckResult("linked-issue", True, f"Issue #{issue} exists.")
            # gh is available but verification failed
            if strict:
                return CheckResult(
                    "linked-issue", False,
                    f"Issue #{issue} could not be verified (gh issue view failed) — strict mode treats this as an error.",
                )
            # non-strict: warn but still pass
            return CheckResult(
                "linked-issue", True,
                f"Issue #{issue} provided (gh CLI verification failed — treating as warning).",
            )
        if strict:
            return CheckResult("linked-issue", False, "gh CLI is required for strict issue verification.")
        return CheckResult("linked-issue", True, f"Issue #{issue} provided (gh not installed — skipped remote check).")

    # Try to discover the issue from decision packets in changed files or docs/decisions/
    discovered_issue = _discover_issue_from_decision_packets(changed)
    if discovered_issue:
        return CheckResult(
            "linked-issue", True,
            f"Issue #{discovered_issue} discovered from decision packet.",
        )

    return CheckResult(
        "linked-issue", False,
        "No linked issue found. Add 'Fixes #NNN' to PR description or include a decision packet in this PR.",
    )


def _resolve_packets_to_validate(
    changed: list[str], issue: str | None,
) -> list[Path]:
    """Return the specific decision packet(s) that should be validated.

    Strategy:
    1. Include any decision packets that appear in the changed files
    2. If we know the active issue number, look for:
       - docs/decisions/issue-<N>.yaml          (single-slice)
       - docs/decisions/issue-<N>-slice-*.yaml  (multi-slice, one per slice)
    3. Never scan all historical packets — they belong to other issues
    """
    seen: set[str] = set()
    packets: list[Path] = []

    # Packets explicitly changed in this PR
    for f in changed:
        if f.startswith("docs/decisions/issue-") and f.endswith(".yaml"):
            p = Path(f)
            if p.exists() and str(p) not in seen:
                packets.append(p)
                seen.add(str(p))

    # The packet for the active issue (may not be in the changed files).
    # Supports both naming patterns:
    #   - Single-slice:  docs/decisions/issue-<N>.yaml
    #   - Multi-slice:   docs/decisions/issue-<N>-slice-<M>.yaml
    if issue:
        target = Path(f"docs/decisions/issue-{issue}.yaml")
        if target.exists() and str(target) not in seen:
            packets.append(target)
            seen.add(str(target))
        decisions_dir = Path("docs/decisions")
        if decisions_dir.exists():
            for slice_packet in sorted(decisions_dir.glob(f"issue-{issue}-slice-*.yaml")):
                if str(slice_packet) not in seen:
                    packets.append(slice_packet)
                    seen.add(str(slice_packet))

    return packets


def _domains_for_changed_files(changed: list[str]) -> set[str]:
    """Determine which system-manifest domains are touched by *changed* source files."""
    if yaml is None:
        return set()
    manifest = Path("docs/system-manifest.yaml")
    if not manifest.exists():
        return set()
    try:
        with open(manifest) as f:
            data = yaml.safe_load(f)
    except Exception:
        return set()
    touched: set[str] = set()
    domains = data.get("domains", {})
    for domain_name, domain_def in domains.items():
        domain_files = domain_def.get("files", [])
        for path in changed:
            if any(path.startswith(df) for df in domain_files):
                touched.add(domain_name)
                break
    return touched


def check_decision_packet(changed: list[str], issue: str | None = None, *, strict: bool = False) -> CheckResult:
    """If manifest-domain files changed, a decision packet must exist and be valid.

    Only validates the packet for the active issue (and any packets in the
    changed files list) — never scans all historical packets.
    """
    domain_files = [f for f in changed if _is_manifest_domain_file(f)]
    if not domain_files:
        return CheckResult("decision-packet", True, "No manifest-domain files changed — skipped.")

    packets = _resolve_packets_to_validate(changed, issue)
    if not packets:
        return CheckResult(
            "decision-packet", False,
            "Manifest-domain files changed but no decision packet found. "
            "Expected docs/decisions/issue-<N>.yaml (single-slice) or "
            "docs/decisions/issue-<N>-slice-<M>.yaml (multi-slice).",
        )

    # Validate the contents of each packet
    if yaml is None:
        return CheckResult("decision-packet", True, f"Found {len(packets)} decision packet(s) (PyYAML not installed — skipped validation).")

    # Determine which domains the changed source files actually touch (for Issue 3)
    touched_domains = _domains_for_changed_files(changed)

    errors: list[str] = []
    warnings: list[str] = []
    for packet in packets:
        try:
            with open(packet) as f:
                data = yaml.safe_load(f)
        except Exception as exc:
            errors.append(f"{packet.name}: failed to parse YAML ({exc})")
            continue

        if not data:
            errors.append(f"{packet.name}: file is empty")
            continue

        prefix = packet.name

        # issue field must be present
        if "issue" not in data:
            errors.append(f"{prefix}: missing 'issue' field")
        elif issue and str(data["issue"]) != str(issue):
            errors.append(f"{prefix}: 'issue' is {data['issue']} but expected {issue} (from --issue)")

        # domains field must be present and non-empty
        packet_domains = data.get("domains")
        if not packet_domains:
            errors.append(f"{prefix}: missing or empty 'domains' field")
        elif touched_domains:
            # Advisory check: warn if a touched domain is missing from the packet
            packet_domain_set = set(packet_domains) if isinstance(packet_domains, list) else set()
            missing = touched_domains - packet_domain_set
            if missing:
                msg = (
                    f"{prefix}: changed files touch domain(s) {sorted(missing)} "
                    f"not listed in packet 'domains' field"
                )
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(f"{msg} (advisory)")

        # source_docs must have at least one entry (hld, lld, or adr)
        source_docs = data.get("source_docs")
        if not source_docs:
            errors.append(f"{prefix}: missing 'source_docs' field")
        elif isinstance(source_docs, dict):
            has_entry = any(source_docs.get(key) for key in ("hld", "lld", "adr"))
            if not has_entry:
                errors.append(f"{prefix}: 'source_docs' must have at least one of: hld, lld, adr")

        # rollout.risk must be present
        rollout = data.get("rollout")
        if not rollout or not isinstance(rollout, dict) or "risk" not in rollout:
            errors.append(f"{prefix}: missing 'rollout.risk' field")

        # risk_level and rollout.risk must agree when both are present
        top_level_risk = data.get("risk_level")
        rollout_risk = rollout.get("risk") if isinstance(rollout, dict) else None
        if top_level_risk and rollout_risk and top_level_risk != rollout_risk:
            errors.append(f"risk_level ({top_level_risk}) and rollout.risk ({rollout_risk}) disagree — use the same value in both fields")

        # tests.registry_updated must be present
        tests = data.get("tests")
        if not tests or not isinstance(tests, dict) or "registry_updated" not in tests:
            errors.append(f"{prefix}: missing 'tests.registry_updated' field")

    # Print warnings (advisory, don't fail the check)
    for w in warnings:
        print(f"[WARN] decision-packet: {w}")

    if errors:
        detail = "; ".join(errors)
        return CheckResult("decision-packet", False, f"Decision packet validation failed: {detail}")

    return CheckResult("decision-packet", True, f"Found and validated {len(packets)} decision packet(s).")


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


TEST_REGISTRY_PATH = "docs/03-engineering/testing/test-registry.yaml"


def check_test_registry(changed: list[str], registry_path: str = TEST_REGISTRY_PATH) -> CheckResult:
    """If test files changed, test-registry.yaml must also be updated."""
    test_files = [f for f in changed if _is_test_file(f)]
    if not test_files:
        return CheckResult("test-registry", True, "No test files changed — skipped.")

    if any(f == registry_path or f.endswith(registry_path) for f in changed):
        return CheckResult("test-registry", True, "Test files changed and test-registry.yaml updated.")
    return CheckResult(
        "test-registry", False,
        f"Test files changed but {registry_path} was not updated.",
    )


def check_rollout_plan(changed: list[str], issue: str | None = None) -> CheckResult:
    """If IaC/deployment files changed, a rollout plan must exist.

    Only checks decision packets relevant to the current change (via
    _resolve_packets_to_validate), not all historical packets.
    """
    iac_files = [f for f in changed if _is_iac_file(f)]
    if not iac_files:
        return CheckResult("rollout-plan", True, "No IaC/deployment files changed — skipped.")

    # Look for a structurally valid rollout section in decision packets
    has_plan = False
    errors: list[str] = []
    packets = _resolve_packets_to_validate(changed, issue)
    for packet in packets:
        try:
            with open(packet) as f:
                data = yaml.safe_load(f) if yaml else {}
        except Exception:
            continue

        if not data:
            continue

        rollout = data.get("rollout")
        if not isinstance(rollout, dict) or not rollout.get("risk"):
            # rollout section missing or has no risk level — not valid
            continue

        # For medium/high/critical risk, a rollout strategy is required
        risk = str(rollout["risk"]).lower()
        if risk in ("medium", "high", "critical") and not rollout.get("strategy"):
            errors.append(
                f"{packet.name}: rollout.risk is '{risk}' but rollout.strategy is missing"
            )
            continue

        has_plan = True
        break

    # Also accept a rollout-plan.md in the PR
    if not has_plan and any("rollout" in f.lower() for f in changed):
        has_plan = True

    if errors and not has_plan:
        detail = "; ".join(errors)
        return CheckResult("rollout-plan", False, f"Rollout plan incomplete: {detail}")

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
    parser.add_argument(
        "--strict", action="store_true", default=False,
        help="Treat domain mismatches as errors instead of warnings.",
    )
    args = parser.parse_args()

    changed = args.changed_files if args.changed_files else _git_changed_files(args.base_ref)
    if not changed:
        print("[INFO] No changed files detected — nothing to check.")
        return 0

    print(f"Checking {len(changed)} changed file(s)...\n")

    results = [
        check_linked_issue(changed, args.issue, strict=args.strict),
        check_decision_packet(changed, args.issue, strict=args.strict),
        check_lld_adr_for_api(changed),
        check_test_registry(changed),
        check_rollout_plan(changed, args.issue),
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
