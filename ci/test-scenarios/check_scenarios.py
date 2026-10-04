#!/usr/bin/env python3
"""Readable test scenarios validator (FR-36). Design: docs/design/readable-test-scenarios/03-lld.md,
sections 1, 2 and 4.

Reads the change record (.hitl/current-change.yaml), the change's scenarios file
(docs/03-engineering/testing/scenarios/<change-id>.md) and the change's tests, and checks both
directions: every live scenario is cited by a test or carries a complete deferral, and every
acceptance or integration test unit in the change's test set cites a scenario.

A finding is {code, message, waivable, locus}. Exit 2 when any non-waivable finding exists, 1 with
--strict when any waivable one does, else 0. Anything it cannot parse is MALFORMED, never a traceback.
Python 3.10, PyYAML only.

Usage:
    python3 ci/test-scenarios/check_scenarios.py [--change .hitl/current-change.yaml]
            [--file <scenarios.md>] [--stage draft|review|verify] [--tests <dir>]... [--strict] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 50 * 1024 * 1024
MAX_WORDS = 1000
MAX_SENTENCES = 5
EM_DASH = chr(0x2014)
DEFAULT_CHANGE = os.path.join(".hitl", "current-change.yaml")
DEFAULT_ROOTS = ("tests", "test", "spec", "__tests__")
STAGES = ("draft", "review", "verify")
# At stage draft (right after someone adds a scenario, before RED) SCENARIO_UNCITED, TEST_UNCITED
# and REVIEW_PENDING warn instead of blocking; structure still blocks. See the per-stage branches below.

KINDS = {"acceptance", "integration", "regression"}
PRIORITIES = {"regression-required", "strongly-recommended", "optional"}
ROLES = {"qa", "pm", "dev"}
REVIEW_STATUSES = {"pending", "done", "skipped"}
REVIEW_DONE_KEYS = ("by", "ts")
REVIEW_SKIPPED_KEYS = ("actor", "pm", "reason", "disposition", "ts")
REQUIRED_FIELDS = ("Kind", "Priority", "Serves", "Added by", "Given", "When", "Then", "Test")

# Codes that never block. REVIEW_PENDING is decided per stage when it is raised.
WAIVABLE = {"CONTEXT_LONG", "TESTS_UNSCOPED", "REVIEW_HEADER_STALE", "LENGTH", "PLAIN"}

CONTEXT_HEADING = "## What this change does"
RE_SCENARIO_HEADING = re.compile(r"^###\s+(SC-(.+?)-(\d{2,}))\s*:\s*(.+?)\s*$")
RE_FIELD = re.compile(r"^-\s+([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$")
RE_ADDED_BY = re.compile(r"^(qa|pm|dev)(\s*\(.+\))?$")
RE_DEFER = re.compile(r"^(deferred|declined)\b(.*)$")
RE_DEFER_BODY = re.compile(r'^\s*\(\s*([^,"()]+?)\s*,\s*"([^"]+)"\s*\)\s*$')
RE_REVIEW_ROW = re.compile(r"^\|\s*Review\s*\|\s*(.*?)\s*\|\s*$")
RE_SENTENCE_END = re.compile(r"[.?!](?=\s|$)")
RE_ANY_ID = re.compile(r"(?<![A-Za-z0-9])SC[-_][A-Za-z0-9_-]+?[-_]\d{2,}(?![A-Za-z0-9])", re.I)
RE_UNIT = {
    "py": re.compile(r"^\s*(async\s+)?def\s+test_"),
    "js": re.compile(r"^\s*(test|it)(\.(skip|only|fixme|todo|each|concurrent|serial|fails|slow))*\s*\("),
    "go": re.compile(r"^func\s+Test"),
    "jvm": re.compile(r"^\s*@Test\b"),
}
LANG_BY_EXT = {
    ".py": "py", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".cjs": "js",
    ".go": "go", ".java": "jvm", ".kt": "jvm",
}
INTEGRATION_DIRS = ("/e2e/", "/integration/", "/acceptance/", "/smoke/")
INTEGRATION_MARKS = ("pytest.mark.integration", "describe('integration'", 'describe("integration')


class Malformed(Exception):
    pass


def _f(code, message, locus="", waivable=None):
    if waivable is None:
        waivable = code in WAIVABLE
    return {"code": code, "message": message, "waivable": waivable, "locus": locus}


# ---------------------------------------------------------------------------
# Loading: duplicate keys, size, symlinks and wrong shapes are MALFORMED
# ---------------------------------------------------------------------------

class _StrictLoader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        try:
            if key in seen:
                raise Malformed("duplicate key %r" % (key,))
        except TypeError:
            raise Malformed("unhashable key")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def _inside(root, path):
    r = os.path.realpath(root)
    p = os.path.realpath(path)
    return p == r or p.startswith(r + os.sep)


def _read_text(path, root, what):
    """Read one file fail-closed: it must be a regular file inside the repo, small enough, UTF-8."""
    if not _inside(root, path):
        raise Malformed("%s resolves outside the repository: %s" % (what, path))
    if not os.path.isfile(path):
        raise Malformed("%s is not a file: %s" % (what, path))
    if os.path.getsize(path) > MAX_BYTES:
        raise Malformed("%s is larger than %d bytes" % (what, MAX_BYTES))
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Malformed("%s cannot be read as UTF-8: %s" % (what, e.__class__.__name__))


def load_record(path, root):
    text = _read_text(path, root, "change record")
    try:
        data = yaml.load(text, Loader=_StrictLoader)
    except Malformed:
        raise
    except yaml.YAMLError as e:
        raise Malformed("change record YAML error: %s" % str(e).splitlines()[0])
    if not isinstance(data, dict):
        raise Malformed("change record top level is not a mapping")
    return data


def change_id_of(record):
    """The change id as the repo writes it (GH-123) or bare (123). `change_id` is the schema key;
    `id` is accepted as well."""
    for key in ("change_id", "id"):
        v = record.get(key)
        if isinstance(v, (int, str)) and not isinstance(v, bool) and str(v).strip():
            return str(v).strip()
    raise Malformed("change record has no change_id")


def id_matches(change_part, change_id):
    """SC-<change_part>-nn belongs to this change. A bare record id (123) accepts GH-123 or 123;
    a prefixed one (GH-123) must match exactly, case insensitive."""
    a, b = change_part.lower(), change_id.lower()
    if a == b:
        return True
    if re.fullmatch(r"\d+", b):
        return re.fullmatch(r"[a-z][a-z0-9]*-" + re.escape(b), a) is not None
    return False


# ---------------------------------------------------------------------------
# The scenarios file
# ---------------------------------------------------------------------------

def parse_scenarios(text, path):
    """Split the file into context sentences, header review status, word count and scenarios.
    Each scenario: {id, change, num, title, fields, line, removed}. Structural defects become
    MALFORMED findings; the parse itself never raises on text."""
    findings = []
    scenarios = []
    lines = text.split("\n")
    context_lines = None
    context = []
    header_review = None
    words = 0
    current = None
    for i, raw in enumerate(lines, 1):
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("|"):
            m = RE_REVIEW_ROW.match(stripped)
            if m and header_review is None:
                header_review = m.group(1)
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            current = None
            context_lines = [] if stripped == CONTEXT_HEADING else None
            if stripped == CONTEXT_HEADING:
                context = context_lines
            continue
        if stripped.startswith("### "):
            context_lines = None
            m = RE_SCENARIO_HEADING.match(stripped)
            if not m:
                findings.append(_f("MALFORMED", "scenario heading is not '### SC-<change-id>-<nn>: <title>'",
                                   "%s:%d" % (path, i)))
                current = None
                continue
            current = {"id": m.group(1), "change": m.group(2), "num": int(m.group(3)), "title": m.group(4),
                       "fields": {}, "line": i, "removed": m.group(4).strip().lower() == "removed"}
            scenarios.append(current)
            continue
        if not stripped.startswith("#"):
            words += len(stripped.split())
        if context_lines is not None:
            context_lines.append(stripped)
            continue
        if current is not None and stripped:
            m = RE_FIELD.match(stripped)
            if m:
                current["fields"].setdefault(m.group(1), m.group(2))
    sentences = len(RE_SENTENCE_END.findall(" ".join(x for x in context if x))) if context else 0
    if context and not sentences and any(context):
        sentences = 1
    return {"findings": findings, "scenarios": scenarios, "context": context, "sentences": sentences,
            "header_review": header_review, "words": words, "has_context": context is not None}


def classify_test(field):
    """A Test field's disposition: ('deferred'|'declined', complete) or ('other', True)."""
    m = RE_DEFER.match(field.strip())
    if not m:
        return "other", True
    body = RE_DEFER_BODY.match(m.group(2))
    return m.group(1), body is not None


