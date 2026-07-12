"""Regression tests for check-platform-ready.sh (the platform-bootstrap deploy gate).

Design: docs/design/platform-bootstrap/01-design.md §5, decision D2 (hard block + waivers).
Rules pinned here:
  - only production targets are gated; staging/canary always pass
  - no register file -> pass (no retro-blocking of pre-register projects)
  - delivery_ready: true -> pass
  - open gap without adequate, unlapsed waiver -> exit 2 for Tier 2+
  - Tier 0/1 changes are never gated; unknown tier is treated as Tier 2

Also covers the statusline platform chip (shown only while not delivery-ready).
"""

import os
import stat
import subprocess
import sys
import textwrap
import pytest

HOOKS = os.path.join(os.path.dirname(__file__), "..", "..", "ai", "claude", "hooks")
GATE = os.path.abspath(os.path.join(HOOKS, "check-platform-ready.sh"))
STATUSLINE = os.path.abspath(os.path.join(HOOKS, "statusline-hitl.sh"))


def run_gate(project_dir, environment, tier=None, env_extra=None):
    # Pin HITL_PY to the test interpreter (which has PyYAML) so results do not depend on
    # whatever bare python3 happens to be first on PATH (2026-07-11 Codex blocker 1).
    env = os.environ.copy()
    env["HITL_PY"] = sys.executable
    if env_extra:
        env.update(env_extra)
    cmd = ["bash", GATE, environment] + ([str(tier)] if tier is not None else [])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir, env=env)
    return result.returncode, result.stderr


def write_register(project_dir, body):
    reg_dir = project_dir / "docs" / "04-operations"
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "platform-readiness.yaml").write_text(textwrap.dedent(body))


