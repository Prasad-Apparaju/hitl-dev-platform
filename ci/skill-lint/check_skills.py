#!/usr/bin/env python3
"""Skill-file linter for the HITL dev platform.

Validates every SKILL.md against Anthropic's Agent Skills best practices, as
captured in docs/design/workflow-model/04-harness-acceptance-criteria.md (Part A).

Two severities:
  - FAIL (hard gate, exit 1): deterministic, false-positive-free checks. The
    frontmatter schema (Part A section 1) and the measurable body limits.
  - WARN (exit 0): judgment checks that cannot be reliably static-linted
    (third person, what+when, forward slashes, reference-link depth, vague
    names). These are surfaced, not gated, so the gate never blocks on a guess.

Run:  python3 ci/skill-lint/check_skills.py [--root ai/claude] [--strict]
  --strict promotes warnings to failures (exit 1 on any warning).

Exit code: 0 = no failures (warnings allowed), 1 = at least one hard-gate failure
(or any warning under --strict).

Dependencies: Python 3.10+. PyYAML optional (a minimal frontmatter parser is
used when PyYAML is absent), so this runs in a bare CI environment.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # graceful degradation: fall back to the minimal parser below
    yaml = None


# ---------------------------------------------------------------------------
# Limits and patterns (Part A sections 1-2)
# ---------------------------------------------------------------------------

NAME_MAX = 64
DESC_MAX = 1024
BODY_MAX_LINES = 500
REF_TOC_MIN_LINES = 100

NAME_RE = re.compile(r"^[a-z0-9-]+$")
XML_TAG_RE = re.compile(r"<[a-zA-Z/][^>]*>")
RESERVED = ("anthropic", "claude")
VAGUE_NAMES = {"helper", "utils", "tools", "documents", "data", "files"}
# First/second-person openers that signal a non-third-person description.
NON_THIRD_PERSON = re.compile(
    r"\b(I can|I'll|I will|I help|you can|you should|you will|we can|we'll)\b",
    re.IGNORECASE,
)
# Local markdown links: [text](path.md) where path is not a URL or anchor.
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
# A Windows drive-letter path (C:\...). Deliberately narrow: `\n`/`\t` escape
# sequences in shell strings look identical to single-backslash file paths, so we
# only flag the unambiguous drive-letter form to stay false-positive-free.
BACKSLASH_PATH_RE = re.compile(r"\b[A-Za-z]:\\")


@dataclass
class Finding:
    path: str
    line: int
    severity: str  # "FAIL" or "WARN"
    criterion: str
    detail: str


@dataclass
class Report:
    files: int = 0
    name_fallback: int = 0  # plugin skills relying on directory-name fallback
    findings: list[Finding] = field(default_factory=list)

    def add(self, *a) -> None:
        self.findings.append(Finding(*a))

    @property
    def fails(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "FAIL"]

    @property
    def warns(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "WARN"]


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[dict | None, str, int]:
    """Return (frontmatter_dict_or_None, body, body_start_line).

    A None dict means the frontmatter fences or YAML are malformed.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            raw = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1:])
            return _parse_yaml(raw), body, i + 2
    return None, text, 1  # no closing fence


