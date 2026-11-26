from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse

from app.dependencies import get_current_tenant
from app.services.checkout import CheckoutError, create_pro_checkout


router = APIRouter(prefix="/billing", tags=["Billing"])

ERROR_STATUS = {
    "checkout_not_configured": 503,
    "subscription_unavailable": 503,
    "already_subscribed": 409,
    "stripe_unavailable": 502,
}


@router.post("/checkout")
def start_checkout(
    tenant: dict = Depends(get_current_tenant),
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
    ),
):
    try:
        return create_pro_checkout(tenant["id"], idempotency_key)
    except CheckoutError as error:
        raise HTTPException(
            status_code=ERROR_STATUS[error.code],
            detail={"code": error.code, "message": str(error)},
        ) from None


@router.get("/success", response_class=PlainTextResponse, include_in_schema=False)
def checkout_success():
    return "Returned from Stripe Checkout. This page does not activate Pro."


@router.get("/cancel", response_class=PlainTextResponse, include_in_schema=False)
def checkout_cancel():
    return "You returned from Checkout without completing this flow."