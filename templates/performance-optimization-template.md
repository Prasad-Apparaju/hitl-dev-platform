# [Project Name] — Performance Optimization Plan

**Date:** YYYY-MM
**Context:** [Language/framework, key performance characteristics of the system]

---

## System Performance Profile

[One paragraph: Is your system I/O-bound, CPU-bound, or mixed? What are the dominant latencies? This determines which optimizations matter.]

| Dominant latency source | Typical range | Optimization lever |
|------------------------|:-------------:|-------------------|
| [e.g., LLM API calls] | 1–30s | Streaming, caching, parallel calls |
| [e.g., Database queries] | 1–50ms | Connection pooling, indexing, query optimization |
| [e.g., File I/O] | Network-bound | Background tasks, CDN, compression |

---

## Tier 1: Already In Place (Foundation)

Optimizations that should be in place from day one.

| Optimization | Status | Details |
|-------------|:------:|---------|
| Async I/O | | [Framework-specific: FastAPI async, Node.js event loop, etc.] |
| Connection pooling | | [DB connection pool config] |
| Health probes | | [Liveness, readiness, startup] |
| Graceful shutdown | | [Drain connections before terminating] |
| Lazy initialization | | [Defer expensive client creation to first use] |

---

## Tier 2: Per-Phase Optimizations

Add these as you build each vertical slice. Don't optimize prematurely — measure first.

### Phase/Slice 1: [Name]

| Optimization | Details | Measure before | Measure after |
|-------------|---------|:--------------:|:------------:|
| [e.g., Batch DB operations] | [Use bulk upsert instead of row-by-row] | | |
| [e.g., Background tasks] | [Offload non-blocking work from request path] | | |

### Phase/Slice 2: [Name]

| Optimization | Details | Measure before | Measure after |
|-------------|---------|:--------------:|:------------:|
| [e.g., Streaming responses] | [SSE/WebSocket for long-running AI operations] | | |
| [e.g., In-memory cache] | [Cache rarely-changing data, TTL-based expiry] | | |

---

## Tier 3: Deferred (Post-Launch)

Optimizations that aren't worth the complexity until you have real traffic data.

| Optimization | When to consider | Complexity |
|-------------|-----------------|:----------:|
| Horizontal scaling (HPA) | P95 latency > SLA with single instance | Medium |
| Query optimization (EXPLAIN) | Slow query log shows >100ms queries | Low |
| CDN for static assets | Global users, high asset load times | Low |
| Read replicas | DB CPU > 70% sustained | High |
| Result caching (Redis) | Same expensive computation repeated frequently | Medium |
| Load testing + profiling | Before major launch or scale event | Medium |

---

## Anti-Patterns to Avoid

| Don't do this | Do this instead |
|--------------|----------------|
| Optimize without measuring | Profile first, optimize the measured bottleneck |
| Add caching everywhere | Cache only what's expensive AND frequently accessed AND tolerant of staleness |
| Synchronous external calls in request path | Async calls or background jobs for anything >100ms |
| Premature horizontal scaling | Vertical scaling (bigger instance) is simpler until you hit its limits |
| Custom connection management | Use your framework's built-in pooling |

---

## Monitoring for Performance

| Metric | Where to track | Alert threshold |
|--------|---------------|:---------------:|
| P50 / P95 / P99 latency | API gateway / APM | P95 > [X]ms |
| Error rate | API gateway | > 1% |
| DB connection pool usage | Pool metrics | > 80% capacity |
| Memory usage | Container metrics | > 80% of limit |
| CPU usage | Container metrics | > 70% sustained |
