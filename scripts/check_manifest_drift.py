#!/usr/bin/env python3
"""Check that files listed in docs/system-manifest.yaml exist on disk.

Exits with code 1 if any listed file is missing (manifest has drifted
from the actual codebase). Used as a pre-commit hook and in CI.

Usage:
    python scripts/check_manifest_drift.py
    python scripts/check_manifest_drift.py --manifest docs/system-manifest.yaml
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(1)


def check_drift(root: Path, manifest_path: Path) -> list[str]:
    """Return list of missing files referenced in the manifest."""
    if not manifest_path.exists():
        return []  # no manifest yet — not an error

    manifest = yaml.safe_load(manifest_path.read_text())
    domains = manifest.get("domains", {})
    missing = []

    for domain, data in domains.items():
        for f in data.get("files", []):
            full = root / f
            if not full.exists() and not (root / f.rstrip("/")).is_dir():
                missing.append(f"{domain}: {f}")

    return missing


def main():
    parser = argparse.ArgumentParser(description="Check manifest drift")
    parser.add_argument(
        "--manifest",
        default="docs/system-manifest.yaml",
        help="Path to system manifest (default: docs/system-manifest.yaml)",
    )
    args = parser.parse_args()

    root = Path.cwd()
    manifest_path = root / args.manifest

    if not manifest_path.exists():
        print(f"No manifest at {args.manifest} — skipping drift check.")
        sys.exit(0)

    missing = check_drift(root, manifest_path)

    if missing:
        print(f"Manifest drift detected — {len(missing)} files not on disk:")
        for m in missing:
            print(f"  {m}")
        print("\nUpdate the manifest or create the missing files.")
        sys.exit(1)
    else:
        manifest = yaml.safe_load(manifest_path.read_text())
        total = sum(len(d.get("files", [])) for d in manifest.get("domains", {}).values())
        print(f"Manifest OK — all {total} listed files exist.")


if __name__ == "__main__":
    main()
