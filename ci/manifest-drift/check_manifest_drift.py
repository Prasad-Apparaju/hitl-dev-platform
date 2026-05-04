#!/usr/bin/env python3
"""Enhanced manifest drift checker.

Detects four categories of drift between docs/system-manifest.yaml and the
actual codebase:

  1. UNLISTED FILES  — source files on disk not tracked by any domain
  2. DELETED FILES   — manifest references files that no longer exist
  3. CROSS-DOMAIN IMPORTS — a file in domain A imports directly from
     domain B instead of using the facade API
  4. MISSING FACADE COVERAGE — facade_apis list functions/classes that
     don't exist in the domain's source files

Exit codes:
  0 — no errors (warnings may still be printed)
  1 — at least one ERROR-level finding

Usage:
    python ci/manifest-drift/check_manifest_drift.py
    python ci/manifest-drift/check_manifest_drift.py --manifest docs/system-manifest.yaml
    python ci/manifest-drift/check_manifest_drift.py --source-dirs app/ src/ lib/
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_manifest(path: Path) -> dict[str, Any]:
    """Load and return the parsed YAML manifest."""
    return yaml.safe_load(path.read_text()) or {}


def _build_file_to_domain(manifest: dict[str, Any]) -> dict[str, str]:
    """Map every listed file path to its owning domain name."""
    mapping: dict[str, str] = {}
    for domain, data in manifest.get("domains", {}).items():
        for f in data.get("files", []):
            mapping[f] = domain
    return mapping


def _collect_source_files(root: Path, source_dirs: list[str]) -> list[Path]:
    """Recursively collect .py files under the given source directories."""
    files: list[Path] = []
    for sd in source_dirs:
        base = root / sd
        if base.is_dir():
            files.extend(base.rglob("*.py"))
    return files


def _top_level_names(filepath: Path) -> set[str]:
    """Return the set of top-level class and function names defined in a Python file."""
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _extract_imports(filepath: Path) -> list[str]:
    """Return a list of dotted module paths imported by a Python file.

    Uses AST parsing — no regex.  Returns strings like 'app.services.auth'
    or 'app.models.user'.
    """
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _module_to_filepath(module: str) -> str:
    """Convert a dotted module path to a file path (e.g. app.services.auth -> app/services/auth.py)."""
    return module.replace(".", "/") + ".py"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_unlisted_files(
    root: Path,
    manifest: dict[str, Any],
    source_dirs: list[str],
) -> list[str]:
    """Find source files on disk that are not listed in any domain."""
    listed = set()
    for _domain, data in manifest.get("domains", {}).items():
        for f in data.get("files", []):
            listed.add(f)

    warnings: list[str] = []
    for fpath in _collect_source_files(root, source_dirs):
        rel = str(fpath.relative_to(root))
        # Skip __pycache__, migrations, __init__.py (typically boilerplate)
        if "__pycache__" in rel or "__init__.py" in fpath.name:
            continue
        if rel not in listed:
            warnings.append(rel)
    return warnings


def check_deleted_files(
    root: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Find files listed in the manifest that no longer exist on disk."""
    errors: list[str] = []
    for domain, data in manifest.get("domains", {}).items():
        for f in data.get("files", []):
            full = root / f
            if not full.exists() and not (root / f.rstrip("/")).is_dir():
                errors.append(f"{domain}: {f}")
    return errors


