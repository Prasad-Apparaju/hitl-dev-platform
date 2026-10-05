#!/usr/bin/env python3
"""Assemble a plugin-shaped directory for the HITL breadcrumb band mod (FR-37, BM-4, BM-7).

`claude plugin validate` and `claude plugin test` want `<dir>/.claude-plugin/plugin.json`,
`<dir>/hooks/hooks.json`, the module beside it, and the tests somewhere under `<dir>`. The source
repo keeps the plugin manifest at ai/claude/plugin/plugin.json and the mod in ai/claude/hooks/, so
this script lays the few files out the way the CLI expects. Stdlib only.

Usage: python3 ci/breadcrumb-mod/assemble_plugin.py [<out>]
Default <out> is a fresh temp directory; the path is printed either way.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOKS = os.path.join(ROOT, "ai", "claude", "hooks")
PLUGIN_JSON = os.path.join(ROOT, "ai", "claude", "plugin", "plugin.json")
MODULE = "breadcrumb-band.js"


def assemble(out):
    with open(PLUGIN_JSON, encoding="utf-8") as f:
        version = json.load(f)["version"]
    os.makedirs(os.path.join(out, ".claude-plugin"), exist_ok=True)
    os.makedirs(os.path.join(out, "hooks"), exist_ok=True)
    os.makedirs(os.path.join(out, "tests"), exist_ok=True)
    manifest = {"name": "hitl", "version": version,
                "description": "HITL breadcrumb band mod, assembled for validation"}
    with open(os.path.join(out, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    for name in ("hooks.json", MODULE):
        shutil.copy2(os.path.join(HOOKS, name), os.path.join(out, "hooks", name))
    tests_dir = os.path.join(HOOKS, "tests")
    for name in sorted(os.listdir(tests_dir)):
        if name.endswith(".test.ts"):
            shutil.copy2(os.path.join(tests_dir, name), os.path.join(out, "tests", name))
    return out


def main(argv):
    if len(argv) > 2 or (len(argv) == 2 and argv[1] in ("-h", "--help")):
        print(__doc__.strip())
        return 2
    out = argv[1] if len(argv) == 2 else tempfile.mkdtemp(prefix="hitl-breadcrumb-mod-")
    print(assemble(os.path.abspath(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
