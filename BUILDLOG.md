# Build Log

## Stage 1: Project setup

AI assistance:
- ChatGPT wrote the README and suggested some of the files to include in the gitignore file

Implementation and verification:


Corrections and changes:


## Stage 1: Design

AI assistance:
- ChatGPT drafted the schema and API 
- ChatGPT explained tenant isolation, idempotency, transactions, overlapping token categories, and background webhook processing.

## FastAPI application setup

AI assistance:
- Explained virtual environments, routing, JSON responses, and Uvicorn.
- Helped with setting up the virtual env and packages
Verification:
- Ran the application locally.
- Confirmed GET /health returns HTTP 200 and {"status":"ok"}.
- Confirmed the endpoint appears in /docs.


## Database connection and first migration

AI assistance:
- ChatGPT provided the connection helper, ideas on how to  
  setup the schema, and helped with the migration runner.
- Explained constraints, foreign keys, parameterized queries,
  transactions, and migration history.

Verification:
- First migration run reported "applied".
- Second run reported "skipped".
- Confirmed plans, tenants, subscriptions, and schema_migrations exist.

## Demo plans and tenants

AI assistance:
- ChatGPT provided the seed script and API-key hashing helper.
- Explained secure key generation, hashing, conflict handling, and SQL joins.

Verification:
- Seeded Free and Pro plans and two Free demo tenants.
- Repeated seeding; counts remained 2 plans, 2 tenants,
  and 2 subscriptions.
- Confirmed .env is ignored by Git.

## Tenant authentication

AI assistance:
- ChatGPT provided the protected router, and verification commands.
- Explained API-key lookup, dependency injection, and tenant identity.

Verification:
- Missing and invalid keys returned 401.
- Tenant A's key returned Tenant A.
- Tenant B's key returned Tenant B.
- A supplied tenant ID could not override the authenticated identity.


## Usage-event schema and request validation

AI assistance:
- ChatGPT provided the request schema, and validation tests.
- Explained tenant-scoped uniqueness, token-category relationships, strict validation, and unittest assertions.

Verification:
- Applied migration 002 and confirmed it is skipped on rerun.
- Confirmed usage_events exists and initially contains zero rows.
- Ran seven request-validation tests successfully.


## Metering and quota enforcement

AI assistance:
- ChatGPT provided the usage repository and integration tests.
- Explained transactions, request hashing, response replay,
  UTC usage periods, and concurrent-request testing.

Verification:
- All 16 tests passed.
- Retrying a successful request returned the original response
  and created exactly one event.
- Changed payloads returned 409.
- Exact quota boundaries succeeded; requests above them returned 429.
- Inactive subscriptions returned 402.
- Concurrent requests respected quotas and duplicate prevention.


## Monthly usage summary

AI assistance:
- ChatGPT provided the shared UTC-period helper, usage-summary
  service, router, and tests.
- Explained consistent read transactions, remaining allowances,
  and monthly boundary checks.

Verification:
- All 26 tests passed.
- Verified authenticated monthly totals and remaining allowances.
- Verified tenant isolation and UTC month boundaries.
- Verified changed plan limits in a temporary database.
- Confirmed reading usage creates no billable events.