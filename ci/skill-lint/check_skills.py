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

def check_file(path: Path, root: Path, rep: Report, require_name: bool = False,
               is_command: bool = False) -> None:
    rel = str(path.relative_to(root.parent if root.name else root))
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body, body_start = split_frontmatter(text)

    # --- Frontmatter structure (section 1, hard) ---
    if fm is None:
        # For a command file every frontmatter field is optional per the Claude Code reference
        # ("All fields are optional. Only `description` is recommended"); with none, Claude falls
        # back to the first paragraph as the description. That is a degradation worth flagging,
        # not a spec violation — so it is a WARN for commands and a hard gate for SKILL.md.
        rep.add(rel, 1, "WARN" if is_command else "FAIL", "frontmatter",
                "missing or malformed `---` fenced YAML frontmatter"
                + (" (command falls back to its first paragraph)" if is_command else ""))
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
        rep.add(rel, 1, "WARN" if is_command else "FAIL", "description",
                "missing or empty `description`")

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


def _iter_unfenced_lines(body: str):
    """Yield (line_no, text) for lines outside fenced code blocks, and report unterminated fences.

    A link inside a fence is usually content the skill *emits* — architect/review-existing writes
    an HLD index template containing `[Deployment View](deployment-view.md)`, correct in the user's
    docs directory and meaningless relative to the skill. Resolving those reports a defect that
    does not exist, and "fixing" it would corrupt the emitted template.

    Fence tracking records the OPENING delimiter length and closes only on a fence at least that
    long, because a naive boolean toggle gets nested fences inside-out: a ```` fence containing an
    odd number of ``` fences flips the state and leaks template content back out as findings — at
    FAIL severity. Returns the open-fence line (or None) so an unterminated fence is an error
    rather than silently blanking the rest of the file.
    """
    lines = body.splitlines()
    kept, fence_len, opened_at = [], 0, None
    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        m = re.match(r"(`{3,}|~{3,})", stripped)
        if m:
            delim = m.group(1)
            if fence_len == 0:
                fence_len, opened_at = len(delim), i
            elif len(delim) >= fence_len and stripped[len(delim):].strip() == "":
                fence_len, opened_at = 0, None
            continue
        if fence_len == 0:
            kept.append((i, line))
    return kept, opened_at


def _clean_target(raw: str) -> str:
    """Normalize a markdown link target: drop anchors, <angle brackets>, and a "title"."""
    t = raw.strip()
    if t.startswith("<") and ">" in t:
        t = t[1:t.index(">")]
    else:
        # `path.md "Some Title"` — the title is not part of the path.
        t = re.split(r'\s+["\'(]', t, maxsplit=1)[0]
    return t.split("#")[0].strip()


def _ship_root(path: Path) -> Path:
    """The directory beyond which a relative link cannot survive packaging.

    The build packages `ai/` (skills, commands, agents, hooks, shared) and nothing else — no
    `docs/`, no `ci/`, no repo root. So the real question for any relative link is "does the
    resolved target stay inside `ai/`", NOT "how many `../` does it contain". Counting substrings
    answers the wrong question in both directions: `foo/../bar.md` climbs nowhere yet counts 1,
    and `a/../../../b.md` climbs two yet counts 3. It also cannot be calibrated for both trees at
    once, because a skill sits one level deep in the built layout and one OR two in source.
    """
    for parent in path.parents:
        if parent.name == "ai":
            return parent
    return path.parent


