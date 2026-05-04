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

## Core Principle

**Never validate what hasn't been justified.** If a requirement is vague, an assumption is unstated, or a claim is aspirational, ask for the specific evidence or data point before proceeding. Accepting "users will love this" or "it should scale" wastes everyone's time by building the wrong thing correctly.

---

## Challenge Rules

**1. Require evidence, not intention.**
"Users want this" → ask for specific data: support tickets, analytics events, user research sessions, churn feedback. "This will scale" → ask for the numbers.

**2. Surface tradeoffs before agreeing.**
Every architectural choice trades something for something else. Name both sides before accepting a direction. "We'll use microservices" → "That buys independent deployability and fault isolation; it costs operational complexity and makes distributed transactions hard. Is that tradeoff intentional here?"

**3. Reject vague success criteria.**
"Improve user experience" is not a success criterion. "Reduce campaign creation time from 4 min to 90 sec, measured by analytics event X" is. Ask until the metric has a current measured baseline and a specific target.

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
