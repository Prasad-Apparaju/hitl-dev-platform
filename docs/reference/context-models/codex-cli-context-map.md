# Codex CLI — Context Injection Mental Map

How the main visible pieces get into **Codex CLI** context when a session starts and as work continues.

This version is for the **Codex CLI + local repo configuration** model, where repo files such as `AGENTS.md` and `.codex/config.toml` matter much more than host-app session scaffolding.

## Diagram

### Overview

```mermaid
sequenceDiagram
    participant User
    participant CLI as Codex CLI
    participant FS as Local Filesystem
    participant Hook as Lifecycle / Git Hooks
    participant Ctx as Context Window

    Note over User,Ctx: LEGEND — 🔴 Enforced or auto-loaded · 🔵 Predictable when configured · 🟢 Optional / trigger-based · 🟡 Best treated as implementation detail

    rect rgb(220, 230, 255)
        Note over User,Ctx: PHASE 1 — Session Init
        User->>CLI: 🔴 start Codex in a project directory
        CLI->>FS: 🔵 read local config and instruction files
        FS-->>CLI: config, AGENTS.md, environment context
        CLI->>Ctx: 🔴 startup context assembled (expand Phase 1 below for detail)
    end

    rect rgb(220, 255, 230)
        Note over User,Ctx: PHASE 2 — During Session
        User->>Ctx: 🔴 messages accumulate continuously
        Note over Ctx: 🟢 files open · tools run · hooks may fire · commit-time git hooks validate
    end
```

---

<details>
<summary><strong>Phase 1 — Session Init (detail)</strong></summary>

```mermaid
sequenceDiagram
    participant User
    participant CLI as Codex CLI
    participant FS as Local Filesystem
    participant Ctx as Context Window

    User->>CLI: 🔴 codex

    rect rgb(220, 230, 255)
        Note over CLI,FS: 🔵 CLI loads repo-local guidance and runtime config
        CLI->>FS: 🔴 read system/runtime defaults
        CLI->>FS: 🔵 read `AGENTS.md` from repo root (if present)
        CLI->>FS: 🔵 read `.codex/config.toml` or user config (if present)
        CLI->>FS: 🔵 read `.codex/hooks.json` when hooks are enabled
        CLI->>FS: 🔵 capture cwd, shell, date, trust, and other environment state
    end

    FS-->>CLI: results returned

    rect rgb(220, 230, 255)
        Note over CLI,Ctx: 🟡 Exact assembly order is implementation detail, but the effective startup envelope is stable enough to reason about
        CLI->>Ctx: 🔴 base instructions
        CLI->>Ctx: 🔵 local repo instructions from `AGENTS.md`
        CLI->>Ctx: 🔵 config-driven behavior from `.codex/config.toml`
        CLI->>Ctx: 🔵 enabled hook definitions and tool permissions
        CLI->>Ctx: 🔵 current environment block
    end

    Note over Ctx: This model is much more repo-local than the Codex app session model
```

</details>

<details>
<summary><strong>Phase 2 — During Session (detail)</strong></summary>

```mermaid
sequenceDiagram
    participant User
    participant CLI as Codex CLI
    participant Hook as Lifecycle / Git Hooks
    participant FS as Local Filesystem
    participant Tool as Tools / Web / Helpers
    participant Ctx as Context Window

    User->>Ctx: 🔴 user message appended
    Ctx-->>Ctx: 🔴 conversation history accumulates continuously

    rect rgb(220, 255, 230)
        Note over CLI,FS: 🟢 Trigger: CLI needs project context
        CLI->>FS: open/read source or docs
        FS-->>CLI: file contents
        CLI->>Ctx: 🔴 file contents or summary appended
    end

    rect rgb(220, 255, 230)
        Note over CLI,Hook: 🔵 Trigger: tool call when lifecycle hooks are enabled
        CLI->>Hook: pre-tool hook
        Hook-->>CLI: approve / block / annotate
        CLI->>Tool: run tool
        Tool-->>CLI: tool result
        CLI->>Hook: post-tool hook
        Hook-->>CLI: follow-up output
        CLI->>Ctx: 🔴 tool result and any hook output appended
    end

    rect rgb(220, 255, 230)
        Note over CLI,Tool: 🟢 Trigger: web lookup or external data access
        CLI->>Tool: fetch/search/query
        Tool-->>CLI: fetched data
        CLI->>Ctx: 🔴 fetched content summarized or quoted
    end

    rect rgb(220, 255, 230)
        Note over User,Hook: 🔵 Trigger: commit
        User->>Hook: git commit
        Hook->>FS: inspect staged files + `.hitl/current-change.yaml`
        FS-->>Hook: staged diff + HITL metadata
        Hook-->>User: allow commit or block with remediation
    end

    Note over Ctx: 🔴 Context pressure grows mainly from conversation, file reads, tool output, and fetched content
```

</details>

---

## Zone Breakdown

### Blue — Present From Startup

Available at the beginning of the session.

| Source | Typical contents | Confidence |
|---|---|---|
| Base runtime instructions | Global CLI/runtime behavior | Partly visible, partly implementation detail |
| `AGENTS.md` | Repo-local workflow, standards, conventions | Directly observable |
| `.codex/config.toml` | model, approval, sandbox, features, hooks enablement | Directly observable |
| `.codex/hooks.json` | lifecycle hook wiring when enabled | Directly observable |
| Environment block | cwd, shell, date, trust, runtime context | Directly observable |

### Green — Loaded On Demand

Only enters context when triggered.

| Trigger | What loads |
|---|---|
| Reading project files | file contents |
| Running a tool | tool result |
| Using web/search capabilities | fetched content |
| Hook execution | hook output |
| Committing changes | git-hook diagnostics and validation output |

### Red — Grows During Session

This is usually what makes the session heavy.

| Source | Notes |
|---|---|
| Conversation turns | Every user and assistant message |
| File reads | Source files, docs, logs, configs |
| Tool results | Shell output, search results, web responses |
| Hook output | Usually small, but can add up |

## Key Insight

For Codex CLI, the most important startup artifact is usually **`AGENTS.md` plus local `.codex` configuration**.

The biggest wins usually come from:

1. **Keeping `AGENTS.md` sharp and focused**
2. **Using hooks to enforce behavior instead of relying on memory**
3. **Reading only the files needed for the current task**
4. **Starting a fresh session when the task changes materially**

## Important Difference From The Codex App Model

The Codex app model is best explained as a host-injected instruction envelope.

Codex CLI is better explained as:

1. **CLI/runtime defaults**
2. **Repo-local instructions from `AGENTS.md`**
3. **Local `.codex` config and optional hooks**
4. **Session growth from files, tools, and conversation**

That makes Codex CLI feel more like a configurable local harness than a pre-orchestrated host environment.

## Accuracy Note

This map is meant as a practical mental model, not a formal internal spec.

- The role of `AGENTS.md`, `.codex/config.toml`, hooks, and git-hook enforcement is directly observable in real setups.
- File reads, tool output, and conversation growth are directly observable.
- Exact low-level startup ordering inside the CLI should still be treated as implementation detail.
