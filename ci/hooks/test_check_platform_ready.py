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


# Canonical-complete register (schema 1.0 requires all D/E/F items present; the gate
# blocks truncated registers). Exactly ONE gap (E3) — several tests string-replace on the
# single "status: gap" occurrence and the chip test asserts "1 gap".
REGISTER_WITH_GAP = """\
    schema_version: "1.0"
    project_kind: brownfield
    layers:
      verification:
        items:
          - id: D1
            name: "Tier test suites exist"
            status: verified
            evidence: "pytest suite in CI, run 812"
          - id: D2
            name: "E2E against staging"
            status: verified
            evidence: "playwright nightly, run 44"
          - id: D3
            name: "Traceability matrix"
            status: verified
            evidence: "matrix seeded 2026-07-11"
      delivery:
        items:
          - id: E1
            name: "Reproducible build"
            status: verified
            evidence: "clean-checkout build, run 812"
          - id: E2
            name: "Deploy playbook"
            status: verified
            evidence: "playbook v3 reviewed"
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
          - id: F2
            name: "Canary exercised"
            status: verified
            evidence: "canary run 2026-07-10"
          - id: F3
            name: "Security posture"
            status: verified
            evidence: "secret scan + dep audit in CI"
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
        # Verified WITH evidence; delivery_ready still false but nothing blocks.
        write_register(project, REGISTER_WITH_GAP.replace(
            "            status: gap\n            severity: red\n",
            '            status: verified\n            severity: red\n'
            '            evidence: "CI run 812, staging deploy job green, 2026-07-11"\n'))
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


class TestItemSchemaValidation:
    """Codex round-2 blocker 1: unknown/malformed item statuses must block, not pass."""

    def _with_status(self, status_line):
        return REGISTER_WITH_GAP.replace("status: gap", status_line)

    def test_unknown_status_blocks(self, project):
        write_register(project, self._with_status("status: blocked"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "invalid status" in err

    def test_typo_status_blocks(self, project):
        write_register(project, self._with_status("status: gaps"))
        assert run_gate(project, "production", 2)[0] == 2

    def test_null_status_blocks(self, project):
        write_register(project, self._with_status("status:"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "invalid status" in err

    def test_verified_without_evidence_blocks(self, project):
        # An unverifiable "verified" claim never releases production.
        write_register(project, REGISTER_WITH_GAP.replace("status: gap", "status: verified"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "verified without evidence" in err

    def test_non_mapping_item_blocks(self, project):
        write_register(
            project,
            'schema_version: "1.0"\nlayers:\n  delivery:\n    items:\n      - "just a string"\n'
            'delivery_ready: false\nwaivers: []\n')
        assert run_gate(project, "production", 2)[0] == 2


class TestWaiverSchemaValidation:
    """Codex round-2 blocker 2: a waiver missing owner/revisit/reason must not release."""

    def _register_with_waiver_lines(self, waiver_lines):
        block = "    waivers:\n      - item: E3\n" + "".join(
            f"        {line}\n" for line in waiver_lines)
        return REGISTER_WITH_GAP.replace("    waivers: []\n", block)

    FULL = ['tier_limit: 3', 'owner: "TA"', 'revisit: "2099-01-01"', 'reason: "pilot"']

    def _run_without(self, project, drop=None, replace=None):
        lines = [l for l in self.FULL if not (drop and l.startswith(drop))]
        if replace:
            lines = [replace.get(l.split(":")[0], l) if l.split(":")[0] in replace else l
                     for l in lines]
        write_register(project, self._register_with_waiver_lines(lines))
        return run_gate(project, "production", 2)

    def test_complete_waiver_passes(self, project):
        code, _ = self._run_without(project)
        assert code == 0

    def test_missing_revisit_blocks(self, project):
        code, err = self._run_without(project, drop="revisit")
        assert code == 2
        assert "no revisit" in err

    def test_empty_revisit_blocks(self, project):
        code, _ = self._run_without(project, replace={"revisit": 'revisit: ""'})
        assert code == 2

    def test_invalid_revisit_blocks(self, project):
        code, err = self._run_without(project, replace={"revisit": 'revisit: "not-a-date"'})
        assert code == 2
        assert "not a valid" in err

    def test_unquoted_date_revisit_passes(self, project):
        # YAML parses an unquoted date to datetime.date; the gate must accept it.
        code, _ = self._run_without(project, replace={"revisit": "revisit: 2099-01-01"})
        assert code == 0

    def test_missing_owner_blocks(self, project):
        code, err = self._run_without(project, drop="owner")
        assert code == 2
        assert "no owner" in err

    def test_empty_owner_blocks(self, project):
        code, _ = self._run_without(project, replace={"owner": 'owner: ""'})
        assert code == 2

    def test_missing_reason_blocks(self, project):
        code, err = self._run_without(project, drop="reason")
        assert code == 2
        assert "no reason" in err

    def test_boolean_tier_limit_blocks(self, project):
        code, err = self._run_without(project, replace={"tier_limit": "tier_limit: true"})
        assert code == 2
        assert "not an integer" in err


WAIVER_E3 = ('waivers:\n  - item: E3\n    tier_limit: 3\n    owner: "TA"\n'
             '    revisit: "2099-01-01"\n    reason: "pilot"\n')


class TestItemIdentity:
    """Codex round-3 blockers 1-2: ids are the waiver join key — required and unique."""

    def test_duplicate_ids_block_even_with_waiver(self, project):
        write_register(project, (
            'schema_version: "1.0"\nproject_kind: brownfield\nlayers:\n  delivery:\n    items:\n'
            '      - id: E3\n        name: "one"\n        status: gap\n'
            '      - id: E3\n        name: "another"\n        status: gap\n'
            'delivery_ready: false\n' + WAIVER_E3))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "duplicate item id" in err

    def test_missing_id_blocks_and_is_not_waivable(self, project):
        write_register(project, (
            'schema_version: "1.0"\nproject_kind: brownfield\nlayers:\n  delivery:\n    items:\n'
            '      - name: "missing id gap"\n        status: gap\n'
            'delivery_ready: false\n'
            'waivers:\n  - item: "?"\n    tier_limit: 3\n    owner: "TA"\n'
            '    revisit: "2099-01-01"\n    reason: "pilot"\n'))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "item has no id" in err

    def test_empty_id_blocks(self, project):
        write_register(project, (
            'schema_version: "1.0"\nproject_kind: brownfield\nlayers:\n  delivery:\n    items:\n'
            '      - id: ""\n        name: "empty id"\n        status: gap\n'
            'delivery_ready: false\nwaivers: []\n'))
        assert run_gate(project, "production", 2)[0] == 2


class TestProjectKind:
    """Codex round-3 blocker 3 (+ the adjacent gap): project_kind is load-bearing."""

    @staticmethod
    def _core_layers_yaml():
        """All 9 canonical D/E/F items verified with evidence, template layer names."""
        layers = {"verification": ("D1", "D2", "D3"), "delivery": ("E1", "E2", "E3"),
                  "operation": ("F1", "F2", "F3")}
        out = []
        for layer, ids in layers.items():
            out.append(f"  {layer}:\n    items:\n")
            for iid in ids:
                out.append(f'      - id: {iid}\n        name: "{iid} item"\n'
                           f'        status: verified\n        evidence: "proof {iid}"\n')
        return "".join(out)

    def migration_register(self, parity_status, extra=""):
        mig = []
        for layer, ids in (("parity", ("P1", "P2")), ("cutover", ("C1", "C2", "C3"))):
            mig.append(f"  {layer}:\n    items:\n")
            for iid in ids:
                mig.append(f'      - id: {iid}\n        name: "{iid} item"\n'
                           f"        status: {parity_status}\n{extra}"
                           if parity_status != "verified" else
                           f'      - id: {iid}\n        name: "{iid} item"\n'
                           f'        status: verified\n        evidence: "proof {iid}"\n')
        return ('schema_version: "1.0"\nproject_kind: migration\nlayers:\n'
                + self._core_layers_yaml() + "".join(mig)
                + 'delivery_ready: false\nwaivers: []\n')

    def test_migration_parity_na_blocks(self, project):
        write_register(project, self.migration_register("na"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "na is not allowed on a migration register" in err

    def test_migration_with_real_statuses_passes(self, project):
        write_register(project, self.migration_register("verified"))
        assert run_gate(project, "production", 2)[0] == 0

    def test_non_migration_parity_na_passes(self, project):
        reg = self.migration_register("na").replace(
            "project_kind: migration", "project_kind: brownfield")
        write_register(project, reg)
        assert run_gate(project, "production", 2)[0] == 0

    def test_missing_project_kind_blocks(self, project):
        write_register(project, (
            'schema_version: "1.0"\nlayers:\n  delivery:\n    items:\n'
            '      - id: E1\n        name: "build"\n        status: verified\n'
            '        evidence: "build pass"\n'
            'delivery_ready: false\nwaivers: []\n'))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "project_kind" in err

    def test_unknown_project_kind_blocks(self, project):
        write_register(project, (
            'schema_version: "1.0"\nproject_kind: weird\nlayers:\n  delivery:\n    items:\n'
            '      - id: E1\n        name: "build"\n        status: verified\n'
            '        evidence: "build pass"\n'
            'delivery_ready: false\nwaivers: []\n'))
        assert run_gate(project, "production", 2)[0] == 2


class TestCanonicalCompleteness:
    """Codex round-4 blockers: truncated registers and na on canonical D/E/F items."""

    def test_truncated_register_blocks(self, project):
        # One verified item is not a readiness register (round-4 repro 1).
        write_register(project, (
            'schema_version: "1.0"\nproject_kind: brownfield\nlayers:\n'
            '  delivery:\n    items:\n'
            '      - id: E1\n        name: "build"\n        status: verified\n'
            '        evidence: "build pass"\n'
            'delivery_ready: false\nwaivers: []\n'))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "canonical item(s)" in err and "D1" in err and "F3" in err

    def test_unknown_layer_only_blocks(self, project):
        # Wrong layer keys mean the canonical set is missing (round-4 repro 3).
        write_register(project, (
            'schema_version: "1.0"\nproject_kind: brownfield\nlayers:\n'
            '  something_else:\n    items:\n'
            '      - id: X1\n        name: "custom"\n        status: verified\n'
            '        evidence: "ok"\n'
            'delivery_ready: false\nwaivers: []\n'))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "canonical item(s)" in err

    def test_core_item_na_blocks(self, project):
        # Round-4 repro 2: D/E/F may never be na — waivers are the escape hatch.
        write_register(project, REGISTER_WITH_GAP.replace(
            "            status: gap\n            severity: red\n",
            "            status: na\n            severity: red\n"))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "na is not allowed for a canonical readiness item" in err

    def test_custom_extra_item_na_passes(self, project):
        # Teams may ADD items; a custom item may be na when the canonical set is green.
        reg = REGISTER_WITH_GAP.replace(
            "            status: gap\n            severity: red\n",
            '            status: verified\n            evidence: "ci deploy job green"\n'
        ).replace(
            "    delivery_ready: false\n",
            '      custom:\n        items:\n          - id: X9\n'
            '            name: "optional extra"\n            status: na\n'
            "    delivery_ready: false\n")
        write_register(project, reg)
        assert run_gate(project, "production", 2)[0] == 0

    def test_missing_schema_version_blocks(self, project):
        write_register(project, REGISTER_WITH_GAP.replace('    schema_version: "1.0"\n', ""))
        code, err = run_gate(project, "production", 2)
        assert code == 2
        assert "schema_version" in err

    def test_unknown_schema_version_blocks(self, project):
        write_register(project, REGISTER_WITH_GAP.replace(
            'schema_version: "1.0"', 'schema_version: "9.9"'))
        assert run_gate(project, "production", 2)[0] == 2


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
