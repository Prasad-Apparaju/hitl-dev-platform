# Language and Stack Support

## What is language-agnostic

The core HITL process — the 31-step workflow, TDD cycle, impact analysis, decision packets, ROI estimation, downstream impact briefs — makes no assumption about the language or framework used. These steps operate on docs, YAML files, and the AI model's ability to read and write code in any language the model supports.

Everything in the process layer runs in any stack:

- `/hitl:dev:tdd` — reads an LLD and generates tests, then implementation; works in any language
- `/hitl:architect:design-system` and `/hitl:architect:design-feature` — generate docs, not code
- `/hitl:dev:impact-brief`, `/hitl:qa:plan-tests`, `/hitl:qa:verify-quality` — read YAML and docs
- Decision packets, system manifest, test registry — YAML files with no language dependency
- All enforcement hooks — shell scripts that check YAML state, not code structure

## What is currently Python-first

Two enforcement tools are language-specific:

### Semgrep rules (`.semgrep/`)

The convention rules in `.semgrep/` target Python. Running `semgrep scan --config .semgrep/ --error` on a TypeScript or Go project will produce zero matches and zero violations — not because the code is clean, but because no rules apply.

### Manifest drift checker (`ci/manifest-drift/`)

The drift checker uses Python's `ast` module to parse source files and verify that the domains declared in `system-manifest.yaml` map to real source paths. It understands Python import structure. Running it against TypeScript or Go source produces incorrect or empty results.

The `manifest-generator` tool (`tools/manifest-generator/`) has the same limitation — it uses AST analysis to infer domain boundaries from Python source.

## How to extend to other stacks

### Tier 1 — Add semgrep rules for your language (1-3 days)

Semgrep supports many languages natively. Adding rules for TypeScript, JavaScript, Go, Java, Rust, etc. is straightforward:

1. Create `.semgrep/rules-typescript.yaml` (or the language of your choice)
2. Write rules using semgrep's pattern syntax for that language
3. The existing `check-conventions` skill picks them up automatically — it runs `semgrep scan --config .semgrep/`

This is the easiest extension point. Semgrep's rule library and pattern documentation cover most common convention checks.

### Tier 2 — Add an alternative linter or checker (1-5 days)

If semgrep does not have good coverage for your stack, add a language-native linter alongside it:

1. Extend `/hitl:dev:check-conventions` (in `ai/claude/check-conventions/SKILL.md`) to conditionally run the linter based on the stack declared in `CLAUDE.md` or `system-manifest.yaml`
2. Map the linter's exit codes and output format to the existing pass/fail pattern
3. The CI workflow in `ci/workflows/` should run the same linter — update it to match

Examples: ESLint for TypeScript, golangci-lint for Go, clippy for Rust, RuboCop for Ruby.

### Tier 3 — Replace the manifest drift checker (1-2 weeks)

The drift checker and manifest generator need per-language parsers to understand source structure:

1. Replace the Python AST parser with a parser for your language (e.g., `@typescript-eslint/parser` for TypeScript, `go/parser` for Go, `tree-sitter` for a universal approach)
2. The checker logic — comparing declared domains to actual source paths — stays the same; only the parsing layer changes
3. Update `ci/manifest-drift/check.py` or replace it with a language-appropriate tool

A `tree-sitter`-based approach handles most languages with one implementation and is the recommended direction for polyglot teams.

## Mixed stacks

If your project uses multiple languages (e.g., Go backend + TypeScript frontend), apply Tiers 1-2 per language. The process layer already handles mixed stacks — LLDs describe components in whatever language they use, and `/hitl:dev:tdd` generates tests in the appropriate language per component. The only constraint is that each domain in `system-manifest.yaml` should map to source in a single language, so the manifest drift check can apply the right parser per domain.

## Current status summary

| Layer | Python-only | Language-agnostic |
|-------|:-----------:|:-----------------:|
| 31-step workflow | | ✓ |
| TDD cycle (`/hitl:dev:tdd`) | | ✓ |
| Impact analysis, decision packets | | ✓ |
| Hooks (domain boundary, HITL context) | | ✓ |
| Semgrep rules (`.semgrep/`) | ✓ | |
| Manifest drift checker | ✓ | |
| Manifest generator | ✓ | |

Adding Tier 1 (semgrep rules) gets any language to full process coverage for convention checks. Tier 3 (drift checker) is only needed if you want automated enforcement that declared manifest domains match real source structure.