def check_cross_domain_imports(
    root: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Flag files that import directly from another domain's files."""
    file_to_domain = _build_file_to_domain(manifest)

    # Build a set of module prefixes per domain by converting file paths to
    # dotted module roots.  For example app/services/auth.py -> app/services/auth
    # belongs to domain "auth".
    file_modules: dict[str, str] = {}
    for fpath, domain in file_to_domain.items():
        if fpath.endswith(".py"):
            mod = fpath[:-3].replace("/", ".")
            file_modules[mod] = domain

    warnings: list[str] = []
    for fpath, src_domain in file_to_domain.items():
        full = root / fpath
        if not full.exists() or not fpath.endswith(".py"):
            continue

        for imp in _extract_imports(full):
            # Check if this import resolves to a file owned by a different domain
            target_domain = file_modules.get(imp)
            if target_domain and target_domain != src_domain:
                warnings.append(
                    f"{fpath} ({src_domain}) imports {imp} ({target_domain}) — "
                    f"use facade API instead"
                )
    return warnings


def check_facade_coverage(
    root: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Check that facade_api names actually exist as top-level definitions in the domain's files."""
    warnings: list[str] = []
    for domain, data in manifest.get("domains", {}).items():
        facade_apis = data.get("facade_apis", {})
        if not facade_apis:
            continue

        # Collect all top-level names across the domain's Python files
        all_names: set[str] = set()
        for f in data.get("files", []):
            full = root / f
            if full.exists() and f.endswith(".py"):
                all_names.update(_top_level_names(full))

        for api_name in facade_apis:
            if api_name not in all_names:
                warnings.append(
                    f"{domain}: facade API '{api_name}' not found as a top-level "
                    f"function/class in domain files"
                )
    return warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enhanced manifest drift checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--manifest",
        default="docs/system-manifest.yaml",
        help="Path to system manifest (default: docs/system-manifest.yaml)",
    )
    parser.add_argument(
        "--source-dirs",
        nargs="+",
        default=["app/", "src/"],
        help="Directories to scan for unlisted source files (default: app/ src/)",
    )
    parser.add_argument(
        "--python-only",
        action="store_true",
        default=True,
        help="Only check Python files (default: true)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Treat unlisted files as errors (exit 1) instead of warnings",
    )
    parser.add_argument(
        "--fail-cross-domain-imports",
        action="store_true",
        default=False,
        help="Treat cross-domain imports as errors (exit 1) instead of warnings",
    )
    parser.add_argument(
        "--fail-missing-facade",
        action="store_true",
        default=False,
        help="Treat missing facade coverage as errors (exit 1) instead of warnings",
    )
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        default=False,
        help="Exit 1 if the manifest file does not exist (useful in CI to ensure it is always present)",
    )
    args = parser.parse_args()

    root = Path.cwd()
    manifest_path = root / args.manifest

    if not manifest_path.exists():
        if args.require_manifest:
            print(f"ERROR: No manifest at {args.manifest} — required by --require-manifest.")
            sys.exit(1)
        print(f"No manifest at {args.manifest} — skipping drift check.")
        sys.exit(0)

    manifest = _load_manifest(manifest_path)

    # -- Run all checks --
    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []

    # 1. Deleted files (ERROR — manifest references something that doesn't exist)
    for item in check_deleted_files(root, manifest):
        errors.append(("DELETED FILE", item))

    # 2. Unlisted files (ERROR in --strict mode, WARNING otherwise)
    for item in check_unlisted_files(root, manifest, args.source_dirs):
        if args.strict:
            errors.append(("UNLISTED FILE", item))
        else:
            warnings.append(("UNLISTED FILE", item))

    # 3. Cross-domain imports (ERROR with --fail-cross-domain-imports, WARNING otherwise)
    for item in check_cross_domain_imports(root, manifest):
        if args.fail_cross_domain_imports:
            errors.append(("CROSS-DOMAIN IMPORT", item))
        else:
            warnings.append(("CROSS-DOMAIN IMPORT", item))

    # 4. Missing facade coverage (ERROR with --fail-missing-facade, WARNING otherwise)
    for item in check_facade_coverage(root, manifest):
        if args.fail_missing_facade:
            errors.append(("MISSING FACADE", item))
        else:
            warnings.append(("MISSING FACADE", item))

    # -- Output --
    has_errors = len(errors) > 0

    if errors:
        print(f"\n{'='*60}")
        print(f"ERRORS ({len(errors)}) — these block deployment")
        print(f"{'='*60}")
        for category, detail in errors:
            print(f"  [{category}] {detail}")

    if warnings:
        print(f"\n{'='*60}")
        print(f"WARNINGS ({len(warnings)}) — advisory, should be addressed")
        print(f"{'='*60}")
        for category, detail in warnings:
            print(f"  [{category}] {detail}")

    if not errors and not warnings:
        total = sum(len(d.get("files", [])) for d in manifest.get("domains", {}).values())
        print(f"Manifest OK — all {total} listed files exist, no drift detected.")

    # Summary line
    print(f"\nTotal: {len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
