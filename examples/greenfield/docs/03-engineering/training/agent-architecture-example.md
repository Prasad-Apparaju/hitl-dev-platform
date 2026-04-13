# Agent Architecture — Training Plan (Example)

> **Status:** Complete
> **This is a worked example.** Adapt the structure to your project's agent framework.

After completing this plan, you will understand how agents are built in this system — from data structures through the execution loop to tool calling and self-evaluation.

**Audience:** Primary = dev team (build and maintain agents). Secondary = PM team (understand capabilities and limits).
**Estimated time:** 3–4 hours total
**Prerequisites:**
- Python async/await basics
- Familiarity with LLM API concepts (messages, tools, streaming)

---

## Module 1: Agent Data Structures (30 min)

### Goal
Understand the state objects that flow through every agent run.

### Reading
| File | What to focus on |
|------|-----------------|
| `app/agents/schemas.py` | `AgentState`, `ToolCall`, `ToolResult`, `EvalResult` — the core data types |
| `app/models/agent_run.py` | How agent state maps to the database (persistence) |

### Key Concepts

Every agent run is a state machine. The state object carries:
- **Input** — what the user asked for
- **Context** — what the agent knows (from memory, RAG, prior tool calls)
- **Tool calls** — what actions the agent has taken
- **Output** — what the agent produced
- **Eval scores** — how the agent rated its own output

Understanding these structures is prerequisite to everything else. Don't skip this module.

### Hands-on Exercise
1. Open `app/agents/schemas.py`
2. Trace `AgentState` through one agent run — add print statements or breakpoints
3. Run one agent with a test input and inspect the state at each step

### Checkpoint
1. What is the difference between `gathered_context` and `compressed_context`?
2. Where are tool call results stored in the state?
3. What happens to the state if the agent retries after a failed self-eval?

---

## Module 2: Base Agent Pipeline (45 min)

### Goal
Understand the standard agent execution loop that all agents inherit.

### Reading
| File | What to focus on |
|------|-----------------|
| `app/agents/base.py` | `BaseAgent.__init__`, `run()`, the state graph definition |
| LLD: `docs/02-design/technical/lld/agents/framework.md` | The pipeline diagram and node descriptions |

### Key Concepts

The BaseAgent defines a graph with these nodes:
1. **gather_context** — load memory, RAG results, brand context
2. **plan** (optional) — LLM produces an explicit plan before acting
3. **execute_tools** — LLM decides which tools to call (the agentic loop)
4. **evaluate** — LLM Judge scores the output
5. **retry or finish** — loop back if score < threshold, else return

Agents are NOT fixed pipelines. The LLM decides tool calls at step 3 — it may call zero tools, one tool, or many tools in sequence. This is what makes it agentic.

### Hands-on Exercise
1. Create a minimal agent that extends BaseAgent with one tool
2. Run it and trace the graph execution — which nodes execute, in what order?
3. Force a low eval score and observe the retry loop

### Checkpoint
1. How does a new agent declare which tools it has access to?
2. What is the maximum number of tool-call iterations before the agent stops?
3. Where is the retry feedback injected when the eval fails?

---

## Module 3: Tool Framework (45 min)

### Goal
Understand how tools work — both read-only and mutating.

### Reading
| File | What to focus on |
|------|-----------------|
| `app/agents/tools/base.py` | `BaseTool` and `MutatingTool` base classes |
| `app/agents/tools/` | 2-3 concrete tool implementations |
| Pattern doc: `docs/patterns/idempotency-keys.md` | Why mutating tools need idempotency |

### Key Concepts

Two kinds of tools:
- **Read-only tools** — search, retrieve, analyze. Can be called any number of times safely.
- **Mutating tools** — publish, send, charge. Produce external side effects. Require idempotency keys and plan-mode support.

Every MutatingTool must implement:
- `_describe_plan()` — returns a dry-run preview (used in PLAN mode to show the user what WOULD happen)
- `execute()` — the actual external call, guarded by idempotency check

### Hands-on Exercise
1. Write a read-only tool (e.g., a knowledge search tool)
2. Write a mutating tool with an idempotency key
3. Test the mutating tool: call it twice with the same key, verify the external call happens only once

### Checkpoint
1. What happens if a MutatingTool is called without an idempotency_key?
2. How does plan mode prevent external side effects?
3. Where is the side effect log checked — before or after the external call?

---

## Module 4: Self-Evaluation (30 min)

### Goal
Understand how agents assess their own output quality.

### Reading
| File | What to focus on |
|------|-----------------|
| `app/agents/eval.py` | `AgentEvaluator`, dimension scoring, threshold logic |
| Pattern doc: `docs/patterns/failure-mode-taxonomy.md` | How failures are categorized |

### Key Concepts

Self-eval is an LLM Judge that scores the agent's output on weighted dimensions. If the weighted average is below the threshold (default 0.7), the agent retries with feedback.

Dimensions are agent-specific. A content agent might score on: brief_understanding (0.3), brand_voice (0.3), creative_quality (0.2), factual_accuracy (0.2). A code agent might score on: requirement_coverage, convention_adherence, test_quality.

When a trace fails, the failure-mode classifier tags it with one category (e.g., "brand_voice") so the team can iterate directionally.

### Hands-on Exercise
1. Run an agent with a deliberately bad input that triggers a low eval score
2. Observe the retry: what feedback does the eval provide to the next iteration?
3. Check the trace in your observability tool — find the eval scores and failure mode tag

### Checkpoint
1. What is the difference between the eval score and the failure mode?
2. Who sets the dimension weights — code or configuration?
3. Can a PM change the eval criteria without a code deploy?

---

## Module 5: Memory and Context (30 min)

### Goal
Understand how agents remember across sessions and manage context size.

### Reading
| File | What to focus on |
|------|-----------------|
| `app/agents/base.py` | `_compress_context_view()`, memory processor chain |
| `app/services/rag.py` | How RAG search provides relevant context |

### Key Concepts

Agents have two kinds of memory:
- **Structured memory** — from the database (past runs, user preferences, entity data)
- **Unstructured memory** — from vector search (documents, past conversations, patterns)

The `memory_processor` chain compresses gathered context before each LLM call to stay within the token budget. The original state is preserved for the replay log.

### Hands-on Exercise
1. Run an agent twice with related inputs — does the second run use context from the first?
2. Inspect the gathered_context vs. compressed_context — what was removed?

### Checkpoint
1. Where does cross-session memory come from?
2. Why is the original context preserved even after compression?
3. How does the agent decide what to retrieve from vector search?

---

## Summary

| You now understand | Evidence |
|-------------------|----------|
| Agent state flow | Module 1 — traced AgentState through a run |
| Execution loop | Module 2 — built a minimal agent, observed retry |
| Tool system | Module 3 — built both read-only and mutating tools |
| Self-evaluation | Module 4 — triggered and observed the eval/retry loop |
| Memory and context | Module 5 — compared gathered vs. compressed context |

## Next Steps
- Build your first real agent using the framework
- Study the failure-mode taxonomy for your agent's specific failure modes
- Review the agent maturity levels pattern to understand L0 → L3 progression

## Related
- `docs/02-design/technical/lld/agents/framework.md` — the full LLD
- `docs/patterns/failure-mode-taxonomy.md` — per-agent failure classification
- `docs/patterns/idempotency-keys.md` — exactly-once external side effects
