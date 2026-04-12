
# HITL AI-Driven Development

## What this is

A development process for teams using AI to generate code, tests, and documentation. AI produces code faster than teams can review it — and does so confidently even when wrong. This process makes that speed safe by organizing the team around documentation as the shared source of truth. AI generates; humans shape, review, and decide.

**Your job changes from producing artifacts to shaping them.** You tell AI what you need. AI drafts it. You iterate — refine, challenge, steer — until it reflects exactly what should happen. That skill is more valuable than typing code from scratch.

**This process works for any system** — REST APIs, data pipelines, agentic AI, frontend apps, infrastructure. "AI-driven" refers to how the team develops (using AI to generate code, tests, and docs), not what they're building. The system under development does not need to contain agents or LLMs.

**Yes, this looks like waterfall.** Design before code. That is intentional. Waterfall failed because the gap between "design done" and "working software" was months. With AI, that gap is minutes. You get waterfall's rigor (coherent design, traced decisions) without the wait. And it turns out AI is exceptionally good at reading precise documentation and generating code that follows it — which makes document-driven development a natural fit for how AI works. Without this discipline, AI-generated code drifts — each session invents its own patterns, and by the time you have customers, you face a rewrite that is orders of magnitude harder than designing coherently from the start.

## What you get by adopting this

| Outcome | How |
|---------|-----|
| **Every piece of code traces back to a reviewed decision** | Issue → design PR → LLD → code → tests → traceability check at integration verification |
| **AI generates code that matches what the team agreed** | LLD is the spec AI executes. Convention checker + TDD + two-round review enforce compliance. |
| **New team members onboard from docs, not from "ask the senior dev"** | HLDs, LLDs, ADRs, and the system manifest ARE the onboarding material |
| **You can change any part of the system without breaking other parts** | System manifest scopes each domain. Facade APIs define the contracts between them. |
| **QA and Ops are never surprised by a deployment** | Downstream impact brief communicates what changed. Canary criteria come from the incident registry. |
| **Past mistakes don't repeat** | Test registry and incident registry capture every lesson. Impact analysis queries them before every change. |
| **You know whether a technical investment paid off** | ROI estimation at the start, 30/90-day verification after. Actual outcomes documented in the ADR. |
| **The system doesn't need a rewrite as it scales** | Coherent from the start because every AI session follows the same conventions and domain boundaries |

## The Core Idea

Design decisions are discussed as a team — PM, Architect, Developers, QA, Ops, and AI — in a shared thread. Once a decision is finalized, it is captured in documentation: HLDs for architecture, LLDs for component design, ADRs for trade-offs, and a System Manifest for domain boundaries. From that point forward, **all downstream activities — code generation, testing, code review, deployment planning, and ROI verification — are driven off that documentation.** The documentation is not a record of what was built. It is the specification that drives what gets built.

This inverts the traditional relationship between docs and code. Write documentation first — with AI's help, in minutes rather than weeks — and generate the code from it. When the code diverges from the docs, update the docs to match, not the other way around. Any developer (or AI session) can then pick up any part of the system, read the docs, and produce correct, convention-honoring code — because the docs capture not just *what* the system does, but *why* it does it that way, *what alternatives were considered*, and *what conventions must be followed*.

![Team Collaboration — How PM, Architect, Developers, QA, Ops, and Claude work together](docs/images/team-collaboration.png)

> **[Download editable PowerPoint version](docs/hitl-team-collaboration.pptx)** — 4 slides covering team collaboration, the 22-step workflow, and the three boundaries.

<details open>
<summary>View as Mermaid diagram (text-based, copy-pasteable)</summary>

```mermaid
graph TD
    subgraph Slack["💬 Slack — where humans discuss"]
        direction LR
        PM["👤 PM"]
        Arch["👤 Architect"]
        D1["👤 Dev 1"]
        D2["👤 Dev 2"]
        QA["👤 QA"]
        Ops["👤 Ops"]
        Bot["🤖 @claude-bot"]
    end

    subgraph Private["🔮 Personal Claude — talks to GitHub only"]
        direction LR
        C1["🤖 Dev 1 Claude Code"]
        C2["🤖 Dev 2 Claude Code"]
    end

    subgraph GitHub["📂 GitHub — source of truth"]
        direction LR
        Docs["📝 HLDs + LLDs + ADRs + Manifest"]
        Code["💻 Code + Tests"]
        IaC["🏗️ IaC: Terraform, K8s"]
        PRs["🔀 PRs = Decision Gates"]
        Reg["🧪 Test + Incident Registries"]
    end

    subgraph Dev["🛠️ Dev environment — Dev owns"]
        direction LR
        DevK8s["⚙️ Dev cluster"]
        DevDB["🗄️ Dev database"]
    end

    subgraph Prod["☁️ Production — Ops owns"]
        direction LR
        Mgmt["🖥️ Management Server"]
        GKE["⚙️ Prod cluster"]
        GCS["📦 Storage"]
    end

    PM & Arch & D1 & D2 & QA & Ops -->|"discuss"| Bot
    Bot -->|"writes decisions"| GitHub
    C1 & C2 -->|"read + write"| GitHub
    GitHub -->|"context"| Slack
    QA -->|"test scenarios"| Reg
    Ops -->|"canary criteria"| Reg
    IaC -->|"Dev deploys"| Dev
    IaC -->|"Ops deploys + refactors"| Prod
    Code -->|"CI/CD"| Dev
    Code -->|"CI/CD"| GKE
    Mgmt --> GKE
    GKE --> GCS

    style Slack fill:#fef3c7,stroke:#d97706,color:#1e293b
    style Private fill:#f3e8ff,stroke:#9333ea,color:#1e293b
    style GitHub fill:#f0fdf4,stroke:#16a34a,color:#1e293b
    style Dev fill:#fff3e0,stroke:#e65100,color:#1e293b
    style Prod fill:#dbeafe,stroke:#2563eb,color:#1e293b
```

