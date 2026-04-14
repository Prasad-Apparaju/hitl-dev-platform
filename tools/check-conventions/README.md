# Convention Checker

Scans the codebase for violations of the team's agreed architectural rules. Reads check definitions from `convention-checks.yaml` and reports violations, warnings, and passes.

## Usage

```bash
# Run all checks
python tools/check-conventions/runner.py --config tools/check-conventions/convention-checks.yaml --verbose

# Run a single check
python tools/check-conventions/runner.py --config tools/check-conventions/convention-checks.yaml --only manifest_drift

# In Claude Code (via skill)
/check-conventions
```

## Requirements

```bash
pip install pyyaml
```

## How It Works

The checker supports two kinds of checks:

**Universal checks** (built-in):
- `manifest_drift` — verifies `docs/system-manifest.yaml` matches the actual codebase structure
- `mermaid_br_tags` — flags `<br/>` tags inside Mermaid blocks (breaks Obsidian)
- `inline_comments` — checks that generated code has inline comments

**Project checks** (defined in `convention-checks.yaml`):

| Check type | What it does | Example use |
|-----------|-------------|-------------|
| `import_check` | Verifies a required import exists in files that use a trigger import | "Controllers must import Pydantic BaseModel" |
| `pattern_check` | Flags a forbidden pattern in files that contain a trigger pattern | "No f-strings in SQL execute calls" |
| `subclass_method_check` | Verifies subclasses implement a required method | "All MutatingTool subclasses must implement _describe_plan" |
| `file_contains` | Checks that specific files contain a required string | "Models must have a deleted_at column" |

## Configuration

Edit `convention-checks.yaml` to add project-specific checks:

```yaml
universal_checks:
  - manifest_drift
  - mermaid_br_tags
  - inline_comments

project_checks:
  - name: pydantic_validation
    description: "API endpoints must use Pydantic request models"
    type: import_check
    directory: app/controllers
    required_import: "BaseModel"
    trigger_imports: [APIRouter, router]
```

## CI Integration

Runs automatically on every PR via `.github/workflows/convention-check.yml`. Violations fail the CI check.

## Output

```
✓ manifest_drift: manifest matches codebase structure
✓ mermaid_br_tags: no <br/> tags in mermaid blocks
✗ pydantic_validation: app/controllers/orders.py uses APIRouter but does not import BaseModel

Passed: 2 | Failed: 1 | Warnings: 0
```
