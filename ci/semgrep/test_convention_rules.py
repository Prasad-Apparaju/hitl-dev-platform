"""Regression test for the non-SQL convention rules (issue #46).

Five of the seven shipped rules were scoped to `V2/app/**` — one product repo's layout — via
`paths.include`. `init-project.sh` copies `.semgrep/` into every onboarded project, so in any repo
not using that structure the rules matched no files and always passed: the convention gate reported
green because the rules never ran.

Removing the scope exposed a second defect underneath it: `controller-must-use-pydantic-models`
could never fire *at all*. Its `pattern-not` (`$BODY: $MODEL`) also bound the very parameter the
positive pattern looks for (`req: Request`), cancelling every match. The path scope had hidden it —
a rule that never runs is never noticed for also never matching.

The fixture is laid out under a deliberately different structure (no `V2/`, no `app/`) so any
regression that reintroduces path scoping fails here. Asserted in both directions: every violating
line is flagged, and every compliant line is not — the `re.search` / `elasticsearch.search` cases
exist because the unconstrained `$CLIENT.search(...)` pattern flags them, which is what the old
path scope was really doing.
"""

import json
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(__file__)
RULES = os.path.abspath(os.path.join(HERE, "..", "..", ".semgrep"))
FIXTURE = os.path.join(HERE, "tests", "fixtures", "convention_rule_cases.py")

# (line, rule id) pairs that MUST be reported.
MUST_FLAG = [
    (25, "vector-search-must-be-tenant-scoped"),          # Pinecone, unfiltered
    (28, "vector-search-must-be-tenant-scoped"),          # Weaviate, unfiltered
    (44, "external-calls-must-be-retried"),               # requests.get, no retry policy
    (71, "controller-must-use-pydantic-models"),
    (85, "side-effecting-tool-must-implement-describe-plan"),
    (85, "side-effecting-tool-must-have-idempotency-key"),
]

# Lines that MUST NOT be reported by any rule, and why.
MUST_NOT_FLAG = {
    31: "Pinecone query WITH a filter — compliant (any tenant key, not just brand_id)",
    32: "Weaviate search WITH where — compliant",
    33: "Chroma similarity_search WITH filter — compliant",
    36: "re.search — not a vector store; the receiver constraint must exclude it",
    37: "elasticsearch.search — not a vector store",
    49: "backoff-decorated caller — compliant",
    55: "tenacity-decorated caller — a different retry library",
    60: "call inside a retry-shaped helper — compliant",
    65: "open() — not an HTTP call",
    79: "endpoint taking a pydantic model — compliant",
    92: "WritingTool satisfying both contracts under a third base name",
    101: "ReadOnlyTool — no side effect, so neither contract applies",
}

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None, reason="semgrep not installed"
)


@pytest.fixture(scope="module")
def findings():
    result = subprocess.run(
        ["semgrep", "scan", "--config", RULES, "--metrics=off",
         "--no-git-ignore", "--json", FIXTURE],
        capture_output=True, text=True,
    )
    assert result.stdout, f"semgrep produced no output:\n{result.stderr}"
    data = json.loads(result.stdout)
    return {(r["start"]["line"], r["check_id"].split(".")[-1]) for r in data["results"]}


@pytest.mark.parametrize("line,rule", MUST_FLAG)
def test_violation_is_flagged(findings, line, rule):
    assert (line, rule) in findings, f"{rule} did not flag line {line}"


@pytest.mark.parametrize("line,why", sorted(MUST_NOT_FLAG.items()))
def test_compliant_code_is_not_flagged(findings, line, why):
    hits = {r for (ln, r) in findings if ln == line}
    assert not hits, f"line {line} ({why}) was flagged by {hits} — false positive"


def _iter_rules():
    """Yield (relative file, rule dict) for every shipped rule."""
    import yaml

    for root, _, files in os.walk(RULES):
        for name in sorted(files):
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(root, name)
            with open(path) as fh:
                doc = yaml.safe_load(fh) or {}
            for rule in doc.get("rules", []):
                yield os.path.relpath(path, RULES), rule


def test_no_rule_is_scoped_to_a_repo_specific_path():
    """The root cause: a shipped rule must never scope itself to one project's layout.

    Inspects the parsed `paths:` config rather than the file text — prose explaining the old
    `V2/app/**` scoping is documentation, not a scope, and must not trip this.
    """
    offenders = []
    for rel, rule in _iter_rules():
        for key in ("include", "exclude"):
            for pattern in (rule.get("paths") or {}).get(key, []):
                # A leading path segment that names a concrete project directory is the smell;
                # `**/…` patterns are layout-independent and fine.
                if not pattern.startswith("**/"):
                    offenders.append(f"{rel}: {rule.get('id')} -> paths.{key}: {pattern}")
    assert not offenders, "rules scoped to a project-specific path:\n  " + "\n  ".join(offenders)


def test_no_rule_names_a_single_customers_identifiers():
    """Shipped rules must encode concepts, not one customer's stack.

    `brand_id` was one project's tenant key, `MutatingTool` its base class, and
    `retry_external_call` / `httpx_client` its helper and variable names — none of which
    appear anywhere in HITL's own schema or pattern docs. Every HITL customer received them.
    Vendor names inside an *alternatives* list (qdrant | pinecone | weaviate | …) are fine:
    those are ecosystem-level and plural. A bare identifier used as THE match is not.
    """
    banned = {
        "brand_id": "a tenant key specific to one product",
        "retry_external_call": "one project's retry helper name",
        "httpx_client": "one project's variable naming",
        "external_client": "one project's variable naming",
    }
    offenders = []
    for rel, rule in _iter_rules():
        blob = json.dumps(rule)
        for token, why in banned.items():
            if token in blob:
                offenders.append(f"{rel}: {rule.get('id')} references {token!r} — {why}")
    assert not offenders, "rules tied to one customer's stack:\n  " + "\n  ".join(offenders)


def test_every_shipped_rule_is_exercised_by_a_fixture():
    """A rule with no fixture is a rule nobody would notice going inert."""
    declared = set()
    for root, _, files in os.walk(RULES):
        for name in files:
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(root, name)) as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped.startswith("- id:"):
                        declared.add(stripped.split("- id:", 1)[1].strip())

    covered = {rule for _, rule in MUST_FLAG}
    # The SQL rules are covered by their own module.
    covered |= {"no-fstring-in-sql-execute", "no-fstring-in-sqlalchemy-text"}
    assert declared <= covered, f"rules with no fixture: {sorted(declared - covered)}"