</details>

---

## 1. The Problem This Solves

The goal is a **coherent, traceable implementation** where:

- The team **critically reviews requirements** before anyone writes or generates code
- Design decisions are **thought through, discussed, and agreed** — not invented by individual AI sessions
- Every piece of code **traces back to a reviewed design decision** — requirement → design → code → test → deployment
- The team **communicates important decisions** to each other and to downstream stakeholders (PM, ops, QA)
- **Everything is documented** — not as an afterthought, but as the specification that drives what gets built
- AI generates code that **conforms to what the team agreed and documented** — it implements decisions, it does not make them

Without this discipline, AI code generation amplifies problems instead of solving them:

| What goes wrong | Why it happens | What it costs |
|----------------|---------------|---------------|
| **Incoherent codebase** — three error handling strategies, two naming conventions, inconsistent patterns | Each developer's AI session invents its own approach. No shared specification constrains the output. | Rework. Every new feature must untangle which pattern to follow. |
| **Untraceable decisions** — "why does this work this way?" has no answer | Design decisions live in ephemeral AI chat transcripts, not in reviewed documents. | Debugging takes 10x longer. New team members can't understand the system. |
| **AI invents instead of implementing** — plausible but wrong code that compiles and passes naive tests | AI was given a vague instruction ("implement publishing") instead of a precise spec. It filled the gaps with hallucinated assumptions. | Bugs surface in integration, not in unit tests. The fix requires re-examining the design. |
| **Decisions don't reach stakeholders** — PM promises features that don't exist, ops deploys without knowing the failure modes | No formal step for communicating what changed, what can break, and how the team's mental model needs to update. | Organizational confusion. Support troubleshoots based on stale assumptions. |

These problems exist in traditional development too, but AI amplifies them because of the sheer volume of code it produces.

### 1.1 How this process addresses each goal

| Goal | How the process achieves it | Where in the workflow |
|------|----------------------------|----------------------|
| **Coherent implementation** | System manifest defines domain boundaries and conventions. CLAUDE.md inlines the rules into every AI session. Convention checker enforces in CI. | Manifest (pre-work), CLAUDE.md (every session), CI (every PR) |
| **Critical review of requirements** | Design PR must merge before code starts. Team reviews HLD/LLD in PR comments. No code generation until design is locked. | Steps 3-5 (design phase), Design PR gate |
| **Decisions thought through** | HLD captures architecture. LLD captures component design. ADRs capture trade-offs and alternatives. TDD tests reveal spec gaps before code exists. | Steps 3, 5 (docs), Steps 6-8 (TDD-as-design) |
| **Traceability** | Issue → design PR → impl PR → traceability check. Lead verifies the chain is unbroken at integration verification. | Step 1 (issue), Step 20 (lead verification) |
| **Team communication** | Downstream impact brief tells PM, QA, and ops what changed. PM mental model update section ensures product team stays current. | Steps 18-19 (assess phase) |
| **Institutional memory** | Test registry catalogs every test by domain, risk, and origin. Incident registry connects past failures to regression tests and canary criteria. Both are queryable during impact analysis so the team doesn't repeat past mistakes. | Step 2 (impact analysis), Step 7 (TDD review), Step 19 (rollout plan), post-incident |
| **QA + Ops without bottlenecks** | QA and Ops contribute to specs (design time) and monitoring (canary time), not to gates (merge time). Their past inputs live in the registries — available even when the individuals are not. | Design PR review, TDD review (step 7), rollout plan (step 19), canary monitoring |
| **Everything documented** | Docs written before code (steps 3-5). Reconciled after code if implementation diverged (step 16). Updated in every PR. | Steps 3-5 (before), Step 16 (after), every PR |
| **AI conforms to agreements** | Tests written first define expected behavior. Convention checker verifies compliance. Two-round code review checks LLD adherence. | Steps 6-8 (TDD), Steps 13-14 (review), CI |

### 1.2 Why documentation first

```mermaid
graph LR
    subgraph Traditional["Traditional"]
        direction TB
        T1["Requirements change"] --> T2["Rewrite code"] --> T3["Maybe update docs"]
    end

    Traditional ~~~ AINative

    subgraph AINative["HITL AI-Driven"]
        direction TB
        A1["Requirements change"] --> A2["Update docs"] --> A3["Generate code"] --> A4["Human review"]
    end

    style Traditional fill:#f5f5f5,stroke:#9e9e9e
    style AINative fill:#e8f5e9,stroke:#2e7d32
```

