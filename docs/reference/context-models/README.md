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

### Loaded on demand → Workflow steps

**Claude Code:** Each workflow step — `/dev-practices`, `/tdd`, `/generate-docs`, `/architect:design-feature`, and so on — is a separate skill rather than one giant instruction block loaded at startup. Skills are lazy-loaded: they enter context only when the user explicitly invokes them. A developer running `/tdd` pays only for the TDD skill instructions — not for the PM, Ops, or Architect workflows. A 30-step workflow written as a skill costs nothing on sessions where it is never invoked.

**Codex CLI:** There is no equivalent lazy-load path for skills. The full workflow is encoded directly in `AGENTS.md`, which is always loaded at startup. The design consequence is different: instead of deferring workflow instructions, the complete AGENTS.md is present from the first message — but every token in it is paid on every session. This is why the HITL `codex/AGENTS.md` is structured differently from the Claude skills: it consolidates all workflows into one focused document rather than splitting them across 25 individually lazy-loaded files.

### Hooks → Enforcement outside the context window

Enforcement logic in HITL runs in hooks — `check-hitl-context.sh`, `check-domain-boundary.sh`, `write-session-summary.sh` — rather than as instructions in `CLAUDE.md`. Hooks fire as OS-level processes. Their output is appended to context when they produce output, but the enforcement logic itself runs outside the model's context window.

This means HITL can enforce that a change context file (`.hitl/current-change.yaml`) exists and contains the required fields — including an issue reference — before any file is edited. The hook fires on `PreToolUse`, checks the file, and either passes silently (zero context cost) or blocks with a one-line message. It does not make a live GitHub API call to verify the issue; it checks that the local context file was properly initialized.

For Codex, the same pattern applies via `.codex/hooks.json` (lifecycle hooks scoped to `Write|Edit` operations) and git hooks (commit-time enforcement).

### Subagents → Parallel role work without red zone accumulation

Role-based agents — `architect-reviewer`, `qa-reviewer`, `spec-conformance-reviewer`, and others — run as subagents in separate context windows. Their analysis runs deep without ballooning the primary session. The main thread receives a summary result; the subagent's full reasoning stays in its own context window.

This maps directly to the session-growth zone insight: every tool result, file read, and assistant turn in the main thread accumulates and never shrinks until compaction. Pushing deep analysis into subagents keeps the main thread lean and lets the primary session run longer before hitting context pressure.

---

## The Design Consequence

**Claude Code:** Because skills are lazy-loaded, the total size of all HITL skills combined does not matter for session cost. What matters is the number of skills invoked in a given session. A developer doing TDD all day pays for the TDD skill once, not for the 25 other skills in the platform. Because `CLAUDE.md` is always loaded, its size does matter — the template stays small by design: conventions as bullet points, not prose; a manifest reference rather than the full manifest inline; a preflight checklist rather than a full workflow.

**Codex CLI:** Because `AGENTS.md` is always loaded, its size matters directly. HITL's `codex/AGENTS.md` consolidates all workflow instructions into one document and is structured to be comprehensive without being redundant. There is no lazy-load path to fall back on, so the document must cover all roles and workflows while remaining focused enough that the startup cost stays reasonable.

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
