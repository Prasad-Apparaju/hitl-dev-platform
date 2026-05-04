# Claude Code — Context Injection Mental Map

How all the pieces get loaded into context when you start a Claude Code session.

> **Confidence framing:** This map is a practical mental model, not a formal internal spec. Items marked 🔴 reflect documented or consistently enforced behavior. Items marked 🔵 are predictable in practice and directly observable. Claims about internal mechanics — concurrent read ordering, exact assembly sequence, binary file locations, and token size estimates — are informed inference from observed behavior and should be treated as directional, not authoritative. The three-zone model (always loaded / lazy loaded / session growth) is the part most worth relying on.

## Diagram

### Overview

```mermaid
sequenceDiagram
    participant User
    participant JS as JS Thread (Bun)
    participant OS as OS / libuv
    participant Ctx as Context Window

    Note over User,Ctx: LEGEND — 🔴 Enforced (Anthropic-controlled) · 🔵 Guaranteed (predictable when condition exists) · 🟢 Optional (explicit action or config required)

    rect rgb(220, 230, 255)
        Note over User,Ctx: PHASE 1 — Session Init
        User->>JS: 🔴 claude (start session)
        JS->>OS: 🔵 concurrent async reads (system prompt, CLAUDE.md files, MEMORY.md, skills, hooks config, MCP tool names)
        OS-->>JS: results arrive (order not guaranteed)
        JS->>Ctx: 🔴 assembled in fixed priority order (expand Phase 1 below for detail)
    end

    rect rgb(220, 255, 230)
        Note over User,Ctx: PHASE 2 — During Session
        User->>Ctx: 🔴 messages accumulate continuously
        Note over Ctx: 🟢 hooks fire · skills lazy-load · tools execute · compaction auto-fires (expand Phase 2 below for detail)
    end
```

---

<details>
<summary><strong>Phase 1 — Session Init (detail)</strong></summary>

```mermaid
sequenceDiagram
    participant User
    participant JS as JS Thread (Bun)
    participant OS as OS / libuv
    participant MCP as MCP Servers
    participant Ctx as Context Window

    User->>JS: 🔴 claude (start session)

    rect rgb(220, 230, 255)
        Note over JS,MCP: 🔵 JS issues all reads concurrently without blocking
        JS->>OS: 🔴 async read — base system prompt (binary)
        JS->>OS: 🔵 async read — ~/.ai/claude/CLAUDE.md
        JS->>OS: 🔵 async read — project CLAUDE.md (cascaded from cwd upward)
        JS->>OS: 🔵 async read — MEMORY.md (if exists for cwd)
        JS->>OS: 🔵 async read — plugin skill descriptions (enabled plugins)
        JS->>OS: 🔵 async read — hooks config from settings.json
        JS->>MCP: 🔵 async — enumerate registered tool names
    end

    OS-->>JS: results arrive (order not guaranteed)
    MCP-->>JS: tool names arrive

    rect rgb(220, 230, 255)
        Note over JS,Ctx: 🔵 Assembly in fixed priority order — no conflict detection
        JS->>Ctx: 🔴 1. base system prompt (Anthropic — highest authority)
        JS->>Ctx: 🔵 2. global CLAUDE.md (~/.ai/claude/CLAUDE.md)
        JS->>Ctx: 🔵 3. parent CLAUDE.md (cascaded upward from cwd)
        JS->>Ctx: 🔵 4. project CLAUDE.md (.ai/claude/CLAUDE.md in cwd)
        JS->>Ctx: 🔵 5. MEMORY.md
        JS->>Ctx: 🔵 6. skill descriptions + deferred tool names + date/email/model
    end

    Note over Ctx: Conflicts NOT detected — model resolves by judgment (more specific beats general)
```

</details>

<details>
<summary><strong>Phase 2 — During Session (detail)</strong></summary>