Treat the LLD as a spec, not a narrative: precise interfaces, explicit edge cases, exact method signatures. Vague prose produces vague code.

**Known limitation:** this works best when the domain and framework are well-understood. For exploratory work, see the Unknown (PoC) phase in Section 5.

---

## 2. Role Definitions

Every role shifts from "produce artifacts" to "review and decide." You are a reviewer and decision-maker, not a typist. If you are typing more than a few sentences of correction, let AI draft; you steer.

| Role | In Dev | After handoff to QA/Prod |
|------|--------|------------------------|
| **PM** | Defines requirements. Reviews AI-drafted PRDs. | Reviews demo. Accepts or requests changes. |
| **Architect** | Designs, reviews, gates PRs. Verifies traceability. | Available if QA/Ops need design clarification. |
| **Developer** | Owns everything in dev: code, tests, IaC, docs, QA-level testing, infra setup. Builds until the change is stable enough to hand off. | Pulled in by QA/Ops as needed for fixes. Retroactively applies Ops IaC refinements back to dev. |
| **QA** | Contributes test scenarios from incident registry to the dev test plan (non-blocking input). | Takes the handoff. Runs independent quality verification. Can block promotion if criteria not met. |
| **Ops** | Contributes canary criteria from incident registry (non-blocking input). | Takes the handoff. Refactors baseline IaC Dev provides. Monitors + promotes to production. Can block if system not stable. |
| **Claude** | Drafts docs, generates code + tests, reviews PRs, monitors metrics. Proposes, never decides. | Reports canary metrics. Available to QA/Ops for analysis. |

**The model:** Dev is empowered to do everything in dev — including QA-level testing and Ops-level IaC. Once the build is stable, Dev hands off with evidence (test registry results, impact brief, rollout plan). QA and Ops take it from there independently and pull Dev in as needed. Ops may refactor the IaC Dev provided; Dev retroactively applies those refinements back to the dev environment.

| Common practice | With this process |
|-----------|----------------|
| Write docs by hand | AI writes all docs. You review, correct, approve. |
| Start coding, figure it out as you go | Tell AI what you need. AI drafts the LLD. You review. Iterate with AI — refine, add detail, challenge assumptions — until the doc reflects exactly what should happen. Only then does AI generate code from it. |
| Docs after the feature ships | Docs first. AI drafts them in minutes. You spend time thinking, not typing. |
| One developer owns a feature end-to-end | The *doc* owns the feature. Any developer (or AI session) can pick it up. |

### 2.1 The Dev Lead's Integration Verification

The lead's final verification step exists because AI code review, even in two rounds, catches *mechanical* issues but misses *intent* issues. Run the feature end-to-end and ask: "Does this actually do what the design said it would?" Check traceability: requirement, design, IaC, code, tests — is the chain unbroken? This catches the cases where each individual piece is correct but the whole does not match the intent.

### 2.2 Vertical Ownership

Every developer owns a full vertical slice — not "the frontend part" or "the backend part." If you are building the monitoring feature, you own the doc, the backend endpoint, the frontend component, the tests, and the bugs. When one person owns the full slice, there is no "it works on my side" across teams. AI helps you move fast across layers you are less familiar with; teammates help with review.

---

## 3. Scaling AI Context: The System Manifest

### 3.1 Problem

The process works well when the system is small. A single AI session can hold the full context — all the docs, all the code, all the patterns — and produce correct output. But systems grow. At 50+ source modules, 33 LLDs, 14 HLDs, 55 architectural decisions, and 300+ tests, no single context window can hold all of it productively. Even if it could, most of the content is noise for any given task.

The two failure modes from Section 1 reappear at scale:
- **Agent reads too much** — hallucinated connections between unrelated modules, changes outside its scope.
- **Agent reads too little** — violated conventions it did not know about, produced interfaces that did not match what other parts of the system expected.

### 3.2 Solution: Hierarchical Knowledge Architecture

Conway's Law (1967): "The structure of a system mirrors the communication structure of the organization that builds it." Applied to AI: **design the knowledge boundaries explicitly, and the quality of agent output mirrors those boundaries.** Scoped agents with clean facades produce modular, convention-honoring output. Unshaped agents with unlimited context produce monolithic, inconsistent output.

### 3.3 How It Works: The System Manifest

A **System Manifest** is a single YAML file checked into the repo that describes the system at three levels of detail:

| Level | What it captures | Who reads it | Size per domain |
|-------|-----------------|-------------|-----------------|
| **Topology** | Domain boundaries, dependency graph, convention assignments | Architect agent only | ~200 tokens |
| **Facade** | Boundary entities, API blurbs, mutation descriptions, preconditions, error modes, events | Architect + any specialist that interacts with this domain | ~500-1500 tokens |
| **Internals** | Source code, test files, LLD detail | Only that domain's specialist | ~5K-30K tokens |

The manifest contains levels 1 and 2. Level 3 (internals) is loaded on demand from the actual source files.

**Why YAML and not a knowledge graph?** Simpler to author, version, diff, and review in a pull request. A knowledge graph would be more powerful for complex cross-domain queries, but harder to maintain. Revisit if cross-domain queries become too complex for flat YAML.

