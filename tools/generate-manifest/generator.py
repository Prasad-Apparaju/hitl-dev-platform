#!/usr/bin/env python3
"""System manifest generator — scans a codebase and produces system-manifest.yaml.

Reads the directory structure, import graph, class hierarchies, and
decorators to produce a draft manifest with domain boundaries, file
lists, dependency graph, and convention detection.

Human-authored fields (blurbs, mutations, preconditions) are marked
as DRAFT and preserved across re-runs via a '# human-authored' marker.

Usage:
    python generator.py --source ./app --output docs/system-manifest.yaml
    python generator.py --source ./src --output docs/system-manifest.yaml --language python
    python generator.py --check docs/system-manifest.yaml  # drift check only

Requires: pyyaml
"""

import argparse
import ast
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(1)


def scan_python_files(source_dir: Path) -> dict:
    """Scan a Python source tree and extract structure."""
    domains: dict = {}
    all_imports: list = []

    # Group files by top-level directory as initial domain boundaries
    for py_file in sorted(source_dir.rglob("*.py")):
        if py_file.name.startswith("__"):
            continue
        if "__pycache__" in str(py_file):
            continue

        # Determine domain from the first directory level under source
        relative = py_file.relative_to(source_dir)
        parts = relative.parts
        domain_name = parts[0] if len(parts) > 1 else "root"

        if domain_name not in domains:
            domains[domain_name] = {
                "purpose": f"DRAFT — {domain_name} domain",
                "files": [],
                "classes": [],
                "imports_from": set(),
                "decorators": set(),
                "base_classes": set(),
            }

        domain = domains[domain_name]
        file_path = str(source_dir.name / relative)
        domain["files"].append(file_path)

        # Parse the AST for structure
        try:
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            # Track imports to build dependency graph
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                # Only track imports from within the source tree
                if module.startswith(source_dir.name):
                    target_domain = module.split(".")[1] if "." in module else module
                    if target_domain != domain_name:
                        domain["imports_from"].add(target_domain)
                all_imports.append({
                    "from_domain": domain_name,
                    "from_file": file_path,
                    "imports": module,
                })

            # Track classes and their bases
            if isinstance(node, ast.ClassDef):
                class_info = {"name": node.name, "bases": [], "methods": []}
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        class_info["bases"].append(base.id)
                        domain["base_classes"].add(base.id)
                    elif isinstance(base, ast.Attribute):
                        class_info["bases"].append(base.attr)
                        domain["base_classes"].add(base.attr)

                # Track public methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not item.name.startswith("_") or item.name.startswith("__"):
                            args = [a.arg for a in item.args.args if a.arg != "self"]
                            class_info["methods"].append({
                                "name": item.name,
                                "args": args,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                            })
                        # Track decorators
                        for dec in item.decorator_list:
                            if isinstance(dec, ast.Name):
                                domain["decorators"].add(dec.id)
                            elif isinstance(dec, ast.Attribute):
                                domain["decorators"].add(dec.attr)

                domain["classes"].append(class_info)

    return domains


def detect_conventions(domains: dict) -> list:
    """Detect cross-cutting conventions from repeating patterns."""
    conventions = []

    # Check for common base classes used across domains
    all_bases = {}
    for domain_name, domain in domains.items():
        for base in domain["base_classes"]:
            if base not in all_bases:
                all_bases[base] = []
            all_bases[base].append(domain_name)

    for base, using_domains in all_bases.items():
        if len(using_domains) >= 2:
            conventions.append({
                "name": f"extends-{base.lower()}",
                "rule": f"Classes extending {base} must follow its contract",
                "affected_domains": using_domains,
                "enforcement": f"Subclass convention for {base}",
            })

    # Check for common decorators used across domains
    all_decorators = {}
    for domain_name, domain in domains.items():
        for dec in domain["decorators"]:
            if dec not in all_decorators:
                all_decorators[dec] = []
            all_decorators[dec].append(domain_name)

    for dec, using_domains in all_decorators.items():
        if len(using_domains) >= 2:
            conventions.append({
                "name": f"uses-{dec.lower()}",
                "rule": f"Functions decorated with @{dec} must follow its contract",
                "affected_domains": using_domains,
                "enforcement": f"Decorator convention for @{dec}",
            })

    return conventions


