# HITL plugin evals

Cases for `claude plugin eval`, one directory each. They exercise the gates and refusals that matter
most: the setup gate, the prefixed-id refusal at intake, the design-approval refusal at TDD, help
routing, and adding a test scenario by chat. Every case runs with the plugin only (no baseline arm:
a `/hitl:` command does not exist without the plugin).

Run from the built plugin, at release (docs/releasing.md step 4), on the default model and on
Sonnet 5.5:

```bash
cd ../hitl-claude-plugin && bash scripts/build.sh >/dev/null
claude plugin eval . --ablation none --runs 1 --scaffold --trust-plugin --no-publish \
  --allow-tools Write Edit --max-cost-usd 5
claude plugin eval . --ablation none --runs 1 --scaffold --trust-plugin --no-publish \
  --allow-tools Write Edit --max-cost-usd 5 --model claude-sonnet-5-5
```

The cases grant no Bash. Granting Bash puts every run in Claude Code's OS sandbox, which refuses a
machine whose Docker credential store holds a symbolic link; the gate cases need only Read and Glob,
and the scenario case needs Write and Edit. A skill's bash fences (the scenario validator, for one)
are reported as not granted in that run, which the graders do not depend on.

Graders check the reply or the files the skill wrote, never "the Skill tool was called": a prompt that
starts with `/hitl:...` is expanded by Claude Code itself, so no Skill tool call happens and a
`tool_used: Skill` grader can never pass for these cases.

Each run is a real model call on the account. `--runs 1` is enough to catch a broken gate; raise it
when a case looks flaky. Results land under `evals/results/` in the plugin repo and are not
committed. The source of truth for the cases is this directory in the source repo; `build.sh`
copies it.
