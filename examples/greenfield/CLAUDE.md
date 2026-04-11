# Claude Code Instructions

These rules apply to EVERY Claude Code session that opens this repo.

## Preflight Check (MANDATORY)

Before making ANY code or doc change, output these 7 lines:

1. **Issue**: Is there a GitHub issue? If no → `gh issue create` now.
2. **Workflow**: Have I run `/workflows:apply-change`? If no → run it now.
3. **Docs**: Does HLD/LLD/ADR cover this change? If no → update BEFORE code.
4. **ROI estimate**: Change costs >1 day? If yes → add ROI Estimate section to the issue.
5. **Training plan**: Introduces a new capability? If yes → stub required. If no → say so explicitly.
6. **Downstream impact**: Affects other teams? If yes → impact brief required.
7. **Plan**: State the order (docs → IaC → code → tests → reconcile docs).

## Development Practices
Before any code change, load `/skills:dev-practices` and follow its workflow.

## System Manifest
Before modifying any code, read `docs/system-manifest.yaml`.

## Cross-Cutting Conventions

### 1. Input Validation
All API endpoints must validate input with Pydantic schemas. Raw request bodies must never reach business logic unvalidated. Enforced by code review.

### 2. Parameterized Queries
All database queries must use parameterized queries. No string interpolation in SQL. No f-strings in query construction. Enforced by convention checker + code review.

### 3. Error Response Format
Error responses must follow RFC 7807 problem detail format: type, title, status, detail. Enforced by output middleware.

## Coding Standards

### Python
- Formatter: black (line length 100)
- Linter: ruff
- Type hints: required on all public function signatures
- Tests: pytest

### Documentation
- All diagrams use Mermaid (no ASCII art)
- No `<br/>` tags inside Mermaid code blocks

## Domain Boundaries
Stay within your domain boundary as defined in `docs/system-manifest.yaml`.

## Quality Over Speed
The goal is meticulous system evolution with minimized problems — NOT speed.