def check_scenario(sc, path, change_id):
    findings = []
    locus = "%s:%d" % (path, sc["line"])
    if not id_matches(sc["change"], change_id):
        findings.append(_f("ID_PREFIX", "%s belongs to change %s, this change is %s"
                           % (sc["id"], sc["change"], change_id), locus))
    f = sc["fields"]
    if sc["removed"]:
        rb = f.get("Removed by", "")
        if len([p for p in rb.split(",") if p.strip()]) < 3:
            findings.append(_f("MALFORMED", "%s is removed but has no '- Removed by: <who>, <date>, <why>' line"
                               % sc["id"], locus))
        return findings
    missing = [k for k in REQUIRED_FIELDS if not f.get(k, "").strip()]
    if missing:
        findings.append(_f("MALFORMED", "%s is missing %s" % (sc["id"], ", ".join(missing)), locus))
    if f.get("Kind") and f["Kind"] not in KINDS:
        findings.append(_f("MALFORMED", "%s Kind '%s' is not one of %s"
                           % (sc["id"], f["Kind"], ", ".join(sorted(KINDS))), locus))
    if f.get("Priority") and f["Priority"] not in PRIORITIES:
        findings.append(_f("MALFORMED", "%s Priority '%s' is not one of %s"
                           % (sc["id"], f["Priority"], ", ".join(sorted(PRIORITIES))), locus))
    if f.get("Added by") and not RE_ADDED_BY.match(f["Added by"]):
        findings.append(_f("MALFORMED", "%s 'Added by' must be qa, pm or dev, optionally with a name in parentheses"
                           % sc["id"], locus))
    kind, complete = classify_test(f.get("Test", ""))
    if kind != "other" and not complete:
        findings.append(_f("DEFERRAL_INCOMPLETE", "%s Test is %s without both an owner and a quoted reason"
                           % (sc["id"], kind), locus))
    return findings


