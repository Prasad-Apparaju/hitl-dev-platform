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
   failure look like a regression. That report is advisory (exit 0). A change file the audit
   could not read — no PyYAML, invalid YAML, or not a mapping — is reported and exits 1: an audit
   that did not run never prints the all-clear (#103).

3. **Syncs the copied-in validators as co-owned files** (`--sync-validators PLUGIN_ROOT`). The
   repo carries its own copy of the plugin's CI tools, and `/hitl:dev-update` used to refresh them
   with a bare `cp`. A repo that had fixed a validator bug ahead of upstream lost the fix on the
   next update — five times in one downstream repo, including runs with no version change (#104).
   Now, per file: absent → install; byte-identical → nothing; **modified in the repo → show the
   diff and leave it alone** unless `--overwrite <path>` names that file; files the repo added →
   never touched; files listed in the directory's `.hitl-optout` → never installed. Same protocol
   the skill already applies to `.semgrep/`.

Lives under ci/first-pass/ because that directory is packaged into the plugin by a wildcard and
copied into product repos by onboarding; a new top-level tool would need a build change in the
plugin repo to ship at all.

Usage:
    python3 migrate_project.py [--root .] [--apply]
    python3 migrate_project.py [--root .] --sync-validators PLUGIN_ROOT [--apply] [--overwrite PATH ...]

Default is a dry run. Nothing is written without --apply.
"""
import argparse
import io
import json
import os
import sys

# This list is the source of truth for what HITL adds to a project's permissions. Short on
# purpose. Three rules, the first two measured against a live session:
#
#   1. Output redirection rides along on a match. `cmd > file` and `cmd >> file` are permitted by
#      a rule for `cmd`, and an EXACT entry with no wildcard does not help. So every entry grants
#      "write this command's stdout to any path". Never allowlist a command whose output is
#      attacker-controlled -- `gh issue view` is the sharp one: issue bodies are untrusted, and
#      `gh issue view N -q .body > .git/hooks/pre-commit` is a working chain.
#   2. Command chaining (`&&`) and each segment of a pipe ARE checked, so those are not the risk.
#   3. Never allowlist an interpreter, shell, or package manager -- python, node, npx, pip, bash
#      and friends are arbitrary code execution.
#
# Most read-only commands (cat, ls, grep, find, and every read-only git/gh subcommand) are
# auto-allowed by Claude Code already and need no entry.
#
# Residual channels this does NOT close, so nobody mistakes a short list for a boundary:
#   - DENY governs the Read TOOL. `cat .env` through Bash is a different path and is auto-allowed,
#     so these rules reduce accidents, not a determined read.
#   - Only stdout `>` and `>>` were measured. stderr (`2>`) and command substitution were not;
#     assume they behave the same until someone measures them.
#   - Rules 1 and 2 are observed behaviour of a particular Claude Code version, not a spec.
#     Re-measure after an upgrade.
#   - Bash-mediated writes bypass the HITL change gate entirely (its matcher is Edit|Write), so an
#     allowlist entry is not backstopped the way a tool-based edit is.
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


# ---------------------------------------------------------------- validator sync (#104)
#
# What dev-update copies into a product repo, and how each target is owned. `dir` sets copy the
# shipped `*.py` files (tests and conftest never ship, and are refused here too in case an older
# build put them in). `mode`:
#   co-owned      absent → install; identical → silent; modified → report + keep; extra → untouched
#   if-present    co-owned, but only when the repo already has the directory (never onboards it)
#   install-only  copied once if absent, then the repo owns it outright — never compared again
SYNC_SETS = (
    {"src": "shared/ci/first-pass",          "dst": "ci/first-pass",          "mode": "co-owned",   "glob": "*.py"},
    {"src": "shared/workflows.yaml",         "dst": "ci/first-pass/workflows.yaml", "mode": "co-owned"},
    {"src": "shared/ci-workflows/first-pass-check.yml", "dst": ".github/workflows/first-pass-check.yml", "mode": "install-only"},
    {"src": "shared/ci/manifest-agentic",    "dst": "ci/manifest-agentic",    "mode": "co-owned",   "glob": "*.py"},
    {"src": "shared/ci/manifest-agentic/manifest-waivers.yaml", "dst": "ci/manifest-agentic/manifest-waivers.yaml", "mode": "install-only"},
    {"src": "shared/tools/manifest-agentic", "dst": "tools/manifest-agentic", "mode": "co-owned",   "glob": "*.py"},
    {"src": "shared/ci/adversarial",         "dst": "ci/adversarial",         "mode": "co-owned",   "glob": "*.py"},
    {"src": "shared/ci/manifest-drift",      "dst": "ci/manifest-drift",      "mode": "if-present", "glob": "*.py"},
)
OPTOUT_NAME = ".hitl-optout"
DIFF_MAX_LINES = 60


def _optout(dst_dir):
    """Paths (relative to dst_dir) the repo has deliberately removed. One per line, `#` comments."""
    path = os.path.join(dst_dir, OPTOUT_NAME)
    if not os.path.isfile(path):
        return set()
    out = set()
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def _pairs(plugin_root, root, spec):
    """([(shipped_file, project_file, name)], project_dir) for one SYNC_SETS entry, or None if the
    shipped source is not in this plugin build (older plugin, or a tool this build does not ship)."""
    src = os.path.join(plugin_root, spec["src"])
    dst = os.path.join(root, spec["dst"])
    if "glob" in spec:
        if not os.path.isdir(src):
            return None
        import fnmatch
        names = sorted(n for n in os.listdir(src)
                       if fnmatch.fnmatch(n, spec["glob"])
                       and not n.startswith("test_") and n != "conftest.py"
                       and os.path.isfile(os.path.join(src, n)))
        return [(os.path.join(src, n), os.path.join(dst, n), n) for n in names], dst
    if not os.path.isfile(src):
        return None
    return [(src, dst, os.path.basename(dst))], os.path.dirname(dst)


def _same(a, b):
    with io.open(a, "rb") as fa, io.open(b, "rb") as fb:
        return fa.read() == fb.read()


def _diff(project_file, shipped_file, rel):
    import difflib
    with io.open(project_file, encoding="utf-8", errors="replace") as f:
        ours = f.readlines()
    with io.open(shipped_file, encoding="utf-8", errors="replace") as f:
        theirs = f.readlines()
    lines = list(difflib.unified_diff(ours, theirs, fromfile=f"{rel} (this repo)",
                                      tofile=f"{rel} (shipped)", n=2))
    out = ["      " + l.rstrip("\n") for l in lines[:DIFF_MAX_LINES]]
    if len(lines) > DIFF_MAX_LINES:
        out.append(f"      … {len(lines) - DIFF_MAX_LINES} more diff lines — `diff -u` the two paths for all of it")
    return "\n".join(out)


def _copy(src, dst):
    import shutil
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copyfile(src, dst)


def sync_validators(root, plugin_root, apply=False, overwrite=()):
    """Bring the repo's validator copies up to the shipped ones without clobbering anything the repo
    changed. Prints as it goes and returns what happened. A modified file is never overwritten
    unless its project-relative path is in `overwrite` — the human said yes to THAT file."""
    root = os.path.abspath(root)
    plugin_root = os.path.abspath(plugin_root)
    want = {os.path.normpath(o) for o in overwrite}
    result = {"installed": [], "identical": [], "modified": [], "overwritten": [],
              "opted_out": [], "skipped_sets": []}
    if not os.path.isdir(plugin_root):
        print(f"! plugin root {plugin_root} is not a directory — nothing synced.")
        return result
    if os.path.isfile(os.path.join(root, "ai", "claude", "start-change", "SKILL.md")):
        # The HITL platform repo: these files are the SOURCE here, not copies. Same guard as the
        # retired-tests cleanup in dev-update Step 4.6.
        print("  · this is the HITL platform repo itself — its validators are the source, nothing to sync")
        return result

    for spec in SYNC_SETS:
        got = _pairs(plugin_root, root, spec)
        if got is None:
            result["skipped_sets"].append(spec["src"])
            continue
        pairs, dst_dir = got
        if spec["mode"] == "if-present" and not os.path.isdir(dst_dir):
            result["skipped_sets"].append(f"{spec['src']} (repo does not have {spec['dst']})")
            continue
        optout = _optout(dst_dir)
        for src, dst, name in pairs:
            rel = os.path.relpath(dst, root).replace(os.sep, "/")
            if name in optout or rel in optout:
                result["opted_out"].append(rel)
                continue
            if not os.path.isfile(dst):
                if apply:
                    _copy(src, dst)
                print(f"  + {'installed' if apply else 'would install'} {rel}")
                result["installed"].append(rel)
                continue
            if spec["mode"] == "install-only":
                continue                      # the repo's now; never compared, never reported
            if _same(src, dst):
                result["identical"].append(rel)
                continue
            if os.path.normpath(rel) in want:
                if apply:
                    _copy(src, dst)
                print(f"  ! {'overwrote' if apply else 'would overwrite'} {rel} with the shipped version (named in --overwrite)")
                result["overwritten"].append(rel)
                continue
            result["modified"].append(rel)
            print(f"  ~ {rel} differs from the shipped version — KEPT yours. Diff (this repo → shipped):")
            print(_diff(dst, src, rel))

    n_id = len(result["identical"])
    if result["opted_out"]:
        print(f"  · opted out ({OPTOUT_NAME}): " + " ".join(result["opted_out"]))
    for sset in result["skipped_sets"]:
        print(f"  · skipped, not in this build or not onboarded here: {sset}")
    if not (result["installed"] or result["modified"] or result["overwritten"]):
        print(f"  ✓ validator copies already current ({n_id} file(s) identical)")
    else:
        print(f"  = {n_id} identical, {len(result['installed'])} {'installed' if apply else 'to install'}, "
              f"{len(result['modified'])} modified here and kept, {len(result['overwritten'])} overwritten by name")
    if result["modified"]:
        print("\n  ASK, per file, before doing anything else: overwrite with the shipped version, or keep yours?")
        print("  (Overwriting loses this repo's edits; keeping yours means missing any upstream fix.)")
        print("  Only on an explicit yes for THAT file:")
        me = os.path.abspath(__file__)
        for m in result["modified"]:
            print(f'    python3 "{me}" --root . --sync-validators "{plugin_root}" --apply --overwrite {m}')
    if result["installed"] and not apply:
        print("\n(dry run — re-run with --apply to install)")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    ap.add_argument("--sync-validators", metavar="PLUGIN_ROOT", default=None,
                    help="only sync the copied-in validators from this plugin root (co-owned protocol, #104)")
    ap.add_argument("--overwrite", action="append", default=[], metavar="PATH",
                    help="with --sync-validators: overwrite this one modified file (repeatable)")
    a = ap.parse_args(argv)

    if a.sync_validators is not None:
        sync_validators(a.root, a.sync_validators, apply=a.apply, overwrite=a.overwrite)
        return 0

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
    #
    # Four states, kept apart on purpose (#103). Absent and empty mean there is nothing in flight
    # to audit, so they are clean. Unreadable, or readable but not a mapping, mean the audit could
    # not run — and an audit that did not run must say so and fail, never print the all-clear.
    # The previous version coerced an unreadable file to `{}`, which has no skips and no lightened
    # steps, so `audit_change_file` found nothing and the tool certified a file it never saw. On a
    # python3 without PyYAML (the common Homebrew case) that happened on every dev-update run. Same
    # ruling as check_skips.py (GH-488): an UNREADABLE record must not masquerade as an EMPTY one.
    audit_failed = False
    if os.path.isfile(cpath):
        change = None
        try:
            import yaml
        except ImportError:
            print(f"! could not read {cpath}: this interpreter ({sys.executable}) has no PyYAML.")
            print("  The change-file audit did NOT run — nothing about the active change has been checked.")
            print("  Install it (pip install pyyaml) or run the migrator with the project's venv, then re-run.")
            audit_failed = True
        else:
            try:
                change = yaml.safe_load(io.open(cpath, encoding="utf-8"))
            except Exception as e:
                print(f"! could not read {cpath} ({e})")
                print("  The change-file audit did NOT run — nothing about the active change has been checked.")
                audit_failed = True
        if not audit_failed:
            if change is None:
                print("= active change file is empty — nothing to audit")
            elif not isinstance(change, dict):
                print(f"! {cpath} parses to a {type(change).__name__}, not a mapping — the audit cannot run.")
                print("  Fix the file by hand; a change file is a YAML mapping.")
                audit_failed = True
            else:
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
    # The lightened-step report above stays advisory (exit 0): check_skips.py is the gate that
    # blocks it later. Only an audit that could not run at all fails here.
    return 1 if audit_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
