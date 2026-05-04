# API Contract Mapping — [Current Framework] → [Target Framework]

**Parent:** [Migration docs index]

---

## 1. Overview

[Current framework/language] endpoints are being migrated to [target framework/language]. This document maps every endpoint so the frontend team knows exactly what changes.

**Key change:** [e.g., Base URL switches from `:3001/v1/...` to `:8000/v1/...`. A reverse proxy handles routing during the transition.]

---

## 2. Endpoint Mapping

### [Domain: Authentication]

| Current | Target | Changes |
|---------|--------|---------|
| `POST /v1/auth/login` | `POST /v1/auth/login` | Same path. Response shape changes: [describe] |
| `POST /v1/auth/register` | `POST /v1/auth/register` | Same. Adds `refresh_token` in response |
| — | `POST /v1/auth/refresh` | **New** — [why added] |
| `GET /v1/auth/session` | — | **Dropped** — replaced by [what] |

**Frontend impact:** [What the frontend team needs to change for this domain]

### [Domain: Users]

| Current | Target | Changes |
|---------|--------|---------|
| `GET /v1/users/:id` | `GET /v1/users/{id}` | Path param syntax change only (framework convention) |
| `PATCH /v1/users/:id` | `PATCH /v1/users/{id}` | Same body shape |

**Frontend impact:** [What changes, if anything]

### [Domain: ...]

[Same structure for each API domain]

---

## 3. Request/Response Shape Changes

For endpoints where the shape changes, document the diff:

### `POST /v1/auth/login` — Response

**Current:**
```json
{
  "user": { "id": "...", "email": "..." },
  "sessionId": "..."
}
```

**Target:**
```json
{
  "user": { "id": "...", "email": "..." },
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600
}
```

**Migration note:** [What the frontend needs to adapt]

---

## 4. Error Response Format

| Aspect | Current | Target |
|--------|---------|--------|
| Format | [e.g., `{ error: "message" }`] | [e.g., RFC 7807 problem detail] |
| Status codes | [any changes?] | [any changes?] |
| Validation errors | [format] | [format] |

**Frontend impact:** [Error handling changes needed]

---

## 5. Authentication Changes

| Aspect | Current | Target |
|--------|---------|--------|
| Mechanism | [e.g., session cookies] | [e.g., JWT Bearer tokens] |
| Token location | [e.g., httpOnly cookie] | [e.g., Authorization header] |
| Refresh | [e.g., automatic via cookie] | [e.g., explicit refresh endpoint] |
| Expiry | [duration] | [duration] |

---

## 6. Summary of Frontend Changes

| Change type | Count | Effort |
|------------|:-----:|:------:|
| Path changes only | N | Minimal — find/replace |
| Response shape changes | N | Medium — update type definitions |
| New endpoints | N | Medium — add API client methods |
| Dropped endpoints | N | Low — remove dead code |
| Auth mechanism change | 1 | High — replace auth library/flow |

---

## 7. Contract Tests

For each mapped endpoint, a contract test verifies the new backend returns the expected shape:

```
tests/contract/
├── test_auth_contract.py
├── test_users_contract.py
└── test_{domain}_contract.py
```

**Rule:** Every contract test that passes against the current backend must also pass against the new backend. Failures are either bugs (fix) or intentional changes (document in the mapping above).
