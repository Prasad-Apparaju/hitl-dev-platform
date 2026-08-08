"""Regression test for .semgrep/security/sql-injection.yaml (issue #45).

Both rules used to match `f"..."` but NOT implicit string concatenation involving an f-string
(`execute(f"..." "...")` and the reverse order). That construct is idiomatic — it is how long
SQL gets written across lines without trailing-space bugs, and formatters produce it — so the
miss was easy to hit. It also degrades the acceptance criterion teams write against these rules:
fix every flagged site, watch `semgrep --error` return 0, and conclude a file is clean while the
interpolation is still there. Found via dilipkpoluru/PSR-Works#382, where a migration with three
f-string `op.execute()` calls reported two.

Asserts on exact line numbers in the fixture, in both directions: every BAD line is flagged and
every OK line is not. A rule that fires on plain literals would be worse than the gap.
"""

import json
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(__file__)
RULE = os.path.abspath(os.path.join(HERE, "..", "..", ".semgrep", "security", "sql-injection.yaml"))
FIXTURE = os.path.join(HERE, "tests", "fixtures", "sql_interpolation_cases.py")

# Lines in the fixture that MUST be flagged, and why. Keep in sync with the fixture.
MUST_FLAG = {
    15: "single-line f-string",
    17: "triple-quoted f-string",
    20: "implicit concatenation, f-string first (the #45 gap)",
    23: "implicit concatenation, plain string first (the #45 gap)",
    25: "explicit + concatenation",
    27: ".format()",
    31: 'f-string in text()',
    33: "implicit concatenation in text() (the #45 gap)",
    35: "implicit concatenation in text(), plain first (the #45 gap)",
}

# Lines that MUST NOT be flagged — no interpolation at all.
MUST_NOT_FLAG = {
    39: "plain literal",
    41: "concatenation of plain literals",
    43: "bound parameter",
}

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None, reason="semgrep not installed"
)


@pytest.fixture(scope="module")
def flagged():
    """Line numbers the rule file reports against the fixture."""
    result = subprocess.run(
        ["semgrep", "scan", "--config", RULE, "--metrics=off",
         "--no-git-ignore", "--json", FIXTURE],
        capture_output=True, text=True,
    )
    assert result.stdout, f"semgrep produced no output:\n{result.stderr}"
    return {r["start"]["line"] for r in json.loads(result.stdout)["results"]}


@pytest.mark.parametrize("line,why", sorted(MUST_FLAG.items()))
def test_interpolated_sql_is_flagged(flagged, line, why):
    assert line in flagged, f"line {line} ({why}) was NOT flagged"


@pytest.mark.parametrize("line,why", sorted(MUST_NOT_FLAG.items()))
def test_plain_sql_is_not_flagged(flagged, line, why):
    assert line not in flagged, f"line {line} ({why}) was flagged — false positive"