def check_ids(scenarios, path):
    findings = []
    seen = {}
    for sc in scenarios:
        if sc["id"].upper() in seen:
            findings.append(_f("ID_DUPLICATE", "%s already used at line %d" % (sc["id"], seen[sc["id"].upper()]),
                               "%s:%d" % (path, sc["line"])))
        else:
            seen[sc["id"].upper()] = sc["line"]
    nums = sorted({sc["num"] for sc in scenarios})
    if nums and nums != list(range(1, len(nums) + 1)):
        findings.append(_f("ID_SEQUENCE", "scenario numbers are %s, expected 01..%02d with no gaps"
                           % (", ".join("%02d" % n for n in nums), len(nums)), path))
    return findings


# ---------------------------------------------------------------------------
# Plain English
# ---------------------------------------------------------------------------

def find_plain_english():
    root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    for cand in (os.path.join(HERE, "plain-english.md"),
                 os.path.join(root, "shared", "plain-english.md") if root else None,
                 os.path.join(HERE, "..", "..", "ai", "shared", "plain-english.md")):
        if cand and os.path.isfile(cand):
            return cand
    return None


def banned_phrases(path):
    """Quoted phrases from the first column of the 'Do not write' table. Pattern rows that use X
    and Y placeholders are skipped; a trailing ellipsis is dropped."""
    phrases = []
    if not path:
        return phrases
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return phrases
    for line in text.splitlines():
        if not line.startswith("|") or "|---" in line:
            continue
        first = line.split("|")[1]
        for q in re.findall(r'"([^"]+)"', first):
            q = q.replace("…", "").strip()
            if re.search(r"\b[XY]\b", q) or not q:
                continue
            phrases.append(q.lower())
    return phrases