**Why three levels, not two?** Two levels (manifest + source) would force the architect to either include all source code (back to "reads too much") or include no cross-domain information (specialists cannot honor interfaces). The facade level is the resolution: **enough to call correctly and reason about side effects, not enough to understand the internal implementation.** Same principle as a Java or Go interface — the contract, not the body.

### 3.4 The Architect/Specialist Pattern

```mermaid
graph TB
    subgraph Manifest["System Manifest (~15K tokens)"]
        Domains["Domain registry"]
        Facades["Facade layer boundary entities, API blurbs"]
        Conventions["Cross-cutting conventions"]
    end

    subgraph Architect["Architect Agent"]
        Read["Read manifest"]
        Decompose["Decompose task"]
        Dispatch["Dispatch to specialists"]
        Validate["Validate results"]
    end

    subgraph Specialists["Domain Specialists"]
        S1["Agent Framework"]
        S2["Publishing"]
        S3["Data Layer"]
        S4["API Controllers"]
    end

    subgraph Gates["Human Gates"]
        Lead["Lead reviews decomposition"]
        PR["PR review"]
    end

    Manifest --> Read --> Decompose
    Lead -.->|approve| Decompose
    Decompose --> Dispatch
    Dispatch --> S1 & S2 & S3 & S4
    S1 & S2 & S3 & S4 --> Validate
    Validate --> PR

    classDef manifest fill:#fef3c7,stroke:#d97706
    classDef arch fill:#dcfce7,stroke:#16a34a
    classDef spec fill:#dbeafe,stroke:#2563eb
    classDef human fill:#fecdd3,stroke:#e11d48
    class Domains,Facades,Conventions manifest
    class Read,Decompose,Dispatch,Validate arch
    class S1,S2,S3,S4 spec
    class Lead,PR human
```

1. **Architect reads the manifest** (~15K tokens) and decomposes the task into scoped task packets.
2. **Human gate**: the lead reviews the decomposition before execution.
3. **Specialists receive task packets** that include exactly the files they need, exactly the conventions to follow, exactly the facades of adjacent domains — and explicit boundaries on what they must *not* modify.
4. **Specialists return result packets** that include files created/modified, conventions honored, interface compliance checks, and cross-cutting discoveries.
5. **Architect validates** interface compliance, propagates cross-cutting discoveries, and updates the manifest.

Specialists are stateless. They re-read their domain files each activation. This is simpler and more reproducible than maintaining warm state, and the cost is acceptable — reading a few source files is cheap compared to re-reading the whole codebase.

### 3.5 Facade-Level Interop

The facade is how disjoint agents know about each other. When the publishing specialist needs to interact with the agent framework, it does not read the framework's source code. It reads a blurb like:

> *"The tool loop in the base agent calls your tool via tool.execute(**args). It expects a ToolResult back. brand_id is auto-injected if not in args."*

That is enough to produce a correct integration. The specialist does not need to understand the framework's internal state machine — just its boundary contract. This is the same principle as microservice API contracts, applied to AI agent context.

---

## 4. Collaborative Development: The Design Room

### 4.1 What It Is

An **AI Design Room** is a per-feature thread where the team collaborates with AI as a participant, not just a tool. This is different from autonomous coding tools (which operate without human oversight) and different from simple AI assistants (which respond to individual prompts without maintaining conversation context across the team).

### 4.2 Three Boundaries

| Boundary | Rule |
|----------|------|
| **Working medium** | Slack (or similar) — the thread where discussion, AI drafts, and human decisions happen in real time |
| **Source of truth** | GitHub — every decision materializes as a commit, PR, or issue update |
| **Decision gates** | PRs — the thread generates artifacts, but nothing ships without PR review and merge |

### 4.3 How It Works

Multiple humans and AI participate in one thread. AI drafts; humans decide. The workflow steps, the manifest, and the role definitions provide the structure. The design room provides the collaboration layer.

**Current state:** The workflow steps, the manifest, and the role definitions exist. A unified thread experience does not yet exist — coordination currently happens across Slack conversations, GitHub PRs, and separate AI sessions. Unifying that is an open project.

---

## 5. The Workflow

**Two phases — Unknown and Known:**

Some changes have unknowns that must be resolved before the team can commit to a design. The workflow splits into an **exploration phase** (resolve the unknowns) and an **execution phase** (build the known).

| Phase | When | What happens | Output |
|-------|------|-------------|--------|
| **Unknown (PoC / Spike)** | The team cannot write a precise LLD because a key question is unanswered — "will the API support this?", "can the model handle this latency?", "does this approach scale?" | Timeboxed PoC. AI generates the throwaway code. Developer validates the hypothesis. No production standards required — this is learning, not building. | Findings doc: what worked, what didn't, constraints discovered, revised assumptions. |
| **Known (Execution)** | The design is understood well enough to write a precise LLD. | Full workflow below. The findings from the PoC feed directly into the LLD — they ARE the design input. | Production code, tests, docs, deployment. |

The PoC phase is explicitly **not** held to the full workflow. Its purpose is to answer questions cheaply so the execution phase doesn't discover unknowns mid-build. But PoC findings MUST be documented — they become the basis for the LLD. A PoC without a findings doc is wasted learning.

**Three entry points:**

