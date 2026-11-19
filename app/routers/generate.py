import sqlite3
from datetime import datetime
from email.utils import format_datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from app.dependencies import get_current_tenant
from app.schemas import GenerateRequest
from app.services.metering import MeteringError, record_usage


router = APIRouter(tags=["Metering"])

ERROR_STATUS = {
    "idempotency_conflict": 409,
    "payment_required": 402,
    "quota_exceeded": 429,
    "subscription_unavailable": 503,
}


@router.post("/generate")
def generate(
    request: GenerateRequest,
    tenant: dict = Depends(get_current_tenant),
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._:-]+$",
    ),
):
    try:
        status_code, body = record_usage(
            tenant["id"], request, idempotency_key
        )

        return JSONResponse(
            status_code=status_code,
            content=body,
        )

    except MeteringError as error:
        headers = {}

        if error.code == "quota_exceeded":
            reset = datetime.fromisoformat(
                error.detail["reset_at"].replace("Z", "+00:00")
            )
            headers["Retry-After"] = format_datetime(
                reset,
                usegmt=True,
            )

        raise HTTPException(
            status_code=ERROR_STATUS[error.code],
            detail={"code": error.code, **error.detail},
            headers=headers,
        ) from None

    except sqlite3.OperationalError as error:
        if (error.sqlite_errorcode & 0xFF) not in (
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
        ):
            raise

        raise HTTPException(
            status_code=503,
            detail="Database busy. Retry with the same Idempotency-Key.",
            headers={"Retry-After": "1"},
        ) from None