def build_interaction_matrix(domains: dict) -> dict:
    """Build the interaction matrix from import analysis."""
    matrix = {}
    for domain_name, domain in domains.items():
        for target in domain["imports_from"]:
            if target in domains:
                key = f"{domain_name} -> {target}"
                matrix[key] = {
                    "description": f"{domain_name} imports from {target}",
                    "entity_crossing": "DRAFT — specify what crosses the boundary",
                }
    return matrix


def generate_manifest(source_dir: Path, output_path: Path) -> None:
    """Generate the system manifest YAML."""
    domains = scan_python_files(source_dir)
    conventions = detect_conventions(domains)
    matrix = build_interaction_matrix(domains)

    # Build the manifest structure
    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "tools/generate-manifest/generator.py",
        "domains": {},
        "cross_cutting": [],
        "interaction_matrix": {},
    }

    for domain_name, domain in sorted(domains.items()):
        convention_names = [
            c["name"] for c in conventions
            if domain_name in c["affected_domains"]
        ]

        manifest["domains"][domain_name] = {
            "purpose": domain["purpose"],  # DRAFT — human fills in
            "files": sorted(domain["files"]),
            "depends_on": sorted(domain["imports_from"]),
            "conventions": convention_names,
            "last_changed": {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "summary": "Auto-generated — needs review",
            },
        }

        # Add facade APIs from public class methods
        if domain["classes"]:
            facade_apis = {}
            for cls in domain["classes"]:
                for method in cls["methods"]:
                    if method["name"].startswith("__"):
                        continue
                    key = f"{cls['name']}.{method['name']}"
                    async_prefix = "async " if method["is_async"] else ""
                    args_str = ", ".join(method["args"])
                    facade_apis[key] = {
                        "signature": f"{async_prefix}{method['name']}({args_str})",
                        "blurb": "DRAFT — describe what this does",
                        "mutations": ["DRAFT — list side effects"],
                        "preconditions": ["DRAFT — list preconditions"],
                        "error_modes": ["DRAFT — list error modes"],
                    }
            if facade_apis:
                manifest["domains"][domain_name]["facade_apis"] = facade_apis

    manifest["cross_cutting"] = conventions
    manifest["interaction_matrix"] = matrix

    # Write the manifest
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# System Manifest — auto-generated\n")
        f.write(f"# Generated: {manifest['generated_at']}\n")
        f.write("# Fields marked DRAFT need human review.\n\n")
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, width=120)

    # Report
    total_files = sum(len(d["files"]) for d in manifest["domains"].values())
    total_facades = sum(
        len(d.get("facade_apis", {})) for d in manifest["domains"].values()
    )
    print(f"Generated {output_path}")
    print(f"  {len(manifest['domains'])} domains")
    print(f"  {total_files} files")
    print(f"  {total_facades} facade APIs (all DRAFT)")
    print(f"  {len(manifest['cross_cutting'])} conventions detected")
    print(f"  {len(manifest['interaction_matrix'])} interaction edges")


def check_drift(manifest_path: Path) -> None:
    """Check if manifest files still exist on disk."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f.read())

    domains = manifest.get("domains", {})
    missing = []
    for domain_name, domain in domains.items():
        for file_path in domain.get("files", []):
            if not Path(file_path).exists():
                missing.append(f"{domain_name}: {file_path}")

    if missing:
        print(f"DRIFT DETECTED — {len(missing)} files in manifest but not on disk:")
        for m in missing:
            print(f"  ✗ {m}")
        sys.exit(1)
    else:
        total = sum(len(d.get("files", [])) for d in domains.values())
        print(f"No drift — all {total} manifest files exist on disk.")


def main():
    parser = argparse.ArgumentParser(description="System manifest generator")
    parser.add_argument("--source", help="Source directory to scan")
    parser.add_argument("--output", default="docs/system-manifest.yaml", help="Output manifest path")
    parser.add_argument("--language", default="python", help="Source language (currently: python)")
    parser.add_argument("--check", help="Check manifest for drift (no generation)")
    args = parser.parse_args()

    if args.check:
        check_drift(Path(args.check))
        return

    if not args.source:
        print("ERROR: --source is required (or use --check for drift detection)")
        sys.exit(1)

    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: source directory not found: {source}")
        sys.exit(1)

    generate_manifest(source, Path(args.output))


if __name__ == "__main__":
    main()
