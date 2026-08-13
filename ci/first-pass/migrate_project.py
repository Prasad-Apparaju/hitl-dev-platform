#!/usr/bin/env python3
"""Bring an already-onboarded product repo up to the current HITL contract.

Onboarding writes `.claude/settings.json` only if it does not already exist, so every repo
onboarded before a change keeps its old file forever and silently misses whatever shipped since.
This is the migration path `/hitl:dev-update` runs.

It does two things, both additive and both reversible:

1. **Merges the permissions block** into `.claude/settings.json` without clobbering anything the
   team added. Existing entries are kept, ours are appended if absent, nothing is removed or
   reordered. A repo with no permissions block gets one; a repo with its own keeps it and gains
   the deny rules.

2. **Reports in-flight change files that were lightened without declaring it** — steps marked
   `skipped`/`starter`, or a populated `skips[]`, with `first_pass` absent. Those certified clean
   under the old validator because enforcement never engaged. After upgrading they will fail
   certification, which is intended, so this names them up front rather than letting the first
   failure look like a regression.

Lives under ci/first-pass/ because that directory is packaged into the plugin by a wildcard and
copied into product repos by onboarding; a new top-level tool would need a build change in the
plugin repo to ship at all.

Usage:
    python3 migrate_project.py [--root .] [--apply]

Default is a dry run. Nothing is written without --apply.
"""
import argparse
import io
import json
import os
import sys

# Kept in step with ai/shared/templates/settings-template.json. Short on purpose: output
# redirection rides along on a permission match (`cmd > file` is permitted by a rule for `cmd`,
# and an exact entry does not help), so every entry grants "write this command's stdout
# anywhere". Never add an interpreter, shell, or package manager.
ALLOW = ["Bash(git add *)"]
DENY = ["Read(./.env)", "Read(./.env.*)", "Read(./**/.env)", "Read(./secrets/**)"]

LIGHTENED = {"skipped", "starter"}


class Unmergeable(Exception):
    """The file is valid JSON but not shaped like settings — refuse rather than guess."""


def merge_permissions(settings):
    """Return (settings, added) with our entries folded in. Never removes or reorders.

    Raises Unmergeable when the existing shape cannot be merged without discarding something. A
    silent replace here would delete a team's configuration to add ours, which is the opposite of
    what a migration is for — and worse than the invalid-JSON path, which already refuses.
    """
    if not isinstance(settings, dict):
        raise Unmergeable(f"top level is {type(settings).__name__}, expected an object")
    perms = settings.get("permissions")
    if perms is None:
        perms = {}
    if not isinstance(perms, dict):
        raise Unmergeable(f"`permissions` is {type(perms).__name__}, expected an object")
    added = {"allow": [], "deny": []}
    for key, wanted in (("allow", ALLOW), ("deny", DENY)):
        have = perms.get(key)
        if have is not None and not isinstance(have, list):
            raise Unmergeable(f"`permissions.{key}` is {type(have).__name__}, expected a list")
        have = list(have) if isinstance(have, list) else []
        for entry in wanted:
            if entry not in have:
                have.append(entry)
                added[key].append(entry)
        perms[key] = have
    settings["permissions"] = perms
    return settings, added


def audit_change_file(change):
    """Why this change file will now fail certification, or [] if it is fine."""
    change = change if isinstance(change, dict) else {}
    fp = change.get("first_pass")
    if fp is not None and fp is not False:
        return []
    reasons = []
    skips = change.get("skips")
    if isinstance(skips, list) and skips:
        reasons.append(f"{len(skips)} skip record(s)")
    wf = change.get("workflow")
    steps = wf.get("steps") if isinstance(wf, dict) and isinstance(wf.get("steps"), list) else []
    # isinstance guard before the membership test: a non-string status is unhashable and `in set()`
    # raises on it, which would turn an advisory audit into a traceback mid-migration.
    lightened = [s.get("key") for s in steps
                 if isinstance(s, dict) and isinstance(s.get("status"), str) and s["status"] in LIGHTENED]
    if lightened:
        reasons.append("lightened step(s): " + ", ".join(str(k) for k in lightened if k))
    return reasons


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    spath = os.path.join(root, ".claude", "settings.json")
    cpath = os.path.join(root, ".hitl", "current-change.yaml")
    changed = False

    # 1) permissions
    if not os.path.isfile(spath):
        print(f"! {spath} not found — this repo is not onboarded. Run an onboarding command first.")
    else:
        try:
            settings = json.load(io.open(spath, encoding="utf-8"))
        except ValueError as e:
            print(f"! {spath} is not valid JSON ({e}) — fix it by hand; refusing to touch it.")
            return 1
        try:
            merged, added = merge_permissions(settings)
        except Unmergeable as e:
            print(f"! {spath}: {e} — fix it by hand; refusing to touch it.")
            return 1
        n = len(added["allow"]) + len(added["deny"])
        if n == 0:
            print("= permissions already current")
        else:
            changed = True
            print(f"+ permissions: {len(added['allow'])} allow, {len(added['deny'])} deny to add")
            for k in ("allow", "deny"):
                for e in added[k]:
                    print(f"    {k}: {e}")
            if a.apply:
                with io.open(spath, "w", encoding="utf-8") as fh:
                    json.dump(merged, fh, indent=2)
                    fh.write("\n")
                print(f"  written to {spath}")

    # 2) in-flight change files
    if os.path.isfile(cpath):
        try:
            import yaml
            change = yaml.safe_load(io.open(cpath, encoding="utf-8")) or {}
        except Exception as e:
            print(f"! could not read {cpath} ({e})")
            change = {}
        reasons = audit_change_file(change)
        if reasons:
            print("\n! this change was lightened without declaring `first_pass`:")
            for r in reasons:
                print(f"    {r}")
            print("  It certified clean before because enforcement never engaged. It will now fail.")
            print("  If the change really is running First Pass, add `first_pass: true`.")
            print("  If not, restore the steps. Do not delete the records to make the check pass.")
        else:
            print("= active change file is consistent")

    if changed and not a.apply:
        print("\n(dry run — re-run with --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