def check_plain(text, path, phrases):
    findings = []
    for i, line in enumerate(text.split("\n"), 1):
        if EM_DASH in line:
            findings.append(_f("PLAIN", "em dash", "%s:%d" % (path, i)))
        low = line.lower()
        for p in phrases:
            if re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", low):
                findings.append(_f("PLAIN", "'%s' is on the plain-English list" % p, "%s:%d" % (path, i)))
    return findings


# ---------------------------------------------------------------------------
# Tests: units, citations and the change's test set
# ---------------------------------------------------------------------------

def test_units(path, text):
    """[(start_line, unit_text)] for the test units in one file, by its language. Unknown
    languages have no units."""
    lang = LANG_BY_EXT.get(os.path.splitext(path)[1].lower())
    if not lang:
        return []
    rx = RE_UNIT[lang]
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if rx.match(line)]
    units = []
    for n, s in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        units.append((s + 1, "\n".join(lines[s:end])))
    return units


def is_integration(path, text):
    p = "/" + path.replace(os.sep, "/")
    return any(d in p for d in INTEGRATION_DIRS) or any(m in text for m in INTEGRATION_MARKS)


def cites(unit_text, scenario_id):
    rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(scenario_id).replace(r"\-", "[-_]") + r"(?![A-Za-z0-9])", re.I)
    return rx.search(unit_text) is not None


def walk_tests(root, roots):
    out = []
    for r in roots:
        base = os.path.join(root, r)
        if not os.path.isdir(base):
            continue
        for d, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if not x.startswith(".") and x not in ("node_modules", "__pycache__")]
            for name in files:
                if os.path.splitext(name)[1].lower() in LANG_BY_EXT:
                    out.append(os.path.relpath(os.path.join(d, name), root))
    return sorted(set(out))


def _git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git failed")
    return r.stdout


def git_changed_tests(root, roots):
    """Files under the test roots that differ from the merge base with the default branch, plus
    untracked ones. Raises when git or the base branch is unavailable."""
    base = None
    for ref in ("origin/main", "main"):
        try:
            base = _git(root, "merge-base", "HEAD", ref).strip()
            break
        except (RuntimeError, OSError, subprocess.SubprocessError):
            continue
    if not base:
        raise RuntimeError("no merge base with origin/main or main")
    changed = _git(root, "diff", "--name-only", base, "--", *roots).split("\n")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "--", *roots).split("\n")
    return sorted({p for p in changed + untracked if p and os.path.isfile(os.path.join(root, p))})


def read_test(root, rel):
    path = os.path.join(root, rel)
    try:
        if not _inside(root, path) or not os.path.isfile(path) or os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# The review record
# ---------------------------------------------------------------------------

