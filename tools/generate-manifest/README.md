# Manifest Generator

Scans a Python codebase and generates `docs/system-manifest.yaml` — the file that defines domain boundaries, facade APIs, conventions, and the interaction matrix.

## Usage

```bash
# Generate a manifest from source code
python tools/generate-manifest/generator.py --source ./app --output docs/system-manifest.yaml

# Specify language explicitly
python tools/generate-manifest/generator.py --source ./src --output docs/system-manifest.yaml --language python

# Check for drift (compare existing manifest against codebase)
python tools/generate-manifest/generator.py --check docs/system-manifest.yaml
```

## Requirements

```bash
pip install pyyaml
```

## How It Works

The generator uses AST analysis to extract:

| What it detects | How |
|----------------|-----|
| **Domains** | Top-level directories under the source root become domains |
| **File lists** | All `.py` files grouped by domain |
| **Dependencies** | Import graph — which domains import from which |
| **Facade APIs** | Public classes and functions (detected from decorators, base classes) |
| **Conventions** | Known patterns (e.g., `MutatingTool` subclasses → idempotency convention) |

## Output

The generated manifest has two kinds of fields:

- **Auto-generated** — file lists, dependencies, detected conventions. Updated on every run.
- **Human-authored** — blurbs, mutations, preconditions, error modes. Marked with `# human-authored` and preserved across re-runs.

## Drift Check Mode

Use `--check` to compare the existing manifest against the current codebase without modifying it. Reports:
- New files not in the manifest
- Deleted files still listed in the manifest
- New imports that change the dependency graph

This runs in CI via `.github/workflows/manifest-check.yml`.

## After Generating

1. Review the auto-generated domains — merge or split as needed
2. Fill in the human-authored fields (blurbs, mutations, preconditions)
3. Add the manifest to `CLAUDE.md` so AI reads it before every change
4. Run the convention checker to verify the manifest matches the codebase
