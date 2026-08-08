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

`ci/workflows/skill-lint.yml` runs `check_skills.py --root ai/claude` plus the linter's own tests on
every PR touching `ai/claude/**/SKILL.md` or `ci/skill-lint/**`. The script exits 1 on any hard gate,
so the job blocks the PR.

**As of 2.4.6 every shipped skill passes: 54/54, 0 failures, 0 warnings.** The body-length backlog
this section used to describe is cleared — the last offender (`dev-start-brownfield`, 521 lines) was
split into `observability-survey.md` following the progressive-disclosure pattern. Nothing is
grandfathered, so the gate can be made a *required* check without exceptions.

Two scope limits worth knowing:

- The workflow lints `--root ai/claude` only. `SKILL.md` files elsewhere in the repo — such as the
  legacy command copy under `.claude/commands/skills/` — are covered by a local
  `check_skills.py --root .` but not by the PR gate.
- `dev-start-migration` sits at 497 body lines against the 500 limit. Anything added to it breaks
  the gate; split a section out rather than trimming prose to fit.
