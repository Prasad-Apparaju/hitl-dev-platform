"""Regression tests for scalar reads out of the change file (plugin issues #25, #23 item 3).

`hitl_scalar` returned the whole remainder of the line, comments included. Three of its call
sites are load-bearing COMPARISONS, not display, so the leak changed hook behaviour:

  - `status`          → a change annotated `status: merged  # PR #42` never deactivated
  - `expected_branch` → a correct branch reconciled as `mismatch`, forever
  - `tier`/`change_id`→ the comment rendered verbatim into the status line

Both helpers now share one awk cleaner (`_HITL_AWK_CLEAN`). Order is load-bearing: comment
first, then quotes — stripping quotes first leaves the closing quote stranded once a comment
follows it. A `#` inside a quoted value must survive (YAML: `#` is only a comment when
preceded by whitespace).

Each test writes a change file and invokes the real helper through bash, exactly as the
hooks do.
"""

import os
import subprocess

import pytest

STEPS = os.path.join(
    os.path.dirname(__file__), "..", "..", "ai", "claude", "hooks", "_steps.sh"
)


def call(func, *args):
    """Source _steps.sh and echo the result of one helper call."""
    script = f'source "{os.path.abspath(STEPS)}"; {func} ' + " ".join(f'"{a}"' for a in args)
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def write(tmp_path, body, name="current-change.yaml"):
    f = tmp_path / name
    f.write_text(body)
    return str(f)


# ── the two table tests named in issue #25 ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "status_line",
    [
        "status: merged",
        "status: merged   # PR #42 merged 2026-08-07",
        'status: "merged"   # closed out at the start of the next change',
    ],
)
def test_merged_change_is_inactive_however_annotated(tmp_path, status_line):
    """A merged change must never stay active — annotating why is the natural thing to write."""
    f = write(tmp_path, f"change_id: GH-1\n{status_line}\ncurrent_step:\n  n: 3\n")
    rc, _ = call("hitl_change_active", f)
    assert rc == 1, f"{status_line!r} left the change ACTIVE"


@pytest.mark.parametrize(
    "branch_line",
    [
        "expected_branch: issue/100-x",
        "expected_branch: issue/100-x   # created 2026-08-07",
        'expected_branch: "issue/100-x"',
        'expected_branch: "issue/100-x"   # created 2026-08-07',
    ],
)
def test_expected_branch_reconciles_on_the_correct_branch(tmp_path, branch_line):
    """The quoted+commented form is the one that regressed: the closing quote survived."""
    f = write(
        tmp_path,
        f"change_id: GH-100\nstatus: active\n{branch_line}\ncurrent_step:\n  n: 3\n",
    )
    _, out = call("hitl_branch_reconcile", f, "issue/100-x")
    assert out == "match", f"{branch_line!r} → {out!r}"


def test_expected_branch_still_detects_a_real_mismatch(tmp_path):
    """The fix must not turn the reconciler into a rubber stamp."""
    f = write(
        tmp_path,
        'change_id: GH-100\nstatus: active\nexpected_branch: "issue/100-x"  # note\n'
        "current_step:\n  n: 3\n",
    )
    _, out = call("hitl_branch_reconcile", f, "issue/999-other")
    assert out == "mismatch"


# ── display leak (#23 item 3) ─────────────────────────────────────────────────────────────

def test_tier_comment_does_not_leak_into_the_status_line(tmp_path):
    f = write(
        tmp_path,
        "change_id: GH-1\ntier: 3   # confirmed at step 3 (Impact); do not downgrade\n",
    )
    _, out = call("hitl_scalar", f, "tier")
    assert out == "3"


def test_change_id_comment_stripped(tmp_path):
    f = write(tmp_path, "change_id: GH-42   # the tracking issue\n")
    _, out = call("hitl_scalar", f, "change_id")
    assert out == "GH-42"


# ── over-strip guard: a '#' inside a quoted value is data, not a comment ───────────────────

def test_hash_inside_a_quoted_value_survives(tmp_path):
    f = write(tmp_path, 'change_id: GH-1\ntitle: "Fix # parsing in slugs"\n')
    _, out = call("hitl_scalar", f, "title")
    assert out == "Fix # parsing in slugs"


# ── the sibling helper had the SAME defect, contrary to what issue #25 assumed ────────────

@pytest.mark.parametrize(
    "name_line,expected",
    [
        ("  name: Docs Change", "Docs Change"),
        ("  name: Docs Change   # 6-step flow", "Docs Change"),
        ('  name: "Docs Change"', "Docs Change"),
        ('  name: "Docs Change"   # 6-step flow', "Docs Change"),
    ],
)
def test_workflow_field_matches_hitl_scalar_cleaning(tmp_path, name_line, expected):
    """#25 cited hitl_workflow_field as already correct; it stripped quotes before comments too."""
    f = write(tmp_path, f"workflow:\n{name_line}\n  steps:\n")
    _, out = call("hitl_workflow_field", f, "name")
    assert out == expected, f"{name_line!r} → {out!r}"


def test_unannotated_files_are_byte_for_byte_unaffected(tmp_path):
    """The overwhelmingly common case: no comments anywhere. Nothing may change."""
    f = write(
        tmp_path,
        'schema_version: "2.0"\nchange_id: compound-agentic-surface\ntier: 3\n'
        "status: merged\nexpected_branch: issue/10-compound-agentic-surface\n",
    )
    for field, expected in [
        ("schema_version", "2.0"),
        ("change_id", "compound-agentic-surface"),
        ("tier", "3"),
        ("status", "merged"),
        ("expected_branch", "issue/10-compound-agentic-surface"),
    ]:
        _, out = call("hitl_scalar", f, field)
        assert out == expected, f"{field}: {out!r}"
