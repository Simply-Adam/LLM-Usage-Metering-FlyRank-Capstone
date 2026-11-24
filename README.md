# Usage Metering & Billing Engine

A FlyRank backend capstone that tracks tenant usage, enforces subscription quotas, calculates costs, and synchronizes subscriptions through Stripe test mode.

## Usage pricing

The app uses fixed demo rates (`demo-v1`) to estimate usage costs in USD.
These estimates are separate from the Stripe subscription price and do not
create charges.

| Resource | Price per unit (microdollars) |
| --- | ---: |
| API call | 100 |
| Fresh input token | 2 |
| Cached input token | 1 |
| Output token | 8 |

One US dollar equals 1,000,000 microdollars. The app calculates costs using
integers and returns `total_usd` as a string with six decimal places.

Fresh input is total input minus cached input. Reasoning tokens are already
included in the output count, so they aren't charged separately.

**Example:** One API call with 1,000 input tokens (200 cached) and 300 output
tokens (100 reasoning) costs `100 + (800 × 2) + (200 × 1) + (300 × 8)`,
or **4,300 microdollars ($0.004300)**.

`POST /generate` returns the estimate for one request. `GET /usage` returns
the authenticated tenant's estimate for the current UTC month.

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
The FastAPI application runs locally and exposes GET /health.
Database and billing features are not implemented yet.

## Non-goals

No real payments, real AI calls, invoicing, proration,
or overage billing in the core project.

## Local setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Migrate database:

```powershell
python -m app.migrate
```

Run from the repository root:

```powershell
python -m uvicorn app.main:app --reload
```

## Tests

Run from the project root with the virtual environment active:

```powershell
python -m unittest discover -s tests -v
```
Health endpoint: http://127.0.0.1:8000/health
API documentation: http://127.0.0.1:8000/docs