def _parse_yaml(raw: str) -> dict | None:
    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return None
    # Minimal `key: value` parser for the two fields we care about.
    out: dict = {}
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_file(path: Path, root: Path, rep: Report, require_name: bool = False) -> None:
    rel = str(path.relative_to(root.parent if root.name else root))
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body, body_start = split_frontmatter(text)

    # --- Frontmatter structure (section 1, hard) ---
    if fm is None:
        rep.add(rel, 1, "FAIL", "frontmatter",
                "missing or malformed `---` fenced YAML frontmatter")
        return
    name = fm.get("name")
    desc = fm.get("description")
    # `name` is OPTIONAL for Claude Code plugin skills in a skills/<dir>/ layout:
    # Claude Code falls back to the (stable) directory basename. So a missing name
    # is a WARN (add it for explicitness), not a hard gate. Adding it blindly risks
    # basename collisions (e.g. pm/design-feature vs architect/design-feature), so it
    # is a deliberate per-skill choice, not a sweep. For Agent Skills (SDK/API), name
    # IS required; run with --skills-require-name to make it a hard gate there.
    if not name:
        if require_name:
            rep.add(rel, 1, "FAIL", "name",
                    "no `name` (required under --skills-require-name)")
        else:
            # Legitimate for plugin skills (directory-name fallback); count, don't spam.
            rep.name_fallback += 1
    if not desc:
        rep.add(rel, 1, "FAIL", "description", "missing or empty `description`")

    # --- name rules (section 1, hard) ---
    if name:
        if len(name) > NAME_MAX:
            rep.add(rel, 2, "FAIL", "name", f"{len(name)} chars > {NAME_MAX} max")
        if not NAME_RE.match(name):
            rep.add(rel, 2, "FAIL", "name", f"'{name}' not ^[a-z0-9-]+$")
        if XML_TAG_RE.search(name):
            rep.add(rel, 2, "FAIL", "name", "contains an XML tag")
        low = name.lower()
        for word in RESERVED:
            if word in low:
                rep.add(rel, 2, "FAIL", "name", f"contains reserved substring '{word}'")
        if name.lower() in VAGUE_NAMES:
            rep.add(rel, 2, "WARN", "naming", f"vague name '{name}'")

    # --- description rules (section 1) ---
    if desc:
        if len(desc) > DESC_MAX:
            rep.add(rel, 3, "FAIL", "description", f"{len(desc)} chars > {DESC_MAX} max")
        if XML_TAG_RE.search(desc):
            rep.add(rel, 3, "FAIL", "description", "contains an XML tag")
        if NON_THIRD_PERSON.search(desc):
            rep.add(rel, 3, "WARN", "description",
                    "looks first/second person (should be third person)")
        if not re.search(r"\b(when|use|for|after|before|if)\b", desc, re.IGNORECASE):
            rep.add(rel, 3, "WARN", "description",
                    "may not say *when* to use the skill (no when/use/for cue)")

    # --- body structure (section 2) ---
    body_lines = body.splitlines()
    if len(body_lines) > BODY_MAX_LINES:
        rep.add(rel, body_start, "FAIL", "body",
                f"{len(body_lines)} body lines > {BODY_MAX_LINES} max")
    for off, line in enumerate(body_lines):
        if BACKSLASH_PATH_RE.search(line):
            rep.add(rel, body_start + off, "WARN", "paths",
                    "backslash in a path-like token (use forward slashes)")
            break

    # --- reference-link depth + TOC (section 2) ---
    _check_references(path, rel, body, body_start, rep)


def _check_references(path: Path, rel: str, body: str, body_start: int, rep: Report) -> None:
    for m in MD_LINK_RE.finditer(body):
        target = m.group(1).split("#")[0].strip()
        if not target.endswith(".md"):
            continue
        ref = (path.parent / target).resolve()
        if not ref.is_file():
            continue
        ref_text = ref.read_text(encoding="utf-8", errors="replace")
        ref_lines = ref_text.splitlines()
        # depth: a reference file that itself links onward to another local .md
        for m2 in MD_LINK_RE.finditer(ref_text):
            t2 = m2.group(1).split("#")[0].strip()
            if t2.endswith(".md") and (ref.parent / t2).resolve().is_file():
                rep.add(rel, body_start, "WARN", "ref-depth",
                        f"{target} links onward to {t2} (keep refs one level deep)")
                break
        # TOC on large reference files
        if len(ref_lines) > REF_TOC_MIN_LINES:
            head = "\n".join(ref_lines[:15]).lower()
            if "## " not in head and "table of contents" not in head and "- [" not in head:
                rep.add(rel, body_start, "WARN", "ref-toc",
                        f"{target} is {len(ref_lines)} lines with no table of contents")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(root: Path, require_name: bool = False) -> Report:
    rep = Report()
    for skill in sorted(root.rglob("SKILL.md")):
        rep.files += 1
        check_file(skill, root, rep, require_name)
    return rep


def render(rep: Report) -> str:
    lines = []
    ok = rep.files - len({f.path for f in rep.fails})
    lines.append(f"Skill lint: {ok}/{rep.files} files pass all hard gates; "
                 f"{len(rep.fails)} failures, {len(rep.warns)} warnings.")
    if rep.name_fallback:
        lines.append(f"  note: {rep.name_fallback} skills use directory-name fallback "
                     f"(no explicit `name`); valid for plugin skills.")
    lines.append("")
    for sev in ("FAIL", "WARN"):
        group = [f for f in rep.findings if f.severity == sev]
        if not group:
            continue
        lines.append(f"--- {sev} ({len(group)}) ---")
        for f in sorted(group, key=lambda x: (x.criterion, x.path)):
            lines.append(f"  [{f.criterion}] {f.path}:{f.line} — {f.detail}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lint SKILL.md files against Part A criteria.")
    p.add_argument("--root", default="ai/claude", help="directory to scan (default ai/claude)")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p.add_argument("--skills-require-name", action="store_true",
                   help="make a missing `name` a hard failure (Agent Skills SDK/API rule; "
                        "off by default since Claude Code plugin skills derive name from the dir)")
    args = p.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: root '{root}' is not a directory", file=sys.stderr)
        return 2
    rep = run(root, require_name=args.skills_require_name)
    print(render(rep))
    if rep.fails:
        return 1
    if args.strict and rep.warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
