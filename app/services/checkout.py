import os
import logging

import stripe
from dotenv import load_dotenv

from app.database import PROJECT_ROOT, get_connection
from app.repositories.usage_repository import get_subscription


LOCAL_BILLING_URL = "http://127.0.0.1:8000/billing"


class CheckoutError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def get_stripe_settings():
    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")

    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    price_id = os.getenv("STRIPE_PRO_PRICE_ID", "").strip()

    if not secret_key.startswith("sk_test_") or not price_id.startswith("price_"):
        raise CheckoutError(
            "checkout_not_configured",
            "Configure a Stripe sandbox secret key and recurring Pro Price ID.",
        )

    return secret_key, price_id


def create_pro_checkout(tenant_id, idempotency_key):
    connection = get_connection()
    try:
        subscription = get_subscription(connection, tenant_id)
    finally:
        connection.close()

    if subscription is None:
        raise CheckoutError(
            "subscription_unavailable",
            "No subscription is configured for this tenant.",
        )

    linked_subscription = subscription["stripe_subscription_id"]
    has_open_subscription = (
        linked_subscription is not None
        and subscription["status"] not in ("canceled", "incomplete_expired")
    )

    if subscription["plan_name"] == "pro" or has_open_subscription:
        raise CheckoutError(
            "already_subscribed",
            "This tenant already has a Pro or open Stripe subscription.",
        )

    secret_key, price_id = get_stripe_settings()
    metadata = {"tenant_id": str(tenant_id)}

    params = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "client_reference_id": str(tenant_id),
        "metadata": metadata,
        "subscription_data": {"metadata": metadata},
        "success_url": f"{LOCAL_BILLING_URL}/success",
        "cancel_url": f"{LOCAL_BILLING_URL}/cancel",
    }

    if subscription["stripe_customer_id"]:
        params["customer"] = subscription["stripe_customer_id"]

    client = stripe.StripeClient(
        secret_key,
        http_client=stripe.RequestsClient(timeout=10),
        max_network_retries=1,
    )

    try:
        session = client.v1.checkout.sessions.create(
            params,
            options={
                "idempotency_key": f"checkout-pro:{tenant_id}:{idempotency_key}"
            },
        )
    except stripe.StripeError as error:
        logging.getLogger("uvicorn.error").warning(
            "Stripe Checkout failed: type=%s status=%s code=%s param=%s request_id=%s",
            type(error).__name__,
            error.http_status,
            error.code,
            getattr(error, "param", None),
            error.request_id,
        )
        raise CheckoutError(
            "stripe_unavailable",
            "Stripe could not create Checkout. Check the sandbox configuration "
            "or retry with the same Idempotency-Key.",
        ) from None

    if session.livemode is not False or not session.url:
        raise CheckoutError(
            "stripe_unavailable",
            "Stripe did not return a sandbox Checkout URL.",
        )

    return {"session_id": session.id, "checkout_url": session.url}