REGISTER_WITH_GAP = """\
    schema_version: "1.0"
    project_kind: brownfield
    layers:
      delivery:
        items:
          - id: E3
            name: "Deploy to staging executes from CI"
            status: gap
            severity: red
      operation:
        items:
          - id: F1
            name: "Observability established"
            status: verified
            evidence: "grafana dashboard 'main', pager rotation, 2026-07-11"
    delivery_ready: false
    waivers: []
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".hitl").mkdir()
    return tmp_path


class TestEnvironmentScope:
    def test_staging_never_gated(self, project):
        write_register(project, REGISTER_WITH_GAP)
        assert run_gate(project, "staging", 3)[0] == 0

    def test_canary_never_gated(self, project):
        write_register(project, REGISTER_WITH_GAP)
        assert run_gate(project, "canary", 3)[0] == 0

    def test_production_gated(self, project):
        write_register(project, REGISTER_WITH_GAP)
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "E3" in err and "no waiver" in err

    def test_production_case_insensitive(self, project):
        write_register(project, REGISTER_WITH_GAP)
        assert run_gate(project, "Production", 2)[0] == 2

    def test_production_trailing_whitespace_still_gated(self, project):
        # Codex major 5: 'Production ' must not slip past the gate.
        write_register(project, REGISTER_WITH_GAP)
        assert run_gate(project, "Production ", 2)[0] == 2
        assert run_gate(project, " prod\t", 2)[0] == 2


class TestRegisterStates:
    def test_no_register_passes(self, project):
        assert run_gate(project, "production", 3)[0] == 0

    def test_delivery_ready_passes(self, project):
        write_register(project, REGISTER_WITH_GAP.replace(
            "delivery_ready: false", "delivery_ready: true"))
        assert run_gate(project, "production", 3)[0] == 0

    def test_verified_items_do_not_block(self, project):
        write_register(project, REGISTER_WITH_GAP.replace("status: gap", "status: verified"))
        # No open gaps left; delivery_ready is still false but nothing blocks.
        assert run_gate(project, "production", 2)[0] == 0

    def test_unparseable_register_blocks(self, project):
        write_register(project, "layers: [broken\ndelivery_ready: false\n")
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "not parseable" in err

    def test_unparseable_register_with_ready_line_still_blocks(self, project):
        # Codex major 6: malformed YAML containing 'delivery_ready: true' must fail
        # CLOSED — the old grep fallback trusted the line and failed open.
        write_register(project, "layers: [broken\ndelivery_ready: true\n")
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "not parseable" in err

    def test_non_mapping_register_blocks(self, project):
        write_register(project, "- just\n- a\n- list\n")
        assert run_gate(project, "production", 2)[0] == 2

    def test_empty_layers_blocks(self, project):
        # Codex blocker 4: a structurally empty register (no items, not ready) has
        # nothing to trust — it must block, not pass for lack of blockers.
        write_register(project, 'schema_version: "1.0"\nlayers: {}\ndelivery_ready: false\nwaivers: []\n')
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "no items" in err

    def test_missing_layers_blocks(self, project):
        write_register(project, 'schema_version: "1.0"\ndelivery_ready: false\n')
        assert run_gate(project, "production", 2)[0] == 2

    def test_gate_blocks_the_actual_shipped_template(self, project):
        # The template ships with real gap items; blockers must NAME them
        # (Codex blocker 2: the gate previously reported it as unparseable).
        template = os.path.join(HOOKS, "..", "..", "shared", "templates",
                                "platform-readiness-template.yaml")
        reg_dir = project / "docs" / "04-operations"
        reg_dir.mkdir(parents=True, exist_ok=True)
        with open(os.path.abspath(template)) as f:
            (reg_dir / "platform-readiness.yaml").write_text(f.read())
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "not parseable" not in err
        for item in ("D1", "E1", "F1"):
            assert item in err


class TestTiers:
    def test_tier1_never_gated(self, project):
        write_register(project, REGISTER_WITH_GAP)
        assert run_gate(project, "production", 1)[0] == 0

    def test_tier_read_from_change_file(self, project):
        write_register(project, REGISTER_WITH_GAP)
        (project / ".hitl" / "current-change.yaml").write_text(
            "change_id: GH-7\ntier: 1\nstatus: implementation-approved\n")
        assert run_gate(project, "production")[0] == 0

    def test_unknown_tier_treated_as_tier2(self, project):
        write_register(project, REGISTER_WITH_GAP)
        assert run_gate(project, "production")[0] == 2


class TestWaivers:
    def _register_with_waiver(self, tier_limit, revisit):
        waiver_block = (
            "    waivers:\n"
            "      - item: E3\n"
            f"        tier_limit: {tier_limit}\n"
            '        owner: "TA"\n'
            f'        revisit: "{revisit}"\n'
            '        reason: "pilot"\n'
        )
        return REGISTER_WITH_GAP.replace("    waivers: []\n", waiver_block)

    def test_adequate_waiver_passes(self, project):
        write_register(project, self._register_with_waiver(3, "2099-01-01"))
        assert run_gate(project, "production", 2)[0] == 0

    def test_waiver_tier_limit_too_low_blocks(self, project):
        write_register(project, self._register_with_waiver(1, "2099-01-01"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "tier_limit" in err

    def test_lapsed_waiver_blocks(self, project):
        write_register(project, self._register_with_waiver(3, "2020-01-01"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "lapsed" in err


class TestAcceptedGap:
    """Codex blocker 3: accepted_gap must go through the same waiver check as gap."""

    def test_accepted_gap_without_waiver_blocks(self, project):
        write_register(project, REGISTER_WITH_GAP.replace("status: gap", "status: accepted_gap"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "accepted_gap without a waiver" in err

    def test_accepted_gap_with_adequate_waiver_passes(self, project):
        reg = REGISTER_WITH_GAP.replace("status: gap", "status: accepted_gap").replace(
            "    waivers: []\n",
            '    waivers:\n      - item: E3\n        tier_limit: 3\n'
            '        owner: "TA"\n        revisit: "2099-01-01"\n        reason: "pilot"\n')
        write_register(project, reg)
        assert run_gate(project, "production", 2)[0] == 0

    def test_accepted_gap_with_lapsed_waiver_blocks(self, project):
        reg = REGISTER_WITH_GAP.replace("status: gap", "status: accepted_gap").replace(
            "    waivers: []\n",
            '    waivers:\n      - item: E3\n        tier_limit: 3\n'
            '        owner: "TA"\n        revisit: "2020-01-01"\n        reason: "pilot"\n')
        write_register(project, reg)
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "lapsed" in err


class TestNoCapablePython:
    """Codex blocker 1 (fail-closed half): no PyYAML-capable python must BLOCK, not guess."""

    def test_no_yaml_python_blocks_production(self, project, tmp_path_factory):
        shim_dir = tmp_path_factory.mktemp("shim")
        # A python3 that passes 'import sys' but fails 'import yaml' (bare-machine stand-in).
        shim = shim_dir / "python3"
        shim.write_text(
            "#!/bin/bash\n"
            'if printf "%s" "$*" | grep -q yaml; then exit 1; fi\n'
            f'exec {sys.executable} "$@"\n')
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
        for name in ("python", "py"):
            (shim_dir / name).symlink_to(shim)
        write_register(project, REGISTER_WITH_GAP.replace(
            "delivery_ready: false", "delivery_ready: true"))
        env = os.environ.copy()
        env["PATH"] = f"{shim_dir}:/usr/bin:/bin"
        env.pop("HITL_PY", None)
        result = subprocess.run(["bash", GATE, "production", "2"], capture_output=True,
                                text=True, cwd=project, env=env)
        # Even a delivery_ready register cannot be TRUSTED unverified: fail closed.
        assert result.returncode == 2
        assert "PyYAML" in result.stderr


class TestStatuslineChip:
    def _statusline(self, project_dir):
        payload = ('{"cwd":"%s","model":{"display_name":"Opus"},'
                   '"context_window":{"used_percentage":42}}' % project_dir)
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        result = subprocess.run(["bash", STATUSLINE], input=payload, capture_output=True,
                                text=True, cwd=project_dir, env=env)
        return result.stdout

    def test_chip_shown_while_not_ready(self, project):
        write_register(project, REGISTER_WITH_GAP)
        out = self._statusline(project)
        assert "not delivery-ready" in out
        assert "1 gap" in out

    def test_chip_hidden_when_ready(self, project):
        write_register(project, REGISTER_WITH_GAP.replace(
            "delivery_ready: false", "delivery_ready: true"))
        assert "delivery-ready" not in self._statusline(project)

    def test_chip_hidden_without_register(self, project):
        assert "delivery-ready" not in self._statusline(project)
