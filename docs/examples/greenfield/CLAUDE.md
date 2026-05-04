# Claude Code Instructions

These rules apply to EVERY Claude Code session that opens this repo.

## HITL Principle

AI proposes, humans approve. No implementation work starts unless there is an approved source artifact chain:

1. GitHub issue or PRD
2. Approved HLD/LLD
3. ADR or decision packet (for tradeoff decisions)
4. `docs/system-manifest.yaml` domain
5. Existing code

**Refusal rule:** Do not implement from chat-only requirements. If no GitHub issue exists, create one first.

**Preflight rule:** Before editing any source file, verify `.hitl/current-change.yaml` exists and has `status: implementation-approved`.

**Traceability rule:** Every behavior change must cite a doc section or decision ID.

## Available Skills (invoke with /skill-name)

| Skill | When to use |
|-------|-------------|
| `/apply-change` | Before any code — impact analysis + HITL context init |
| `/dev-practices` | Full change workflow reference |
| `/tdd` | TDD cycle after LLD is approved |
| `/impact-brief` | Downstream impact + rollout plan before PR |
| `/generate-docs` | HLD/LLD/ADR generation or brownfield reverse-engineer |
| `/check-conventions` | Before PR — semgrep, manifest drift, Mermaid checks |

## Available Agents (invoke with Task tool or @agent-name)

| Agent | Role |
|-------|------|
| `pm-reviewer` | Reviews PRDs and acceptance criteria |
| `architect-reviewer` | Reviews HLD/LLD/ADR before implementation |
| `developer-implementer` | Implements code from approved LLD |
| `qa-reviewer` | Reviews test coverage against acceptance criteria |
| `ops-release-reviewer` | Reviews rollout plan and canary criteria |
| `spec-conformance-reviewer` | Compares code to LLD after implementation |

## System Manifest
Before modifying any code, read `docs/system-manifest.yaml` and identify which domain the change belongs to.

## Tooling Commands
- Test: `pytest`
- Lint: `ruff check .`
- Format: `black .`
- Convention check: `/check-conventions`
- Manifest drift: `python tools/manifest-drift/check_manifest_drift.py --source-dirs src/`

## Cross-Cutting Conventions

### 1. Input Validation
All API endpoints must validate input with Pydantic schemas. Raw request bodies must never reach business logic unvalidated. Enforced by code review.

### 2. Parameterized Queries
All database queries must use parameterized queries. No string interpolation in SQL. Enforced by convention checker + code review.

### 3. Error Response Format
Error responses must follow RFC 7807 problem detail format: type, title, status, detail. Enforced by output middleware.

## Coding Standards

- Formatter: black (line length 100)
- Linter: ruff
- Type hints: required on all public function signatures
- Tests: pytest
- All diagrams: Mermaid (no ASCII art, no `<br/>` in Mermaid blocks)

## Domain Boundaries
Stay within `allowed_paths` from `.hitl/current-change.yaml`. The domain boundary hook will warn on violations.
