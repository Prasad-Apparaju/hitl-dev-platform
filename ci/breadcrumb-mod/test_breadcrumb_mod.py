#!/usr/bin/env python3
"""The breadcrumb band mod is draw-only, and provably so (FR-37, BM-4 and BM-7).

Assembles the plugin once, then asks the Claude Code CLI itself: `claude plugin validate --json`
must list exactly the two hooks and four calls the requirement allows, and `claude plugin test`
must pass. Two cheap guards sit beside that: hooks.json names one module, and the module source
never reaches for any other part of the mods API. Skips when `claude` is not on PATH."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOKS = os.path.join(ROOT, "ai", "claude", "hooks")
MODULE = "./breadcrumb-band.js"

ALLOWED_HOOKS = {"ui.render{component=AbovePrompt}", "turn.complete"}
ALLOWED_CALLS = {"$.fs.exists", "$.fs.read", "$.ui.resolve", "$.ui.invalidate"}
FORBIDDEN_NAMESPACES = ("process.", "http.", "model.", "store.", "clock.", "command.", "tool.",
                        "prompt.", "session.")

CLAUDE = shutil.which("claude")
pytestmark = pytest.mark.skipif(
    CLAUDE is None,
    reason="the `claude` CLI is not installed (not on PATH); `claude plugin validate` and `claude plugin test` "
           "need Claude Code 2.1.287 or later (install it in CI before this job)")

_spec = importlib.util.spec_from_file_location("assemble_plugin", os.path.join(HERE, "assemble_plugin.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


@pytest.fixture(scope="module")
def assembled():
    out = tempfile.mkdtemp(prefix="hitl-breadcrumb-mod-")
    A.assemble(out)
    yield out
    shutil.rmtree(out, ignore_errors=True)


def run(*args, cwd):
    return subprocess.run([CLAUDE, *args], cwd=cwd, capture_output=True, text=True)


def _footprint_from_notes(notes):
    """The validator's notes for our module, as (hooks, calls) sets. Returns None when absent."""
    hooks = calls = None
    for note in notes:
        m = re.match(r"^(\S+) hooks: (.*)$", note)
        if m and m.group(1) == MODULE:
            hooks = {h.strip() for h in m.group(2).split(",") if h.strip()}
        m = re.match(r"^(\S+) calls: (.*)$", note)
        if m and m.group(1) == MODULE:
            calls = {c.strip() for c in _strip_via(m.group(2)).split(",") if c.strip()}
    if hooks is None or calls is None:
        return None
    return hooks, calls


def _strip_via(calls_line):
    # "$.fs.read (via readCache, readMode)" names the helpers a call sits in; the call is what we
    # police, and the note's own commas must go before the line is split on commas.
    return re.sub(r"\s*\(via [^)]*\)", "", calls_line)


def footprint(report_json, human_output):
    try:
        report = json.loads(report_json)
    except ValueError:
        report = None
    if isinstance(report, dict):
        for entry in report.get("contents", []):
            if entry.get("type") == "hooks":
                found = _footprint_from_notes(entry.get("notes", []))
                if found is not None:
                    return found
    # Fallback: the human lines look like "  ❯ ./breadcrumb-band.js hooks: ..."
    lines = [re.sub(r"^\s*\S\s+", "", ln) for ln in human_output.splitlines() if MODULE in ln]
    found = _footprint_from_notes(lines)
    assert found is not None, "could not find the module's hooks/calls in validator output:\n" + human_output
    return found


def test_validate_passes_with_exactly_the_allowed_footprint(assembled):
    res = run("plugin", "validate", "--json", assembled, cwd=assembled)
    assert res.returncode == 0, res.stdout + res.stderr
    human = run("plugin", "validate", assembled, cwd=assembled)
    assert human.returncode == 0, human.stdout + human.stderr
    hooks, calls = footprint(res.stdout, human.stdout + human.stderr)
    assert hooks == ALLOWED_HOOKS, "hooks drifted: %s" % sorted(hooks)
    assert calls == ALLOWED_CALLS, "calls drifted: %s" % sorted(calls)


def test_plugin_tests_pass(assembled):
    res = run("plugin", "test", assembled, cwd=assembled)
    assert res.returncode == 0, res.stdout + res.stderr
    assert " 0 fail" in res.stdout + res.stderr, res.stdout + res.stderr
    assert "(pass)" in res.stdout + res.stderr, res.stdout + res.stderr


def test_hooks_json_names_one_module():
    with open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8") as f:
        hooks = json.load(f)
    assert hooks.get("modules") == [MODULE], hooks


def test_module_source_touches_no_other_namespace():
    with open(os.path.join(HOOKS, MODULE[2:]), encoding="utf-8") as f:
        src = f.read()
    hits = sorted({ns for ns in FORBIDDEN_NAMESPACES if "$." + ns in src})
    assert not hits, "module reaches into forbidden namespaces: %s" % hits
    # Every `$.<ns>.<method>` call in the source is one of the four allowed ones.
    used = set(re.findall(r"\$\.[a-z]+\.[a-zA-Z]+", src))
    assert used == ALLOWED_CALLS, "source calls drifted: %s" % sorted(used)
