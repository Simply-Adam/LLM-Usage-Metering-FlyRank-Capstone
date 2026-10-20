# Usage Metering & Billing Engine

A FlyRank backend capstone that tracks tenant usage, enforces subscription quotas, calculates costs, and synchronizes subscriptions through Stripe test mode.

## Planned stack

- Python
- FastAPI
- SQLite
- Stripe test mode and Stripe CLI

## Core scope

- Free and Pro plans
- API-call and simulated AI-token usage
- One dummy billable endpoint
- Idempotent usage recording
- Monthly quotas and cost summaries
- Verified, deduplicated Stripe webhooks
- A background job with retries and failure reporting

## Current status

Stage 1: project setup.
The application is not implemented or runnable yet.

## Non-goals

No real payments, real AI calls, invoicing, proration,
or overage billing in the core project.