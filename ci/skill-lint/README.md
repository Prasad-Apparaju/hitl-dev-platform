# ci/skill-lint/

Lints every `SKILL.md` against Anthropic's Agent Skills best practices, as captured in
[docs/design/workflow-model/04-harness-acceptance-criteria.md](../../docs/design/workflow-model/04-harness-acceptance-criteria.md)
Part A. This is the Phase-1 `command`-coverage gate's sibling: it keeps generated/authored skills
inside the published schema.

## Run

```bash
python3 ci/skill-lint/check_skills.py            # scans ai/claude, exit 1 on any hard-gate failure
python3 ci/skill-lint/check_skills.py --strict   # also fail on warnings
python3 ci/skill-lint/check_skills.py --root path/to/skills
python3 ci/skill-lint/check_skills.py --skills-require-name   # Agent-Skills (SDK/API) rule: name required
pytest ci/skill-lint/test_check_skills.py
```

No third-party dependencies required (PyYAML used if present, else a minimal frontmatter parser).

## Severities

| Severity | Meaning | Source |
|---|---|---|
| **FAIL** (exit 1) | Deterministic, false-positive-free hard gates: frontmatter validity, `description` present/valid, `name` format *when present*, body ≤ 500 lines. | Part A §1–2 |
| **WARN** (exit 0) | Judgment checks that can't be reliably static-linted: third-person, what+when, Windows paths, reference-link depth, vague names. Surfaced, not gated. | Part A §1–5 |

## The `name` field

`name` is **optional** for Claude Code plugin skills in a `skills/<dir>/` layout: Claude Code falls
back to the stable directory basename (verified against code.claude.com/docs/en/plugins-reference,
2026-06-23). So a missing `name` is reported as a one-line note, not a failure. It becomes a hard
failure only under `--skills-require-name` (the Agent Skills SDK/API rule). When you *do* add an
explicit `name`, disambiguate it (basename collisions exist, e.g. `pm/design-feature` vs
`architect/design-feature`) and keep it equal to the current invocation name.

## Wiring into CI

Add a job that runs `python3 ci/skill-lint/check_skills.py` on PRs that touch `ai/claude/**`. It is
not yet a blocking GitHub Actions workflow because two skills currently exceed the 500-line body gate
(`architect/design-feature`, `architect/design-system`); split those into reference files first, then
promote the linter to a required check.
