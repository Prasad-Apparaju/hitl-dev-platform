"""Breadcrumb renderer regression tests for the 1.1.0/2.1.0 workflow additions.

The welcome banner and statusline read the self-describing workflow block in
.hitl/current-change.yaml. These cases pin that the renderers handle:
  - the prd workflow's new step 5 (platform_roadmap), seeded without per-step phase
    fields (the 1.x seeding style) and with them (the 2.x style)
  - a platform workflow block, including the additive `cond: migration` field the
    flow-map parser had never seen before 1.1.0

On main these overlap the breadcrumb matrix; on release/1.x (which has no matrix)
they are the only automated renderer coverage — keep the file identical on both lines.
"""

import os
import subprocess
import textwrap
import pytest

HOOKS = os.path.join(os.path.dirname(__file__), "..", "..", "ai", "claude", "hooks")
STATUSLINE = os.path.abspath(os.path.join(HOOKS, "statusline-hitl.sh"))
WELCOME = os.path.abspath(os.path.join(HOOKS, "welcome.sh"))

PRD_AT_STEP5 = """\
    schema_version: "2.0"
    change_id: prd-setup
    tier: 3
    status: planning
    workflow:
      id: prd
      total: 5
      steps:
        - { n: 1, key: claude_md,        label: "CLAUDE.md", status: done }
        - { n: 2, key: manifest,         label: "Manifest",  status: done }
        - { n: 3, key: create_issue,     label: "Issue",     status: done }
        - { n: 4, key: confirm_ready,    label: "Ready",     status: done }
        - { n: 5, key: platform_roadmap, label: "Platform",  status: current }
    current_step:
      number: 5
      name: "Generate platform roadmap"
      phase: "PRD Setup"
"""

PLATFORM_WITH_COND = """\
    schema_version: "2.0"
    change_id: platform-setup
    tier: 2
    status: planning
    workflow:
      id: platform
      total: 17
      steps:
        - { n: 1,  key: derive_register, label: "Register", phase: "Survey", status: done }
        - { n: 2,  key: roadmap,         label: "Roadmap",  phase: "Survey", status: done }
        - { n: 3,  key: test_suites,     label: "Suites",   phase: "Verify", status: current }
        - { n: 4,  key: e2e_env,         label: "E2E",      phase: "Verify", status: open }
        - { n: 12, key: golden_dataset,  label: "Golden",   phase: "Parity", cond: migration, status: open }
        - { n: 17, key: delivery_ready,  label: "Ready",    phase: "Ready",  status: open }
    current_step:
      number: 3
      name: "Tier Test Suites Stand"
      phase: "Verify"
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".hitl").mkdir()
    return tmp_path


def write_change(project_dir, body):
    (project_dir / ".hitl" / "current-change.yaml").write_text(textwrap.dedent(body))


def run_statusline(project_dir):
    payload = ('{"cwd":"%s","model":{"display_name":"Opus"},'
               '"context_window":{"used_percentage":42}}' % project_dir)
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    r = subprocess.run(["bash", STATUSLINE], input=payload, capture_output=True,
                       text=True, cwd=project_dir, env=env)
    return r.stdout + r.stderr


def run_welcome(project_dir):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    r = subprocess.run(["bash", WELCOME], input="", capture_output=True,
                       text=True, cwd=project_dir, env=env)
    return r.stdout + r.stderr


# The two lines render differently (1.x: "Step 5/5" counter + numbered labels;
# 2.x: numberless phase ribbon + name-expanded trail). Assert only the invariants
# both share: the current step's full name renders, neighboring steps render, and
# no failure marker appears.
FAILURE_MARKERS = ("unavailable", "Step ?", "dev-update")


def assert_healthy(out):
    for m in FAILURE_MARKERS:
        assert m not in out, f"renderer failure marker {m!r} in output: {out[-200:]}"


class TestPrdStepFive:
    def test_statusline_renders_new_step(self, project):
        write_change(project, PRD_AT_STEP5)
        out = run_statusline(project)
        assert "Generate platform roadmap" in out
        assert "Ready" in out          # neighboring done step renders
        assert_healthy(out)

    def test_welcome_renders_new_step(self, project):
        write_change(project, PRD_AT_STEP5)
        out = run_welcome(project)
        assert "Generate platform roadmap" in out
        assert "prd-setup" in out
        assert_healthy(out)


class TestPlatformBlockWithCond:
    """The additive `cond:` field must not break the flow-map step parser."""

    def test_statusline_tolerates_cond_field(self, project):
        write_change(project, PLATFORM_WITH_COND)
        out = run_statusline(project)
        assert "Tier Test Suites Stand" in out or "Suites" in out
        assert "Golden" in out         # the cond-marked step still renders
        assert_healthy(out)

    def test_welcome_tolerates_cond_field(self, project):
        write_change(project, PLATFORM_WITH_COND)
        out = run_welcome(project)
        assert "platform-setup" in out
        assert "Golden" in out
        assert_healthy(out)