def _check_references(path: Path, rel: str, body: str, body_start: int, rep: Report) -> None:
    kept, unterminated = _iter_unfenced_lines(body)
    if unterminated is not None:
        rep.add(rel, body_start + unterminated - 1, "FAIL", "fence",
                f"unterminated code fence opened at body line {unterminated} — everything after it "
                "is skipped, which hides real findings")

    ship_root = _ship_root(path)
    seen: set[tuple[str, int]] = set()
    for lineno, line in kept:
        # Inline [text](target) AND reference-style [label]: target — the latter was invisible
        # to the old inline-only pattern, so a 3-level escape written that way was never reported.
        targets = [m.group(1) for m in MD_LINK_RE.finditer(line)]
        ref_def = re.match(r"^\s*\[[^\]]+\]:\s*(\S+)", line)
        if ref_def:
            targets.append(ref_def.group(1))

        for raw in targets:
            target = _clean_target(raw)
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if (target, lineno) in seen:
                continue
            seen.add((target, lineno))

            abs_line = body_start + lineno - 1
            resolved = (path.parent / target).resolve()

            # Escapes the packaged tree -> broken for every installed user, even though it
            # resolves perfectly here in the source repo. This is the class the source tree
            # cannot reveal, and it is what shipped broken in 2.4.6.
            try:
                resolved.relative_to(ship_root.resolve())
            except ValueError:
                rep.add(rel, abs_line, "FAIL", "ref-escapes",
                        f"{target} resolves outside {ship_root.name}/ — the build packages ai/ "
                        "only, so this points at nothing once installed; use a URL or ship the "
                        "target under ai/shared/")
                continue

            # Existence is checked for ANY local target, file or directory. Gating this behind
            # endswith('.md') is half of why the 2.4.6 defect was invisible: it pointed at a
            # directory, so the filter skipped it before any check ran.
            if not resolved.exists():
                rep.add(rel, abs_line, "FAIL", "ref-missing",
                        f"{target} does not resolve from {path.parent.name}/")
                continue

            if not target.endswith(".md") or not resolved.is_file():
                continue
            ref = resolved
            ref_text = ref.read_text(encoding="utf-8", errors="replace")
            ref_lines = ref_text.splitlines()

            # depth: a reference file that itself links onward to another local .md
            for m2 in MD_LINK_RE.finditer(ref_text):
                t2 = _clean_target(m2.group(1))
                if t2.endswith(".md") and (ref.parent / t2).resolve().is_file():
                    rep.add(rel, abs_line, "WARN", "ref-depth",
                            f"{target} links onward to {t2} (keep refs one level deep)")
                    break

            # TOC on large reference files. A heading is NOT a table of contents: the point is
            # that Claude can see the file's full scope from a partial read (`head -100`), which
            # only an actual list of the sections provides. This check used to accept any `## `
            # in the first 15 lines, so a file that merely started with a section passed while
            # giving a previewer nothing. Now it wants a real contents list.
            if len(ref_lines) > REF_TOC_MIN_LINES:
                head = "\n".join(ref_lines[:25]).lower()
                has_toc = ("contents" in head) or head.count("- [") >= 3
                if not has_toc:
                    rep.add(rel, abs_line, "WARN", "ref-toc",
                            f"{target} is {len(ref_lines)} lines with no table of contents")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(root: Path, require_name: bool = False) -> Report:
    rep = Report()
    for skill in sorted(root.rglob("SKILL.md")):
        rep.files += 1
        check_file(skill, root, rep, require_name)

    # Command files are skills too. Claude Code merged custom commands into skills — "a file at
    # .claude/commands/deploy.md and a skill at .claude/skills/deploy/SKILL.md both create /deploy
    # and work the same way" — and the plugin's commands/ files do NOT set
    # disable-model-invocation, which makes them the model-invocable surface: the descriptions
    # Claude actually chooses between. Globbing SKILL.md alone left exactly that surface unlinted
    # (found by an independent audit of 2.4.6).
    for cmd in sorted(root.rglob("commands/**/*.md")):
        if cmd.name == "README.md":
            continue
        # docs/examples/ is a sample PROJECT — a fixture showing what an onboarded repo looks
        # like. Its command files are illustrative content, not HITL's shipped surface, and
        # linting them produces findings nobody should act on.
        if "docs/examples/" in cmd.as_posix():
            continue
        rep.files += 1
        check_file(cmd, root, rep, require_name, is_command=True)
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
