from fastapi import FastAPI

from app.routers import billing, generate, tenants, usage

app = FastAPI(
    title="Usage Metering & Billing Engine",
    version="0.1.0",
)

app.include_router(tenants.router)
app.include_router(generate.router)
app.include_router(usage.router)
app.include_router(billing.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}