# Harness Acceptance Criteria

**Status:** Acceptance criteria (branch `design/workflow-model`).
**Companion docs:** [00-requirements.md](00-requirements.md) · [01-design.md](01-design.md) · [02-rollout.md](02-rollout.md) · [03-execution-model.md](03-execution-model.md)

HITL is an external harness built over Claude Code: it generates and ships `SKILL.md` files, agents,
and commands, and it relies on hooks, slash commands, and settings precedence to enforce its
guardrails. These criteria hold HITL to Anthropic's official standards for those features. They are a
**harness-wide quality bar**, broader than the workflow-model encoding, and apply to the catalog,
skills, hooks, and the plugin build as the redesign lands.

**Sources of truth** (verified current as of 2026-06-23; re-check before relying on, these pages move
and event lists churn between releases):
- Skill authoring: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`
- Hooks reference: `https://code.claude.com/docs/en/hooks`
- SDK hooks: `https://platform.claude.com/docs/en/agent-sdk/hooks`

**How to read this doc:**
- **MUST** items are hard gates: the generator/validator rejects, or the harness must enforce, on failure.
- **SHOULD** items are quality guidance: warn, don't necessarily block.
- **EVAL** items can't be statically linted; they need a triggering/behavior test.
- **VERIFY** items depend on fast-moving upstream details; validate against live docs at build time.

> **HITL applicability.** Part A binds **`scripts/build.sh` + a CI validator** over every `SKILL.md`
> in `ai/claude/`. Part B binds the **hooks, commands, and `settings.json`** the plugin installs.
> HITL runs as a **Claude Code CLI plugin** (not the Agent SDK), so the CLI path applies throughout
> §7/§8; if that ever changes, re-read those sections.

---

# PART A: Skill files (validate every `SKILL.md` in `ai/claude/`)

## 1. Frontmatter validation (HARD GATES, reject on failure)

### `name`
- [ ] **MUST** be present and non-empty
- [ ] **MUST** be ≤ 64 characters
- [ ] **MUST** match `^[a-z0-9-]+$` (lowercase letters, numbers, hyphens only)
- [ ] **MUST NOT** contain XML tags
- [ ] **MUST NOT** contain the reserved substrings `anthropic` or `claude`

### `description`
- [ ] **MUST** be present and non-empty
- [ ] **MUST** be ≤ 1024 characters
- [ ] **MUST NOT** contain XML tags
- [ ] **MUST** describe *what* the skill does AND *when* to use it
- [ ] **MUST** be third person ("Processes Excel files...", not "I can help you..." / "You can use this...")

### Structure
- [ ] **MUST** be valid YAML at the top of the file, delimited by `---` fences
- [ ] **MUST** include both `name` and `description` (the only two required fields)

## 2. Body structure (enforce as gates where measurable)
- [ ] **MUST** keep the `SKILL.md` body under 500 lines (target < ~150 for most; push deep content into reference files)
- [ ] **MUST** use forward slashes in all file paths (no Windows backslashes)
- [ ] **MUST** keep reference links one level deep from `SKILL.md` (no `SKILL.md` → a.md → b.md chains; nested files get only partially read)
- [ ] **MUST** include a table of contents at the top of any reference file > 100 lines

## 3. Naming convention (SHOULD, warn)
- [ ] **SHOULD** use gerund form (`processing-pdfs`, `analyzing-spreadsheets`); noun phrase (`pdf-processing`) or action (`process-pdfs`) are acceptable
- [ ] **SHOULD NOT** use vague names: `helper`, `utils`, `tools`, `documents`, `data`, `files`
- [ ] **SHOULD** keep naming patterns consistent across the skill library

## 4. Content quality (SHOULD, warn)
- [ ] **SHOULD** be concise: only add context Claude doesn't already have (don't explain what a PDF / PR / library is)
- [ ] **SHOULD** match degrees of freedom to task fragility: high freedom (prose) when many valid approaches exist; low freedom (exact scripts, "do not modify the command") when fragile or sequence-critical
- [ ] **SHOULD NOT** contain time-sensitive info ("before August 2025, use..."); collapse deprecated material into an "old patterns" section
- [ ] **SHOULD** use consistent terminology (one term per concept, no synonym drift)
- [ ] **SHOULD NOT** offer too many options; give one default plus an escape hatch

