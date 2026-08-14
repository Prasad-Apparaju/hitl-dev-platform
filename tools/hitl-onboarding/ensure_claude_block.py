#!/usr/bin/env python3
"""Ensure a project's CLAUDE.md carries the managed HITL section.

CLAUDE.md is the only thing that can tell a developer this project uses HITL when they have NOT
installed the plugin: no hook runs, no skill exists, nothing else in the repo speaks. Onboarding
used to skip CLAUDE.md whenever one already existed -- which is every real project -- so nothing
ever said so.

Never overwrites the team's file. Maintains exactly one marker-delimited block.

    ensure_claude_block.py <claude-md-path> <block-template-path>

Exit codes:
    0  created / appended / refreshed / already current
    3  BEGIN marker with no END -- file deliberately left untouched
    1  usage or I/O error
"""
import io
import os
import re
import sys

BEGIN = "<!-- HITL:BEGIN"
END = "<!-- HITL:END -->"
# Non-greedy so two blocks (shouldn't happen, but a hand-edited file can) collapse one at a time
# rather than swallowing everything between the first BEGIN and the last END.
_SPAN = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


def apply(current, block):
    """Return (new_text, action). Pure -- no I/O, so the cases are directly testable.

    action is one of: created, appended, refreshed, current, unterminated
    """
    block = block.rstrip("\n")
    if current is None:
        return block + "\n", "created"
    if BEGIN in current:
        if END not in current:
            # Truncated block. Replacing to end-of-file would eat the team's real content.
            return current, "unterminated"
        new = _SPAN.sub(lambda _: block, current, count=1)
        return (new, "current") if new == current else (new, "refreshed")
    sep = "" if current.endswith("\n\n") else ("\n" if current.endswith("\n") else "\n\n")
    return current + sep + block + "\n", "appended"


MESSAGES = {
    "created": "  CLAUDE.md created with the HITL section",
    "appended": "  CLAUDE.md - HITL section added (existing content untouched)",
    "refreshed": "  CLAUDE.md HITL section refreshed",
    "current": "  CLAUDE.md HITL section already current",
    "unterminated": "  WARNING: HITL:BEGIN with no HITL:END - left CLAUDE.md untouched",
}


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 1
    dest, block_path = argv[1], argv[2]
    try:
        block = io.open(block_path, encoding="utf-8").read()
    except OSError as exc:
        sys.stderr.write("  WARNING: block template unreadable (%s) - skipping\n" % exc)
        return 1
    current = None
    if os.path.isfile(dest):
        try:
            current = io.open(dest, encoding="utf-8").read()
        except OSError as exc:
            sys.stderr.write("  WARNING: could not read %s (%s)\n" % (dest, exc))
            return 1

    new, action = apply(current, block)
    if action == "unterminated":
        sys.stderr.write(MESSAGES[action] + "\n")
        return 3
    if action != "current":
        try:
            io.open(dest, "w", encoding="utf-8").write(new)
        except OSError as exc:
            sys.stderr.write("  WARNING: could not write %s (%s)\n" % (dest, exc))
            return 1
    print(MESSAGES[action])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
