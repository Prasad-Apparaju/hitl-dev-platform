# Codex — Context Injection Mental Map

How the visible pieces get into Codex context when a session starts and as work continues.

This version reflects the **Codex app session model**: host-provided instructions up front, then file/tool/plugin context added as the session evolves.

## Diagram

### Overview

```mermaid
sequenceDiagram
    participant User
    participant Host as Codex Host App
    participant Agent as Codex Agent
    participant Tool as Tools / Plugins / Apps
    participant Ctx as Context Window

    Note over User,Ctx: LEGEND — 🔴 Enforced (host-controlled) · 🔵 Predictable when enabled or requested · 🟢 Optional / trigger-based · 🟡 Best treated as implementation detail

    rect rgb(220, 230, 255)
        Note over User,Ctx: PHASE 1 — Session Init
        User->>Host: 🔴 open trusted project / start session
        Host->>Agent: 🔴 inject system prompt, developer instructions, tool schemas, plugin/skill catalog, environment block
        Host->>Ctx: 🔴 startup context assembled (expand Phase 1 below for detail)
    end

    rect rgb(220, 255, 230)
        Note over User,Ctx: PHASE 2 — During Session
        User->>Ctx: 🔴 messages accumulate continuously
        Note over Ctx: 🟢 files open · skills load on use · tools execute · web/app data arrives · sub-agent outputs return
    end
```

---

<details>
<summary><strong>Phase 1 — Session Init (detail)</strong></summary>

```mermaid
sequenceDiagram
    participant User
    participant Host as Codex Host App
    participant Agent as Codex Agent
    participant Skill as Skills / Plugins
    participant Ctx as Context Window

    User->>Host: 🔴 start Codex session

    rect rgb(220, 230, 255)
        Note over Host,Skill: 🔴 The host prepares the instruction envelope before the agent starts working
        Host->>Agent: 🔴 1. system instructions
        Host->>Agent: 🔴 2. developer instructions (tool rules, formatting, coding constraints)
        Host->>Agent: 🔴 3. tool definitions + permissions
        Host->>Agent: 🔵 4. available skills list + plugin descriptions
        Host->>Agent: 🔵 5. app/plugin availability
        Host->>Agent: 🔵 6. environment block (cwd, shell, date, timezone)
        Host->>Agent: 🔵 7. prior thread history (if continuing)
    end

    rect rgb(220, 230, 255)
        Note over Agent,Ctx: 🟡 The visible structure is stable for users, but exact internal assembly is still best treated as implementation detail
        Agent->>Ctx: 🔴 instruction envelope available from turn start
    end

    Note over Ctx: Unlike Claude Code, this model is not primarily explained through auto-loaded project memory files
```

</details>

<details>
<summary><strong>Phase 2 — During Session (detail)</strong></summary>

```mermaid
sequenceDiagram
    participant User
    participant Agent as Codex Agent
    participant Files as Local Files
    participant Tool as Tools / Plugins / Apps
    participant Sub as Sub-agents
    participant Ctx as Context Window

    User->>Ctx: 🔴 user message appended
    Ctx-->>Ctx: 🔴 conversation history accumulates continuously

    rect rgb(220, 255, 230)
        Note over User,Files: 🟢 Trigger: agent decides it needs local project context
        Agent->>Files: open/read file
        Files-->>Agent: file contents
        Agent->>Ctx: 🔴 file contents or summary appended
    end

    rect rgb(220, 255, 230)
        Note over User,Tool: 🟢 Trigger: user names a skill or the task matches a skill
        Agent->>Tool: load relevant SKILL.md instructions
        Tool-->>Agent: skill body / references
        Agent->>Ctx: 🔵 skill guidance becomes active for the turn
    end

    rect rgb(220, 255, 230)
        Note over Agent,Tool: 🟢 Trigger: tool execution
        Agent->>Tool: shell / patch / web / browser / image / app call
        Tool-->>Agent: tool result
        Agent->>Ctx: 🔴 result summary or raw output appended
    end

    rect rgb(220, 255, 230)
        Note over Agent,Sub: 🟢 Trigger: delegated parallel work
        Agent->>Sub: spawn task
        Sub-->>Agent: result summary / changed files / findings
        Agent->>Ctx: 🔴 sub-agent output appended
    end

    rect rgb(220, 255, 230)
        Note over Agent,Ctx: 🟢 Trigger: web or app inspection
        Agent->>Tool: fetch page / inspect app / read connector data
        Tool-->>Agent: page content / app state / metadata
        Agent->>Ctx: 🔴 fetched content summarized or quoted
    end

    Note over Ctx: 🔴 Context pressure grows mainly from messages, file reads, command output, fetched content, and sub-agent results
```

</details>

---

## Zone Breakdown

### Blue — Present From Startup

Available from the beginning of the session.

| Source | Typical contents | Confidence |
|---|---|---|
| System instructions | Global behavior rules | Documented by visible session structure |
| Developer instructions | Coding, tool, formatting, review, and workflow rules | Documented by visible session structure |
| Tool definitions | Schemas, permission model, tool availability | Documented by visible session structure |
| Skill / plugin catalog | Skill names, descriptions, plugin availability | Documented by visible session structure |
| Environment block | cwd, shell, date, timezone | Documented by visible session structure |
| Thread history | Prior turns in the same conversation | Observed |

### Green — Loaded On Demand

Only enters context when a trigger happens.

| Trigger | What loads |
|---|---|
| Opening a file | File contents |
| Using a skill | `SKILL.md` instructions and referenced guidance |
| Running a tool | Tool result |
| Browsing the web or an app | Retrieved page/app state |
| Spawning a sub-agent | Sub-agent results |
| Viewing an image or document | Extracted visual/document content |

### Red — Grows During Session

This is usually what makes the context window feel full.

| Source | Notes |
|---|---|
| Conversation turns | Every user and assistant message |
| Terminal output | Can grow fast if commands are noisy |
| File reads | Large files add a lot of weight |
| Web/app fetches | Pages and fetched content can be bulky |
| Sub-agent results | Helpful, but they stack up |

## Key Insight

For Codex, the startup context is important, but most context pressure still comes from the growing session layer.

The biggest wins usually come from:

1. **Keeping tool output tight**
2. **Reading only the files needed for the task**
3. **Starting a fresh thread for unrelated work**
4. **Using summaries instead of repeatedly pasting raw logs**

## Important Difference From Claude Code

Claude Code is often explained through auto-loaded project memory such as `CLAUDE.md`, memory files, hooks, and slash-command content.

Codex is better understood as:

1. **Host-injected instruction envelope first**
2. **Tool/file/skill loading second**
3. **Session accumulation third**

That makes Codex feel more like a controlled agent runtime than a project-memory-first shell.

## Accuracy Note

This map is meant as a practical mental model, not an internal product spec.

- The visible startup envelope is well supported by what Codex exposes in-session.
- The on-demand loading behavior for files, skills, tools, web content, and sub-agents is directly observable.
- Exact hidden assembly order inside the host should still be treated as implementation detail, not a guaranteed contract.
