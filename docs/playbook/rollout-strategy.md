# Rollout Strategy Guide

Every change that reaches production needs a risk-rated deployment plan. The risk level determines the rollout speed and monitoring gates.

---

## Risk Levels

| Risk | When to use | Examples |
|---|---|---|
| **Low** | Cosmetic, internal-only, no external side effects | Doc updates, log format changes, internal tool tweaks |
| **Medium** | New feature (additive), no existing behavior changed | New endpoint behind feature flag, new admin page |
| **High** | Changes existing behavior, new external integration | Modified API response shape, new third-party API call |
| **Critical** | Irreversible side effects, billing, data migration | Email/SMS sends, payment processing, schema migrations that drop columns |

---

## Rollout Plans by Risk

### Low Risk — Direct Deploy

```
1. Merge PR
2. Deploy to production
3. Verify in production (smoke test)
```

No feature flag. No canary. No soak period.

### Medium Risk — Feature Flag + Soak

```
1. Merge PR with feature flag OFF
2. Deploy to production (no user impact — flag is off)
3. Enable flag on staging, verify E2E
4. Enable flag for internal team (dogfood)
5. Enable flag for 100% of users
6. 24-hour soak — monitor error rates, latency, user feedback
7. If clean → remove flag, clean up code
8. If issues → disable flag, investigate, fix, restart from step 3
```

### High Risk — Canary Deployment

```
1. Merge PR with feature flag at 0%
2. Deploy to production
3. Enable flag for 5-10% of users (deterministic hash)
4. 4-hour monitor window — check:
   - Error rate delta < 1% vs baseline
   - p95 latency delta < 200ms vs baseline
   - No new error types in logs
   - Business metrics within 5% of baseline
5. If clean → expand to 25%
6. 4-hour monitor → expand to 50%
7. 4-hour monitor → expand to 100%
8. 24-hour soak at 100%
9. If clean → remove flag, clean up code
10. If issues at ANY step → revert to 0%, investigate
```

### Critical Risk — Manual Gates

```
1. Merge PR with feature flag at 0%
2. Deploy to production
3. Enable flag for 1% of users
4. 24-hour soak with manual monitoring:
   - Dedicated person watches dashboards
   - Check external side effects (emails sent, API calls made)
   - Verify idempotency — retry doesn't cause duplicates
   - Compare against incident registry for this domain
5. Manual go/no-go decision by team lead
6. If go → expand to 5%, repeat 24-hour soak
7. If go → expand to 25%, repeat 24-hour soak
8. If go → expand to 100%
9. 48-hour soak at 100% with monitoring
10. If clean → remove flag
11. If issues at ANY step → revert to 0%, write incident report
```

---

## Go/No-Go Criteria

Default criteria (customize per change):

| Metric | Threshold | How to check |
|---|---|---|
| Error rate | < 1% delta vs pre-deploy baseline | Error monitoring dashboard |
| p95 latency | < 200ms delta | APM / request metrics |
| New error types | 0 new error categories | Log aggregator |
| Business metric | Within 5% of baseline | Product analytics |
| External side effects | No duplicates, no unintended calls | Side effect / idempotency log |
| Incident registry match | No recurrence of past incidents in this domain | `docs/04-operations/incident-registry.yaml` |

For **High** and **Critical** changes, customize the criteria based on:
- The specific risks identified in the impact brief (§2)
- Past incidents in this domain (from the incident registry)
- The nature of the external side effects

---

## Feature Flag Implementation

Feature flags should be:
- **Deterministic** — same user always gets the same result (hash-based, not random)
- **Queryable** — stored in the database, cached with short TTL (30s)
- **Auditable** — changes logged with who, when, old value, new value
- **Cleanable** — after GA, remove the flag and the old code path

```
Flag lifecycle: OFF → canary (5%) → expanding (25-50%) → GA (100%) → archived (flag removed)
```

---

## Post-Rollout

After reaching 100% and completing the soak period:

1. **Remove the feature flag** — dead code paths accumulate tech debt
2. **Update the incident registry** — if any issues occurred during rollout
3. **Update canary criteria** — if you discovered new metrics to watch
4. **30-day ROI check** — is the feature delivering the expected value?

---

## Quick Decision Table

| Question | Answer determines risk level |
|---|---|
| Does this change user-visible behavior? | No → Low. Yes → Medium+. |
| Does this call an external API? | No → stays. Yes → bump one level. |
| Is the external call irreversible? (email, payment, post) | No → stays. Yes → Critical. |
| Does this change a database schema? | Additive (new column) → stays. Destructive (drop/rename) → Critical. |
| Has this domain had incidents before? | No → stays. Yes → bump one level. |
