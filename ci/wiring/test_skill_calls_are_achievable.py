#!/usr/bin/env python3
"""A skill must not tell the model to invoke a command the model cannot invoke (#130).

`dev-start-change` Step 3c said "Call `/hitl:dev-apply-change`" while apply-change's frontmatter
carries `disable-model-invocation: true`. Some runs read the file and ran the analysis inline; some
stopped and handed the command to the person. The instruction was unachievable as written, so the
behaviour depended on the run.

Nearly every HITL skill carries that frontmatter flag (commands are user-initiated by design), so the
achievable forms are: follow the skill's steps from its file, or tell the person what to run. This
test reads every SKILL.md, resolves each `/hitl:<command>` a sentence tells the model to call or run
to its source skill, and fails when that skill forbids model invocation.

Run: python3 -m pytest ci/wiring/test_skill_calls_are_achievable.py -q
"""
import io
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CLAUDE = os.path.join(ROOT, "ai", "claude")

# The plugin build's naming (scripts/build.sh in the plugin repo): a flat skill dir becomes
# `dev-<dir>`, a role dir keeps its role as the prefix, and the two meta skills keep their names.
ROLE_DIRS = ("architect", "pm", "qa", "ops")
FLAT_AS_IS = ("help", "ta-approve")

# A sentence that tells the model to do it. Lines inside code fences, list items, block quotes and
# the closing messages people read are not the model's instructions and are left alone.
CALL = re.compile(r"(?:^|[.:;]\s+)(?:Call|Run|Invoke)\s+`/hitl:([a-z0-9-]+)")
LIST_OR_QUOTE = re.compile(r"^\s*(?:[-*]|\d+\.|>)\s")
QUOTED = re.compile(r'"[^"]*"')


def _skill_files():
    out = []
    for dirpath, _dirs, files in os.walk(CLAUDE):
        if "SKILL.md" in files:
            out.append(os.path.join(dirpath, "SKILL.md"))
    return sorted(out)


def _command_name(path):
    rel = os.path.relpath(os.path.dirname(path), CLAUDE).replace(os.sep, "/")
    parts = rel.split("/")
    if parts[0] in ROLE_DIRS:
        return "%s-%s" % (parts[0], "-".join(parts[1:]))
    if parts[0] == "migrate":
        return "dev-" + "-".join(parts[1:])
    if parts[0] == "skills":
        return "-".join(parts[1:])
    if parts[0] in FLAT_AS_IS:
        return parts[0]
    return "dev-" + parts[0]


def _forbids_model_invocation(path):
    text = io.open(path, encoding="utf-8").read()
    fm = re.match(r"---\n(.*?)\n---", text, re.S)
    return bool(fm and re.search(r"^disable-model-invocation:\s*true\s*$", fm.group(1), re.M))


def _model_addressed_calls(path):
    """(line_no, command) for each sentence in `path` that tells the model to call a command."""
    hits = []
    fenced = False
    for n, line in enumerate(io.open(path, encoding="utf-8").read().splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or LIST_OR_QUOTE.match(line):
            continue
        # Text inside double quotes is what the model says to the person ("stop: ... Run X first.").
        for m in CALL.finditer(QUOTED.sub('""', line)):
            hits.append((n, m.group(1)))
    return hits


GUARDED = {_command_name(p): p for p in _skill_files() if _forbids_model_invocation(p)}


def test_the_guard_map_names_apply_change():
    """The resolver must agree with the build's naming, or the test checks nothing."""
    assert "dev-apply-change" in GUARDED
    assert "qa-report-defect" in GUARDED
    assert GUARDED["dev-apply-change"].endswith(os.path.join("apply-change", "SKILL.md"))


@pytest.mark.parametrize("path", _skill_files(), ids=lambda p: os.path.relpath(p, CLAUDE))
def test_no_skill_tells_the_model_to_invoke_a_guarded_command(path):
    bad = [(n, cmd) for n, cmd in _model_addressed_calls(path) if cmd in GUARDED]
    assert not bad, (
        "%s tells the model to call a command it cannot invoke (disable-model-invocation): %s. "
        "Say to follow the skill's steps from its file, or tell the person what to run."
        % (os.path.relpath(path, ROOT), ", ".join("line %d: /hitl:%s" % b for b in bad)))


def test_start_change_runs_the_impact_analysis_inline():
    """#130: Step 3c names the file to follow and never tells the model to call the command."""
    text = io.open(os.path.join(CLAUDE, "start-change", "SKILL.md"), encoding="utf-8").read()
    step = text.split("## Step 3c")[1].split("## Step 4")[0]
    assert "skills/dev-apply-change/SKILL.md" in step
    assert "Do not invoke the command" in step
    assert "Call `/hitl:dev-apply-change`" not in step