def check_review(review, stage):
    """Returns (status, findings). An absent review block counts as pending."""
    findings = []
    if review is None:
        review = {}
    if not isinstance(review, dict):
        return "pending", [_f("MALFORMED", "tests.scenario_review is not a mapping", "change record")]
    status = review.get("status", "pending")
    if status not in REVIEW_STATUSES:
        return "pending", [_f("MALFORMED", "tests.scenario_review.status '%s' is not pending, done or skipped"
                              % status, "change record")]
    if status == "pending":
        findings.append(_f("REVIEW_PENDING", "the PM review of the scenarios is still pending",
                           "change record", waivable=(stage != "verify")))  # draft and review warn
    need = REVIEW_DONE_KEYS if status == "done" else REVIEW_SKIPPED_KEYS if status == "skipped" else ()
    missing = [k for k in need if review.get(k) in (None, "")]
    if missing:
        findings.append(_f("REVIEW_RECORD_INCOMPLETE", "tests.scenario_review is %s without %s"
                           % (status, ", ".join(missing)), "change record"))
    return status, findings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def analyze(change_path=DEFAULT_CHANGE, file=None, stage="review", tests_roots=None, root=None):
    """(findings, summary). Raises Malformed only through its own guards; run() wraps the rest."""
    root = os.path.abspath(root or os.getcwd())
    roots = tuple(tests_roots) if tests_roots else DEFAULT_ROOTS
    summary = {"scenarios": 0, "cited": 0, "deferred": 0, "review": "unknown"}
    findings = []

    def abs_(p):
        return p if os.path.isabs(p) else os.path.join(root, p)

    try:
        record = load_record(abs_(change_path), root)
        change_id = change_id_of(record)
    except Malformed as e:
        return [_f("MALFORMED", str(e), change_path)], summary

    tests = record.get("tests") if isinstance(record.get("tests"), dict) else {}
    status, review_findings = check_review(tests.get("scenario_review"), stage)
    summary["review"] = status
    findings += review_findings

    rel = file or (tests.get("scenarios_file") if isinstance(tests.get("scenarios_file"), str) else None)
    if not rel:
        if stage in ("review", "verify"):
            findings.append(_f("FILE_MISSING", "the change record names no tests.scenarios_file", change_path))
        return findings, summary
    path = abs_(rel)
    if not os.path.exists(path) and not os.path.islink(path):
        findings.append(_f("FILE_MISSING", "scenarios file does not exist: %s" % rel, rel))
        return findings, summary
    try:
        text = _read_text(path, root, "scenarios file")
    except Malformed as e:
        findings.append(_f("MALFORMED", str(e), rel))
        return findings, summary

    parsed = parse_scenarios(text, rel)
    findings += parsed["findings"]
    if not parsed["has_context"] or not any(parsed["context"]):
        findings.append(_f("CONTEXT_MISSING", "no '%s' section, or it is empty" % CONTEXT_HEADING, rel))
    elif parsed["sentences"] > MAX_SENTENCES:
        findings.append(_f("CONTEXT_LONG", "the context has %d sentences, at most %d"
                           % (parsed["sentences"], MAX_SENTENCES), rel))
    if parsed["words"] > MAX_WORDS:
        findings.append(_f("LENGTH", "%d words outside the header and headings, at most %d"
                           % (parsed["words"], MAX_WORDS), rel))
    findings += check_plain(text, rel, banned_phrases(find_plain_english()))
    findings += check_ids(parsed["scenarios"], rel)
    for sc in parsed["scenarios"]:
        findings += check_scenario(sc, rel, change_id)
    hdr = parsed["header_review"]
    hdr_status = (hdr.split(":", 1)[1] if hdr and ":" in hdr else hdr or "").strip().lower()
    hdr_status = re.split(r"[\s,(]", hdr_status, 1)[0] if hdr_status else hdr_status   # "done, 2026-10-05" is done
    if hdr_status != status:
        findings.append(_f("REVIEW_HEADER_STALE", "the file's Review line says '%s', the record says '%s'"
                           % (hdr or "nothing", status), rel))

    # The change's test set (test-to-scenario direction) and the citation corpus (both directions).
    files = tests.get("files")
    unscoped = False
    if isinstance(files, list) and files:
        test_set = [p for p in files if isinstance(p, str)]
    else:
        try:
            test_set = git_changed_tests(root, roots)
        except (RuntimeError, OSError, subprocess.SubprocessError):
            test_set = []
            unscoped = True
            findings.append(_f("TESTS_UNSCOPED", "no tests.files in the record and git gave no merge base; "
                               "the test-to-scenario direction was not run", change_path))
    corpus = {}
    for rel_t in sorted(set(walk_tests(root, roots)) | set(test_set)):
        t = read_test(root, rel_t)
        if t is not None:
            corpus[rel_t] = t

    # Citation corpus: the text of every test unit; a file in a language without unit detection
    # counts as one unit.
    unit_texts = []
    for rel_t, t in corpus.items():
        if os.path.splitext(rel_t)[1].lower() in LANG_BY_EXT:
            unit_texts += [u for _, u in test_units(rel_t, t)]
        else:
            unit_texts.append(t)

    live = [sc for sc in parsed["scenarios"] if not sc["removed"]]
    summary["scenarios"] = len(live)
    for sc in live:
        kind, _ = classify_test(sc["fields"].get("Test", ""))
        cited = any(cites(u, sc["id"]) for u in unit_texts)
        if cited:
            summary["cited"] += 1
        elif kind != "other":
            summary["deferred"] += 1
        else:
            findings.append(_f("SCENARIO_UNCITED", "%s is cited by no test and its Test field is '%s'"
                               % (sc["id"], sc["fields"].get("Test", "")), "%s:%d" % (rel, sc["line"]),
                               waivable=(stage == "draft")))
    if not unscoped:
        for rel_t in test_set:
            t = corpus.get(rel_t)
            if t is None or not is_integration(rel_t, t):
                continue
            for line, unit in test_units(rel_t, t):
                if not RE_ANY_ID.search(unit):
                    findings.append(_f("TEST_UNCITED", "acceptance or integration test cites no scenario id",
                                       "%s:%d" % (rel_t, line), waivable=(stage == "draft")))
    return findings, summary


