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
