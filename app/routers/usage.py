import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_tenant
from app.services.metering import MeteringError
from app.services.usage import get_usage_summary


router = APIRouter(tags=["Usage"])


@router.get("/usage")
def read_usage(tenant: dict = Depends(get_current_tenant)):
    try:
        return get_usage_summary(tenant["id"])

    except MeteringError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": error.code, **error.detail},
        ) from None

    except sqlite3.OperationalError as error:
        if (error.sqlite_errorcode & 0xFF) not in (
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
        ):
            raise

        raise HTTPException(
            status_code=503,
            detail="Database busy. Try again shortly.",
            headers={"Retry-After": "1"},
        ) from None