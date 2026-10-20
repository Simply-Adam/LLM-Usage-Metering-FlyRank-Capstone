# Usage Metering & Billing Engine — Design

## Problem and scope
Build a backend that records tenant usage, enforces monthly
allowances, calculates costs, and synchronizes subscriptions
through Stripe test mode.

A tenant represents one customer organization.
AI-token counts are simulated; no real AI calls are made.

Non-goal: real payments, invoicing, proration, and overage billing.

## Stack and layers
Python, FastAPI, SQLite, and Stripe test mode.

HTTP routes validate requests and call services.
Services apply billing rules and call repositories.
Repositories read and write SQLite.
Versioned SQL migrations define the database schema.

## Plans
| Plan | API calls/month | AI tokens/month |
| --- | ---: | ---: |
| Free | 1,000 | 100,000 |
| Pro | 10,000 | 1,000,000 |

Usage periods are calendar months in UTC.
Old events remain stored; monthly queries select the current period.

## Database tables
- plans: id, name, api_call_limit, token_limit.
- tenants: id, name, api_key_hash.
- subscriptions: tenant_id, plan_id, status,
  stripe_customer_id, stripe_subscription_id.
- usage_events: id, tenant_id, idempotency_key, request_hash,
  api_calls, input_tokens, cached_input_tokens, output_tokens,
  reasoning_tokens, created_at, response_status, response_body.
- webhook_events: stripe_event_id, event_type, payload,
  status, attempts, next_attempt_at, last_error, received_at.

Important constraints and indexes:
- Unique API-key hash.
- One subscription record per tenant.
- Unique (tenant_id, idempotency_key).
- Index usage_events on (tenant_id, created_at).
- Unique Stripe event ID.
- Index webhook_events on (status, next_attempt_at).

## API
| Method | Endpoint | Purpose |

| GET    | /health  | Confirm the service is running |
| POST   | /generate| Simulate an action and meter usage |
| GET    | /usage   | Return monthly usage, limits, and costs |
| POST   | /billing/checkout | Create a Stripe test Checkout session |
| POST   | /webhooks/stripe  | Verify and queue Stripe events |

Tenant routes require an X-API-Key header.
The server resolves the tenant from the key; clients cannot
select another tenant by passing a tenant ID.
The webhook uses Stripe signature verification instead.

## Metering and quotas
Each successful /generate request records one API call
and its simulated token counts in one usage event.

Require an Idempotency-Key header:
- Same tenant, key, and payload: return the saved response.
- Same tenant and key but different payload: return 409.
- New key: check subscription status and available quota.
- Exact quota is allowed; exceeding either quota returns 429.
- A subscription blocked for payment reasons returns 402.
- Rejected requests do not create billable usage events.

Check duplicates before checking current quotas.
Use one BEGIN IMMEDIATE transaction for the duplicate lookup,
quota check, and event insertion. Roll back on failure.

## Token and cost rules
All counts must be non-negative integers.
input_tokens includes cached_input_tokens.
output_tokens includes reasoning_tokens.

Require cached_input_tokens <= input_tokens.
Require reasoning_tokens <= output_tokens.

Quota tokens = input_tokens + output_tokens.
Fresh input = input_tokens - cached_input_tokens.
Price fresh input, cached input, and total output separately.
Do not add reasoning tokens to output a second time.

Pin illustrative prices in configuration during the cost stage.
Calculate money with integers and documented units, never floats.
Usage costs are estimates; they do not create overage charges.

## Stripe and background processing
Use test mode only. Verify the raw webhook body and signature
before accepting an event. Invalid signatures return 400.

Store each verified event once in webhook_events.
Return success only after the event is durably stored.

A separate worker processes queued events and synchronizes
subscriptions from Stripe's current state. Handle:
checkout.session.completed,
customer.subscription.updated,
customer.subscription.deleted.

Apply the local subscription update and mark the event processed
in one database transaction. Duplicate delivery must not reapply it.
Recover interrupted work. Retry transient failures up to three
attempts, then mark failed and emit a clear alert without secrets.

## Demo and security
Seed two independent demo tenants on Free.
Keep tenant API keys and Stripe secrets out of Git and logs.
Store tenant API-key hashes, not plaintext keys, in the database.
Populate EVIDENCE.md as each requirement is demonstrated.