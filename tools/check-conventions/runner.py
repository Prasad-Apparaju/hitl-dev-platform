#!/usr/bin/env python3
"""Pluggable convention checker — reads a YAML config and runs checks.

Supports universal checks (built-in) and project-specific checks
defined in convention-checks.yaml. Designed for CI integration.

Usage:
    python runner.py --config convention-checks.yaml
    python runner.py --config convention-checks.yaml --verbose
    python runner.py --config convention-checks.yaml --only manifest_drift
"""

import argparse
import ast
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(1)

# ── Results tracking ──

errors: list[str] = []
passes: list[str] = []
warnings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)

def passed(msg: str) -> None:
    passes.append(msg)

def warn(msg: str) -> None:
    warnings.append(msg)


# ── AST helpers ──

def find_subclasses(base_name: str, search_dir: Path) -> list[tuple[Path, str]]:
    """Find classes that inherit from base_name."""
    results = []
    for py in search_dir.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(), filename=str(py))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    name = base.id if isinstance(base, ast.Name) else (
                        base.attr if isinstance(base, ast.Attribute) else "")
                    if name == base_name:
                        results.append((py, node.name))
    return results


def has_method(file_path: Path, class_name: str, method_name: str) -> bool:
    """Check if a class has a specific method."""
    try:
        tree = ast.parse(file_path.read_text(), filename=str(file_path))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return any(
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == method_name
                for item in node.body
            )
    return False


# ── Check type implementations ──

def run_subclass_method_check(check: dict, root: Path) -> None:
    """Verify subclasses of X implement required methods."""
    base = check["base_class"]
    required = check.get("required_methods", [])
    search = root / check.get("directory", "")

    subclasses = find_subclasses(base, search)
    if not subclasses:
        passed(f"{check['name']}: no {base} subclasses found")
        return

    for fpath, cls in subclasses:
        if cls == base:
            continue
        for method in required:
            if has_method(fpath, cls, method):
                passed(f"{check['name']}: {cls} implements {method}")
            else:
                error(f"{check['name']}: {cls} in {fpath.relative_to(root)} missing {method}()")


def run_import_check(check: dict, root: Path) -> None:
    """Verify files that import A also import B."""
    directory = root / check["directory"]
    required = check["required_import"]
    triggers = check.get("trigger_imports", [])

    if not directory.exists():
        passed(f"{check['name']}: directory {check['directory']} not found")
        return

    for py in directory.rglob("*.py"):
        if py.name.startswith("__"):
            continue
        content = py.read_text()
        has_trigger = any(t in content for t in triggers)
        if has_trigger:
            if required in content:
                passed(f"{check['name']}: {py.name} has {required}")
            else:
                error(f"{check['name']}: {py.relative_to(root)} imports {triggers} but not {required}")


def run_pattern_check(check: dict, root: Path) -> None:
    """Verify files with pattern X also have pattern Y."""
    directory = root / check["directory"]
    trigger = check["trigger_pattern"]
    required = check.get("required_pattern")
    forbidden = check.get("forbidden_pattern")

    if not directory.exists():
        passed(f"{check['name']}: directory {check['directory']} not found")
        return

    for py in directory.rglob("*.py"):
        if py.name.startswith("__"):
            continue
        content = py.read_text()
        if trigger not in content:
            continue
        if required and required not in content:
            error(f"{check['name']}: {py.relative_to(root)} has '{trigger}' but not '{required}'")
        elif forbidden and forbidden in content:
            error(f"{check['name']}: {py.relative_to(root)} has '{trigger}' with forbidden '{forbidden}'")
        else:
            passed(f"{check['name']}: {py.name} OK")


def run_file_contains(check: dict, root: Path) -> None:
    """Verify a file contains required text."""
    fpath = root / check["file"]
    required = check["required_text"]

    if not fpath.exists():
        error(f"{check['name']}: {check['file']} not found")
        return

    if required in fpath.read_text():
        passed(f"{check['name']}: {check['file']} contains '{required}'")
    else:
        error(f"{check['name']}: {check['file']} missing '{required}'")


# ── Universal checks ──

