from fastapi import FastAPI

from app.routers import tenants


app = FastAPI(
    title="Usage Metering & Billing Engine",
    version="0.1.0",
)

app.include_router(tenants.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}