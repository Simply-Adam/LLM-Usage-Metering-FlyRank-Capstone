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

Run from the repository root:

```powershell
python -m uvicorn app.main:app --reload
```

Health endpoint: http://127.0.0.1:8000/health
API documentation: http://127.0.0.1:8000/docs