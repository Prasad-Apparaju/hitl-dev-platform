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

DEFAULT_BEGIN = "<!-- HITL:BEGIN"
DEFAULT_END = "<!-- HITL:END -->"


def _span(begin, end):
    """A block that cannot cross a second BEGIN.

    A plain non-greedy `BEGIN.*?END` is NOT enough: with an orphaned BEGIN above a complete block,
    it matches from the orphan to the later END and eats everything in between — which on a real
    CLAUDE.md meant deleting the team's own rules while reporting that nothing was touched. The
    tempered repetition below refuses to pass a second BEGIN.

    Anchored to start-of-line, for the reason the sibling preferences block was broken by: prose
    that *describes* a marker is inline, a real marker begins its own line. Counting or matching
    unanchored lets documentation impersonate a block, and the writer then edits the sentence
    describing it.
    """
    return re.compile(r"^" + re.escape(begin) + r"(?:(?!^" + re.escape(begin) + r").)*?^" +
                      re.escape(end), re.S | re.M)


def apply(current, block, begin=DEFAULT_BEGIN, end=DEFAULT_END):
    """Return (new_text, action). Pure -- no I/O, so the cases are directly testable.

    action is one of: created, appended, refreshed, current, unterminated, malformed
    """
    block = block.rstrip("\n")
    if current is None:
        return block + "\n", "created"
    if re.search(r"^" + re.escape(begin), current, re.M):
        n_begin = len(re.findall(r"^" + re.escape(begin), current, re.M))
        n_end = len(re.findall(r"^" + re.escape(end), current, re.M))
        if n_end == 0:
            # Truncated block. Replacing to end-of-file would eat the team's real content.
            return current, "unterminated"
        if n_begin != 1 or n_end != 1:
            # Duplicated or orphaned markers: the file's structure is not what we wrote, so we
            # cannot know which span is ours. Refusing is the only safe answer — a wrong guess
            # deletes content we do not own.
            return current, "malformed"
        new = _span(begin, end).sub(lambda _: block, current, count=1)
        if new == current and end not in _span(begin, end).findall(current or "") and \
                not _span(begin, end).search(current):
            return current, "malformed"
        return (new, "current") if new == current else (new, "refreshed")
    sep = "" if current.endswith("\n\n") else ("\n" if current.endswith("\n") else "\n\n")
    return current + sep + block + "\n", "appended"


MESSAGES = {
    "malformed": ("  WARNING: CLAUDE.md has duplicated or orphaned HITL markers - refusing to "
                  "touch it. Fix them by hand; nothing was written."),
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
    if action in ("unterminated", "malformed"):
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