```mermaid
sequenceDiagram
    participant User
    participant Hook as Hooks (OS processes)
    participant JS as JS Thread (Bun)
    participant OS as OS / libuv
    participant MCP as MCP Servers
    participant Ctx as Context Window

    rect rgb(220, 230, 255)
        Note over User,Hook: 🔵 Fires on every message if configured
        User->>Hook: 🔵 UserPromptSubmit hook
        Hook-->>JS: hook output injected into prompt context
    end

    User->>Ctx: 🔴 message appended — conversation begins
    Ctx-->>Ctx: 🔴 conversation history accumulates continuously

    rect rgb(220, 255, 230)
        Note over JS,Ctx: 🟢 Trigger: user explicitly types a skill command (e.g. /commit — git only)
        User->>JS: /commit
        JS->>OS: async read — commit.md (~5KB)
        OS-->>Ctx: skill content appended
    end

    rect rgb(220, 255, 230)
        Note over JS,Ctx: 🟢 Trigger: model judges memory file relevant (model judgment — not guaranteed)
        JS->>OS: async read — feedback_dev_workflow.md (~2KB)
        OS-->>Ctx: memory detail appended
    end

    rect rgb(220, 255, 230)
        Note over JS,Ctx: 🟢 Trigger: model decides to call a tool (Bash / Read / Edit / Write)
        JS->>Hook: 🔵 PreToolUse hook — can block tool (non-zero exit cancels call)
        Hook-->>JS: approved (exit 0) or blocked (non-zero)
        JS->>OS: 🔵 tool executes
        OS-->>JS: tool result
        JS->>Hook: 🔵 PostToolUse hook
        Hook-->>JS: hook output
        JS-->>Ctx: 🔴 tool result appended (accumulates)
    end

    rect rgb(220, 255, 230)
        Note over JS,Ctx: 🟢 Trigger: first use of an MCP tool
        JS->>Hook: 🔵 PreToolUse hook — can block
        Hook-->>JS: approved or blocked
        JS->>MCP: tool call
        MCP-->>JS: tool result
        JS->>Hook: 🔵 PostToolUse hook
        JS-->>Ctx: 🔴 tool result appended (accumulates)
    end

    rect rgb(220, 255, 230)
        Note over JS,Hook: 🟢 Trigger: Claude finishes a response
        JS->>Hook: 🔵 Stop hook — side effects only (Slack alert, session log etc.)
        Hook-->>JS: hook output
    end

    Note over Ctx: 🔴 Compaction fires automatically when context window fills
```

</details>

---

## Zone Breakdown

### Blue — Always Loaded (fixed cost per session)

Paid on every session regardless of what you do.

| Source | File / Location | Size (order of magnitude — treat as directional) |
|---|---|---|
| Base system prompt | Binary (`~/.local/bin/claude`) | ~6–8K tokens |
| Global instructions | `~/.ai/claude/CLAUDE.md` | ~0.5KB |
| Project instructions | `<project>/.ai/claude/CLAUDE.md` or parent `CLAUDE.md` | ~4KB |
| Project memory index | `~/.ai/claude/projects/<slug>/memory/MEMORY.md` | 0–7KB |
| Skills list | Descriptions from enabled plugin `SKILL.md` frontmatter | ~4KB |
| Deferred tools list | Tool names from MCP servers + harness | ~2–3KB |
| System injections | Date, user email, model info | ~0.1KB |

**Rough fixed cost: ~12–25K tokens per session** _(observed range — not a guarantee)_

---

### Green — Lazy Loaded (pay only when triggered)

| Trigger | What loads | Size |
|---|---|---|
| `/skill-name` typed | Full `SKILL.md` content | 5–32KB each |
| I judge memory relevant | Individual `feedback_*.md`, `project_*.md` | 1–3KB each |
| First use of an MCP tool | Tool schema via `ToolSearch` | 1–5KB |
| `Read` tool call | File contents | varies |
| Slash command run | Command `.md` file | 2–10KB |

---

### Red — Grows During Session

Every message, tool call, and result accumulates and never shrinks until compaction.

| Source | Notes |
|---|---|
| Conversation turns | Every user + assistant message |
| Tool results | Bash output, file reads, web fetches — can be large |
| Sub-agent outputs | Agent tool results returned to main context |

This is where long sessions balloon. Large file reads, verbose bash output, and agent results stack up fast. Compaction kicks in automatically when context gets large.

---

## Key Insight

The always-loaded blue zone is largely fixed and small. Real context pressure comes from the red zone growing during a session. Disabling unused plugins trims a few lines from the skills list, but the bigger wins are:

1. **Keeping tool results lean** — avoid reading large files unnecessarily
2. **Disabling MCP servers you don't use** — removes tool names from the deferred list and prevents schema loads
3. **Disabling unused plugins** — removes skill entries from the always-loaded list
4. **Starting fresh sessions** for unrelated tasks — avoids carrying red zone weight forward

## Files Referenced

| Path | Purpose |
|---|---|
| `~/.local/bin/claude` | Claude Code binary (base prompt baked in) |
| `~/.ai/claude/settings.json` | Plugin enable/disable, theme, env vars, status line |
| `~/.ai/claude/CLAUDE.md` | Global instructions (all projects) |
| `~/.ai/claude/plugins/cache/` | Cached plugin skill files |
| `~/.ai/claude/projects/<slug>/memory/` | Per-project persistent memory |
| `<project>/.ai/claude/settings.json` | Project-local overrides |
| `<project>/CLAUDE.md` | Project-specific instructions |
