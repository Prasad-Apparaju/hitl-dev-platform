# GH-147 release 2.16.1, round 2 (correctness + upgrade, one pass)

Verdict: PASS. All six round-1 claims are fixed at 096c1f0; gates green; scratch build at 2.16.1 validates; no new blocking findings.

Reviewed: /Users/Prasad_1/Projects/hitl-dev-platform at 096c1f005b7ada50a0c354c4d771f01df19c1f88. Plugin repo copied to a scratch dir and built there; neither repo modified.

## Round-1 claims (verbatim) and status

- C1: "The changelog sentence \"Skills take `<PREFIX>-<n>`, refuse a bare number when a prefix is configured\" is carried only by start-change/SKILL.md:47 and switch-context/SKILL.md:49." — **fixed**. ai/claude/apply-change/SKILL.md:51 and ai/claude/tdd/SKILL.md:27 now each state the rule (full id `SVC-3`, bare number refused when `change_id_prefix` is configured, #145).
- C2: "start-change/SKILL.md:284 pre-fills ack_by as \"the person confirming the plan\", while rule 1 at line 330 says a floor skip needs \"the accountable role's\" ack_by." — **fixed**. Line 284 now reads "`ack_by` the person confirming the plan (the validator needs a named person; for these two Ops floor steps the confirmer is that person)". It reconciles the two rather than naming a winner: the confirmer is the accountable person for deploy/promote, so rule 1 at line 330 is satisfied. ci/first-pass/check_skips.py:538 accepts "a person or role".
- C3: "ops/deploy/SKILL.md:140 posts the Deployed comment to `<issue-number>` with no derivation line, unlike ta-approve and the hook." — **fixed**. ai/claude/ops/deploy/SKILL.md:140 derives ISSUE_NUM with the same sed as ta-approve and the hook, line 141 posts to `"$ISSUE_NUM"`; prose at line 137 explains the derivation. Sed on `SVC-3` yields `3`.
- U1: "shipped-validators.sha256 relabels the 2.16.0 line." — **fixed**. ci/shipped-validators.sha256:77 is `f21651d6… ci/linked/linked.py  # 2.16.0` (matches `git show 39c3e28:ci/linked/linked.py`), line 78 is `192889a6… ci/linked/linked.py  # 2.16.1` (matches the tree). `--check` passes.
- U2: "dev-start-change Step 1 prose calls resolve before $LINKED exists." — **fixed**. Built skills/dev-start-change/SKILL.md:47 (Step 2) carries the inline ROOT/LINKED resolution before `python3 "$LINKED" resolve <id>`; no `$LINKED` use precedes a definition in the built skill. Extracted command run in an empty dir resolves LINKED to `<scratch>/shared/ci/linked/linked.py` and `resolve --help` exits 0.
- U3: "bare-number change ids: the hook/ta-approve sed requires a non-digit before the trailing digits, so \"12\" and \"GH-12-foo\" yield empty and the hook exits silently." — **fixed**. Built hook sed `s/^\(.*[^0-9]\)\{0,1\}\([0-9][0-9]*\)$/\2/p` gives 12 → 12, GH-12 → 12, SVC-3 → 3, GH-12-foo → empty, nodigits → empty. Same expression in ta-approve (three sites) and ops/deploy.

## Checks

1. C1/C2/C3 source: `grep -n change_id_prefix ai/claude/apply-change/SKILL.md ai/claude/tdd/SKILL.md`; `grep -n ack_by ai/claude/start-change/SKILL.md`; `grep -n 'ISSUE_NUM\|gh issue comment' ai/claude/ops/deploy/SKILL.md`; `printf SVC-3 | sed -n '<deploy expr>'` → 3. PASS.
2. U1: `python3 tools/scripts/shipped-validators-hashes.py --check` → exit 0, "manifest current"; `shasum -a 256 ci/linked/linked.py` = 192889a6…; `git show 39c3e28:ci/linked/linked.py | shasum -a 256` = f21651d6…. PASS.
   U2: extracted `resolve it with \`…python3 "$LINKED"\`` from the BUILT skill into u2.sh, appended `resolve --help`; `cd <empty dir> && env -i PATH HOME CLAUDE_PLUGIN_ROOT=<scratch>/plugin bash u2.sh` → help text, LINKED under the scratch build, exit 0. PASS.
   U3: expression taken from BUILT hooks/sync-step-to-issue.sh (byte-identical to source via `cmp`); five inputs as above. PASS.
3. Gates at 096c1f0: `python3 -m pytest ci/ tools/ -q` → 1319 passed; `python3 ci/skill-lint/check_skills.py` → 65/65 pass, 0 failures, 0 warnings; `(cd tools/workflow-catalog && python3 derive.py verify)` → VERIFY OK. PASS.
4. Build: `cp -R hitl-claude-plugin <scratch>/plugin && bash scripts/build.sh /Users/Prasad_1/Projects/hitl-dev-platform > build.log 2>&1` → exit 0, "Build complete", all shared/ references resolve; plugin.json version 2.16.1; `claude plugin validate <scratch>/plugin` → "Validation passed". Fence scan (python, fenced blocks only, skills/ shared/ agents/): 0 bare `${CLAUDE_PLUGIN_ROOT}` outside a `${CLAUDE_PLUGIN_ROOT:-` fallback. `git -C <scratch>/plugin status --short` → 14 modified files (plugin.json, CHANGELOG.md, hook, shared/ci/linked/linked.py, retired-tests.sha256, shipped-validators.sha256, shared/linked-changes.md, change-context.schema.yaml, six skills), each mapping to a file in `git diff --name-only 39c3e28 096c1f0`; nothing untracked. PASS.
5. `git diff --stat 40a6b56 096c1f0` → apply-change, ops/deploy, start-change, ta-approve, tdd SKILL.md; hooks/sync-step-to-issue.sh; ci/shipped-validators.sha256; 7 files, +13/−12. PASS.

## New findings

None blocking. One observation, not counted against the release because it predates it:

- ops/deploy (new at :140) and ta-approve (:164, :213, :235) use `$CHANGE_ID` inside the fence with no shell line that sets it from `.hitl/current-change.yaml`; the hook sets it itself. ta-approve has shipped this way since 2.16.0 and both skills read the record in prose first, so the model fills it in. If a later release wants these fences runnable as written, add one `CHANGE_ID=$(awk …current-change.yaml)` line above the sed. Low.
