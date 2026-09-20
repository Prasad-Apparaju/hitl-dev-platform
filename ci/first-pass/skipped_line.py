#!/usr/bin/env python3
"""One line at the top of the change's issue listing the steps the plan left out.

A deferred step used to seed a follow-up ticket each (CR-7 as first shipped). On a Fast Track
change that meant two or three new issues per run, opened at plan confirm behind a line that never
said an issue would be opened. Users noticed the issues before they noticed the question.

The skip ledger is the record. This is the notice: one line, regenerated from the ledger, kept
between markers at the top of the issue body so it stays visible while the thread grows. A skip
someone actually wants scheduled gets a ticket by explicit choice, never by default.

Usage:
  skipped_line.py --change .hitl/current-change.yaml            # print the line
  skipped_line.py --change .hitl/current-change.yaml --apply    # write it to the issue via gh

The issue number comes from `--issue N` or from `change_id` (`GH-123` -> 123). `--apply` is
idempotent: an unchanged body is not rewritten. Voice is neutral, and user-supplied reasons pass
through the same blame filter the resurfacing reminders use.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from resurface import _clean  # CR-9: never blame, even when the recorded reason does
except Exception:  # pragma: no cover - resurface ships beside this file
    def _clean(text):
        return str(text)

OPEN = "<!-- hitl:skipped -->"
CLOSE = "<!-- /hitl:skipped -->"
_BLOCK = re.compile(re.escape(OPEN) + r".*?" + re.escape(CLOSE) + r"\n*", re.S)
REASON_MAX = 60

_WORD = {"defer": "deferred", "decline": "declined", "starter": "thin version now"}


def _label(change, key):
    steps = ((change.get("workflow") or {}).get("steps") or []) if isinstance(change, dict) else []
    for s in steps:
        if isinstance(s, dict) and s.get("key") == key and s.get("label"):
            return str(s["label"])
    return str(key)


def _reason(text):
    t = " ".join(str(text or "").split())
    t = _clean(t)
    if len(t) > REASON_MAX:
        t = t[:REASON_MAX - 1].rstrip() + "…"
    return t


def issue_number(change, explicit=None):
    """`--issue` wins; else the digits of change_id (GH-123 -> 123); else None."""
    if explicit:
        m = re.search(r"\d+", str(explicit))
        return int(m.group()) if m else None
    cid = str((change or {}).get("change_id") or "")
    m = re.search(r"(\d+)\s*$", cid)
    return int(m.group(1)) if m else None


def render_line(change):
    """The one line, or '' when nothing was skipped (the block is then removed, not written)."""
    skips = [s for s in ((change or {}).get("skips") or []) if isinstance(s, dict) and s.get("step")]
    if not skips:
        return ""
    parts, actors = [], []
    for s in skips:
        disp = str(s.get("disposition") or "skipped")
        word = _WORD.get(disp, disp)
        item = f"{_label(change, s['step'])} ({word}"
        r = _reason(s.get("reason"))
        if r and disp != "starter":
            item += f": {r}"
        if s.get("resolved") is True:
            item += ", since done"
        ref = str(s.get("followup_ref") or "")
        if ref and not ref.lower().startswith("issue:"):
            item += f", ticket {ref}"
        parts.append(item + ")")
        a = _clean(str(s.get("actor") or "")).strip()
        if a and a not in actors:
            actors.append(a)
    who = f", chosen by {', '.join(actors)}" if actors else ""
    return f"**Skipped:** {'; '.join(parts)}{who} at plan confirm. Record: `.hitl/current-change.yaml`."


def splice(body, line):
    """Return the body with the block replaced (or removed when line is empty), block first."""
    body = body or ""
    rest = _BLOCK.sub("", body, count=1).lstrip("\n")
    if not line:
        return rest
    return f"{OPEN}\n{line}\n{CLOSE}\n\n{rest}"


def _gh(args, run):
    p = run(["gh"] + args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "gh failed").strip())
    return p.stdout


def apply(change, issue, run=subprocess.run):
    """Write the line to the issue body. Returns 'written', 'unchanged' or 'removed'."""
    line = render_line(change)
    body = _gh(["issue", "view", str(issue), "--json", "body", "-q", ".body"], run)
    new = splice(body, line)
    if new == body:
        return "unchanged"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(new)
        path = fh.name
    try:
        _gh(["issue", "edit", str(issue), "--body-file", path], run)
    finally:
        os.unlink(path)
    return "written" if line else "removed"


def main(argv=None, run=subprocess.run):
    import argparse
    import yaml
    ap = argparse.ArgumentParser(description="One line on the issue listing the steps the plan left out.")
    ap.add_argument("--change", default=".hitl/current-change.yaml")
    ap.add_argument("--issue", default=None, help="issue number; default from change_id")
    ap.add_argument("--apply", action="store_true", help="write to the issue via gh (idempotent)")
    a = ap.parse_args(argv)
    try:
        change = yaml.safe_load(open(a.change)) or {}
    except Exception as e:
        print(f"skipped_line: cannot read {a.change}: {e}", file=sys.stderr)
        return 2
    if not isinstance(change, dict):
        print(f"skipped_line: {a.change} is not a mapping", file=sys.stderr)
        return 2
    line = render_line(change)
    if not a.apply:
        print(line or "(nothing skipped)")
        return 0
    n = issue_number(change, a.issue)
    if n is None:
        print("skipped_line: no issue number (pass --issue N or set change_id like GH-123)", file=sys.stderr)
        return 2
    try:
        result = apply(change, n, run)
    except (RuntimeError, OSError) as e:
        print(f"skipped_line: issue #{n} not updated: {e}", file=sys.stderr)
        return 3
    print(f"issue #{n}: skipped line {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