| Starting from | What happens first |
|---------------|-------------------|
| **A PRD (new system or major feature)** | AI helps decompose the PRD into HLD → LLDs → issues. Each issue enters the workflow. |
| **An issue with unknowns** | PoC phase first → findings doc → then enter the execution workflow with the unknowns resolved. |
| **An issue (known, ready to build)** | Enter the execution workflow directly. |

For truly small changes (a one-line config fix), this workflow is too heavy — see "Common Pitfalls" (Section 6) for when to abbreviate.

### 5.1 The Pipeline View

Each shippable unit — a vertical slice of backend + frontend + tests + docs — goes through this pipeline:

```mermaid
graph LR
    subgraph Registries["Institutional Knowledge"]
        TR["Test Registry"]
        IR["Incident Registry"]
    end

    subgraph Pipeline["Shippable Slice"]
        direction LR

        subgraph Requirements["Requirements"]
            R0["PRD (if new system)"]
            R1["Issue"]
            R2["Design spec"]
            R0 -.->|"decompose"| R1
        end

        subgraph PoC["Unknown (if needed)"]
            P1["Timeboxed PoC"]
            P2["Findings doc"]
            P1 --> P2
        end

        subgraph Design["Design + QA/Ops input"]
            D1["Impact Analysis"]
            D2["HLD/LLD + Test Plan"]
            D3["IaC"]
        end

        subgraph Build["Build (TDD)"]
            B1["Tests first (RED)"]
            B2["Human + QA review"]
            B3["Code (GREEN)"]
            B4["Refactor"]
        end

        subgraph Verify["Verify"]
            V1["Review Round 1 + 2"]
            V2["Reconcile Docs"]
        end

        subgraph Assess["Assess"]
            A1["Downstream Impact"]
            A2["Rollout Plan"]
        end

        subgraph Ship["Ship"]
            S1["PR + Integration Verify"]
            S2["Canary Deploy"]
            S3["Promote / Rollback"]
        end

        Requirements -.->|"unknowns?"| PoC
        PoC -->|"findings feed design"| Design
        Requirements -->|"known"| Design
        Design --> Build --> Verify --> Assess --> Ship
    end

    TR -->|"coverage gaps?"| D1
    IR -->|"past incidents?"| D1
    IR -->|"canary criteria"| A2
    B2 -->|"new tests"| TR
    S3 -->|"new incidents"| IR

    style Pipeline fill:#fafafa,stroke:#616161
    style Registries fill:#f3e8ff,stroke:#9333ea
    style Requirements fill:#e3f2fd,stroke:#1565c0
    style PoC fill:#fff3e0,stroke:#e65100
    style Design fill:#e3f2fd,stroke:#1565c0
    style Build fill:#e8f5e9,stroke:#2e7d32
    style Verify fill:#fff3e0,stroke:#e65100
    style Assess fill:#fce7f3,stroke:#db2777
    style Ship fill:#ffcdd2,stroke:#c62828
```

### 5.2 The Steps

Most steps are AI-driven. Human work is review and judgment, not production.

> 🤖 AI does it &nbsp; 👤🤖 AI drafts, human reviews &nbsp; 👤 Human only &nbsp; 🔁 Iterative until correct

| Phase | Steps |
|-------|-------|
| **Design** | Issue 👤🤖 → Design spec 👤🤖 (if exists) → Impact analysis 🤖 → Update docs 👤🤖 🔁 → Update IaC 👤🤖 → Test plan 👤🤖 🔁 → Training plan 👤🤖 |
| **Build (TDD)** | Generate tests 🤖 → Human + QA review 👤 🔁 → Tests improve LLD 🤖 🔁 → Verify RED 🤖 → Generate code 🤖 → Verify GREEN 🤖 🔁 → Refactor 👤🤖 🔁 |
| **Verify** | Code review R1 🤖 🔁 → Code review R2 🤖 🔁 → Reconcile docs 🤖 |
| **Assess** | Impact brief 👤🤖 🔁 → Rollout plan 👤 |
| **Ship** | PR + integration verify 👤 → Handoff to QA + Ops 👤 → QA verifies quality 👤 → Ops deploys + monitors 👤🤖 → Promote/rollback 👤 |
| **Post-ship** | 30-day ROI check 👤 → 90-day ROI check 👤 |

The 🔁 steps loop until the human is satisfied — AI revises, human re-reviews, repeat. Non-🔁 steps run once.

Of 24 steps: **12 AI-driven** 🤖, **8 AI-assisted** 👤🤖, **4 human-only** 👤.

### 5.3 The Two-Round Code Review

| | Round 1 (pre-test) | Round 2 (post-test) |
|---|---|---|
| **Focus** | Structure, security, spec adherence | Edge cases, regressions, completeness |
| **What it catches** | Design-level problems | Behavior-level problems |
| **When it saves time** | Before test investment | After tests reveal unexpected behavior |
| **Who** | AI reviewer | AI reviewer |

Finding structural problems after tests pass means the tests are now wrong too. Round 1 catches those early.

### 5.4 Design Spec: Input at the Start, Verification at the End

If a visual design (Figma or similar) exists, it appears twice in the workflow: at the start it feeds requirements into the issue, and at the end it verifies the implementation matches the original intent. The design is both the input and the acceptance criteria. This prevents the common drift where the implemented feature gradually diverges from the original design during implementation.