def safe_analyze(*args, **kwargs):
    """analyze() that never raises: any residual exception is a MALFORMED blocker."""
    try:
        return analyze(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        return ([_f("MALFORMED", "validation crashed on malformed input: %s: %s" % (e.__class__.__name__, e))],
                {"scenarios": 0, "cited": 0, "deferred": 0, "review": "unknown"})


def run(change_path=DEFAULT_CHANGE, file=None, stage="review", tests_roots=None, root=None):
    """The finding list. Never raises."""
    return safe_analyze(change_path, file, stage, tests_roots, root)[0]


def exit_code(findings, strict=False):
    if any(not f["waivable"] for f in findings):
        return 2
    if strict and findings:
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Readable test scenarios validator (FR-36, fail-closed)")
    ap.add_argument("--change", default=DEFAULT_CHANGE, help="path to the change record")
    ap.add_argument("--file", default=None, help="scenarios file; overrides tests.scenarios_file")
    ap.add_argument("--stage", choices=STAGES, default="review")
    ap.add_argument("--tests", action="append", default=None, metavar="DIR", help="test root (repeatable)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings")
    ap.add_argument("--json", action="store_true", help="print the finding list as JSON")
    a = ap.parse_args(argv)
    findings, s = safe_analyze(a.change, a.file, a.stage, a.tests)
    if a.json:
        print(json.dumps(findings, indent=2, default=str))
    else:
        for f in findings:
            tag = "BLOCK" if not f["waivable"] else "warn"
            where = " (%s)" % f["locus"] if f.get("locus") else ""
            print("[%s] %s: %s%s" % (tag, f["code"], f["message"], where))
        print("Scenarios: %d scenarios, %d cited, %d deferred, review %s."
              % (s["scenarios"], s["cited"], s["deferred"], s["review"]))
    return exit_code(findings, a.strict)


if __name__ == "__main__":
    sys.exit(main())