## 5. Skills with executable code (SHOULD, gate where possible)
- [ ] Scripts **SHOULD** handle error conditions explicitly (solve, don't punt to Claude)
- [ ] **SHOULD NOT** contain unjustified magic numbers; every timeout / retry / limit needs a justifying comment
- [ ] **MUST** state whether each script is executed or read as reference
- [ ] **MUST** list required packages explicitly in `SKILL.md`
- [ ] MCP tool references **MUST** be fully qualified: `ServerName:tool_name` (e.g. `BigQuery:bigquery_schema`)
- [ ] For high-stakes batch / destructive operations, **SHOULD** use plan → validate → execute with a machine-validated intermediate file and verbose, specific validation errors
- [ ] **MUST** account for execution-environment package policy: claude.ai can install from npm/PyPI and GitHub; the raw Claude API has NO network access and NO runtime install, so packages must be pre-installed. Validate every listed package is available in the target environment.

## 6. Evaluation-driven development (EVAL, behavior tests not static lint)
- [ ] Each generated skill **SHOULD** ship with ≥ 3 evaluations
- [ ] Eval format: JSON with `skills`, `query`, `files`, `expected_behavior` (rubric list)
- [ ] Establish a baseline (Claude's behavior WITHOUT the skill) before measuring
- [ ] **EVAL, triggering:** the skill fires on the intended query AND stays quiet on unrelated queries (description quality can't be statically linted; test it)
- [ ] **SHOULD** test across all target models (Haiku / Sonnet / Opus) if multi-model; what suffices for Opus may underspecify for Haiku
- [ ] There is no built-in eval runner; the harness must provide its own

## 7. CLI vs SDK gating
- [ ] The `allowed-tools` frontmatter field works ONLY in the Claude Code CLI; it is IGNORED via the Agent SDK
- [ ] On the SDK path, tool access is the `allowedTools` query option AND **MUST** be paired with `permissionMode: "dontAsk"` to actually deny unlisted tools (an allowlist alone only pre-approves; unlisted tools otherwise fall through to the active permission mode)
- [ ] **HITL note:** HITL ships as a CLI plugin, so `allowed-tools` frontmatter is honored. If HITL ever moves to the SDK, this flips.

---

# PART B: Harness use of Claude Code features (hooks, commands, settings)

## 8. Architecture decision: CLI vs SDK (decide first)
- [ ] **MUST** decide CLI vs Agent SDK explicitly; hooks, permissions, and skill tool-gating all branch on it. CLI: a hook is a shell command reading JSON from stdin, signaling via exit codes + stdout JSON. SDK: the same lifecycle events are in-process callbacks.
- [ ] **HITL: CLI.** Confirmed; the rest of Part B is read on the CLI path.

## 9. Hooks: enforcement model (HARD GATES)
- [ ] **MUST** treat hooks (not CLAUDE.md / skill text) as the enforcement layer for anything that must NEVER happen; hooks fire on system events, not model decisions
- [ ] **MUST** use `PreToolUse` with exit code 2 for hard blocks (the only reliable pre-execution block; permission rules and `.claudeignore` can be bypassed via indexing / system-reminder injection). exit 2 = block + stderr fed back to model; exit 0 = allow; JSON output parsed only on exit 0
- [ ] **MUST NOT** encode path/argument logic in the matcher regex; matchers filter by TOOL NAME only. Check `tool_input.file_path` inside the callback (this is exactly how `check-hitl-context.sh` gates edits)
- [ ] **MUST** match MCP tools with the `mcp__<server>__<action>` scheme (e.g. `mcp__.*` to catch all MCP tools)
- [ ] **MUST** invoke hook scripts by a path that resolves regardless of the hook's working directory: an absolute path or `"$CLAUDE_PROJECT_DIR"/...`, never a bare repo-relative path. *(Lesson: this repo's `settings.json` wired `bash ai/claude/hooks/*.sh` relatively, which threw `No such file or directory` on every Edit/Write because the hook cwd was not the repo root.)*

## 10. Hooks: handler types & failure modes
- [ ] **SHOULD** pick the handler type by need: `command` (shell/stdin), `http` (POST body), `prompt` (single-turn LLM), `agent` (multi-step subagent with tools)
- [ ] **MUST** account for HTTP hooks failing OPEN: non-2xx, connection failures, and timeouts are non-blocking. To block, return 2xx with `decision: "block"`. Never rely on an HTTP hook as the sole block on a dangerous op.
- [ ] **SHOULD** use `async: true` for non-blocking work (logging, notifications, backups)
- [ ] **MUST** only rely on stdout reaching the model from `UserPromptSubmit`, `UserPromptExpansion`, and `SessionStart`; other events' stdout goes to the debug log only
- [ ] **MUST** surface user-facing messages via `systemMessage` (JSON) or a bell via `terminalSequence`; command hooks run without a controlling TTY on macOS/Linux (as of v2.1.139), so direct `/dev/tty` writes silently fail
- [ ] **MUST** treat hook scripts as trusted code: they run with full user permissions, no sandbox. Review and version-control every hook script.
- [ ] **SHOULD** degrade gracefully: a HITL hook in a project with no `.hitl/` must no-op and exit 0, not error.

## 11. Hooks: subagent hazards (HARD GATES for any harness spawning subagents)
- [ ] **MUST** handle that subagents do NOT inherit parent permissions; use `PreToolUse` auto-approve hooks or subagent-scoped permission rules to avoid repeated prompts
- [ ] **MUST** prevent infinite loops where a `UserPromptSubmit` hook spawns subagents that re-trigger the same hook; guard by checking the subagent indicator in hook input, tracking session state, or scoping the hook to the top-level session only
- [ ] **SHOULD** log hook decisions to a dedicated channel; `systemMessage` may not appear in all output modes

## 12. Slash commands (SHOULD)
- [ ] Custom commands live at `.claude/commands/<name>.md` (project) or `~/.claude/commands/<name>.md` (user)
- [ ] Markdown body = prompt template; optional YAML frontmatter sets `description`, `allowed-tools`, `model`
- [ ] **SHOULD** treat commands as version-controlled, reviewable prompt artifacts with the same conciseness/consistency discipline as skills
- [ ] **MUST** resolve a workflow step's `command` against the full executor surface, **commands + agents + skills**, not just `SKILL.md` dirs. *(Lesson: the W1 coverage audit false-negatived three steps as "no executor" because it only checked skill dirs; they exist as command files delegating to agents. See [02-rollout.md §7](02-rollout.md).)*

## 13. Settings precedence & guardrails (HARD GATES)
- [ ] **MUST** understand the resolution order: managed policy (org) → user → project → local → plugin hooks → skill/agent frontmatter
- [ ] **MUST** place non-negotiable guardrail hooks at the MANAGED-POLICY level; `disableAllHooks` in user/project/local cannot disable managed hooks, only `disableAllHooks` at the managed level can
- [ ] **SHOULD** (enterprise) set `allowManagedHooksOnly` to restrict users to org-approved hooks
- [ ] **MUST** keep `settings.json` valid JSON at all times; a malformed file silently disables ALL settings from that file
- [ ] Settings edits are normally hot-reloaded, but matcher/event changes or new tools may need `/hooks` re-run or a restart to reload

## 14. Cross-cutting
- [ ] **MUST** apply defense-in-depth for secrets: there is no built-in redaction. Read returns `.env` contents and Bash can `cat`/`grep` them; `.claudeignore` and allow-lists do NOT fully prevent access. Pair a `PreToolUse` hook (exit 2 on sensitive paths, matched to `Edit|Write|Read`) WITH a deny rule like `Read(./.env)`.
- [ ] **SHOULD** match the enforcement mechanism to failure cost: CLAUDE.md / skill text for things the model should usually do; permission rules for a default-deny posture; hooks for things that must never happen regardless of model reasoning.

## 15. Upstream-churn validation (VERIFY at build time)
- [ ] **VERIFY** the canonical hook event list against `code.claude.com/docs/en/hooks` at build time; event count/names churn (sources cite 21, 30, and "occasionally added between releases"). Do NOT hardcode an event list from memory.
- [ ] **VERIFY** the skill best-practices spec (Part A) against the canonical page if this doc is more than a few weeks old at handoff.

---

## How this binds the rollout

- **Part A** is a CI gate over `ai/claude/**/SKILL.md`, run by an extension of `scripts/build.sh`.
  Sections 1–2 are hard schema gates (reject); 3–5 are lint warnings; 6 is behavior tests.
- **Part B** is verified once against the installed plugin and re-checked whenever hooks, commands,
  or `settings.json` change. §9's absolute-path rule and §13's valid-JSON rule are regression-tested
  in the same CI that runs the breadcrumb matrix (see [02-rollout.md §6](02-rollout.md)).
- The two HITL-specific lessons (absolute-path hooks §9, executor resolution §12) come from real bugs
  hit while building this redesign; they are non-negotiable.