### 5.5 ROI Estimation

For changes costing more than a day of effort, add three items to the GitHub issue before build starts: (1) a specific, falsifiable expected outcome with timeframe, (2) the current baseline metric (measured, not estimated), and (3) what happens if ROI is not realized. Verify at 30 days (direction check) and 90 days (magnitude check). Document the actual outcome in the ADR so future estimates calibrate against reality.

### 5.6 Downstream Impact Assessment

This step solves a problem that most AI-assisted development processes ignore entirely: **the people downstream of the code change need to understand what happened and why.**

When AI generates code at high velocity, the blast radius of each change increases. A developer using AI can produce in a day what previously took a sprint — but the product team, QA, ops, and customer support then need to absorb a sprint's worth of changes in a day. If they do not, the code is correct but the team's mental model is wrong, leading to mis-prioritized roadmap items, missed regression scenarios, and deployment incidents that ops did not anticipate.

The impact brief has five sections, each aimed at a different stakeholder:

```mermaid
graph TD
    subgraph Brief["Downstream Impact Brief"]
        direction TB
        Flows["1. Flows + Components Changed"]
        Risk["2. Risk Assessment"]
        Test["3. Manual Verification Scenarios"]
        Mental["4. Product Mental Model Update"]
        Deploy["5. Rollout Strategy + Canary Criteria"]
    end

    subgraph Readers["Who reads"]
        PM["PM: sections 1 + 4"]
        Lead["Lead: sections 2 + 5"]
    end

    subgraph Contributors["Who contributes (non-blocking)"]
        QA["QA: adds test scenarios from incident registry"]
        Ops["Ops: adjusts canary criteria from incident registry"]
    end

    subgraph Registries["Institutional Knowledge"]
        IR["Incident Registry"]
        TR["Test Registry"]
    end

    Flows --> PM
    Mental --> PM
    Risk --> Lead
    Deploy --> Lead
    Test --> QA
    Deploy --> Ops
    IR -->|"past failures shape"| Deploy
    IR -->|"regression scenarios"| QA
    TR -->|"coverage check"| Test

    classDef brief fill:#fef3c7,stroke:#d97706
    classDef reader fill:#dbeafe,stroke:#2563eb
    classDef contributor fill:#dcfce7,stroke:#16a34a
    classDef registry fill:#f3e8ff,stroke:#9333ea
    class Flows,Risk,Test,Mental,Deploy brief
    class PM,Lead reader
    class QA,Ops contributor
    class IR,TR registry
```

**Section 4 — the mental model update — is the one most often skipped and most often regretted.** Example: if you change the campaign approval flow so that "approved" no longer triggers publishing (instead it queues for scheduled delivery), the PM's mental model of "approve = publish" is now wrong. Every roadmap discussion, every customer promise, every support playbook that assumed "approve = publish" is silently incorrect. Writing "approve now queues for scheduled delivery instead of publishing immediately" in the impact brief takes 30 seconds and prevents weeks of downstream confusion.

> **The impact brief is not about protecting against technical risk.** Tests and code review handle that. The brief is about protecting against **organizational risk** — the risk that the humans around the code do not understand what changed.

**Who writes it**: the developer, with AI assistance. AI can draft the flows/components section from the diff and the risk section from the test plan. The mental model section requires human judgment — you need to know what assumptions the PM holds.

**When it is reviewed**: by the team lead during integration verification (step 18). The lead checks: "Is this brief complete? Would the PM understand what changed from reading this? Would ops know how to deploy it safely?"

### 5.7 Canary Deployment Strategy

The rollout plan at step 17 is risk-rated — not every change gets the full canary treatment:

| Risk level | Example | Rollout |
|-----------|---------|---------|
| **Low** | CSS fix, copy change, internal doc update | Direct deploy |
| **Medium** | New feature behind feature flag, additive endpoint | Flag off, staging, 24h soak, production |
| **High** | Changed existing behavior, external integration, schema migration | Canary 5-10%, 4h monitor, 25%, 4h, 100% |
| **Critical** | Irreversible side effects, billing, data migration | Canary 1%, manual gate each step, 24h soak per tier |

Each promotion step checks explicit go/no-go criteria: error rate delta, latency delta, business metric delta (e.g., campaign publish success rate), and failure-mode score trends from the observability layer. If any criterion fails, the canary pauses — not rolls back immediately, but pauses so the team can investigate. Most "failures" turn out to be noise or pre-existing; automatic rollback on noise creates churn.

Calibrate the criteria to the specific change, not universal thresholds. A change to the payment flow has tighter thresholds than a change to a dashboard component. The developer proposes the criteria in the rollout plan; the lead reviews them during integration verification.

> **Canary deployment is not new.** What is new is making it a formal step in the dev workflow with AI-generated monitoring summaries. AI reads the observability dashboards during the canary window and produces a go/no-go recommendation — the human still makes the call, but the analysis is pre-digested.

### 5.8 Worked Example: "Add a New Publishing Channel"

