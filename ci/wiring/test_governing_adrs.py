"""Accepted ADRs that govern all code reach every review that checks code (#159).

Six slices once passed every review with none of an accepted observability ADR built: intake never
listed it, and the reviews only read the LLD. These tests run the snippets the skills ship, against
fixtures, so a broken escape or a renamed field fails here rather than in a product repo.

Run: python3 -m pytest ci/wiring/test_governing_adrs.py -q
"""
import io
import os
import re
import shutil
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SKILLS = os.path.join(ROOT, "ai", "claude")
TEMPLATES = os.path.join(ROOT, "ai", "shared", "templates")
ADRS = os.path.join("docs", "02-design", "technical", "adrs")


def _read(*parts):
    return io.open(os.path.join(*parts), encoding="utf-8").read()


def _fence_after(text, marker):
    m = re.search(re.escape(marker) + r".*?```bash\n(.*?)```", text, re.S)
    assert m, "no bash fence after %r" % marker
    return m.group(1)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(text)


@pytest.fixture
def repo(tmp_path):
    adrs = tmp_path / ADRS
    obs = _read(TEMPLATES, "adr-0005-observability-strategy.md")
    _write(str(adrs / "ADR-0005-observability-strategy.md"),
           re.sub(r"(\| \*\*Status\*\* \|)[^|\n]*", r"\1 Accepted ", obs, count=1))
    shutil.copy(os.path.join(TEMPLATES, "adr-0007-security-baseline.md"), str(adrs / "ADR-0007-security-baseline.md"))
    _write(str(adrs / "ADR-0009-observability.md"), "# ADR-0009: Observability Strategy\n\n| **Status** | Accepted |\n")
    _write(str(adrs / "ADR-0010-postgres.md"), "# ADR-0010: Use Postgres\n\n| **Status** | Accepted |\n")
    _write(str(adrs / "ADR-0011-errors.md"), "# ADR-0011: Error envelope\n\nStatus: Accepted\n\n| **Applies to** | all-code |\n")
    _write(str(tmp_path / "docs" / "04-operations" / "platform-readiness.yaml"),
           _read(TEMPLATES, "platform-readiness-template.yaml"))
    return tmp_path


def _discover(cwd):
    snippet = _fence_after(_read(SKILLS, "apply-change", "SKILL.md"), "Which accepted")
    r = subprocess.run(["bash", "-c", snippet], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return yaml.safe_load(r.stdout)


def test_templates_declare_they_govern_all_code():
    for name in ("adr-0005-observability-strategy.md", "adr-0007-security-baseline.md"):
        assert re.search(r"\| \*\*Applies to\*\* \| all-code", _read(TEMPLATES, name)), name
    assert "### Required log fields" in _read(TEMPLATES, "adr-0005-observability-strategy.md")


def test_intake_lists_accepted_governing_adrs_and_red_gaps(repo):
    out = _discover(repo)
    names = sorted(os.path.basename(p) for p in out["governing_adrs"])
    # accepted template, an older baseline ADR matched by title, a custom all-code ADR; not ADR-0010
    assert names == ["ADR-0005-observability-strategy.md", "ADR-0009-observability.md", "ADR-0011-errors.md"]
    # the template's own "## 7. Status / Draft" section must not override an Accepted header row
    assert [os.path.basename(p) for p in out["draft_governing_adrs"]] == ["ADR-0007-security-baseline.md"]
    gaps = [k for g in out["readiness_red_gaps"] for k in g]   # "- F1: name" parses as {F1: name}
    assert "F1" in gaps and "P1" not in gaps and "F2" not in gaps   # P1 is na, F2 is yellow


def test_intake_on_a_repo_with_no_adrs_says_none(tmp_path):
    out = _discover(tmp_path)
    assert out == {"governing_adrs": None, "draft_governing_adrs": None, "readiness_red_gaps": None}


def test_the_change_file_carries_the_governing_adrs(tmp_path):
    shutil.copytree(os.path.join(ROOT, "ci", "first-pass"), str(tmp_path / "ci" / "first-pass"))
    os.makedirs(str(tmp_path / "ai" / "shared"))
    shutil.copy(os.path.join(ROOT, "ai", "shared", "workflows.yaml"), str(tmp_path / "ai" / "shared"))
    gen = os.path.join("ci", "first-pass", "gen_change.py")
    env = dict(os.environ, HITL_TIER_PROPOSED="2")

    def run(record):
        stub = subprocess.run([sys.executable, gen, "--stub", "GH-7", "issue/7-x", "2.18.0"],
                              cwd=str(tmp_path), capture_output=True, text=True, check=True).stdout
        _write(str(tmp_path / ".hitl" / "current-change.yaml"), stub)
        _write(str(tmp_path / ".hitl" / "impact" / "GH-7.yaml"), record)
        r = subprocess.run([sys.executable, gen, "development", "GH-7", "issue/7-x", "2.18.0", "2", "none", "", ""],
                           cwd=str(tmp_path), capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        return yaml.safe_load(r.stdout)

    rec = "change_id: GH-7\ngoverning_adrs:\n  - id: ADR-0005\n    path: docs/a/ADR-0005.md\n    touched: true\n"
    assert run(rec)["source_artifacts"] == {"governing_adrs": ["docs/a/ADR-0005.md"]}
    assert run("change_id: GH-7\ngoverning_adrs: []\n")["source_artifacts"] == {"governing_adrs": []}
    assert "source_artifacts" not in run("change_id: GH-7\n")  # a record from before the field


def test_added_log_calls_are_listed_with_their_lines(tmp_path):
    snippet = _fence_after(_read(SKILLS, "check-conventions", "SKILL.md"), "List every log call the change adds")
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(tmp_path), check=True)
    _write(str(tmp_path / "a.py"), "import logging\n")
    subprocess.run(git + ["add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(git + ["commit", "-qm", "i"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "f"], cwd=str(tmp_path), check=True)
    _write(str(tmp_path / "a.py"), "import logging\nlog = logging.getLogger()\n"
           "def f(t):\n    log.info('routed %s', t)\n    catalog.info_page()\n    console.log('x')\n")
    subprocess.run(git + ["commit", "-qam", "f"], cwd=str(tmp_path), check=True)
    r = subprocess.run(["bash", "-c", snippet], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert [l.split(": ")[0] for l in r.stdout.splitlines()] == ["a.py:4", "a.py:6"]


@pytest.mark.parametrize("skill", ["review-lld-adherence", "architect/review-code", "check-conventions",
                                   "ops/setup-observability", "qa/plan-tests"])
def test_every_code_check_reads_the_governing_adrs(skill):
    assert "governing_adrs" in _read(SKILLS, skill, "SKILL.md"), skill
