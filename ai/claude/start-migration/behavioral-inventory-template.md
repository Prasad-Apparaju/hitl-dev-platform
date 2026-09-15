# Source Behavioral Inventory — [Source System Name]

**Extracted from:** [repo path or URL]
**Extraction date:** [today's date]
**Status:** DRAFT — review with source system owner before use as migration target

## API surface

| ID | Endpoint / contract | Type | Domain | Notes |
|---|---|---|---|---|
| BI-001 | GET /users/{id} | REST | User | Returns user profile |

## Core behaviors

| ID | Behavior | Domain | Source location | Notes |
|---|---|---|---|---|
| BI-010 | Calculate order total with tax | Order | OrderService.java:45 | Includes promotional discount logic |

## Data contracts

| ID | Entity | Storage | Key fields | Notes |
|---|---|---|---|---|
| BI-020 | User | users table (PostgreSQL) | id, email, tenant_id | Multi-tenant — tenant_id on every query |

## Integration contracts

| ID | Integration | Direction | Protocol | Notes |
|---|---|---|---|---|
| BI-030 | Payment gateway | Outbound | REST | Stripe v3, async webhook confirmation |

## Background jobs

| ID | Job | Schedule / trigger | Domain | Notes |
|---|---|---|---|---|
| BI-040 | Invoice generation | Nightly 02:00 UTC | Billing | |

## Auth and access control

| ID | Rule | Scope | Notes |
|---|---|---|---|
| BI-050 | Admins can delete any user | Admin role | Non-admins see 403 |

## Known gaps

[Behaviors that could not be determined from code alone — require source system owner clarification]