| Step | Who | What happens |
|------|-----|-------------|
| 1 | PM + AI | PM describes the need. AI drafts PRD update. PM reviews. |
| 2 | Architect + AI | AI analyzes impact across LLDs. Architect opens Design PR with HLD/LLD/IaC/test plan changes. |
| 3 | Team + QA + Ops | Devs review LLD sections. QA adds test scenarios from incident registry. Ops reviews IaC. PR merged — design locked. |
| 4 | Devs + AI | AI generates tests (RED). Dev + QA review, add edge cases. AI generates code (GREEN). Refactor. |
| 5 | AI | Reviews both PRs against LLD. Flags gaps. Devs fix. |
| 6 | Dev + AI | Downstream impact brief. QA adds manual verification scenarios. PM mental model update written. |
| 7 | Dev + Ops | Rollout plan. Ops adjusts canary criteria from incident registry. |
| 8 | Architect | Reviews traceability + impact brief + rollout plan. |
| 9 | Dev → QA + Ops | **Handoff.** Dev delivers stable build with evidence: test registry results, impact brief, rollout plan, baseline IaC. QA and Ops take it from here. |
| 10 | QA | Independent quality verification. Exploratory testing. Blocks promotion if criteria not met. Pulls Dev in for fixes if needed. |
| 11 | Ops + AI | Deploys to canary. Refactors IaC if needed (Dev applies refinements back to dev). AI monitors go/no-go criteria. Promotes or rolls back. |
| 12 | Team + PM | Demo. PM gives feedback. Next iteration if needed. |

**Total time: days, not sprints.** The downstream impact brief adds ~30 minutes to the process. The canary monitoring adds ~4 hours of wall-clock time (mostly waiting, not working). Both prevent classes of problems that would otherwise take days to diagnose and fix.

---

## 6. Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **Shipping without issues** | Code works, tests pass, but there is zero traceability. No link from requirements to design to code. When someone later asks "why does this integration use this retry strategy?", the answer is buried in a chat transcript. | Add a preflight check that blocks code generation if no issue is linked. GitHub issue first, always (step 1). |
| **Skipping the training plan** | Architectural decisions around new techniques (e.g., Thompson sampling, bandit routing) ship without training materials. A developer encountering the new pattern for the first time has to reverse-engineer it from code. | Use the conditional step 7 (training plan stub). The trigger list is explicit. |
| **Using the full process for trivial changes** | A one-line config change goes through 20 steps. The overhead exceeds the value. | There is no clean answer. In practice, skip steps for trivial changes — but "trivial" is a judgment call, and sometimes what looks trivial has architectural implications that surface later. A formal "light path" (issue, code, review) for changes below some complexity threshold is worth defining, but setting that threshold reliably is hard. |
| **Using the full process for cross-cutting changes** | A cross-cutting change (new convention, framework upgrade, security patch) is treated as a single pipeline. But it has n-domain impact, and the pipeline's single Design PR does not adequately capture the review burden. | The hierarchical knowledge architecture helps (the architect decomposes across domains), but the human review bottleneck at the integration verification step does not scale. If the lead has to verify integration across 8 domains in one PR, something will get missed. Break cross-cutting changes into domain-scoped PRs. |

### 6.1 Open Questions

- **Exploratory work**: How to handle genuinely exploratory work where the design emerges from the code. The design-first approach has clear value, but some tasks require building before knowing what to build.
- **Developer identity**: How to onboard developers who are uncomfortable with the "review, don't write" model. Some engineers derive identity from writing code. Telling them "your job is review" can feel like a demotion even when it is not.
- **Manifest accuracy**: How to keep the manifest accurate as the system evolves fast. The generator script helps, but human-authored blurbs (mutation descriptions, preconditions, the "IRREVERSIBLE" annotation on side effects) require judgment that cannot be automated yet.
- **Two-round review ROI**: Whether the two-round code review actually saves time compared to a single thorough review is an open question without data.

---

## 7. Adoption Checklist

Use this checklist when considering or implementing this process:

- [ ] **Docs discipline first.** If the team does not currently maintain design docs, do not jump to docs-first AI development. The transition is: (1) start writing docs at all, (2) make them precise enough to generate from, (3) start generating. Skipping to step 3 produces convention drift and hallucination.
- [ ] **Address the cultural barrier.** The tools work. The hard part is convincing experienced developers that their job is now "review and correct" instead of "write." This requires trust — in the tools, in the process, and in the fact that review is harder and more valuable than generation.
- [ ] **Start with one change.** Pick one non-trivial feature, try the doc-first flow, and see what happens. If the generated code is better than what would have been written by hand, the process sells itself. If it is not, either the docs were not precise enough or the feature is not a good fit for this approach.
- [ ] **Recognize that docs are the moat.** Every team has access to the same AI models. The competitive advantage is in the documentation that makes those models produce *your* system's conventions, *your* architecture's patterns, *your* domain's edge cases. A team with 55 well-maintained architectural decisions and 33 precise LLDs will outproduce a team with better AI tools but no docs.
- [ ] **Invest in evals early.** Quality scoring — even simple LLM-judge rubrics — gives you the feedback loop to improve. Without evals, you cannot tell whether AI output is getting better or worse over time, and you cannot compare the effect of process changes. Eval infrastructure is boring to build but transformative to have.
- [ ] **Accept that the process will evolve.** Steps will be added, reordered, and entire concepts introduced late. Treat the process as a living system, not a fixed standard.