def check_manifest_drift(root: Path, manifest_path: str = "docs/system-manifest.yaml") -> None:
    """Verify files listed in the manifest exist on disk."""
    mpath = root / manifest_path
    if not mpath.exists():
        passed("manifest_drift: manifest not found (OK if not generated yet)")
        return

    manifest = yaml.safe_load(mpath.read_text())
    domains = manifest.get("domains", {})
    missing = []

    for domain, data in domains.items():
        for f in data.get("files", []):
            full = root / f
            if not full.exists() and not (root / f.rstrip("/")).is_dir():
                missing.append(f"{domain}: {f}")

    if missing:
        for m in missing:
            error(f"manifest_drift: file not on disk: {m}")
    else:
        total = sum(len(d.get("files", [])) for d in domains.values())
        passed(f"manifest_drift: all {total} manifest files exist")


def check_mermaid_br_tags(root: Path) -> None:
    """No <br/> inside Mermaid code blocks."""
    docs = root / "docs"
    if not docs.exists():
        passed("mermaid_br_tags: no docs/ directory")
        return

    violations = []
    for md in docs.rglob("*.md"):
        content = md.read_text()
        for match in re.finditer(r"```mermaid\n(.*?)```", content, re.DOTALL):
            if "<br" in match.group(1):
                violations.append(str(md.relative_to(root)))
                break

    if violations:
        for v in violations:
            error(f"mermaid_br_tags: {v} has <br/> in mermaid block")
    else:
        passed(f"mermaid_br_tags: clean across all docs")


def check_inline_comments(root: Path, source_dir: str = "app") -> None:
    """Files >50 lines should have >5% comment density (warning only)."""
    src = root / source_dir
    if not src.exists():
        # Try common alternatives
        for alt in ["src", "lib", "pkg"]:
            src = root / alt
            if src.exists():
                break
        else:
            passed("inline_comments: no source directory found")
            return

    for py in src.rglob("*.py"):
        if py.name.startswith("__"):
            continue
        try:
            lines = py.read_text().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if len(lines) < 50:
            continue
        code = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        comments = [l for l in lines if l.strip().startswith("#")]
        if code and len(comments) / len(code) < 0.05:
            warn(f"inline_comments: {py.relative_to(root)} ({len(code)} code, {len(comments)} comments)")


# ── Main runner ──

CHECK_TYPES = {
    "subclass_method_check": run_subclass_method_check,
    "import_check": run_import_check,
    "pattern_check": run_pattern_check,
    "file_contains": run_file_contains,
}

UNIVERSAL_CHECKS = {
    "manifest_drift": check_manifest_drift,
    "mermaid_br_tags": check_mermaid_br_tags,
    "inline_comments": check_inline_comments,
}


def main():
    parser = argparse.ArgumentParser(description="Convention checker")
    parser.add_argument("--config", default="convention-checks.yaml", help="Config file path")
    parser.add_argument("--verbose", action="store_true", help="Show passing checks")
    parser.add_argument("--only", help="Run only this check name")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config_path = root / args.config

    if not config_path.exists():
        print(f"Config not found: {config_path}")
        sys.exit(1)

    config = yaml.safe_load(config_path.read_text())
    print("Convention checker\n")

    # Run universal checks
    for name in config.get("universal_checks", []):
        if args.only and args.only != name:
            continue
        check_fn = UNIVERSAL_CHECKS.get(name)
        if check_fn:
            check_fn(root)
        else:
            warn(f"Unknown universal check: {name}")

    # Run project-specific checks
    for check in config.get("project_checks", []):
        if args.only and args.only != check.get("name"):
            continue
        check_type = check.get("type")
        runner = CHECK_TYPES.get(check_type)
        if runner:
            runner(check, root)
        else:
            warn(f"Unknown check type: {check_type} for {check.get('name')}")

    # Report
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")

    if args.verbose and passes:
        print(f"\n✅ Passed ({len(passes)}):")
        for p in passes:
            print(f"  ✓ {p}")

    if errors:
        print(f"\n❌ Failed ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n{len(errors)} violation(s). Fix before merging.")
        sys.exit(1)
    else:
        print(f"\n✅ All checks passed ({len(passes)} checks, 0 violations)")


if __name__ == "__main__":
    main()
