# Enhanced Manifest Drift Checker

Detects four categories of drift between `docs/system-manifest.yaml` and the actual codebase.

## What It Checks

| Check | Severity | What it detects |
|---|---|---|
| **Deleted files** | ERROR | Manifest lists a file that no longer exists on disk |
| **Unlisted files** | WARNING (ERROR with `--strict`) | A source file exists but is not tracked by any domain |
| **Cross-domain imports** | WARNING | A file in domain A imports directly from domain B (should use facade API) |
| **Missing facade coverage** | WARNING | A `facade_apis` entry names a function/class that doesn't exist in the domain's files |

ERRORS cause exit code 1 (blocks CI). WARNINGS cause exit code 0 (advisory only).

## Usage

```bash
# Basic — uses defaults (manifest at docs/system-manifest.yaml, scans app/ and src/)
python tools/manifest-drift/check_manifest_drift.py

# Custom manifest path
python tools/manifest-drift/check_manifest_drift.py --manifest path/to/manifest.yaml

# Custom source directories to scan for unlisted files
python tools/manifest-drift/check_manifest_drift.py --source-dirs app/ lib/ services/

# Strict mode — unlisted files become errors (exit 1) instead of warnings
python tools/manifest-drift/check_manifest_drift.py --strict

# Python-only mode (default, currently the only mode)
python tools/manifest-drift/check_manifest_drift.py --python-only
```

## How Cross-Domain Import Detection Works

The checker uses Python's `ast` module to parse imports (not regex). For each file listed in a domain, it extracts all `import` and `from ... import` statements and resolves them to see if the imported module belongs to a different domain.

Example: if `app/services/orders.py` (domain: orders) contains `from app.services.auth import verify_token`, and `app/services/auth.py` belongs to domain auth, this is flagged as a cross-domain import. The orders domain should use auth's facade API instead.

## How Facade Coverage Works

For each domain that has `facade_apis` defined, the checker collects all top-level function and class names from the domain's Python files (using AST parsing). It then checks that each facade API name appears as a top-level definition. If `facade_apis.create_order` is listed but no function or class named `create_order` exists in the domain's files, it is flagged.

## CI Integration

Add to your GitHub Actions workflow:

```yaml
manifest-drift:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install pyyaml
    - name: Check manifest drift
      run: python tools/manifest-drift/check_manifest_drift.py
```

## Pre-Commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: manifest-drift
      name: Manifest drift check
      entry: python tools/manifest-drift/check_manifest_drift.py
      language: python
      additional_dependencies: [pyyaml]
      pass_filenames: false
```