> The goal is not to ship faster. The goal is to minimize the problems that come from AI-generated code — convention drift, untraceable decisions, hallucination — so the system evolves correctly. Speed is a side effect of correctness, not a goal in itself.

---

## 8. Brownfield: Adopting This on an Existing Codebase

An architect working with AI can produce the full documentation baseline — manifest, HLDs, LLDs, ADRs, CLAUDE.md, convention checks — in one sprint. AI does the mechanical work (scanning code, generating drafts). The architect does the judgment (correcting boundaries, adding "why" knowledge, verifying inferred decisions). The baseline will be ~70% accurate; the process corrects the rest through normal use.

Use the `/generate-docs reverse-engineer` skill to automate the sprint. See [docs/playbook/adoption-guide.md](docs/playbook/adoption-guide.md) for the full guide including: the sprint structure, gap assessment and closure plan, handling areas nobody understands, the expedited path for production incidents, and common objections.

---

## Skills and Tools

Skills are Claude Code commands that automate parts of the workflow. Tools run in CI or from the command line. Templates provide the starting structure for project artifacts. Everything lives in two repos:

- **[hitl-dev-platform](https://github.com/Prasad-Apparaju/hitl-dev-platform)** — the process, skills, tools, and templates (this repo)
- **[agentic-platform](https://github.com/Prasad-Apparaju/agentic-platform)** — reusable Python/LangGraph infrastructure for building agents (BaseAgent, tools, resilience, routing, observability) + [7 agentic patterns](https://github.com/Prasad-Apparaju/agentic-platform/tree/main/docs/patterns) for transitioning from deterministic to agentic systems

### Available now

| Type | Name | Source | What it does |
|------|------|--------|-------------|
| Skill | `/dev-practices` | [skills/dev-practices.md](skills/dev-practices.md) | The full workflow — phases, steps, TDD cycle, ROI, downstream impact |
| Skill | `/apply-change` | [skills/apply-change.md](skills/apply-change.md) | Impact analysis — affected components, APIs, docs, tests |
| Skill | `/generate-docs` | [skills/generate-docs/](skills/generate-docs/) | HLD/LLD/ADRs from feature description (new) or from existing code (reverse-engineer) |
| Tool | Convention checker | [tools/check-conventions/](tools/check-conventions/) | Pluggable YAML-driven checker — AST-based, fails CI on violations |
| Tool | Mermaid fixer | [tools/fix-mermaid/](tools/fix-mermaid/) | Removes `<br/>` from Mermaid blocks for Obsidian compatibility |
| Tool | PDF renderer | [tools/render-pdf/](tools/render-pdf/) | Markdown to PDF with Mermaid diagram rendering |
| Template | CLAUDE.md | [templates/CLAUDE.md.template](templates/CLAUDE.md.template) | Project CLAUDE.md with placeholder sections for conventions |
| Template | System manifest | [templates/system-manifest.schema.yaml](templates/system-manifest.schema.yaml) | Schema definition for the system manifest |
| Template | Issue | [templates/issue-template.md](templates/issue-template.md) | GitHub issue template with ROI + downstream impact sections |
| Template | Test registry | [templates/test-registry-template.yaml](templates/test-registry-template.yaml) | Test case catalog (domain, risk, origin, incident link) |
| Template | Incident registry | [templates/incident-registry-template.yaml](templates/incident-registry-template.yaml) | Incident catalog (root cause, fix, regression test, canary criteria) |
| Template | ADR, Training plan | [templates/adr-template.md](templates/adr-template.md), [templates/training-plan-template.md](templates/training-plan-template.md) | Standard doc formats |
| Skill | `/tdd` | [skills/tdd.md](skills/tdd.md) | TDD-as-design loop: generate tests → human review → improve LLD → RED → GREEN → refactor |
| Skill | `/impact-brief` | [skills/impact-brief.md](skills/impact-brief.md) | Generate 5-section downstream impact brief from PR diff + manifest + incident registry |
| Skill | `/check-conventions` | [skills/check-conventions.md](skills/check-conventions.md) | Run convention checker in-chat, offer to fix violations |
| Tool | Manifest generator | [tools/generate-manifest/](tools/generate-manifest/) | Auto-generate system-manifest.yaml from codebase via AST scanning |
| Infra | Agent platform | [agentic-platform repo](https://github.com/Prasad-Apparaju/agentic-platform) | BaseAgent, tools, resilience, routing, observability, 7 patterns |

---

## Further Reading

- **Conway's Law (1967)** — Melvin Conway, "How Do Committees Invent?" — the architectural principle behind the knowledge hierarchy
- **Team Topologies** (Skelton & Pais, 2019) — the modern framework for applying Conway's Law to human teams, directly applicable to AI agent boundaries
- **DSPy** (Khattab et al., Stanford) — programmatic prompt optimization, relevant to the continuous quality improvement discussion
- **LangGraph** (LangChain) — the agent framework pattern of graph-based state machines with checkpointing, relevant to HITL implementation
- **arc42** (Starke & Hruschka) — the documentation template that influenced the HLD/LLD structure described here
- **"Prompt Engineering vs. Fine-Tuning"** (various) — background on why API-only continuous learning matters as an alternative to model adaptation
