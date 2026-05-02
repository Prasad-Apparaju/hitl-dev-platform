# Context Models — How HITL Was Designed

HITL was built by studying exactly how Claude Code and Codex CLI load and accumulate context, then placing each platform component in the zone where it is most effective. This page explains that design rationale. The context maps linked at the bottom are the reference material we used.

---

## The Three-Zone Model

Both Claude Code and Codex CLI context can be understood as three zones:

| Zone | Claude Code | Codex CLI | Cost |
|---|---|---|---|
| **Always loaded** | `CLAUDE.md`, plugin skill descriptions | `AGENTS.md`, `.codex/config.toml` | Fixed — paid on every session regardless |
| **Loaded on demand** | Skills (when `/skill-name` is typed), hooks output | File reads, tool output, hook results | Pay only when triggered |
| **Session growth** | Conversation turns, tool results, file reads | Conversation, file reads, tool output | Grows continuously; compaction fires eventually |

The always-loaded zone is small and fixed. Real context pressure accumulates in the session-growth zone — long conversations, repeated file reads, and verbose tool output are what make sessions heavy, not startup instructions.

---

## How HITL Maps to Each Zone

### Always loaded → Conventions and rules (`CLAUDE.md` / `AGENTS.md`)

Project conventions belong in the always-loaded zone because they must be available from the very first message — before any skill is invoked, before any tool runs. `CLAUDE.md` for Claude Code and `AGENTS.md` for Codex are loaded at session startup. They are always present without triggering a lazy-load.

This is why HITL puts coding standards, domain boundaries, the preflight checklist, and the system manifest reference in `CLAUDE.md` / `AGENTS.md` rather than in a skill. Every Claude Code or Codex session on the project gets those rules automatically.

Keep these files focused. Every token in the always-loaded zone is paid on every session.

### Loaded on demand → Workflow steps (Skills)

Each workflow step — `/dev-practices`, `/tdd`, `/generate-docs`, `/architect:design-feature`, and so on — is a separate skill rather than one giant instruction block loaded at startup. Skills are lazy-loaded: they enter context only when the user explicitly invokes them.

A developer running `/tdd` pays only for the TDD skill instructions — not for the PM, Ops, or Architect workflows. A PM running `/pm:prioritize` does not load any developer workflow content.

This also means each skill can be thorough. A 30-step workflow written as a skill costs nothing on sessions where it is never invoked. Written in `CLAUDE.md`, it would cost that every session.

### Hooks → Enforcement outside the context window

Enforcement logic in HITL runs in hooks — `check-hitl-context.sh`, `check-domain-boundary.sh`, `write-session-summary.sh` — rather than as instructions in `CLAUDE.md`. Hooks fire as OS-level processes. Their output is appended to context when they produce output, but the enforcement logic itself runs outside the model's context window.

This means HITL can enforce: "a GitHub issue must exist before any file is edited" without spending any permanent tokens on that rule. The hook fires on `PreToolUse`, checks the `.hitl/current-change.yaml` file, and either passes silently (zero context cost) or blocks with a one-line message.

For Codex, the same pattern applies via `.codex/hooks.json` (lifecycle hooks) and git hooks (commit-time enforcement).

### Subagents → Parallel role work without red zone accumulation

Role-based agents — `architect-reviewer`, `qa-reviewer`, `spec-conformance-reviewer`, and others — run as subagents in separate context windows. Their analysis runs deep without ballooning the primary session. The main thread receives a summary result; the subagent's full reasoning stays in its own context window.

This maps directly to the session-growth zone insight: every tool result, file read, and assistant turn in the main thread accumulates and never shrinks until compaction. Pushing deep analysis into subagents keeps the main thread lean and lets the primary session run longer before hitting context pressure.

---

## The Design Consequence

Because skills are lazy-loaded, the total size of all HITL skills combined does not matter for session cost. What matters is the number of skills invoked in a given session. A developer doing TDD all day pays for the TDD skill once, not for the 25 other skills in the platform.

Because `CLAUDE.md` is always loaded, its size does matter. The template is intentionally structured to stay small: conventions as bullet points, not prose; a manifest reference rather than the full manifest inline; a preflight checklist rather than a full workflow.

Because hooks run outside the context window, enforcement has near-zero runtime cost. HITL can apply strict checks on every file edit without any incremental token cost per check.

---

## Context Map Files

| File | What it covers |
|---|---|
| [Claude Code overview](claude-code-context-map-overview.md) | Three-zone model for Claude Code — quick reference |
| [Claude Code detailed](claude-code-context-map.md) | Full sequence diagrams with phase-by-phase loading detail |
| [Codex CLI overview](codex-context-map-overview.md) | Three-zone model for Codex CLI — quick reference |
| [Codex CLI detailed](codex-cli-context-map.md) | Full sequence diagrams for the local repo / CLI model |
| [Codex app model](codex-app-context-map.md) | Codex in a host-app session context (vs. local CLI) |

Start with the overview files. Read the detailed maps if you are tuning context budget, debugging hook timing, or designing new skills.
