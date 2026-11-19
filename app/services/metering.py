import hashlib
import json
from datetime import datetime, timezone
from app.periods import month_bounds, utc_string
from uuid import uuid4

from app.database import get_connection
from app.repositories import usage_repository


class MeteringError(Exception):
    def __init__(self, code, message, **context):
        super().__init__(message)
        self.code = code
        self.detail = {"message": message, **context}


def record_usage(tenant_id, request, idempotency_key, now=None):
    payload = request.model_dump()
    canonical = json.dumps(payload, sort_keys=True)
    request_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        existing = usage_repository.find_event(
            connection, tenant_id, idempotency_key
        )

        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise MeteringError(
                    "idempotency_conflict",
                    "This Idempotency-Key was used with different data.",
                )

            body = json.loads(existing["response_body"])
            connection.execute("COMMIT")
            return existing["response_status"], body

        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        start_text, end_text = month_bounds(now)

        subscription = usage_repository.get_subscription(
            connection, tenant_id
        )

        if subscription is None:
            raise MeteringError(
                "subscription_unavailable",
                "No subscription is configured for this tenant.",
            )

        if subscription["status"] not in ("active", "trialing"):
            raise MeteringError(
                "payment_required",
                "Subscription is inactive. Update payment or subscription.",
            )

        usage = usage_repository.get_usage(
            connection, tenant_id, start_text, end_text
        )

        total_tokens = request.input_tokens + request.output_tokens

        for resource, requested, limit in [
            ("api_calls", 1, subscription["api_call_limit"]),
            ("tokens", total_tokens, subscription["token_limit"]),
        ]:
            if usage[resource] + requested > limit:
                raise MeteringError(
                    "quota_exceeded",
                    f"Monthly {resource} quota exceeded.",
                    resource=resource,
                    used=usage[resource],
                    requested=requested,
                    limit=limit,
                    reset_at=end_text,
                )

        body = {
            "result_id": str(uuid4()),
            "tenant_id": tenant_id,
            "message": "Simulated generation completed.",
            "usage": {
                "api_calls": 1,
                **payload,
                "total_tokens": total_tokens,
            },
        }

        event = {
            "tenant_id": tenant_id,
            "idempotency_key": idempotency_key,
            "request_hash": request_hash,
            "api_calls": 1,
            **payload,
            "created_at": utc_string(now),
            "response_status": 200,
            "response_body": json.dumps(body),
        }

        usage_repository.insert_event(connection, event)

        connection.execute("COMMIT")
        return 200, body

    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise

    finally:
        connection.close()