# ADR-0005: Observability Strategy

| | |
|---|---|
| **Status** | Draft — complete before the first Tier 2 change |
| **Date** | [fill in] |
| **Deciders** | [fill in: architect, platform/ops lead] |
| **Supersedes** | — |
| **Related** | ADR-0001 (HITL adoption), ADR-0003 (test strategy), ADR-0004 (change tier policy) |

---

## 1. Context

The HITL workflow gates every Tier 2+ deployment on observability: `/hitl:ops-setup-observability` must be run before `/hitl:ops-deploy`, and every go/no-go criterion in a rollout plan requires a named dashboard panel and active alert. Without a defined observability strategy, these gates cannot be configured consistently.

Additionally, AI-assisted development introduces a second observability layer — **agentic observability** — covering token costs, AI session decisions, and audit trails. Without this, the cost and behaviour of AI agents in the development process are invisible.

## 2. Decision

### Application observability

| Signal | Tool | Location / config | Notes |
|---|---|---|---|
| Structured logs | [fill in — e.g., CloudWatch / ELK / Datadog / Loki] | [fill in] | |
| Metrics | [fill in — e.g., Prometheus + Grafana / CloudWatch / Datadog] | [fill in] | |
| Distributed tracing | [fill in — e.g., OpenTelemetry + Jaeger / Datadog APM / none] | [fill in] | |
| Error tracking | [fill in — e.g., Sentry / Rollbar / Datadog / none] | [fill in] | |
| Primary dashboard | [fill in — URL or path] | | |
| Alerting | [fill in — tool + on-call routing approach] | [fill in] | |

### Agentic observability

| Signal | Location | Owner | Notes |
|---|---|---|---|
| Session logs | `docs/session-logs/` (gitignored) | Auto — `write-session-summary.sh` hook | Written at end of every Claude Code session |
| Token cost registry | `docs/04-operations/token-cost-registry.yaml` | Dev lead | Updated at Step 31 of every change |
| AI decision audit | HITL session logs + PR descriptions | Developer | Key AI recommendations and architect decisions are recorded in the PR |

### On-call routing

[fill in — which team or rotation owns production incidents for each domain. Must be configured before the first Tier 2 production deploy.]

| Domain | On-call rotation | Escalation path |
|---|---|---|
| [fill in] | [fill in] | [fill in] |

## 3. Alternatives Considered

[fill in after team discussion — e.g., "Evaluated Datadog vs Prometheus + Grafana; chose Prometheus because we are already running it for infrastructure metrics."]

## 4. Consequences

### Positive
- Every deployment has a verified observability baseline before traffic is switched
- Token cost is tracked per change — cost trends are visible over sprints
- On-call routing is explicit — incidents are not silently swallowed

### Negative
- [fill in — e.g., "Datadog adds $X/month per host. Approved budget: ..."]

## 5. Implementation Notes

- `/hitl:ops-setup-observability` runs before every Tier 2+ deploy and wires go/no-go criteria to the tools defined here. It will fail if the tools in this ADR are not provisioned.
- The token cost registry template is at `shared/templates/token-cost-registry-template.yaml`. Update it at Step 31 of the 32-step workflow for every change.
- Session logs are written automatically by the `write-session-summary.sh` hook at the end of each Claude Code session. They are gitignored and local only.

## 6. Open Questions

1. [ ] Is distributed tracing required for this project? (Required for microservices with cross-service calls; optional for monoliths.)
2. [ ] What is the approved budget for observability tooling?
3. [ ] Who owns on-call for each domain? (Must be answered before first Tier 2 production deploy.)
4. [ ] Are session logs written to a central store (e.g., S3) or local-only?

## 7. Status

**Draft.** Must be accepted before the first Tier 2 change. Assign to: [fill in: platform/ops lead].

## ROI Estimate

**Value dimension:** Risk / Operability
**Expected outcome:** Mean time to detect (MTTD) production incidents < 5 minutes; AI development cost visible per sprint
**Baseline metric:** [fill in: current MTTD, current AI cost visibility]
**Expected cost:** [fill in: observability tooling cost + setup time]
**Verification:** 30-day check [fill in date] | 90-day check [fill in date]

## Actual Outcome (filled at 90-day checkpoint)

**Expected:** [copy from above]
**Actual:** [measured result]
**Verdict:** [ROI realized / Partial / Not realized — action taken]
