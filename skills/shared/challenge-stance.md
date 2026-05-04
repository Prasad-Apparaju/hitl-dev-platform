# Challenge Stance — Design-Phase Critical Evaluation

Reference this document from the Important Rules section of any design-phase skill.

---

## When it applies

Apply the challenge stance in:
- Requirements definition (`pm/add-feature`, `pm/design-feature`)
- Architecture and system design (`architect/design-system`, `architect/design-feature`)
- Impact analysis and scope definition (`apply-change`, `dev-practices` step 3)

**Do not apply in execution phases** (TDD, code review, convention checks, deployment). In execution, trust the approved design and execute — challenge mode in build phases creates friction without benefit.

---

## TODO Deferral

Available at **all challenge levels**. Any time the PM is unsure of an answer, they can defer it rather than block the session.

**Trigger phrases** (any of these → record and proceed):
- "add to TODO", "defer this", "come back to this", "not sure yet", "TBD", "I'll find out"

**Behavior:**
1. Acknowledge: "Got it — I'll add that to the open items list and we'll keep going."
2. Record the item: question label + what's missing (e.g., "Evidence: no specific data point yet — needs ticket count or analytics pull").
3. Proceed as if the question was answered at Light level (note the gap, do not block).
4. At the end of Phase 1 (or the full session for `pm/add-feature`), present the collected TODO list:

   > **Open items to revisit before this feature ships:**
   > - [ ] Evidence: ticket count or analytics to confirm the problem scope
   > - [ ] Success metric: specific baseline + target (or hypothesis + validation plan)

The TODO list is informational — it does not block moving to the next phase. It surfaces what the PM still needs to resolve before the feature can be treated as fully justified.

---

## Challenge Levels

Skills that apply the challenge stance offer three levels. Ask the user which they prefer at the start of any requirements or design session.

| Level | What it means | Best for |
|---|---|---|
| **Rigorous** | Every question is a blocker. Do not proceed without specific answers. Push back on vague or aspirational responses until a concrete data point, metric, or stated assumption is provided. | High-stakes features, complex or cross-domain changes, first-time capability design |
| **Moderate** | Ask all questions. Accept reasonable answers without demanding exact numbers. Flag gaps as notes and proceed — only delivery surface and problem statement are hard blockers. | Standard feature work, iterative product development |
| **Light** | Ask only the four key framing questions (delivery surface, evidence, success, conflicts). Note everything else as recommendations in the summary. Move quickly. | Well-understood incremental changes, internal tooling, low-risk additions |

**Architecture phases (design-system, design-feature, apply-change) always operate at Rigorous for NFR interrogation** — delivery medium and scale assumptions are too consequential to leave at Light. Level selection applies to PM skills only.

---

## Core Principle

**Never validate what hasn't been justified.** If a requirement is vague, an assumption is unstated, or a claim is aspirational, ask for the specific evidence or data point before proceeding. Accepting "users will love this" or "it should scale" wastes everyone's time by building the wrong thing correctly.

---

## Challenge Rules

**1. Require evidence, not intention.**
"Users want this" → ask for specific data: support tickets, analytics events, user research sessions, churn feedback. "This will scale" → ask for the numbers.

**2. Surface tradeoffs before agreeing.**
Every architectural choice trades something for something else. Name both sides before accepting a direction. "We'll use microservices" → "That buys independent deployability and fault isolation; it costs operational complexity and makes distributed transactions hard. Is that tradeoff intentional here?"

**3. Ask for success criteria — don't demand hard numbers.**
"Improve user experience" is not a success criterion, but that doesn't mean you need a fully measured baseline before proceeding. Ask: "What would tell you this feature worked — even roughly?" Accept:
- A specific metric with a rough target ("reduce support tickets related to this, currently about 10/week")
- A hypothesis with a validation plan ("we believe time-to-first-campaign will drop; we'll measure with analytics event X")
- An acknowledged gap + TODO deferral ("I don't have a number yet — I'll pull analytics")

What is not acceptable: pure intent without any rationale ("users will enjoy this", "it'll be better"). One follow-up probe is appropriate: "Do you have a rough sense of the current state — even a ballpark?" If they don't, offer the TODO option.

**4. Name what you're not building.**
Unstated non-goals become scope creep. Ask "what is explicitly out of scope?" before finalizing requirements.

**5. Challenge the tier and scope.**
If the stated scope is smaller than the actual blast radius, say so. Cross-domain changes are Tier 3 regardless of how they're framed. If the change should be split, say so and wait for confirmation.

**6. Challenge the solution, not just the requirements.**
If a simpler approach would solve the same problem, name it before designing the proposed solution. "You could solve this with X instead — it's simpler but trades Y. Is the proposed approach intentional?"

---

## Minimum NFR Checklist (Architecture Phases)

In any design session, if the following are absent or vague in the PRD, ask before proceeding. These three drive every major architectural decision — "TBD" on any of them means the architecture is guesswork.

| NFR | If absent or vague, ask | Why it matters |
|---|---|---|
| **Throughput** | What is the peak load? (req/sec, messages/sec, or jobs/sec) What is the peak-to-average ratio? When does peak occur? | Determines whether a single instance, horizontal scaling, or an async queue is required |
| **Latency** | What is the p99 response time target for interactive operations? A different target for background operations? | Drives sync vs. async design, caching strategy, and DB index requirements |
| **Availability** | What is the uptime SLA? (99.9% = 8.7h downtime/year; 99.99% = 52 min/year) What is acceptable planned downtime per month? | Determines redundancy model, failover strategy, and whether active-active is required |
| **Data volume** | How much data at launch? Growth rate per month/year? How long must data be retained? | Drives storage choice, archival policy, and whether sharding will eventually be needed |
| **Geographic distribution** | Single region or multi-region? Which regions? Any data residency or sovereignty requirements? | Multi-region adds significant operational complexity; residency requirements may force separate deployments |
| **Consistency** | Where is strong consistency required? Where is eventual consistency acceptable? | Determines whether distributed transactions are needed — avoid if possible |
| **Failure modes** | What happens when a key dependency (DB, external API) is unavailable? Which operations must succeed under degradation? | Drives circuit breaker, fallback, and graceful degradation design |
| **Concurrency** | Are there operations that must be serialized? Any operations that could be triggered concurrently with the same inputs? | Determines locking strategy and idempotency requirements |

**Rule:** "We don't know yet" is not acceptable for throughput, availability, or consistency. If genuinely unknown, make a stated assumption with a specific number and flag it as a design risk. A named assumption the team can challenge is better than an unnamed one embedded in the architecture.

---

## Language

Challenge respectfully — the goal is accurate requirements, not pushback for its own sake.

| Instead of | Use |
|---|---|
| "That's wrong" | "What evidence supports this?" |
| "That won't work" | "What are we trading away with this approach?" |
| "That's too vague" | "What does success look like in specific, measurable terms?" |
| "You haven't thought about scale" | "What's the peak load this needs to handle?" |
| "That's too big" | "Should this be split into smaller independently-deployable changes?" |
