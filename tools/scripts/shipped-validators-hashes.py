#!/usr/bin/env python3
"""Append the current tree's synced-validator hashes to ci/shipped-validators.sha256.

Run at release time (docs/releasing.md step 3). dev-update uses the manifest to tell an unmodified
older copy of a validator from a repo's own edit (plugin #35), so every version that ships must be
in it; ci/wiring/test_shipped_validators_manifest.py fails the build when one is missing.

Usage: python3 tools/scripts/shipped-validators-hashes.py [--check]
  --check   exit 1 if any current file is missing from the manifest, write nothing
"""
import hashlib, io, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MANIFEST = os.path.join(ROOT, "ci", "shipped-validators.sha256")

# source-repo path -> the project-relative path dev-update installs it at (migrate_project.SYNC_SETS)
SOURCES = (
    ("ci/first-pass", "ci/first-pass", True),
    ("ai/shared/workflows.yaml", "ci/first-pass/workflows.yaml", False),
    ("ci/manifest-agentic", "ci/manifest-agentic", True),
    ("tools/manifest-agentic", "tools/manifest-agentic", True),
    ("ci/adversarial", "ci/adversarial", True),
    ("ci/manifest-drift", "ci/manifest-drift", True),
)


def current():
    out = []
    for src, dst, is_dir in SOURCES:
        p = os.path.join(ROOT, src)
        if is_dir:
            if not os.path.isdir(p):
                continue
            for n in sorted(os.listdir(p)):
                if n.endswith(".py") and not n.startswith("test_") and n != "conftest.py":
                    out.append((os.path.join(p, n), dst + "/" + n))
        elif os.path.isfile(p):
            out.append((p, dst))
    res = []
    for path, rel in out:
        with io.open(path, "rb") as f:
            res.append((hashlib.sha256(f.read()).hexdigest(), rel))
    return res


def listed():
    have = set()
    if os.path.isfile(MANIFEST):
        for line in io.open(MANIFEST, encoding="utf-8"):
            parts = line.split("#", 1)[0].split()
            if len(parts) >= 2:
                have.add((parts[0], parts[1]))
    return have


def main(argv):
    check = "--check" in argv
    have = listed()
    missing = [(h, rel) for h, rel in current() if (h, rel) not in have]
    if not missing:
        print("manifest current: every synced validator in the tree is listed")
        return 0
    if check:
        for h, rel in missing:
            print(f"missing: {rel}")
        print("run tools/scripts/shipped-validators-hashes.py to append them")
        return 1
    ver = json.load(io.open(os.path.join(ROOT, "ai", "claude", "plugin", "plugin.json")))["version"]
    with io.open(MANIFEST, "a", encoding="utf-8") as f:
        for h, rel in missing:
            f.write(f"{h}  {rel}  # {ver}\n")
            print(f"appended {rel} ({ver})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
